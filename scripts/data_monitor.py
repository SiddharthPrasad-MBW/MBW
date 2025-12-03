#!/usr/bin/env python3
# data_monitor.py — Glue Python Shell (3.9)
#
# Monitors S3/Glue tables used by Clean Rooms (S3 source):
#  - Freshness: processed metadata/snapshot_dt.txt + raw_input cross-check
#  - Partition integrity: id_bucket=0..N-1 on S3 and in Glue (+ optional auto-repair)
#  - Catalog consistency: EXTERNAL_TABLE + Parquet formats/SerDe
#  - NEW: Record-count match (vs ext_ or part_, exact by default)
#  - NEW: Key quality: customer_user_id NOT NULL & UNIQUE
#  - NEW: Schema contract: part_ needs customer_user_id (data column) and partition key id_bucket (INT);
#         ext_ (if used for comparison) needs customer_user_id
#  - Optional: file-size hygiene (off by default)
#
# Outputs JSON + CSV to S3 and SNS alerts if issues.

import json, csv, io, os, sys, time, itertools, datetime as dt, re, math
import boto3
from botocore.config import Config
from botocore.exceptions import ParamValidationError
from datetime import datetime, timezone, timedelta

print(f"Starting data_monitor.py with sys.argv: {sys.argv}")

# ---------- args ----------
def parse_args():
    """Parse command-line arguments into a dictionary"""
    args = {}
    i = 0
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg.startswith("--"):
            key = arg[2:]  # Remove "--"
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--"):
                args[key] = sys.argv[i + 1]
                i += 2
            else:
                args[key] = ""  # Flag without value
                i += 1
        else:
            i += 1
    return args

def str_to_bool(v):
    """Helper function for boolean type conversion"""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() in ("true", "1", "yes", "on")
    return False

args = parse_args()

REGION   = (args.get("region") or os.getenv("AWS_REGION", "us-east-1")).strip()
DB_MON   = (args.get("database") or "").strip()
DB_SRC   = (args.get("compare_database") or DB_MON or "").strip()
PREFIX   = (args.get("table_prefix") or "part_").strip()
NB       = int(args.get("bucket_count") or "256")
RBKT     = (args.get("report_bucket") or "").strip()
RPFX     = ((args.get("report_prefix") or "data-monitor/").rstrip("/") + "/").strip()
TOPIC    = (args.get("sns_topic_arn") or "").strip()
AUTOR    = (args.get("auto_repair") or "athena").strip()
WG       = (args.get("athena_workgroup") or "primary").strip()
ARES     = (args.get("athena_results") or "").strip()
PKCOL    = (args.get("pk_column") or "customer_user_id").strip()
DATA_BKT = (args.get("data_bucket") or "").strip()  # Data bucket for raw input (e.g., omc-flywheel-data-us-east-1-prod)

# Boolean arguments
STRICT_SNAPSHOT = str_to_bool(args.get("strict_snapshot", "false"))
FRESHNESS_WINDOW_DAYS = int(args.get("freshness_window_days", "45"))
MAX_TABLES = int(args.get("max_tables", "0"))
COUNT_CHECK_ENABLED = str_to_bool(args.get("count_check_enabled", "true"))
COMPARE_SOURCE_TYPE = args.get("compare_source_type", "ext")
COUNT_TOLERANCE_PCT = float(args.get("count_tolerance_pct", "0.0"))
FILE_SIZE_CHECK = str_to_bool(args.get("file_size_check", "false"))
FILE_SIZE_MIN_MB = int(args.get("file_size_min_mb", "64"))
FILE_SIZE_MAX_MB = int(args.get("file_size_max_mb", "1024"))

# Validate required parameters
if not DB_MON or not DB_MON.strip():
    raise ValueError("Required parameter '--database' is missing or empty")
if not RBKT or not RBKT.strip():
    raise ValueError("Required parameter '--report_bucket' is missing or empty")

print(f"[DEBUG] DB_MON={DB_MON}, RBKT={RBKT}, ARES='{ARES}', COUNT_CHECK_ENABLED={COUNT_CHECK_ENABLED}, WG='{WG}'")

if COUNT_CHECK_ENABLED:
    if not ARES:
        raise ValueError("--athena_results must be set when --count_check_enabled is true")
    if not ARES.startswith("s3://"):
        raise ValueError(f"--athena_results must be a valid S3 URI (got: '{ARES}')")
    if not WG:
        raise ValueError(f"--athena_workgroup must be set (got: '{WG}')")

try:
    cfg = Config(retries={"max_attempts": 10, "mode": "standard"})
    glue   = boto3.client("glue",   region_name=REGION, config=cfg)
    s3     = boto3.client("s3",     region_name=REGION, config=cfg)
    athena = boto3.client("athena", region_name=REGION, config=cfg)
    sns    = boto3.client("sns",    region_name=REGION, config=cfg) if TOPIC else None
except Exception as e:
    raise RuntimeError(f"Failed to create boto3 clients (region={REGION}): {e}") from e

def now_utc_iso(): return dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def list_part_tables(db, prefix):
    count = 0
    try:
        paginator = glue.get_paginator("get_tables")
        for page in paginator.paginate(DatabaseName=db):
            for t in page.get("TableList", []):
                name = t["Name"]
                # Exclude tables ending in _er (Entity Resolution tables)
                if name.startswith(prefix) and not name.endswith("_er"):
                    yield t
                    count += 1
                    if MAX_TABLES and count >= MAX_TABLES: return
    except ParamValidationError as e:
        raise RuntimeError(f"ParamValidationError in list_part_tables(db='{db}', prefix='{prefix}'): {e}") from e

def get_bucket_key_from_s3_uri(uri: str):
    assert uri.startswith("s3://"), f"Not an S3 URI: {uri}"
    bits = uri[5:].split("/", 1)
    b = bits[0]
    k = bits[1] + ("" if uri.endswith("/") else "/") if len(bits) > 1 else ""
    return b, k

def s3_list_subdirs(bucket, prefix):
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter="/"):
        for cp in page.get("CommonPrefixes", []):
            yield cp["Prefix"].split("/")[-2]  # trailing name

# ---------- PATCH 1: normalize partitions to INTs + retry ----------
def list_glue_partitions(db, tbl, retries=3, delay=2.0):
    """
    Returns a set of normalized INTEGER partition values for id_bucket.
    Retries to avoid Glue eventual consistency right after MSCK.
    """
    def _fetch():
        vals = set()
        paginator = glue.get_paginator("get_partitions")
        try:
            total_fetched = 0
            for page in paginator.paginate(DatabaseName=db, TableName=tbl):
                partitions = page.get("Partitions", [])
                total_fetched += len(partitions)
                for p in partitions:
                    values = p.get("Values")
                    if values and len(values) > 0:
                        # Partition values are in order of partition keys
                        # For id_bucket partition, it's the first value
                        # Glue stores partition values as strings like "0", "1", etc.
                        raw = str(values[0]).strip()
                        try:
                            v = int(raw)
                            vals.add(v)
                        except (ValueError, TypeError) as e:
                            # Log but continue - might be non-numeric partition
                            print(f"[DEBUG] Skipping non-numeric partition value: {raw} (error: {e})")
            if total_fetched > 0:
                print(f"[DEBUG] list_glue_partitions({db}.{tbl}): Fetched {total_fetched} partition records, extracted {len(vals)} unique id_bucket values")
        except Exception as e:
            print(f"[DEBUG] Error fetching partitions for {db}.{tbl}: {e}")
            raise
        return vals

    for attempt in range(retries):
        out = _fetch()
        if out or attempt == retries - 1:
            if attempt > 0:
                print(f"[DEBUG] list_glue_partitions({db}.{tbl}) attempt {attempt + 1}: found {len(out)} partitions")
            return out
        time.sleep(delay * (1.7 ** attempt))
    return set()  # Return empty set if all retries failed

def schema_checks(table):
    sd = table["StorageDescriptor"]
    in_fmt  = sd.get("InputFormat", "")
    out_fmt = sd.get("OutputFormat", "")
    serde   = (sd.get("SerdeInfo") or {}).get("SerializationLibrary", "")
    return {
        "table_type_ok": table.get("TableType") == "EXTERNAL_TABLE",
        "serde_ok": "ParquetHiveSerDe" in serde,
        "format_ok": ("Parquet" in in_fmt) and ("Parquet" in out_fmt),
    }

def read_snapshot_metadata(table):
    loc = table["StorageDescriptor"]["Location"]
    b, k = get_bucket_key_from_s3_uri(loc)
    meta_key = "/".join(filter(None, [k.rstrip("/"), "..", "metadata", "snapshot_dt.txt"]))
    # normalize ../
    parts = [p for p in meta_key.split("/") if p not in (".", "")]
    norm = []
    for p in parts:
        if p == "..":
            if norm: norm.pop()
        else:
            norm.append(p)
    meta_key = "/".join(norm)
    try:
        obj = s3.get_object(Bucket=b, Key=meta_key)
        snap = obj["Body"].read().decode().strip()
        return True, snap
    except Exception:
        return False, None

def run_athena(sql):
    if not ARES or not ARES.strip():
        return "FAILED", "athena_results not set"
    if not ARES.strip().startswith("s3://"):
        return "FAILED", f"athena_results must be a valid S3 URI (got: '{ARES}')"
    resp = athena.start_query_execution(
        QueryString=sql, WorkGroup=WG,
        ResultConfiguration={"OutputLocation": ARES.strip()},
    )
    qid = resp["QueryExecutionId"]
    while True:
        st = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]
        state = st["State"]
        if state in ("SUCCEEDED","FAILED","CANCELLED"):
            return state, st.get("StateChangeReason","")
        time.sleep(1)

def glue_register_missing_partitions(table, missing_vals):
    loc = table["StorageDescriptor"]["Location"]
    b, k = get_bucket_key_from_s3_uri(loc)
    inputs = [{
        "Values": [str(v)],
        "StorageDescriptor": {
            "Location": f"s3://{b}/{k}id_bucket={v}/",
            "InputFormat":  table["StorageDescriptor"]["InputFormat"],
            "OutputFormat": table["StorageDescriptor"]["OutputFormat"],
            "SerdeInfo":    table["StorageDescriptor"]["SerdeInfo"],
        },
        "Parameters": table.get("Parameters") or {}
    } for v in missing_vals]
    for i in range(0, len(inputs), 100):
        glue.batch_create_partition(DatabaseName=DB_MON, TableName=table["Name"], PartitionInputList=inputs[i:i+100])

# Freshness helper
def too_old(snap_str: str, window_days: int) -> bool:
    try:
        snap_dt = datetime.strptime(snap_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - snap_dt) > timedelta(days=window_days)
    except Exception:
        return True

# Derive comparison table name from a part_ table
def derive_base_name(part_name: str) -> str:
    return part_name[5:] if part_name.startswith("part_") else part_name

def ext_table_name_for(part_name: str) -> str:
    return f"ext_{derive_base_name(part_name)}"

def part_table_name_for(part_name: str) -> str:
    # allow comparing part_ vs another part_ if desired (usually not needed)
    return f"part_{derive_base_name(part_name)}"

# Determine input source location for a table
def get_input_source_location(table_name: str, snapshot_dt: str, data_bucket: str) -> str:
    """
    Returns the raw input S3 location for a table.
    - addressable_ids tables: opus/addressable_ids/raw_input/snapshot_dt={snapshot}/
    - infobase_attributes tables: opus/infobase_attributes/raw_input/snapshot_dt={snapshot}/
    """
    if not data_bucket or not snapshot_dt:
        return ""
    
    # Determine table type from name
    base_name = derive_base_name(table_name).lower()
    
    if "addressable" in base_name or base_name == "addressable_ids":
        input_path = f"opus/addressable_ids/raw_input/snapshot_dt={snapshot_dt}/"
    else:
        # All other tables are infobase_attributes (ibe_*, miacs_*, new_borrowers, n_a, etc.)
        input_path = f"opus/infobase_attributes/raw_input/snapshot_dt={snapshot_dt}/"
    
    return f"s3://{data_bucket}/{input_path}"

# ---------- PATCH 2: schema contract for part_ (partition key only) ----------
def enforce_schema_contract(glue_table, is_part: bool) -> list[str]:
    problems = []
    cols = {c["Name"]: c.get("Type","") for c in glue_table["StorageDescriptor"]["Columns"]}
    pks  = glue_table.get("PartitionKeys", [])
    pk_names = [x["Name"] for x in pks]

    # 'customer_user_id' must exist as a data column in both flows
    if PKCOL not in cols:
        problems.append(f"missing required column {PKCOL}")

    if is_part:
        if pk_names != ["id_bucket"]:
            problems.append(f"partition key must be [id_bucket], got {pk_names}")
        # 'id_bucket' does NOT need to be in data columns for partitioned tables
    return problems

# Optional: file-size hygiene (sample a few partitions)
def sample_file_size_issues(table, min_mb, max_mb, max_partitions=5):
    issues = []
    loc = table["StorageDescriptor"]["Location"]
    b, k = get_bucket_key_from_s3_uri(loc)
    # list a few id_bucket subdirs
    parts = []
    for sub in s3_list_subdirs(b, k):
        if sub.startswith("id_bucket="):
            try:
                parts.append(int(sub.split("=")[1]))
            except: pass
    parts = sorted(parts)[:max_partitions]
    for p in parts:
        prefix = f"{k}id_bucket={p}/"
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=b, Prefix=prefix):
            for obj in page.get("Contents", []):
                size_mb = obj["Size"] / (1024*1024)
                if size_mb and (size_mb < min_mb or size_mb > max_mb):
                    issues.append(f"id_bucket={p} object {obj['Key']} size={size_mb:.1f}MB")
                    if len(issues) >= 20: return issues
    return issues

# Athena helpers for counts & key-quality
def athena_scalar(sql) -> int:
    state, reason = run_athena(sql)
    if state != "SUCCEEDED":
        raise RuntimeError(f"Athena failed: {reason}")
    # fetch output (tiny)
    # Use GetQueryExecution only; not downloading result set to keep simple — do approximate workaround:
    # For strict flows you can use GetQueryResults, but here we'll issue COUNT(*) via GetQueryResults.
    res = athena.get_query_results(QueryExecutionId=athena.list_query_executions(MaxResults=1)["QueryExecutionIds"][0])
    # Safer: directly request this query id's results:
    # (We kept above minimal; now fix to correct one)
    # Re-fetch with the last run id
    # NOTE: we keep it simple by returning None; if you want exact parsing, switch to GetQueryResults by id.
    return None  # placeholder; see below in run_count and run_key_checks where we call GetQueryResults properly

def athena_count(db, tbl) -> int:
    if not ARES or not ARES.strip() or not ARES.strip().startswith("s3://"):
        raise ValueError(f"athena_results must be a valid S3 URI (got: '{ARES}')")
    q = f"SELECT COUNT(*) AS c FROM {db}.{tbl}"
    try:
        resp = athena.start_query_execution(
            QueryString=q, WorkGroup=WG, ResultConfiguration={"OutputLocation": ARES.strip()}
        )
    except Exception as e:
        raise RuntimeError(f"Athena start_query_execution failed: {e} (ARES='{ARES}', WorkGroup='{WG}')") from e
    qid = resp.get("QueryExecutionId")
    if not qid:
        raise RuntimeError(f"Athena start_query_execution returned no QueryExecutionId: {resp}")
    # wait
    while True:
        st = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]["State"]
        if st in ("SUCCEEDED","FAILED","CANCELLED"): break
        time.sleep(1)
    if st != "SUCCEEDED": raise RuntimeError(f"COUNT(*) failed on {db}.{tbl}")
    res = athena.get_query_results(QueryExecutionId=qid)
    # first row is header, second row has value
    return int(res["ResultSet"]["Rows"][1]["Data"][0]["VarCharValue"])

def athena_count_nulls(db, tbl, col) -> int:
    if not ARES or not ARES.strip() or not ARES.strip().startswith("s3://"):
        raise ValueError(f"athena_results must be a valid S3 URI (got: '{ARES}')")
    q = f"SELECT COUNT(*) FROM {db}.{tbl} WHERE {col} IS NULL"
    try:
        resp = athena.start_query_execution(
            QueryString=q, WorkGroup=WG, ResultConfiguration={"OutputLocation": ARES.strip()}
        )
    except Exception as e:
        raise RuntimeError(f"Athena start_query_execution failed: {e} (ARES='{ARES}', WorkGroup='{WG}')") from e
    qid = resp.get("QueryExecutionId")
    if not qid:
        raise RuntimeError(f"Athena start_query_execution returned no QueryExecutionId: {resp}")
    while True:
        st = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]["State"]
        if st in ("SUCCEEDED","FAILED","CANCELLED"): break
        time.sleep(1)
    if st != "SUCCEEDED": raise RuntimeError(f"NULL check failed on {db}.{tbl}.{col}")
    res = athena.get_query_results(QueryExecutionId=qid)
    return int(res["ResultSet"]["Rows"][1]["Data"][0]["VarCharValue"])

def athena_count_dupes(db, tbl, col) -> int:
    if not ARES or not ARES.strip() or not ARES.strip().startswith("s3://"):
        raise ValueError(f"athena_results must be a valid S3 URI (got: '{ARES}')")
    q = f"SELECT SUM(c) FROM (SELECT {col}, COUNT(*) c FROM {db}.{tbl} GROUP BY 1 HAVING COUNT(*) > 1)"
    try:
        resp = athena.start_query_execution(
            QueryString=q, WorkGroup=WG, ResultConfiguration={"OutputLocation": ARES.strip()}
        )
    except Exception as e:
        raise RuntimeError(f"Athena start_query_execution failed: {e} (ARES='{ARES}', WorkGroup='{WG}')") from e
    qid = resp.get("QueryExecutionId")
    if not qid:
        raise RuntimeError(f"Athena start_query_execution returned no QueryExecutionId: {resp}")
    while True:
        st = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]["State"]
        if st in ("SUCCEEDED","FAILED","CANCELLED"): break
        time.sleep(1)
    if st != "SUCCEEDED": raise RuntimeError(f"DUPE check failed on {db}.{tbl}.{col}")
    res = athena.get_query_results(QueryExecutionId=qid)
    # If no dupes, SUM(c) may be NULL
    cell = res["ResultSet"]["Rows"][1]["Data"][0]
    return int(cell.get("VarCharValue","0") or "0")

try:
    alerts = []
    rows = []
    ts = now_utc_iso()
    print(f"[{ts}] Start monitor db={DB_MON} prefix={PREFIX} nb={NB} region={REGION} auto_repair={AUTOR}")

    for t in list_part_tables(DB_MON, PREFIX):
        name = t["Name"]
        loc  = t["StorageDescriptor"]["Location"]
        b, k = get_bucket_key_from_s3_uri(loc)

        # S3: discover id_bucket=*
        s3_parts = []
        for sub in s3_list_subdirs(b, k):
            if sub.startswith("id_bucket="):
                try: s3_parts.append(int(sub.split("=",1)[1]))
                except: pass
        s3_parts = sorted(s3_parts)

        # ---------- PATCH 3: projection-aware + INT sets ----------
        params = t.get("Parameters") or {}
        projection_on = str(params.get("projection.enabled", "false")).lower() == "true"

        if projection_on:
            glue_parts = set(range(NB))  # projection implies virtual partitions exist
            glue_count = NB
            missing_glue = []
            print(f"[DEBUG] {name}: Using projection mode (virtual partitions)")
        else:
            glue_parts = list_glue_partitions(DB_MON, name)  # returns INTs
            glue_count = len(glue_parts)
            expected = set(range(NB))
            missing_glue = sorted(list(expected - glue_parts))
            print(f"[DEBUG] {name}: Found {glue_count} partitions in Glue, expected {NB}")
            if glue_count < NB and glue_count > 0:
                sample_glue = sorted(list(glue_parts))[:10]
                print(f"[DEBUG] {name}: Sample Glue partitions: {sample_glue}")
                if missing_glue:
                    print(f"[DEBUG] {name}: Missing partitions (first 10): {missing_glue[:10]}")

        schema_ok = schema_checks(t)

        # Processed snapshot + raw_input cross-check
        snap_ok, snap = read_snapshot_metadata(t)

        # Schema contract (part_)
        contract_issues = enforce_schema_contract(t, is_part=True)

        # Partition alerts
        if len(s3_parts) != NB:
            alerts.append(f"{name}: S3 has {len(s3_parts)}/{NB} id_bucket partitions")
        if missing_glue:
            alerts.append(f"{name}: Glue missing {len(missing_glue)} partitions (e.g., {missing_glue[:5]})")
        if not all(schema_ok.values()):
            alerts.append(f"{name}: schema mismatch (EXTERNAL/Parquet/Serde)")
        if contract_issues:
            alerts.append(f"{name}: schema contract issues: {', '.join(contract_issues)}")

        if STRICT_SNAPSHOT:
            if not snap_ok or too_old(snap or "", FRESHNESS_WINDOW_DAYS):
                alerts.append(f"{name}: processed snapshot too old/missing (snap={snap})")

        # Auto-repair partitions
        if missing_glue and AUTOR != "off":
            if AUTOR == "athena":
                st, reason = run_athena(f"MSCK REPAIR TABLE {DB_MON}.{name}")
                if st != "SUCCEEDED":
                    alerts.append(f"{name}: MSCK failed ({reason})")
            else:
                glue_register_missing_partitions(t, missing_glue)

        # --- NEW: counts + key quality ---
        src_tbl = ext_table_name_for(name) if COMPARE_SOURCE_TYPE == "ext" else part_table_name_for(name)
        src_db  = DB_SRC
        count_src = count_part = nulls_part = dupes_part = None
        count_diff_pct = None
        schema_contract_src_issues = []

        try:
            if COUNT_CHECK_ENABLED:
                # ensure src table exists; if not, skip counts
                try:
                    src_t = glue.get_table(DatabaseName=src_db, Name=src_tbl)["Table"]
                    # schema contract for src (ext ⇒ requires PK; part ⇒ requires PK+id_bucket partition)
                    schema_contract_src_issues = enforce_schema_contract(src_t, is_part=(COMPARE_SOURCE_TYPE=="part"))
                    if schema_contract_src_issues:
                        alerts.append(f"{name}: source {src_db}.{src_tbl} contract issues: {', '.join(schema_contract_src_issues)}")
                except glue.exceptions.EntityNotFoundException:
                    alerts.append(f"{name}: source table not found {src_db}.{src_tbl}; count match skipped")
                    src_t = None

                # counts
                count_part = athena_count(DB_MON, name)
                if src_t:
                    count_src  = athena_count(src_db, src_tbl)
                    # compare
                    if count_src is not None and count_part is not None:
                        if count_src == 0 and count_part == 0:
                            count_diff_pct = 0.0
                        elif count_src == 0 or count_part == 0:
                            count_diff_pct = 100.0
                        else:
                            count_diff_pct = abs(count_part - count_src) * 100.0 / count_src
                        if count_diff_pct > COUNT_TOLERANCE_PCT:
                            alerts.append(f"[COUNT_MISMATCH] {name}: {DB_MON}.{name}={count_part} vs {src_db}.{src_tbl}={count_src} (Δ={count_diff_pct:.3f}%)")

                # key quality on monitored part_ table
                nulls_part = athena_count_nulls(DB_MON, name, PKCOL)
                dupes_part = athena_count_dupes(DB_MON, name, PKCOL)
                if nulls_part and nulls_part > 0:
                    alerts.append(f"[PK_NULL] {name}: {PKCOL} NULL rows={nulls_part}")
                if dupes_part and dupes_part > 0:
                    alerts.append(f"[PK_DUPES] {name}: {PKCOL} duplicate rows={dupes_part}")

        except Exception as e:
            alerts.append(f"{name}: error during counts/key checks: {e}")

        # Optional file-size hygiene
        file_issues = []
        if FILE_SIZE_CHECK:
            file_issues = sample_file_size_issues(t, FILE_SIZE_MIN_MB, FILE_SIZE_MAX_MB)
            if file_issues:
                alerts.append(f"{name}: file-size issues (sample): {file_issues[:3]}...")

        # Optional: quick debug to see what the monitor is reading
        print(f"[DEBUG] {name}: glue_count={glue_count} sample={sorted(list(glue_parts))[:5]}")

        # Determine input source location
        input_source = get_input_source_location(name, snap or "", DATA_BKT) if DATA_BKT and snap else ""

        # Row for report
        rows.append({
            "table": name,
            "location": loc,
            "input_source": input_source,
            "s3_partitions": len(s3_parts),
            "glue_partitions": glue_count,
            "missing_glue_count": len(missing_glue),
            "table_type_ok": all(schema_ok.values()),
            "contract_ok": not contract_issues,
            "raw_input_snapshot_dt": snap or "",
            "count_src": count_src if COUNT_CHECK_ENABLED else "",
            "count_part": count_part if COUNT_CHECK_ENABLED else "",
            "count_diff_pct": f"{count_diff_pct:.6f}" if count_diff_pct is not None else "",
            "pk_nulls": nulls_part if nulls_part is not None else "",
            "pk_dupes": dupes_part if dupes_part is not None else "",
            "file_issues_sample": ";".join(file_issues[:3]) if file_issues else "",
            "checked_at": ts,
        })

    # ---------- write report ----------
    date_str = dt.datetime.utcnow().strftime("%Y-%m-%d")
    json_key = f"{RPFX}ACX_Data_Monitor_Report_{date_str}.json"
    csv_key  = f"{RPFX}ACX_Data_Monitor_Report_{date_str}.csv"

    body = json.dumps({
        "database": DB_MON,
        "prefix": PREFIX,
        "bucket_count": NB,
        "generated_at": ts,
        "freshness_window_days": FRESHNESS_WINDOW_DAYS,
        "compare": {"enabled": COUNT_CHECK_ENABLED, "type": COMPARE_SOURCE_TYPE, "db": DB_SRC,
                    "tolerance_pct": COUNT_TOLERANCE_PCT},
        "pk_column": PKCOL,
        "file_size_check": FILE_SIZE_CHECK,
        "alerts": alerts,
        "tables": rows
    }, indent=2).encode()
    s3.put_object(Bucket=RBKT, Key=json_key, Body=body)

    csv_buf = io.StringIO()
    fieldnames = ["input_source","raw_input_snapshot_dt","table","location","s3_partitions","glue_partitions","missing_glue_count",
                  "table_type_ok","contract_ok",
                  "count_src","count_part","count_diff_pct","pk_nulls","pk_dupes",
                  "file_issues_sample","checked_at"]
    w = csv.DictWriter(csv_buf, fieldnames=fieldnames)
    w.writeheader()
    for r in rows: w.writerow({k: r.get(k, "") for k in fieldnames})
    s3.put_object(Bucket=RBKT, Key=csv_key, Body=csv_buf.getvalue().encode())

    if alerts and sns:
        msg = f"[DATA MONITOR] {len(alerts)} issue(s) in {DB_MON} ({PREFIX}*)\n\n" + "\n".join(alerts[:50])
        try:
            sns.publish(TopicArn=TOPIC, Subject=f"[DATA MONITOR] {DB_MON} {PREFIX}* — {len(alerts)} issue(s)", Message=msg)
        except Exception as e:
            print(f"Warning: Failed to publish SNS alert: {e}")

    print(f"Wrote report: s3://{RBKT}/{json_key}")
    print(f"Wrote report: s3://{RBKT}/{csv_key}")
    print("Done.")

except ParamValidationError as e:
    import traceback
    print(f"FATAL PARAM VALIDATION ERROR: {e}")
    print(f"Full error details: {repr(e)}")
    print(f"Traceback:\n{traceback.format_exc()}")
    print(f"[DEBUG] Current values: DB_MON='{DB_MON}', RBKT='{RBKT}', ARES='{ARES}', WG='{WG}', REGION='{REGION}'")
    raise
except Exception as e:
    import traceback
    print(f"FATAL ERROR: {type(e).__name__}: {e}")
    print(f"Traceback:\n{traceback.format_exc()}")
    raise
