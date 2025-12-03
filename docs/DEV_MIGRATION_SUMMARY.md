# Dev Environment Migration Summary

## What Was Done

### 1. Fixed Hardcoded Environment Values ✅

**Problem**: All Glue jobs had hardcoded "prod" in names and script paths.

**Solution**: Made everything environment-aware using Terraform variables.

**Changes Made**:
- Added `job_name_prefix` local variable: `etl-omc-flywheel-${var.environment}`
- Added `script_location_prefix` local variable
- Replaced all hardcoded job names with `${local.job_name_prefix}-{job-name}`
- Replaced all hardcoded script paths with `${local.script_location_prefix}/...`
- Changed `--ENV` parameter from hardcoded "prod" to `var.environment`

**Files Modified**:
- `infra/modules/gluejobs/main.tf` - All job definitions now environment-aware

### 2. Created Dev Scripts ✅

**Created Dev Versions**:
- `etl-omc-flywheel-dev-infobase-split-and-bucket.py`
- `etl-omc-flywheel-dev-addressable-bucket.py`
- `etl-omc-flywheel-dev-register-staged-tables.py`
- `etl-omc-flywheel-dev-create-athena-bucketed-tables.py`
- (Partitioned pipeline scripts already existed)

**Script Updates**:
- Replaced hardcoded "prod" with "dev" in script contents
- Updated bucket names, database names, etc.

### 3. Updated Dev Stack Configuration ✅

**Added**:
- `cleanrooms_membership_id` variable (optional for dev)
- Environment-aware job configuration

**Dev-Specific Settings**:
- Lower worker count: 5 (vs 24 in prod)
- Shorter timeout: 30 min (vs 2880 min in prod)
- More retries: 2 (vs 0-1 in prod)

### 4. Created Helper Scripts ✅

**`scripts/setup-dev-scripts.sh`**:
- Automatically creates dev script copies
- Replaces hardcoded values
- Uploads scripts to S3

### 5. Created Documentation ✅

**`docs/DEV_SETUP_AND_VALIDATION.md`**:
- Complete setup guide
- Step-by-step instructions
- Troubleshooting section

**`docs/DEV_QUICK_START.md`**:
- Quick reference for fast setup
- Essential commands only

## Current Status

### ✅ Completed
- [x] Environment-aware job naming
- [x] Environment-aware script paths
- [x] Dev scripts created
- [x] Dev stack configuration updated
- [x] Helper scripts created
- [x] Documentation created

### 🔄 Next Steps (For You)

1. **Deploy Dev Infrastructure**:
   ```bash
   cd infra/stacks/dev-gluejobs
   terraform init
   terraform plan
   terraform apply
   ```

2. **Upload Scripts**:
   ```bash
   ./scripts/setup-dev-scripts.sh
   ```

3. **Run Validation Pipeline**:
   ```bash
   # See docs/DEV_QUICK_START.md
   ```

## Job Naming Convention

### Before (Hardcoded)
- `etl-omc-flywheel-prod-infobase-split-and-bucket`
- `etl-omc-flywheel-prod-addressable-bucket`
- etc.

### After (Environment-Aware)
- **Dev**: `etl-omc-flywheel-dev-infobase-split-and-bucket`
- **Prod**: `etl-omc-flywheel-prod-infobase-split-and-bucket`

## Script Locations

### Before (Hardcoded)
```
s3://aws-glue-assets-{account}/scripts/etl-omc-flywheel-prod-{script}.py
```

### After (Environment-Aware)
```
s3://aws-glue-assets-{account}/scripts/etl-omc-flywheel-{env}-{script}.py
```

## Benefits

1. **Single Module**: One module works for both dev and prod
2. **No Duplication**: No need to maintain separate prod/dev modules
3. **Easy Promotion**: Same code works in both environments
4. **Consistent Naming**: Clear environment identification
5. **Maintainable**: Changes to module affect both environments

## Testing Checklist

Before running in dev, verify:

- [ ] Terraform plan shows correct job names (dev)
- [ ] Scripts uploaded to S3 with dev naming
- [ ] IAM role has correct permissions
- [ ] Source data exists in dev bucket
- [ ] CSV mapping files exist
- [ ] Glue database exists

## Promotion Path

Once validated in dev:

1. **Same Terraform Module**: No changes needed
2. **Different Variables**: Use prod stack with prod values
3. **Same Scripts**: Scripts work in both environments (use --ENV parameter)
4. **Deploy**: `cd infra/stacks/prod-gluejobs && terraform apply`

---

**Status**: Ready for dev deployment and validation  
**Last Updated**: November 18, 2025

