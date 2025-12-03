# Dev Environment Terraform Update - Summary

## ✅ Completed Successfully

### **dev-gluejobs Stack**
- ✅ **11 Glue Jobs** created/imported and configured
- ✅ **2 Glue Crawlers** imported
- ✅ **IAM Role** imported: `omc_flywheel-dev-glue-role`
- ✅ **IAM Policies** created:
  - `omc-flywheel-dev-glue-role-s3-access`
  - `omc-flywheel-dev-glue-role-cleanrooms-read`
- ✅ **3 Python Shell Jobs Fixed**: Updated to use `max_capacity = 0.0625` (aligned with prod)

### **dev-monitoring Stack**
- ✅ **9 Resources** created:
  - Data monitor Glue job: `etl-omc-flywheel-dev-generate-data-monitor-report`
  - IAM role: `omc-flywheel-dev-data-monitor-role`
  - IAM policy: `omc-flywheel-dev-data-monitor-policy`
  - SNS topic: `omc-flywheel-dev-data-monitor-alerts`
  - CloudWatch dashboard: `omc-flywheel-dev-Data-Monitor`
  - CloudWatch log group

## 📋 Dev Job Names for Manual Execution

### **Production Flow (Partitioned Pipeline)**
1. `etl-omc-flywheel-dev-addressable-split-and-part`
2. `etl-omc-flywheel-dev-infobase-split-and-part`
3. `etl-omc-flywheel-dev-register-part-tables`
4. `etl-omc-flywheel-dev-prepare-part-tables`
5. `etl-omc-flywheel-dev-create-part-addressable-ids-er-table`
6. `etl-omc-flywheel-dev-generate-data-monitor-report`
7. `etl-omc-flywheel-dev-generate-cleanrooms-report`

### **Bucketed Pipeline (if needed)**
- `etl-omc-flywheel-dev-infobase-split-and-bucket`
- `etl-omc-flywheel-dev-addressable-bucket`
- `etl-omc-flywheel-dev-register-staged-tables`
- `etl-omc-flywheel-dev-create-athena-bucketed-tables`

### **Additional Jobs**
- `etl-omc-flywheel-dev-create-all-part-tables-er`

## 🔧 Quick Commands

### List all dev jobs:
```bash
export AWS_PROFILE=flywheel-dev
aws glue list-jobs --query 'JobNames[?contains(@, `etl-omc-flywheel-dev`)]' --output table
```

### Run a job:
```bash
export AWS_PROFILE=flywheel-dev
aws glue start-job-run --job-name etl-omc-flywheel-dev-addressable-split-and-part
```

### Check job status:
```bash
export AWS_PROFILE=flywheel-dev
aws glue get-job-runs --job-name <job-name> --max-items 1
```

## ✅ Alignment with Production

**Yes, dev is now aligned with prod:**
- ✅ Same Terraform module used for both environments
- ✅ Python shell jobs use `max_capacity = 0.0625` (1 DPU)
- ✅ Spark/Glue ETL jobs use `worker_type` and `number_of_workers`
- ✅ Environment-aware naming via variables
- ✅ Same job configurations (dev has lower defaults for testing)

## 📝 Notes

- **dev-crconfigtables** stack was skipped (Terraform doesn't support table associations - use Python scripts)
- All jobs are ready for manual execution and validation
- Terraform state is fully synced: "No changes. Your infrastructure matches the configuration."

## 🎯 Next Steps

1. Run jobs manually in the production flow sequence
2. Validate outputs and data quality
3. Test monitoring and reporting jobs
4. Verify Cleanrooms integration (if membership_id configured)

## ⚠️ Known Issues / Technical Debt

### Production Scripts - Account ID Hardcoding

**Status:** Dev scripts fixed, prod scripts still have hardcoded account IDs

**Issue:** Production ETL scripts have hardcoded account ID (`239083076653`) in Glue assets bucket paths.

**Dev Status:** ✅ Fixed - All dev scripts now use dynamic account ID lookup via `boto3.client('sts').get_caller_identity()['Account']`

**Action Required:** Update prod scripts to use dynamic account ID (see `docs/TECHNICAL_DEBT.md` for details)

**Files to Update:**
- `scripts/etl-omc-flywheel-prod-addressable-split-and-part.py`
- `scripts/etl-omc-flywheel-prod-infobase-split-and-part.py`
- `scripts/etl-omc-flywheel-prod-addressable-bucket.py`
- `scripts/etl-omc-flywheel-prod-infobase-split-and-bucket.py`

