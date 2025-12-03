#!/usr/bin/env python3
# etl-omc-flywheel-prod-prepare-part-tables.py — Glue Spark job
#
# Option A (classic): Ensure every part_* table is partitioned by id_bucket
#   1) If not partitioned, recreate via Glue API as PARTITIONED BY (id_bucket INT)
#   2) Always run MSCK REPAIR TABLE via Athena API (adds any missing partitions)
#   3) If MSCK fails, fallback to S3 discovery + batch_create_partition
#   4) Optionally strip partition projection properties if previously set
#
# Args (Glue job parameters):
#   --DATABASE omc_flywheel_prod
#   --TABLE_PREFIX part_
#   --AWS_REGION us-east-1
#   --ATHENA_WORKGROUP primary              (optional, default primary)
#   --ATHENA_RESULTS s3://bucket/path/       (optional, default from analysis bucket)
#   --STRIP_PROJECTION true|false            (optional, default true)
#   --MAX_PARTS_PER_BATCH 100               (optional, default 100)
#   --LOG_SAMPLE 3                           (optional, default 0=off)

import sys
import time
import boto3
from botocore.config import Config
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext

# ---------- Parse args ----------
def get_optional_arg(name: str, default: str) -> str:
    """Helper to read optional args passed to Glue without making them required"""
    flag = f"--{name}"
    try:
        idx = sys.argv.index(flag)
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    except ValueError:
        pass
    return default

# Get required parameters (using names that match actual Glue job configuration)
args = getResolvedOptions(sys.argv, [
    'DATABASE', 'TABLE_PREFIX'
])

DB               = args['DATABASE']
TABLE_PREFIX     = args['TABLE_PREFIX']

# Get optional parameters with defaults
REGION           = get_optional_arg('AWS_REGION', get_optional_arg('REGION', 'us-east-1'))
ATHENA_WG        = get_optional_arg('ATHENA_WORKGROUP', 'primary')
ATHENA_RESULTS   = get_optional_arg('ATHENA_RESULTS', '')  # Will be validated if needed
STRIP_PROJECTION = get_optional_arg('STRIP_PROJECTION', 'true').lower() in ('1','true','yes','on')
MAX_BATCH        = max(1, int(get_optional_arg('MAX_PARTS_PER_BATCH', '100')))
LOG_SAMPLE       = int(get_optional_arg('LOG_SAMPLE', '0'))

# ---------- Spark / Glue setup ----------
sc = SparkContext.getOrCreate()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

# Speed up partition discovery and use Glue/Hive catalog
spark.conf.set("spark.sql.sources.parallelPartitionDiscovery.enabled", "true")
spark.conf.set("spark.sql.sources.parallelPartitionDiscovery.threshold", "1")
# spark.sql.catalogImplementation is a static config - cannot be set at runtime (removed)
spark.conf.set("spark.sql.hive.manageFilesourcePartitions", "true")
# Avoid record-per-file capping that can slow writes during incidental ops
spark.conf.set("spark.sql.files.maxRecordsPerFile", str(10**12))

cfg  = Config(retries={"max_attempts": 10, "mode": "standard"})
glue   = boto3.client("glue",   region_name=REGION, config=cfg)
athena = boto3.client("athena", region_name=REGION, config=cfg)
s3     = boto3.client("s3",     region_name=REGION, config=cfg)

# ---------- Helpers ----------
def list_part_tables(db: str, prefix: str):
    p = glue.get_paginator("get_tables")
    for page in p.paginate(DatabaseName=db):
        for t in page.get("TableList", []):
            if t["Name"].startswith(prefix):
                yield t

def get_partition_count(db: str, table: str) -> int:
    p = glue.get_paginator("get_partitions")
    total = 0
    for page in p.paginate(DatabaseName=db, TableName=table, PaginationConfig={"MaxItems": 100000}):
        total += len(page.get("Partitions", []))
    return total

def recreate_as_partitioned_if_needed(t: dict) -> str:
    """
    If the Glue table isn't partitioned, recreate it with PARTITIONED BY (id_bucket INT)
    pointing at the SAME S3 location. No data is moved. Uses Glue API instead of Spark SQL.
    """
    name = t["Name"]
    sd   = t["StorageDescriptor"]
    loc  = sd["Location"]
    pk_names = [pk["Name"] for pk in t.get("PartitionKeys", [])]
    if pk_names == ["id_bucket"]:
        return "already_partitioned"

    # Build column list from Glue schema; ensure id_bucket is NOT a data column
    cols = [c for c in sd["Columns"] if c["Name"] != "id_bucket"]
    
    # Create partition key definition
    partition_keys = [{"Name": "id_bucket", "Type": "int"}]
    
    # Prepare table input for Glue API
    table_input = {
        "Name": name,
        "TableType": "EXTERNAL_TABLE",
        "StorageDescriptor": {
            "Columns": cols,
            "Location": loc,
            "InputFormat": sd.get("InputFormat", "org.apache.hadoop.mapred.TextInputFormat"),
            "OutputFormat": sd.get("OutputFormat", "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"),
            "SerdeInfo": sd.get("SerdeInfo", {
                "SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe",
                "Parameters": {"serialization.format": "1"}
            }),
            "Parameters": sd.get("Parameters", {})
        },
        "PartitionKeys": partition_keys,
        "Parameters": {
            **(t.get("Parameters") or {}),
            "classification": "parquet",
            "EXTERNAL": "TRUE",
            "parquet.compression": "SNAPPY"
        }
    }
    
    print(f"[{name}] Recreating as partitioned at {loc}")
    try:
        glue.update_table(DatabaseName=DB, TableInput=table_input)
        return "migrated"
    except glue.exceptions.EntityNotFoundException:
        glue.create_table(DatabaseName=DB, TableInput=table_input)
        return "migrated"
    except Exception as e:
        print(f"[{name}] ERROR updating table via Glue API: {e}")
        raise

def strip_projection_properties_if_any(name: str, params: dict):
    """
    Remove projection.* and storage.location.template properties if present.
    Uses Glue API to update table parameters.
    """
    if not STRIP_PROJECTION:
        return "skipped"
    keys = [k for k in (params or {}).keys()
            if k.startswith("projection.") or k == "storage.location.template"]
    if not keys:
        return "none"
    
    # Get current table to preserve all properties except projection ones
    try:
        current_table = glue.get_table(DatabaseName=DB, Name=name)["Table"]
        current_params = current_table.get("Parameters") or {}
        
        # Filter out projection properties
        cleaned_params = {k: v for k, v in current_params.items()
                         if not (k.startswith("projection.") or k == "storage.location.template")}
        
        # Update table with cleaned parameters
        table_input = {
            "Name": name,
            "StorageDescriptor": current_table["StorageDescriptor"],
            "PartitionKeys": current_table.get("PartitionKeys", []),
            "Parameters": cleaned_params
        }
        glue.update_table(DatabaseName=DB, TableInput=table_input)
        return f"unset {len(keys)}"
    except Exception as e:
        print(f"[{name}] WARN: Failed to strip projection properties ({e}); leaving properties as-is")
        return "failed"

def run_athena(sql: str):
    """Run one Athena statement and wait for completion."""
    if not ATHENA_RESULTS:
        raise ValueError("ATHENA_RESULTS must be set for Athena-based MSCK repair")
    resp = athena.start_query_execution(
        QueryString=sql,
        WorkGroup=ATHENA_WG,
        ResultConfiguration={"OutputLocation": ATHENA_RESULTS},
    )
    qid = resp["QueryExecutionId"]
    while True:
        st = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]
        state = st["State"]
        if state in ("SUCCEEDED","FAILED","CANCELLED"):
            if state != "SUCCEEDED":
                reason = st.get("StateChangeReason","")
                raise RuntimeError(f"Athena {state}: {reason} :: {sql[:160]}...")
            return
        time.sleep(0.8)

def parse_s3_loc(uri: str):
    """Parse S3 URI into bucket and key."""
    assert uri.startswith("s3://"), f"Not an S3 URI: {uri}"
    parts = uri[5:].split("/", 1)
    bucket = parts[0]
    key = parts[1] if len(parts) > 1 else ""
    return bucket, key

def s3_list_subdirs(bucket: str, prefix: str):
    """Yield immediate child dir tokens (last path component before '/')."""
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter="/"):
        for cp in page.get("CommonPrefixes", []):
            yield cp["Prefix"].split("/")[-2]

def existing_partitions_in_glue(table_name: str) -> set:
    """Get set of partition values (id_bucket) already registered in Glue."""
    have = set()
    paginator = glue.get_paginator("get_partitions")
    for page in paginator.paginate(DatabaseName=DB, TableName=table_name):
        for part in page.get("Partitions", []):
            try:
                have.add(int(part["Values"][0]))
            except Exception:
                pass
    return have

def s3_buckets_present(loc: str) -> set:
    """Discover id_bucket partitions present on S3."""
    bucket, key = parse_s3_loc(loc)
    present = set()
    for last in s3_list_subdirs(bucket, key):
        if last.startswith("id_bucket="):
            try:
                present.add(int(last.split("=")[1]))
            except Exception:
                pass
    return present

def batch_create_missing(table_name: str, sd_ref: dict, missing_vals: list):
    """Glue batch_create_partition in chunks."""
    loc = sd_ref["Location"].rstrip("/")
    inputs = [{
        "Values": [str(v)],
        "StorageDescriptor": {
            "Location": f"{loc}/id_bucket={v}/",
            "InputFormat":  sd_ref.get("InputFormat"),
            "OutputFormat": sd_ref.get("OutputFormat"),
            "SerdeInfo":    sd_ref.get("SerdeInfo"),
            "Compressed":   sd_ref.get("Compressed", False),
            "NumberOfBuckets": 0,
            "StoredAsSubDirectories": False,
            "Parameters": sd_ref.get("Parameters") or {}
        },
        "Parameters": {}
    } for v in missing_vals]

    created = 0
    for i in range(0, len(inputs), MAX_BATCH):
        batch = inputs[i:i+MAX_BATCH]
        glue.batch_create_partition(DatabaseName=DB, TableName=table_name, PartitionInputList=batch)
        created += len(batch)
    return created

def msck_repair(name: str, table_storage_descriptor: dict):
    """Run MSCK REPAIR TABLE via Athena API, with fallback to manual partition creation."""
    # If ATHENA_RESULTS not set, skip Athena and use fallback directly
    if not ATHENA_RESULTS:
        print(f"[{name}] ATHENA_RESULTS not set, using fallback partition discovery")
    else:
        sql = f"MSCK REPAIR TABLE {DB}.{name}"
        print(f"[{name}] Athena: {sql}")
        try:
            run_athena(sql)
            return "succeeded"
        except Exception as e:
            print(f"[{name}] WARN: MSCK failed ({e}), will batch-create missing partitions")
    
    # Fallback: discover partitions on S3 and compare with Glue
    try:
        s3_have = s3_buckets_present(table_storage_descriptor["Location"])
        glue_have = existing_partitions_in_glue(name)
        missing = sorted(list(s3_have - glue_have))
        if missing:
            created = batch_create_missing(name, table_storage_descriptor, missing)
            print(f"[{name}] Glue: added {created} missing partitions via batch_create_partition")
            return f"fallback_added_{created}"
        else:
            print(f"[{name}] No missing partitions detected (fallback path)")
            return "fallback_no_missing"
    except Exception as e2:
        print(f"[{name}] ERROR: Fallback also failed: {e2}")
        raise

def sample_partitions(db: str, table: str, k: int):
    """Sample partition values using Athena (if ATHENA_RESULTS configured)."""
    if k <= 0 or not ATHENA_RESULTS:
        return []
    try:
        sql = f"SELECT DISTINCT id_bucket FROM {db}.{table} ORDER BY 1 LIMIT {k}"
        run_athena(sql)
        # Note: We run the query but don't fetch results to keep it simple
        # The sample is optional and mainly for logging
        return []  # Could enhance later to fetch results if needed
    except Exception:
        return []

# ---------- Main ----------
print(f"=== PREPARE PARTITIONS START === db={DB} prefix={TABLE_PREFIX} region={REGION} strip_projection={STRIP_PROJECTION}")
print(f"Athena workgroup={ATHENA_WG} results={ATHENA_RESULTS or '(not set - MSCK will use fallback only)'}")
migrated = 0
repaired = 0
batch_added = 0
errors   = 0

for t in list_part_tables(DB, TABLE_PREFIX):
    name   = t["Name"]
    params = t.get("Parameters") or {}
    try:
        # 1) Ensure table is partitioned by id_bucket
        status = recreate_as_partitioned_if_needed(t)
        if status == "migrated":
            migrated += 1
            # refresh Glue table snapshot after DDL change
            t = glue.get_table(DatabaseName=DB, Name=name)["Table"]
            params = t.get("Parameters") or {}

        # 2) Strip projection props if materializing partitions
        proj_status = strip_projection_properties_if_any(name, params)

        # 3) Run MSCK via Athena API (or fallback to manual partition creation)
        sd = t["StorageDescriptor"]
        msck_status = msck_repair(name, sd)
        
        if msck_status == "succeeded":
            repaired += 1
        elif msck_status.startswith("fallback_added_"):
            repaired += 1
            batch_added += 1
            try:
                created_count = int(msck_status.split("_")[-1])
                # Already logged in msck_repair function
            except:
                pass
        elif msck_status == "fallback_no_missing":
            repaired += 1
        else:
            # Still count as repaired if we attempted it
            repaired += 1

        # 4) Report partition count + optional sample
        pc = get_partition_count(DB, name)
        samp = sample_partitions(DB, name, LOG_SAMPLE)
        extra = f" sample={samp}" if samp else ""
        print(f"[{name}] partitions={pc} (proj={proj_status} msck={msck_status}){extra}")

    except Exception as e:
        errors += 1
        print(f"[{name}] ERROR: {e}")

print(f"=== PREPARE PARTITIONS DONE === migrated={migrated} repaired={repaired} batch_added={batch_added} errors={errors}")
