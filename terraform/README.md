# OMC Flywheel Cleanroom Production Terraform Configuration

This directory contains Terraform configuration for managing the production OMC Flywheel Cleanroom bucketing solution.

## Overview

This Terraform configuration manages:
- **4 Glue ETL Jobs** for data processing and bucketing
- **2 Glue Crawlers** for table discovery
- **IAM Roles and Policies** for secure access
- **S3 Buckets** for data storage
- **Glue Catalog Database** for metadata

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Source Data   │    │  Glue ETL Jobs  │    │  Bucketed Data  │
│                 │    │                 │    │                 │
│ • infobase_*    │───▶│ • Split & Bucket│───▶│ • Cleanroom     │
│ • addressable_* │    │ • Register      │    │ • Athena Tables │
│                 │    │ • Create Tables │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Prerequisites

1. **AWS CLI** configured with `flywheel-prod` profile
2. **Terraform** >= 1.0 installed
3. **AWS Permissions** to create/modify:
   - Glue jobs and crawlers
   - IAM roles and policies
   - S3 buckets
   - Glue catalog databases

## Usage

### 1. Initialize Terraform
```bash
cd terraform
terraform init
```

### 2. Review the Plan
```bash
terraform plan
```

### 3. Apply the Configuration
```bash
terraform apply
```

### 4. Verify Resources
```bash
terraform output
```

## Configuration Files

- **`main.tf`** - Main resource definitions
- **`variables.tf`** - Input variables
- **`outputs.tf`** - Output values
- **`terraform.tfvars`** - Variable values for production

## Resources Created

### Glue Jobs
- `etl-omc-flywheel-prod-infobase-split-and-bucket`
- `etl-omc-flywheel-prod-addressable-bucket`
- `etl-omc-flywheel-prod-register-staged-tables`
- `etl-omc-flywheel-prod-create-athena-bucketed-tables`

### Glue Crawlers
- `crw-omc-flywheel-prod-infobase-attributes-bucketed-cr`
- `crw-omc-flywheel-prod-addressable-ids-bucketed-cr`

### IAM Resources
- `omc_flywheel-prod-glue-role` - IAM role for Glue jobs
- S3 access policies
- Athena access policies
- Glue catalog access policies

### S3 Buckets
- `omc-flywheel-data-us-east-1-prod` - Main data bucket
- `omc-flywheel-prod-analysis-data` - Athena results bucket

### Glue Catalog
- `omc_flywheel_prod` - Glue catalog database

## Key Features

- **Production-optimized** Spark parameters
- **Dynamic file sizing** based on data volume
- **Snapshot date tracking** for data lineage
- **S3A protocol** for optimal performance
- **Comprehensive IAM permissions**
- **Idempotent operations** for safe reruns

## Customization

### Worker Configuration
Modify worker types and counts in `terraform.tfvars`:
```hcl
infobase_worker_type   = "G.4X"
infobase_worker_count  = 24
```

### Performance Tuning
Adjust performance parameters:
```hcl
bucket_count        = 256
target_file_mb      = 512
job_timeout_minutes = 2880
```

### S3 Paths
Update S3 paths in `main.tf` if needed:
```hcl
"--SOURCE_PATH" = "s3://your-bucket/path/"
```

## Monitoring

After deployment, monitor:
- **CloudWatch Logs** for job execution
- **Glue Job Metrics** for performance
- **S3 Storage** for data volumes
- **Athena Queries** for table access

## Troubleshooting

### Common Issues
1. **Permission Errors** - Verify IAM role has required permissions
2. **S3 Access** - Check bucket policies and paths
3. **Job Failures** - Review CloudWatch logs for errors
4. **Resource Limits** - Check AWS service limits

### Useful Commands
```bash
# Check job status
aws glue get-job --job-name etl-omc-flywheel-prod-infobase-split-and-bucket

# View job logs
aws logs describe-log-groups --log-group-name-prefix "/aws-glue/jobs"

# List S3 objects
aws s3 ls s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/
```

## Security

- **Least Privilege** IAM policies
- **S3 Bucket Encryption** enabled
- **VPC Endpoints** for secure S3 access
- **CloudTrail** logging for audit

## Cost Optimization

- **Right-sized** worker configurations
- **Efficient** Spark parameters
- **S3 Lifecycle** policies for data retention
- **Spot Instances** for non-critical jobs

## Support

For issues or questions:
1. Check CloudWatch logs
2. Review Terraform state
3. Verify AWS permissions
4. Contact Data Engineering team
