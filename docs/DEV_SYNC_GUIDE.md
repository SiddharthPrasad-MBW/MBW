# DEV Environment Sync Guide

This guide helps you sync the DEV environment with the latest PROD configurations while maintaining DEV-specific naming and resources.

## 🎯 **Sync Objectives**

- ✅ **Keep DEV working** - Don't break existing functionality
- ✅ **Update configurations** - Apply PROD optimizations to DEV
- ✅ **Maintain naming** - Keep dev vs prod naming conventions
- ✅ **Update scripts** - Ensure DEV has latest script versions
- ✅ **Sync permissions** - Ensure DEV has same IAM permissions as PROD

## 📋 **Current State Analysis**

### **DEV Environment Status:**
- **12 Glue Jobs** (vs 4 in PROD)
- **6 Glue Crawlers** (vs 2 in PROD)
- **Latest scripts** already synced from PROD
- **Working configuration** - don't break this!

### **Key Differences:**
- DEV has more jobs (including old/experimental ones)
- DEV uses different S3 buckets and IAM roles
- DEV may have different job parameters

## 🔄 **Sync Strategy**

### **Phase 1: Script Sync (Already Done)**
✅ DEV already has the latest scripts from PROD

### **Phase 2: Job Configuration Sync**
Update the 4 core DEV jobs to match PROD configurations:

1. **`etl-omc-flywheel-dev-infobase-split-and-bucket`**
2. **`etl-omc-flywheel-dev-addressable-bucket`**
3. **`etl-omc-flywheel-dev-register-staged-tables`**
4. **`etl-omc-flywheel-dev-create-athena-bucketed-tables`**

### **Phase 3: IAM Permissions Sync**
Ensure DEV IAM role has same permissions as PROD

### **Phase 4: Crawler Sync**
Update crawler configurations to match PROD

## 🚀 **Automated Sync (Recommended)**

### **Run the Sync Script:**
```bash
cd /Users/patrick.spann/Documents/acx_omc_flywheel_cr/scripts
python3 sync_dev_with_prod.py
```

This script will:
- ✅ Get PROD job configurations
- ✅ Update DEV jobs with PROD settings
- ✅ Convert S3 paths from prod to dev
- ✅ Convert IAM role names from prod to dev
- ✅ Convert script locations to dev versions

## 🔧 **Manual Sync Steps**

### **Step 1: Update Core DEV Jobs**

#### **1.1 Infobase Split and Bucket Job**
```bash
# Get PROD configuration
export AWS_PROFILE=flywheel-prod
aws glue get-job --job-name etl-omc-flywheel-prod-infobase-split-and-bucket > prod_infobase_config.json

# Update DEV job (manual process)
export AWS_PROFILE=flywheel-dev
# Compare configurations and update as needed
```

#### **1.2 Addressable Bucket Job**
```bash
# Get PROD configuration
export AWS_PROFILE=flywheel-prod
aws glue get-job --job-name etl-omc-flywheel-prod-addressable-bucket > prod_addressable_config.json

# Update DEV job
export AWS_PROFILE=flywheel-dev
# Apply PROD configurations to DEV
```

#### **1.3 Register Staged Tables Job**
```bash
# Get PROD configuration
export AWS_PROFILE=flywheel-prod
aws glue get-job --job-name etl-omc-flywheel-prod-register-staged-tables > prod_register_config.json

# Update DEV job
export AWS_PROFILE=flywheel-dev
# Apply PROD configurations to DEV
```

#### **1.4 Create Athena Bucketed Tables Job**
```bash
# Get PROD configuration
export AWS_PROFILE=flywheel-prod
aws glue get-job --job-name etl-omc-flywheel-prod-create-athena-bucketed-tables > prod_athena_config.json

# Update DEV job
export AWS_PROFILE=flywheel-dev
# Apply PROD configurations to DEV
```

### **Step 2: Update IAM Permissions**

#### **2.1 Check Current DEV IAM Role**
```bash
export AWS_PROFILE=flywheel-dev
aws iam get-role --role-name omc_flywheel-dev-glue-role
aws iam list-attached-role-policies --role-name omc_flywheel-dev-glue-role
```

#### **2.2 Compare with PROD IAM Role**
```bash
export AWS_PROFILE=flywheel-prod
aws iam get-role --role-name omc_flywheel-prod-glue-role
aws iam list-attached-role-policies --role-name omc_flywheel-prod-glue-role
```

#### **2.3 Update DEV IAM Permissions**
Add any missing permissions that PROD has:
- S3 access permissions
- Athena permissions
- Glue catalog permissions

### **Step 3: Update Crawler Configurations**

#### **3.1 Check Current DEV Crawlers**
```bash
export AWS_PROFILE=flywheel-dev
aws glue get-crawler --name crw-omc-flywheel-dev-infobase-attributes-bucketed-cr
aws glue get-crawler --name crw-omc-flywheel-dev-addressable-ids-bucketed-cr
```

#### **3.2 Compare with PROD Crawlers**
```bash
export AWS_PROFILE=flywheel-prod
aws glue get-crawler --name crw-omc-flywheel-prod-infobase-attributes-bucketed-cr
aws glue get-crawler --name crw-omc-flywheel-prod-addressable-ids-bucketed-cr
```

## 📊 **Configuration Mapping**

### **S3 Bucket Mappings:**
- **PROD**: `omc-flywheel-data-us-east-1-prod` → **DEV**: `omc-flywheel-data-us-east-1-dev`
- **PROD**: `omc-flywheel-prod-analysis-data` → **DEV**: `omc-flywheel-dev-analysis-data`
- **PROD**: `aws-glue-assets-239083076653-us-east-1` → **DEV**: `aws-glue-assets-417649522250-us-east-1`

### **IAM Role Mappings:**
- **PROD**: `omc_flywheel-prod-glue-role` → **DEV**: `omc_flywheel-dev-glue-role`

### **Database Mappings:**
- **PROD**: `omc_flywheel_prod` → **DEV**: `omc_flywheel_dev`

### **Script Mappings:**
- **PROD**: `etl-omc-flywheel-prod-*` → **DEV**: `etl-omc-flywheel-dev-*`

## ✅ **Verification Steps**

### **1. Test DEV Jobs**
```bash
# Test each core job
export AWS_PROFILE=flywheel-dev

# Test infobase job
aws glue start-job-run --job-name etl-omc-flywheel-dev-infobase-split-and-bucket

# Test addressable job
aws glue start-job-run --job-name etl-omc-flywheel-dev-addressable-bucket

# Test register job
aws glue start-job-run --job-name etl-omc-flywheel-dev-register-staged-tables

# Test Athena job
aws glue start-job-run --job-name etl-omc-flywheel-dev-create-athena-bucketed-tables
```

### **2. Verify Permissions**
```bash
# Check if jobs can access S3
aws s3 ls s3://omc-flywheel-data-us-east-1-dev/ --profile flywheel-dev
aws s3 ls s3://omc-flywheel-dev-analysis-data/ --profile flywheel-dev
```

### **3. Verify Scripts**
```bash
# Check script locations
aws s3 ls s3://aws-glue-assets-417649522250-us-east-1/scripts/ --profile flywheel-dev
```

## 🚨 **Troubleshooting**

### **Common Issues:**

#### **1. Permission Errors**
- Check IAM role permissions
- Verify S3 bucket access
- Ensure Athena permissions

#### **2. Script Not Found**
- Verify script exists in DEV S3 bucket
- Check script name in job configuration
- Ensure script was copied from PROD

#### **3. Job Configuration Errors**
- Compare with PROD configuration
- Check parameter values
- Verify S3 paths are correct

### **Recovery Steps:**
1. **Backup current DEV configuration**
2. **Test changes incrementally**
3. **Rollback if issues occur**
4. **Verify each step before proceeding**

## 📈 **Expected Results**

After sync, DEV should have:
- ✅ **Same job configurations** as PROD (with dev naming)
- ✅ **Same IAM permissions** as PROD
- ✅ **Latest scripts** from PROD
- ✅ **Same performance optimizations** as PROD
- ✅ **Working functionality** maintained

## 🎯 **Next Steps**

1. **Run automated sync script**
2. **Verify all configurations**
3. **Test DEV jobs**
4. **Update documentation**
5. **Create DEV run sequence**

---

**Last Updated**: October 24, 2025  
**Version**: 1.0  
**Environment**: DEV Sync with PROD
