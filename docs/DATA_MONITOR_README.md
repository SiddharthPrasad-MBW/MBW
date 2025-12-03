# Data Monitor ETL Job

## Overview

The Data Monitor is a Glue Python Shell job that monitors S3/Glue tables used by AWS Cleanrooms. It performs comprehensive data quality checks, partition integrity validation, and schema compliance verification for all `part_*` tables in the specified database.

## Purpose

The Data Monitor ensures that:
- All partitioned tables have complete partition coverage (256 `id_bucket` partitions)
- Data is fresh and up-to-date
- Schema contracts are enforced
- Record counts match between source and target tables
- Primary key integrity is maintained (no NULLs or duplicates)
- Tables are ready for Cleanrooms analysis

## What It Tracks

### 1. **Partition Integrity**

#### S3 Partition Discovery
- Scans S3 bucket structure to discover all `id_bucket=*` partitions
- Validates that all 256 partitions (0-255) exist on S3
- Alerts if any partitions are missing

#### Glue Catalog Partition Registration
- Verifies all 256 partitions are registered in Glue Data Catalog
- Identifies missing partitions that exist on S3 but aren't in Glue
- Supports partition projection mode (virtual partitions)

#### Auto-Repair Capabilities
- **Athena MSCK REPAIR** (default): Runs `MSCK REPAIR TABLE` to auto-register missing partitions
- **Glue API**: Directly registers missing partitions via Glue API
- **Off**: Disabled (only reports issues)

### 2. **Data Freshness**

#### Snapshot Metadata Validation
- Reads `snapshot_dt.txt` from S3 metadata location
- Validates snapshot date format and presence
- Cross-checks with raw input data freshness

#### Freshness Window
- Default window: **45 days**
- Alerts if snapshot is older than configured window
- Strict mode: Can enforce snapshot presence and recency

**Configuration:**
- `--freshness_window_days`: Number of days before snapshot is considered stale
- `--strict_snapshot`: Enforce strict snapshot validation (default: `true`)

### 3. **Schema Validation**

#### Table Type & Format Checks
- **Table Type**: Verifies `EXTERNAL_TABLE` type
- **Format**: Validates Parquet format
- **SerDe**: Checks Parquet SerDe configuration

#### Schema Contract Enforcement
For `part_*` tables, enforces:
- ✅ `customer_user_id` must exist as a **data column**
- ✅ `id_bucket` must be the **partition key** (INT type)
- ✅ Table must be `EXTERNAL_TABLE` with Parquet format

**Alerts Generated:**
- Missing required columns
- Incorrect partition key configuration
- Wrong table type or format

### 4. **Record Count Matching**

#### Source Comparison
- Compares `part_*` table record counts against source table
- Default source: `ext_*` tables (e.g., `part_ibe_01` vs `ext_ibe_01`)
- Can compare against other `part_*` tables if configured

#### Tolerance Configuration
- **Default tolerance**: `0%` (exact match required)
- Configurable via `--count_tolerance_pct`
- Calculates percentage difference: `|count_part - count_src| * 100 / count_src`

#### Count Checks
```sql
-- Example queries run:
SELECT COUNT(*) FROM omc_flywheel_prod.part_ibe_01;
SELECT COUNT(*) FROM omc_flywheel_prod.ext_ibe_01;
```

**Alerts Generated:**
- `[COUNT_MISMATCH]` when counts differ beyond tolerance
- Includes actual counts and percentage difference

**Configuration:**
- `--count_check_enabled`: Enable/disable count checks (default: `true`)
- `--compare_source_type`: Source type (`ext` or `part`, default: `ext`)
- `--compare_database`: Database for source tables (default: same as monitored DB)
- `--count_tolerance_pct`: Allowed percentage difference (default: `0.0`)

### 5. **Primary Key Quality**

#### NULL Checks
- Counts rows where `customer_user_id` IS NULL
- Ensures primary key integrity

**Query:**
```sql
SELECT COUNT(*) FROM omc_flywheel_prod.part_ibe_01 
WHERE customer_user_id IS NULL;
```

#### Duplicate Checks
- Counts duplicate `customer_user_id` values
- Ensures uniqueness constraint

**Query:**
```sql
SELECT SUM(c) FROM (
  SELECT customer_user_id, COUNT(*) c 
  FROM omc_flywheel_prod.part_ibe_01 
  GROUP BY customer_user_id 
  HAVING COUNT(*) > 1
);
```

**Alerts Generated:**
- `[PK_NULL]`: When NULL values found in primary key
- `[PK_DUPES]`: When duplicate primary key values found

**Configuration:**
- `--pk_column`: Primary key column name (default: `customer_user_id`)

### 6. **File Size Hygiene** (Optional)

#### Size Validation
- Samples files from up to 5 partitions
- Validates file sizes are within configured range
- Reports issues for files outside acceptable range

**Configuration:**
- `--file_size_check`: Enable/disable file size checks (default: `false`)
- `--file_size_min_mb`: Minimum file size in MB (default: `64`)
- `--file_size_max_mb`: Maximum file size in MB (default: `1024`)

**Alerts Generated:**
- File size issues (sample of first 20 issues found)

### 7. **Partition Projection Support**

#### Virtual Partitions
- Detects if table uses partition projection
- Handles projection mode where partitions are virtual
- Validates projection configuration

## Configuration Parameters

### Required Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `--database` | Glue database name | `omc_flywheel_prod` |
| `--report_bucket` | S3 bucket for reports | `omc-flywheel-prod-analysis-data` |
| `--athena_results` | S3 URI for Athena query results | `s3://bucket/query-results/` |

### Optional Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--region` | AWS region | `us-east-1` |
| `--table_prefix` | Table prefix to monitor | `part_` |
| `--bucket_count` | Expected number of partitions | `256` |
| `--report_prefix` | S3 prefix for reports | `data-monitor/` |
| `--sns_topic_arn` | SNS topic for alerts | (none) |
| `--auto_repair` | Auto-repair mode | `athena` |
| `--athena_workgroup` | Athena workgroup | `primary` |
| `--strict_snapshot` | Strict snapshot validation | `true` |
| `--freshness_window_days` | Freshness window in days | `45` |
| `--count_check_enabled` | Enable count checks | `true` |
| `--compare_source_type` | Source type for comparison | `ext` |
| `--compare_database` | Database for source tables | (same as monitored) |
| `--count_tolerance_pct` | Count difference tolerance | `0.0` |
| `--pk_column` | Primary key column name | `customer_user_id` |
| `--file_size_check` | Enable file size checks | `false` |
| `--file_size_min_mb` | Minimum file size (MB) | `64` |
| `--file_size_max_mb` | Maximum file size (MB) | `1024` |
| `--max_tables` | Maximum tables to process | `0` (unlimited) |

## Outputs

### JSON Report

**Location:** `s3://{report_bucket}/{report_prefix}omc_monitor_report_{date}.json`

**Structure:**
```json
{
  "database": "omc_flywheel_prod",
  "prefix": "part_",
  "bucket_count": 256,
  "generated_at": "2025-01-15T10:30:00Z",
  "freshness_window_days": 45,
  "compare": {
    "enabled": true,
    "type": "ext",
    "db": "omc_flywheel_prod",
    "tolerance_pct": 0.0
  },
  "pk_column": "customer_user_id",
  "file_size_check": false,
  "alerts": [
    "[COUNT_MISMATCH] part_ibe_01: count mismatch...",
    "[PK_NULL] part_ibe_02: customer_user_id NULL rows=5"
  ],
  "tables": [
    {
      "table": "part_ibe_01",
      "location": "s3://bucket/path/",
      "s3_partitions": 256,
      "glue_partitions": 256,
      "missing_glue_count": 0,
      "table_type_ok": true,
      "contract_ok": true,
      "raw_input_snapshot_dt": "2025-01-10",
      "count_src": 1000000,
      "count_part": 1000000,
      "count_diff_pct": "0.000000",
      "pk_nulls": 0,
      "pk_dupes": 0,
      "file_issues_sample": "",
      "checked_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

### CSV Report

**Location:** `s3://{report_bucket}/{report_prefix}omc_monitor_report_{date}.csv`

**Columns:**
- `table` - Table name
- `location` - S3 location
- `s3_partitions` - Number of partitions found on S3
- `glue_partitions` - Number of partitions registered in Glue
- `missing_glue_count` - Number of missing Glue partitions
- `table_type_ok` - Schema validation passed
- `contract_ok` - Schema contract validation passed
- `raw_input_snapshot_dt` - Snapshot date from metadata
- `count_src` - Record count from source table
- `count_part` - Record count from part table
- `count_diff_pct` - Percentage difference in counts
- `pk_nulls` - Number of NULL primary keys
- `pk_dupes` - Number of duplicate primary keys
- `file_issues_sample` - Sample file size issues
- `checked_at` - Timestamp of check

### SNS Alerts

**Topic:** Configured via `--sns_topic_arn`

**Format:**
```
Subject: [DATA MONITOR] omc_flywheel_prod part_* — 3 issue(s)

Message:
[DATA MONITOR] 3 issue(s) in omc_flywheel_prod (part_*)

[COUNT_MISMATCH] part_ibe_01: omc_flywheel_prod.part_ibe_01=999950 vs omc_flywheel_prod.ext_ibe_01=1000000 (Δ=0.005000%)
[PK_NULL] part_ibe_02: customer_user_id NULL rows=5
[PK_DUPES] part_ibe_03: customer_user_id duplicate rows=10
```

## Current Production Configuration

Based on Terraform configuration in `infra/modules/monitoring/main.tf`:

```hcl
--database: omc_flywheel_prod
--table_prefix: part_
--bucket_count: 256
--report_bucket: omc-flywheel-prod-analysis-data
--report_prefix: data-monitor/
--sns_topic_arn: (configured SNS topic)
--auto_repair: athena
--athena_workgroup: primary
--athena_results: s3://omc-flywheel-prod-analysis-data/query-results/monitor/
--strict_snapshot: true
--freshness_window_days: 45
--count_check_enabled: true
--compare_source_type: ext
--compare_database: omc_flywheel_prod
--count_tolerance_pct: 0
--pk_column: customer_user_id
--file_size_check: false
```

## Alert Types

| Alert Type | Description | Severity |
|------------|-------------|----------|
| `[COUNT_MISMATCH]` | Record count differs between source and target | High |
| `[PK_NULL]` | NULL values found in primary key column | High |
| `[PK_DUPES]` | Duplicate values found in primary key column | High |
| Partition alerts | Missing partitions on S3 or in Glue | Medium |
| Schema alerts | Schema contract violations | Medium |
| Freshness alerts | Snapshot too old or missing | Medium |
| File size alerts | Files outside acceptable size range | Low |

## Usage Examples

### Manual Execution

```bash
# Run with default settings
aws glue start-job-run \
  --job-name omc-flywheel-prod-data-monitor \
  --profile flywheel-prod

# Run with custom parameters
aws glue start-job-run \
  --job-name omc-flywheel-prod-data-monitor \
  --arguments '{
    "--database": "omc_flywheel_prod",
    "--table_prefix": "part_",
    "--bucket_count": "256",
    "--report_bucket": "omc-flywheel-prod-analysis-data",
    "--count_check_enabled": "true",
    "--count_tolerance_pct": "0.1"
  }' \
  --profile flywheel-prod
```

### Viewing Reports

```bash
# List recent reports
aws s3 ls s3://omc-flywheel-prod-analysis-data/data-monitor/ \
  --profile flywheel-prod

# Download latest JSON report
aws s3 cp s3://omc-flywheel-prod-analysis-data/data-monitor/omc_monitor_report_2025-01-15.json . \
  --profile flywheel-prod

# View in jq
cat omc_monitor_report_2025-01-15.json | jq '.alerts'
```

## Troubleshooting

### Common Issues

#### 1. Missing Partitions
**Symptom:** `[ALERT] part_ibe_01: Glue missing 10 partitions`

**Solution:**
- Check if auto-repair is enabled (`--auto_repair=athena`)
- Manually run: `MSCK REPAIR TABLE omc_flywheel_prod.part_ibe_01`
- Verify S3 data exists for missing partitions

#### 2. Count Mismatch
**Symptom:** `[COUNT_MISMATCH] part_ibe_01: count mismatch`

**Solution:**
- Verify source table (`ext_ibe_01`) has correct data
- Check for data processing errors in ETL jobs
- Review partition coverage (missing partitions = missing data)

#### 3. Primary Key Issues
**Symptom:** `[PK_NULL]` or `[PK_DUPES]` alerts

**Solution:**
- Review ETL job logic for primary key handling
- Check source data quality
- Verify deduplication logic in split-and-part jobs

#### 4. Freshness Alerts
**Symptom:** `processed snapshot too old/missing`

**Solution:**
- Check if ETL jobs are running successfully
- Verify `snapshot_dt.txt` is being written to S3
- Review freshness window configuration

## Best Practices

1. **Schedule Regular Runs**: Run data monitor daily or after each ETL job execution
2. **Monitor Alerts**: Set up CloudWatch alarms on SNS topic for critical alerts
3. **Review Reports**: Regularly review CSV reports for trends and patterns
4. **Adjust Tolerance**: Set appropriate `count_tolerance_pct` based on business requirements
5. **Enable Auto-Repair**: Use `--auto_repair=athena` to automatically fix partition issues
6. **File Size Checks**: Enable `--file_size_check` if file size optimization is important

## Related Documentation

- [Production Run Sequence](PRODUCTION_RUN_SEQUENCE.md)
- [Operations Guide](OPERATIONS_GUIDE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)

---

**Last Updated:** January 2025  
**Maintainer:** Data Engineering Team

