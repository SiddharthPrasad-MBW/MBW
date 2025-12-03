# Dev Environment Complete Setup Checklist

## Pre-Deployment Checklist

### Infrastructure Prerequisites

- [ ] **AWS Account Access**
  - [ ] Dev account credentials configured
  - [ ] AWS CLI profile: `flywheel-dev`
  - [ ] Terraform >= 1.0 installed

- [ ] **S3 Buckets**
  - [ ] `omc-flywheel-data-us-east-1-dev` exists
  - [ ] `omc-flywheel-dev-analysis-data` exists
  - [ ] `aws-glue-assets-{account-id}-us-east-1` exists (created automatically by Glue)

- [ ] **Glue Database**
  - [ ] `omc_flywheel_dev` exists
  - [ ] Or will be created by Terraform

- [ ] **IAM Roles** (if not created by Terraform)
  - [ ] `omc_flywheel-dev-glue-role` exists
  - [ ] Role has S3 permissions
  - [ ] Role has Glue permissions

- [ ] **Source Data**
  - [ ] Data in `s3://omc-flywheel-data-us-east-1-dev/opus/infobase_attributes/raw_input/`
  - [ ] Data in `s3://omc-flywheel-data-us-east-1-dev/opus/addressable_ids/raw_input/`
  - [ ] Snapshot structure: `snapshot_dt=YYYY-MM-DD/`
  - [ ] CSV mapping files in `s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/`

## Deployment Steps

### Step 1: Deploy Glue Jobs Stack

- [ ] Navigate to `infra/stacks/dev-gluejobs`
- [ ] Run `terraform init`
- [ ] Run `terraform plan` (review changes)
- [ ] Run `terraform apply`
- [ ] Verify jobs created: `aws glue list-jobs --profile flywheel-dev | grep etl-omc-flywheel-dev`

**Expected Resources**:
- [ ] 8+ Glue jobs with `etl-omc-flywheel-dev-*` naming
- [ ] IAM policies: `omc-flywheel-dev-glue-role-s3-access`
- [ ] IAM policies: `omc-flywheel-dev-glue-role-cleanrooms-read`
- [ ] 2 Glue crawlers with `crw-omc-flywheel-dev-*` naming

### Step 2: Deploy Monitoring Stack

- [ ] Navigate to `infra/stacks/dev-monitoring`
- [ ] Run `terraform init`
- [ ] Run `terraform plan` (review changes)
- [ ] Run `terraform apply`
- [ ] Verify monitoring job: `aws glue get-job --job-name etl-omc-flywheel-dev-generate-data-monitor-report --profile flywheel-dev`

**Expected Resources**:
- [ ] Monitoring job: `etl-omc-flywheel-dev-generate-data-monitor-report`
- [ ] Monitoring role: `omc-flywheel-dev-data-monitor-role`
- [ ] SNS topic: `omc-flywheel-dev-data-monitor-alerts`
- [ ] CloudWatch log group
- [ ] CloudWatch dashboard

### Step 3: Upload Scripts

- [ ] Run `./scripts/setup-dev-scripts.sh`
- [ ] Or manually upload scripts to S3
- [ ] Verify scripts uploaded: `aws s3 ls s3://aws-glue-assets-{account-id}-us-east-1/scripts/ --profile flywheel-dev`

**Required Scripts**:
- [ ] `etl-omc-flywheel-dev-infobase-split-and-bucket.py`
- [ ] `etl-omc-flywheel-dev-addressable-bucket.py`
- [ ] `etl-omc-flywheel-dev-register-staged-tables.py`
- [ ] `etl-omc-flywheel-dev-create-athena-bucketed-tables.py`
- [ ] `etl-omc-flywheel-dev-infobase-split-and-part.py`
- [ ] `etl-omc-flywheel-dev-addressable-split-and-part.py`
- [ ] `etl-omc-flywheel-dev-register-part-tables.py`
- [ ] `etl-omc-flywheel-dev-prepare-part-tables.py`
- [ ] `data_monitor.py` (shared)
- [ ] `create-part-addressable-ids-er-table.py` (shared)
- [ ] `create-all-part-tables-er.py` (shared)
- [ ] `generate-cleanrooms-report.py` (shared)

## Validation Steps

### Step 4: Run Test Pipeline

- [ ] **Bucketed Pipeline**:
  - [ ] Run `etl-omc-flywheel-dev-infobase-split-and-bucket`
  - [ ] Verify job succeeds
  - [ ] Run `etl-omc-flywheel-dev-addressable-bucket`
  - [ ] Verify job succeeds
  - [ ] Run `etl-omc-flywheel-dev-register-staged-tables`
  - [ ] Verify job succeeds
  - [ ] Run `etl-omc-flywheel-dev-create-athena-bucketed-tables`
  - [ ] Verify job succeeds

- [ ] **Verify Output**:
  - [ ] Check S3 output: `aws s3 ls s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/ --recursive --profile flywheel-dev`
  - [ ] Check Glue tables: `aws glue get-tables --database-name omc_flywheel_dev --profile flywheel-dev`
  - [ ] Verify table names: `bucketed_*`, `ext_*`

### Step 5: Run Monitoring

- [ ] Run monitoring job: `aws glue start-job-run --job-name etl-omc-flywheel-dev-generate-data-monitor-report --profile flywheel-dev`
- [ ] Wait for completion
- [ ] Check monitoring report: `aws s3 ls s3://omc-flywheel-dev-analysis-data/data-monitor/ --profile flywheel-dev`
- [ ] Review report for any issues

### Step 6: Verify Permissions

- [ ] **Glue Role Permissions**:
  - [ ] S3 access working
  - [ ] Glue catalog access working
  - [ ] Cleanrooms read access (if using reporting)

- [ ] **Monitoring Role Permissions**:
  - [ ] S3 access working
  - [ ] Athena access working
  - [ ] SNS publish working

## Post-Deployment Verification

### Resource Verification

- [ ] All jobs have correct naming (`dev` not `prod`)
- [ ] All IAM policies have correct naming (`dev` not `prod`)
- [ ] All scripts reference dev resources
- [ ] All jobs use environment variable (`--ENV=dev`)

### Functional Verification

- [ ] Jobs can read from source S3
- [ ] Jobs can write to target S3
- [ ] Jobs can access Glue catalog
- [ ] Jobs can create tables
- [ ] Monitoring job can generate reports
- [ ] Reports are written to correct S3 location

### Data Verification

- [ ] Tables created in Glue catalog
- [ ] Data written to S3 correctly
- [ ] Partition structure correct
- [ ] Snapshot metadata present
- [ ] Record counts reasonable

## Common Issues and Solutions

### Issue: IAM Policy Name Conflict

**Symptom**: Terraform error about policy already exists

**Solution**: 
- Policy names are now environment-aware
- Old policies may need to be removed or renamed
- Check: `aws iam list-policies --profile flywheel-dev | grep omc-flywheel`

### Issue: Job Name Conflict

**Symptom**: Job already exists with different configuration

**Solution**:
- Jobs are now environment-aware
- Old jobs may need to be removed
- Check: `aws glue list-jobs --profile flywheel-dev | grep omc-flywheel`

### Issue: Script Not Found

**Symptom**: Job fails with "Script not found"

**Solution**:
- Verify script uploaded with correct name
- Check script name matches job name exactly
- Ensure script has `.py` extension

### Issue: Permission Denied

**Symptom**: AccessDeniedException errors

**Solution**:
- Verify IAM role attached to job
- Check role has required permissions
- Verify bucket policies allow access

## Next Steps After Validation

1. ✅ Document any dev-specific configurations
2. ✅ Note any differences from production
3. ✅ Update scripts if environment-specific logic needed
4. ✅ Prepare promotion to production
5. ✅ Consider automation setup (EventBridge schedules)

## Quick Reference

### Dev Job Names
- `etl-omc-flywheel-dev-infobase-split-and-bucket`
- `etl-omc-flywheel-dev-addressable-bucket`
- `etl-omc-flywheel-dev-register-staged-tables`
- `etl-omc-flywheel-dev-create-athena-bucketed-tables`
- `etl-omc-flywheel-dev-infobase-split-and-part`
- `etl-omc-flywheel-dev-addressable-split-and-part`
- `etl-omc-flywheel-dev-register-part-tables`
- `etl-omc-flywheel-dev-prepare-part-tables`
- `etl-omc-flywheel-dev-generate-cleanrooms-report`
- `etl-omc-flywheel-dev-generate-data-monitor-report`

### Dev IAM Policies
- `omc-flywheel-dev-glue-role-s3-access`
- `omc-flywheel-dev-glue-role-cleanrooms-read`

### Dev Resources
- Database: `omc_flywheel_dev`
- Data Bucket: `omc-flywheel-data-us-east-1-dev`
- Analysis Bucket: `omc-flywheel-dev-analysis-data`
- Glue Role: `omc_flywheel-dev-glue-role`
- Monitoring Role: `omc-flywheel-dev-data-monitor-role`

---

**Last Updated**: November 18, 2025

