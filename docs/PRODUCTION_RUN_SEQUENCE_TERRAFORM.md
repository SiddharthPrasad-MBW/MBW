# OMC Flywheel Cleanroom Production Run Sequence (Terraform Managed)

This document outlines the complete production run sequence for the OMC Flywheel Cleanroom bucketing solution, now managed with Terraform.

## 🏗️ **Infrastructure Overview**

### **Terraform-Managed Resources:**
- **4 Glue ETL Jobs** for data processing and bucketing
- **2 Glue Crawlers** for table discovery
- **1 IAM Role** with comprehensive permissions
- **2 S3 Buckets** for data storage and analysis
- **1 Glue Catalog Database** for metadata

### **Production Environment:**
- **Account**: `239083076653`
- **Region**: `us-east-1`
- **Profile**: `flywheel-prod`

## 📋 **Pre-Run Checklist**

### **1. Verify Infrastructure Status**
```bash
# Check Terraform state
cd /Users/patrick.spann/Documents/acx_omc_flywheel_cr/terraform
terraform plan

# Verify all resources are in sync
terraform show
```

### **2. Verify Data Availability**
```bash
# Check source data availability
aws s3 ls s3://omc-flywheel-data-us-east-1-prod/opus/infobase_attributes/raw_input/ --profile flywheel-prod
aws s3 ls s3://omc-flywheel-data-us-east-1-prod/opus/addressable_ids/raw_input/ --profile flywheel-prod

# Verify latest snapshot_dt
aws s3 ls s3://omc-flywheel-data-us-east-1-prod/opus/infobase_attributes/raw_input/ --profile flywheel-prod | grep snapshot_dt
```

### **3. Check Glue Job Status**
```bash
# List all Glue jobs
aws glue list-jobs --profile flywheel-prod --query 'JobNames'

# Check job configurations
aws glue get-job --job-name etl-omc-flywheel-prod-infobase-split-and-bucket --profile flywheel-prod
aws glue get-job --job-name etl-omc-flywheel-prod-addressable-bucket --profile flywheel-prod
aws glue get-job --job-name etl-omc-flywheel-prod-register-staged-tables --profile flywheel-prod
aws glue get-job --job-name etl-omc-flywheel-prod-create-athena-bucketed-tables --profile flywheel-prod
```

## 🚀 **Production Run Sequence**

### **Step 1: Data Processing and Bucketing**

#### **1.1 Infobase Attributes Processing**
```bash
# Run infobase split and bucket job
aws glue start-job-run \
  --job-name etl-omc-flywheel-prod-infobase-split-and-bucket \
  --profile flywheel-prod

# Monitor job progress
aws glue get-job-runs \
  --job-name etl-omc-flywheel-prod-infobase-split-and-bucket \
  --max-items 1 \
  --profile flywheel-prod
```

**Expected Output:**
- Bucketed data in: `s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_cluster/infobase_attributes/`
- Snapshot metadata: `s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_cluster/infobase_attributes/metadata/snapshot_dt.txt`

#### **1.2 Addressable IDs Processing**
```bash
# Run addressable bucket job
aws glue start-job-run \
  --job-name etl-omc-flywheel-prod-addressable-bucket \
  --profile flywheel-prod

# Monitor job progress
aws glue get-job-runs \
  --job-name etl-omc-flywheel-prod-addressable-bucket \
  --max-items 1 \
  --profile flywheel-prod
```

**Expected Output:**
- Bucketed data in: `s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_cluster/addressable_ids/`
- Snapshot metadata: `s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_cluster/addressable_ids/metadata/snapshot_dt.txt`

### **Step 2: Table Registration**

#### **2.1 Register Staged Tables**
```bash
# Run register staged tables job
aws glue start-job-run \
  --job-name etl-omc-flywheel-prod-register-staged-tables \
  --profile flywheel-prod

# Monitor job progress
aws glue get-job-runs \
  --job-name etl-omc-flywheel-prod-register-staged-tables \
  --max-items 1 \
  --profile flywheel-prod
```

**Expected Output:**
- External tables registered in Glue catalog
- Tables: `ext_ibe_01`, `ext_ibe_04`, `ext_miacs_01`, `ext_addressable_ids`
- Database: `omc_flywheel_prod`

### **Step 3: Create Bucketed Tables**

#### **3.1 Create Athena Bucketed Tables**
```bash
# Run create Athena bucketed tables job
aws glue start-job-run \
  --job-name etl-omc-flywheel-prod-create-athena-bucketed-tables \
  --profile flywheel-prod

# Monitor job progress
aws glue get-job-runs \
  --job-name etl-omc-flywheel-prod-create-athena-bucketed-tables \
  --max-items 1 \
  --profile flywheel-prod
```

**Expected Output:**
- True Hive bucketed tables created
- Tables: `bucketed_ibe_01`, `bucketed_ibe_04`, `bucketed_miacs_01`, `bucketed_addressable_ids`
- Database: `omc_flywheel_prod`

### **Step 4: Table Discovery**

#### **4.1 Run Crawlers**
```bash
# Start infobase attributes crawler
aws glue start-crawler \
  --name crw-omc-flywheel-prod-infobase-attributes-bucketed-cr \
  --profile flywheel-prod

# Start addressable IDs crawler
aws glue start-crawler \
  --name crw-omc-flywheel-prod-addressable-ids-bucketed-cr \
  --profile flywheel-prod

# Monitor crawler status
aws glue get-crawler --name crw-omc-flywheel-prod-infobase-attributes-bucketed-cr --profile flywheel-prod
aws glue get-crawler --name crw-omc-flywheel-prod-addressable-ids-bucketed-cr --profile flywheel-prod
```

**Expected Output:**
- Tables discovered and registered in Glue catalog
- Schema information updated
- Partition information updated

## 📊 **Monitoring and Verification**

### **1. Check Job Status**
```bash
# Get job run status
aws glue get-job-run \
  --job-name etl-omc-flywheel-prod-infobase-split-and-bucket \
  --run-id <RUN_ID> \
  --profile flywheel-prod

# Check job logs
aws logs describe-log-groups --log-group-name-prefix "/aws-glue/jobs" --profile flywheel-prod
```

### **2. Verify Data Output**
```bash
# Check bucketed data
aws s3 ls s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_cluster/infobase_attributes/ --profile flywheel-prod
aws s3 ls s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_cluster/addressable_ids/ --profile flywheel-prod

# Check final bucketed tables
aws s3 ls s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/cleanroom_tables/bucketed/ --profile flywheel-prod
```

### **3. Verify Tables in Glue Catalog**
```bash
# List tables in database
aws glue get-tables --database-name omc_flywheel_prod --profile flywheel-prod

# Check specific table
aws glue get-table --database-name omc_flywheel_prod --name bucketed_ibe_01 --profile flywheel-prod
```

## 🔧 **Terraform Management**

### **Infrastructure Updates**
```bash
# Navigate to Terraform directory
cd /Users/patrick.spann/Documents/acx_omc_flywheel_cr/terraform

# Review changes
terraform plan

# Apply changes
terraform apply

# View current state
terraform show
```

### **Resource Management**
```bash
# List all resources
terraform state list

# View specific resource
terraform state show aws_glue_job.infobase_split_and_bucket

# Import new resources
terraform import aws_glue_job.new_job job-name
```

## 🚨 **Troubleshooting**

### **Common Issues**

#### **1. Job Failures**
```bash
# Check job logs
aws logs describe-log-groups --log-group-name-prefix "/aws-glue/jobs" --profile flywheel-prod
aws logs get-log-events --log-group-name "/aws-glue/jobs/etl-omc-flywheel-prod-infobase-split-and-bucket" --log-stream-name <STREAM_NAME> --profile flywheel-prod
```

#### **2. Permission Errors**
```bash
# Check IAM role permissions
aws iam get-role --role-name omc_flywheel-prod-glue-role --profile flywheel-prod
aws iam list-attached-role-policies --role-name omc_flywheel-prod-glue-role --profile flywheel-prod
```

#### **3. S3 Access Issues**
```bash
# Test S3 access
aws s3 ls s3://omc-flywheel-data-us-east-1-prod/ --profile flywheel-prod
aws s3 ls s3://omc-flywheel-prod-analysis-data/ --profile flywheel-prod
```

### **Recovery Procedures**

#### **1. Restart Failed Jobs**
```bash
# Stop running job
aws glue stop-job-run --job-name <JOB_NAME> --run-id <RUN_ID> --profile flywheel-prod

# Start new run
aws glue start-job-run --job-name <JOB_NAME> --profile flywheel-prod
```

#### **2. Clean Up Partial Data**
```bash
# Remove partial output
aws s3 rm s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_cluster/infobase_attributes/ --recursive --profile flywheel-prod
aws s3 rm s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_cluster/addressable_ids/ --recursive --profile flywheel-prod
```

## 📈 **Performance Monitoring**

### **Job Performance Metrics**
- **Infobase Split & Bucket**: ~25-30 minutes (G.4X, 24 workers)
- **Addressable Bucket**: ~15-20 minutes (G.4X, 24 workers)
- **Register Staged Tables**: ~2-3 minutes (G.1X, 2 workers)
- **Create Athena Bucketed Tables**: ~20-25 minutes (G.4X, 10 workers)

### **Resource Utilization**
- **Total DPUs**: ~96 DPUs for heavy jobs
- **S3 Storage**: Monitor bucket sizes and costs
- **Athena Queries**: Monitor query performance and costs

## 🔄 **Monthly Run Process**

### **1. Data Preparation**
- Verify new snapshot data is available
- Check data quality and completeness
- Update any configuration changes

### **2. Infrastructure Updates**
```bash
# Update Terraform configuration if needed
cd /Users/patrick.spann/Documents/acx_omc_flywheel_cr/terraform
terraform plan
terraform apply
```

### **3. Execute Run Sequence**
- Follow the complete run sequence above
- Monitor each step for success
- Verify final output quality

### **4. Post-Run Validation**
- Verify all tables are created
- Check data quality and completeness
- Update documentation if needed

## 📚 **Documentation and Support**

### **Key Files**
- **Terraform Configuration**: `/Users/patrick.spann/Documents/acx_omc_flywheel_cr/terraform/`
- **Scripts**: `/Users/patrick.spann/Documents/acx_omc_flywheel_cr/scripts/`
- **Documentation**: `/Users/patrick.spann/Documents/acx_omc_flywheel_cr/docs/`

### **Support Contacts**
- **Data Engineering Team**: Primary support
- **AWS Support**: For infrastructure issues
- **Terraform Documentation**: For configuration management

## 🎯 **Success Criteria**

### **Run Completion**
- ✅ All 4 Glue jobs completed successfully
- ✅ All 2 crawlers completed successfully
- ✅ All tables created in Glue catalog
- ✅ Data available in final bucketed format
- ✅ Snapshot metadata properly tracked

### **Quality Assurance**
- ✅ Data integrity maintained
- ✅ Performance within expected ranges
- ✅ No errors in CloudWatch logs
- ✅ All S3 paths accessible
- ✅ Tables queryable in Athena

---

**Last Updated**: October 24, 2025  
**Version**: 2.0 (Terraform Managed)  
**Environment**: Production (Terraform Managed)
