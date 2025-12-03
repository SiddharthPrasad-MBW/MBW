#!/usr/bin/env python3
"""
Fix collaboration association names using dynamic discovery.

This script:
1. Dynamically discovers all configured tables starting with "part_"
2. Excludes part_n_a and part_n_a_a
3. Deletes all existing associations (two-phase approach for idempotency)
4. Creates new associations with correct names (acx_<table_name>)
5. Limits to 25 associations (AWS quota limit)
"""

import boto3
import argparse
import sys
from botocore.exceptions import ClientError
from botocore.config import Config
import urllib3

MAX_ASSOCIATIONS = 25  # AWS quota limit
EXCLUDED_TABLES = ['part_n_a', 'part_n_a_a']


def get_collaboration_id(cleanrooms_client, membership_id):
    """Get collaboration ID from membership ID."""
    try:
        membership = cleanrooms_client.get_membership(membershipIdentifier=membership_id)
        return membership['membership']['collaborationId']
    except Exception as e:
        print(f"❌ Error getting collaboration ID: {e}")
        raise


def discover_configured_tables(cleanrooms_client):
    """Dynamically discover all configured tables starting with 'part_'."""
    print("📋 Discovering configured tables...")
    tables = []
    
    try:
        paginator = cleanrooms_client.get_paginator('list_configured_tables')
        for page in paginator.paginate():
            for table in page.get('configuredTableSummaries', []):
                table_name = table.get('name', '')
                table_id = table.get('id', '')
                
                # Filter: must start with "part_" and not be excluded
                if (table_name.startswith('part_') and 
                    table_name not in EXCLUDED_TABLES and
                    table_id):
                    tables.append({
                        'name': table_name,
                        'id': table_id
                    })
        
        # Sort alphabetically
        tables.sort(key=lambda x: x['name'])
        
        print(f"   Found {len(tables)} configured tables starting with 'part_'")
        print(f"   Excluded: {', '.join(EXCLUDED_TABLES)}")
        
        # Limit to quota
        if len(tables) > MAX_ASSOCIATIONS:
            print(f"   ⚠️  Limiting to first {MAX_ASSOCIATIONS} tables (quota limit)")
            tables = tables[:MAX_ASSOCIATIONS]
        
        return tables
    except Exception as e:
        print(f"❌ Error discovering configured tables: {e}")
        raise


def get_existing_associations(cleanrooms_client, membership_id):
    """Get all existing associations for a membership."""
    existing = {}
    try:
        paginator = cleanrooms_client.get_paginator('list_configured_table_associations')
        for page in paginator.paginate(membershipIdentifier=membership_id):
            for assoc in page.get('configuredTableAssociationSummaries', []):
                table_id = assoc.get('configuredTableId') or assoc.get('configuredTableIdentifier')
                if table_id:
                    existing[table_id] = {
                        'id': assoc['id'],
                        'name': assoc['name']
                    }
    except Exception as e:
        print(f"⚠️  Error listing associations: {e}")
    return existing


def delete_all_associations(cleanrooms_client, membership_id, existing_associations, dry_run=False):
    """Delete all existing associations (Phase 1)."""
    print(f"\n🗑️  PHASE 1: Deleting all existing associations...")
    print(f"   Found {len(existing_associations)} associations to delete\n")
    
    deleted_count = 0
    failed_count = 0
    
    for table_id, assoc_info in existing_associations.items():
        assoc_id = assoc_info['id']
        assoc_name = assoc_info['name']
        
        if dry_run:
            print(f"   Would delete: {assoc_name} (ID: {assoc_id})")
            deleted_count += 1
        else:
            try:
                cleanrooms_client.delete_configured_table_association(
                    membershipIdentifier=membership_id,
                    configuredTableAssociationIdentifier=assoc_id
                )
                print(f"   ✅ Deleted: {assoc_name}")
                deleted_count += 1
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    print(f"   ⏭️  Already deleted: {assoc_name}")
                    deleted_count += 1
                else:
                    print(f"   ❌ Error deleting {assoc_name}: {e}")
                    failed_count += 1
            except Exception as e:
                print(f"   ❌ Error deleting {assoc_name}: {e}")
                failed_count += 1
    
    print(f"\n   Deleted: {deleted_count}")
    if failed_count > 0:
        print(f"   Failed: {failed_count}")
    
    return deleted_count, failed_count


def create_associations(cleanrooms_client, membership_id, tables, role_arn, dry_run=False):
    """Create associations for discovered tables (Phase 2)."""
    print(f"\n➕ PHASE 2: Creating associations for {len(tables)} tables...\n")
    
    created_count = 0
    skipped_count = 0
    failed_count = 0
    
    for table in tables:
        table_name = table['name']
        table_id = table['id']
        association_name = f"acx_{table_name}"
        
        if dry_run:
            print(f"   Would create: {association_name} (table: {table_name})")
            created_count += 1
        else:
            try:
                response = cleanrooms_client.create_configured_table_association(
                    membershipIdentifier=membership_id,
                    configuredTableIdentifier=table_id,
                    name=association_name,
                    description=f"ACX standard table {table_name}",
                    roleArn=role_arn
                )
                assoc_id = response['configuredTableAssociation']['id']
                print(f"   ✅ Created: {association_name} (ID: {assoc_id})")
                created_count += 1
            except ClientError as e:
                if e.response['Error']['Code'] == 'ConflictException':
                    print(f"   ⏭️  Already exists: {association_name}")
                    skipped_count += 1
                else:
                    print(f"   ❌ Error creating {association_name}: {e}")
                    failed_count += 1
            except Exception as e:
                print(f"   ❌ Error creating {association_name}: {e}")
                failed_count += 1
    
    print(f"\n   Created: {created_count}")
    if skipped_count > 0:
        print(f"   Skipped (already exists): {skipped_count}")
    if failed_count > 0:
        print(f"   Failed: {failed_count}")
    
    return created_count, skipped_count, failed_count


def get_role_arn(cleanrooms_client, role_name):
    """Get IAM role ARN for Cleanrooms access."""
    try:
        sts = boto3.client('sts')
        account_id = sts.get_caller_identity()['Account']
        return f"arn:aws:iam::{account_id}:role/{role_name}"
    except Exception as e:
        print(f"⚠️  Could not determine role ARN: {e}")
        return None


def verify_final_state(cleanrooms_client, membership_id, expected_tables):
    """Verify final state after operations."""
    print(f"\n🔍 Verifying final state...")
    
    existing = get_existing_associations(cleanrooms_client, membership_id)
    expected_table_ids = {t['id']: t['name'] for t in expected_tables}
    
    correct_count = 0
    wrong_name_count = 0
    unexpected_count = 0
    
    for table_id, assoc_info in existing.items():
        if table_id in expected_table_ids:
            expected_name = f"acx_{expected_table_ids[table_id]}"
            if assoc_info['name'] == expected_name:
                correct_count += 1
            else:
                wrong_name_count += 1
                print(f"   ⚠️  Wrong name: {assoc_info['name']} (expected: {expected_name})")
        else:
            unexpected_count += 1
            print(f"   ⚠️  Unexpected association: {assoc_info['name']} (table ID: {table_id})")
    
    print(f"\n   ✅ Correct: {correct_count}")
    if wrong_name_count > 0:
        print(f"   ⚠️  Wrong names: {wrong_name_count}")
    if unexpected_count > 0:
        print(f"   ⚠️  Unexpected: {unexpected_count}")
    
    return correct_count == len(expected_tables) and wrong_name_count == 0 and unexpected_count == 0


def main():
    parser = argparse.ArgumentParser(
        description='Fix collaboration association names using dynamic discovery'
    )
    parser.add_argument('--membership-id', required=True,
                       help='Cleanrooms membership ID')
    parser.add_argument('--role-name', default='cleanrooms-glue-s3-access',
                       help='IAM role name for Cleanrooms access (default: cleanrooms-glue-s3-access)')
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    parser.add_argument('--no-verify-ssl', action='store_true',
                       help='Disable SSL certificate verification')
    
    args = parser.parse_args()
    
    # Configure boto3 clients
    if args.no_verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        import ssl
        import os
        os.environ['PYTHONHTTPSVERIFY'] = '0'
        ssl._create_default_https_context = ssl._create_unverified_context
        config = Config(connect_timeout=60, read_timeout=60)
    else:
        config = Config()
    
    # Create AWS client
    session = boto3.Session(profile_name=args.profile) if args.profile else boto3.Session()
    cleanrooms = session.client('cleanrooms', region_name=args.region, config=config, verify=not args.no_verify_ssl)
    
    print(f"\n🔧 Fixing Collaboration Associations (Dynamic Discovery)")
    print(f"   Membership ID: {args.membership_id}")
    print(f"   Region: {args.region}")
    if args.dry_run:
        print(f"   🔍 DRY RUN MODE - No changes will be made\n")
    else:
        print()
    
    # Get collaboration ID
    print(f"📋 Getting collaboration ID...")
    try:
        collaboration_id = get_collaboration_id(cleanrooms, args.membership_id)
        print(f"   ✅ Collaboration ID: {collaboration_id}\n")
    except Exception as e:
        print(f"   ❌ Failed to get collaboration ID: {e}")
        sys.exit(1)
    
    # Get role ARN
    role_arn = get_role_arn(cleanrooms, args.role_name)
    if not role_arn:
        print(f"   ❌ Failed to get role ARN")
        sys.exit(1)
    print(f"   ✅ Using role: {role_arn}\n")
    
    # Discover configured tables
    try:
        tables = discover_configured_tables(cleanrooms)
        if not tables:
            print("   ❌ No configured tables found starting with 'part_'")
            sys.exit(1)
        print(f"   ✅ Will process {len(tables)} tables\n")
    except Exception as e:
        print(f"   ❌ Failed to discover configured tables: {e}")
        sys.exit(1)
    
    # Get existing associations
    existing_associations = get_existing_associations(cleanrooms, args.membership_id)
    print(f"📋 Found {len(existing_associations)} existing associations\n")
    
    # PHASE 1: Delete all existing associations
    deleted_count, delete_failed = delete_all_associations(
        cleanrooms, args.membership_id, existing_associations, args.dry_run
    )
    
    if not args.dry_run and delete_failed > 0:
        print(f"\n⚠️  Warning: {delete_failed} deletions failed. Continuing anyway...")
    
    # PHASE 2: Create associations for discovered tables
    created_count, skipped_count, create_failed = create_associations(
        cleanrooms, args.membership_id, tables, role_arn, args.dry_run
    )
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    print(f"  Discovered tables: {len(tables)}")
    print(f"  Deleted associations: {deleted_count}")
    if delete_failed > 0:
        print(f"  Delete failures: {delete_failed}")
    print(f"  Created associations: {created_count}")
    if skipped_count > 0:
        print(f"  Skipped (already exists): {skipped_count}")
    if create_failed > 0:
        print(f"  Create failures: {create_failed}")
    print()
    
    if not args.dry_run:
        # Verify final state
        if verify_final_state(cleanrooms, args.membership_id, tables):
            print("✅ All associations have correct names!")
        else:
            print("⚠️  Some associations may need attention")
    else:
        print("🔍 DRY RUN complete - no changes made")


if __name__ == "__main__":
    main()
