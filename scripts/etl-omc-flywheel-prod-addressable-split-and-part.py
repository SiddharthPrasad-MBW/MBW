import sys
import boto3
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, count, sum as spark_sum
# ✅ add Spark functions for hashing/modulo
from pyspark.sql import functions as F
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
        prefix = base_path.split('/', 3)[3] if len(base_path.split('/')) > 3 else ""
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter='/')
        snapshots = []
        for obj in response.get('CommonPrefixes', []):
            match = re.search(r'snapshot_dt=(\d{4}-\d{2}-\d{2})', obj['Prefix'])
            if match:
                snapshots.append(match.group(1))
        if snapshots:
            return sorted(snapshots, reverse=True)[0]
        else:
            raise Exception("No snapshots found")
    except Exception as e:
        raise Exception(f"Could not discover snapshots: {e}")

if args['SNAPSHOT_DT'] and args['SNAPSHOT_DT'] != '' and args['SNAPSHOT_DT'] != '_NONE_':
    snapshot_dt = args['SNAPSHOT_DT']
    source_path = f"{base_source_path.rstrip('/')}/snapshot_dt={snapshot_dt}/"
else:
    snapshot_dt = discover_latest_snapshot(base_source_path)
    source_path = f"{base_source_path.rstrip('/')}/snapshot_dt={snapshot_dt}/"

# Convert s3:// to s3a:// for Spark
if source_path.startswith('s3://'):
    source_path = source_path.replace('s3://', 's3a://', 1)
if target_path.startswith('s3://'):
    target_path = target_path.replace('s3://', 's3a://', 1)

# Size helpers (unchanged)
from urllib.parse import urlparse
PREFERRED = [24, 28, 32, 36, 48, 56, 64, 96, 112, 128]

def _sum_s3_prefix_bytes(s3_uri: str) -> int:
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
    if size_gb >= 30: return 380
    elif size_gb >= 20: return 392
    elif size_gb >= 10: return 490
    else: return 400

def _snap(n: int) -> int:
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

job.init(job_name, args)

try:
    print(f"\n📖 Reading addressable_ids data from {source_path}")
    df = spark.read.parquet(source_path)

    total_records = df.count()
    print(f"📊 Total records: {total_records:,}")

    if "Customer_User_id" not in df.columns:
        print("❌ ERROR: Customer_User_id column not found in addressable_ids table")
        print(f"Available columns: {df.columns}")
        sys.exit(1)

    # normalize column name
    df = df.withColumnRenamed("Customer_User_id", "customer_user_id")

    # ✅ ADD id_bucket using xxhash64, normalized to [0..bucket_count-1]
    df = df.withColumn(
        "id_bucket",
        F.pmod(F.xxhash64(F.col("customer_user_id")), F.lit(bucket_count)).cast("int")
    )

    # 2) dynamic partition overwrite = replace only the partitions you write
    spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")

    # (recommended) speeds up discovery/repairs
    spark.conf.set("spark.sql.sources.parallelPartitionDiscovery.enabled", "true")
    spark.conf.set("spark.sql.sources.parallelPartitionDiscovery.threshold", "1")

    # (Optional) measure size to pick file count — keep if you like your sizing step
    # Get account ID dynamically
    sts_client = boto3.client('sts')
    account_id = sts_client.get_caller_identity()['Account']
    region = boto3.Session().region_name or 'us-east-1'
    glue_bucket = f"aws-glue-assets-{account_id}-{region}"
    temp_path = f"s3://{glue_bucket}/temp/addressable_ids/"
    df.select("customer_user_id", "id_bucket").write.mode("overwrite").parquet(temp_path)  # sample size
    table_size_bytes = _sum_s3_prefix_bytes(temp_path)
    table_size_gb = table_size_bytes / (1024**3)
    target_mb = _target_mb_for_size_gb(table_size_gb)
    raw_files = max(1, math.ceil((table_size_gb * 1024) / target_mb))
    target_files = max(1, _snap(raw_files))
    print(f"📊 Size (approx from sample): {table_size_gb:.2f} GB  → target files: {target_files}")

    # 🔁 Repartition BY id_bucket to co-locate data per bucket
    print(f"\n🔄 Repartitioning to {bucket_count} buckets by id_bucket...")
    df_bucketed = df.repartition(bucket_count, "id_bucket")

    # ✅ Write partitioned by id_bucket (no coalesce; let Spark create files per partition)
    data_path = f"{target_path.rstrip('/')}/addressable_ids/"
    print(f"💾 Writing partitioned addressable_ids to {data_path}")
    (df_bucketed.write
        .mode("overwrite")
        .option("compression", "snappy")
        .partitionBy("id_bucket")
        .parquet(data_path))

    # metadata
    try:
        s3_client = boto3.client('s3')
        bucket = target_path.split('/')[2]
        metadata_key = f"{target_path.split('/', 3)[3]}metadata/snapshot_dt.txt"
        s3_client.put_object(Bucket=bucket, Key=metadata_key, Body=snapshot_dt)
        print(f"📅 Wrote snapshot_dt={snapshot_dt} to s3://{bucket}/{metadata_key}")
    except Exception as e:
        print(f"⚠️  Error writing metadata: {e}")

    print("✅ Successfully wrote addressable_ids with id_bucket partitioning")
    print(f"📂 Output: {data_path}")
    print(f"🪣 Partitions: id_bucket (0..{bucket_count-1})")

except Exception as e:
    print(f"❌ Error processing addressable_ids: {str(e)}")
    raise e
finally:
    job.commit()
