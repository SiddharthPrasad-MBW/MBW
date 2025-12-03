terraform {
  required_version = ">= 1.0"
}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.id
  
  # Read and process Step Functions definition
  step_functions_definition = templatefile(
    "${path.module}/step-functions-definition.json",
    {
      # These will be replaced with actual values from variables
      Job1Name = var.job_names.job1
      Job2Name = var.job_names.job2
      Job3Name = var.job_names.job3
      Job4Name = var.job_names.job4
      Job5Name = var.job_names.job5
      Job6Name = var.job_names.job6
      Job7Name = var.job_names.job7
    }
  )
  
  common_tags = merge(
    var.tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
      Module      = "orchestration"
    }
  )
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# SNS Topic for Notifications
resource "aws_sns_topic" "orchestration_notifications" {
  name              = "omc-flywheel-${var.environment}-db-refresh-notifications"
  display_name      = "OMC Flywheel ${title(var.environment)} DB Refresh Notifications"
  kms_master_key_id = var.sns_kms_key_id
  
  tags = merge(
    local.common_tags,
    {
      Name = "omc-flywheel-${var.environment}-db-refresh-notifications"
    }
  )
}

# SNS Topic Subscription (optional - can be added via variables)
resource "aws_sns_topic_subscription" "email" {
  count     = length(var.notification_emails)
  topic_arn = aws_sns_topic.orchestration_notifications.arn
  protocol  = "email"
  endpoint  = var.notification_emails[count.index]
}

# IAM Role for Step Functions
resource "aws_iam_role" "step_functions" {
  name = "omc-flywheel-${var.environment}-step-functions-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
  
  tags = local.common_tags
}

# IAM Policy for Step Functions to invoke Glue jobs
resource "aws_iam_role_policy" "step_functions_glue" {
  name = "omc-flywheel-${var.environment}-step-functions-glue-policy"
  role = aws_iam_role.step_functions.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "glue:StartJobRun",
          "glue:GetJobRun",
          "glue:GetJobRuns",
          "glue:BatchStopJobRun"
        ]
        Resource = [
          "arn:aws:glue:${local.region}:${local.account_id}:job/${var.job_names.job1}",
          "arn:aws:glue:${local.region}:${local.account_id}:job/${var.job_names.job2}",
          "arn:aws:glue:${local.region}:${local.account_id}:job/${var.job_names.job3}",
          "arn:aws:glue:${local.region}:${local.account_id}:job/${var.job_names.job4}",
          "arn:aws:glue:${local.region}:${local.account_id}:job/${var.job_names.job5}",
          "arn:aws:glue:${local.region}:${local.account_id}:job/${var.job_names.job6}",
          "arn:aws:glue:${local.region}:${local.account_id}:job/${var.job_names.job7}"
        ]
      }
    ]
  })
}

# IAM Policy for Step Functions to publish to SNS
resource "aws_iam_role_policy" "step_functions_sns" {
  name = "omc-flywheel-${var.environment}-step-functions-sns-policy"
  role = aws_iam_role.step_functions.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.orchestration_notifications.arn
      }
    ]
  })
}

# IAM Policy for Step Functions to write to CloudWatch Logs
resource "aws_iam_role_policy" "step_functions_logs" {
  name = "omc-flywheel-${var.environment}-step-functions-logs-policy"
  role = aws_iam_role.step_functions.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.step_functions.arn}:*"
      }
    ]
  })
}

# Step Functions State Machine
resource "aws_sfn_state_machine" "db_refresh" {
  name     = "omc-flywheel-${var.environment}-db-refresh"
  role_arn = aws_iam_role.step_functions.arn
  
  definition = jsonencode({
    Comment = "OMC Flywheel Database Refresh - 7-Step Process Orchestration"
    StartAt = "Step1_ParallelSplitJobs"
    States = {
      Step1_ParallelSplitJobs = {
        Type = "Parallel"
        ResultPath = "$.Step1Results"
        Branches = [
          {
            StartAt = "Step1A_AddressableSplitAndPart"
            States = {
              Step1A_AddressableSplitAndPart = {
                Type = "Task"
                Resource = "arn:aws:states:::glue:startJobRun.sync"
                Parameters = {
                  "JobName.$" = "$.Job1Name"
                  "Arguments.$" = "$.Job1Arguments"
                }
                Retry = [
                  {
                    ErrorEquals = ["States.TaskFailed"]
                    IntervalSeconds = 60
                    MaxAttempts = 2
                    BackoffRate = 2.0
                  }
                ]
                End = true
              }
            }
          },
          {
            StartAt = "Step1B_InfobaseSplitAndPart"
            States = {
              Step1B_InfobaseSplitAndPart = {
                Type = "Task"
                Resource = "arn:aws:states:::glue:startJobRun.sync"
                Parameters = {
                  "JobName.$" = "$.Job2Name"
                  "Arguments.$" = "$.Job2Arguments"
                }
                Retry = [
                  {
                    ErrorEquals = ["States.TaskFailed"]
                    IntervalSeconds = 60
                    MaxAttempts = 2
                    BackoffRate = 2.0
                  }
                ]
                End = true
              }
            }
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            ResultPath = "$.error"
            Next = "NotifyFailure"
          }
        ]
        Next = "Step2_RegisterPartTables"
      }
      Step2_RegisterPartTables = {
        Type = "Parallel"
        ResultPath = "$.Step2Results"
        Branches = [
          {
            StartAt = "Step2A_RegisterAddressableIds"
            States = {
              Step2A_RegisterAddressableIds = {
                Type = "Task"
                Resource = "arn:aws:states:::glue:startJobRun.sync"
                Parameters = {
                  "JobName.$" = "$.Job3Name"
                  "Arguments.$" = "$.Job3AArguments"
                }
                Retry = [
                  {
                    ErrorEquals = ["States.TaskFailed"]
                    IntervalSeconds = 30
                    MaxAttempts = 2
                    BackoffRate = 2.0
                  }
                ]
                End = true
              }
            }
          },
          {
            StartAt = "Step2B_RegisterInfobaseAttributes"
            States = {
              Step2B_RegisterInfobaseAttributes = {
                Type = "Task"
                Resource = "arn:aws:states:::glue:startJobRun.sync"
                Parameters = {
                  "JobName.$" = "$.Job3Name"
                  "Arguments.$" = "$.Job3BArguments"
                }
                Retry = [
                  {
                    ErrorEquals = ["States.TaskFailed"]
                    IntervalSeconds = 30
                    MaxAttempts = 2
                    BackoffRate = 2.0
                  }
                ]
                End = true
              }
            }
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            ResultPath = "$.error"
            Next = "NotifyFailure"
          }
        ]
        Next = "Step3_PreparePartTables"
      }
      Step3_PreparePartTables = {
        Type = "Task"
        Resource = "arn:aws:states:::glue:startJobRun.sync"
        ResultPath = "$.Step3Results"
        Parameters = {
          "JobName.$" = "$.Job4Name"
        }
        Retry = [
          {
            ErrorEquals = ["States.TaskFailed"]
            IntervalSeconds = 30
            MaxAttempts = 2
            BackoffRate = 2.0
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            ResultPath = "$.error"
            Next = "NotifyFailure"
          }
        ]
        Next = "Step4_CreateERTable"
      }
      Step4_CreateERTable = {
        Type = "Task"
        Resource = "arn:aws:states:::glue:startJobRun.sync"
        ResultPath = "$.Step4Results"
        Parameters = {
          "JobName.$" = "$.Job5Name"
        }
        Retry = [
          {
            ErrorEquals = ["States.TaskFailed"]
            IntervalSeconds = 30
            MaxAttempts = 2
            BackoffRate = 2.0
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            ResultPath = "$.error"
            Next = "NotifyFailure"
          }
        ]
        Next = "Step5_ParallelReporting"
      }
      Step5_ParallelReporting = {
        Type = "Parallel"
        ResultPath = "$.Step5Results"
        Branches = [
          {
            StartAt = "Step5A_DataMonitorReport"
            States = {
              Step5A_DataMonitorReport = {
                Type = "Task"
                Resource = "arn:aws:states:::glue:startJobRun.sync"
                Parameters = {
                  "JobName.$" = "$.Job6Name"
                }
                Retry = [
                  {
                    ErrorEquals = ["States.TaskFailed"]
                    IntervalSeconds = 30
                    MaxAttempts = 1
                    BackoffRate = 2.0
                  }
                ]
                End = true
              }
            }
          },
          {
            StartAt = "Step5B_CleanroomsReport"
            States = {
              Step5B_CleanroomsReport = {
                Type = "Task"
                Resource = "arn:aws:states:::glue:startJobRun.sync"
                Parameters = {
                  "JobName.$" = "$.Job7Name"
                }
                Retry = [
                  {
                    ErrorEquals = ["States.TaskFailed"]
                    IntervalSeconds = 30
                    MaxAttempts = 1
                    BackoffRate = 2.0
                  }
                ]
                End = true
              }
            }
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            ResultPath = "$.error"
            Next = "NotifyFailure"
          }
        ]
        Next = "NotifySuccess"
      }
      NotifySuccess = {
        Type = "Task"
        Resource = "arn:aws:states:::sns:publish"
        Parameters = {
          "TopicArn.$" = "$.SNSTopicArn"
          Subject = "✅ Database Refresh Completed Successfully"
          Message = "Database refresh completed successfully!\n\nAll 7 steps completed:\n1. Addressable IDs Split and Part\n2. Infobase Split and Part\n3. Register Part Tables (addressable_ids + infobase_attributes)\n4. Prepare Part Tables\n5. Create Part Addressable IDs ER Table\n6. Generate Data Monitor Report\n7. Generate Cleanrooms Report"
        }
        End = true
      }
      NotifyFailure = {
        Type = "Task"
        Resource = "arn:aws:states:::sns:publish"
        Parameters = {
          "TopicArn.$" = "$.SNSTopicArn"
          Subject = "❌ Database Refresh Failed"
          Message = "Database refresh failed!\n\nPlease check the Step Functions console for details."
        }
        Next = "ExecutionFailed"
      }
      ExecutionFailed = {
        Type = "Fail"
        Error = "JobExecutionFailed"
        Cause = "One or more Glue jobs failed during the database refresh process. Check the execution history for details."
      }
    }
  })
  
  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }
  
  tags = merge(
    local.common_tags,
    {
      Name = "omc-flywheel-${var.environment}-db-refresh"
    }
  )
}

# CloudWatch Log Group for Step Functions
resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/vendedlogs/states/omc-flywheel-${var.environment}-db-refresh"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.cloudwatch_kms_key_id
  
  tags = local.common_tags
}

# EventBridge Rule for Monthly Scheduling
resource "aws_cloudwatch_event_rule" "monthly_schedule" {
  count               = var.enable_scheduled_execution ? 1 : 0
  name                = "omc-flywheel-${var.environment}-db-refresh-schedule"
  description         = "Monthly schedule for OMC Flywheel database refresh"
  schedule_expression = var.schedule_expression
  
  tags = local.common_tags
}

# EventBridge Target - Step Functions State Machine
resource "aws_cloudwatch_event_target" "step_functions" {
  count     = var.enable_scheduled_execution ? 1 : 0
  rule      = aws_cloudwatch_event_rule.monthly_schedule[0].name
  target_id = "StepFunctionsTarget"
  arn       = aws_sfn_state_machine.db_refresh.arn
  role_arn  = aws_iam_role.eventbridge[0].arn
  
  input = jsonencode({
    Environment = var.environment
    Job1Name    = var.job_names.job1
    Job2Name    = var.job_names.job2
    Job3Name    = var.job_names.job3
    Job4Name    = var.job_names.job4
    Job5Name    = var.job_names.job5
    Job6Name    = var.job_names.job6
    Job7Name    = var.job_names.job7
    Job1Arguments = var.job_arguments.job1
    Job2Arguments = var.job_arguments.job2
    Job3AArguments = var.job_arguments.job3a
    Job3BArguments = var.job_arguments.job3b
    SNSTopicArn = aws_sns_topic.orchestration_notifications.arn
  })
}

# IAM Role for EventBridge to invoke Step Functions
resource "aws_iam_role" "eventbridge" {
  count = var.enable_scheduled_execution ? 1 : 0
  name  = "omc-flywheel-${var.environment}-eventbridge-step-functions-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
  
  tags = local.common_tags
}

# IAM Policy for EventBridge to start Step Functions executions
resource "aws_iam_role_policy" "eventbridge_step_functions" {
  count = var.enable_scheduled_execution ? 1 : 0
  name  = "omc-flywheel-${var.environment}-eventbridge-step-functions-policy"
  role  = aws_iam_role.eventbridge[0].id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = aws_sfn_state_machine.db_refresh.arn
      }
    ]
  })
}

