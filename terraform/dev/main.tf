# DEV Environment Terraform Configuration
# Cleanroom Bucketing Solution - DEV

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

# =============================================================================
# GLUE JOBS
# =============================================================================

# Infobase Split and Bucket Job
resource "aws_glue_job" "infobase_split_and_bucket" {
  name              = "etl-omc-flywheel-dev-infobase-split-and-bucket"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "5.0"
  worker_type       = "G.4X"
  number_of_workers = 24
  timeout           = 2880

  command {
    script_location = "s3://${var.glue_assets_bucket}/scripts/etl-omc-flywheel-dev-infobase-split-and-bucket.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"                    = "python"
    "--job-bookmark-option"            = "job-bookmark-disable"
    "--enable-metrics"                 = "true"
    "--enable-continuous-cloudwatch-log-group" = "true"
    "--AWS_REGION"                     = var.aws_region
    "--SOURCE_PATH"                    = "s3://${var.data_bucket}/opus/infobase_attributes/raw_input/"
    "--TARGET_PATH"                    = "s3://${var.data_bucket}/omc_cleanroom_data/split_cluster/"
    "--SNAPSHOT_DT"                    = "_NONE_"
    "--ENV"                           = "dev"
  }

  tags = {
    Name        = "etl-omc-flywheel-dev-infobase-split-and-bucket"
    Environment = "dev"
    Project     = "omc-flywheel"
    Purpose     = "infobase-split-and-bucket"
  }
}

# Addressable Bucket Job
resource "aws_glue_job" "addressable_bucket" {
  name              = "etl-omc-flywheel-dev-addressable-bucket"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "5.0"
  worker_type       = "G.4X"
  number_of_workers = 24
  timeout           = 2880

  command {
    script_location = "s3://${var.glue_assets_bucket}/scripts/etl-omc-flywheel-dev-addressable-bucket.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"                    = "python"
    "--job-bookmark-option"            = "job-bookmark-disable"
    "--enable-metrics"                 = "true"
    "--enable-continuous-cloudwatch-log-group" = "true"
    "--AWS_REGION"                     = var.aws_region
    "--SOURCE_PATH"                    = "s3://${var.data_bucket}/opus/addressable_ids/raw_input/"
    "--TARGET_PATH"                    = "s3://${var.data_bucket}/omc_cleanroom_data/split_cluster/"
    "--SNAPSHOT_DT"                    = "_NONE_"
    "--ENV"                           = "dev"
  }

  tags = {
    Name        = "etl-omc-flywheel-dev-addressable-bucket"
    Environment = "dev"
    Project     = "omc-flywheel"
    Purpose     = "addressable-bucket"
  }
}

# Register Staged Tables Job
resource "aws_glue_job" "register_staged_tables" {
  name              = "etl-omc-flywheel-dev-register-staged-tables"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 60

  command {
    script_location = "s3://${var.glue_assets_bucket}/scripts/etl-omc-flywheel-dev-register-staged-tables.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"                    = "python"
    "--job-bookmark-option"            = "job-bookmark-disable"
    "--enable-metrics"                 = "true"
    "--enable-continuous-cloudwatch-log-group" = "true"
    "--AWS_REGION"                     = var.aws_region
    "--STAGED_DB"                      = var.staged_database
    "--BUCKETED_BASE"                  = "s3://${var.data_bucket}/omc_cleanroom_data/split_cluster/"
    "--ENV"                           = "dev"
  }

  tags = {
    Name        = "etl-omc-flywheel-dev-register-staged-tables"
    Environment = "dev"
    Project     = "omc-flywheel"
    Purpose     = "register-staged-tables"
  }
}

# Create Athena Bucketed Tables Job
resource "aws_glue_job" "create_athena_bucketed_tables" {
  name              = "etl-omc-flywheel-dev-create-athena-bucketed-tables"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "5.0"
  worker_type       = "G.2X"
  number_of_workers = 8
  timeout           = 60

  command {
    script_location = "s3://${var.glue_assets_bucket}/scripts/etl-omc-flywheel-dev-create-athena-bucketed-tables.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"                    = "python"
    "--job-bookmark-option"            = "job-bookmark-disable"
    "--enable-metrics"                 = "true"
    "--enable-continuous-cloudwatch-log-group" = "true"
    "--AWS_REGION"                     = var.aws_region
    "--ATHENA_WORKGROUP"               = var.athena_workgroup
    "--ATHENA_RESULTS_S3"              = "s3://${var.analysis_bucket}/query-results/"
    "--STAGED_DB"                      = var.staged_database
    "--FINAL_DB"                       = var.final_database
    "--BUCKETED_BASE"                  = "s3://${var.data_bucket}/omc_cleanroom_data/split_cluster/"
    "--BUCKET_COL"                     = "customer_user_id"
    "--BUCKET_COUNT"                   = "64"
    "--VERSION_SUFFIX"                 = "v1"
    "--TABLES_FILTER"                  = "_NONE_"
    "--ENV"                           = "dev"
  }

  tags = {
    Name        = "etl-omc-flywheel-dev-create-athena-bucketed-tables"
    Environment = "dev"
    Project     = "omc-flywheel"
    Purpose     = "create-athena-bucketed-tables"
  }
}

# =============================================================================
# GLUE CRAWLERS
# =============================================================================

# Infobase Attributes Bucketed Crawler
resource "aws_glue_crawler" "infobase_attributes_bucketed" {
  name          = "crw-omc-flywheel-dev-infobase-attributes-bucketed-cr"
  role         = aws_iam_role.glue_role.arn
  database_name = var.final_database

  s3_target {
    path = "s3://${var.data_bucket}/omc_cleanroom_data/split_cluster/infobase_attributes/"
  }

  tags = {
    Name        = "crw-omc-flywheel-dev-infobase-attributes-bucketed-cr"
    Environment = "dev"
    Project     = "omc-flywheel"
    Purpose     = "infobase-attributes-bucketed"
  }
}

# Addressable IDs Bucketed Crawler
resource "aws_glue_crawler" "addressable_ids_bucketed" {
  name          = "crw-omc-flywheel-dev-addressable-ids-bucketed-cr"
  role         = aws_iam_role.glue_role.arn
  database_name = var.final_database

  s3_target {
    path = "s3://${var.data_bucket}/omc_cleanroom_data/split_cluster/addressable_ids/"
  }

  tags = {
    Name        = "crw-omc-flywheel-dev-addressable-ids-bucketed-cr"
    Environment = "dev"
    Project     = "omc-flywheel"
    Purpose     = "addressable-ids-bucketed"
  }
}

# =============================================================================
# IAM ROLE
# =============================================================================

# Glue Role
resource "aws_iam_role" "glue_role" {
  name = var.glue_role_name

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

  tags = {
    Name        = var.glue_role_name
    Environment = "dev"
    Project     = "omc-flywheel"
    Purpose     = "glue-execution-role"
  }
}

# Import existing managed policy for Glue Role
data "aws_iam_policy" "glue_s3_access" {
  name = "${var.glue_role_name}-s3-access"
}

# Attach existing managed policy to Glue Role
resource "aws_iam_role_policy_attachment" "glue_s3_access" {
  role       = aws_iam_role.glue_role.name
  policy_arn = data.aws_iam_policy.glue_s3_access.arn
}

# =============================================================================
# S3 BUCKETS
# =============================================================================

# Data Bucket
resource "aws_s3_bucket" "data_bucket" {
  bucket = var.data_bucket

  tags = {
    Name        = var.data_bucket
    Environment = "dev"
    Project     = "omc-flywheel"
    Purpose     = "data-storage"
  }
}

# Analysis Bucket
resource "aws_s3_bucket" "analysis_bucket" {
  bucket = var.analysis_bucket

  tags = {
    Name        = var.analysis_bucket
    Environment = "dev"
    Project     = "omc-flywheel"
    Purpose     = "analysis-results"
  }
}

# =============================================================================
# GLUE CATALOG DATABASE
# =============================================================================

# Final Database
resource "aws_glue_catalog_database" "final_database" {
  name        = var.final_database
  description = "Final bucketed tables for Cleanroom analysis"

  tags = {
    Name        = var.final_database
    Environment = "dev"
    Project     = "omc-flywheel"
    Purpose     = "final-tables"
  }
}
