# Troubleshooting Guide

## 🚨 Common Issues and Solutions

### Terraform Issues

#### 1. State Lock Errors
**Error**: `Error acquiring the state lock`

**Solution**:
```bash
# Force unlock (use with caution)
terraform force-unlock <lock-id>

# Check for running processes
ps aux | grep terraform

# Kill hanging processes
kill -9 <process-id>
```

#### 2. Import Failures
**Error**: `Cannot import non-existent remote object`

**Solution**:
```bash
# Verify resource exists
aws glue get-job --job-name job-name

# Check correct resource name
aws glue get-jobs --query 'JobList[].Name'

# Use correct import format
terraform import aws_glue_job.resource_name job-name
```

#### 3. Configuration Drift
**Error**: `Resource has changed outside of Terraform`

**Solution**:
```bash
# Refresh state from AWS
terraform refresh

# Review changes
terraform plan

# Apply to sync state
terraform apply
```

### AWS Glue Issues

#### 1. Job Execution Failures

**Error**: `Job failed with timeout`

**Diagnosis**:
```bash
# Check job logs
aws logs get-log-events \
  --log-group-name /aws-glue/jobs/logs-v2 \
  --log-stream-name <stream-name>

# Review job configuration
aws glue get-job --job-name job-name
```

**Solutions**:
```bash
# Increase timeout
terraform apply -var="timeout=1200"

# Add more workers
terraform apply -var="worker_count=32"

# Change worker type
terraform apply -var="worker_type=G.2X"
```

#### 2. Permission Errors

**Error**: `Access Denied`

**Diagnosis**:
```bash
# Check IAM role permissions
aws iam get-role --role-name omc_flywheel-prod-glue-role

# Test S3 access
aws s3 ls s3://omc-flywheel-data-us-east-1-prod/

# Verify role policies
aws iam list-attached-role-policies --role-name omc_flywheel-prod-glue-role
```

**Solutions**:
```bash
# Update IAM role permissions
# Edit IAM policy in Terraform configuration
terraform apply

# Check S3 bucket policy
aws s3api get-bucket-policy --bucket omc-flywheel-data-us-east-1-prod
```

#### 3. Script Not Found

**Error**: `Script not found in S3`

**Diagnosis**:
```bash
# Check script location
aws s3 ls s3://aws-glue-assets-239083076653-us-east-1/scripts/

# Verify script exists
aws s3api head-object --bucket aws-glue-assets-239083076653-us-east-1 --key scripts/script-name.py
```

**Solutions**:
```bash
# Upload missing script
aws s3 cp script.py s3://aws-glue-assets-239083076653-us-east-1/scripts/

# Update job script location
terraform apply
```

### S3 Issues

#### 1. Access Denied

**Error**: `Access Denied when accessing S3`

**Diagnosis**:
```bash
# Check bucket policy
aws s3api get-bucket-policy --bucket bucket-name

# Test IAM permissions
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::239083076653:role/omc_flywheel-prod-glue-role \
  --action-names s3:GetObject \
  --resource-arns arn:aws:s3:::bucket-name/*
```

**Solutions**:
```bash
# Update bucket policy
aws s3api put-bucket-policy --bucket bucket-name --policy file://policy.json

# Check IAM role permissions
aws iam get-role-policy --role-name omc_flywheel-prod-glue-role --policy-name policy-name
```

#### 2. Bucket Not Found

**Error**: `Bucket does not exist`

**Diagnosis**:
```bash
# List all buckets
aws s3 ls

# Check bucket name spelling
aws s3api head-bucket --bucket bucket-name
```

**Solutions**:
```bash
# Create missing bucket
aws s3 mb s3://bucket-name

# Update Terraform configuration
terraform apply
```

### Crawler Issues

#### 1. Crawler Not Running

**Error**: `Crawler not discovering new data`

**Diagnosis**:
```bash
# Check crawler status
aws glue get-crawler --name crawler-name

# Check crawler runs
aws glue get-crawler-runs --crawler-name crawler-name

# Verify S3 path
aws s3 ls s3://bucket-name/path/
```

**Solutions**:
```bash
# Manually start crawler
aws glue start-crawler --name crawler-name

# Update crawler configuration
terraform apply

# Check S3 path permissions
aws s3api get-bucket-policy --bucket bucket-name
```

#### 2. Schema Discovery Issues

**Error**: `No tables created`

**Diagnosis**:
```bash
# Check crawler logs
aws logs get-log-events \
  --log-group-name /aws-glue/crawlers \
  --log-stream-name <stream-name>

# Verify data format
aws s3 ls s3://bucket-name/path/ --recursive
```

**Solutions**:
```bash
# Check data format compatibility
# Ensure data is in supported format (Parquet, JSON, CSV)

# Update crawler schema policy
terraform apply
```

## 🔍 Diagnostic Commands

### System Health Check
```bash
#!/bin/bash
# health-check.sh

echo "=== AWS Account Info ==="
aws sts get-caller-identity

echo "=== Terraform State ==="
terraform state list

echo "=== Glue Jobs Status ==="
aws glue get-jobs --query 'JobList[].{Name:Name,Role:Role}'

echo "=== S3 Buckets ==="
aws s3 ls

echo "=== Glue Crawlers ==="
aws glue get-crawlers --query 'CrawlerList[].{Name:Name,State:State}'

echo "=== Recent Job Runs ==="
aws glue get-job-runs --job-name etl-omc-flywheel-prod-addressable-ids-compaction --max-items 5
```

### Resource Verification
```bash
#!/bin/bash
# verify-resources.sh

echo "=== Verifying Glue Jobs ==="
for job in etl-omc-flywheel-prod-addressable-ids-compaction etl-omc-flywheel-prod-infobase-attributes-compaction etl-omc-flywheel-prod-infobase-cleanroom-from-csv; do
  echo "Checking job: $job"
  aws glue get-job --job-name $job --query 'Job.{Name:Name,Role:Role,WorkerType:WorkerType}'
done

echo "=== Verifying S3 Buckets ==="
for bucket in omc-flywheel-data-us-east-1-prod aws-glue-assets-239083076653-us-east-1 omc-flywheel-prod-analysis-data; do
  echo "Checking bucket: $bucket"
  aws s3api head-bucket --bucket $bucket
done

echo "=== Verifying IAM Role ==="
aws iam get-role --role-name omc_flywheel-prod-glue-role --query 'Role.{RoleName:RoleName,Arn:Arn}'
```

## 📊 Monitoring and Alerting

### CloudWatch Metrics
```bash
# Get job success rate
aws cloudwatch get-metric-statistics \
  --namespace AWS/Glue \
  --metric-name JobRunSuccess \
  --dimensions Name=JobName,Value=etl-omc-flywheel-prod-addressable-ids-compaction \
  --statistics Average \
  --start-time 2025-10-16T00:00:00Z \
  --end-time 2025-10-17T00:00:00Z \
  --period 3600

# Get job duration
aws cloudwatch get-metric-statistics \
  --namespace AWS/Glue \
  --metric-name JobRunDuration \
  --dimensions Name=JobName,Value=etl-omc-flywheel-prod-addressable-ids-compaction \
  --statistics Average \
  --start-time 2025-10-16T00:00:00Z \
  --end-time 2025-10-17T00:00:00Z \
  --period 3600
```

### Log Analysis
```bash
# Search for errors in job logs
aws logs filter-log-events \
  --log-group-name /aws-glue/jobs/logs-v2 \
  --filter-pattern "ERROR" \
  --start-time $(date -d '24 hours ago' +%s)000

# Get recent job runs
aws logs describe-log-streams \
  --log-group-name /aws-glue/jobs/logs-v2 \
  --order-by LastEventTime \
  --descending \
  --max-items 10
```

## 🚨 Emergency Procedures

### Stop All Jobs
```bash
#!/bin/bash
# stop-all-jobs.sh

echo "Stopping all Glue jobs..."

# Get all running job runs
for job in etl-omc-flywheel-prod-addressable-ids-compaction etl-omc-flywheel-prod-infobase-attributes-compaction etl-omc-flywheel-prod-infobase-cleanroom-from-csv; do
  echo "Checking job: $job"
  runs=$(aws glue get-job-runs --job-name $job --query 'JobRuns[?JobRunState==`RUNNING`].Id' --output text)
  
  for run in $runs; do
    echo "Stopping run: $run"
    aws glue stop-job-run --job-name $job --run-id $run
  done
done
```

### Restore from Backup
```bash
#!/bin/bash
# restore-from-backup.sh

echo "Restoring from backup..."

# Restore Terraform state
aws s3 cp s3://omc-flywheel-prod-analysis-data/backups/terraform-state-backup.json terraform.tfstate

# Restore S3 data (if needed)
aws s3 sync s3://backup-bucket/ s3://omc-flywheel-data-us-east-1-prod/

# Re-import resources
terraform import aws_glue_job.job_name job-name
```

### Rollback Changes
```bash
#!/bin/bash
# rollback.sh

echo "Rolling back changes..."

# Get previous commit
PREVIOUS_COMMIT=$(git log --oneline -n 2 | tail -1 | cut -d' ' -f1)

# Checkout previous version
git checkout $PREVIOUS_COMMIT terraform/environments/prod/

# Apply previous configuration
terraform apply
```

## 📞 Support Contacts

### Internal Support
- **Infrastructure Team**: infrastructure@company.com
- **Data Engineering Team**: data-engineering@company.com
- **On-Call Engineer**: +1-XXX-XXX-XXXX

### AWS Support
- **AWS Support Case**: [Create case in AWS Console]
- **AWS Documentation**: https://docs.aws.amazon.com/glue/
- **AWS Status Page**: https://status.aws.amazon.com/

### Escalation Procedures
1. **Level 1**: Check logs and basic troubleshooting
2. **Level 2**: Contact infrastructure team
3. **Level 3**: Escalate to AWS support
4. **Emergency**: Use emergency procedures above

## 📚 Additional Resources

### Documentation Links
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS Glue Developer Guide](https://docs.aws.amazon.com/glue/latest/dg/)
- [S3 User Guide](https://docs.aws.amazon.com/s3/latest/userguide/)

### Useful Commands Reference
```bash
# Terraform
terraform plan -detailed-exitcode
terraform show -json
terraform graph | dot -Tpng > graph.png

# AWS CLI
aws configure list
aws sts get-caller-identity
aws glue get-jobs --max-items 10
aws s3 ls --recursive s3://bucket-name/

# Monitoring
aws logs describe-log-groups
aws cloudwatch list-metrics --namespace AWS/Glue
```

---

**Last Updated**: October 17, 2025  
**Environment**: Production  
**Support Level**: 24/7 On-Call
