# Dev Environment Quick Start

## Quick Setup for Dev Validation

This guide provides the fastest path to get dev running and validate production processes.

## Prerequisites Check

```bash
# 1. Verify AWS access
aws sts get-caller-identity --profile flywheel-dev

# 2. Verify Terraform
terraform version

# 3. Check required resources exist
aws s3 ls s3://omc-flywheel-data-us-east-1-dev/ --profile flywheel-dev
aws glue get-database --name omc_flywheel_dev --profile flywheel-dev
```

## Step 1: Setup Dev Scripts

```bash
# Run the setup script to create and upload dev scripts
cd /Users/patrick.spann/Documents/acx_omc_flywheel_cr
./scripts/setup-dev-scripts.sh
```

This script will:
- ✅ Create dev versions of all production scripts
- ✅ Replace hardcoded 'prod' with 'dev' in scripts
- ✅ Upload scripts to dev Glue assets bucket

## Step 2: Deploy Infrastructure

### 2.1 Deploy Glue Jobs

```bash
# Navigate to dev stack
cd infra/stacks/dev-gluejobs

# Initialize Terraform
terraform init

# Review what will be created
terraform plan

# Apply (creates Glue jobs with dev naming)
terraform apply
```

**Expected Output:**
- Jobs created: `etl-omc-flywheel-dev-*`
- IAM policies: `omc-flywheel-dev-glue-role-*`
- Crawlers: `crw-omc-flywheel-dev-*`
- All jobs reference dev scripts
- Environment-aware configuration

### 2.2 Deploy Monitoring (Optional but Recommended)

```bash
# Navigate to monitoring stack
cd infra/stacks/dev-monitoring

# Initialize Terraform
terraform init

# Review what will be created
terraform plan

# Apply (creates monitoring job and resources)
terraform apply
```

**Expected Output:**
- Monitoring job: `etl-omc-flywheel-dev-generate-data-monitor-report`
- Monitoring role: `omc-flywheel-dev-data-monitor-role`
- SNS topic: `omc-flywheel-dev-data-monitor-alerts`
- CloudWatch dashboard and log group

## Step 3: Run Validation Pipeline

### Option A: Bucketed Pipeline (Production Process)

```bash
export AWS_PROFILE=flywheel-dev

# Run in sequence
aws glue start-job-run --job-name etl-omc-flywheel-dev-infobase-split-and-bucket
# Wait for completion, check status:
aws glue get-job-run --job-name etl-omc-flywheel-dev-infobase-split-and-bucket --run-id <run-id>

aws glue start-job-run --job-name etl-omc-flywheel-dev-addressable-bucket
aws glue start-job-run --job-name etl-omc-flywheel-dev-register-staged-tables
aws glue start-job-run --job-name etl-omc-flywheel-dev-create-athena-bucketed-tables
```

### Option B: Partitioned Pipeline

```bash
export AWS_PROFILE=flywheel-dev

aws glue start-job-run --job-name etl-omc-flywheel-dev-infobase-split-and-part
aws glue start-job-run --job-name etl-omc-flywheel-dev-addressable-split-and-part
aws glue start-job-run --job-name etl-omc-flywheel-dev-register-part-tables
aws glue start-job-run --job-name etl-omc-flywheel-dev-prepare-part-tables
```

## Step 4: Verify Results

```bash
# Check Glue tables created
aws glue get-tables --database-name omc_flywheel_dev --profile flywheel-dev

# Check S3 output
aws s3 ls s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/ --recursive --profile flywheel-dev

# Check job status
aws glue get-job-runs --job-name etl-omc-flywheel-dev-infobase-split-and-bucket --max-items 5 --profile flywheel-dev
```

## Key Differences: Dev vs Prod

| Aspect | Dev | Prod |
|--------|-----|------|
| Job Names | `etl-omc-flywheel-dev-*` | `etl-omc-flywheel-prod-*` |
| Database | `omc_flywheel_dev` | `omc_flywheel_prod` |
| Data Bucket | `omc-flywheel-data-us-east-1-dev` | `omc-flywheel-data-us-east-1-prod` |
| Workers | 5 | 24 |
| Timeout | 30 min | 2880 min |
| Retries | 2 | 0-1 |
| IAM Policies | `omc-flywheel-dev-glue-role-*` | `omc-flywheel-prod-glue-role-*` |
| Monitoring Job | `etl-omc-flywheel-dev-generate-data-monitor-report` | `etl-omc-flywheel-prod-generate-data-monitor-report` |
| Monitoring Schedule | Every 12 hours | Every 24 hours |

## Troubleshooting

### Script Not Found
```bash
# Verify script uploaded
ACCOUNT_ID=$(aws sts get-caller-identity --profile flywheel-dev --query Account --output text)
aws s3 ls s3://aws-glue-assets-${ACCOUNT_ID}-us-east-1/scripts/ --profile flywheel-dev
```

### Job Fails Immediately
- Check IAM role permissions
- Verify database exists
- Check S3 bucket access
- Check CloudWatch logs for detailed errors

### Permission Denied
```bash
# Verify IAM role and policies
aws iam get-role --role-name omc_flywheel-dev-glue-role --profile flywheel-dev
aws iam list-attached-role-policies --role-name omc_flywheel-dev-glue-role --profile flywheel-dev
```

### No Output Data
- Verify source data exists in dev bucket
- Check snapshot_dt structure
- Verify CSV mapping files exist

### Monitoring Job Issues
```bash
# Check monitoring job
aws glue get-job --job-name etl-omc-flywheel-dev-generate-data-monitor-report --profile flywheel-dev

# Check monitoring role
aws iam get-role --role-name omc-flywheel-dev-data-monitor-role --profile flywheel-dev

# View monitoring logs
aws logs tail /aws/glue/jobs/etl-omc-flywheel-dev-generate-data-monitor-report --profile flywheel-dev --follow
```

## Next Steps After Validation

1. ✅ Document any dev-specific issues
2. ✅ Update scripts if environment-specific logic needed
3. ✅ Prepare for production deployment
4. ✅ Consider automation setup

---

**See Also**: `docs/DEV_SETUP_AND_VALIDATION.md` for detailed guide

