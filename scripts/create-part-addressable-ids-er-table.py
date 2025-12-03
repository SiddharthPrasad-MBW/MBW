#!/usr/bin/env python3
"""
Create the part_addressable_ids_er table for Entity Resolution.

This script creates a table that maps customer_user_id to row_id for use with
AWS Entity Resolution Service in Cleanrooms.
"""

import os
import sys
import time
import argparse
import boto3
from botocore.exceptions import ClientError

# Configuration
ENV = os.getenv("ENV", "prod").lower()
REGION = os.getenv("AWS_REGION", "us-east-1")
WORKGROUP = os.getenv("ATHENA_WORKGROUP", "primary")
RESULTS_S3 = os.getenv("ATHENA_RESULTS_S3", f"s3://omc-flywheel-{ENV}-analysis-data/query-results/")
DATABASE = os.getenv("DATABASE", "omc_flywheel_prod")
# PROFILE: In Glue, AWS_PROFILE is empty string, so default to None to use IAM role
PROFILE = os.getenv("AWS_PROFILE", "").strip() or None

# Table configuration
SOURCE_TABLE = "part_addressable_ids"
TARGET_TABLE = "part_addressable_ids_er"


def run_athena(athena_client, sql: str, desc: str, workgroup: str = WORKGROUP, results_s3: str = RESULTS_S3):
    """Execute an Athena query and wait for completion."""
    print(f"📝 Executing: {desc}")
    print(f"   SQL: {sql[:100]}..." if len(sql) > 100 else f"   SQL: {sql}")
    
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


def main():
    parser = argparse.ArgumentParser(description='Create part_addressable_ids_er table for Entity Resolution')
    parser.add_argument('--profile', default=PROFILE, help='AWS profile name')
    parser.add_argument('--region', '--AWS_REGION', default=REGION, dest='region', help='AWS region')
    parser.add_argument('--database', '--DATABASE', default=DATABASE, dest='database', help='Glue database name')
    parser.add_argument('--workgroup', '--ATHENA_WORKGROUP', default=WORKGROUP, dest='workgroup', help='Athena workgroup')
    parser.add_argument('--ENV', default=ENV, dest='env', help='Environment (dev/prod)')
    parser.add_argument('--ATHENA_RESULTS_S3', default=RESULTS_S3, dest='athena_results_s3', help='Athena results S3 location')
    parser.add_argument('--force', action='store_true', help='Drop and recreate table if it exists')
    parser.add_argument('--no-verify-ssl', action='store_true', help='Disable SSL verification')
    
    # Ignore unknown arguments (Glue passes many automatic args like --enable-metrics, --TempDir, etc.)
    args, unknown = parser.parse_known_args()
    
    # Use args values (from Glue parameters) or fall back to environment variables
    actual_env = args.env.lower() if args.env else ENV
    actual_database = args.database if args.database else DATABASE
    actual_region = args.region if args.region else REGION
    actual_workgroup = args.workgroup if args.workgroup else WORKGROUP
    actual_results_s3 = args.athena_results_s3 if args.athena_results_s3 else RESULTS_S3
    
    # Set S3 location based on environment
    if actual_env == "dev":
        s3_location = "s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/identity/acx_ids_cur/"
    else:
        s3_location = "s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/identity/acx_ids_cur/"
    
    print("=" * 80)
    print("Create part_addressable_ids_er Table for Entity Resolution")
    print("=" * 80)
    print()
    print(f"Environment: {actual_env}")
    print(f"Region: {actual_region}")
    print(f"Database: {actual_database}")
    print(f"Source Table: {SOURCE_TABLE}")
    print(f"Target Table: {TARGET_TABLE}")
    print(f"S3 Location: {s3_location}")
    print()
    
    # Create AWS clients
    # In Glue, profile will be empty string or None, so use default session (IAM role)
    profile_to_use = args.profile.strip() if args.profile and args.profile.strip() else None
    if profile_to_use:
        session = boto3.Session(profile_name=profile_to_use)
    else:
        session = boto3.Session()  # Uses IAM role in Glue
    athena = session.client("athena", region_name=actual_region, verify=not args.no_verify_ssl)
    glue = session.client("glue", region_name=actual_region, verify=not args.no_verify_ssl)
    
    # Check if source table exists
    print(f"📋 Checking if source table {actual_database}.{SOURCE_TABLE} exists...")
    if not check_table_exists(glue, actual_database, SOURCE_TABLE):
        print(f"❌ Source table {actual_database}.{SOURCE_TABLE} does not exist!")
        print("   Please create the source table first.")
        sys.exit(1)
    print(f"✅ Source table {actual_database}.{SOURCE_TABLE} exists")
    print()
    
    # Check if target table already exists
    print(f"📋 Checking if target table {actual_database}.{TARGET_TABLE} already exists...")
    if check_table_exists(glue, actual_database, TARGET_TABLE):
        print(f"⚠️  Target table {actual_database}.{TARGET_TABLE} already exists!")
        if args.force:
            print("   --force flag set, dropping existing table...")
            # Drop existing table
            drop_sql = f"DROP TABLE IF EXISTS {actual_database}.{TARGET_TABLE};"
            run_athena(athena, drop_sql, f"DROP {TARGET_TABLE}", actual_workgroup, actual_results_s3)
            print()
        else:
            print("   Use --force to drop and recreate it.")
            sys.exit(0)
    else:
        print(f"✅ Target table {actual_database}.{TARGET_TABLE} does not exist, will create new")
        print()
    
    # Create the table
    print("=" * 80)
    print("Creating table...")
    print("=" * 80)
    print()
    
    # Build SQL with actual database name and S3 location
    create_sql = f"""CREATE TABLE {actual_database}.{TARGET_TABLE}
WITH (
  external_location = '{s3_location}',
  format = 'PARQUET',
  write_compression = 'SNAPPY'
) AS
SELECT
  customer_user_id as row_id,
  customer_user_id 
FROM {actual_database}.{SOURCE_TABLE};"""
    
    try:
        run_athena(athena, create_sql, f"CREATE {TARGET_TABLE}", actual_workgroup, actual_results_s3)
        print()
        
        # Verify table was created
        print(f"📋 Verifying table {actual_database}.{TARGET_TABLE} was created...")
        if check_table_exists(glue, actual_database, TARGET_TABLE):
            print(f"✅ Table {actual_database}.{TARGET_TABLE} created successfully!")
            
            # Get table details
            table_info = glue.get_table(DatabaseName=actual_database, Name=TARGET_TABLE)
            storage_desc = table_info['Table']['StorageDescriptor']
            location = storage_desc.get('Location', 'N/A')
            print(f"   Location: {location}")
            print(f"   Format: {storage_desc.get('InputFormat', 'N/A')}")
        else:
            print(f"⚠️  Table {actual_database}.{TARGET_TABLE} was not found after creation")
        
        print()
        print("=" * 80)
        print("✅ SUCCESS")
        print("=" * 80)
        print(f"Table {actual_database}.{TARGET_TABLE} is ready for Entity Resolution Service")
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

