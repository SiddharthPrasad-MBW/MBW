#!/usr/bin/env python3
"""
Update allowed analysis providers for configured tables associated with a specific collaboration.

This script:
1. Finds a collaboration by name or ID
2. Gets the membership ID for that collaboration
3. Lists all configured table associations
4. Updates each configured table's analysis rule to add a new provider
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


def find_collaboration(cleanrooms_client, search_term: str) -> Optional[Dict]:
    """Find a collaboration by name or ID."""
    try:
        # Only try direct get if it looks like a full UUID (36 chars)
        if len(search_term) == 36:
            try:
                response = cleanrooms_client.get_collaboration(collaborationIdentifier=search_term)
                return response.get('collaboration', {})
            except ClientError:
                pass
        
        # Search by listing all collaborations
        paginator = cleanrooms_client.get_paginator('list_collaborations')
        for page in paginator.paginate():
            for collab in page.get('collaborationList', []):
                collab_id = collab.get('id') or collab.get('collaborationId', '')
                collab_name = collab.get('name', '')
                
                # Match by ID or name (case-insensitive, partial match)
                if (search_term.lower() in collab_id.lower() or 
                    search_term.lower() in collab_name.lower()):
                    return collab
        
        return None
    except Exception as e:
        print(f"❌ Error finding collaboration: {e}")
        return None


def get_membership_for_collaboration(cleanrooms_client, collaboration_id: str) -> Optional[str]:
    """Get the membership ID for a collaboration."""
    try:
        paginator = cleanrooms_client.get_paginator('list_memberships')
        for page in paginator.paginate():
            for membership in page.get('membershipSummaries', []):
                if membership.get('collaborationId') == collaboration_id:
                    return membership.get('id')
        return None
    except Exception as e:
        print(f"❌ Error getting membership: {e}")
        return None


def get_configured_table_associations(cleanrooms_client, membership_id: str) -> List[Dict]:
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


def update_table_provider(
    cleanrooms_client,
    configured_table_id: str,
    table_name: str,
    new_provider: str,
    dry_run: bool = False
) -> Dict:
    """Update a configured table to add a new provider."""
    result = {
        'name': table_name,
        'id': configured_table_id,
        'current_providers': [],
        'updated_providers': [],
        'needs_update': False,
        'needs_create': False,
        'updated': False,
        'status': 'unknown'
    }
    
    # Get current analysis rule
    current_rule = get_configured_table_analysis_rule(cleanrooms_client, configured_table_id)
    
    if current_rule:
        current_providers = extract_analysis_providers(current_rule)
        result['current_providers'] = current_providers
        
        # Check if new provider is already present
        if new_provider in current_providers:
            result['status'] = 'already_has_provider'
            result['updated_providers'] = current_providers
            return result
        
        # Add new provider to existing list
        updated_providers = list(set(current_providers + [new_provider]))
        result['updated_providers'] = updated_providers
        result['needs_update'] = True
        result['status'] = 'needs_update'
        
        if not dry_run:
            if update_analysis_rule(cleanrooms_client, configured_table_id, updated_providers):
                result['updated'] = True
                result['status'] = 'updated'
            else:
                result['status'] = 'update_failed'
    else:
        # No rule exists, create one with just the new provider
        result['needs_create'] = True
        result['status'] = 'needs_create'
        result['updated_providers'] = [new_provider]
        
        if not dry_run:
            if create_analysis_rule(cleanrooms_client, configured_table_id, [new_provider]):
                result['updated'] = True
                result['status'] = 'created'
            else:
                result['status'] = 'create_failed'
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description='Update allowed analysis providers for configured tables in a collaboration'
    )
    parser.add_argument('--collaboration', required=True,
                       help='Collaboration name or ID (e.g., "AMC amcmyuvske7" or full ID)')
    parser.add_argument('--provider', required=True,
                       help='AWS account ID to add as allowed query provider (e.g., "803109464991")')
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
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
    print("Update Collaboration Table Analysis Providers")
    print("=" * 80)
    print()
    print(f"Collaboration: {args.collaboration}")
    print(f"New Provider: {args.provider}")
    print()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    print()
    print("=" * 80)
    print()
    
    # Find collaboration
    print(f"📋 Finding collaboration '{args.collaboration}'...")
    collaboration = find_collaboration(cleanrooms, args.collaboration)
    
    if not collaboration:
        print(f"❌ Collaboration '{args.collaboration}' not found")
        sys.exit(1)
    
    collaboration_id = collaboration.get('id') or collaboration.get('collaborationId', '')
    collaboration_name = collaboration.get('name', 'N/A')
    print(f"✅ Found collaboration: {collaboration_name} (ID: {collaboration_id})")
    print()
    
    # Get membership ID
    print(f"📋 Getting membership ID for collaboration...")
    membership_id = get_membership_for_collaboration(cleanrooms, collaboration_id)
    
    if not membership_id:
        print(f"❌ No membership found for collaboration {collaboration_id}")
        sys.exit(1)
    
    print(f"✅ Found membership ID: {membership_id}")
    print()
    
    # Get configured table associations
    print(f"📋 Getting configured table associations...")
    associations = get_configured_table_associations(cleanrooms, membership_id)
    print(f"✅ Found {len(associations)} configured table associations")
    print()
    
    if not associations:
        print("⚠️  No configured table associations found. Nothing to update.")
        sys.exit(0)
    
    # Process each association
    print("=" * 80)
    print("PROCESSING TABLES")
    print("=" * 80)
    print()
    
    results = []
    for assoc in associations:
        assoc_name = assoc.get('name', 'N/A')
        configured_table_id = assoc.get('configuredTableId') or assoc.get('configuredTableIdentifier', '')
        
        if not configured_table_id:
            print(f"⚠️  Skipping {assoc_name}: No configured table ID found")
            continue
        
        print(f"Processing: {assoc_name}")
        result = update_table_provider(
            cleanrooms,
            configured_table_id,
            assoc_name,
            args.provider,
            dry_run=args.dry_run
        )
        results.append(result)
        
        # Print result
        if result['status'] == 'already_has_provider':
            print(f"   ✅ Already has provider {args.provider}")
        elif result['status'] == 'needs_update':
            current_str = ', '.join(result['current_providers'])
            updated_str = ', '.join(result['updated_providers'])
            if args.dry_run:
                print(f"   🔍 Would update: [{current_str}] → [{updated_str}]")
            else:
                print(f"   ✅ Updated: [{current_str}] → [{updated_str}]")
        elif result['status'] == 'needs_create':
            if args.dry_run:
                print(f"   🔍 Would create rule with provider: [{args.provider}]")
            else:
                print(f"   ✅ Created rule with provider: [{args.provider}]")
        elif result['status'] in ['updated', 'created']:
            print(f"   ✅ Successfully updated")
        else:
            print(f"   ❌ Status: {result['status']}")
        print()
    
    # Print summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    already_has = [r for r in results if r['status'] == 'already_has_provider']
    updated = [r for r in results if r['status'] in ['updated', 'created']]
    needs_update = [r for r in results if r['status'] == 'needs_update']
    needs_create = [r for r in results if r['status'] == 'needs_create']
    failed = [r for r in results if r['status'] in ['update_failed', 'create_failed']]
    
    print(f"Total tables: {len(results)}")
    print(f"✅ Already has provider: {len(already_has)}")
    if args.dry_run:
        print(f"🔍 Would update: {len(needs_update)}")
        print(f"🔍 Would create: {len(needs_create)}")
    else:
        print(f"✅ Updated: {len(updated)}")
        print(f"❌ Failed: {len(failed)}")
    print()
    
    if failed:
        print("Failed tables:")
        for r in failed:
            print(f"  - {r['name']}")
        print()
    
    if args.dry_run and (needs_update or needs_create):
        print("💡 Run without --dry-run to apply updates")
    elif not args.dry_run and updated:
        print("✅ Updates applied successfully!")


if __name__ == "__main__":
    main()

