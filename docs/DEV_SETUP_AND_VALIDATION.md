# Dev Environment Setup and Validation Guide

## Overview

This guide helps you set up the dev environment to validate the production processes. After fixing hardcoded values, all jobs are now environment-aware and will work in both dev and prod.

## Prerequisites

### 1. AWS Account Access
- Dev account access with appropriate permissions
- AWS CLI configured with dev profile
- Terraform >= 1.0 installed

### 2. Required Resources in Dev
- S3 buckets:
  - `omc-flywheel-data-us-east-1-dev` (data bucket)
  - `omc-flywheel-dev-analysis-data` (analysis bucket)
- Glue database: `omc_flywheel_dev`
- IAM role: `omc_flywheel-dev-glue-role`
- Glue assets bucket: `aws-glue-assets-{account-id}-us-east-1`

## Step 1: Deploy Infrastructure to Dev

### 1.1 Navigate to Dev Stack

```bash
cd infra/stacks/dev-gluejobs
```

### 1.2 Initialize Terraform

```bash
terraform init
```

### 1.3 Review Configuration

Check `variables.tf` to ensure dev values are correct:
- `glue_database_name = "omc_flywheel_dev"`
- `data_bucket_name = "omc-flywheel-data-us-east-1-dev"`
- `analysis_bucket_name = "omc-flywheel-dev-analysis-data"`
- `glue_role_name = "omc_flywheel-dev-glue-role"`

### 1.4 Plan and Apply

```bash
# Review what will be created
terraform plan

# Apply infrastructure
terraform apply
```

**Expected Output:**
- ✅ Glue jobs created with `etl-omc-flywheel-dev-*` naming
- ✅ All jobs reference environment-aware script locations
- ✅ Jobs configured with dev-specific settings (lower workers, shorter timeouts)

## Step 2: Upload Scripts to S3

### 2.1 Get Dev Account ID and Glue Assets Bucket

```bash
# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --profile flywheel-dev --query Account --output text)
echo "Account ID: $ACCOUNT_ID"

# Glue assets bucket name
GLUE_BUCKET="aws-glue-assets-${ACCOUNT_ID}-us-east-1"
echo "Glue bucket: $GLUE_BUCKET"
```

### 2.2 Upload Scripts

The scripts need to be uploaded with environment-specific names. For dev, they should be named:
- `etl-omc-flywheel-dev-infobase-split-and-bucket.py`
- `etl-omc-flywheel-dev-addressable-bucket.py`
- etc.

**Option A: Copy from Production Scripts (Recommended)**

If you have the production scripts, copy and rename them:

```bash
# Set variables
ACCOUNT_ID=$(aws sts get-caller-identity --profile flywheel-dev --query Account --output text)
GLUE_BUCKET="aws-glue-assets-${ACCOUNT_ID}-us-east-1"
SCRIPT_DIR="scripts"

# Create scripts directory in S3 if it doesn't exist
aws s3api put-object --bucket $GLUE_BUCKET --key scripts/ --profile flywheel-dev

# Upload scripts with dev naming
# Note: You'll need to copy the production scripts and rename them, or
# create environment-aware versions

# Example for one script:
aws s3 cp scripts/etl-omc-flywheel-prod-infobase-split-and-bucket.py \
  s3://$GLUE_BUCKET/scripts/etl-omc-flywheel-dev-infobase-split-and-bucket.py \
  --profile flywheel-dev
```

**Option B: Create Environment-Aware Scripts**

The scripts should read the `--ENV` parameter and adjust paths accordingly. Most scripts already support this via the `--ENV` argument.

### 2.3 Required Scripts for Dev

Upload these scripts with `dev` in the name:

1. **Bucketed Pipeline:**
   - `etl-omc-flywheel-dev-infobase-split-and-bucket.py`
   - `etl-omc-flywheel-dev-addressable-bucket.py`
   - `etl-omc-flywheel-dev-register-staged-tables.py`
   - `etl-omc-flywheel-dev-create-athena-bucketed-tables.py`

2. **Partitioned Pipeline:**
   - `etl-omc-flywheel-dev-infobase-split-and-part.py`
   - `etl-omc-flywheel-dev-addressable-split-and-part.py`
   - `etl-omc-flywheel-dev-register-part-tables.py`
   - `etl-omc-flywheel-dev-prepare-part-tables.py`

3. **Other Scripts:**
   - `create-part-addressable-ids-er-table.py` (shared, no env in name)
   - `create-all-part-tables-er.py` (shared, no env in name)
   - `generate-cleanrooms-report.py` (shared, no env in name)

## Step 3: Prepare Dev Data

### 3.1 Verify Source Data Structure

Ensure dev S3 bucket has the expected structure:

```bash
aws s3 ls s3://omc-flywheel-data-us-east-1-dev/opus/infobase_attributes/raw_input/ --profile flywheel-dev --recursive
aws s3 ls s3://omc-flywheel-data-us-east-1-dev/opus/addressable_ids/raw_input/ --profile flywheel-dev --recursive
```

**Expected Structure:**
```
opus/
├── infobase_attributes/raw_input/snapshot_dt=YYYY-MM-DD/
│   ├── IBE_01/
│   ├── IBE_02/
│   └── ...
└── addressable_ids/raw_input/snapshot_dt=YYYY-MM-DD/
    └── addressable_ids/
```

### 3.2 Verify CSV Mapping Files

Ensure mapping CSV files exist:

```bash
aws s3 ls s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/ --profile flywheel-dev --recursive | grep csv
```

**Required Files:**
- `omc_flywheel_infobase_table_split_part.csv`
- `omc_flywheel_addressable_ids_table_split_part.csv`

## Step 4: Run Validation Pipeline

### 4.1 Bucketed Pipeline (Production Process)

```bash
# Set AWS profile
export AWS_PROFILE=flywheel-dev

# Step 1: Infobase Split and Bucket
aws glue start-job-run \
  --job-name etl-omc-flywheel-dev-infobase-split-and-bucket \
  --profile flywheel-dev

# Wait for completion, then:
# Step 2: Addressable Bucket
aws glue start-job-run \
  --job-name etl-omc-flywheel-dev-addressable-bucket \
  --profile flywheel-dev

# Wait for completion, then:
# Step 3: Register Staged Tables
aws glue start-job-run \
  --job-name etl-omc-flywheel-dev-register-staged-tables \
  --profile flywheel-dev

# Wait for completion, then:
# Step 4: Create Athena Bucketed Tables
aws glue start-job-run \
  --job-name etl-omc-flywheel-dev-create-athena-bucketed-tables \
  --profile flywheel-dev
```

### 4.2 Partitioned Pipeline (Alternative Process)

```bash
# Step 1: Infobase Split and Part
aws glue start-job-run \
  --job-name etl-omc-flywheel-dev-infobase-split-and-part \
  --profile flywheel-dev

# Step 2: Addressable Split and Part
aws glue start-job-run \
  --job-name etl-omc-flywheel-dev-addressable-split-and-part \
  --profile flywheel-dev

# Step 3: Register Part Tables
aws glue start-job-run \
  --job-name etl-omc-flywheel-dev-register-part-tables \
  --profile flywheel-dev

# Step 4: Prepare Part Tables
aws glue start-job-run \
  --job-name etl-omc-flywheel-dev-prepare-part-tables \
  --profile flywheel-dev
```

## Step 5: Verify Results

### 5.1 Check Glue Tables

```bash
# List tables in dev database
aws glue get-tables \
  --database-name omc_flywheel_dev \
  --profile flywheel-dev \
  --query 'TableList[*].Name' \
  --output table
```

**Expected Tables:**
- Bucketed: `bucketed_ibe_01`, `bucketed_ibe_02`, etc.
- Partitioned: `part_ibe_01`, `part_ibe_02`, etc.
- External: `ext_ibe_01`, `ext_ibe_02`, etc.

### 5.2 Check S3 Output

```bash
# Check bucketed output
aws s3 ls s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/cleanroom_tables/bucketed/ \
  --profile flywheel-dev --recursive

# Check partitioned output
aws s3 ls s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_part/ \
  --profile flywheel-dev --recursive
```

### 5.3 Test Athena Queries

```bash
# Query a bucketed table
aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM omc_flywheel_dev.bucketed_ibe_01 LIMIT 1" \
  --work-group primary \
  --result-configuration OutputLocation=s3://omc-flywheel-dev-analysis-data/query-results/ \
  --profile flywheel-dev
```

## Step 6: Compare Dev vs Prod

### 6.1 Job Configuration Comparison

| Aspect | Dev | Prod |
|--------|-----|------|
| Worker Count | 5 | 24 |
| Timeout | 30 min | 2880 min (48 hours) |
| Max Retries | 2 | 0-1 |
| Database | `omc_flywheel_dev` | `omc_flywheel_prod` |
| Bucket | `omc-flywheel-data-us-east-1-dev` | `omc-flywheel-data-us-east-1-prod` |

### 6.2 Validation Checklist

- [ ] All jobs created successfully
- [ ] Scripts uploaded to correct S3 locations
- [ ] Jobs run without errors
- [ ] Tables created in Glue catalog
- [ ] Data written to S3 correctly
- [ ] Athena queries work
- [ ] Job names use `dev` instead of `prod`
- [ ] Environment parameter (`--ENV`) set to `dev`

## Troubleshooting

### Issue: Script Not Found

**Error**: `Script not found: s3://aws-glue-assets-.../scripts/etl-omc-flywheel-dev-...`

**Solution**:
1. Verify script uploaded: `aws s3 ls s3://aws-glue-assets-{account}-us-east-1/scripts/ --profile flywheel-dev`
2. Check script name matches job name exactly
3. Ensure script has `.py` extension

### Issue: Permission Denied

**Error**: `AccessDeniedException` when accessing S3

**Solution**:
1. Verify IAM role has S3 permissions
2. Check bucket policies
3. Ensure role is attached to job

### Issue: Database Not Found

**Error**: `Database omc_flywheel_dev not found`

**Solution**:
1. Create database: `aws glue create-database --database-input Name=omc_flywheel_dev --profile flywheel-dev`
2. Or update job to use existing database name

### Issue: No Data in Source

**Error**: Job completes but no output

**Solution**:
1. Verify source data exists: `aws s3 ls s3://omc-flywheel-data-us-east-1-dev/opus/ --recursive`
2. Check snapshot_dt structure matches expected format
3. Verify CSV mapping files exist

## Next Steps

After successful validation in dev:

1. **Document Differences**: Note any dev-specific issues or configurations
2. **Update Scripts**: If scripts need environment-specific logic, update them
3. **Promote to Prod**: Once validated, the same process works in prod (with prod values)
4. **Set Up Automation**: After validation, consider adding EventBridge schedules

## Quick Reference

### Dev Job Names

All jobs follow the pattern: `etl-omc-flywheel-dev-{job-name}`

- `etl-omc-flywheel-dev-infobase-split-and-bucket`
- `etl-omc-flywheel-dev-addressable-bucket`
- `etl-omc-flywheel-dev-register-staged-tables`
- `etl-omc-flywheel-dev-create-athena-bucketed-tables`
- `etl-omc-flywheel-dev-infobase-split-and-part`
- `etl-omc-flywheel-dev-addressable-split-and-part`
- `etl-omc-flywheel-dev-register-part-tables`
- `etl-omc-flywheel-dev-prepare-part-tables`

### Dev Resources

- **Database**: `omc_flywheel_dev`
- **Data Bucket**: `omc-flywheel-data-us-east-1-dev`
- **Analysis Bucket**: `omc-flywheel-dev-analysis-data`
- **IAM Role**: `omc_flywheel-dev-glue-role`
- **Glue Assets**: `aws-glue-assets-{account-id}-us-east-1`

---

**Last Updated**: November 18, 2025

