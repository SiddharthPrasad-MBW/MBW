#!/usr/bin/env python3
"""
Fix Cleanrooms configured table columns when Glue table has extra columns.

This script helps identify and fix issues where:
- Glue table has more columns than expected
- Cleanrooms configured table needs to be updated to exclude certain columns
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


def get_glue_table_columns(glue_client, database: str, table: str) -> List[str]:
    """Get all column names from a Glue table."""
    try:
        response = glue_client.get_table(DatabaseName=database, Name=table)
        columns = response['Table']['StorageDescriptor']['Columns']
        return [col['Name'] for col in columns]
    except ClientError as e:
        print(f"❌ Error getting columns for {database}.{table}: {e}")
        raise


def get_configured_table(cleanrooms_client, name: str) -> Optional[Dict]:
    """Get a configured table by name."""
    try:
        paginator = cleanrooms_client.get_paginator('list_configured_tables')
        for page in paginator.paginate():
            for ct in page.get('configuredTableSummaries', []):
                if ct['name'] == name:
                    # Get full details
                    return cleanrooms_client.get_configured_table(
                        configuredTableIdentifier=ct['id']
                    )['configuredTable']
        return None
    except Exception as e:
        print(f"⚠️  Error getting configured table {name}: {e}")
        return None


def get_configured_table_columns(cleanrooms_client, configured_table_id: str) -> List[str]:
    """Get allowed columns from a configured table."""
    try:
        response = cleanrooms_client.get_configured_table(
            configuredTableIdentifier=configured_table_id
        )
        return response['configuredTable'].get('allowedColumns', [])
    except ClientError as e:
        print(f"❌ Error getting configured table columns: {e}")
        raise


def update_configured_table_columns(
    cleanrooms_client,
    configured_table_id: str,
    new_allowed_columns: List[str]
) -> bool:
    """Update allowed columns in a configured table.
    
    Note: AWS Cleanrooms may not support updating allowedColumns directly.
    This function will attempt the update and provide guidance if it fails.
    """
    try:
        # Try to update the configured table
        cleanrooms_client.update_configured_table(
            configuredTableIdentifier=configured_table_id,
            allowedColumns=new_allowed_columns
        )
        print(f"✅ Updated configured table columns")
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ValidationException':
            print(f"⚠️  Cleanrooms does not support updating allowedColumns directly")
            print(f"   You will need to:")
            print(f"   1. Delete the configured table association (if exists)")
            print(f"   2. Delete the configured table")
            print(f"   3. Recreate the configured table with correct columns")
            return False
        else:
            print(f"❌ Error updating configured table: {e}")
            raise


def analyze_table_columns(
    glue_client,
    cleanrooms_client,
    database: str,
    table_name: str,
    expected_column_count: Optional[int] = None,
    exclude_columns: List[str] = None
) -> Dict:
    """Analyze columns in Glue table vs configured table."""
    exclude_columns = exclude_columns or []
    
    print(f"\n📋 Analyzing: {database}.{table_name}")
    print("=" * 80)
    
    # Get Glue table columns
    glue_columns = get_glue_table_columns(glue_client, database, table_name)
    print(f"Glue table columns: {len(glue_columns)}")
    
    # Get configured table
    configured_table = get_configured_table(cleanrooms_client, table_name)
    if not configured_table:
        print(f"⚠️  Configured table '{table_name}' not found")
        return {
            'glue_columns': glue_columns,
            'configured_columns': [],
            'extra_columns': glue_columns,
            'missing_columns': [],
            'needs_fix': True
        }
    
    configured_table_id = configured_table['id']
    configured_columns = configured_table.get('allowedColumns', [])
    
    print(f"Configured table columns: {len(configured_columns)}")
    print(f"Configured table ID: {configured_table_id}")
    
    # Compare columns
    glue_set = set(glue_columns)
    configured_set = set(configured_columns)
    
    # Columns in Glue but not in configured (should be excluded)
    extra_in_glue = glue_set - configured_set
    
    # Columns in configured but not in Glue (shouldn't happen)
    missing_in_glue = configured_set - glue_set
    
    # Expected columns (all Glue columns except excluded ones)
    expected_columns = [col for col in glue_columns if col not in exclude_columns]
    expected_set = set(expected_columns)
    
    # Columns that should be removed from configured table
    should_remove = configured_set - expected_set
    
    # Columns that should be added to configured table
    should_add = expected_set - configured_set
    
    needs_fix = len(should_remove) > 0 or len(should_add) > 0
    
    print(f"\nColumn Analysis:")
    print(f"  Expected columns (excluding {exclude_columns}): {len(expected_columns)}")
    if expected_column_count:
        print(f"  Expected count: {expected_column_count}")
        if len(expected_columns) != expected_column_count:
            print(f"  ⚠️  Column count mismatch! Expected {expected_column_count}, got {len(expected_columns)}")
    
    if extra_in_glue:
        print(f"\n  ⚠️  Columns in Glue but not in configured table:")
        for col in sorted(extra_in_glue):
            print(f"    - {col}")
    
    if missing_in_glue:
        print(f"\n  ⚠️  Columns in configured table but not in Glue:")
        for col in sorted(missing_in_glue):
            print(f"    - {col}")
    
    if should_remove:
        print(f"\n  ❌ Columns that should be REMOVED from configured table:")
        for col in sorted(should_remove):
            print(f"    - {col}")
    
    if should_add:
        print(f"\n  ✅ Columns that should be ADDED to configured table:")
        for col in sorted(should_add):
            print(f"    - {col}")
    
    if not needs_fix:
        print(f"\n  ✅ Configured table columns are correct!")
    
    return {
        'glue_columns': glue_columns,
        'configured_columns': configured_columns,
        'expected_columns': expected_columns,
        'extra_in_glue': list(extra_in_glue),
        'missing_in_glue': list(missing_in_glue),
        'should_remove': list(should_remove),
        'should_add': list(should_add),
        'configured_table_id': configured_table_id,
        'needs_fix': needs_fix
    }


def main():
    parser = argparse.ArgumentParser(
        description='Fix Cleanrooms configured table columns'
    )
    parser.add_argument('--table', required=True, help='Table name (e.g., part_miacs_02_a)')
    parser.add_argument('--database', default='omc_flywheel_prod', help='Glue database name')
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--expected-count', type=int, help='Expected column count')
    parser.add_argument('--exclude-columns', nargs='+', default=['id_bucket'],
                       help='Columns to exclude from configured table')
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
    print("Fix Cleanrooms Configured Table Columns")
    print("=" * 80)
    
    # Analyze the table
    analysis = analyze_table_columns(
        glue,
        cleanrooms,
        args.database,
        args.table,
        args.expected_count,
        args.exclude_columns
    )
    
    if not analysis['needs_fix']:
        print("\n✅ No fixes needed!")
        return
    
    print("\n" + "=" * 80)
    print("RECOMMENDED FIX")
    print("=" * 80)
    
    if analysis['should_remove']:
        print(f"\nTo fix this issue, you need to:")
        print(f"1. Update the configured table to exclude: {', '.join(analysis['should_remove'])}")
        print(f"2. The corrected allowedColumns should be: {len(analysis['expected_columns'])} columns")
        print(f"\nCorrected columns list:")
        for i, col in enumerate(analysis['expected_columns'], 1):
            print(f"  {i:3d}. {col}")
        
        if not args.dry_run:
            print(f"\n⚠️  Note: AWS Cleanrooms may not support updating allowedColumns directly.")
            print(f"   You may need to:")
            print(f"   1. Delete the configured table association (if it exists)")
            print(f"   2. Delete the configured table")
            print(f"   3. Recreate it with the correct columns using:")
            print(f"      python3 scripts/create-cleanrooms-configured-tables.py \\")
            print(f"        --tables {args.table} \\")
            print(f"        --profile {args.profile or 'default'}")
            
            response = input("\nDo you want to attempt to update the configured table? (yes/no): ")
            if response.lower() == 'yes':
                success = update_configured_table_columns(
                    cleanrooms,
                    analysis['configured_table_id'],
                    analysis['expected_columns']
                )
                if success:
                    print("\n✅ Configured table updated successfully!")
                else:
                    print("\n⚠️  Update failed. Follow the manual steps above.")
        else:
            print(f"\n[DRY RUN] Would update configured table with {len(analysis['expected_columns'])} columns")
    else:
        print("\n✅ Configured table columns are correct!")


if __name__ == "__main__":
    main()

