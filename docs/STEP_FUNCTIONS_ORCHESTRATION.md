# Step Functions Orchestration Guide

## Overview

This guide covers the AWS Step Functions + EventBridge orchestration for the 7-step database refresh process. This provides fully automated, scheduled execution with built-in error handling, retries, and notifications.

## Architecture

### Components

1. **Step Functions State Machine** - Orchestrates the 7-step workflow
2. **EventBridge Rule** - Schedules monthly execution (optional)
3. **SNS Topic** - Sends success/failure notifications
4. **CloudWatch Logs** - Execution logs and monitoring
5. **IAM Roles** - Permissions for Step Functions and EventBridge

### Workflow Structure

```
Step 1: Parallel Split Jobs
├── Job 1: Addressable IDs Split and Part
└── Job 2: Infobase Split and Part

Step 2: Register Part Tables (Parallel)
├── Job 3a: Register addressable_ids tables
└── Job 3b: Register infobase_attributes tables

Step 3: Prepare Part Tables
└── Job 4: Prepare Part Tables

Step 4: Create ER Table
└── Job 5: Create Part Addressable IDs ER Table

Step 5: Parallel Reporting
├── Job 6: Generate Data Monitor Report
└── Job 7: Generate Cleanrooms Report
```

## Deployment

### Prerequisites

- Terraform >= 1.0
- AWS credentials configured
- Glue jobs already deployed
- Appropriate IAM permissions

### Deploy Dev Environment

```bash
cd infra/stacks/dev-orchestration

# Initialize Terraform
terraform init

# Review plan
terraform plan

# Apply
terraform apply
```

### Deploy Production Environment

```bash
cd infra/stacks/prod-orchestration

# Initialize Terraform
terraform init

# Review plan
terraform plan

# Apply
terraform apply
```

## Configuration

### Schedule Expression

The default schedule runs monthly at 2 AM UTC on the 1st of the month:

```
cron(0 2 1 * ? *)
```

To customize, update `schedule_expression` in your stack's `terraform.tfvars`:

```hcl
schedule_expression = "cron(0 6 1 * ? *)"  # 6 AM UTC instead
```

### Notification Emails

Add email addresses to receive SNS notifications:

```hcl
notification_emails = [
  "team@example.com",
  "oncall@example.com"
]
```

**Important:** After applying, check your email and confirm the SNS subscription.

### Disable Scheduled Execution

To disable automatic scheduling (manual execution only):

```hcl
enable_scheduled_execution = false
```

## Manual Execution

### Via AWS Console

1. Navigate to Step Functions console
2. Select the state machine: `omc-flywheel-{env}-db-refresh`
3. Click "Start execution"
4. Use the default input (or customize)
5. Click "Start execution"

### Via AWS CLI

```bash
# Get the state machine ARN from Terraform outputs
terraform output -json | jq -r '.step_functions_state_machine_arn.value'

# Start execution
aws stepfunctions start-execution \
  --state-machine-arn <STATE_MACHINE_ARN> \
  --input '{
    "Environment": "dev",
    "Job1Name": "etl-omc-flywheel-dev-addressable-split-and-part",
    "Job2Name": "etl-omc-flywheel-dev-infobase-split-and-part",
    "Job3Name": "etl-omc-flywheel-dev-register-part-tables",
    "Job4Name": "etl-omc-flywheel-dev-prepare-part-tables",
    "Job5Name": "etl-omc-flywheel-dev-create-part-addressable-ids-er-table",
    "Job6Name": "etl-omc-flywheel-dev-generate-data-monitor-report",
    "Job7Name": "etl-omc-flywheel-dev-generate-cleanrooms-report",
    "Job1Arguments": {"--SNAPSHOT_DT": "_NONE_"},
    "Job2Arguments": {"--SNAPSHOT_DT": "_NONE_"},
    "Job3AArguments": {
      "--DATABASE": "omc_flywheel_dev_clean",
      "--S3_ROOT": "s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_part/addressable_ids/",
      "--TABLE_PREFIX": "part_",
      "--MAX_COLS": "100"
    },
    "Job3BArguments": {
      "--DATABASE": "omc_flywheel_dev_clean",
      "--S3_ROOT": "s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_part/infobase_attributes/",
      "--TABLE_PREFIX": "part_",
      "--MAX_COLS": "100"
    },
    "SNSTopicArn": "<SNS_TOPIC_ARN>"
  }'
```

### Custom Snapshot Date

To process a specific snapshot date, modify the input:

```json
{
  "Job1Arguments": {"--SNAPSHOT_DT": "2025-01-15"},
  "Job2Arguments": {"--SNAPSHOT_DT": "2025-01-15"}
}
```

## Monitoring

### Step Functions Console

1. Navigate to AWS Step Functions console
2. Select your state machine
3. View execution history
4. Click on an execution to see:
   - Visual workflow diagram
   - Execution timeline
   - Input/output for each step
   - Error details (if failed)

### CloudWatch Logs

Logs are available at:

```
/aws/vendedlogs/states/omc-flywheel-{env}-db-refresh
```

View logs:

```bash
aws logs tail /aws/vendedlogs/states/omc-flywheel-dev-db-refresh --follow
```

### CloudWatch Metrics

Step Functions automatically publishes metrics:
- `ExecutionsStarted`
- `ExecutionsSucceeded`
- `ExecutionsFailed`
- `ExecutionsTimedOut`
- `ExecutionTime`

View in CloudWatch Metrics console or create dashboards.

## Error Handling

### Automatic Retries

Each step has automatic retry configuration:

- **Split Jobs (1, 2)**: 2 retries, 60s interval, 2x backoff
- **Register/Prepare Jobs (3, 4)**: 2 retries, 30s interval, 2x backoff
- **ER Table (5)**: 2 retries, 30s interval, 2x backoff
- **Reporting Jobs (6, 7)**: 1 retry, 30s interval, 2x backoff

### Failure Notifications

On failure:
1. Step Functions catches the error
2. Publishes to SNS topic
3. Email notification sent (if subscribed)
4. Error details included in message

### Manual Recovery

If a step fails after retries:

1. **Check the error** in Step Functions console
2. **Fix the underlying issue** (data, permissions, etc.)
3. **Re-run from failed step**:
   - Option A: Fix issue and re-run entire workflow (wastes time if early steps completed)
   - Option B: Use local scripts with `--skip-steps` to resume (recommended)

**📖 For detailed recovery workflow, see [RECOVERY_WORKFLOW.md](./RECOVERY_WORKFLOW.md)**

The recovery guide covers:
- How to identify which step failed
- How to determine which steps completed successfully
- How to resume efficiently using local scripts
- Time savings (especially important for 1-hour split jobs)
- Common failure scenarios and recovery steps

## Notifications

### SNS Topic

The SNS topic is created automatically:
- Name: `omc-flywheel-{env}-db-refresh-notifications`
- ARN available in Terraform outputs

### Email Subscriptions

After adding emails in Terraform:

1. Check your email for subscription confirmation
2. Click the confirmation link
3. You'll receive notifications for:
   - ✅ Successful completions
   - ❌ Failures

### Custom Subscriptions

Add additional subscriptions (Slack, PagerDuty, etc.):

```bash
# Slack webhook (via Lambda)
aws sns subscribe \
  --topic-arn <SNS_TOPIC_ARN> \
  --protocol lambda \
  --notification-endpoint <LAMBDA_FUNCTION_ARN>

# PagerDuty
aws sns subscribe \
  --topic-arn <SNS_TOPIC_ARN> \
  --protocol https \
  --notification-endpoint <PAGERDUTY_URL>
```

## Cost Considerations

### Step Functions Pricing

- **State transitions**: $0.000025 per transition
- **Estimated cost per run**: ~$0.001 (40 transitions × $0.000025)
- **Monthly cost**: ~$0.001 (1 run per month)

### EventBridge Pricing

- **Custom events**: $1.00 per million events
- **Monthly cost**: Negligible (1 event per month)

### CloudWatch Logs

- **Ingestion**: $0.50 per GB
- **Storage**: $0.03 per GB/month
- **Estimated cost**: < $1/month for typical usage

**Total estimated monthly cost: < $2/month**

## Troubleshooting

### Execution Not Starting

**Issue:** Scheduled execution not triggering

**Solutions:**
1. Check EventBridge rule status: `aws events describe-rule --name <rule-name>`
2. Verify rule is enabled: `aws events enable-rule --name <rule-name>`
3. Check IAM permissions for EventBridge role
4. Review CloudWatch Events logs

### Step Functions Permission Errors

**Issue:** `AccessDenied` when invoking Glue jobs

**Solutions:**
1. Verify Step Functions IAM role has Glue permissions
2. Check job ARNs in IAM policy match actual job names
3. Ensure role has `glue:StartJobRun` and `glue:GetJobRun` permissions

### SNS Notifications Not Received

**Issue:** No email notifications

**Solutions:**
1. Check email subscription status: `aws sns list-subscriptions-by-topic --topic-arn <arn>`
2. Verify email confirmation link was clicked
3. Check spam/junk folder
4. Verify SNS topic ARN in Step Functions input

### Job Failures

**Issue:** Jobs failing in Step Functions

**Solutions:**
1. Check Step Functions execution details for error message
2. Review CloudWatch logs for the specific Glue job
3. Verify job parameters are correct
4. Check S3 paths and permissions
5. Review Glue job logs in CloudWatch

## Best Practices

### 1. Test in Dev First

Always test changes in dev before deploying to prod:

```bash
# Deploy to dev
cd infra/stacks/dev-orchestration
terraform apply

# Test manual execution
aws stepfunctions start-execution --state-machine-arn <DEV_ARN> --input <input>
```

### 2. Monitor First Few Runs

After deployment:
- Monitor the first 2-3 scheduled runs
- Verify notifications are working
- Check execution times
- Review any warnings or errors

### 3. Set Up CloudWatch Alarms

Create alarms for:
- Execution failures
- Execution timeouts
- High error rates

### 4. Document Customizations

If you customize:
- Schedule expression
- Retry policies
- Notification settings

Document the changes and reasons.

### 5. Regular Reviews

Monthly:
- Review execution history
- Check for trends or issues
- Verify costs
- Update documentation if needed

## Related Documentation

- [Database Refresh Automation](./DB_REFRESH_AUTOMATION.md) - Local script automation
- [Production Run Sequence](./PRODUCTION_RUN_SEQUENCE.md) - Manual execution guide
- [Current Process Flow](./CURRENT_PROCESS_FLOW.md) - Overall architecture

---

**Last Updated:** 2025-01-XX  
**Version:** 1.0

