# Quick Reference Guide

## 🚀 Production Job Commands

### Run All Production Jobs
```bash
# Set AWS profile
export AWS_PROFILE=flywheel-prod

# 1. Process infobase_attributes data
aws glue start-job-run --job-name etl-omc-flywheel-prod-infobase-split-and-bucket

# 2. Process addressable_ids data  
aws glue start-job-run --job-name etl-omc-flywheel-prod-addressable-bucket

# 3. Register external tables
aws glue start-job-run --job-name etl-omc-flywheel-prod-register-staged-tables

# 4. Create Hive bucketed tables
aws glue start-job-run --job-name etl-omc-flywheel-prod-create-athena-bucketed-tables
```

### Run with Custom Parameters
```bash
# Process specific snapshot date
aws glue start-job-run --job-name etl-omc-flywheel-prod-infobase-split-and-bucket \
  --arguments '{"--SNAPSHOT_DT": "2025-10-22"}'

# Process specific tables only
aws glue start-job-run --job-name etl-omc-flywheel-prod-create-athena-bucketed-tables \
  --arguments '{"--TABLES_FILTER": "addressable_ids,ibe_01"}'
```

## 📊 Monitor Job Status

### Check Job Status
```bash
# Get job run status
aws glue get-job-run --job-name JOB_NAME --run-id RUN_ID

# List recent job runs
aws glue get-job-runs --job-name JOB_NAME --max-items 5
```

### View Logs
```bash
# CloudWatch logs location
/aws-glue/jobs/logs-v2/JOB_NAME/
```

## 🔧 Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--SNAPSHOT_DT` | `_NONE_` | Snapshot date (auto-discovery if `_NONE_`) |
| `--TABLES_FILTER` | `_NONE_` | Comma-separated table list |
| `--ENV` | `prod` | Environment (dev/prod) |
| `--SOURCE_PATH` | Required | Source S3 path |
| `--TARGET_PATH` | Required | Target S3 path |

## 📁 S3 Paths

### Production Data Paths
```
Source: s3://omc-flywheel-data-us-east-1-prod/opus/
├── infobase_attributes/raw_input/snapshot_dt=YYYY-MM-DD/
└── addressable_ids/raw_input/snapshot_dt=YYYY-MM-DD/

Target: s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/
├── split_cluster/
│   ├── infobase_attributes/
│   └── addressable_ids/
└── cleanroom_tables/bucketed/
```

### Glue Assets
```
Scripts: s3://aws-glue-assets-239083076653-us-east-1/scripts/
Temp: s3://aws-glue-assets-239083076653-us-east-1/temp/
Logs: s3://aws-glue-assets-239083076653-us-east-1/spark-event-logs/
```

## 🗄️ Database & Tables

### Glue Databases
- **Staged**: `omc_flywheel_prod` (external tables)
- **Final**: `omc_flywheel_prod` (bucketed tables)

### Table Naming
- **External Tables**: `ext_ibe_01`, `ext_ibe_04`, `ext_addressable_ids`
- **Bucketed Tables**: `ibe_01`, `ibe_04`, `addressable_ids`

## ⚡ Performance Tuning

### Job Configuration
- **Worker Type**: G.4X
- **Workers**: 10
- **Glue Version**: 5.0
- **Timeout**: 60 minutes

### File Sizing
- **Target**: 2 files per GB
- **Maximum**: 256 files per table
- **Compression**: Snappy

### Bucketing
- **Buckets**: 256
- **Key**: `customer_user_id`
- **Format**: Parquet

## 🚨 Troubleshooting

### Common Issues
1. **Permission Errors**: Check IAM role permissions
2. **Path Not Found**: Verify S3 paths and snapshot dates
3. **Column Errors**: Check column name case sensitivity
4. **Timeout**: Increase timeout or worker count

### Debug Commands
```bash
# Check job logs
aws logs describe-log-groups --log-group-name-prefix "/aws-glue/jobs/logs-v2/"

# Verify S3 access
aws s3 ls s3://omc-flywheel-data-us-east-1-prod/opus/

# Check Glue catalog
aws glue get-tables --database-name omc_flywheel_prod
```

## 📞 Support

### Documentation
- **Process Flow**: [docs/CURRENT_PROCESS_FLOW.md](docs/CURRENT_PROCESS_FLOW.md)
- **Run Sequence**: [docs/PRODUCTION_RUN_SEQUENCE.md](docs/PRODUCTION_RUN_SEQUENCE.md)
- **API Reference**: [docs/API_REFERENCE.md](docs/API_REFERENCE.md)

### Key Files
- **Scripts**: `scripts/etl-omc-flywheel-prod-*.py`
- **Documentation**: `docs/` directory
- **Configuration**: Job definitions in AWS Glue console

---

**Last Updated**: October 2025  
**Version**: Production Ready
