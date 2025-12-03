#!/usr/bin/env python3
"""
Verify that all tables in the collaboration have the same configuration:
- Analysis provider: 921290734397 (AMC Service)
- Results receivers: 657425294073 (Query Submitter/AMC Results Receiver), 803109464991 (Advertiser)
"""

import boto3
import argparse
import urllib3
from botocore.exceptions import ClientError
from botocore.config import Config
from typing import Dict, List, Optional

# Expected configuration
EXPECTED_ANALYSIS_PROVIDER = "921290734397"  # AMC Service
EXPECTED_RESULT_RECEIVERS = ["657425294073", "803109464991"]  # Query Submitter/AMC Results Receiver, Advertiser


def get_configured_table_analysis_rule(cleanrooms_client, configured_table_id: str) -> Optional[Dict]:
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


def get_collaboration_analysis_rule(cleanrooms_client, membership_id: str, association_id: str) -> Optional[Dict]:
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


def extract_analysis_providers(policy: Dict) -> List[str]:
    """Extract allowedAnalysisProviders from a configured table analysis rule policy."""
    try:
        v1 = policy.get('v1', {})
        custom = v1.get('custom', {})
        providers = custom.get('allowedAnalysisProviders', [])
        return providers if isinstance(providers, list) else []
    except Exception:
        return []


def extract_result_receivers(policy: Dict) -> List[str]:
    """Extract allowedResultReceivers from a collaboration analysis rule policy."""
    try:
        v1 = policy.get('v1', {})
        custom = v1.get('custom', {})
        receivers = custom.get('allowedResultReceivers', [])
        return receivers if isinstance(receivers, list) else []
    except Exception:
        return []


def verify_table_config(cleanrooms_client, membership_id: str, association: Dict) -> Dict:
    """Verify configuration for a single table association."""
    assoc_id = association['id']
    assoc_name = association['name']
    configured_table_id = association['configuredTableId']
    
    result = {
        'name': assoc_name,
        'association_id': assoc_id,
        'configured_table_id': configured_table_id,
        'analysis_provider_match': False,
        'analysis_providers': [],
        'result_receivers_match': False,
        'result_receivers': [],
        'issues': []
    }
    
    # Check configured table analysis rule (Analysis Provider)
    table_rule = get_configured_table_analysis_rule(cleanrooms_client, configured_table_id)
    if table_rule:
        providers = extract_analysis_providers(table_rule)
        result['analysis_providers'] = providers
        if providers == [EXPECTED_ANALYSIS_PROVIDER]:
            result['analysis_provider_match'] = True
        else:
            result['issues'].append(f"Analysis provider mismatch: expected [{EXPECTED_ANALYSIS_PROVIDER}], got {providers}")
    else:
        result['issues'].append("No CUSTOM analysis rule found on configured table")
    
    # Check collaboration analysis rule (Results Receivers)
    collab_rule = get_collaboration_analysis_rule(cleanrooms_client, membership_id, assoc_id)
    if collab_rule:
        receivers = extract_result_receivers(collab_rule)
        result['result_receivers'] = receivers
        # Check if receivers match (order doesn't matter)
        if set(receivers) == set(EXPECTED_RESULT_RECEIVERS):
            result['result_receivers_match'] = True
        else:
            result['issues'].append(f"Result receivers mismatch: expected {EXPECTED_RESULT_RECEIVERS}, got {receivers}")
    else:
        result['issues'].append("No CUSTOM collaboration analysis rule found")
    
    return result


def main():
    parser = argparse.ArgumentParser(description='Verify collaboration table configurations')
    parser.add_argument('--membership-id', required=True, help='Cleanrooms membership ID')
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
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
    
    print("=" * 80)
    print("VERIFICATION: Collaboration Table Configuration")
    print("=" * 80)
    print()
    print("Expected Configuration:")
    print(f"  Analysis Provider (allowedAnalysisProviders): [{EXPECTED_ANALYSIS_PROVIDER}]")
    print(f"    → 921290734397 (AMC Service)")
    print(f"  Results Receivers (allowedResultReceivers): {EXPECTED_RESULT_RECEIVERS}")
    print(f"    → 657425294073 (Query Submitter/AMC Results Receiver)")
    print(f"    → 803109464991 (Advertiser)")
    print()
    print("=" * 80)
    print()
    
    # Get all associations (with pagination)
    print(f"📋 Getting all table associations for membership {args.membership_id}...\n")
    all_associations = []
    paginator = cleanrooms.get_paginator('list_configured_table_associations')
    for page in paginator.paginate(membershipIdentifier=args.membership_id):
        all_associations.extend(page.get('configuredTableAssociationSummaries', []))
    
    association_list = all_associations
    print(f"Found {len(association_list)} table associations\n")
    print("=" * 80)
    print()
    
    # Verify each table
    results = []
    for assoc in association_list:
        result = verify_table_config(cleanrooms, args.membership_id, assoc)
        results.append(result)
    
    # Print results
    all_match = True
    for result in results:
        status = "✅" if (result['analysis_provider_match'] and result['result_receivers_match']) else "❌"
        print(f"{status} {result['name']}")
        print(f"   Analysis Provider: {result['analysis_providers']} {'✅' if result['analysis_provider_match'] else '❌'}")
        print(f"   Result Receivers: {result['result_receivers']} {'✅' if result['result_receivers_match'] else '❌'}")
        if result['issues']:
            for issue in result['issues']:
                print(f"   ⚠️  {issue}")
            all_match = False
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    match_count = sum(1 for r in results if r['analysis_provider_match'] and r['result_receivers_match'])
    total_count = len(results)
    
    print(f"Total Tables: {total_count}")
    print(f"✅ Correctly Configured: {match_count}")
    print(f"❌ Misconfigured: {total_count - match_count}")
    print()
    
    if all_match:
        print("✅ ALL TABLES HAVE THE SAME CORRECT CONFIGURATION")
    else:
        print("❌ SOME TABLES HAVE MISMATCHED CONFIGURATIONS")
        print()
        print("Tables with issues:")
        for result in results:
            if result['issues']:
                print(f"  - {result['name']}: {', '.join(result['issues'])}")
    
    print()


if __name__ == "__main__":
    main()

