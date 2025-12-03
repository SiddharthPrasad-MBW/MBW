# Orchestration Module

Terraform module for Step Functions + EventBridge orchestration of the 7-step database refresh process.

## Features

- ✅ Step Functions state machine for workflow orchestration
- ✅ EventBridge rule for scheduled execution (optional)
- ✅ SNS topic for success/failure notifications
- ✅ CloudWatch logs for execution tracking
- ✅ Automatic retries with exponential backoff
- ✅ Parallel execution support
- ✅ Error handling and notifications

## Usage

```hcl
module "orchestration" {
  source = "../../modules/orchestration"
  
  environment = "dev"
  
  job_names = {
    job1 = "etl-omc-flywheel-dev-addressable-split-and-part"
    job2 = "etl-omc-flywheel-dev-infobase-split-and-part"
    job3 = "etl-omc-flywheel-dev-register-part-tables"
    job4 = "etl-omc-flywheel-dev-prepare-part-tables"
    job5 = "etl-omc-flywheel-dev-create-part-addressable-ids-er-table"
    job6 = "etl-omc-flywheel-dev-generate-data-monitor-report"
    job7 = "etl-omc-flywheel-dev-generate-cleanrooms-report"
  }
  
  job_arguments = {
    job1 = {
      "--SNAPSHOT_DT" = "_NONE_"
    }
    job2 = {
      "--SNAPSHOT_DT" = "_NONE_"
    }
    job3a = {
      "--DATABASE"     = "omc_flywheel_dev_clean"
      "--S3_ROOT"      = "s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_part/addressable_ids/"
      "--TABLE_PREFIX" = "part_"
      "--MAX_COLS"     = "100"
    }
    job3b = {
      "--DATABASE"     = "omc_flywheel_dev_clean"
      "--S3_ROOT"      = "s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_part/infobase_attributes/"
      "--TABLE_PREFIX" = "part_"
      "--MAX_COLS"     = "100"
    }
  }
  
  enable_scheduled_execution = true
  schedule_expression        = "cron(0 2 1 * ? *)"
  notification_emails       = ["team@example.com"]
}
```

## Resources Created

- `aws_sfn_state_machine` - Step Functions state machine
- `aws_cloudwatch_event_rule` - EventBridge rule (if enabled)
- `aws_cloudwatch_event_target` - EventBridge target
- `aws_sns_topic` - SNS topic for notifications
- `aws_sns_topic_subscription` - Email subscriptions (if provided)
- `aws_cloudwatch_log_group` - CloudWatch logs
- `aws_iam_role` - Step Functions execution role
- `aws_iam_role_policy` - Glue and SNS permissions
- `aws_iam_role` - EventBridge role (if scheduled)

## Inputs

See `variables.tf` for complete list.

## Outputs

- `step_functions_state_machine_arn` - State machine ARN
- `step_functions_state_machine_name` - State machine name
- `sns_topic_arn` - SNS topic ARN
- `eventbridge_rule_arn` - EventBridge rule ARN (if enabled)

## Workflow

The state machine orchestrates:

1. **Step 1**: Parallel execution of split jobs (1 & 2)
2. **Step 2**: Parallel execution of register jobs (3a & 3b)
3. **Step 3**: Prepare part tables (4)
4. **Step 4**: Create ER table (5)
5. **Step 5**: Parallel execution of reporting jobs (6 & 7)

Each step includes:
- Automatic retries
- Error catching
- SNS notifications on failure

## See Also

- [Step Functions Orchestration Guide](../../../docs/STEP_FUNCTIONS_ORCHESTRATION.md)
- [Database Refresh Automation](../../../docs/DB_REFRESH_AUTOMATION.md)

