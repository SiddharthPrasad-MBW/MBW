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
    Environment = "Development"
    Owner       = "Data Engineering"
    ManagedBy   = "Terraform"
  }
}

# Glue Jobs Module only (separate state for Glue)
module "glue_jobs" {
  source = "../../modules/gluejobs"

  # Environment
  aws_region   = local.region
  environment  = "dev"  # Used in tags (will display as "Development")
  project_name = "omc-flywheel"
  
  # Optional: Add additional tags if needed
  # additional_tags = {
  #   CostCenter = "DataEngineering"
  #   Team       = "OMC"
  # }

  # Existing resources (passed in)
  glue_database_name    = var.glue_database_name
  data_bucket_name      = var.data_bucket_name
  analysis_bucket_name  = var.analysis_bucket_name
  glue_role_name        = var.glue_role_name

  # Do not create shared resources in this stack
  create_s3_buckets    = false
  create_glue_database = false
  create_iam_role      = false

  # Pipeline toggles (keep both enabled)
  enable_bucketed_pipeline     = true
  enable_partitioned_pipeline  = true
  enable_crawlers              = true

  # Job config defaults (dev-specific: lower resources, more retries for testing)
  worker_count    = 5   # Lower than prod (10)
  timeout_minutes = 30  # Shorter than prod (60)
  max_retries     = 2   # More retries for testing (prod: 1)

  # Cleanrooms configuration (optional for dev)
  cleanrooms_membership_id = var.cleanrooms_membership_id
}

output "glue_jobs" {
  description = "Glue jobs and related outputs from the Glue module"
  value = {
    bucketed_pipeline    = module.glue_jobs.bucketed_pipeline_jobs
    partitioned_pipeline = module.glue_jobs.partitioned_pipeline_jobs
    all_jobs             = module.glue_jobs.all_glue_jobs
    crawlers             = module.glue_jobs.glue_crawlers
  }
}

