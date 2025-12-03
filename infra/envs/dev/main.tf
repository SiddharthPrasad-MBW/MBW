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
  
  common_tags = {
    Project     = "OMC Flywheel Cleanroom"
    Environment = "Development"
    Owner       = "Data Engineering"
    ManagedBy   = "Terraform"
  }
}

# S3 Buckets
resource "aws_s3_bucket" "data_bucket" {
  bucket = var.data_bucket_name
  
  tags = local.common_tags
}

resource "aws_s3_bucket" "analysis_bucket" {
  bucket = var.analysis_bucket_name
  
  tags = local.common_tags
}

# Glue Database
resource "aws_glue_catalog_database" "main" {
  name = var.glue_database_name
  
  tags = local.common_tags
}

# Glue Jobs Module
module "glue_jobs" {
  source = "../../modules/gluejobs"
  
  # Environment
  aws_region  = local.region
  environment = "dev"
  project_name = "omc-flywheel"
  
  # Dependencies (use existing resources)
  glue_database_name  = aws_glue_catalog_database.main.name
  data_bucket_name    = aws_s3_bucket.data_bucket.bucket
  analysis_bucket_name = aws_s3_bucket.analysis_bucket.bucket
  glue_role_name      = "omc_flywheel-dev-glue-role"
  
  # Don't create these resources (they're created above)
  create_s3_buckets   = false
  create_glue_database = false
  create_iam_role     = true
  
  # Pipeline Configuration
  enable_bucketed_pipeline    = true
  enable_partitioned_pipeline = true
  enable_crawlers            = true
  
  # Job Configuration (smaller for dev)
  worker_count     = 5
  timeout_minutes  = 30
  max_retries      = 1
  bucket_count     = 64  # Smaller for dev
  athena_workgroup = "primary"
}

# Monitoring Module
module "monitoring" {
  source = "../../modules/monitoring"
  
  # Environment
  aws_region  = local.region
  environment = "dev"
  project_name = "omc-flywheel"
  
  # Dependencies
  glue_database_name  = aws_glue_catalog_database.main.name
  data_bucket_name    = aws_s3_bucket.data_bucket.bucket
  analysis_bucket_name = aws_s3_bucket.analysis_bucket.bucket
  
  # Monitoring Configuration (more frequent for dev)
  monitoring_schedule = "rate(6 hours)"
  retention_days      = 7  # Shorter retention for dev
  worker_count        = 1
  timeout_minutes     = 3
  
  # Data Quality Checks
  enable_file_size_check    = true  # Enable for dev testing
  count_tolerance_percent   = 5     # More lenient for dev
  freshness_window_days     = 7     # Shorter window for dev
}

# Lake Formation Module
module "lake_formation" {
  source = "../../modules/lakeformation"
  
  # Environment
  region     = local.region
  account_id = local.account_id
  env        = "dev"
  
  # Database
  database_name = aws_glue_catalog_database.main.name
  
  # S3 Paths
  target_bucket = aws_s3_bucket.data_bucket.bucket
  target_prefix = "omc_cleanroom_data/cleanroom_tables/bucketed/"
  
  source_bucket = aws_s3_bucket.data_bucket.bucket
  source_prefix = "omc_cleanroom_data/split_cluster/"
  
  raw_source_bucket = aws_s3_bucket.data_bucket.bucket
  raw_source_prefix = "opus/"
  
  # Principals
  writer_principals = [module.glue_jobs.glue_role_arn]
  reader_principals = [
    "arn:aws:iam::${local.account_id}:role/omc_flywheel-dev-cleanroom-role"
  ]
  
  # Configuration
  register_source     = true
  register_raw_source = true
  lf_only_defaults    = false
  enable              = true
}