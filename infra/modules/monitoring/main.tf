terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

# Configure AWS Provider
provider "aws" {
  region = var.aws_region
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Local values
locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name
  
  # Capitalize environment for display (prod -> Production, dev -> Development)
  environment_display = title(var.environment)
  
  common_tags = merge(
    {
      Project     = "OMC Flywheel Cleanroom"
      Environment = local.environment_display
      Owner       = "Data Engineering"
      ManagedBy   = "Terraform"
      Component   = "Data Monitoring"
    },
    var.additional_tags
  )
}

# SNS Topic for monitoring alerts
resource "aws_sns_topic" "data_monitor_alerts" {
  name = "${var.project_name}-${var.environment}-data-monitor-alerts"
  
  tags = local.common_tags
}

# SNS Topic Policy
resource "aws_sns_topic_policy" "data_monitor_alerts" {
  arn = aws_sns_topic.data_monitor_alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
        Action = "sns:Publish"
        Resource = aws_sns_topic.data_monitor_alerts.arn
      }
    ]
  })
}

# CloudWatch Log Group for monitoring
resource "aws_cloudwatch_log_group" "data_monitor" {
  name              = "/aws/glue/jobs/etl-${var.project_name}-${var.environment}-generate-data-monitor-report"
  retention_in_days = 30
  
  tags = local.common_tags
}

# IAM Role for Data Monitor
resource "aws_iam_role" "data_monitor_role" {
  name = "${var.project_name}-${var.environment}-data-monitor-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })
  
  tags = local.common_tags
}

# IAM Policy for Data Monitor
resource "aws_iam_policy" "data_monitor_policy" {
  name        = "${var.project_name}-${var.environment}-data-monitor-policy"
  description = "Policy for OMC Flywheel Data Monitor Glue job"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.data_bucket_name}",
          "arn:aws:s3:::${var.data_bucket_name}/*",
          "arn:aws:s3:::${var.analysis_bucket_name}",
          "arn:aws:s3:::${var.analysis_bucket_name}/*",
          "arn:aws:s3:::aws-glue-assets-${local.account_id}-${local.region}",
          "arn:aws:s3:::aws-glue-assets-${local.account_id}-${local.region}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetPartitions",
          "glue:BatchGetPartition"
        ]
        Resource = [
          "arn:aws:glue:${local.region}:${local.account_id}:catalog",
          "arn:aws:glue:${local.region}:${local.account_id}:database/${var.glue_database_name}",
          "arn:aws:glue:${local.region}:${local.account_id}:table/${var.glue_database_name}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:StopQueryExecution"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.data_monitor_alerts.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = aws_cloudwatch_log_group.data_monitor.arn
      }
    ]
  })
  
  tags = local.common_tags
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "data_monitor_policy" {
  role       = aws_iam_role.data_monitor_role.name
  policy_arn = aws_iam_policy.data_monitor_policy.arn
}

# Attach Glue service role
resource "aws_iam_role_policy_attachment" "data_monitor_glue_service" {
  role       = aws_iam_role.data_monitor_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# Data Monitor Glue Job
resource "aws_glue_job" "data_monitor" {
  name         = "etl-${var.project_name}-${var.environment}-generate-data-monitor-report"
  role_arn     = aws_iam_role.data_monitor_role.arn
  glue_version = "4.0"

  command {
    name            = "pythonshell"
    python_version  = "3.9"
    script_location = "s3://aws-glue-assets-${local.account_id}-${local.region}/scripts/data_monitor.py"
  }

  timeout           = 300
  max_retries       = 0

  default_arguments = {
    "--job-language"         = "python"
    "--enable-metrics"       = "true"
    "--enable-job-insights"  = "true"
    "--spark-event-logs-path" = "s3://aws-glue-assets-${local.account_id}-${local.region}/spark-event-logs/"
    "--TempDir"              = "s3://aws-glue-assets-${local.account_id}-${local.region}/temp/"

    "--region"                = local.region
    "--database"              = var.glue_database_name
    "--table_prefix"          = "part_"
    "--bucket_count"          = "256"
    "--report_bucket"         = var.analysis_bucket_name
    "--report_prefix"         = "data-monitor/"
    "--data_bucket"           = var.data_bucket_name
    "--sns_topic_arn"         = aws_sns_topic.data_monitor_alerts.arn
    "--auto_repair"           = "athena"
    "--athena_workgroup"      = "primary"
    "--athena_results"        = "s3://${var.analysis_bucket_name}/query-results/monitor/"
    "--strict_snapshot"       = "true"
    "--freshness_window_days" = "45"

    # Counts & schema/PK checks
    "--count_check_enabled"   = "true"
    "--compare_source_type"   = "part"
    "--compare_database"      = var.glue_database_name
    "--count_tolerance_pct"   = "0"
    "--pk_column"             = var.pk_column

    # Optional file-size hygiene (off by default)
    "--file_size_check"       = "false"
    "--file_size_min_mb"      = "64"
    "--file_size_max_mb"      = "1024"
  }

  execution_property {
    max_concurrent_runs = 1
  }

  tags = local.common_tags
}

# CloudWatch Dashboard for monitoring
resource "aws_cloudwatch_dashboard" "data_monitor" {
  dashboard_name = "${var.project_name}-${var.environment}-Data-Monitor"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Glue", "glue.driver.aggregate.numCompletedTasks", "JobName", "etl-${var.project_name}-${var.environment}-generate-data-monitor-report"],
            [".", "glue.driver.aggregate.numFailedTasks", ".", "."],
            [".", "glue.driver.aggregate.numKilledTasks", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.region
          title   = "Data Monitor Job Execution"
          period  = 300
        }
      },
      {
        type   = "log"
        x      = 0
        y      = 6
        width  = 24
        height = 6

        properties = {
          query   = "SOURCE '/aws/glue/jobs/etl-${var.project_name}-${var.environment}-generate-data-monitor-report' | fields @timestamp, @message | sort @timestamp desc | limit 100"
          region  = local.region
          title   = "Data Monitor Logs"
        }
      }
    ]
  })
}
