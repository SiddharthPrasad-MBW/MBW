# Database Refresh Automation Guide

## Overview

This guide covers the automation tools for the 7-step database refresh process. The automation handles the complete partitioned tables pipeline from data splitting through reporting.

## 7-Step Process

The database refresh consists of 7 sequential steps:

1. **Addressable IDs Split and Part** - Processes addressable IDs data into partitioned format
2. **Infobase Split and Part** - Processes infobase attributes data into partitioned format
   - *Note: Steps 1 and 2 can run in parallel*
3. **Register Part Tables** - Creates initial Glue table definitions for `part_*` tables
   - *Note: This step runs **twice in parallel** with different S3_ROOT parameters:*
     - `addressable_ids` context: `split_part/addressable_ids/`
     - `infobase_attributes` context: `split_part/infobase_attributes/`
4. **Prepare Part Tables** - Ensures partitioning and runs `MSCK REPAIR TABLE`
5. **Create Part Addressable IDs ER Table** - Creates Entity Resolution table
6. **Generate Data Monitor Report** - Data quality monitoring report
7. **Generate Cleanrooms Report** - Cleanrooms status and configuration report

## Automation Tools

### 1. Bash Scripts (Simple & Direct)

#### Dev Environment: `scripts/run-dev-db-refresh.sh`

```bash
# Basic usage
./scripts/run-dev-db-refresh.sh

# Dry run (preview without executing)
./scripts/run-dev-db-refresh.sh --dry-run

# Skip specific steps
./scripts/run-dev-db-refresh.sh --skip-steps=1,2

# Specify snapshot date
./scripts/run-dev-db-refresh.sh --snapshot-dt=2025-01-15

# Combine options
./scripts/run-dev-db-refresh.sh --dry-run --skip-steps=6,7
```

#### Production Environment: `scripts/run-prod-db-refresh.sh`

```bash
# Set AWS profile
export AWS_PROFILE=flywheel-prod

# Basic usage
./scripts/run-prod-db-refresh.sh

# Dry run
./scripts/run-prod-db-refresh.sh --dry-run

# Skip steps
./scripts/run-prod-db-refresh.sh --skip-steps=1,2

# Specify snapshot date
./scripts/run-prod-db-refresh.sh --snapshot-dt=2025-01-15
```

**Features:**
- ✅ Simple bash script, easy to understand
- ✅ Color-coded output for easy reading
- ✅ Parallel execution for steps 1 & 2
- ✅ Automatic job status monitoring
- ✅ Error handling with detailed error messages
- ✅ Dry-run mode for testing
- ✅ Skip specific steps for partial runs

### 2. Python Orchestrator (Advanced & Robust)

The Python orchestrator provides better error handling, logging, and programmatic control.

#### Usage

```bash
# Dev environment
python3 scripts/orchestrate-db-refresh.py --env dev

# Production environment
python3 scripts/orchestrate-db-refresh.py --env prod

# Dry run
python3 scripts/orchestrate-db-refresh.py --env dev --dry-run

# Skip steps
python3 scripts/orchestrate-db-refresh.py --env dev --skip-steps 1,2

# Specify snapshot date
python3 scripts/orchestrate-db-refresh.py --env prod --snapshot-dt 2025-01-15

# Custom AWS profile
python3 scripts/orchestrate-db-refresh.py --env dev --aws-profile my-profile

# Custom region
python3 scripts/orchestrate-db-refresh.py --env prod --region us-west-2
```

**Features:**
- ✅ Better error handling and recovery
- ✅ Structured logging
- ✅ Programmatic control (can be imported as a module)
- ✅ More detailed status reporting
- ✅ Better integration with AWS SDK
- ✅ Extensible for future enhancements

## Job Names by Environment

### Dev Environment

1. `etl-omc-flywheel-dev-addressable-split-and-part`
2. `etl-omc-flywheel-dev-infobase-split-and-part`
3. `etl-omc-flywheel-dev-register-part-tables`
4. `etl-omc-flywheel-dev-prepare-part-tables`
5. `etl-omc-flywheel-dev-create-part-addressable-ids-er-table`
6. `etl-omc-flywheel-dev-generate-data-monitor-report`
7. `etl-omc-flywheel-dev-generate-cleanrooms-report`

### Production Environment

1. `etl-omc-flywheel-prod-addressable-split-and-part`
2. `etl-omc-flywheel-prod-infobase-split-and-part`
3. `etl-omc-flywheel-prod-register-part-tables`
4. `etl-omc-flywheel-prod-prepare-part-tables`
5. `etl-omc-flywheel-prod-create-part-addressable-ids-er-table`
6. `etl-omc-flywheel-prod-generate-data-monitor-report`
7. `etl-omc-flywheel-prod-generate-cleanrooms-report`

## Common Use Cases

### 1. Full Refresh (All Steps)

```bash
# Dev
./scripts/run-dev-db-refresh.sh

# Prod
export AWS_PROFILE=flywheel-prod
./scripts/run-prod-db-refresh.sh
```

### 2. Re-run After Failure (Skip Completed Steps)

If steps 1-3 completed successfully but step 4 failed:

```bash
# Dev - Skip steps 1, 2, 3
./scripts/run-dev-db-refresh.sh --skip-steps=1,2,3

# Prod - Skip steps 1, 2, 3
./scripts/run-prod-db-refresh.sh --skip-steps=1,2,3
```

### 3. Process Specific Snapshot Date

```bash
# Dev
./scripts/run-dev-db-refresh.sh --snapshot-dt=2025-01-15

# Prod
./scripts/run-prod-db-refresh.sh --snapshot-dt=2025-01-15
```

### 4. Testing (Dry Run)

```bash
# Dev - Preview what would run
./scripts/run-dev-db-refresh.sh --dry-run

# Prod - Preview what would run
./scripts/run-prod-db-refresh.sh --dry-run
```

### 5. Reporting Only (Skip Data Processing)

```bash
# Dev - Only run reporting steps
./scripts/run-dev-db-refresh.sh --skip-steps=1,2,3,4,5

# Prod - Only run reporting steps
./scripts/run-prod-db-refresh.sh --skip-steps=1,2,3,4,5
```

## Monitoring

### During Execution

Both scripts provide real-time status updates:
- ✅ Job start confirmation with Run ID
- ⏳ Progress updates every 30 seconds
- ❌ Detailed error messages on failure
- ⏱️ Total execution time

### After Execution

#### Check Job Status Manually

```bash
# Get job run details
aws glue get-job-run --job-name JOB_NAME --run-id RUN_ID --profile flywheel-dev

# List recent job runs
aws glue get-job-runs --job-name JOB_NAME --max-items 5 --profile flywheel-dev
```

#### View CloudWatch Logs

```bash
# List log groups
aws logs describe-log-groups --log-group-name-prefix "/aws-glue/jobs" --profile flywheel-dev

# View logs
aws logs tail /aws-glue/jobs/logs-v2/JOB_NAME --follow --profile flywheel-dev
```

#### Verify Output

**Dev Environment:**
- Data: `s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_part/`
- Data Monitor Report: `s3://omc-flywheel-dev-analysis-data/data-monitor-reports/`
- Cleanrooms Report: `s3://omc-flywheel-dev-analysis-data/cleanrooms-reports/`
- Glue Database: `omc_flywheel_dev_clean`

**Production Environment:**
- Data: `s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_part/`
- Data Monitor Report: `s3://omc-flywheel-prod-analysis-data/data-monitor-reports/`
- Cleanrooms Report: `s3://omc-flywheel-prod-analysis-data/cleanrooms-reports/`
- Glue Database: `omc_flywheel_prod`

## Error Handling

### Automatic Error Detection

Both scripts automatically detect and report:
- ❌ Job failures (FAILED, ERROR, TIMEOUT states)
- ❌ Job timeouts (exceeds max wait time)
- ❌ Missing jobs (job not found in Glue)
- ❌ AWS API errors

### Error Recovery

If a step fails:

1. **Check the error message** - The script will display detailed error information
2. **Review CloudWatch logs** - Get full stack traces and detailed logs
3. **Fix the issue** - Address the root cause
4. **Re-run from failed step** - Use `--skip-steps` to skip completed steps

Example recovery:

```bash
# Step 4 failed, steps 1-3 completed successfully
# Fix the issue, then re-run from step 4:

./scripts/run-dev-db-refresh.sh --skip-steps=1,2,3
```

## Timeouts

Default timeouts per step:

| Step | Job | Default Timeout |
|------|-----|----------------|
| 1 | addressable-split-and-part | 60 minutes (3600s) |
| 2 | infobase-split-and-part | 60 minutes (3600s) |
| 3 | register-part-tables | 30 minutes (1800s) |
| 4 | prepare-part-tables | 30 minutes (1800s) |
| 5 | create-part-addressable-ids-er-table | 30 minutes (1800s) |
| 6 | generate-data-monitor-report | 10 minutes (600s) |
| 7 | generate-cleanrooms-report | 10 minutes (600s) |

**Total Expected Duration:** ~2-3 hours (depending on data size)

## Prerequisites

### AWS Credentials

Ensure AWS credentials are configured:

```bash
# Dev
export AWS_PROFILE=flywheel-dev

# Prod
export AWS_PROFILE=flywheel-prod

# Verify
aws sts get-caller-identity
```

### Required Permissions

The AWS profile/role must have:
- `glue:GetJob` - Read job configurations
- `glue:StartJobRun` - Start job executions
- `glue:GetJobRun` - Check job status
- `logs:DescribeLogGroups` - Access CloudWatch logs
- `logs:GetLogEvents` - Read job logs

### Python Dependencies (for orchestrator)

```bash
pip install boto3
```

## Best Practices

### 1. Always Test in Dev First

```bash
# Test in dev
./scripts/run-dev-db-refresh.sh --dry-run

# Then run for real
./scripts/run-dev-db-refresh.sh
```

### 2. Use Dry Run for Validation

Before running in production, use dry-run to verify:
- ✅ All jobs exist
- ✅ Correct job names
- ✅ Proper configuration

```bash
./scripts/run-prod-db-refresh.sh --dry-run
```

### 3. Monitor First Run

For the first automated run, monitor closely:
- Watch CloudWatch logs
- Verify S3 outputs
- Check Glue tables

### 4. Document Custom Runs

If you skip steps or use custom parameters, document why:
- Which steps were skipped
- What snapshot date was used
- Any issues encountered

### 5. Schedule Regular Runs

Consider scheduling monthly runs:
- Use EventBridge rules (future enhancement)
- Or cron jobs on a scheduler
- Document the schedule

## Troubleshooting

### Job Not Found

**Error:** `Job not found: etl-omc-flywheel-dev-xxx`

**Solution:**
- Verify the job exists: `aws glue list-jobs --profile flywheel-dev`
- Check environment matches (dev vs prod)
- Ensure Terraform has been applied

### Job Timeout

**Error:** `Job timed out after X seconds`

**Solution:**
- Check CloudWatch logs for actual job status
- Job may still be running (check manually)
- Increase timeout if needed (modify script)

### Permission Errors

**Error:** `AccessDenied` or permission errors

**Solution:**
- Verify AWS profile has required permissions
- Check IAM role permissions
- Ensure correct profile is set

### Parallel Jobs Not Starting

**Issue:** Steps 1 & 2 not running in parallel

**Solution:**
- Check if both jobs exist
- Verify AWS API limits
- Check for concurrent execution limits

## Future Enhancements

### EventBridge Automation (Planned)

- Scheduled monthly runs
- Automatic retry on failure
- SNS notifications on completion/failure

### Step Functions (Planned)

- Visual workflow representation
- Better error recovery
- Parallel execution with dependencies

### Enhanced Logging

- Structured JSON logs
- Integration with CloudWatch Insights
- Performance metrics tracking

## Related Documentation

- [Production Run Sequence](./PRODUCTION_RUN_SEQUENCE.md) - Detailed step-by-step guide
- [Current Process Flow](./CURRENT_PROCESS_FLOW.md) - Overall architecture
- [Dev Setup Guide](./DEV_SETUP_AND_VALIDATION.md) - Dev environment setup

---

**Last Updated:** 2025-01-XX  
**Version:** 1.0

