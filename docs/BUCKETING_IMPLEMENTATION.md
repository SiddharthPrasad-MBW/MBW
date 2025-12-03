# Bucketing Implementation for Cleanroom Performance Optimization

## Overview

This document outlines the implementation of data bucketing to optimize join performance in AWS Cleanroom. The solution creates 256-bucketed tables by `customer_user_id` for optimal join performance.

## Architecture

### Data Flow
1. **Source Data**: Original parquet files in `omc_cleanroom_data/cleanroom_tables/infobase_attributes/`
2. **Bucketing Process**: Creates logically bucketed parquet files with controlled file counts
3. **Athena Tables**: Creates true Hive bucketed tables using CTAS with `bucketed_by` and `bucket_count`
4. **Cleanroom Integration**: Bucketed tables are available for optimal join performance

### Key Components

#### 1. Bucketing Job (`etl-omc-flywheel-dev-infobase-attributes-comp-bucketing-improved`)
- **Purpose**: Creates bucketed parquet files with controlled file counts
- **Method**: `repartition(256, "customer_user_id")` + `coalesce(target_files)`
- **File Sizing**: Dynamic calculation based on source data size with clean number snapping
- **Output**: Parquet files in `bucketed_<table>/` directories

#### 2. Register Staged Tables Job (`etl-omc-flywheel-dev-register-staged-tables`)
- **Purpose**: Creates external tables in Glue catalog from S3 parquet files
- **Method**: Uses Glue API to create external tables with proper parquet format
- **Output**: Tables like `ext_ibe_01`, `ext_ibe_04`, etc. in Glue catalog

#### 3. Athena Bucketed Tables Job (`etl-omc-flywheel-dev-create-athena-bucketed-tables`)
- **Purpose**: Creates true Hive bucketed tables using Athena CTAS
- **Method**: `CREATE TABLE ... WITH (bucketed_by = ARRAY['customer_user_id'], bucket_count = 256)`
- **Output**: Tables like `ibe_01_bucketed`, `ibe_04_bucketed`, etc.

## Implementation Details

### File Sizing Strategy
```python
# Dynamic file sizing based on data size
def _target_mb_for_size_gb(size_gb: float) -> int:
    if size_gb >= 30:  return 380   # Very large
    if size_gb >= 20:  return 392   # Large  
    if size_gb >= 10:  return 490   # Medium
    return 400                      # Small

# Clean number snapping to preferred counts
PREFERRED = [24, 28, 32, 36, 48, 56, 64, 96, 112, 128]
```

### Bucketing Configuration
- **Bucket Count**: 256 buckets (optimal for 374M unique customer_user_ids)
- **Bucket Column**: `customer_user_id` (primary join key)
- **File Format**: Parquet with Snappy compression
- **Column Limit**: ≤100 columns for Athena performance

### Environment Configuration
```bash
# Dev Environment
ENV=dev
STAGED_DB=omc_flywheel_dev
FINAL_DB=omc_flywheel_dev
BUCKETED_BASE=s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/cleanroom_tables/bucketed/
ATHENA_RESULTS_S3=s3://omc-flywheel-dev-analysis-data/query-results/
```

## Jobs Created

### 1. Bucketing Job
- **Name**: `etl-omc-flywheel-dev-infobase-attributes-comp-bucketing-improved`
- **Worker Type**: G.4X with 24 workers
- **Timeout**: 2880 minutes
- **Status**: ✅ Completed successfully (9.5 minutes)

### 2. Register Staged Tables Job  
- **Name**: `etl-omc-flywheel-dev-register-staged-tables`
- **Worker Type**: G.1X with 2 workers
- **Timeout**: 60 minutes
- **Status**: ✅ Ready to run

### 3. Athena Bucketed Tables Job
- **Name**: `etl-omc-flywheel-dev-create-athena-bucketed-tables`
- **Worker Type**: G.1X with 2 workers
- **Timeout**: 60 minutes
- **Status**: ✅ Ready to run

## Tables Processed

### All 27 Tables
- **addressable_ids** (1 table)
- **infobase_attributes** (26 tables): IBE_01, IBE_02, IBE_03, IBE_03_A, IBE_04, IBE_04_A, IBE_05, IBE_05_A, IBE_06, IBE_06_A, IBE_08, IBE_09, MIACS_01, MIACS_01_A, MIACS_02, MIACS_02_A, MIACS_02_B, MIACS_03, MIACS_03_A, MIACS_03_B, MIACS_04, NEW_BORROWERS, N_A, N_A_A

## IAM Permissions

### Glue Role Permissions Added
```json
{
  "Sid": "AthenaAccess",
  "Effect": "Allow", 
  "Action": [
    "athena:StartQueryExecution",
    "athena:GetQueryExecution", 
    "athena:GetQueryResults",
    "athena:StopQueryExecution",
    "athena:GetWorkGroup",
    "athena:ListWorkGroups"
  ],
  "Resource": "*"
},
{
  "Sid": "GlueCatalogAccess",
  "Effect": "Allow",
  "Action": [
    "glue:GetTable",
    "glue:GetDatabase", 
    "glue:GetPartitions",
    "glue:CreateTable",
    "glue:UpdateTable",
    "glue:DeleteTable"
  ],
  "Resource": "*"
}
```

## Next Steps

### Immediate (Tomorrow)
1. **Run Register Staged Tables Job**: Create external tables in Glue catalog
2. **Run Athena Bucketed Tables Job**: Create true Hive bucketed tables
3. **Validate Results**: Check table creation and bucketing metadata

### Future
1. **Production Deployment**: Deploy to production environment
2. **Performance Testing**: Validate join performance improvements in Cleanroom
3. **Monitoring**: Set up monitoring for bucketed table maintenance

## Performance Benefits

### Expected Improvements
- **Join Performance**: 256 buckets provide optimal distribution for joins
- **Query Speed**: Bucketed tables eliminate shuffle operations for joins on `customer_user_id`
- **Cleanroom Optimization**: Direct bucket-to-bucket joins instead of full table scans
- **Scalability**: Consistent performance regardless of table size

### File Count Optimization
- **Dynamic Sizing**: File counts based on actual data size
- **Clean Numbers**: Snapped to preferred file counts (24, 28, 32, 36, etc.)
- **Size Control**: Target ~400-500MB per file for optimal performance

## Troubleshooting

### Common Issues
1. **Missing Source Tables**: Ensure register-staged-tables job runs first
2. **IAM Permissions**: Verify Athena and Glue catalog permissions
3. **S3 Paths**: Check S3 bucket permissions and paths
4. **File Count Issues**: Monitor `maxRecordsPerFile` settings

### Debug Commands
```bash
# Check job status
aws glue get-job-run --job-name <job-name> --run-id <run-id>

# Check logs
aws logs get-log-events --log-group-name "/aws-glue/jobs/output" --log-stream-name <stream-name>

# Verify tables
aws athena start-query-execution --query-string "SHOW TABLES IN omc_flywheel_dev"
```

## Files Created

### Scripts
- `scripts/etl-omc-flywheel-dev-infobase-attributes-comp-bucketing-improved.py`
- `scripts/register-staged-tables.py` 
- `scripts/create-athena-bucketed-tables.py`

### Documentation
- `docs/BUCKETING_IMPLEMENTATION.md` (this file)

## Status Summary

✅ **Completed**:
- Bucketing job implementation and testing
- IAM permissions configuration
- All Glue jobs created and configured
- Environment setup complete

🔄 **Pending**:
- Register staged tables execution
- Athena bucketed tables creation
- Production deployment
- Performance validation

---

**Last Updated**: October 21, 2025  
**Environment**: Dev  
**Status**: Ready for testing
