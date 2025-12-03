# Deployment Guide

## 🚀 Deployment Overview

This guide covers deploying the ACX OMC Flywheel infrastructure to different environments using Terraform.

## 📋 Prerequisites

### Required Tools
- **Terraform**: >= 1.0
- **AWS CLI**: >= 2.0
- **Git**: For version control
- **jq**: For JSON processing (optional)

### AWS Configuration
```bash
# Configure AWS credentials
aws configure --profile flywheel-prod

# Verify access
aws sts get-caller-identity --profile flywheel-prod
```

## 🏗️ Environment Setup

### 1. Production Environment (Current)

#### Configuration
- **Account**: 239083076653
- **Region**: us-east-1
- **Profile**: flywheel-prod
- **State**: Local (consider S3 backend for production)

#### Deployment Steps
```bash
# Navigate to production environment
cd terraform/environments/prod

# Initialize Terraform
terraform init

# Review current state
terraform plan

# Apply changes (if any)
terraform apply
```

### 2. Development Environment (Future)

#### Configuration
- **Account**: [Development Account ID]
- **Region**: us-east-1
- **Profile**: flywheel-dev
- **State**: S3 backend

#### Setup Steps
```bash
# Create development environment
mkdir -p terraform/environments/dev
cd terraform/environments/dev

# Copy production configuration
cp ../prod/*.tf .

# Modify for development
# - Change resource names
# - Update S3 bucket names
# - Adjust worker counts
# - Update tags
```

### 3. Staging Environment (Future)

#### Configuration
- **Account**: [Staging Account ID]
- **Region**: us-east-1
- **Profile**: flywheel-staging
- **State**: S3 backend

## 🔧 Configuration Management

### Environment Variables

#### Required Variables
```bash
export AWS_PROFILE=flywheel-prod
export TF_VAR_environment=prod
export TF_VAR_project_name=acx-omc-flywheel-p0
export TF_VAR_owner=data-team
```

#### Optional Variables
```bash
export TF_VAR_worker_count=24
export TF_VAR_worker_type=G.1X
export TF_VAR_timeout=600
```

### Terraform Variables

#### Production Variables (`variables.tf`)
```hcl
variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "acx-omc-flywheel-p0"
}

variable "owner" {
  description = "Resource owner"
  type        = string
  default     = "data-team"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}
```

## 🚀 Deployment Procedures

### Initial Deployment

#### 1. First-Time Setup
```bash
# Clone repository
git clone <repository-url>
cd acx_omc_flywheel_p0

# Navigate to environment
cd terraform/environments/prod

# Initialize Terraform
terraform init

# Import existing resources (already done)
# terraform import aws_glue_job.job_name job-name

# Review configuration
terraform plan

# Apply configuration
terraform apply
```

#### 2. Resource Import (Already Completed)
```bash
# All resources have been imported:
# - 3 Glue Jobs
# - 4 Glue Crawlers  
# - 2 Glue Databases
# - 1 IAM Role
# - 3 S3 Buckets

# Verify current state
terraform state list
```

### Updates and Changes

#### 1. Making Changes
```bash
# Edit Terraform configuration
vim terraform_config_*.tf

# Review changes
terraform plan

# Apply changes
terraform apply
```

#### 2. Adding New Resources
```bash
# Add new resource to configuration
# Example: New Glue job

# Import existing resource (if it exists in AWS)
terraform import aws_glue_job.new_job job-name

# Or create new resource
terraform apply
```

#### 3. Removing Resources
```bash
# Remove from configuration
# Remove resource block from .tf file

# Remove from state (if needed)
terraform state rm aws_glue_job.old_job

# Apply changes
terraform apply
```

## 🔒 Security Considerations

### IAM Permissions

#### Required Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "glue:*",
        "s3:*",
        "iam:PassRole",
        "logs:*"
      ],
      "Resource": "*"
    }
  ]
}
```

#### Least Privilege Approach
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "glue:GetJob",
        "glue:StartJobRun",
        "glue:GetJobRun",
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:glue:*:*:job/*",
        "arn:aws:s3:::omc-flywheel-*/*"
      ]
    }
  ]
}
```

### State Management

#### Local State (Current)
```bash
# State stored locally
ls -la terraform.tfstate

# Backup state
cp terraform.tfstate terraform.tfstate.backup
```

#### S3 Backend (Recommended for Production)
```hcl
terraform {
  backend "s3" {
    bucket         = "acx-omc-flywheel-p0-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "acx-omc-flywheel-p0-terraform-locks"
  }
}
```

## 📊 Data Monitoring & Quality Assurance

### Comprehensive Data Monitoring Solution

The deployment includes an advanced data monitoring system that provides comprehensive quality checks for Cleanroom tables.

#### **Monitoring Features**

1. **Record Count Validation**
   - Compares `part_` tables against `ext_` tables (or other `part_` tables)
   - Configurable tolerance (default: exact 100% match)
   - Identifies data loss or duplication issues

2. **Key Quality Checks**
   - Validates `customer_base_id` is NOT NULL
   - Ensures `customer_base_id` is UNIQUE across all records
   - Prevents data integrity issues in Cleanroom queries

3. **Schema Contract Enforcement**
   - **Partitioned Tables**: Must contain `customer_base_id` and `id_bucket:int`, partitioned by `id_bucket`
   - **External Tables**: Must contain `customer_base_id` for comparison
   - Validates data types and partition structure

4. **Partition Integrity**
   - Verifies all 256 `id_bucket` partitions exist in S3
   - Checks Glue catalog partition registration
   - Auto-repair missing partitions via MSCK REPAIR

5. **Data Freshness**
   - Monitors `snapshot_dt` metadata files
   - Configurable freshness window (default: 45 days)
   - Cross-checks with raw input data

6. **File Size Hygiene** (Optional)
   - Samples partition files for size validation
   - Identifies over/under-sized files
   - Configurable size thresholds

#### **Monitoring Job Configuration**

```hcl
resource "aws_glue_job" "data_monitor" {
  name         = "etl-omc-flywheel-prod-generate-data-monitor-report"
  role_arn     = aws_iam_role.glue_role.arn
  glue_version = "4.0"

  command {
    name            = "pythonshell"
    python_version  = "3.9"
    script_location = "s3://${local.glue_assets_bucket}/scripts/data_monitor.py"
  }

  default_arguments = {
    "--region"                = "us-east-1"
    "--database"              = "omc_flywheel_prod"
    "--table_prefix"          = "part_"
    "--bucket_count"          = "256"
    "--report_bucket"         = "omc-flywheel-prod-analysis-data"
    "--report_prefix"         = "data-monitor/"
    "--auto_repair"           = "athena"
    "--athena_workgroup"      = "primary"
    "--athena_results"        = "s3://omc-flywheel-prod-analysis-data/query-results/monitor/"
    "--strict_snapshot"       = "true"
    "--freshness_window_days" = "45"

    # Counts & schema/PK checks
    "--count_check_enabled"   = "true"
    "--compare_source_type"   = "ext"
    "--count_tolerance_pct"   = "0"
    "--pk_column"             = "customer_base_id"

    # Optional file-size hygiene
    "--file_size_check"       = "false"
    "--file_size_min_mb"      = "64"
    "--file_size_max_mb"      = "1024"
  }
}
```

#### **Cleanrooms Reporting Job Configuration**

```hcl
resource "aws_glue_job" "generate_cleanrooms_report" {
  name         = "etl-omc-flywheel-prod-generate-cleanrooms-report"
  role_arn     = aws_iam_role.glue_role.arn
  glue_version = "5.0"

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "s3://${local.glue_assets_bucket}/scripts/generate-cleanrooms-report.py"
  }

  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 60

  default_arguments = {
    "--region"        = "us-east-1"
    "--database"      = "omc_flywheel_prod"
    "--table-prefix"  = "part_"
    "--membership-id" = "6610c9aa-9002-475c-8695-d833485741bc"
    "--report-bucket" = "omc-flywheel-prod-analysis-data"
    "--report-prefix" = "cleanrooms-reports/"
    "--output-format" = "both"
  }
}
```

**Required IAM Permissions**:
- Cleanrooms read-only access (GetConfiguredTable, ListConfiguredTables, GetMembership, etc.)
- Entity Resolution Service read access (GetIdNamespace, GetSchemaMapping)
- Glue catalog read access
- S3 write access for report output

#### **Running Data Monitoring**

```bash
# Manual execution
aws glue start-job-run --job-name etl-omc-flywheel-prod-generate-data-monitor-report

# With custom parameters
aws glue start-job-run \
  --job-name etl-omc-flywheel-prod-generate-data-monitor-report \
  --arguments '{
    "--count_tolerance_pct": "1.0",
    "--file_size_check": "true",
    "--freshness_window_days": "30"
  }'
```

#### **Running Cleanrooms Report**

```bash
# Generate comprehensive Cleanrooms report
aws glue start-job-run --job-name etl-omc-flywheel-prod-generate-cleanrooms-report

# With custom parameters
aws glue start-job-run \
  --job-name etl-omc-flywheel-prod-generate-cleanrooms-report \
  --arguments '{
    "--membership-id": "6610c9aa-9002-475c-8695-d833485741bc",
    "--database": "omc_flywheel_prod",
    "--table-prefix": "part_",
    "--report-bucket": "omc-flywheel-prod-analysis-data",
    "--report-prefix": "cleanrooms-reports/",
    "--output-format": "both"
  }'
```

#### **Monitoring Reports**

The monitoring job generates comprehensive reports in S3:

**Location**: `s3://omc-flywheel-prod-analysis-data/data-monitor/`

**Report Formats**:
- **JSON**: Complete monitoring results with metadata
- **CSV**: Tabular data for analysis and alerting

**Report Contents**:
- Table health status
- Partition counts and missing partitions
- Schema validation results
- Record count comparisons
- Key quality metrics (NULLs, duplicates)
- Snapshot freshness information
- File size issues (if enabled)

#### **Cleanrooms Reports**

The Cleanrooms reporting job generates comprehensive reports in S3:

**Location**: `s3://omc-flywheel-prod-analysis-data/cleanrooms-reports/`

**Report Formats**:
- **JSON**: Complete Cleanrooms resource data with metadata
- **CSV (Tables)**: Tabular data for configured tables and associations
- **CSV (Identity Resolution)**: Identity Resolution Service resources

**Report Contents**:
- **Tables Report**:
  - Table name and Glue table status
  - Configured table status and ARN
  - Association status and name
  - Analysis providers (allowed query accounts)
  - Ready for analysis status
- **Identity Resolution Report**:
  - ID namespace name and method
  - Source database, region, and table
  - Schema mapping name
  - Unique ID field
  - Input field and matchkey

#### **Alerting Integration**

```bash
# Configure SNS topic for alerts
aws sns create-topic --name data-monitor-alerts

# Update monitoring job with SNS topic
terraform apply -var="sns_topic_arn=arn:aws:sns:us-east-1:239083076653:data-monitor-alerts"
```

#### **Monitoring Dashboard**

Create CloudWatch dashboards to visualize:
- Table health trends
- Partition completeness
- Data freshness metrics
- Key quality statistics
- Alert frequency

### Pre-Deployment Checks
```bash
# Validate configuration
terraform validate

# Check for syntax errors
terraform fmt -check

# Review planned changes
terraform plan -detailed-exitcode
```

### Post-Deployment Verification
```bash
# Verify resources created
terraform state list

# Check resource details
terraform show

# Test data monitoring
aws glue start-job-run --job-name etl-omc-flywheel-prod-generate-data-monitor-report

# Verify monitoring reports
aws s3 ls s3://omc-flywheel-prod-analysis-data/data-monitor/

# Test Cleanrooms reporting
aws glue start-job-run --job-name etl-omc-flywheel-prod-generate-cleanrooms-report

# Verify Cleanrooms reports
aws s3 ls s3://omc-flywheel-prod-analysis-data/cleanrooms-reports/
```

### Deployment Validation
```bash
# Test Glue job execution
aws glue start-job-run --job-name etl-omc-flywheel-prod-addressable-ids-compaction

# Verify S3 access
aws s3 ls s3://omc-flywheel-data-us-east-1-prod/

# Check crawler status
aws glue get-crawler --name crw-omc-flywheel-prod-addressable_ids-compaction-cr

# Run comprehensive data quality check
aws glue start-job-run --job-name etl-omc-flywheel-prod-generate-data-monitor-report

# Generate Cleanrooms resource report
aws glue start-job-run --job-name etl-omc-flywheel-prod-generate-cleanrooms-report
```

## 🔄 CI/CD Integration

### GitHub Actions (Example)

#### Workflow File (`.github/workflows/deploy.yml`)
```yaml
name: Deploy Infrastructure

on:
  push:
    branches: [main]
    paths: ['terraform/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Setup Terraform
      uses: hashicorp/setup-terraform@v1
      with:
        terraform_version: 1.0.0
    
    - name: Configure AWS Credentials
      uses: aws-actions/configure-aws-credentials@v1
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    
    - name: Terraform Init
      run: terraform init
      working-directory: terraform/environments/prod
    
    - name: Terraform Plan
      run: terraform plan
      working-directory: terraform/environments/prod
    
    - name: Terraform Apply
      run: terraform apply -auto-approve
      working-directory: terraform/environments/prod
```

### GitLab CI (Example)

#### Pipeline File (`.gitlab-ci.yml`)
```yaml
stages:
  - validate
  - plan
  - apply

variables:
  TF_ROOT: terraform/environments/prod

validate:
  stage: validate
  script:
    - cd $TF_ROOT
    - terraform init
    - terraform validate

plan:
  stage: plan
  script:
    - cd $TF_ROOT
    - terraform init
    - terraform plan
  artifacts:
    paths:
      - $TF_ROOT/terraform.tfplan

apply:
  stage: apply
  script:
    - cd $TF_ROOT
    - terraform init
    - terraform apply terraform.tfplan
  when: manual
  only:
    - main
```

## 🚨 Rollback Procedures

### Emergency Rollback
```bash
# Stop all running jobs
aws glue stop-job-run --job-name <job-name> --run-id <run-id>

# Revert Terraform changes
git checkout HEAD~1 terraform/environments/prod/
terraform apply

# Restore from backup
aws s3 cp s3://backup-bucket/terraform-state-backup.json terraform.tfstate
```

### Gradual Rollback
```bash
# Rollback specific resources
terraform apply -target=aws_glue_job.job_name

# Verify rollback
terraform plan
```

## 📈 Scaling Considerations

### Horizontal Scaling
```bash
# Increase worker count
terraform apply -var="worker_count=48"

# Add more Glue jobs
# Add new job configuration to .tf file
```

### Vertical Scaling
```bash
# Upgrade worker type
terraform apply -var="worker_type=G.2X"

# Increase timeout
terraform apply -var="timeout=1200"
```

### Multi-Region Deployment
```bash
# Deploy to additional regions
terraform apply -var="aws_region=us-west-2"
```

## 📚 Best Practices

### 1. Version Control
- Commit all Terraform files
- Use meaningful commit messages
- Tag releases
- Review changes before merging

### 2. State Management
- Use S3 backend for production
- Enable state locking with DynamoDB
- Regular state backups
- Never edit state files manually

### 3. Security
- Use least privilege IAM policies
- Encrypt state files
- Rotate access keys regularly
- Monitor access logs

### 4. Testing
- Test in development first
- Use `terraform plan` before apply
- Validate configurations
- Test rollback procedures

---

**Last Updated**: November 18, 2025  
**Terraform Version**: >= 1.0  
**AWS Provider**: ~> 5.60
