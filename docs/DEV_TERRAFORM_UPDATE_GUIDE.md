# Dev Environment Terraform Update Guide

## Overview

This guide explains how to update the dev environment using Terraform. The dev environment includes:

1. **Glue Jobs** (`dev-gluejobs`) - All ETL jobs with environment-aware naming
2. **Monitoring** (`dev-monitoring`) - Data quality monitoring and alerts
3. **Cleanrooms Config** (`dev-crconfigtables`) - Configured tables for Cleanrooms

## What Gets Updated

### Glue Jobs Stack (`dev-gluejobs`)
- ✅ All Glue ETL jobs (environment-aware: `etl-omc-flywheel-dev-*`)
- ✅ IAM role: `omc_flywheel-dev-glue-role`
- ✅ IAM policies:
  - S3 access policy
  - Cleanrooms read-only policy
  - AWS Glue service role attachment
- ✅ Glue crawlers (if enabled)

### Monitoring Stack (`dev-monitoring`)
- ✅ Data monitor Glue job
- ✅ IAM role and policies for monitoring
- ✅ SNS topic for alerts
- ✅ CloudWatch dashboard
- ✅ CloudWatch log group

### Cleanrooms Stack (`dev-crconfigtables`)
- ✅ Cleanrooms configured tables
- ✅ Table associations (if membership_id provided)
- ✅ IAM role for Cleanrooms access

## Quick Start

### Option 1: Automated Script (Recommended)

```bash
cd /Users/patrick.spann/Documents/acx_omc_flywheel_cr
./scripts/update-dev-terraform.sh
```

The script will:
1. Validate all Terraform configurations
2. Initialize Terraform (if needed)
3. Plan changes for all stacks
4. Prompt for confirmation before applying
5. Apply changes to all stacks in order

### Option 2: Manual Update

#### Step 1: Update Glue Jobs

```bash
cd infra/stacks/dev-gluejobs

# Initialize (if first time)
terraform init

# Plan changes
terraform plan -out=tfplan

# Review plan
terraform show tfplan

# Apply changes
terraform apply tfplan
```

#### Step 2: Update Monitoring

```bash
cd infra/stacks/dev-monitoring

terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

#### Step 3: Update Cleanrooms Config

```bash
cd infra/stacks/dev-crconfigtables

terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

## Prerequisites

### AWS Credentials

Make sure you have AWS credentials configured for the dev account:

```bash
# Check current AWS identity
aws sts get-caller-identity

# Or set profile
export AWS_PROFILE=your-dev-profile
```

### Required Variables

The stacks use default values, but you can override them:

**dev-gluejobs:**
- `glue_database_name` (default: `omc_flywheel_dev`)
- `data_bucket_name` (default: `omc-flywheel-data-us-east-1-dev`)
- `analysis_bucket_name` (default: `omc-flywheel-dev-analysis-data`)
- `glue_role_name` (default: `omc_flywheel-dev-glue-role`)
- `cleanrooms_membership_id` (optional, default: `null`)

**dev-monitoring:**
- Same as above (uses same variables)

**dev-crconfigtables:**
- `cleanrooms_membership_id` (required if creating associations)
- `cleanrooms_allowed_query_providers` (optional, list of account IDs)

### Create terraform.tfvars (Optional)

You can create a `terraform.tfvars` file in each stack directory:

```hcl
# infra/stacks/dev-gluejobs/terraform.tfvars
aws_region = "us-east-1"
glue_database_name = "omc_flywheel_dev"
data_bucket_name = "omc-flywheel-data-us-east-1-dev"
analysis_bucket_name = "omc-flywheel-dev-analysis-data"
glue_role_name = "omc_flywheel-dev-glue-role"
cleanrooms_membership_id = "your-membership-id-here"  # Optional
```

## What Gets Created/Updated

### IAM Resources

#### Glue Role (`omc_flywheel-dev-glue-role`)
- **Policies attached:**
  - `AWSGlueServiceRole` (AWS managed)
  - `omc-flywheel-dev-glue-role-s3-access` (custom)
  - `omc-flywheel-dev-glue-role-cleanrooms-read` (custom)

#### Monitoring Role (`omc-flywheel-dev-data-monitor-role`)
- **Policies attached:**
  - `AWSGlueServiceRole` (AWS managed)
  - `omc-flywheel-dev-data-monitor-policy` (custom)

### Glue Jobs Created

All jobs use the `etl-omc-flywheel-dev-` prefix:

**Partitioned Pipeline:**
- `etl-omc-flywheel-dev-addressable-split-and-part`
- `etl-omc-flywheel-dev-infobase-split-and-part`
- `etl-omc-flywheel-dev-register-part-tables`
- `etl-omc-flywheel-dev-prepare-part-tables`
- `etl-omc-flywheel-dev-create-part-addressable-ids-er-table`
- `etl-omc-flywheel-dev-create-all-part-tables-er`
- `etl-omc-flywheel-dev-generate-cleanrooms-report`

**Bucketed Pipeline (if enabled):**
- `etl-omc-flywheel-dev-infobase-split-and-bucket`
- `etl-omc-flywheel-dev-addressable-bucket`
- `etl-omc-flywheel-dev-register-staged-tables`
- `etl-omc-flywheel-dev-create-athena-bucketed-tables`

**Monitoring:**
- `etl-omc-flywheel-dev-generate-data-monitor-report`

## Verification

After applying Terraform, verify the resources:

### Check Glue Jobs

```bash
aws glue list-jobs --query 'JobNames[?contains(@, `etl-omc-flywheel-dev`)]'
```

### Check IAM Roles

```bash
aws iam get-role --role-name omc_flywheel-dev-glue-role
aws iam list-role-policies --role-name omc_flywheel-dev-glue-role
```

### Check Cleanrooms Tables

```bash
aws cleanrooms list-configured-tables --membership-identifier <membership-id>
```

## Troubleshooting

### Error: "Role already exists"

If the IAM role already exists but wasn't created by Terraform:

1. Import the existing role:
   ```bash
   terraform import aws_iam_role.glue_role omc_flywheel-dev-glue-role
   ```

2. Or set `create_iam_role = false` in the module and pass existing role name

### Error: "Bucket already exists"

If S3 buckets already exist:

- The stacks are configured with `create_s3_buckets = false` by default
- Make sure `data_bucket_name` and `analysis_bucket_name` match existing buckets

### Error: "Script not found in S3"

Make sure scripts are uploaded to S3:

```bash
# Upload dev scripts
./scripts/setup-dev-scripts.sh
```

### Error: "Membership not found"

If `cleanrooms_membership_id` is required but not provided:

- Set it in `terraform.tfvars` or pass via `-var`
- Or set to `null` if you don't need associations yet

## State Management

Each stack has its own Terraform state file:

- `infra/stacks/dev-gluejobs/terraform.tfstate`
- `infra/stacks/dev-monitoring/terraform.tfstate`
- `infra/stacks/dev-crconfigtables/terraform.tfstate`

**Important:** Don't delete state files! They track what Terraform manages.

## Next Steps

After updating Terraform:

1. ✅ Verify all jobs exist in AWS Console
2. ✅ Check IAM roles have correct policies
3. ✅ Upload scripts to S3 (if not already done)
4. ✅ Test job execution with `run-dev-flow.sh`
5. ✅ Review monitoring dashboard

## Rollback

If something goes wrong:

1. **Don't delete resources manually** - Terraform will try to recreate them
2. **Use Terraform destroy** (carefully):
   ```bash
   terraform destroy  # Only if you want to remove everything
   ```
3. **Or revert Terraform code** and re-apply

## Support

For issues:
- Check Terraform plan output for details
- Review AWS CloudWatch logs for job errors
- Verify IAM permissions in AWS Console
- Check S3 bucket permissions

