terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  region     = data.aws_region.current.name
  account_id = data.aws_caller_identity.current.account_id

  common_tags = {
    Project     = "OMC Flywheel Cleanroom"
    Environment = "Production"
    Owner       = "Data Engineering"
    ManagedBy   = "Terraform"
  }
}

# Monitoring Module only (separate state for Monitoring)
module "monitoring" {
  source = "../../modules/monitoring"

  # Environment
  aws_region   = local.region
  environment  = "prod"  # Used in tags (will display as "Production")
  project_name = "omc-flywheel"
  
  # Optional: Add additional tags if needed
  # additional_tags = {
  #   CostCenter = "DataEngineering"
  #   Team       = "OMC"
  # }

  # Dependencies (use existing resources)
  glue_database_name   = var.glue_database_name
  data_bucket_name     = var.data_bucket_name
  analysis_bucket_name = var.analysis_bucket_name

  # Do not create shared resources in this stack
  create_s3_buckets    = false
  create_glue_database = false

  # Monitoring Configuration
  monitoring_schedule = "rate(24 hours)"
  retention_days       = 30
  worker_count        = 2
  timeout_minutes     = 5

  # Data Quality Checks
  enable_file_size_check    = false
  count_tolerance_percent   = 0
  freshness_window_days     = 45
  pk_column                 = "customer_user_id"
}

output "monitoring" {
  description = "Monitoring infrastructure outputs"
  value = {
    job_name        = module.monitoring.data_monitor_job_name
    job_arn         = module.monitoring.data_monitor_job_arn
    sns_topic_arn   = module.monitoring.sns_topic_arn
    dashboard_url   = module.monitoring.cloudwatch_dashboard_url
    monitoring_role = module.monitoring.monitoring_role_arn
    log_group       = module.monitoring.log_group_name
    report_location = module.monitoring.report_s3_location
  }
}

