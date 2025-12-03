#!/usr/bin/env python3
"""
Generate Entity Resolution schema mapping JSON files for all part_*_er tables.

This script reads Glue table schemas and generates schema mapping JSON files
that can be used with AWS Entity Resolution Service.
"""

import boto3
import json
import argparse
import os
import sys
from typing import List, Dict, Optional
from botocore.exceptions import ClientError

# Default configuration
DEFAULT_REGION = "us-east-1"
DEFAULT_DATABASE = "omc_flywheel_prod"
DEFAULT_ID_NAMESPACE_ARN = "arn:aws:entityresolution:us-east-1:239083076653:idnamespace/ACXIdNamespace"
DEFAULT_MATCHING_KEY = "AXM"
DEFAULT_EXCLUDE_COLUMNS = ["id_bucket"]  # Columns to exclude from ER
ROW_ID_COLUMN = "row_id"
ID_COLUMN = "customer_user_id"

# All part_ tables (excluding part_addressable_ids - not added to configured tables)
PART_TABLES = [
    "part_ibe_01", "part_ibe_01_a",
    "part_ibe_02", "part_ibe_02_a",
    "part_ibe_03", "part_ibe_03_a",
    "part_ibe_04", "part_ibe_04_a", "part_ibe_04_b",
    "part_ibe_05", "part_ibe_05_a",
    "part_ibe_06", "part_ibe_06_a",
    "part_ibe_08", "part_ibe_09",
    "part_miacs_01", "part_miacs_01_a",
    "part_miacs_02", "part_miacs_02_a", "part_miacs_02_b",
    "part_miacs_03", "part_miacs_03_a", "part_miacs_03_b",
    "part_miacs_04",
    "part_n_a", "part_n_a_a",
    "part_new_borrowers"
]


def get_table_schema(glue_client, database: str, table: str) -> Optional[Dict]:
    """Get the schema for a Glue table."""
    try:
        resp = glue_client.get_table(DatabaseName=database, Name=table)
        return resp["Table"]
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityNotFoundException':
            return None
        raise


def generate_schema_mapping(
    table_name: str,
    table_schema: Dict,
    id_namespace_arn: str,
    matching_key: str,
    id_column: str,
    exclude_columns: List[str],
    output_dir: str
) -> Optional[str]:
    """Generate schema mapping JSON for a table."""
    # Get all columns
    cols = [c["Name"] for c in table_schema["StorageDescriptor"]["Columns"]]
    
    # Plus partition keys, if any
    part_cols = [p["Name"] for p in table_schema.get("PartitionKeys", [])]
    
    all_cols = cols + part_cols
    
    # Filter out excluded columns
    filtered_cols = [col for col in all_cols if col not in exclude_columns]
    
    if not filtered_cols:
        print(f"⚠️  No columns remaining after exclusions for {table_name}")
        return None
    
    # Build mapped input fields
    mapped_input_fields = []
    
    for col in filtered_cols:
        # ID field
        if col == id_column:
            mapped_input_fields.append({
                "fieldName": col,
                "type": "ID",
                "matchingKey": matching_key,
                "idNamespaceArn": id_namespace_arn
            })
        else:
            # Everything else is an attribute (including row_id, ibeXXXX, etc.)
            mapped_input_fields.append({
                "fieldName": col,
                "type": "ATTRIBUTE"
            })
    
    # Generate schema name (remove 'part_' prefix and '_er' suffix, convert to uppercase)
    table_suffix = table_name.upper().replace('PART_', '').replace('_ER', '')
    schema_name = f"ACX_SCHEMA_{table_suffix}"
    
    schema_mapping = {
        "schemaName": schema_name,
        "description": f"ER schema for {table_name} with {matching_key} identity and attributes",
        "mappedInputFields": mapped_input_fields
    }
    
    # Write to file
    output_file = os.path.join(output_dir, f"{table_name}_schema_mapping.json")
    with open(output_file, "w") as f:
        json.dump(schema_mapping, f, indent=2)
    
    return output_file


def main():
    parser = argparse.ArgumentParser(
        description='Generate Entity Resolution schema mapping JSON files for all part_*_er tables'
    )
    parser.add_argument('--region', default=DEFAULT_REGION, help='AWS region')
    parser.add_argument('--database', default=DEFAULT_DATABASE, help='Glue database name')
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--id-namespace-arn', default=DEFAULT_ID_NAMESPACE_ARN,
                       help='Entity Resolution ID namespace ARN')
    parser.add_argument('--matching-key', default=DEFAULT_MATCHING_KEY,
                       help='Matching key for ID field (default: AXM)')
    parser.add_argument('--id-column', default=ID_COLUMN,
                       help='Column name to use as ID (default: customer_user_id)')
    parser.add_argument('--exclude-columns', nargs='+', default=DEFAULT_EXCLUDE_COLUMNS,
                       help='Columns to exclude from schema mapping')
    parser.add_argument('--tables', nargs='+', default=PART_TABLES,
                       help='List of table names (without _er suffix) to process')
    parser.add_argument('--output-dir', default='./schema_mappings',
                       help='Output directory for JSON files (default: ./schema_mappings)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be generated without creating files')
    parser.add_argument('--no-verify-ssl', action='store_true',
                       help='Disable SSL certificate verification')
    
    args = parser.parse_args()
    
    # Create output directory
    if not args.dry_run:
        os.makedirs(args.output_dir, exist_ok=True)
    
    # Create AWS client
    session = boto3.Session(profile_name=args.profile) if args.profile else boto3.Session()
    glue = session.client("glue", region_name=args.region, verify=not args.no_verify_ssl)
    
    print("=" * 80)
    print("Generate Entity Resolution Schema Mappings")
    print("=" * 80)
    print()
    print(f"Region: {args.region}")
    print(f"Database: {args.database}")
    print(f"ID Namespace ARN: {args.id_namespace_arn}")
    print(f"Matching Key: {args.matching_key}")
    print(f"ID Column: {args.id_column}")
    print(f"Exclude Columns: {args.exclude_columns}")
    print(f"Output Directory: {args.output_dir}")
    print(f"Tables to process: {len(args.tables)}")
    print()
    print("=" * 80)
    print()
    
    # Process each table
    er_table_suffix = "_er"
    success_count = 0
    skipped_count = 0
    failed_count = 0
    
    for table_name in args.tables:
        er_table_name = f"{table_name}{er_table_suffix}"
        
        print(f"📋 Processing: {er_table_name}")
        
        # Get table schema
        table_schema = get_table_schema(glue, args.database, er_table_name)
        
        if not table_schema:
            print(f"   ⚠️  Table {args.database}.{er_table_name} does not exist, skipping")
            skipped_count += 1
            print()
            continue
        
        # Generate schema mapping
        try:
            if args.dry_run:
                # Just show what would be generated
                cols = [c["Name"] for c in table_schema["StorageDescriptor"]["Columns"]]
                part_cols = [p["Name"] for p in table_schema.get("PartitionKeys", [])]
                all_cols = cols + part_cols
                filtered_cols = [col for col in all_cols if col not in args.exclude_columns]
                
                table_suffix = er_table_name.upper().replace('PART_', '').replace('_ER', '')
                schema_name = f"ACX_SCHEMA_{table_suffix}"
                
                print(f"   Would generate: {schema_name}")
                print(f"   Columns: {len(filtered_cols)} (ID: {args.id_column}, Attributes: {len(filtered_cols) - 1})")
                print(f"   Output: {os.path.join(args.output_dir, f'{er_table_name}_schema_mapping.json')}")
            else:
                output_file = generate_schema_mapping(
                    er_table_name,
                    table_schema,
                    args.id_namespace_arn,
                    args.matching_key,
                    args.id_column,
                    args.exclude_columns,
                    args.output_dir
                )
                
                if output_file:
                    print(f"   ✅ Generated: {output_file}")
                    success_count += 1
                else:
                    print(f"   ⚠️  Failed to generate schema mapping")
                    failed_count += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
            failed_count += 1
        
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total tables: {len(args.tables)}")
    print(f"✅ Success: {success_count}")
    print(f"⚠️  Skipped (table not found): {skipped_count}")
    print(f"❌ Failed: {failed_count}")
    print()
    
    if not args.dry_run and success_count > 0:
        print(f"Schema mapping JSON files written to: {args.output_dir}")
        print()
        print("To create schema mappings in AWS Entity Resolution, use:")
        print("  aws entityresolution create-schema-mapping \\")
        print("    --schema-name <schema_name> \\")
        print("    --mapped-input-fields file://<json_file>")


if __name__ == "__main__":
    main()

