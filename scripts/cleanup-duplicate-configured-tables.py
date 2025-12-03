#!/usr/bin/env python3
"""
Clean up duplicate configured tables in AWS Cleanrooms

This script identifies and deletes duplicate configured tables, keeping only:
- The original (oldest) configured table for each name
- All instances of part_n_a, part_n_a_a, and part_new_borrowers (needed for future collaboration)
"""

import boto3
import argparse
import urllib3
import ssl
import os
from collections import defaultdict
from botocore.exceptions import ClientError
from botocore.config import Config

# The 3 tables to keep for future collaboration
KEEP_FOR_COLLABORATION = {'part_n_a', 'part_n_a_a', 'part_new_borrowers'}

def get_all_configured_tables(cleanrooms_client):
    """Get all configured tables with pagination."""
    all_tables = []
    paginator = cleanrooms_client.get_paginator('list_configured_tables')
    for page in paginator.paginate():
        all_tables.extend(page.get('configuredTableSummaries', []))
    return all_tables

def get_associated_table_ids(cleanrooms_client, membership_id):
    """Get all configured table IDs that are associated with a membership."""
    associated_ids = set()
    paginator = cleanrooms_client.get_paginator('list_configured_table_associations')
    for page in paginator.paginate(membershipIdentifier=membership_id):
        for assoc in page.get('configuredTableAssociationSummaries', []):
            associated_ids.add(assoc['configuredTableId'])
    return associated_ids

def identify_duplicates(all_tables, associated_table_ids, keep_for_collaboration):
    """Identify which tables to retain and which duplicates to delete."""
    # Group by name
    tables_by_name = defaultdict(list)
    for table in all_tables:
        is_associated = table['id'] in associated_table_ids
        tables_by_name[table['name']].append({
            'id': table['id'],
            'name': table['name'],
            'createTime': table.get('createTime', ''),
            'is_associated': is_associated
        })
    
    tables_to_retain = {}
    duplicates_to_delete = []
    
    for name, tables in tables_by_name.items():
        if len(tables) == 1:
            # No duplicates, keep it
            tables_to_retain[tables[0]['id']] = tables[0]
            continue
        
        # Sort by createTime (oldest first = original)
        tables_sorted = sorted(tables, key=lambda x: x['createTime'])
        
        # If this is one of the 3 tables we need to keep, keep all instances
        if name in keep_for_collaboration:
            for table in tables_sorted:
                tables_to_retain[table['id']] = table
            continue
        
        # For other tables, keep the oldest (original) - prefer associated if available
        keep_table = None
        for table in tables_sorted:
            if table['is_associated']:
                keep_table = table
                break
        
        if not keep_table:
            keep_table = tables_sorted[0]  # Keep oldest
        
        tables_to_retain[keep_table['id']] = keep_table
        
        # Mark others for deletion
        for dup in tables_sorted:
            if dup['id'] != keep_table['id']:
                duplicates_to_delete.append(dup)
    
    return tables_to_retain, duplicates_to_delete

def delete_configured_table(cleanrooms_client, table_id, table_name):
    """Delete a configured table."""
    try:
        cleanrooms_client.delete_configured_table(configuredTableIdentifier=table_id)
        print(f"✅ Deleted duplicate: {table_name} (ID: {table_id})")
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            print(f"⚠️  Already deleted: {table_name} (ID: {table_id})")
            return True
        else:
            print(f"❌ Error deleting {table_name} (ID: {table_id}): {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Clean up duplicate configured tables')
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--membership-id', help='Membership ID to check associations (optional)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without actually deleting')
    parser.add_argument('--no-verify-ssl', action='store_true', help='Disable SSL certificate verification')
    
    args = parser.parse_args()
    
    # Configure boto3 clients
    if args.no_verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        os.environ['PYTHONHTTPSVERIFY'] = '0'
        ssl._create_default_https_context = ssl._create_unverified_context
        config = Config(connect_timeout=60, read_timeout=60)
    else:
        config = Config()
    
    # Create AWS client
    session = boto3.Session(profile_name=args.profile) if args.profile else boto3.Session()
    cleanrooms = session.client('cleanrooms', region_name=args.region, config=config, verify=not args.no_verify_ssl)
    
    print("📋 Fetching all configured tables...")
    all_tables = get_all_configured_tables(cleanrooms)
    print(f"Found {len(all_tables)} total configured tables\n")
    
    # Get associated table IDs if membership ID provided
    associated_table_ids = set()
    if args.membership_id:
        print(f"📋 Checking associations for membership {args.membership_id}...")
        associated_table_ids = get_associated_table_ids(cleanrooms, args.membership_id)
        print(f"Found {len(associated_table_ids)} associated configured tables\n")
    
    # Identify duplicates
    print("🔍 Identifying duplicates...\n")
    tables_to_retain, duplicates_to_delete = identify_duplicates(
        all_tables, 
        associated_table_ids, 
        KEEP_FOR_COLLABORATION
    )
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total configured tables: {len(all_tables)}")
    print(f"Tables to retain: {len(tables_to_retain)}")
    print(f"Duplicates to delete: {len(duplicates_to_delete)}")
    print()
    
    # Show what will be retained
    print("=" * 80)
    print("TABLES TO BE RETAINED")
    print("=" * 80)
    retained_by_name = defaultdict(list)
    for table_id, info in tables_to_retain.items():
        retained_by_name[info['name']].append(info)
    
    for name in sorted(retained_by_name.keys()):
        tables = retained_by_name[name]
        if len(tables) > 1:
            print(f"✅ {name}: {len(tables)} instances (preserved for collaboration)")
        else:
            status = "ASSOCIATED ✅" if tables[0]['is_associated'] else "NOT ASSOCIATED"
            print(f"✅ {name}: {status}")
    
    print()
    
    # Show duplicates to delete
    if duplicates_to_delete:
        print("=" * 80)
        print("DUPLICATES TO BE DELETED")
        print("=" * 80)
        for dup in sorted(duplicates_to_delete, key=lambda x: (x['name'], x['createTime'])):
            status = "ASSOCIATED ⚠️" if dup['is_associated'] else "NOT ASSOCIATED"
            print(f"❌ {dup['name']}: {dup['id']} ({status}, created: {dup['createTime']})")
        print()
        
        if args.dry_run:
            print("🔍 DRY RUN MODE - No tables will be deleted")
            print("Run without --dry-run to actually delete duplicates")
        else:
            print("🗑️  Deleting duplicates...")
            print()
            success_count = 0
            failed_count = 0
            
            for dup in duplicates_to_delete:
                if delete_configured_table(cleanrooms, dup['id'], dup['name']):
                    success_count += 1
                else:
                    failed_count += 1
            
            print()
            print("=" * 80)
            print("DELETION SUMMARY")
            print("=" * 80)
            print(f"✅ Successfully deleted: {success_count}")
            print(f"❌ Failed: {failed_count}")
    else:
        print("✅ No duplicates found - all configured tables are unique!")

if __name__ == "__main__":
    main()

