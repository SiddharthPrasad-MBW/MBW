#!/usr/bin/env python3
import os, sys, time, boto3, datetime

# ---------------- CONFIG: tweak here or pass as env vars ----------------
ENV             = os.getenv("ENV", "dev").lower()          # "dev" | "prod"
REGION          = os.getenv("AWS_REGION", "us-east-1")
WORKGROUP       = os.getenv("ATHENA_WORKGROUP", "primary")
RESULTS_S3      = os.getenv("ATHENA_RESULTS_S3", f"s3://omc-flywheel-{ENV}-analysis-data/query-results/")
STAGED_DB       = os.getenv("STAGED_DB", f"omc_flywheel_{ENV}")
FINAL_DB        = os.getenv("FINAL_DB",  f"omc_flywheel_{ENV}")  # use _prod when running in prod
BUCKETED_BASE   = os.getenv("BUCKETED_BASE", f"s3://omc-flywheel-data-us-east-1-{ENV}/omc_cleanroom_data/cleanroom_tables/bucketed/")
BUCKET_COL      = os.getenv("BUCKET_COL", "customer_user_id")
BUCKET_COUNT    = int(os.getenv("BUCKET_COUNT", "256"))
# Version output S3 prefixes automatically (safer for prod). Set to "" to disable.
VERSION_SUFFIX  = os.getenv("VERSION_SUFFIX", datetime.datetime.utcnow().strftime("v=%Y%m%dT%H%M%SZ"))

# Tables to process (lowercase names). Add/remove as needed.
ALL_TABLES = [
    "addressable_ids",
    "ibe_01","ibe_02","ibe_03","ibe_03_a","ibe_04","ibe_04_a","ibe_05","ibe_05_a",
    "ibe_06","ibe_06_a","ibe_08","ibe_09",
    "miacs_01","miacs_01_a","miacs_02","miacs_02_a","miacs_02_b",
    "miacs_03","miacs_03_a","miacs_03_b","miacs_04",
    "new_borrowers","n_a","n_a_a"
]

# Filter tables if TABLES_FILTER is provided (comma-separated list)
TABLES_FILTER = os.getenv("TABLES_FILTER", "").strip()
if TABLES_FILTER:
    filter_list = [t.strip().lower() for t in TABLES_FILTER.split(",")]
    TABLES = [t for t in ALL_TABLES if t in filter_list]
    print(f"🔍 Filtering tables to: {TABLES}")
else:
    TABLES = ALL_TABLES
# -----------------------------------------------------------------------

athena = boto3.client("athena", region_name=REGION)
glue   = boto3.client("glue",   region_name=REGION)

def run_athena(sql: str, desc: str):
    resp = athena.start_query_execution(
        QueryString=sql,
        WorkGroup=WORKGROUP,
        ResultConfiguration={"OutputLocation": RESULTS_S3},
    )
    qid = resp["QueryExecutionId"]
    while True:
        st = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]
        state = st["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(2)
    if state != "SUCCEEDED":
        reason = st.get("StateChangeReason", "")
        raise RuntimeError(f"{desc} failed: {reason}")
    return qid

def get_glue_columns(db: str, table: str):
    """
    Return Glue column list (Name, Type). Ensures customer_user_id is first and caps to ≤100 cols.
    """
    try:
        t = glue.get_table(DatabaseName=db, Name=table)["Table"]
    except glue.exceptions.EntityNotFoundException:
        raise RuntimeError(f"Source table not found: {db}.{table}")

    cols = t["StorageDescriptor"]["Columns"]
    # Promote customer_user_id to the front if present; cap to 100 (1 + 99)
    names = [c["Name"] for c in cols]
    if BUCKET_COL in names:
        # keep order but pop and insert at 0
        cols_sorted = [c for c in cols if c["Name"] == BUCKET_COL] + [c for c in cols if c["Name"] != BUCKET_COL]
    else:
        cols_sorted = cols
    # Cap total columns
    cols_capped = cols_sorted[:100]
    return cols_capped

def mk_select_list(cols):
    return ",\n  ".join([c["Name"] for c in cols])

def make_drop_sql(final_db, final_table):
    return f"DROP TABLE IF EXISTS {final_db}.{final_table}"

def get_snapshot_dt_from_metadata(bucketed_base):
    """Read snapshot_dt from metadata file"""
    try:
        s3_client = boto3.client('s3')
        bucket = bucketed_base.split('/')[2]
        key = f"{bucketed_base.split('/', 3)[3]}metadata/snapshot_dt.txt"
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read().decode('utf-8').strip()
    except Exception as e:
        print(f"⚠️  Could not read snapshot_dt metadata: {e}")
        return None

def make_ctas_sql(source_db, source_table, final_db, final_table, external_location, select_cols, snapshot_dt=None):
    comment = f"Bucketed table created from snapshot_dt={snapshot_dt}" if snapshot_dt else "Bucketed table"
    return f"""
CREATE TABLE {final_db}.{final_table}
COMMENT '{comment}'
WITH (
  format = 'PARQUET',
  parquet_compression = 'SNAPPY',
  external_location = '{external_location}',
  bucketed_by = ARRAY['{BUCKET_COL}'],
  bucket_count = {BUCKET_COUNT}
) AS
SELECT
  {select_cols}
FROM {source_db}.{source_table}
""".strip()

def get_available_tables():
    """Get list of tables that actually exist in the Glue catalog"""
    available_tables = []
    for base in TABLES:
        src_table = f"ext_{base}"
        try:
            glue.get_table(DatabaseName=STAGED_DB, Name=src_table)
            available_tables.append(base)
            print(f"✅ Found source table: {STAGED_DB}.{src_table}")
        except glue.exceptions.EntityNotFoundException:
            print(f"⚠️  Source table not found: {STAGED_DB}.{src_table}")
    return available_tables

def main():
    print(f"ENV={ENV}  WG={WORKGROUP}")
    print(f"STAGED_DB={STAGED_DB}  FINAL_DB={FINAL_DB}")
    print(f"RESULTS_S3={RESULTS_S3}")
    
    # Read snapshot_dt from metadata
    snapshot_dt = get_snapshot_dt_from_metadata(BUCKETED_BASE)
    if snapshot_dt:
        print(f"📅 Snapshot date: {snapshot_dt}")
    else:
        print("⚠️  No snapshot_dt metadata found")
    
    run_athena(f"CREATE DATABASE IF NOT EXISTS {FINAL_DB}", "ensure-final-db")

    # Only process tables that actually exist
    available_tables = get_available_tables()
    print(f"\n📊 Processing {len(available_tables)} available tables: {available_tables}")

    successes, failures = [], []

    for base in available_tables:
        src_table = f"ext_{base}"
        dst_table = f"bucketed_{base}"

        # destination S3 (with optional versioning)
        dst_path = f"{BUCKETED_BASE.rstrip('/')}/{base}/"
        if VERSION_SUFFIX:
            dst_path = f"{dst_path.rstrip('/')}/{VERSION_SUFFIX}/"

        print(f"\n=== {base} ===")
        print(f"Source: {STAGED_DB}.{src_table}")
        print(f"Final : {FINAL_DB}.{dst_table}")
        print(f"Out   : {dst_path}")

        try:
            # Build ≤100 column projection with customer_user_id first
            glue_cols = get_glue_columns(STAGED_DB, src_table)
            select_cols = mk_select_list(glue_cols)

            # First drop the table if it exists
            drop_sql = make_drop_sql(FINAL_DB, dst_table)
            run_athena(drop_sql, f"DROP {dst_table}")

            # Then create the bucketed table
            ctas_sql = make_ctas_sql(STAGED_DB, src_table, FINAL_DB, dst_table, dst_path, select_cols, snapshot_dt)
            run_athena(ctas_sql, f"CTAS {dst_table}")
            print(f"✅ Created {FINAL_DB}.{dst_table}")

            # Quick metadata check (optional)
            run_athena(f"DESCRIBE FORMATTED {FINAL_DB}.{dst_table}", f"describe {dst_table}")

            successes.append(base)
        except Exception as e:
            print(f"❌ {base}: {e}")
            failures.append((base, str(e)))

    print("\nSummary")
    print("-------")
    print(f"✅ Success: {len(successes)}")
    if successes: print("   " + ", ".join(successes))
    print(f"❌ Failed : {len(failures)}")
    for n, err in failures:
        print(f"   - {n}: {err}")

if __name__ == "__main__":
    main()
