# Lake Formation Source Data Path Fix - Testing Plan

## 🎯 **Issue Identified & Resolved**

**Problem**: The initial Lake Formation module was missing registration of source data paths where `ext_*` tables point to, causing CTAS operations to fail with "Insufficient Lake Formation permissions" when reading from external tables.

**Root Cause**: CTAS operations read from `ext_*` tables (pointing to `split_cluster/` data) but Lake Formation only registered the target `bucketed/` path, not the source path.

## ✅ **Fix Applied**

### **Complete Data Flow Now Registered**

```
Raw Data → Processed Data → External Tables → CTAS → Bucketed Tables
   ↓            ↓              ↓              ↓         ↓
opus/    split_cluster/    ext_* tables   CTAS job   bucketed_*
```

### **Lake Formation Registration**

1. **Target Path**: `s3://bucket/omc_cleanroom_data/cleanroom_tables/bucketed/`
   - Where CTAS writes bucketed tables
   - ✅ Previously registered

2. **Source Path**: `s3://bucket/omc_cleanroom_data/split_cluster/`
   - Where `ext_*` tables point to (CTAS reads from)
   - ✅ **NOW REGISTERED** (was missing)

3. **Raw Source Path**: `s3://bucket/opus/` (optional)
   - Original input data
   - ✅ Available for future governance

### **Permissions Granted**

- **DATA_LOCATION_ACCESS** on both source and target buckets
- **Database permissions**: CREATE_TABLE, ALTER, DROP, DESCRIBE
- **Table permissions**: SELECT, DESCRIBE (wildcard for all tables)

## 🧪 **Testing Plan for Tomorrow**

### **Phase 1: Deploy Dev Environment**

```bash
cd infra/envs/dev
terraform init
terraform plan
terraform apply
```

**Expected Output**:
- Lake Formation data lake settings configured
- S3 paths registered:
  - `s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_cluster/`
  - `s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/cleanroom_tables/bucketed/`
- Permissions granted to `omc_flywheel-dev-glue-role`

### **Phase 2: Validate Registration**

```bash
# Check registered resources
aws lakeformation list-resources --region us-east-1 --profile flywheel-dev

# Should show both paths:
# arn:aws:s3:::omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_cluster
# arn:aws:s3:::omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/cleanroom_tables/bucketed
```

### **Phase 3: Test CTAS Operations**

```bash
# Test with single table first
aws glue start-job-run \
  --job-name etl-omc-flywheel-dev-create-athena-bucketed-tables \
  --arguments '{"--TABLES_FILTER": "ibe_01_a"}' \
  --region us-east-1 \
  --profile flywheel-dev
```

**Success Criteria**:
- ✅ Job completes without Lake Formation permission errors
- ✅ Bucketed table `bucketed_ibe_01_a` created in Glue catalog
- ✅ Data written to S3 under Lake Formation governance
- ✅ No "Insufficient Lake Formation permissions" errors

### **Phase 4: Test Multiple Tables**

```bash
# Test with multiple tables
aws glue start-job-run \
  --job-name etl-omc-flywheel-dev-create-athena-bucketed-tables \
  --arguments '{"--TABLES_FILTER": "ibe_01_a,ibe_02_a"}' \
  --region us-east-1 \
  --profile flywheel-dev
```

### **Phase 5: Verify Data Access**

```bash
# Check created tables
aws glue get-table --database-name omc_flywheel_dev --name bucketed_ibe_01_a --region us-east-1 --profile flywheel-dev

# Verify S3 data
aws s3 ls s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/cleanroom_tables/bucketed/ibe_01_a/ --region us-east-1 --profile flywheel-dev
```

## 🔍 **Validation Checklist**

### **Pre-Test Verification**
- [ ] Dev environment Terraform configuration updated
- [ ] Source paths correctly configured in module
- [ ] Glue role has necessary permissions
- [ ] External tables (`ext_*`) exist and point to correct S3 paths

### **During Test**
- [ ] Terraform apply completes successfully
- [ ] Lake Formation resources registered correctly
- [ ] CTAS job starts without immediate errors
- [ ] Job completes with SUCCESS status
- [ ] Bucketed tables created in Glue catalog
- [ ] Data written to correct S3 locations

### **Post-Test Verification**
- [ ] All expected bucketed tables exist
- [ ] S3 data accessible and properly formatted
- [ ] No Lake Formation permission errors in logs
- [ ] Performance metrics within expected ranges

## 🚨 **Troubleshooting Guide**

### **Common Issues & Solutions**

**"Insufficient Lake Formation permissions on split_cluster"**
- ✅ **Fixed**: Source path now registered
- **Verify**: Check `aws lakeformation list-resources`

**"Resource does not exist"**
- **Check**: S3 paths exist and are accessible
- **Verify**: Bucket names and prefixes are correct

**"Access denied on bucketed path"**
- **Check**: Target path registration
- **Verify**: DATA_LOCATION_ACCESS permissions

**CTAS job fails immediately**
- **Check**: Glue role permissions
- **Verify**: Database exists and is accessible

### **Debug Commands**

```bash
# Check Lake Formation registration
aws lakeformation list-resources --region us-east-1 --profile flywheel-dev

# Check permissions for Glue role
aws lakeformation list-permissions \
  --principal "arn:aws:iam::ACCOUNT_ID:role/omc_flywheel-dev-glue-role" \
  --region us-east-1 --profile flywheel-dev

# Check Glue database
aws glue get-database --name omc_flywheel_dev --region us-east-1 --profile flywheel-dev

# Check external tables
aws glue get-tables --database-name omc_flywheel_dev --region us-east-1 --profile flywheel-dev
```

## 📊 **Expected Results**

### **Successful Deployment**
- Lake Formation enabled for dev environment
- Both source and target S3 paths registered
- Glue role has comprehensive permissions
- CTAS operations work without permission errors

### **Performance Expectations**
- CTAS job completion time: 2-5 minutes per table
- Data written in proper Parquet format
- Bucketed tables optimized for Cleanroom queries
- No Lake Formation blocking operations

## 🎯 **Success Criteria**

The fix is successful when:

1. **✅ Terraform Deployment**: Dev environment deploys without errors
2. **✅ Path Registration**: Both source and target paths registered with Lake Formation
3. **✅ CTAS Operations**: Jobs complete without Lake Formation permission errors
4. **✅ Data Creation**: Bucketed tables created successfully
5. **✅ Data Access**: S3 data accessible and properly formatted

## 📚 **Related Documentation**

- [Lake Formation Infrastructure README](infra/README.md)
- [Deployment Guide](infra/DEPLOYMENT_GUIDE.md)
- [Current Process Flow](docs/CURRENT_PROCESS_FLOW.md)
- [Production Run Sequence](docs/PRODUCTION_RUN_SEQUENCE.md)

## 🔄 **Next Steps After Successful Test**

1. **Document Results**: Record any issues or observations
2. **Performance Analysis**: Check job completion times and data quality
3. **Prod Preparation**: Plan production deployment with `enable = true`
4. **Cleanroom Setup**: Configure Cleanroom role permissions for bucketed tables

---

**Fix Applied**: October 28, 2025  
**Testing Scheduled**: Tomorrow  
**Status**: Ready for Dev Environment Testing  
**Confidence Level**: High (comprehensive fix applied)
