#!/usr/bin/env python3
"""
Refresh Cleanrooms Collaboration Associations with New Naming Convention

This script migrates existing collaboration associations from the old naming
convention (part_*-assoc) to the new convention (acx_part_*).

It will:
1. List all existing associations
2. For each association:
   - Delete the collaboration analysis rule
   - Delete the old association
   - Create new association with acx_ prefix
   - Recreate collaboration analysis rule
"""

import boto3
import argparse
import urllib3
import ssl
import os
from botocore.exceptions import ClientError
from botocore.config import Config

# Disable SSL verification if needed
def setup_ssl_bypass():
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    os.environ['PYTHONHTTPSVERIFY'] = '0'
    ssl._create_default_https_context = ssl._create_unverified_context


def get_existing_associations(cleanrooms_client, membership_id):
    """Get all existing associations for the membership."""
    assoc_list = []
    paginator = cleanrooms_client.get_paginator('list_configured_table_associations')
    for page in paginator.paginate(membershipIdentifier=membership_id):
        assoc_list.extend(page.get('configuredTableAssociationSummaries', []))
    return assoc_list


def delete_collaboration_analysis_rule(cleanrooms_client, membership_id, assoc_id):
    """Delete collaboration analysis rule if it exists."""
    try:
        cleanrooms_client.delete_configured_table_association_analysis_rule(
            membershipIdentifier=membership_id,
            configuredTableAssociationIdentifier=assoc_id,
            analysisRuleType='CUSTOM'
        )
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return False  # Rule doesn't exist, that's fine
        print(f"⚠️  Error deleting collaboration analysis rule: {e}")
        return False


def delete_association(cleanrooms_client, membership_id, assoc_id, assoc_name):
    """Delete an association."""
    try:
        cleanrooms_client.delete_configured_table_association(
            membershipIdentifier=membership_id,
            configuredTableAssociationIdentifier=assoc_id
        )
        print(f"✅ Deleted old association: {assoc_name} ({assoc_id})")
        return True
    except ClientError as e:
        print(f"❌ Error deleting association {assoc_name}: {e}")
        return False


def create_new_association(cleanrooms_client, membership_id, configured_table_id, new_name, role_arn):
    """Create a new association with acx_ prefix."""
    try:
        response = cleanrooms_client.create_configured_table_association(
            membershipIdentifier=membership_id,
            configuredTableIdentifier=configured_table_id,
            name=new_name,
            roleArn=role_arn
        )
        new_assoc_id = response['configuredTableAssociation']['id']
        print(f"✅ Created new association: {new_name} ({new_assoc_id})")
        return new_assoc_id
    except ClientError as e:
        print(f"❌ Error creating association {new_name}: {e}")
        return None


def create_collaboration_analysis_rule(cleanrooms_client, membership_id, assoc_id, result_receivers):
    """Create collaboration analysis rule."""
    try:
        rule_policy = {
            "v1": {
                "custom": {
                    "allowedResultReceivers": result_receivers
                }
            }
        }
        
        cleanrooms_client.create_configured_table_association_analysis_rule(
            membershipIdentifier=membership_id,
            configuredTableAssociationIdentifier=assoc_id,
            analysisRuleType="CUSTOM",
            analysisRulePolicy=rule_policy
        )
        print(f"✅ Created collaboration analysis rule")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConflictException':
            print(f"⚠️  Collaboration analysis rule already exists")
            return True
        print(f"❌ Error creating collaboration analysis rule: {e}")
        return False


def get_new_association_name(old_name):
    """Convert old association name to new naming convention."""
    # Old: part_ibe_01-assoc or part_ibe_01_assoc
    # New: acx_part_ibe_01
    
    # Remove -assoc or _assoc suffix
    if old_name.endswith('-assoc'):
        base_name = old_name[:-6]  # Remove '-assoc'
    elif old_name.endswith('_assoc'):
        base_name = old_name[:-6]  # Remove '_assoc'
    else:
        # If it doesn't have the suffix, assume it's already the base name
        base_name = old_name
    
    # Add acx_ prefix
    if not base_name.startswith('acx_'):
        return f"acx_{base_name}"
    return base_name


def main():
    parser = argparse.ArgumentParser(description='Refresh collaboration associations with new naming')
    parser.add_argument('--membership-id', required=True, help='Cleanrooms membership ID')
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--role-name', default='cleanrooms-glue-s3-access', help='IAM role name')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--no-verify-ssl', action='store_true', help='Disable SSL certificate verification')
    
    args = parser.parse_args()
    
    # Configure SSL if needed
    if args.no_verify_ssl:
        setup_ssl_bypass()
        config = Config(connect_timeout=60, read_timeout=60)
    else:
        config = Config()
    
    # Create AWS clients
    session = boto3.Session(profile_name=args.profile) if args.profile else boto3.Session()
    cleanrooms = session.client('cleanrooms', region_name=args.region, config=config, verify=not args.no_verify_ssl)
    iam = session.client('iam', region_name=args.region, config=config, verify=not args.no_verify_ssl)
    
    # Get IAM role ARN
    try:
        role_response = iam.get_role(RoleName=args.role_name)
        role_arn = role_response['Role']['Arn']
        print(f'✅ Found IAM role: {role_arn}\n')
    except Exception as e:
        print(f'❌ Error getting IAM role: {e}')
        return
    
    # Get collaboration ID and result receivers
    try:
        membership = cleanrooms.get_membership(membershipIdentifier=args.membership_id)
        collaboration_id = membership['membership']['collaborationId']
        members = cleanrooms.list_members(collaborationIdentifier=collaboration_id)
        all_account_ids = [m['accountId'] for m in members.get('memberSummaries', [])]
        default_account_ids = ["657425294073", "803109464991"]
        result_receivers = [aid for aid in default_account_ids if aid in all_account_ids]
        if not result_receivers:
            result_receivers = all_account_ids
        print(f'Using result receivers: {result_receivers}\n')
    except Exception as e:
        print(f'⚠️  Could not determine result receivers: {e}')
        result_receivers = []
    
    # Get all existing associations
    print('📋 Getting existing associations...\n')
    associations = get_existing_associations(cleanrooms, args.membership_id)
    print(f'Found {len(associations)} existing associations\n')
    
    if args.dry_run:
        print('🔍 DRY RUN MODE - No changes will be made\n')
        print('=' * 60)
        for assoc in associations:
            old_name = assoc['name']
            new_name = get_new_association_name(old_name)
            if old_name != new_name:
                print(f'Would migrate: {old_name} → {new_name}')
            else:
                print(f'Already correct: {old_name}')
        print('=' * 60)
        return
    
    # Process each association
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for assoc in associations:
        old_name = assoc['name']
        new_name = get_new_association_name(old_name)
        assoc_id = assoc['id']
        configured_table_id = assoc['configuredTableId']
        
        print(f'\n{"=" * 60}')
        print(f'Processing: {old_name}')
        print(f'{"=" * 60}')
        
        # Skip if already using new naming
        if old_name == new_name:
            print(f'✅ Already using new naming convention, skipping')
            skipped_count += 1
            continue
        
        # Check if new association already exists
        existing_new = None
        all_assocs = get_existing_associations(cleanrooms, args.membership_id)
        for a in all_assocs:
            if a['name'] == new_name:
                existing_new = a
                break
        
        if existing_new:
            print(f'⚠️  New association {new_name} already exists, deleting old one only')
            # Just delete the old one
            delete_collaboration_analysis_rule(cleanrooms, args.membership_id, assoc_id)
            if delete_association(cleanrooms, args.membership_id, assoc_id, old_name):
                success_count += 1
            else:
                failed_count += 1
            continue
        
        # Step 1: Delete collaboration analysis rule
        print(f'Step 1: Deleting collaboration analysis rule...')
        delete_collaboration_analysis_rule(cleanrooms, args.membership_id, assoc_id)
        
        # Step 2: Delete old association
        print(f'Step 2: Deleting old association...')
        if not delete_association(cleanrooms, args.membership_id, assoc_id, old_name):
            failed_count += 1
            continue
        
        # Step 3: Create new association
        print(f'Step 3: Creating new association {new_name}...')
        new_assoc_id = create_new_association(
            cleanrooms, args.membership_id, configured_table_id, new_name, role_arn
        )
        
        if not new_assoc_id:
            failed_count += 1
            continue
        
        # Step 4: Create collaboration analysis rule
        print(f'Step 4: Creating collaboration analysis rule...')
        if create_collaboration_analysis_rule(cleanrooms, args.membership_id, new_assoc_id, result_receivers):
            success_count += 1
            print(f'✅ Successfully migrated: {old_name} → {new_name}')
        else:
            failed_count += 1
    
    # Final summary
    print(f'\n{"=" * 60}')
    print('✅ MIGRATION COMPLETE')
    print(f'{"=" * 60}')
    print(f'Successfully migrated: {success_count}')
    print(f'Failed: {failed_count}')
    print(f'Skipped (already correct): {skipped_count}')
    print()
    
    # Verify final state
    final_assocs = get_existing_associations(cleanrooms, args.membership_id)
    print(f'Final association count: {len(final_assocs)}')
    
    # Show naming summary
    acx_count = sum(1 for a in final_assocs if a['name'].startswith('acx_'))
    old_count = len(final_assocs) - acx_count
    print(f'  - Using acx_ prefix: {acx_count}')
    print(f'  - Old naming: {old_count}')


if __name__ == "__main__":
    main()

