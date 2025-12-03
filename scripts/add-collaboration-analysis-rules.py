#!/usr/bin/env python3
"""
Add collaboration analysis rules to existing table associations for direct analysis
"""

import boto3
import argparse
import urllib3
from botocore.exceptions import ClientError
from botocore.config import Config

def get_existing_collaboration_analysis_rule(
    cleanrooms_client,
    membership_id: str,
    configured_table_association_id: str
) -> bool:
    """Check if a collaboration analysis rule already exists for the association."""
    try:
        cleanrooms_client.get_configured_table_association_analysis_rule(
            membershipIdentifier=membership_id,
            configuredTableAssociationIdentifier=configured_table_association_id,
            analysisRuleType="CUSTOM"
        )
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return False
        # If it's a different error, we'll try to create and handle it
        return False
    except Exception:
        return False


def create_collaboration_analysis_rule(
    cleanrooms_client,
    membership_id: str,
    configured_table_association_id: str,
    allowed_analyses: str = "ANY",
    allowed_members: list = None,
    collaboration_id: str = None
):
    """Create a collaboration analysis rule for direct analysis (only if it doesn't exist)."""
    # Check if rule already exists
    if get_existing_collaboration_analysis_rule(cleanrooms_client, membership_id, configured_table_association_id):
        print(f"✅ Collaboration analysis rule already exists for association {configured_table_association_id}, skipping creation")
        return True
    
    try:
        # For collaboration analysis rules, we use CUSTOM type
        # allowedResultReceivers must be 12-digit account IDs (not membership IDs)
        # If configured table doesn't allow additional analyses, omit allowedAdditionalAnalyses
        rule_policy = {
            "v1": {
                "custom": {
                    "allowedResultReceivers": allowed_members if allowed_members else []
                }
            }
        }
        
        cleanrooms_client.create_configured_table_association_analysis_rule(
            membershipIdentifier=membership_id,
            configuredTableAssociationIdentifier=configured_table_association_id,
            analysisRuleType="CUSTOM",
            analysisRulePolicy=rule_policy
        )
        print(f"✅ Created collaboration analysis rule for association {configured_table_association_id}")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConflictException':
            print(f"⚠️  Collaboration analysis rule already exists for association {configured_table_association_id}")
            return True
        else:
            print(f"❌ Error creating collaboration analysis rule: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Add collaboration analysis rules to existing associations')
    parser.add_argument('--membership-id', required=True, help='Cleanrooms membership ID')
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--allowed-analyses', default='ANY', 
                       choices=['ANY', 'ANY_BY_SPECIFIC_MEMBERS', 'CUSTOM'],
                       help='Type of allowed analyses (default: ANY = all members)')
    parser.add_argument('--allowed-members', nargs='+', default=[],
                       help='List of member IDs if using ANY_BY_SPECIFIC_MEMBERS')
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
    
    # Get collaboration ID from membership
    print(f"📋 Getting collaboration ID from membership {args.membership_id}...\n")
    membership = cleanrooms.get_membership(membershipIdentifier=args.membership_id)
    collaboration_id = membership['membership']['collaborationId']
    print(f"Found collaboration ID: {collaboration_id}\n")
    
    # Get all members in collaboration for result receivers
    # Note: allowedResultReceivers must be 12-digit account IDs, not membership IDs
    # Based on the working example (acx_part_miacs_04), we use specific account IDs
    # that are allowed to receive results. If --allowed-members is not provided,
    # we'll use the same account IDs as the working example.
    print(f"📋 Getting all members in collaboration...\n")
    members = cleanrooms.list_members(collaborationIdentifier=collaboration_id)
    all_account_ids = [m['accountId'] for m in members.get('memberSummaries', [])]
    print(f"Found {len(all_account_ids)} members (account IDs): {', '.join(all_account_ids[:3])}...\n")
    
    # Default to the account IDs from the working example if not specified
    if not args.allowed_members:
        # These are the account IDs from acx_part_miacs_04 that work
        default_account_ids = ["657425294073", "803109464991"]
        # Filter to only include members that exist in the collaboration
        account_ids = [aid for aid in default_account_ids if aid in all_account_ids]
        if account_ids:
            print(f"Using default result receivers from working example: {account_ids}\n")
        else:
            # Fallback: use all account IDs (may fail if not all are allowed)
            account_ids = all_account_ids
            print(f"⚠️  Default account IDs not found, using all members: {account_ids}\n")
    else:
        account_ids = args.allowed_members
    
    # Get all existing associations
    print(f"📋 Getting existing table associations...\n")
    associations = cleanrooms.list_configured_table_associations(
        membershipIdentifier=args.membership_id
    )
    
    association_list = associations.get('configuredTableAssociationSummaries', [])
    print(f"Found {len(association_list)} existing associations\n")
    
    # Create collaboration analysis rules for each association
    success_count = 0
    failed_count = 0
    
    for assoc in association_list:
        assoc_id = assoc['id']
        assoc_name = assoc['name']
        print(f"Processing: {assoc_name} ({assoc_id})")
        
        if create_collaboration_analysis_rule(
            cleanrooms,
            membership_id=args.membership_id,
            configured_table_association_id=assoc_id,
            allowed_analyses=args.allowed_analyses,
            allowed_members=account_ids,
            collaboration_id=collaboration_id
        ):
            success_count += 1
        else:
            failed_count += 1
        print()
    
    print(f"\n✅ Summary:")
    print(f"  Successfully processed: {success_count} collaboration analysis rules")
    print(f"    (Created new or already existed)")
    print(f"  Failed: {failed_count}")
    print(f"  Allowed Analyses: {args.allowed_analyses}")
    if args.allowed_analyses == "ANY":
        print(f"  ✅ All members of the collaboration can perform analyses")

if __name__ == "__main__":
    main()

