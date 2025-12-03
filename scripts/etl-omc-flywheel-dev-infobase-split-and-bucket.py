import sys
import boto3
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, count, sum as spark_sum
from urllib.parse import urlparse
import math
import time

# Initialize Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)

# Get job parameters
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'SOURCE_PATH',
    'TARGET_BUCKET', 
    'BUCKET_COUNT',
    'TARGET_FILE_MB',
    'CSV_PATH',
    'SNAPSHOT_DT'
])

job_name = args['JOB_NAME']
base_source_path = args['SOURCE_PATH']
target_path = args['TARGET_BUCKET']
bucket_count = int(args['BUCKET_COUNT'])
target_file_mb = int(args['TARGET_FILE_MB'])
csv_path = args['CSV_PATH']

# Determine snapshot_dt (manual override or auto-discover)
import re
from datetime import datetime

def discover_latest_snapshot(base_path):
    """Auto-discover the latest snapshot_dt from raw_input directory"""
    try:
        s3_client = boto3.client('s3')
        bucket = base_path.split('/')[2]
        
        # Look in the raw_input directory for snapshots (not the full path)
        # Extract the raw_input prefix from the base_path
        if 'raw_input' in base_path:
            # If base_path already contains raw_input, use it as-is
            prefix = base_path.split('/', 3)[3] if len(base_path.split('/')) > 3 else ""
        else:
            # If base_path doesn't contain raw_input, construct it
            prefix = "opus/infobase_attributes/raw_input/"
        
        # List all snapshot_dt=* directories
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix,
            Delimiter='/'
        )
        
        snapshots = []
        for obj in response.get('CommonPrefixes', []):
            match = re.search(r'snapshot_dt=(\d{4}-\d{2}-\d{2})', obj['Prefix'])
            if match:
                snapshots.append(match.group(1))
        
        if snapshots:
            # Return the latest date (lexicographically sorted)
            latest = sorted(snapshots, reverse=True)[0]
            print(f"🔍 Found snapshots in raw_input: {snapshots}")
            print(f"📅 Latest snapshot: {latest}")
            return latest
        else:
            print("⚠️  No snapshots found in raw_input directory")
            raise Exception("No snapshots found")
    except Exception as e:
        print(f"⚠️  Error discovering snapshots: {e}")
        raise Exception(f"Could not discover snapshots: {e}")

if args['SNAPSHOT_DT'] and args['SNAPSHOT_DT'] != '' and args['SNAPSHOT_DT'] != '_NONE_':
    # Manual override - use specific date
    snapshot_dt = args['SNAPSHOT_DT']
    source_path = f"{base_source_path.rstrip('/')}/snapshot_dt={snapshot_dt}/"
    print(f"📅 Manual snapshot_dt: {snapshot_dt}")
else:
    # Auto-discover latest snapshot
    snapshot_dt = discover_latest_snapshot(base_source_path)
    source_path = f"{base_source_path.rstrip('/')}/snapshot_dt={snapshot_dt}/"
    print(f"📅 Auto-discovered snapshot_dt: {snapshot_dt}")

# Convert s3:// to s3a:// for Spark compatibility
if source_path.startswith('s3://'):
    source_path = source_path.replace('s3://', 's3a://', 1)
    print(f"🔄 Converted to s3a:// protocol: {source_path}")

if target_path.startswith('s3://'):
    target_path = target_path.replace('s3://', 's3a://', 1)
    print(f"🔄 Converted target to s3a:// protocol: {target_path}")

print(f"🚀 Starting {job_name}")
print(f"📂 Source: {source_path}")
print(f"📂 Target: {target_path}")
print(f"🪣 Buckets: {bucket_count}")
print(f"📄 Target file size: {target_file_mb} MB")
print(f"📋 CSV mapping: {csv_path}")

# Size calculation functions (from bucket job)
PREFERRED = [24, 28, 32, 36, 48, 56, 64, 96, 112, 128]

def _sum_s3_prefix_bytes(s3_uri: str) -> int:
    """Sum object sizes under an S3 prefix (recursive)."""
    u = urlparse(s3_uri if s3_uri.startswith("s3://") else f"s3://{s3_uri}")
    bucket, prefix = u.netloc, u.path.lstrip("/")
    s3 = boto3.client("s3")
    total = 0
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            # skip 0-byte markers if any
            if obj["Size"] > 0:
                total += obj["Size"]
    return total

def _target_mb_for_size_gb(size_gb: float) -> int:
    """Pick target MB/file by size band (keeps ≤512 MB typical)."""
    if size_gb >= 30:  return 380   # Very large
    if size_gb >= 20:  return 392   # Large
    if size_gb >= 10:  return 490   # Medium
    return 400                      # Small

def _snap(n: int, choices=PREFERRED) -> int:
    """Snap to the nearest preferred count (ties → smaller)."""
    return min(choices, key=lambda c: (abs(c - n), c))

def choose_target_files_from_prefix(src_prefix: str) -> int:
    """Compute a stable target file count from the total source size."""
    total_bytes = _sum_s3_prefix_bytes(src_prefix)
    size_gb = total_bytes / (1024**3)
    target_mb = _target_mb_for_size_gb(size_gb)
    raw = max(1, math.ceil((size_gb * 1024) / target_mb))  # files ≈ size_mb / target_mb
    return max(1, _snap(raw))

# Initialize job
job.init(job_name, args)

try:
    # Step 1: Read the CSV mapping file to get table names and columns
    print(f"\n📋 Reading table mapping from {csv_path}")
    csv_df = spark.read.option("header", "true").csv(csv_path)
    table_mappings = csv_df.collect()
    
    print(f"📊 Found {len(table_mappings)} table mappings")
    
    # Step 2: Read the source data
    print(f"\n📖 Reading source data from {source_path}")
    source_df = spark.read.parquet(source_path)
    
    # Get basic stats
    total_records = source_df.count()
    print(f"📊 Total records: {total_records:,}")
    
    # Check if customer_user_id column exists, or if we need to rename Customer_User_id
    if "customer_user_id" not in source_df.columns:
        if "Customer_User_id" in source_df.columns:
            # Rename to standard lowercase for consistency with other tables
            source_df = source_df.withColumnRenamed("Customer_User_id", "customer_user_id")
            print("🔄 Renamed Customer_User_id to customer_user_id for consistency")
        else:
            print("❌ ERROR: customer_user_id or Customer_User_id column not found in source data")
            print(f"Available columns: {source_df.columns}")
            sys.exit(1)
    
    # Group columns by table
    table_columns = {}
    for mapping in table_mappings:
        table_name = mapping['OMC_FLYWHEEL_TABLE']
        column_name = mapping['OMC_FLYWHEEL_COLUMN']
        
        if table_name not in table_columns:
            table_columns[table_name] = []
        table_columns[table_name].append(column_name)
    
    print(f"📊 Found {len(table_columns)} unique tables")
    
    # Step 3: Process each table
    for i, (table_name, columns) in enumerate(table_columns.items()):
        print(f"\n🔄 Processing table {i+1}/{len(table_columns)}: {table_name}")
        print(f"📋 Columns: {len(columns)}")
        
        # Ensure customer_user_id is included
        if 'customer_user_id' not in columns:
            columns.append('customer_user_id')
        
        # Select only the required columns
        try:
            table_df = source_df.select(*columns)
        except Exception as e:
            print(f"⚠️  Warning: Could not select columns for {table_name}: {str(e)}")
            print(f"Available columns: {source_df.columns}")
            continue
        
        # Calculate target files based on ACTUAL table size (like bucket job)
        table_records = table_df.count()
        
        # Write table to temp location to measure actual size
        # Get account ID dynamically
        sts_client = boto3.client('sts')
        account_id = sts_client.get_caller_identity()['Account']
        region = boto3.Session().region_name or 'us-east-1'
        glue_bucket = f"aws-glue-assets-{account_id}-{region}"
        temp_path = f"s3://{glue_bucket}/temp/{table_name}/"
        table_df.write.mode("overwrite").parquet(temp_path)
        
        # Measure actual size of this table's data
        table_size_bytes = _sum_s3_prefix_bytes(temp_path)
        table_size_gb = table_size_bytes / (1024**3)
        
        # Use the same size bands as bucket job
        if table_size_gb >= 30:  target_mb = 380   # Very large
        elif table_size_gb >= 20:  target_mb = 392   # Large  
        elif table_size_gb >= 10:  target_mb = 490   # Medium
        else: target_mb = 400                      # Small
        
        # Calculate files for this table
        raw_files = max(1, math.ceil((table_size_gb * 1024) / target_mb))
        target_files = max(1, _snap(raw_files))
        
        print(f"📊 Table size: {table_size_gb:.2f} GB (actual measured)")
        print(f"📄 Target MB per file: {target_mb} MB")
        print(f"🔢 Raw files calculation: {raw_files}")
        print(f"🎯 Snapped to: {target_files}")
        
        print(f"📊 Table records: {table_records:,}")
        print(f"📋 Columns: {len(columns)}")
        print(f"🪣 Buckets: {bucket_count} (for bucketing)")
        print(f"📄 Target files: {target_files} (calculated from source size)")
        
        # Step 4: Bucket the data (like bucket job)
        print(f"🔄 Bucketing {table_name}...")
        
        # Prevent record-cap splitting; we control count via coalesce()
        spark.conf.set("spark.sql.files.maxRecordsPerFile", 10**12)
        
        # Use repartition + coalesce to control file count, then write as parquet
        output_path = f"{target_path.rstrip('/')}/{table_name}/"
        print(f"💾 Writing bucketed {table_name} to {output_path}")
        
        try:
            (table_df.repartition(bucket_count, "customer_user_id")  # Logical bucketing by customer_user_id
                .coalesce(target_files)  # Control final file count
                .write
                .mode("overwrite")
                .option("compression", "snappy")
                .parquet(output_path))
        except Exception as e:
            print(f"⚠️  Error writing {table_name}: {str(e)}")
            print(f"🔄 Trying with different mode...")
            # Try with append mode and then overwrite
            (table_df.repartition(bucket_count, "customer_user_id")
                .coalesce(target_files)
                .write
                .mode("append")
                .option("compression", "snappy")
                .parquet(output_path))
        
        print(f"✅ Successfully created bucketed {table_name}!")
    
    # Write snapshot_dt metadata for downstream jobs
    try:
        s3_client = boto3.client('s3')
        bucket = target_path.split('/')[2]
        metadata_key = f"{target_path.split('/', 3)[3]}metadata/snapshot_dt.txt"
        
        s3_client.put_object(
            Bucket=bucket,
            Key=metadata_key,
            Body=snapshot_dt
        )
        print(f"📅 Wrote snapshot_dt={snapshot_dt} to s3://{bucket}/{metadata_key}")
    except Exception as e:
        print(f"⚠️  Error writing metadata: {e}")
    
    print(f"\n🎉 All tables processed successfully!")
    print(f"📂 Output location: {target_path}")
    print(f"🪣 Bucketed by: customer_user_id")
    print(f"📊 Tables created: {len(table_mappings)}")
    print(f"📅 Snapshot date: {snapshot_dt}")
    
except Exception as e:
    print(f"❌ Error processing tables: {str(e)}")
    raise e

finally:
    job.commit()
