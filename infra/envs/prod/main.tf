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
    Environment = "Production"
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

# Lake Formation Module
module "lake_formation" {
  source = "../../modules/lakeformation"
  
  # Environment
  region     = local.region
  account_id = local.account_id
  env        = "prod"
  
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
  writer_principals = ["arn:aws:iam::${local.account_id}:role/omc_flywheel-prod-glue-role"]
  reader_principals = [
    "arn:aws:iam::${local.account_id}:role/omc_flywheel-prod-cleanroom-consumer"
  ]
  
  # Configuration
  register_raw_source = true
  lf_only_defaults    = false
  enable              = true
}