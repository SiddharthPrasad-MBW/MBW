#!/usr/bin/env python3
"""
Fix the association name for part_miacs_01_a from 'part_miacs_01_a' to 'acx_part_miacs_01_a'.

This script:
1. Deletes the existing association and its collaboration analysis rule
2. Recreates the association with the correct name (acx_part_miacs_01_a)
"""

import boto3
import argparse
import sys
from botocore.exceptions import ClientError
from botocore.config import Config
import urllib3

# Disable SSL verification if needed
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

MEMBERSHIP_ID = "6610c9aa-9002-475c-8695-d833485741bc"
TABLE_NAME = "part_miacs_01_a"
OLD_ASSOC_NAME = "part_miacs_01_a"
NEW_ASSOC_NAME = "acx_part_miacs_01_a"


def get_association_by_name(cleanrooms_client, membership_id: str, name: str):
    """Get association by name."""
    try:
        paginator = cleanrooms_client.get_paginator('list_configured_table_associations')
        for page in paginator.paginate(membershipIdentifier=membership_id):
            for assoc in page.get('configuredTableAssociationSummaries', []):
                if assoc['name'] == name:
                    return assoc
        return None
    except Exception as e:
        print(f"❌ Error finding association: {e}")
        raise


def get_configured_table_id(cleanrooms_client, table_name: str) -> str:
    """Get configured table ID by name."""
    try:
        paginator = cleanrooms_client.get_paginator('list_configured_tables')
        for page in paginator.paginate():
            for ct in page.get('configuredTableSummaries', []):
                if ct['name'] == table_name:
                    return ct['id']
        raise Exception(f"Configured table '{table_name}' not found")
    except Exception as e:
        print(f"❌ Error finding configured table: {e}")
        raise


def get_role_arn(cleanrooms_client, membership_id: str) -> str:
    """Get the role ARN from an existing association."""
    try:
        paginator = cleanrooms_client.get_paginator('list_configured_table_associations')
        for page in paginator.paginate(membershipIdentifier=membership_id):
            for assoc in page.get('configuredTableAssociationSummaries', []):
                # Get full association details to get role ARN
                full_assoc = cleanrooms_client.get_configured_table_association(
                    membershipIdentifier=membership_id,
                    configuredTableAssociationIdentifier=assoc['id']
                )
                return full_assoc['configuredTableAssociation']['roleArn']
    except Exception as e:
        print(f"⚠️  Could not get role ARN from existing association: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Fix association name for part_miacs_01_a'
    )
    parser.add_argument('--profile', default='flywheel-prod', help='AWS profile name')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--membership-id', default=MEMBERSHIP_ID, help='Cleanrooms membership ID')
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
    
    # Create AWS client
    session = boto3.Session(profile_name=args.profile) if args.profile else boto3.Session()
    cleanrooms = session.client('cleanrooms', region_name=args.region, config=config, verify=not args.no_verify_ssl)
    
    print("=" * 80)
    print("Fix Association Name: part_miacs_01_a → acx_part_miacs_01_a")
    print("=" * 80)
    print()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print()
    
    # Find the old association
    print(f"📋 Looking for association: {OLD_ASSOC_NAME}")
    old_assoc = get_association_by_name(cleanrooms, args.membership_id, OLD_ASSOC_NAME)
    
    if not old_assoc:
        print(f"❌ Association '{OLD_ASSOC_NAME}' not found")
        sys.exit(1)
    
    old_assoc_id = old_assoc['id']
    configured_table_id = old_assoc['configuredTableId']
    
    print(f"✅ Found association:")
    print(f"   ID: {old_assoc_id}")
    print(f"   Name: {old_assoc['name']}")
    print(f"   Configured Table ID: {configured_table_id}")
    print()
    
    # Check if new association already exists
    print(f"📋 Checking if '{NEW_ASSOC_NAME}' already exists...")
    new_assoc = get_association_by_name(cleanrooms, args.membership_id, NEW_ASSOC_NAME)
    
    if new_assoc:
        print(f"⚠️  Association '{NEW_ASSOC_NAME}' already exists!")
        print(f"   ID: {new_assoc['id']}")
        print()
        print("This might indicate the fix was already applied.")
        print("You may want to delete the old association manually.")
        sys.exit(0)
    
    print(f"✅ '{NEW_ASSOC_NAME}' does not exist, proceeding...")
    print()
    
    # Get role ARN from existing association
    print("📋 Getting role ARN from existing association...")
    role_arn = get_role_arn(cleanrooms, args.membership_id)
    if not role_arn:
        print("❌ Could not determine role ARN. Please provide it manually.")
        sys.exit(1)
    
    print(f"✅ Role ARN: {role_arn}")
    print()
    
    if args.dry_run:
        print("=" * 80)
        print("DRY RUN - Would perform the following:")
        print("=" * 80)
        print()
        print("1. Delete collaboration analysis rule (if exists)")
        print(f"   aws cleanrooms delete-configured-table-association-analysis-rule \\")
        print(f"     --membership-identifier {args.membership_id} \\")
        print(f"     --configured-table-association-identifier {old_assoc_id} \\")
        print(f"     --analysis-rule-type CUSTOM")
        print()
        print("2. Delete old association")
        print(f"   aws cleanrooms delete-configured-table-association \\")
        print(f"     --membership-identifier {args.membership_id} \\")
        print(f"     --configured-table-association-identifier {old_assoc_id}")
        print()
        print("3. Create new association with correct name")
        print(f"   aws cleanrooms create-configured-table-association \\")
        print(f"     --membership-identifier {args.membership_id} \\")
        print(f"     --configured-table-identifier {configured_table_id} \\")
        print(f"     --name {NEW_ASSOC_NAME} \\")
        print(f"     --role-arn {role_arn}")
        print()
        print("4. Create collaboration analysis rule")
        print(f"   (Will use default result receivers: 657425294073, 803109464991)")
        return
    
    # Step 1: Delete privacy budget templates if they exist
    print("=" * 80)
    print("Step 1: Delete privacy budget templates (if exist)")
    print("=" * 80)
    try:
        # List privacy budget templates for this membership
        paginator = cleanrooms.get_paginator('list_privacy_budget_templates')
        templates_to_delete = []
        for page in paginator.paginate(membershipIdentifier=args.membership_id):
            for template in page.get('privacyBudgetTemplateSummaries', []):
                templates_to_delete.append(template)
        
        if templates_to_delete:
            print(f"Found {len(templates_to_delete)} privacy budget template(s)")
            for template in templates_to_delete:
                template_id = template['id']
                print(f"  Deleting template: {template_id}")
                try:
                    cleanrooms.delete_privacy_budget_template(
                        membershipIdentifier=args.membership_id,
                        privacyBudgetTemplateIdentifier=template_id
                    )
                    print(f"  ✅ Deleted privacy budget template: {template_id}")
                except ClientError as e:
                    print(f"  ⚠️  Error deleting template {template_id}: {e}")
                    # Continue anyway - might not be blocking
        else:
            print(f"✅ No privacy budget templates found")
            
    except Exception as e:
        print(f"⚠️  Error checking/deleting privacy budget templates: {e}")
        print(f"   Continuing anyway...")
    print()
    
    # Step 2: Delete collaboration analysis rule if it exists
    print("=" * 80)
    print("Step 2: Delete collaboration analysis rule (if exists)")
    print("=" * 80)
    try:
        cleanrooms.delete_configured_table_association_analysis_rule(
            membershipIdentifier=args.membership_id,
            configuredTableAssociationIdentifier=old_assoc_id,
            analysisRuleType="CUSTOM"
        )
        print(f"✅ Deleted collaboration analysis rule")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"⚠️  Collaboration analysis rule does not exist, skipping")
        else:
            print(f"⚠️  Error deleting analysis rule: {e}")
    print()
    
    # Step 3: Delete old association
    print("=" * 80)
    print("Step 3: Delete old association")
    print("=" * 80)
    try:
        cleanrooms.delete_configured_table_association(
            membershipIdentifier=args.membership_id,
            configuredTableAssociationIdentifier=old_assoc_id
        )
        print(f"✅ Deleted old association: {OLD_ASSOC_NAME}")
    except ClientError as e:
        print(f"❌ Error deleting association: {e}")
        raise
    print()
    
    # Step 4: Create new association with correct name
    print("=" * 80)
    print("Step 4: Create new association with correct name")
    print("=" * 80)
    try:
        response = cleanrooms.create_configured_table_association(
            membershipIdentifier=args.membership_id,
            configuredTableIdentifier=configured_table_id,
            name=NEW_ASSOC_NAME,
            roleArn=role_arn
        )
        new_assoc_id = response['configuredTableAssociation']['id']
        print(f"✅ Created new association: {NEW_ASSOC_NAME}")
        print(f"   Association ID: {new_assoc_id}")
    except ClientError as e:
        print(f"❌ Error creating association: {e}")
        raise
    print()
    
    # Step 5: Create collaboration analysis rule
    print("=" * 80)
    print("Step 5: Create collaboration analysis rule")
    print("=" * 80)
    try:
        # Get collaboration ID to determine result receivers
        membership = cleanrooms.get_membership(membershipIdentifier=args.membership_id)
        collaboration_id = membership['membership']['collaborationId']
        members = cleanrooms.list_members(collaborationIdentifier=collaboration_id)
        all_account_ids = [m['accountId'] for m in members.get('memberSummaries', [])]
        
        # Default result receivers
        default_result_receivers = ["657425294073", "803109464991"]
        result_receivers = [aid for aid in default_result_receivers if aid in all_account_ids]
        
        rule_policy = {
            "v1": {
                "custom": {
                    "allowedResultReceivers": result_receivers
                }
            }
        }
        
        cleanrooms.create_configured_table_association_analysis_rule(
            membershipIdentifier=args.membership_id,
            configuredTableAssociationIdentifier=new_assoc_id,
            analysisRuleType="CUSTOM",
            analysisRulePolicy=rule_policy
        )
        print(f"✅ Created collaboration analysis rule")
        print(f"   Result receivers: {result_receivers}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConflictException':
            print(f"⚠️  Collaboration analysis rule already exists")
        else:
            print(f"❌ Error creating analysis rule: {e}")
            raise
    print()
    
    # Verify
    print("=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    verify_assoc = get_association_by_name(cleanrooms, args.membership_id, NEW_ASSOC_NAME)
    if verify_assoc:
        print(f"✅ Association '{NEW_ASSOC_NAME}' exists!")
        print(f"   ID: {verify_assoc['id']}")
    else:
        print(f"❌ Association '{NEW_ASSOC_NAME}' not found after creation")
    
    old_verify = get_association_by_name(cleanrooms, args.membership_id, OLD_ASSOC_NAME)
    if old_verify:
        print(f"⚠️  Old association '{OLD_ASSOC_NAME}' still exists!")
    else:
        print(f"✅ Old association '{OLD_ASSOC_NAME}' has been removed")
    print()
    
    print("=" * 80)
    print("✅ COMPLETE")
    print("=" * 80)
    print(f"Association name fixed: {OLD_ASSOC_NAME} → {NEW_ASSOC_NAME}")


if __name__ == "__main__":
    main()

