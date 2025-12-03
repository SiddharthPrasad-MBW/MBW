#!/usr/bin/env python3
"""
Update allowed analysis providers for all Cleanrooms configured tables.

This script ensures all configured tables have the correct allowed analysis providers:
- 921290734397 (AMC Service) - already exists
- 657425294073 (Query Submitter/AMC Results Receiver) - needs to be added

It also verifies that only these 2 accounts are allowed.
"""

import boto3
import argparse
import sys
from typing import List, Dict, Optional, Set
from botocore.exceptions import ClientError
from botocore.config import Config
import urllib3

# Disable SSL verification if needed
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Expected analysis providers
EXPECTED_PROVIDERS = ["921290734397", "657425294073"]  # AMC Service, Query Submitter/AMC Results Receiver


def get_all_configured_tables(cleanrooms_client) -> List[Dict]:
    """Get all configured tables."""
    all_tables = []
    try:
        paginator = cleanrooms_client.get_paginator('list_configured_tables')
        for page in paginator.paginate():
            all_tables.extend(page.get('configuredTableSummaries', []))
    except Exception as e:
        print(f"❌ Error listing configured tables: {e}")
        raise
    return all_tables


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


def extract_analysis_providers(policy: Dict) -> List[str]:
    """Extract allowedAnalysisProviders from a configured table analysis rule policy."""
    try:
        v1 = policy.get('v1', {})
        custom = v1.get('custom', {})
        providers = custom.get('allowedAnalysisProviders', [])
        return providers if isinstance(providers, list) else []
    except Exception:
        return []


def update_analysis_rule(
    cleanrooms_client,
    configured_table_id: str,
    allowed_providers: List[str]
) -> bool:
    """Update the CUSTOM analysis rule for a configured table."""
    try:
        # Build analysis rule policy
        analysis_rule_policy = {
            "v1": {
                "custom": {
                    "allowedAnalyses": ["ANY_QUERY"],
                    "allowedAnalysisProviders": allowed_providers
                }
            }
        }
        
        cleanrooms_client.update_configured_table_analysis_rule(
            configuredTableIdentifier=configured_table_id,
            analysisRuleType="CUSTOM",
            analysisRulePolicy=analysis_rule_policy
        )
        return True
    except ClientError as e:
        print(f"❌ Error updating analysis rule: {e}")
        return False


def create_analysis_rule(
    cleanrooms_client,
    configured_table_id: str,
    allowed_providers: List[str]
) -> bool:
    """Create a CUSTOM analysis rule for a configured table."""
    try:
        # Build analysis rule policy
        analysis_rule_policy = {
            "v1": {
                "custom": {
                    "allowedAnalyses": ["ANY_QUERY"],
                    "allowedAnalysisProviders": allowed_providers
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
        print(f"❌ Error creating analysis rule: {e}")
        return False


def check_and_update_table(
    cleanrooms_client,
    table: Dict,
    dry_run: bool = False
) -> Dict:
    """Check and update a single configured table."""
    table_id = table['id']
    table_name = table['name']
    
    result = {
        'name': table_name,
        'id': table_id,
        'current_providers': [],
        'needs_update': False,
        'needs_create': False,
        'updated': False,
        'status': 'unknown'
    }
    
    # Get current analysis rule
    current_rule = get_configured_table_analysis_rule(cleanrooms_client, table_id)
    
    if current_rule:
        current_providers = extract_analysis_providers(current_rule)
        result['current_providers'] = current_providers
        
        # Check if update is needed
        current_set = set(current_providers)
        expected_set = set(EXPECTED_PROVIDERS)
        
        if current_set != expected_set:
            result['needs_update'] = True
            result['status'] = 'needs_update'
            
            if not dry_run:
                # Update the rule
                if update_analysis_rule(cleanrooms_client, table_id, EXPECTED_PROVIDERS):
                    result['updated'] = True
                    result['status'] = 'updated'
                else:
                    result['status'] = 'update_failed'
        else:
            result['status'] = 'correct'
    else:
        result['needs_create'] = True
        result['status'] = 'needs_create'
        
        if not dry_run:
            # Create the rule
            if create_analysis_rule(cleanrooms_client, table_id, EXPECTED_PROVIDERS):
                result['updated'] = True
                result['status'] = 'created'
            else:
                result['status'] = 'create_failed'
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description='Update allowed analysis providers for all Cleanrooms configured tables'
    )
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    parser.add_argument('--verify-only', action='store_true',
                       help='Only verify, do not update')
    parser.add_argument('--table', help='Process only this specific table name')
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
    print("Update Configured Table Analysis Providers")
    print("=" * 80)
    print()
    print(f"Expected Analysis Providers:")
    print(f"  - 921290734397 (AMC Service)")
    print(f"  - 657425294073 (Query Submitter/AMC Results Receiver)")
    print()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    elif args.verify_only:
        print("🔍 VERIFY ONLY MODE - No changes will be made")
    print()
    print("=" * 80)
    print()
    
    # Get all configured tables
    print("📋 Getting all configured tables...")
    all_tables = get_all_configured_tables(cleanrooms)
    
    # Filter if specific table requested
    if args.table:
        all_tables = [t for t in all_tables if t['name'] == args.table]
        if not all_tables:
            print(f"❌ Table '{args.table}' not found")
            sys.exit(1)
    
    print(f"Found {len(all_tables)} configured tables\n")
    
    # Process each table
    results = []
    for table in all_tables:
        result = check_and_update_table(
            cleanrooms,
            table,
            dry_run=(args.dry_run or args.verify_only)
        )
        results.append(result)
    
    # Print results
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()
    
    # Group by status
    correct = [r for r in results if r['status'] == 'correct']
    needs_update = [r for r in results if r['status'] == 'needs_update']
    needs_create = [r for r in results if r['status'] == 'needs_create']
    updated = [r for r in results if r['status'] in ['updated', 'created']]
    failed = [r for r in results if r['status'] in ['update_failed', 'create_failed']]
    
    # Show correct tables
    if correct:
        print(f"✅ Correct ({len(correct)} tables):")
        for r in correct:
            providers_str = ', '.join(r['current_providers'])
            print(f"   {r['name']}: [{providers_str}]")
        print()
    
    # Show tables that need update
    if needs_update:
        print(f"⚠️  Needs Update ({len(needs_update)} tables):")
        for r in needs_update:
            current_str = ', '.join(r['current_providers'])
            expected_str = ', '.join(EXPECTED_PROVIDERS)
            print(f"   {r['name']}:")
            print(f"     Current: [{current_str}]")
            print(f"     Expected: [{expected_str}]")
        print()
    
    # Show tables that need creation
    if needs_create:
        print(f"⚠️  Missing Analysis Rule ({len(needs_create)} tables):")
        for r in needs_create:
            print(f"   {r['name']}")
        print()
    
    # Show updated tables
    if updated:
        print(f"✅ Updated ({len(updated)} tables):")
        for r in updated:
            print(f"   {r['name']}")
        print()
    
    # Show failed updates
    if failed:
        print(f"❌ Failed ({len(failed)} tables):")
        for r in failed:
            print(f"   {r['name']}")
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total tables: {len(results)}")
    print(f"✅ Correct: {len(correct)}")
    print(f"⚠️  Needs update: {len(needs_update)}")
    print(f"⚠️  Missing rule: {len(needs_create)}")
    if not args.dry_run and not args.verify_only:
        print(f"✅ Updated: {len(updated)}")
        print(f"❌ Failed: {len(failed)}")
    print()
    
    # Verify part_miacs_01_a specifically
    print("=" * 80)
    print("VERIFICATION: part_miacs_01_a")
    print("=" * 80)
    part_miacs_01_a = [r for r in results if r['name'] == 'part_miacs_01_a']
    if part_miacs_01_a:
        r = part_miacs_01_a[0]
        providers_set = set(r['current_providers'])
        expected_set = set(EXPECTED_PROVIDERS)
        if providers_set == expected_set:
            print(f"✅ part_miacs_01_a has correct providers: {r['current_providers']}")
        else:
            print(f"❌ part_miacs_01_a has incorrect providers:")
            print(f"   Current: {r['current_providers']}")
            print(f"   Expected: {EXPECTED_PROVIDERS}")
    else:
        print("⚠️  part_miacs_01_a not found in results")
    print()
    
    # Check for any extra providers
    print("=" * 80)
    print("EXTRA PROVIDERS CHECK")
    print("=" * 80)
    all_providers = set()
    for r in results:
        all_providers.update(r['current_providers'])
    
    extra_providers = all_providers - set(EXPECTED_PROVIDERS)
    if extra_providers:
        print(f"⚠️  Found extra providers: {sorted(extra_providers)}")
        print(f"   Tables with extra providers:")
        for r in results:
            current_set = set(r['current_providers'])
            if current_set & extra_providers:
                print(f"     {r['name']}: {r['current_providers']}")
    else:
        print(f"✅ No extra providers found. Only expected providers are used.")
    print()
    
    if needs_update or needs_create:
        if args.dry_run or args.verify_only:
            print("💡 Run without --dry-run or --verify-only to apply updates")
        else:
            print("✅ Updates applied. Please verify the results above.")
    elif len(correct) == len(results):
        print("✅ All tables have the correct analysis providers!")


if __name__ == "__main__":
    main()

