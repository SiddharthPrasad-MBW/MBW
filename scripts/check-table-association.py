#!/usr/bin/env python3
"""
Check a specific table association configuration in a collaboration.
"""

import boto3
import argparse
import json
from botocore.exceptions import ClientError
from botocore.config import Config
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_association(cleanrooms_client, membership_id: str, association_name: str):
    """Get association by name."""
    try:
        paginator = cleanrooms_client.get_paginator('list_configured_table_associations')
        for page in paginator.paginate(membershipIdentifier=membership_id):
            for assoc in page.get('configuredTableAssociationSummaries', []):
                if assoc.get('name') == association_name:
                    return assoc
        return None
    except Exception as e:
        print(f"❌ Error listing associations: {e}")
        return None


def get_configured_table_analysis_rule(cleanrooms_client, configured_table_id: str):
    """Get the CUSTOM analysis rule for a configured table."""
    try:
        response = cleanrooms_client.get_configured_table_analysis_rule(
            configuredTableIdentifier=configured_table_id,
            analysisRuleType="CUSTOM"
        )
        return response.get('analysisRule', {}).get('policy', {})
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return None
        raise


def get_collaboration_analysis_rule(cleanrooms_client, membership_id: str, association_id: str):
    """Get the CUSTOM collaboration analysis rule for an association."""
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


def get_association_details(cleanrooms_client, membership_id: str, association_id: str):
    """Get full association details."""
    try:
        response = cleanrooms_client.get_configured_table_association(
            membershipIdentifier=membership_id,
            configuredTableAssociationIdentifier=association_id
        )
        return response.get('configuredTableAssociation', {})
    except ClientError as e:
        print(f"❌ Error getting association details: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description='Check table association configuration')
    parser.add_argument('--membership-id', required=True, help='Membership ID')
    parser.add_argument('--association-name', required=True, help='Association name (e.g., acx_part_new_borrowers)')
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--no-verify-ssl', action='store_true', help='Disable SSL verification')
    
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
    print(f"Checking Table Association: {args.association_name}")
    print("=" * 80)
    print()
    
    # Get association
    print(f"📋 Finding association '{args.association_name}'...")
    association = get_association(cleanrooms, args.membership_id, args.association_name)
    
    if not association:
        print(f"❌ Association '{args.association_name}' not found")
        return
    
    association_id = association['id']
    configured_table_id = association.get('configuredTableId') or association.get('configuredTableIdentifier')
    
    print(f"✅ Found association:")
    print(f"   Association ID: {association_id}")
    print(f"   Configured Table ID: {configured_table_id}")
    print(f"   Status: {association.get('status', 'N/A')}")
    print()
    
    # Get full association details
    print(f"📋 Getting association details...")
    assoc_details = get_association_details(cleanrooms, args.membership_id, association_id)
    if assoc_details:
        print(f"   Table Name: {assoc_details.get('configuredTable', {}).get('name', 'N/A')}")
        print(f"   Description: {assoc_details.get('configuredTable', {}).get('description', 'N/A')}")
        print(f"   Analysis Method: {assoc_details.get('configuredTable', {}).get('analysisMethod', 'N/A')}")
    print()
    
    # Check configured table analysis rule (Query Providers)
    print("=" * 80)
    print("Configured Table Analysis Rule (Query Providers)")
    print("=" * 80)
    print()
    
    table_rule = get_configured_table_analysis_rule(cleanrooms, configured_table_id)
    if table_rule:
        v1 = table_rule.get('v1', {})
        custom = v1.get('custom', {})
        allowed_analyses = custom.get('allowedAnalyses', [])
        allowed_providers = custom.get('allowedAnalysisProviders', [])
        
        print(f"✅ Analysis rule exists")
        print(f"   Allowed Analyses: {allowed_analyses}")
        print(f"   Allowed Query Providers: {allowed_providers}")
        print()
    else:
        print(f"❌ No CUSTOM analysis rule found on configured table")
        print()
    
    # Check collaboration analysis rule (Result Receivers)
    print("=" * 80)
    print("Collaboration Analysis Rule (Result Receivers)")
    print("=" * 80)
    print()
    
    collab_rule = get_collaboration_analysis_rule(cleanrooms, args.membership_id, association_id)
    if collab_rule:
        v1 = collab_rule.get('v1', {})
        custom = v1.get('custom', {})
        allowed_receivers = custom.get('allowedResultReceivers', [])
        
        print(f"✅ Collaboration analysis rule exists")
        print(f"   Allowed Result Receivers: {allowed_receivers}")
        print()
    else:
        print(f"❌ No CUSTOM collaboration analysis rule found")
        print()
    
    # Summary
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print()
    
    ready_for_query = False
    if table_rule and collab_rule:
        providers = table_rule.get('v1', {}).get('custom', {}).get('allowedAnalysisProviders', [])
        receivers = collab_rule.get('v1', {}).get('custom', {}).get('allowedResultReceivers', [])
        
        if providers and receivers:
            ready_for_query = True
            print(f"✅ Table is ready for query")
            print(f"   - Has query providers configured: {len(providers)} provider(s)")
            print(f"   - Has result receivers configured: {len(receivers)} receiver(s)")
        else:
            print(f"⚠️  Table configuration incomplete:")
            if not providers:
                print(f"   - Missing query providers")
            if not receivers:
                print(f"   - Missing result receivers")
    else:
        print(f"❌ Table is NOT ready for query:")
        if not table_rule:
            print(f"   - Missing configured table analysis rule")
        if not collab_rule:
            print(f"   - Missing collaboration analysis rule")
    print()


if __name__ == "__main__":
    main()

