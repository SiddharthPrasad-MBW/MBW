#!/usr/bin/env python3
"""
Create _er tables for all part_* tables for Entity Resolution Service.

This script creates Entity Resolution tables (part_*_er) from all part_* tables
by selecting customer_user_id as both row_id and customer_user_id.
"""

import os
import sys
import time
import argparse
import boto3
from botocore.exceptions import ClientError
from typing import List, Dict, Optional

# Default configuration
DEFAULT_REGION = "us-east-1"
DEFAULT_DATABASE = "omc_flywheel_prod"
DEFAULT_BUCKET = "omc-flywheel-data-us-east-1-prod"
DEFAULT_ER_BASE_PATH = "s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/identity/acx_ids_cur/"

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


def run_athena(athena_client, sql: str, desc: str, workgroup: str, results_s3: str):
    """Execute an Athena query and wait for completion."""
    print(f"📝 Executing: {desc}")
    print(f"   SQL: {sql[:150]}..." if len(sql) > 150 else f"   SQL: {sql}")
    
    try:
        resp = athena_client.start_query_execution(
            QueryString=sql,
            WorkGroup=workgroup,
            ResultConfiguration={"OutputLocation": results_s3},
        )
        qid = resp["QueryExecutionId"]
        print(f"   Query ID: {qid}")
        
        # Wait for query to complete
        while True:
            st = athena_client.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]
            state = st["State"]
            if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
                break
            print(f"   Status: {state}...")
            time.sleep(2)
        
        if state != "SUCCEEDED":
            reason = st.get("StateChangeReason", "")
            error = st.get("AthenaError", {})
            error_msg = error.get("ErrorMessage", "") if error else ""
            raise RuntimeError(f"{desc} failed: {reason} {error_msg}")
        
        print(f"✅ {desc} completed successfully")
        return qid
    except ClientError as e:
        print(f"❌ Error executing query: {e}")
        raise


def check_table_exists(glue_client, database: str, table: str) -> bool:
    """Check if a Glue table exists."""
    try:
        glue_client.get_table(DatabaseName=database, Name=table)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityNotFoundException':
            return False
        raise


def get_table_columns(glue_client, database: str, table: str) -> List[str]:
    """Get all column names from a Glue table."""
    try:
        response = glue_client.get_table(DatabaseName=database, Name=table)
        columns = response['Table']['StorageDescriptor']['Columns']
        return [col['Name'] for col in columns]
    except ClientError as e:
        print(f"❌ Error getting columns for {database}.{table}: {e}")
        raise


def create_er_table(
    athena_client,
    glue_client,
    database: str,
    source_table: str,
    target_table: str,
    s3_location: str,
    workgroup: str,
    results_s3: str,
    force: bool = False
) -> Optional[bool]:
    """Create an _er table from a source part_* table.
    
    Returns:
        True: Successfully created
        False: Failed to create
        None: Skipped (source table doesn't exist or target already exists without force)
    """
    print(f"\n📋 Processing: {source_table} → {target_table}")
    
    # Check if source table exists
    if not check_table_exists(glue_client, database, source_table):
        print(f"   ⚠️  Source table {database}.{source_table} does not exist, skipping")
        return None
    
    # Check if target table already exists
    if check_table_exists(glue_client, database, target_table):
        if force:
            print(f"   ⚠️  Target table {database}.{target_table} already exists, dropping...")
            drop_sql = f"DROP TABLE IF EXISTS {database}.{target_table};"
            try:
                run_athena(athena_client, drop_sql, f"DROP {target_table}", workgroup, results_s3)
            except Exception as e:
                print(f"   ⚠️  Error dropping table: {e}, continuing...")
        else:
            print(f"   ✅ Target table {database}.{target_table} already exists, skipping")
            return None  # Skipped, not a failure
    
    # Get columns from source table to build SELECT statement
    # We need to select all columns, but map customer_user_id to both row_id and customer_user_id
    columns = get_table_columns(glue_client, database, source_table)
    
    if "customer_user_id" not in columns:
        print(f"   ⚠️  Source table {source_table} does not have customer_user_id column, skipping")
        return None  # Skipped, not a failure
    
    # Build SELECT statement
    # First select customer_user_id as row_id, then customer_user_id, then all other columns
    select_parts = []
    
    # Add row_id (from customer_user_id)
    select_parts.append("customer_user_id as row_id")
    
    # Add customer_user_id
    select_parts.append("customer_user_id")
    
    # Add all other columns (excluding customer_user_id to avoid duplicate)
    for col in columns:
        if col != "customer_user_id":
            select_parts.append(col)
    
    select_clause = ",\n  ".join(select_parts)
    
    # Build CREATE TABLE AS SELECT statement
    create_sql = f"""CREATE TABLE {database}.{target_table}
WITH (
  external_location = '{s3_location}',
  format = 'PARQUET',
  write_compression = 'SNAPPY'
) AS
SELECT
  {select_clause}
FROM {database}.{source_table};"""
    
    try:
        run_athena(athena_client, create_sql, f"CREATE {target_table}", workgroup, results_s3)
        
        # Verify table was created
        if check_table_exists(glue_client, database, target_table):
            print(f"   ✅ Table {database}.{target_table} created successfully!")
            return True
        else:
            print(f"   ⚠️  Table {database}.{target_table} was not found after creation")
            return False
    except Exception as e:
        print(f"   ❌ Error creating table: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Create _er tables for all part_* tables for Entity Resolution'
    )
    parser.add_argument('--profile', default=os.getenv("AWS_PROFILE"), help='AWS profile name')
    parser.add_argument('--region', default=os.getenv("AWS_REGION", DEFAULT_REGION), help='AWS region')
    parser.add_argument('--database', default=os.getenv("DATABASE", DEFAULT_DATABASE), help='Glue database name')
    parser.add_argument('--workgroup', default=os.getenv("ATHENA_WORKGROUP", "primary"), help='Athena workgroup')
    parser.add_argument('--er-base-path', default=os.getenv("ER_BASE_PATH", DEFAULT_ER_BASE_PATH),
                       help='S3 base path for ER tables')
    parser.add_argument('--results-s3', default=os.getenv("ATHENA_RESULTS_S3"), 
                       help='S3 path for Athena query results')
    parser.add_argument('--tables', nargs='+', default=PART_TABLES,
                       help='List of table names (without _er suffix) to process')
    parser.add_argument('--force', action='store_true',
                       help='Drop and recreate tables if they exist')
    parser.add_argument('--no-verify-ssl', action='store_true',
                       help='Disable SSL certificate verification')
    
    args = parser.parse_args()
    
    # Set default results S3 if not provided
    if not args.results_s3:
        # Try to get from environment or use default
        args.results_s3 = os.getenv("ATHENA_RESULTS_S3", 
                                   f"s3://omc-flywheel-prod-analysis-data/query-results/")
    
    print("=" * 80)
    print("Create _er Tables for All part_* Tables")
    print("=" * 80)
    print()
    print(f"Region: {args.region}")
    print(f"Database: {args.database}")
    print(f"ER Base Path: {args.er_base_path}")
    print(f"Athena Workgroup: {args.workgroup}")
    print(f"Results S3: {args.results_s3}")
    print(f"Tables to process: {len(args.tables)}")
    print(f"Force recreate: {args.force}")
    print()
    print("=" * 80)
    print()
    
    # Create AWS clients
    # In Glue, profile will be empty string, so use default session (IAM role)
    if args.profile and args.profile.strip():
        session = boto3.Session(profile_name=args.profile)
    else:
        session = boto3.Session()  # Uses IAM role in Glue
    athena = session.client("athena", region_name=args.region, verify=not args.no_verify_ssl)
    glue = session.client("glue", region_name=args.region, verify=not args.no_verify_ssl)
    
    # Process each table
    success_count = 0
    skipped_count = 0
    failed_count = 0
    
    for table_name in args.tables:
        er_table_name = f"{table_name}_er"
        
        # Determine S3 location for this table
        # Use table name as subdirectory
        s3_location = f"{args.er_base_path.rstrip('/')}/{table_name}/"
        
        success = create_er_table(
            athena,
            glue,
            args.database,
            table_name,
            er_table_name,
            s3_location,
            args.workgroup,
            args.results_s3,
            args.force
        )
        
        if success is True:
            success_count += 1
        elif success is None:
            skipped_count += 1
        else:
            failed_count += 1
    
    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total tables: {len(args.tables)}")
    print(f"✅ Success: {success_count}")
    print(f"⚠️  Skipped: {skipped_count}")
    print(f"❌ Failed: {failed_count}")
    print()
    
    if success_count > 0:
        print(f"✅ Created {success_count} _er tables for Entity Resolution Service")
    else:
        print("⚠️  No tables were created")
        sys.exit(1)


if __name__ == "__main__":
    main()

