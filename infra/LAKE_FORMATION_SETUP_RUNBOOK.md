# Lake Formation Setup & Consumer Policy Runbook

**Purpose**: Operational runbook for enabling Lake Formation and setting up Cleanroom consumer policies  
**Audience**: DevOps Engineers, Data Engineers  
**Last Updated**: October 28, 2025  
**Status**: Production Ready

---

## 📋 **Overview**

This runbook provides step-by-step instructions for:
1. **Enabling Lake Formation** infrastructure via Terraform
2. **Creating and configuring** Cleanroom consumer IAM role and policies
3. **Validating** the complete setup

---

## 🎯 **Prerequisites**

- [ ] AWS CLI configured with appropriate profiles (`flywheel-dev`, `flywheel-prod`)
- [ ] Terraform >= 1.0 installed
- [ ] Lake Formation admin permissions
- [ ] IAM permissions to create roles and policies
- [ ] Access to both dev and prod AWS accounts
- [ ] Git repository cloned locally

---

## 🚀 **Runbook: Complete Lake Formation Setup**

### **Part 1: Create Consumer Role & IAM Policies**

#### **Step 1.1: Create Consumer Role (Dev)**

```bash
# Set AWS profile
export AWS_PROFILE=flywheel-dev

# Create the consumer role
aws iam create-role \
  --role-name omc_flywheel-dev-cleanroom-consumer \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {
        "Service": "athena.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }]
  }' \
  --region us-east-1

# Verify role creation
aws iam get-role --role-name omc_flywheel-dev-cleanroom-consumer
```

**Expected Output**: Role ARN and trust policy confirmation

#### **Step 1.2: Create IAM Policy Files**

Create policy files locally:

**File: `consumer-policy-data-read-dev.json`**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListBucketBucketed",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::omc-flywheel-data-us-east-1-dev",
      "Condition": {
        "StringLike": {
          "s3:prefix": "omc_cleanroom_data/cleanroom_tables/bucketed/*"
        }
      }
    },
    {
      "Sid": "ReadBucketedOnly",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:GetObjectTagging"],
      "Resource": "arn:aws:s3:::omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/cleanroom_tables/bucketed/*"
    }
  ]
}
```

**File: `consumer-policy-athena-dev.json`**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AthenaResultsWrite",
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::omc-flywheel-dev-analysis-data",
        "arn:aws:s3:::omc-flywheel-dev-analysis-data/query-results/cleanroom/*"
      ]
    },
    {
      "Sid": "AthenaAPI",
      "Effect": "Allow",
      "Action": [
        "athena:StartQueryExecution",
        "athena:GetQueryExecution",
        "athena:GetQueryResults",
        "athena:ListWorkGroups",
        "athena:GetWorkGroup",
        "athena:StopQueryExecution"
      ],
      "Resource": "*"
    },
    {
      "Sid": "GlueCatalogRead",
      "Effect": "Allow",
      "Action": [
        "glue:GetDatabase",
        "glue:GetDatabases",
        "glue:GetTable",
        "glue:GetTables",
        "glue:GetPartitions"
      ],
      "Resource": "*"
    }
  ]
}
```

#### **Step 1.3: Create and Attach IAM Policies (Dev)**

```bash
# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create data read policy
aws iam create-policy \
  --policy-name omc-flywheel-dev-cleanroom-data-read \
  --policy-document file://consumer-policy-data-read-dev.json \
  --region us-east-1

# Create Athena results write policy
aws iam create-policy \
  --policy-name omc-flywheel-dev-cleanroom-athena-results \
  --policy-document file://consumer-policy-athena-dev.json \
  --region us-east-1

# Attach policies to role
aws iam attach-role-policy \
  --role-name omc_flywheel-dev-cleanroom-consumer \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/omc-flywheel-dev-cleanroom-data-read \
  --region us-east-1

aws iam attach-role-policy \
  --role-name omc_flywheel-dev-cleanroom-consumer \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/omc-flywheel-dev-cleanroom-athena-results \
  --region us-east-1

# Verify policies attached
aws iam list-attached-role-policies --role-name omc_flywheel-dev-cleanroom-consumer
```

**Expected Output**: Both policies listed as attached

#### **Step 1.4: Repeat for Production (When Ready)**

```bash
# Switch to prod profile
export AWS_PROFILE=flywheel-prod

# Repeat steps 1.1-1.3 with prod values:
# - Role name: omc_flywheel-prod-cleanroom-consumer
# - Bucket: omc-flywheel-data-us-east-1-prod
# - Analysis bucket: omc-flywheel-prod-analysis-data
# - Policy names: omc-flywheel-prod-cleanroom-*
```

---

### **Part 2: Enable Lake Formation via Terraform**

#### **Step 2.1: Verify Terraform Configuration**

```bash
# Navigate to dev environment
cd infra/envs/dev

# Check configuration
cat main.tf | grep -A 10 "writer_principals\|reader_principals"

# Verify reader role is configured
cat main.tf | grep "omc_flywheel-dev-cleanroom-consumer"
```

**Expected Output**: 
- `writer_principals` includes Glue role
- `reader_principals` includes consumer role

#### **Step 2.2: Initialize Terraform**

```bash
# Initialize Terraform
terraform init

# Verify backend and providers initialized
terraform version
```

**Expected Output**: Terraform initialized successfully

#### **Step 2.3: Plan Terraform Changes**

```bash
# Review planned changes
terraform plan

# Check for:
# - Lake Formation resources being created
# - Permissions being granted to writer role
# - Permissions being granted to reader role
# - No unexpected changes
```

**Expected Output**: Plan shows:
- `aws_lakeformation_resource` (target and source)
- `aws_lakeformation_permissions` (writers and readers)
- `aws_glue_catalog_database`

#### **Step 2.4: Apply Terraform Configuration**

```bash
# Apply changes
terraform apply

# Review output and confirm by typing 'yes'
```

**Expected Output**:
```
Apply complete! Resources: X added, Y changed, Z destroyed.
```

#### **Step 2.5: Verify Deployment**

```bash
# Check registered resources
aws lakeformation list-resources --region us-east-1 --profile flywheel-dev

# Should show:
# - arn:aws:s3:::omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_cluster
# - arn:aws:s3:::omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/cleanroom_tables/bucketed

# Check writer role permissions
aws lakeformation list-permissions \
  --principal "arn:aws:iam::${ACCOUNT_ID}:role/omc_flywheel-dev-glue-role" \
  --region us-east-1 --profile flywheel-dev

# Check reader role permissions
aws lakeformation list-permissions \
  --principal "arn:aws:iam::${ACCOUNT_ID}:role/omc_flywheel-dev-cleanroom-consumer" \
  --region us-east-1 --profile flywheel-dev

# Verify Glue database
aws glue get-database --name omc_flywheel_dev --region us-east-1 --profile flywheel-dev
```

**Expected Output**: All resources exist and permissions are granted

---

### **Part 3: Test Setup**

#### **Step 3.1: Test Writer Role (CTAS Operations)**

```bash
# Test CTAS job with writer role
aws glue start-job-run \
  --job-name etl-omc-flywheel-dev-create-athena-bucketed-tables \
  --arguments '{"--TABLES_FILTER": "ibe_01_a"}' \
  --region us-east-1 \
  --profile flywheel-dev

# Get job run ID
JOB_RUN_ID=$(aws glue get-job-runs \
  --job-name etl-omc-flywheel-dev-create-athena-bucketed-tables \
  --max-items 1 \
  --query 'JobRuns[0].Id' \
  --output text)

# Wait and check status
aws glue get-job-run \
  --job-name etl-omc-flywheel-dev-create-athena-bucketed-tables \
  --run-id $JOB_RUN_ID \
  --region us-east-1 \
  --profile flywheel-dev \
  --query 'JobRun.JobRunState'
```

**Expected Output**: `SUCCEEDED` (no Lake Formation permission errors)

#### **Step 3.2: Test Reader Role (Cleanroom Access & Athena Query)**

```bash
# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Start query execution (Athena will use the role configured in workgroup or caller context)
aws athena start-query-execution \
  --query-string "SELECT COUNT(*) as total_rows FROM omc_flywheel_dev.bucketed_ibe_01_a LIMIT 1" \
  --result-configuration "OutputLocation=s3://omc-flywheel-dev-analysis-data/query-results/cleanroom/" \
  --work-group primary \
  --region us-east-1 \
  --profile flywheel-dev

# Capture query execution ID from output
# Or start a new query and capture the ID
QUERY_EXECUTION_ID=$(aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM omc_flywheel_dev.bucketed_ibe_01_a" \
  --result-configuration "OutputLocation=s3://omc-flywheel-dev-analysis-data/query-results/cleanroom/" \
  --work-group primary \
  --region us-east-1 \
  --profile flywheel-dev \
  --query 'QueryExecutionId' \
  --output text)

# Wait for query to complete
echo "Waiting for query to complete..."
sleep 10

# Check query status
aws athena get-query-execution \
  --query-execution-id $QUERY_EXECUTION_ID \
  --region us-east-1 \
  --profile flywheel-dev \
  --query 'QueryExecution.Status.State' \
  --output text

# Get query results (should succeed if permissions are correct)
aws athena get-query-results \
  --query-execution-id $QUERY_EXECUTION_ID \
  --region us-east-1 \
  --profile flywheel-dev \
  --max-items 1

# Verify results accessible in S3
aws s3 ls s3://omc-flywheel-dev-analysis-data/query-results/cleanroom/ --profile flywheel-dev | head -5
```

**Note**: For production Cleanroom access:
1. **Configure Athena Workgroup**: Set workgroup execution role to consumer role via AWS Console
2. **Verify Lake Formation Permissions**: Ensure SELECT permissions granted via Terraform
3. **Test Access**: Execute queries against `bucketed_*` tables
4. **Results Location**: Query results written to configured S3 results bucket

**Expected Output**: 
- Query execution succeeds with `State: SUCCEEDED`
- Query results returned via API
- Results files present in S3 results bucket
- No Lake Formation permission errors

---

### **Part 4: Configure Cleanroom Access**

#### **Step 4.1: Verify Consumer Role Permissions**

```bash
# Verify Lake Formation SELECT permission on bucketed tables
aws lakeformation list-permissions \
  --principal "arn:aws:iam::${ACCOUNT_ID}:role/omc_flywheel-dev-cleanroom-consumer" \
  --region us-east-1 --profile flywheel-dev \
  --query 'PrincipalResourcePermissions[?contains(Permissions, `SELECT`)]'

# Verify IAM policies attached
aws iam list-attached-role-policies \
  --role-name omc_flywheel-dev-cleanroom-consumer \
  --profile flywheel-dev
```

**Expected Output**: 
- SELECT permission present for tables
- Data read and Athena policies attached

#### **Step 4.2: Configure Athena Workgroup for Cleanroom**

```bash
# Option 1: Via AWS Console (Recommended for Production)
# 1. Navigate to: Athena → Workgroups → primary
# 2. Click "Edit workgroup"
# 3. Under "Query result location and encryption":
#    - Output location: s3://omc-flywheel-dev-analysis-data/query-results/cleanroom/
#    - Encryption: Server-side encryption with Amazon S3-managed keys (SSE-S3)
# 4. Under "Execution role" (if available):
#    - Select: Use a custom role
#    - Role: omc_flywheel-dev-cleanroom-consumer
# 5. Save changes

# Option 2: Via CLI (update workgroup settings)
aws athena update-work-group \
  --work-group primary \
  --configuration-updates "{
    \"EnforceWorkGroupConfiguration\": true,
    \"ResultConfiguration\": {
      \"OutputLocation\": \"s3://omc-flywheel-dev-analysis-data/query-results/cleanroom/\",
      \"EncryptionConfiguration\": {\"EncryptionOption\": \"SSE_S3\"}
    }
  }" \
  --region us-east-1 \
  --profile flywheel-dev
```

#### **Step 4.3: Test Cleanroom Query Access**

```bash
# Test query against bucketed table
aws athena start-query-execution \
  --query-string "
    SELECT 
      COUNT(*) as total_rows,
      COUNT(DISTINCT customer_user_id) as distinct_users
    FROM omc_flywheel_dev.bucketed_ibe_01_a
  " \
  --result-configuration "OutputLocation=s3://omc-flywheel-dev-analysis-data/query-results/cleanroom/" \
  --work-group primary \
  --region us-east-1 \
  --profile flywheel-dev

# Verify results are accessible
aws s3 ls s3://omc-flywheel-dev-analysis-data/query-results/cleanroom/ \
  --recursive \
  --profile flywheel-dev | tail -5
```

**Expected Output**: 
- Query executes successfully
- Results files written to S3 results bucket
- No Lake Formation permission errors

---

## 🔍 **Validation Checklist**

### **Pre-Deployment Checks**
- [ ] AWS CLI configured with correct profiles
- [ ] Terraform installed and accessible
- [ ] Consumer role created (or will be created)
- [ ] Policy files prepared
- [ ] Configuration files reviewed

### **Post-Deployment Validation**
- [ ] Consumer role exists in IAM
- [ ] IAM policies attached to consumer role
- [ ] Lake Formation resources registered
- [ ] Writer role has full permissions
- [ ] Reader role has read-only permissions
- [ ] Glue database exists
- [ ] CTAS job completes successfully
- [ ] No Lake Formation permission errors
- [ ] **Cleanroom access verified**: Consumer role can query bucketed tables
- [ ] **Athena results access verified**: Query results accessible in S3
- [ ] **Athena queries succeed**: Test queries execute without permission errors

### **Troubleshooting Checks**
- [ ] All S3 paths exist and are accessible
- [ ] Role ARNs match configuration
- [ ] Lake Formation admin permissions verified
- [ ] Terraform state is consistent

---

## 🚨 **Troubleshooting**

### **Issue: Consumer Role Not Found**

```bash
# Check if role exists
aws iam get-role --role-name omc_flywheel-dev-cleanroom-consumer

# If missing, create it (Step 1.1)
# If exists but Terraform fails, check role ARN in main.tf
```

### **Issue: Lake Formation Permission Errors**

```bash
# Check current permissions
aws lakeformation list-permissions \
  --principal "arn:aws:iam::ACCOUNT_ID:role/omc_flywheel-dev-cleanroom-consumer" \
  --region us-east-1 --profile flywheel-dev

# Re-run Terraform apply
cd infra/envs/dev
terraform apply
```

### **Issue: CTAS Job Fails**

```bash
# Check job logs
aws logs get-log-events \
  --log-group-name "/aws-glue/jobs/output" \
  --log-stream-name "jr_<JOB_RUN_ID>" \
  --region us-east-1 --profile flywheel-dev

# Verify writer role permissions
aws lakeformation list-permissions \
  --principal "arn:aws:iam::ACCOUNT_ID:role/omc_flywheel-dev-glue-role" \
  --region us-east-1 --profile flywheel-dev
```

### **Issue: Terraform Apply Fails**

```bash
# Check Terraform state
terraform state list

# Validate configuration
terraform validate

# Check for provider issues
terraform providers
```

---

## 📋 **Production Deployment**

### **Enable Production Lake Formation**

```bash
# Navigate to prod environment
cd infra/envs/prod

# Edit main.tf and set enable = true
# Change: enable = false to enable = true

# Initialize and plan
terraform init
terraform plan

# Review changes carefully
# Apply when ready
terraform apply
```

### **Production Validation**

```bash
# Verify all resources
aws lakeformation list-resources --region us-east-1 --profile flywheel-prod

# Test with small dataset first
aws glue start-job-run \
  --job-name etl-omc-flywheel-prod-create-athena-bucketed-tables \
  --arguments '{"--TABLES_FILTER": "ibe_01_a"}' \
  --region us-east-1 \
  --profile flywheel-prod
```

---

## 📚 **Related Documentation**

- [Deployment Guide](infra/DEPLOYMENT_GUIDE.md) - Detailed deployment instructions
- [Consumer Role IAM Policies](infra/CONSUMER_ROLE_IAM_POLICIES.md) - Policy templates
- [Permissions Summary](infra/PERMISSIONS_SUMMARY.md) - Permission breakdown
- [Lake Formation README](infra/README.md) - Infrastructure overview

---

## ✅ **Success Criteria**

Setup is complete when:

1. ✅ Consumer role created in IAM
2. ✅ IAM policies attached to consumer role
3. ✅ Terraform applied successfully
4. ✅ Lake Formation resources registered
5. ✅ Writer role has full permissions
6. ✅ Reader role has read-only permissions
7. ✅ CTAS job completes without errors
8. ✅ **Bucketed tables accessible via consumer role**
9. ✅ **Cleanroom queries succeed**: Consumer role can query bucketed_* tables
10. ✅ **Athena results accessible**: Query results written to and readable from S3
11. ✅ **No permission errors**: All operations complete without Lake Formation errors

---

**Runbook Version**: 1.0  
**Last Updated**: October 28, 2025  
**Maintained By**: Data Engineering Team
