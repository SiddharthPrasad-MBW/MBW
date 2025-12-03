# Operations Guide

## 🚀 Daily Operations

### Checking System Health

#### 1. Verify All Resources
```bash
# Navigate to Terraform directory
cd terraform/environments/prod

# Check current state
terraform state list

# Verify no drift
terraform plan
```

#### 2. Monitor Glue Jobs
```bash
# List recent job runs
aws glue get-job-runs --job-name etl-omc-flywheel-prod-addressable-ids-compaction

# Check job status
aws glue get-job --job-name etl-omc-flywheel-prod-addressable-ids-compaction
```

#### 3. Check S3 Bucket Status
```bash
# List bucket contents
aws s3 ls s3://omc-flywheel-data-us-east-1-prod/ --recursive

# Check bucket metrics
aws s3api get-bucket-metrics-configuration --bucket omc-flywheel-data-us-east-1-prod
```

### Running Glue Jobs

#### Manual Job Execution
```bash
# Start a Glue job
aws glue start-job-run --job-name etl-omc-flywheel-prod-addressable-ids-compaction

# Monitor job progress
aws glue get-job-run --job-name etl-omc-flywheel-prod-addressable-ids-compaction --run-id <run-id>
```

#### Scheduled Jobs
- Jobs are typically scheduled via AWS EventBridge
- Check CloudWatch Events for scheduling configuration
- Monitor job execution in Glue console

### Data Pipeline Monitoring

#### 1. Check Crawler Status
```bash
# List crawler runs
aws glue get-crawler --name crw-omc-flywheel-prod-addressable_ids-compaction-cr

# Check crawler metrics
aws glue get-crawler-metrics --crawler-name-list crw-omc-flywheel-prod-addressable_ids-compaction-cr
```

#### 2. Verify Data Catalog
```bash
# List tables in database
aws glue get-tables --database-name omc_flywheel_prod

# Check table schema
aws glue get-table --database-name omc_flywheel_prod --name <table-name>
```

## 🔧 Maintenance Tasks

### Weekly Tasks

#### 1. Review Resource Costs
```bash
# Check S3 storage costs
aws s3api get-bucket-analytics-configuration --bucket omc-flywheel-data-us-east-1-prod

# Review Glue job costs in AWS Cost Explorer
```

#### 2. Clean Up Temporary Files
```bash
# List temporary files
aws s3 ls s3://omc-flywheel-prod-analysis-data/temp/ --recursive

# Remove old temporary files (older than 7 days)
aws s3 rm s3://omc-flywheel-prod-analysis-data/temp/ --recursive
```

#### 3. Update Scripts
```bash
# Upload new script versions
aws s3 cp new-script.py s3://aws-glue-assets-239083076653-us-east-1/scripts/

# Update Glue job script location if needed
terraform apply
```

### Monthly Tasks

#### 1. Review and Update Tags
```bash
# Check current tags
terraform show | grep tags

# Update tags if needed
# Edit terraform configuration and apply
```

#### 2. Security Review
```bash
# Check IAM role permissions
aws iam get-role --role-name omc_flywheel-prod-glue-role

# Review S3 bucket policies
aws s3api get-bucket-policy --bucket omc-flywheel-data-us-east-1-prod
```

#### 3. Performance Optimization
```bash
# Review job execution times
aws logs describe-log-groups --log-group-name-prefix /aws-glue

# Analyze slow-running jobs
aws glue get-job-run --job-name <job-name> --run-id <run-id>
```

## 🚨 Troubleshooting

### Common Issues and Solutions

#### 1. Glue Job Failures

**Issue**: Job fails with timeout
```bash
# Check job logs
aws logs get-log-events --log-group-name /aws-glue/jobs/logs-v2 --log-stream-name <stream-name>

# Increase timeout if needed
terraform apply -var="job_timeout=1200"
```

**Issue**: Job fails with permission error
```bash
# Check IAM role permissions
aws iam get-role-policy --role-name omc_flywheel-prod-glue-role --policy-name <policy-name>

# Verify S3 bucket access
aws s3api head-bucket --bucket omc-flywheel-data-us-east-1-prod
```

#### 2. S3 Access Issues

**Issue**: Cannot access S3 bucket
```bash
# Check bucket policy
aws s3api get-bucket-policy --bucket omc-flywheel-data-us-east-1-prod

# Verify IAM permissions
aws iam simulate-principal-policy --policy-source-arn arn:aws:iam::239083076653:role/omc_flywheel-prod-glue-role --action-names s3:GetObject --resource-arns arn:aws:s3:::omc-flywheel-data-us-east-1-prod/*
```

#### 3. Crawler Issues

**Issue**: Crawler not discovering new data
```bash
# Check crawler configuration
aws glue get-crawler --name crw-omc-flywheel-prod-addressable_ids-compaction-cr

# Manually trigger crawler
aws glue start-crawler --name crw-omc-flywheel-prod-addressable_ids-compaction-cr
```

### Emergency Procedures

#### 1. Stop All Jobs
```bash
# List running jobs
aws glue get-job-runs --job-name etl-omc-flywheel-prod-addressable-ids-compaction

# Stop specific job run
aws glue stop-job-run --job-name <job-name> --run-id <run-id>
```

#### 2. Restore from Backup
```bash
# List S3 object versions
aws s3api list-object-versions --bucket omc-flywheel-data-us-east-1-prod

# Restore specific version
aws s3api restore-object --bucket omc-flywheel-data-us-east-1-prod --key <object-key> --version-id <version-id>
```

#### 3. Rollback Terraform Changes
```bash
# View Terraform history
terraform show -json | jq '.values.root_module.resources'

# Rollback to previous state
terraform apply -target=aws_glue_job.job_omc_flywheel_prod_addressable_ids_compaction
```

## 📊 Monitoring and Alerting

### CloudWatch Metrics

#### Key Metrics to Monitor
- **Glue Job Success Rate**: `AWS/Glue/JobRunSuccess`
- **Job Duration**: `AWS/Glue/JobRunDuration`
- **S3 Storage**: `AWS/S3/BucketSizeBytes`
- **S3 Requests**: `AWS/S3/NumberOfObjects`

#### Setting Up Alerts
```bash
# Create CloudWatch alarm for job failures
aws cloudwatch put-metric-alarm \
  --alarm-name "GlueJobFailures" \
  --alarm-description "Alert on Glue job failures" \
  --metric-name JobRunSuccess \
  --namespace AWS/Glue \
  --statistic Average \
  --period 300 \
  --threshold 0.9 \
  --comparison-operator LessThanThreshold
```

### Log Analysis

#### Glue Job Logs
```bash
# View job execution logs
aws logs get-log-events \
  --log-group-name /aws-glue/jobs/logs-v2 \
  --log-stream-name <stream-name> \
  --start-time $(date -d '1 hour ago' +%s)000
```

#### Error Pattern Analysis
```bash
# Search for error patterns
aws logs filter-log-events \
  --log-group-name /aws-glue/jobs/logs-v2 \
  --filter-pattern "ERROR" \
  --start-time $(date -d '24 hours ago' +%s)000
```

## 🔄 Backup and Recovery

### Backup Strategy

#### 1. Terraform State Backup
```bash
# Export current state
terraform show -json > terraform-state-backup.json

# Backup to S3
aws s3 cp terraform-state-backup.json s3://omc-flywheel-prod-analysis-data/backups/
```

#### 2. S3 Data Backup
```bash
# Create cross-region replication
aws s3api put-bucket-replication \
  --bucket omc-flywheel-data-us-east-1-prod \
  --replication-configuration file://replication-config.json
```

#### 3. Glue Script Backup
```bash
# Backup all Glue scripts
aws s3 sync s3://aws-glue-assets-239083076653-us-east-1/scripts/ ./scripts-backup/
```

### Recovery Procedures

#### 1. Restore Terraform State
```bash
# Download state backup
aws s3 cp s3://omc-flywheel-prod-analysis-data/backups/terraform-state-backup.json .

# Import resources if needed
terraform import aws_glue_job.job_name job-name
```

#### 2. Restore S3 Data
```bash
# List available versions
aws s3api list-object-versions --bucket omc-flywheel-data-us-east-1-prod

# Restore specific objects
aws s3api restore-object --bucket omc-flywheel-data-us-east-1-prod --key <key> --version-id <version>
```

## 📈 Performance Tuning

### Glue Job Optimization

#### 1. Worker Configuration
```bash
# Adjust worker count based on data volume
terraform apply -var="worker_count=32"

# Change worker type for better performance
terraform apply -var="worker_type=G.2X"
```

#### 2. Spark Configuration
```bash
# Add custom Spark properties
terraform apply -var="spark_properties={spark.sql.adaptive.enabled=true}"
```

### S3 Optimization

#### 1. Lifecycle Policies
```bash
# Configure automatic cleanup
aws s3api put-bucket-lifecycle-configuration \
  --bucket omc-flywheel-prod-analysis-data \
  --lifecycle-configuration file://lifecycle-config.json
```

#### 2. Storage Class Optimization
```bash
# Transition to cheaper storage classes
aws s3api put-object --bucket omc-flywheel-data-us-east-1-prod --key <key> --storage-class STANDARD_IA
```

---

**Last Updated**: October 17, 2025  
**Environment**: Production  
**Maintenance Window**: Sundays 2-4 AM EST
