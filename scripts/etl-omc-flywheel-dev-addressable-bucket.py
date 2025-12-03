import sys
import boto3
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, count, sum as spark_sum
import time
from urllib.parse import urlparse

# Initialize Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)

# Get job parameters
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'SOURCE_PATH',
    'TARGET_PATH', 
    'BUCKET_COUNT',
    'TARGET_FILE_MB',
    'SNAPSHOT_DT'
])

job_name = args['JOB_NAME']
base_source_path = args['SOURCE_PATH']
target_path = args['TARGET_PATH']
bucket_count = int(args['BUCKET_COUNT'])
target_file_mb = int(args['TARGET_FILE_MB'])

# Determine snapshot_dt (manual override or auto-discover)
import re
import math
from datetime import datetime

def discover_latest_snapshot(base_path):
    """Auto-discover the latest snapshot_dt from raw_input directory"""
    try:
        s3_client = boto3.client('s3')
        bucket = base_path.split('/')[2]
        # Look for subdirectories within the raw_input path
        prefix = base_path.split('/', 3)[3] if len(base_path.split('/')) > 3 else ""
        
        print(f"🔍 DEBUG: base_path = {base_path}")
        print(f"🔍 DEBUG: bucket = {bucket}")
        print(f"🔍 DEBUG: prefix = {prefix}")
        
        # List all snapshot_dt=* directories within the raw_input path
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix,
            Delimiter='/'
        )
        
        print(f"🔍 DEBUG: CommonPrefixes count = {len(response.get('CommonPrefixes', []))}")
        for cp in response.get('CommonPrefixes', []):
            print(f"🔍 DEBUG: CommonPrefix = {cp['Prefix']}")
        
        snapshots = []
        for obj in response.get('CommonPrefixes', []):
            print(f"🔍 DEBUG: checking prefix = {obj['Prefix']}")
            match = re.search(r'snapshot_dt=(\d{4}-\d{2}-\d{2})', obj['Prefix'])
            if match:
                snapshots.append(match.group(1))
                print(f"🔍 DEBUG: found snapshot = {match.group(1)}")
        
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
    # Auto-discover latest snapshot from raw_input directory
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

# Size calculation functions (from infobase script)
PREFERRED = [24, 28, 32, 36, 48, 56, 64, 96, 112, 128]

def _sum_s3_prefix_bytes(s3_uri: str) -> int:
    """Sum object sizes under an S3 prefix (recursive)."""
    u = urlparse(s3_uri if s3_uri.startswith("s3://") else f"s3://{s3_uri}")
    bucket, prefix = u.netloc, u.path.lstrip("/")
    s3_client = boto3.client("s3")
    total = 0
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            total += obj["Size"]
    return total

def _target_mb_for_size_gb(size_gb: float) -> int:
    """Target MB per file based on total size in GB."""
    if size_gb >= 30: return 380   # Very large
    elif size_gb >= 20: return 392   # Large  
    elif size_gb >= 10: return 490   # Medium
    else: return 400                # Small

def _snap(n: int) -> int:
    """Snap to preferred file counts."""
    if n <= PREFERRED[0]: return PREFERRED[0]
    if n >= PREFERRED[-1]: return PREFERRED[-1]
    for i in range(len(PREFERRED) - 1):
        if PREFERRED[i] <= n <= PREFERRED[i + 1]:
            return PREFERRED[i + 1] if n - PREFERRED[i] > PREFERRED[i + 1] - n else PREFERRED[i]
    return PREFERRED[-1]

print(f"🚀 Starting {job_name}")
print(f"📂 Source: {source_path}")
print(f"📂 Target: {target_path}")
print(f"🪣 Buckets: {bucket_count}")
print(f"📄 Target file size: {target_file_mb} MB")

# Initialize job
job.init(job_name, args)

try:
    # Read the addressable_ids table
    print(f"\n📖 Reading addressable_ids data from {source_path}")
    df = spark.read.parquet(source_path)
    
    # Get basic stats
    total_records = df.count()
    print(f"📊 Total records: {total_records:,}")
    
    # Check if Customer_User_id column exists and rename to standard lowercase
    if "Customer_User_id" not in df.columns:
        print("❌ ERROR: Customer_User_id column not found in addressable_ids table")
        print(f"Available columns: {df.columns}")
        sys.exit(1)
    
    # Rename to standard lowercase for consistency with other tables
    df = df.withColumnRenamed("Customer_User_id", "customer_user_id")
    print("🔄 Renamed Customer_User_id to customer_user_id for consistency")
    
    # Calculate target files based on ACTUAL data size (like infobase script)
    print(f"📊 Calculating optimal file count for addressable_ids...")
    
    # Write data to temp location to measure actual size
    # Use the production Glue assets bucket
    # Get account ID dynamically
    sts_client = boto3.client('sts')
    account_id = sts_client.get_caller_identity()['Account']
    region = boto3.Session().region_name or 'us-east-1'
    glue_bucket = f"aws-glue-assets-{account_id}-{region}"
    
    temp_path = f"s3://{glue_bucket}/temp/addressable_ids/"
    df.write.mode("overwrite").parquet(temp_path)
    
    # Measure actual size of addressable_ids data
    table_size_bytes = _sum_s3_prefix_bytes(temp_path)
    table_size_gb = table_size_bytes / (1024**3)
    
    # Use the same size bands as infobase script
    target_mb = _target_mb_for_size_gb(table_size_gb)
    
    # Calculate files for addressable_ids
    raw_files = max(1, math.ceil((table_size_gb * 1024) / target_mb))
    target_files = max(1, _snap(raw_files))
    
    print(f"📊 Addressable_ids size: {table_size_gb:.2f} GB (actual measured)")
    print(f"📄 Target MB per file: {target_mb} MB")
    print(f"🔢 Raw files calculation: {raw_files}")
    print(f"🎯 Snapped to: {target_files}")
    print(f"🪣 Buckets: {bucket_count} (consistent across all joinable tables)")
    print(f"📄 Target files: {target_files} (calculated from actual size)")
    
    # Step 1: Repartition to buckets by customer_user_id
    print(f"\n🔄 Repartitioning to {bucket_count} buckets by customer_user_id...")
    df_repartitioned = df.repartition(bucket_count, "customer_user_id")
    
    # Step 2: Coalesce to target file count
    print(f"📦 Coalescing to {target_files} files...")
    df_bucketed = df_repartitioned.coalesce(target_files)
    
    # Write the bucketed data to a subdirectory (same structure as infobase_attributes)
    data_path = f"{target_path.rstrip('/')}/addressable_ids/"
    print(f"💾 Writing bucketed addressable_ids to {data_path}")
    df_bucketed.write \
        .mode("overwrite") \
        .option("compression", "snappy") \
        .parquet(data_path)
    
    # Write snapshot_dt metadata for downstream jobs
    try:
        s3_client = boto3.client('s3')
        bucket = target_path.split('/')[2]
        # Write metadata in the same directory as the data
        metadata_key = f"{target_path.split('/', 3)[3]}metadata/snapshot_dt.txt"
        
        s3_client.put_object(
            Bucket=bucket,
            Key=metadata_key,
            Body=snapshot_dt
        )
        print(f"📅 Wrote snapshot_dt={snapshot_dt} to s3://{bucket}/{metadata_key}")
    except Exception as e:
        print(f"⚠️  Error writing metadata: {e}")
    
    print(f"✅ Successfully created bucketed addressable_ids table!")
    print(f"📂 Output location: {target_path}")
    print(f"🪣 Bucketed by: customer_user_id")
    print(f"📄 Files created: {target_files}")
    print(f"📅 Snapshot date: {snapshot_dt}")
    
except Exception as e:
    print(f"❌ Error processing addressable_ids: {str(e)}")
    raise e

finally:
    job.commit()
