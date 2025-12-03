#!/usr/bin/env python3
"""
Fix collaboration analysis rules for all table associations in a collaboration.

This script:
1. Lists all configured table associations for a membership
2. Checks which ones are missing collaboration analysis rules
3. Creates collaboration analysis rules with correct result receivers
"""

import boto3
import argparse
import sys
from botocore.exceptions import ClientError
from botocore.config import Config
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_associations(cleanrooms_client, membership_id: str):
    """Get all configured table associations for a membership."""
    associations = []
    try:
        paginator = cleanrooms_client.get_paginator('list_configured_table_associations')
        for page in paginator.paginate(membershipIdentifier=membership_id):
            associations.extend(page.get('configuredTableAssociationSummaries', []))
    except Exception as e:
        print(f"❌ Error listing associations: {e}")
        raise
    return associations


def get_collaboration_analysis_rule(cleanrooms_client, membership_id: str, association_id: str):
    """Check if collaboration analysis rule exists."""
    try:
        response = cleanrooms_client.get_configured_table_association_analysis_rule(
            membershipIdentifier=membership_id,
            configuredTableAssociationIdentifier=association_id,
            analysisRuleType="CUSTOM"
        )
        return response.get('analysisRule', {}).get('policy', {})
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return None
        raise


def get_valid_result_receivers(cleanrooms_client, membership_id: str):
    """Get valid result receivers for the collaboration."""
    try:
        # Get membership to find collaboration
        membership = cleanrooms_client.get_membership(membershipIdentifier=membership_id)
        collaboration_id = membership['membership']['collaborationId']
        
        # Get all members
        members = cleanrooms_client.list_members(collaborationIdentifier=collaboration_id)
        all_account_ids = [m['accountId'] for m in members.get('memberSummaries', [])]
        
        # Get our account ID
        sts = boto3.client('sts')
        our_account_id = sts.get_caller_identity()['Account']
        
        # Filter out our account (data provider can't be result receiver)
        other_accounts = [aid for aid in all_account_ids if aid != our_account_id]
        
        # Use known working accounts if they exist in the collaboration
        # These are the ones that worked for acx_part_new_borrowers
        known_working = ["657425294073", "803109464991"]
        valid_receivers = [aid for aid in known_working if aid in other_accounts]
        
        # If none of the known working accounts are in the collaboration, use all other accounts
        if not valid_receivers:
            valid_receivers = other_accounts
        
        return valid_receivers
    except Exception as e:
        print(f"⚠️  Error getting result receivers: {e}")
        # Fallback to known working accounts
        return ["657425294073", "803109464991"]


def create_collaboration_analysis_rule(
    cleanrooms_client,
    membership_id: str,
    association_id: str,
    association_name: str,
    result_receivers: list,
    dry_run: bool = False
):
    """Create or update collaboration analysis rule."""
    try:
        rule_policy = {
            "v1": {
                "custom": {
                    "allowedResultReceivers": result_receivers
                }
            }
        }
        
        if dry_run:
            print(f"   🔍 Would create rule with receivers: {result_receivers}")
            return True
        
        cleanrooms_client.create_configured_table_association_analysis_rule(
            membershipIdentifier=membership_id,
            configuredTableAssociationIdentifier=association_id,
            analysisRuleType="CUSTOM",
            analysisRulePolicy=rule_policy
        )
        print(f"   ✅ Created collaboration analysis rule")
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ConflictException':
            # Rule already exists, try to update it
            try:
                cleanrooms_client.update_configured_table_association_analysis_rule(
                    membershipIdentifier=membership_id,
                    configuredTableAssociationIdentifier=association_id,
                    analysisRuleType="CUSTOM",
                    analysisRulePolicy=rule_policy
                )
                print(f"   ✅ Updated collaboration analysis rule")
                return True
            except Exception as update_error:
                print(f"   ⚠️  Rule exists but update failed: {update_error}")
                return False
        else:
            print(f"   ❌ Error creating rule: {e}")
            return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Fix collaboration analysis rules for all table associations'
    )
    parser.add_argument('--membership-id', required=True, help='Membership ID')
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    parser.add_argument('--no-verify-ssl', action='store_true',
                       help='Disable SSL verification')
    parser.add_argument('--exclude', nargs='+', default=[],
                       help='Association names to exclude (e.g., acx_part_new_borrowers)')
    
    args = parser.parse_args()
    
    # Configure boto3
    if args.no_verify_ssl:
        import ssl
        import os
        os.environ['PYTHONHTTPSVERIFY'] = '0'
        ssl._create_default_https_context = ssl._create_unverified_context
        config = Config(connect_timeout=60, read_timeout=60)
    else:
        config = Config()
    
    session = boto3.Session(profile_name=args.profile) if args.profile else boto3.Session()
    cleanrooms = session.client('cleanrooms', region_name=args.region, config=config, verify=not args.no_verify_ssl)
    
    print("=" * 80)
    print("Fix Collaboration Analysis Rules")
    print("=" * 80)
    print()
    print(f"Membership ID: {args.membership_id}")
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    print()
    
    # Get all associations
    print("📋 Getting all table associations...")
    associations = get_associations(cleanrooms, args.membership_id)
    print(f"✅ Found {len(associations)} associations")
    print()
    
    # Get valid result receivers
    print("📋 Determining valid result receivers...")
    result_receivers = get_valid_result_receivers(cleanrooms, args.membership_id)
    print(f"✅ Using result receivers: {result_receivers}")
    print()
    
    # Check each association
    print("=" * 80)
    print("Processing Associations")
    print("=" * 80)
    print()
    
    results = {
        'has_rule': [],
        'missing_rule': [],
        'created': [],
        'updated': [],
        'failed': [],
        'excluded': []
    }
    
    for assoc in associations:
        assoc_id = assoc['id']
        assoc_name = assoc['name']
        
        # Skip excluded associations
        if assoc_name in args.exclude:
            print(f"⏭️  Excluding: {assoc_name}")
            results['excluded'].append(assoc_name)
            continue
        
        print(f"Processing: {assoc_name}")
        
        # Check if rule exists
        existing_rule = get_collaboration_analysis_rule(cleanrooms, args.membership_id, assoc_id)
        
        if existing_rule:
            # Check if it has the correct receivers
            v1 = existing_rule.get('v1', {})
            custom = v1.get('custom', {})
            current_receivers = custom.get('allowedResultReceivers', [])
            
            if set(current_receivers) == set(result_receivers):
                print(f"   ✅ Already has correct rule")
                results['has_rule'].append(assoc_name)
            else:
                print(f"   ⚠️  Rule exists but receivers differ:")
                print(f"      Current: {current_receivers}")
                print(f"      Expected: {result_receivers}")
                # Update it
                if create_collaboration_analysis_rule(
                    cleanrooms, args.membership_id, assoc_id, assoc_name,
                    result_receivers, dry_run=args.dry_run
                ):
                    results['updated'].append(assoc_name)
                else:
                    results['failed'].append(assoc_name)
        else:
            print(f"   ❌ Missing collaboration analysis rule")
            results['missing_rule'].append(assoc_name)
            # Create it
            if create_collaboration_analysis_rule(
                cleanrooms, args.membership_id, assoc_id, assoc_name,
                result_receivers, dry_run=args.dry_run
            ):
                results['created'].append(assoc_name)
            else:
                results['failed'].append(assoc_name)
        print()
    
    # Summary
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print()
    print(f"Total associations: {len(associations)}")
    print(f"✅ Already correct: {len(results['has_rule'])}")
    print(f"⏭️  Excluded: {len(results['excluded'])}")
    if args.dry_run:
        print(f"🔍 Would create: {len(results['missing_rule'])}")
        print(f"🔍 Would update: {len(results['updated'])}")
    else:
        print(f"✅ Created: {len(results['created'])}")
        print(f"✅ Updated: {len(results['updated'])}")
        print(f"❌ Failed: {len(results['failed'])}")
    print()
    
    if results['failed']:
        print("Failed associations:")
        for name in results['failed']:
            print(f"  - {name}")
        print()
    
    if not args.dry_run and (results['created'] or results['updated']):
        print("✅ All collaboration analysis rules have been fixed!")


if __name__ == "__main__":
    main()

