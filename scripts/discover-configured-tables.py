#!/usr/bin/env python3
"""
Discover existing Cleanrooms configured tables and output for Terraform.

This script lists all configured tables (optionally filtered by prefix)
and outputs them in a format suitable for Terraform variables.
"""

import boto3
import argparse
import json
import sys
from typing import List, Dict
from botocore.exceptions import ClientError


def discover_configured_tables(cleanrooms_client, filter_prefix: str = None) -> List[Dict]:
    """Discover all configured tables, optionally filtered by prefix."""
    tables = []
    
    try:
        print("📋 Discovering configured tables...")
        paginator = cleanrooms_client.get_paginator('list_configured_tables')
        
        for page in paginator.paginate():
            for table in page.get('configuredTableSummaries', []):
                table_name = table.get('name', '')
                # API returns 'id' not 'configuredTableId'
                table_id = table.get('id', '') or table.get('configuredTableId', '')
                
                # Filter by prefix if provided
                if filter_prefix and not table_name.startswith(filter_prefix):
                    continue
                
                tables.append({
                    'id': table_id,
                    'name': table_name,
                    'arn': table.get('configuredTableArn', ''),
                    'analysis_method': table.get('analysisMethod', '')
                })
        
        print(f"✅ Found {len(tables)} configured table(s)")
        return tables
        
    except Exception as e:
        print(f"❌ Error discovering tables: {e}")
        return []


def output_terraform_vars(tables: List[Dict], output_format: str = "hcl"):
    """Output tables in Terraform variable format."""
    if output_format == "hcl":
        print("\n# Terraform variable format:")
        print("existing_configured_tables = {")
        for table in tables:
            print(f'  "{table["id"]}" = {{')
            print(f'    name = "{table["name"]}"')
            print(f'  }}  # {table["name"]}')
        print("}")
    elif output_format == "json":
        table_map = {t['id']: {'name': t['name']} for t in tables}
        print(json.dumps({"existing_configured_tables": table_map}, indent=2))
    elif output_format == "list":
        for table in tables:
            print(f'{table["id"]}  # {table["name"]}')


def main():
    parser = argparse.ArgumentParser(
        description='Discover existing Cleanrooms configured tables for Terraform'
    )
    parser.add_argument('--filter', help='Filter tables by name prefix (e.g., "part_")')
    parser.add_argument('--output', choices=['hcl', 'json', 'list'], default='hcl',
                       help='Output format')
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    
    args = parser.parse_args()
    
    # Create Cleanrooms client
    session = boto3.Session(profile_name=args.profile) if args.profile else boto3.Session()
    cleanrooms = session.client('cleanrooms', region_name=args.region)
    
    # Discover tables
    tables = discover_configured_tables(cleanrooms, filter_prefix=args.filter)
    
    if not tables:
        print("⚠️  No tables found")
        sys.exit(1)
    
    # Output results
    output_terraform_vars(tables, args.output)


if __name__ == "__main__":
    main()

