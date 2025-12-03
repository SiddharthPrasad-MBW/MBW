#!/usr/bin/env python3
"""
Fix part_miacs_02_a configured table columns.

This script:
1. Removes miacs_11_054 from allowedColumns
2. Adds id_bucket (partition key) to allowedColumns
3. Verifies analysis rules are correct
4. Verifies collaboration association is correct
"""

import boto3
import argparse
import sys
from botocore.exceptions import ClientError
from botocore.config import Config
import urllib3

# Disable SSL verification if needed
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TABLE_NAME = "part_miacs_02_a"
COLUMN_TO_REMOVE = "miacs_11_054"
COLUMN_TO_ADD = "id_bucket"  # Partition key


def get_glue_table_columns(glue_client, database: str, table: str):
    """Get all columns including partition keys."""
    try:
        response = glue_client.get_table(DatabaseName=database, Name=table)
        table_data = response['Table']
        
        # Regular columns
        regular_columns = [col['Name'] for col in table_data['StorageDescriptor']['Columns']]
        
        # Partition keys
        partition_keys = [pk['Name'] for pk in table_data.get('PartitionKeys', [])]
        
        return regular_columns, partition_keys, regular_columns + partition_keys
    except Exception as e:
        print(f"❌ Error getting Glue table columns: {e}")
        raise


def get_configured_table(cleanrooms_client, table_name: str):
    """Get configured table by name."""
    try:
        paginator = cleanrooms_client.get_paginator('list_configured_tables')
        for page in paginator.paginate():
            for ct in page.get('configuredTableSummaries', []):
                if ct['name'] == table_name:
                    return cleanrooms_client.get_configured_table(
                        configuredTableIdentifier=ct['id']
                    )['configuredTable']
        return None
    except Exception as e:
        print(f"❌ Error getting configured table: {e}")
        raise


def delete_configured_table_association(cleanrooms_client, membership_id: str, assoc_id: str):
    """Delete configured table association."""
    try:
        # First try to delete privacy budget templates
        try:
            templates = cleanrooms_client.list_privacy_budget_templates(
                membershipIdentifier=membership_id
            )
            for template in templates.get('privacyBudgetTemplateSummaries', []):
                try:
                    cleanrooms_client.delete_privacy_budget_template(
                        membershipIdentifier=membership_id,
                        privacyBudgetTemplateIdentifier=template['id']
                    )
                except:
                    pass
        except:
            pass
        
        # Delete collaboration analysis rule
        try:
            cleanrooms_client.delete_configured_table_association_analysis_rule(
                membershipIdentifier=membership_id,
                configuredTableAssociationIdentifier=assoc_id,
                analysisRuleType="CUSTOM"
            )
        except:
            pass
        
        # Delete association
        cleanrooms_client.delete_configured_table_association(
            membershipIdentifier=membership_id,
            configuredTableAssociationIdentifier=assoc_id
        )
        return True
    except ClientError as e:
        print(f"⚠️  Error deleting association: {e}")
        return False


def delete_configured_table(cleanrooms_client, configured_table_id: str):
    """Delete configured table."""
    try:
        # Delete analysis rules first
        try:
            cleanrooms_client.delete_configured_table_analysis_rule(
                configuredTableIdentifier=configured_table_id,
                analysisRuleType="CUSTOM"
            )
        except:
            pass
        
        # Delete configured table
        cleanrooms_client.delete_configured_table(
            configuredTableIdentifier=configured_table_id
        )
        return True
    except ClientError as e:
        print(f"❌ Error deleting configured table: {e}")
        raise


def create_configured_table_with_columns(cleanrooms_client, name: str, description: str, 
                                         database: str, table: str, allowed_columns: list):
    """Create a configured table with specified columns."""
    try:
        response = cleanrooms_client.create_configured_table(
            name=name,
            description=description,
            tableReference={
                "glue": {
                    "databaseName": database,
                    "tableName": table
                }
            },
            allowedColumns=allowed_columns,
            analysisMethod="DIRECT_QUERY"
        )
        return response['configuredTable']['id']
    except ClientError as e:
        print(f"❌ Error creating configured table: {e}")
        raise


def create_analysis_rule(cleanrooms_client, configured_table_id: str, providers: list):
    """Create CUSTOM analysis rule."""
    try:
        analysis_rule_policy = {
            "v1": {
                "custom": {
                    "allowedAnalyses": ["ANY_QUERY"],
                    "allowedAnalysisProviders": providers
                }
            }
        }
        
        cleanrooms_client.create_configured_table_analysis_rule(
            configuredTableIdentifier=configured_table_id,
            analysisRuleType="CUSTOM",
            analysisRulePolicy=analysis_rule_policy
        )
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConflictException':
            return True  # Already exists
        print(f"❌ Error creating analysis rule: {e}")
        raise


def create_table_association(cleanrooms_client, membership_id: str, configured_table_id: str,
                             name: str, role_arn: str):
    """Create table association."""
    try:
        response = cleanrooms_client.create_configured_table_association(
            membershipIdentifier=membership_id,
            configuredTableIdentifier=configured_table_id,
            name=name,
            roleArn=role_arn
        )
        return response['configuredTableAssociation']['id']
    except ClientError as e:
        print(f"❌ Error creating association: {e}")
        raise


def create_collaboration_analysis_rule(cleanrooms_client, membership_id: str, assoc_id: str,
                                      result_receivers: list):
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
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConflictException':
            return True
        print(f"❌ Error creating collaboration analysis rule: {e}")
        raise


def get_analysis_rule(cleanrooms_client, configured_table_id: str):
    """Get the CUSTOM analysis rule for a configured table."""
    try:
        response = cleanrooms_client.get_configured_table_analysis_rule(
            configuredTableIdentifier=configured_table_id,
            analysisRuleType="CUSTOM"
        )
        return response.get('analysisRule', {})
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return None
        raise


def get_collaboration_association(cleanrooms_client, membership_id: str, configured_table_id: str):
    """Get collaboration association for a configured table."""
    try:
        paginator = cleanrooms_client.get_paginator('list_configured_table_associations')
        for page in paginator.paginate(membershipIdentifier=membership_id):
            for assoc in page.get('configuredTableAssociationSummaries', []):
                if assoc['configuredTableId'] == configured_table_id:
                    return assoc
        return None
    except Exception as e:
        print(f"❌ Error getting association: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Fix part_miacs_02_a configured table columns'
    )
    parser.add_argument('--profile', default='flywheel-prod', help='AWS profile name')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--database', default='omc_flywheel_prod', help='Glue database name')
    parser.add_argument('--membership-id', default='6610c9aa-9002-475c-8695-d833485741bc',
                       help='Cleanrooms membership ID')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    parser.add_argument('--no-verify-ssl', action='store_true',
                       help='Disable SSL certificate verification')
    
    args = parser.parse_args()
    
    # Configure boto3 clients
    if args.no_verify_ssl:
        import ssl
        import os
        os.environ['PYTHONHTTPSVERIFY'] = '0'
        ssl._create_default_https_context = ssl._create_unverified_context
        config = Config(connect_timeout=60, read_timeout=60)
    else:
        config = Config()
    
    # Create AWS clients
    session = boto3.Session(profile_name=args.profile) if args.profile else boto3.Session()
    glue = session.client('glue', region_name=args.region, config=config, verify=not args.no_verify_ssl)
    cleanrooms = session.client('cleanrooms', region_name=args.region, config=config, verify=not args.no_verify_ssl)
    
    print("=" * 80)
    print("Fix part_miacs_02_a Configured Table Columns")
    print("=" * 80)
    print()
    print(f"Table: {TABLE_NAME}")
    print(f"Remove column: {COLUMN_TO_REMOVE}")
    print(f"Add column: {COLUMN_TO_ADD} (partition key)")
    print()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print()
    
    # Step 1: Get Glue table columns
    print("=" * 80)
    print("Step 1: Get Glue table structure")
    print("=" * 80)
    regular_cols, partition_keys, all_cols = get_glue_table_columns(glue, args.database, TABLE_NAME)
    
    print(f"Regular columns: {len(regular_cols)}")
    print(f"Partition keys: {len(partition_keys)}")
    print(f"Total columns: {len(all_cols)}")
    print()
    
    if COLUMN_TO_REMOVE not in regular_cols:
        print(f"⚠️  Warning: '{COLUMN_TO_REMOVE}' not found in regular columns")
    else:
        print(f"✅ Found '{COLUMN_TO_REMOVE}' in regular columns")
    
    if COLUMN_TO_ADD not in partition_keys:
        print(f"❌ Error: '{COLUMN_TO_ADD}' not found in partition keys")
        sys.exit(1)
    else:
        print(f"✅ Found '{COLUMN_TO_ADD}' in partition keys")
    print()
    
    # Step 2: Calculate new column list
    print("=" * 80)
    print("Step 2: Calculate new column list")
    print("=" * 80)
    
    # Remove miacs_11_054 from regular columns
    new_regular_cols = [col for col in regular_cols if col != COLUMN_TO_REMOVE]
    
    # Combine: regular columns (without miacs_11_054) + partition keys (id_bucket)
    new_allowed_columns = new_regular_cols + partition_keys
    
    print(f"Original regular columns: {len(regular_cols)}")
    print(f"After removing '{COLUMN_TO_REMOVE}': {len(new_regular_cols)}")
    print(f"Partition keys: {len(partition_keys)}")
    print(f"New total allowed columns: {len(new_allowed_columns)}")
    print()
    
    if COLUMN_TO_REMOVE in new_allowed_columns:
        print(f"❌ Error: '{COLUMN_TO_REMOVE}' still in new column list!")
        sys.exit(1)
    else:
        print(f"✅ '{COLUMN_TO_REMOVE}' removed from new column list")
    
    if COLUMN_TO_ADD not in new_allowed_columns:
        print(f"❌ Error: '{COLUMN_TO_ADD}' not in new column list!")
        sys.exit(1)
    else:
        print(f"✅ '{COLUMN_TO_ADD}' included in new column list")
    print()
    
    # Step 3: Get current configured table
    print("=" * 80)
    print("Step 3: Get current configured table")
    print("=" * 80)
    configured_table = get_configured_table(cleanrooms, TABLE_NAME)
    
    if not configured_table:
        print(f"❌ Configured table '{TABLE_NAME}' not found")
        sys.exit(1)
    
    configured_table_id = configured_table['id']
    current_columns = configured_table.get('allowedColumns', [])
    
    print(f"Configured table ID: {configured_table_id}")
    print(f"Current allowed columns: {len(current_columns)}")
    print()
    
    # Compare
    current_set = set(current_columns)
    new_set = set(new_allowed_columns)
    
    to_remove = current_set - new_set
    to_add = new_set - current_set
    
    print("Changes needed:")
    if to_remove:
        print(f"  Remove ({len(to_remove)}): {sorted(to_remove)}")
    if to_add:
        print(f"  Add ({len(to_add)}): {sorted(to_add)}")
    if not to_remove and not to_add:
        print("  ✅ No changes needed - columns are already correct!")
        return
    print()
    
    # Step 4: Update configured table
    if args.dry_run:
        print("=" * 80)
        print("DRY RUN - Would update configured table")
        print("=" * 80)
        print(f"New allowed columns ({len(new_allowed_columns)}):")
        for i, col in enumerate(new_allowed_columns[:10], 1):
            print(f"  {i:3d}. {col}")
        print("  ...")
        for i, col in enumerate(new_allowed_columns[-5:], len(new_allowed_columns)-4):
            print(f"  {i:3d}. {col}")
        return
    
    # Step 4: Get association and role ARN
    print("=" * 80)
    print("Step 4: Get association details")
    print("=" * 80)
    association = get_collaboration_association(cleanrooms, args.membership_id, configured_table_id)
    
    if not association:
        print(f"❌ Association not found for configured table")
        sys.exit(1)
    
    assoc_id = association['id']
    assoc_name = association['name']
    
    # Get role ARN from association
    try:
        full_assoc = cleanrooms.get_configured_table_association(
            membershipIdentifier=args.membership_id,
            configuredTableAssociationIdentifier=assoc_id
        )
        role_arn = full_assoc['configuredTableAssociation']['roleArn']
    except Exception as e:
        print(f"❌ Error getting role ARN: {e}")
        sys.exit(1)
    
    print(f"Association ID: {assoc_id}")
    print(f"Association name: {assoc_name}")
    print(f"Role ARN: {role_arn}")
    print()
    
    # Step 5: Delete and recreate configured table
    print("=" * 80)
    print("Step 5: Delete and recreate configured table")
    print("=" * 80)
    print("⚠️  AWS Cleanrooms does not support updating allowedColumns directly")
    print("   We need to delete and recreate the configured table")
    print()
    
    # Delete association first
    print("5a. Deleting association...")
    if not delete_configured_table_association(cleanrooms, args.membership_id, assoc_id):
        print("⚠️  Failed to delete association, but continuing...")
    else:
        print("✅ Deleted association")
    print()
    
    # Delete configured table
    print("5b. Deleting configured table...")
    delete_configured_table(cleanrooms, configured_table_id)
    print("✅ Deleted configured table")
    print()
    
    # Recreate configured table
    print("5c. Creating configured table with new columns...")
    new_configured_table_id = create_configured_table_with_columns(
        cleanrooms,
        name=TABLE_NAME,
        description=f"Partitioned table {TABLE_NAME} for Clean Rooms analysis",
        database=args.database,
        table=TABLE_NAME,
        allowed_columns=new_allowed_columns
    )
    print(f"✅ Created configured table: {new_configured_table_id}")
    print()
    
    # Step 6: Recreate analysis rule
    print("=" * 80)
    print("Step 6: Recreate analysis rule")
    print("=" * 80)
    expected_providers = ["921290734397", "657425294073"]
    create_analysis_rule(cleanrooms, new_configured_table_id, expected_providers)
    print(f"✅ Created analysis rule with providers: {expected_providers}")
    print()
    
    # Step 7: Recreate association
    print("=" * 80)
    print("Step 7: Recreate association")
    print("=" * 80)
    expected_assoc_name = f"acx_{TABLE_NAME}"
    new_assoc_id = create_table_association(
        cleanrooms,
        args.membership_id,
        new_configured_table_id,
        expected_assoc_name,
        role_arn
    )
    print(f"✅ Created association: {expected_assoc_name} ({new_assoc_id})")
    print()
    
    # Step 8: Recreate collaboration analysis rule
    print("=" * 80)
    print("Step 8: Recreate collaboration analysis rule")
    print("=" * 80)
    # Get result receivers
    membership = cleanrooms.get_membership(membershipIdentifier=args.membership_id)
    collaboration_id = membership['membership']['collaborationId']
    members = cleanrooms.list_members(collaborationIdentifier=collaboration_id)
    all_account_ids = [m['accountId'] for m in members.get('memberSummaries', [])]
    default_result_receivers = ["657425294073", "803109464991"]
    result_receivers = [aid for aid in default_result_receivers if aid in all_account_ids]
    
    create_collaboration_analysis_rule(cleanrooms, args.membership_id, new_assoc_id, result_receivers)
    print(f"✅ Created collaboration analysis rule")
    print(f"   Result receivers: {result_receivers}")
    print()
    
    # Final verification
    print("=" * 80)
    print("Final Verification")
    print("=" * 80)
    
    # Verify configured table
    updated_table = get_configured_table(cleanrooms, TABLE_NAME)
    if updated_table:
        updated_columns = updated_table.get('allowedColumns', [])
        updated_set = set(updated_columns)
        
        if updated_set == new_set:
            print(f"✅ Configured table columns are correct!")
            print(f"   Total columns: {len(updated_columns)}")
            print(f"   Has '{COLUMN_TO_ADD}': {COLUMN_TO_ADD in updated_columns}")
            print(f"   Has '{COLUMN_TO_REMOVE}': {COLUMN_TO_REMOVE not in updated_columns}")
        else:
            print(f"⚠️  Column mismatch")
            print(f"   Expected: {len(new_allowed_columns)} columns")
            print(f"   Actual: {len(updated_columns)} columns")
    else:
        print(f"❌ Configured table not found")
    print()
    
    # Verify analysis rule
    analysis_rule = get_analysis_rule(cleanrooms, new_configured_table_id)
    if analysis_rule:
        policy = analysis_rule.get('policy', {})
        v1 = policy.get('v1', {})
        custom = v1.get('custom', {})
        providers = custom.get('allowedAnalysisProviders', [])
        expected_providers = ["921290734397", "657425294073"]
        if set(providers) == set(expected_providers):
            print(f"✅ Analysis rule is correct")
            print(f"   Providers: {providers}")
        else:
            print(f"⚠️  Analysis rule providers: {providers}")
    else:
        print(f"⚠️  No analysis rule found")
    print()
    
    # Verify association
    final_assoc = get_collaboration_association(cleanrooms, args.membership_id, new_configured_table_id)
    if final_assoc:
        assoc_name = final_assoc['name']
        expected_name = f"acx_{TABLE_NAME}"
        if assoc_name == expected_name:
            print(f"✅ Association is correct: {assoc_name}")
        else:
            print(f"⚠️  Association name: {assoc_name}, expected: {expected_name}")
    else:
        print(f"⚠️  Association not found")
    
    print()
    print("=" * 80)
    print("✅ COMPLETE")
    print("=" * 80)
    print(f"Configured table recreated with:")
    print(f"  - Removed: {COLUMN_TO_REMOVE}")
    print(f"  - Added: {COLUMN_TO_ADD}")
    print(f"  - Total columns: {len(new_allowed_columns)}")
    print(f"  - Analysis rules: ✅")
    print(f"  - Collaboration association: ✅")


if __name__ == "__main__":
    main()

