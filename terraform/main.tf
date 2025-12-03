# OMC Flywheel Cleanroom Production Terraform Configuration
# This configuration manages the production Cleanroom bucketing solution

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
  region = var.aws_region
  profile = var.aws_profile
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Local values
locals {
  account_id = data.aws_caller_identity.current.account_id
  region = data.aws_region.current.name
  
  # Common tags
  common_tags = {
    Project     = "OMC Flywheel Cleanroom"
    Environment = "Production"
    ManagedBy   = "Terraform"
    Owner       = "Data Engineering"
  }
  
  # S3 bucket names
  data_bucket = "omc-flywheel-data-us-east-1-prod"
  analysis_bucket = "omc-flywheel-prod-analysis-data"
  glue_assets_bucket = "aws-glue-assets-${local.account_id}-${local.region}"
}

# S3 Buckets
resource "aws_s3_bucket" "data_bucket" {
  bucket = local.data_bucket
  
  tags = merge(local.common_tags, {
    Name = "OMC Flywheel Production Data"
    Purpose = "Cleanroom data storage"
  })
}

resource "aws_s3_bucket" "analysis_bucket" {
  bucket = local.analysis_bucket
  
  tags = merge(local.common_tags, {
    Name = "OMC Flywheel Production Analysis"
    Purpose = "Athena query results"
  })
}

# Glue Database
resource "aws_glue_catalog_database" "main" {
  name = var.glue_database_name
  
  description = "OMC Flywheel Production Cleanroom Database"
}

# IAM Role for Glue Jobs
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
  
  tags = local.common_tags
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

# Attach AWS managed policy for Glue service role
resource "aws_iam_role_policy_attachment" "glue_service_role" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# Glue Jobs
resource "aws_glue_job" "infobase_split_and_bucket" {
  name         = "etl-omc-flywheel-prod-infobase-split-and-bucket"
  role_arn     = aws_iam_role.glue_role.arn
  glue_version = "5.0"
  
  command {
    script_location = "s3://${local.glue_assets_bucket}/scripts/etl-omc-flywheel-prod-infobase-split-and-bucket.py"
    python_version  = "3"
  }
  
  worker_type       = "G.4X"
  number_of_workers = 24
  timeout           = 2880
  max_retries       = 0
  
  default_arguments = {
    "--job-language"                                    = "python"
    "--job-bookmark-option"                             = "job-bookmark-disable"
    "--enable-glue-datacatalog"                         = "true"
    "--enable-metrics"                                  = "true"
    "--enable-spark-ui"                                 = "true"
    "--enable-job-insights"                             = "true"
    "--enable-observability-metrics"                    = "true"
    "--spark-event-logs-path"                           = "s3://${local.glue_assets_bucket}/sparkHistoryLogs/"
    "--TempDir"                                         = "s3://${local.glue_assets_bucket}/temporary/"
    "--SOURCE_PATH"                                     = "s3://${local.data_bucket}/opus/infobase_attributes/raw_input/"
    "--TARGET_BUCKET"                                   = "s3://${local.data_bucket}/omc_cleanroom_data/split_cluster/infobase_attributes/"
    "--CSV_PATH"                                        = "s3://${local.data_bucket}/omc_cleanroom_data/support_files/omc_flywheel_infobase_table_split_part.csv"
    "--SNAPSHOT_DT"                                     = "_NONE_"
    "--BUCKET_COUNT"                                    = "256"
    "--TARGET_FILE_MB"                                  = "512"
    "--spark.sql.adaptive.enabled"                      = "true"
    "--spark.sql.adaptive.coalescePartitions.enabled"   = "true"
    "--spark.sql.adaptive.coalescePartitions.minPartitionNum" = "24"
    "--spark.sql.adaptive.coalescePartitions.initialPartitionNum" = "600"
    "--spark.sql.adaptive.advisoryPartitionSizeInBytes" = "536870912"
    "--spark.sql.adaptive.skewJoin.enabled"            = "true"
    "--spark.sql.parquet.enableVectorizedReader"       = "true"
    "--spark.sql.parquet.mergeSchema"                  = "false"
    "--spark.sql.parquet.compression.codec"            = "snappy"
    "--spark.serializer"                                = "org.apache.spark.serializer.KryoSerializer"
  }
  
  execution_property {
    max_concurrent_runs = 1
  }
  
  tags = local.common_tags
}

resource "aws_glue_job" "addressable_bucket" {
  name         = "etl-omc-flywheel-prod-addressable-bucket"
  role_arn     = aws_iam_role.glue_role.arn
  glue_version = "5.0"
  
  command {
    script_location = "s3://${local.glue_assets_bucket}/scripts/etl-omc-flywheel-prod-addressable-bucket.py"
    python_version  = "3"
  }
  
  worker_type       = "G.4X"
  number_of_workers = 24
  timeout           = 2880
  max_retries       = 0
  
  default_arguments = {
    "--job-language"                = "python"
    "--job-bookmark-option"         = "job-bookmark-disable"
    "--enable-glue-datacatalog"     = "true"
    "--enable-metrics"              = "true"
    "--enable-spark-ui"             = "true"
    "--enable-job-insights"         = "true"
    "--enable-observability-metrics" = "true"
    "--spark-event-logs-path"       = "s3://${local.glue_assets_bucket}/sparkHistoryLogs/"
    "--TempDir"                     = "s3://${local.glue_assets_bucket}/temporary/"
    "--SOURCE_PATH"                 = "s3://${local.data_bucket}/opus/addressable_ids/raw_input/"
    "--TARGET_PATH"                 = "s3://${local.data_bucket}/omc_cleanroom_data/split_cluster/addressable_ids/"
    "--SNAPSHOT_DT"                 = "_NONE_"
    "--BUCKET_COUNT"                = "256"
    "--TARGET_FILE_MB"              = "512"
  }
  
  execution_property {
    max_concurrent_runs = 1
  }
  
  tags = local.common_tags
}

resource "aws_glue_job" "register_staged_tables" {
  name         = "etl-omc-flywheel-prod-register-staged-tables"
  role_arn     = aws_iam_role.glue_role.arn
  glue_version = "5.0"
  
  command {
    script_location = "s3://${local.glue_assets_bucket}/scripts/etl-omc-flywheel-prod-register-staged-tables.py"
    python_version  = "3"
  }
  
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 60
  max_retries       = 0
  
  default_arguments = {
    "--job-language"        = "python"
    "--enable-metrics"      = "true"
    "--enable-job-insights" = "true"
    "--spark-event-logs-path" = "s3://${local.glue_assets_bucket}/spark-event-logs/"
    "--TempDir"             = "s3://${local.glue_assets_bucket}/temp/"
    "--DATABASE"            = var.glue_database_name
    "--S3_ROOT"             = "s3://${local.data_bucket}/omc_cleanroom_data/split_cluster/addressable_ids/"
    "--MAX_COLS"            = "100"
    "--TABLE_PREFIX"        = "ext_"
  }
  
  execution_property {
    max_concurrent_runs = 1
  }
  
  tags = local.common_tags
}

resource "aws_glue_job" "create_athena_bucketed_tables" {
  name         = "etl-omc-flywheel-prod-create-athena-bucketed-tables"
  role_arn     = aws_iam_role.glue_role.arn
  glue_version = "5.0"
  
  command {
    script_location = "s3://${local.glue_assets_bucket}/scripts/etl-omc-flywheel-prod-create-athena-bucketed-tables.py"
    python_version  = "3"
  }
  
  worker_type       = "G.4X"
  number_of_workers = 10
  timeout           = 60
  max_retries       = 0
  
  default_arguments = {
    "--job-language"        = "python"
    "--enable-metrics"      = "true"
    "--enable-job-insights"  = "true"
    "--spark-event-logs-path" = "s3://${local.glue_assets_bucket}/spark-event-logs/"
    "--TempDir"             = "s3://${local.glue_assets_bucket}/temp/"
    "--ENV"                 = "prod"
    "--AWS_REGION"          = local.region
    "--ATHENA_WORKGROUP"    = "primary"
    "--ATHENA_RESULTS_S3"   = "s3://${local.analysis_bucket}/query-results/"
    "--STAGED_DB"           = var.glue_database_name
    "--FINAL_DB"            = var.glue_database_name
    "--BUCKETED_BASE"       = "s3://${local.data_bucket}/omc_cleanroom_data/cleanroom_tables/bucketed/"
    "--BUCKET_COL"          = "customer_user_id"
    "--BUCKET_COUNT"        = "256"
    "--VERSION_SUFFIX"      = "_NONE_"
    "--TABLES_FILTER"       = "_NONE_"
  }
  
  execution_property {
    max_concurrent_runs = 1
  }
  
  tags = local.common_tags
}

# Infobase Split and Part Job
resource "aws_glue_job" "infobase_split_and_part" {
  name         = "etl-omc-flywheel-prod-infobase-split-and-part"
  role_arn     = aws_iam_role.glue_role.arn
  glue_version = "5.0"
  
  command {
    script_location = "s3://${local.glue_assets_bucket}/scripts/etl-omc-flywheel-prod-infobase-split-and-part.py"
    python_version  = "3"
  }
  
  worker_type       = "G.4X"
  number_of_workers = 24
  timeout           = 2880
  max_retries       = 0
  
  default_arguments = {
    "--job-language"                                    = "python"
    "--job-bookmark-option"                             = "job-bookmark-disable"
    "--enable-glue-datacatalog"                         = "true"
    "--enable-metrics"                                  = "true"
    "--enable-spark-ui"                                 = "true"
    "--enable-job-insights"                             = "true"
    "--enable-observability-metrics"                    = "true"
    "--spark-event-logs-path"                           = "s3://${local.glue_assets_bucket}/sparkHistoryLogs/"
    "--TempDir"                                         = "s3://${local.glue_assets_bucket}/temporary/"
    "--SOURCE_PATH"                                     = "s3://${local.data_bucket}/opus/infobase_attributes/raw_input/"
    "--TARGET_BUCKET"                                   = "s3://${local.data_bucket}/omc_cleanroom_data/split_part/infobase_attributes/"
    "--CSV_PATH"                                        = "s3://${local.data_bucket}/omc_cleanroom_data/support_files/omc_flywheel_infobase_table_split_part.csv"
    "--SNAPSHOT_DT"                                     = "_NONE_"
    "--BUCKET_COUNT"                                    = "256"
    "--TARGET_FILE_MB"                                  = "512"
    "--spark.sql.adaptive.enabled"                      = "true"
    "--spark.sql.adaptive.coalescePartitions.enabled"   = "true"
    "--spark.sql.adaptive.coalescePartitions.minPartitionNum" = "24"
    "--spark.sql.adaptive.coalescePartitions.initialPartitionNum" = "600"
    "--spark.sql.adaptive.advisoryPartitionSizeInBytes" = "536870912"
    "--spark.sql.adaptive.skewJoin.enabled"            = "true"
    "--spark.sql.parquet.enableVectorizedReader"       = "true"
    "--spark.sql.parquet.mergeSchema"                  = "false"
    "--spark.sql.parquet.compression.codec"            = "snappy"
    "--spark.serializer"                                = "org.apache.spark.serializer.KryoSerializer"
  }
  
  execution_property {
    max_concurrent_runs = 1
  }
  
  tags = local.common_tags
}

# Addressable Split and Part Job
resource "aws_glue_job" "addressable_split_and_part" {
  name         = "etl-omc-flywheel-prod-addressable-split-and-part"
  role_arn     = aws_iam_role.glue_role.arn
  glue_version = "5.0"
  
  command {
    script_location = "s3://${local.glue_assets_bucket}/scripts/etl-omc-flywheel-prod-addressable-split-and-part.py"
    python_version  = "3"
  }
  
  worker_type       = "G.4X"
  number_of_workers = 24
  timeout           = 2880
  max_retries       = 0
  
  default_arguments = {
    "--job-language"                = "python"
    "--job-bookmark-option"         = "job-bookmark-disable"
    "--enable-glue-datacatalog"     = "true"
    "--enable-metrics"              = "true"
    "--enable-spark-ui"             = "true"
    "--enable-job-insights"         = "true"
    "--enable-observability-metrics" = "true"
    "--spark-event-logs-path"       = "s3://${local.glue_assets_bucket}/sparkHistoryLogs/"
    "--TempDir"                     = "s3://${local.glue_assets_bucket}/temporary/"
    "--SOURCE_PATH"                 = "s3://${local.data_bucket}/opus/addressable_ids/raw_input/"
    "--TARGET_PATH"                 = "s3://${local.data_bucket}/omc_cleanroom_data/split_part/addressable_ids/"
    "--SNAPSHOT_DT"                 = "_NONE_"
    "--BUCKET_COUNT"                = "256"
    "--TARGET_FILE_MB"              = "512"
  }
  
  execution_property {
    max_concurrent_runs = 1
  }
  
  tags = local.common_tags
}

# Register Part Tables Job
resource "aws_glue_job" "register_part_tables" {
  name         = "etl-omc-flywheel-prod-register-part-tables"
  role_arn     = aws_iam_role.glue_role.arn
  glue_version = "5.0"
  
  command {
    script_location = "s3://${local.glue_assets_bucket}/scripts/etl-omc-flywheel-prod-register-part-tables.py"
    python_version  = "3"
  }
  
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 60
  max_retries       = 0
  
  default_arguments = {
    "--job-language"        = "python"
    "--enable-metrics"      = "true"
    "--enable-job-insights" = "true"
    "--spark-event-logs-path" = "s3://${local.glue_assets_bucket}/spark-event-logs/"
    "--TempDir"             = "s3://${local.glue_assets_bucket}/temp/"
    "--DATABASE"            = var.glue_database_name
    "--S3_ROOT"             = "s3://${local.data_bucket}/omc_cleanroom_data/split_part/addressable_ids/"
    "--MAX_COLS"            = "100"
    "--TABLE_PREFIX"        = "part_"
  }
  
  execution_property {
    max_concurrent_runs = 1
  }
  
  tags = local.common_tags
}

# Prepare partitioned tables: run Athena MSCK REPAIR on part_* tables
resource "aws_glue_job" "prepare_part_tables" {
  name         = "etl-omc-flywheel-prod-prepare-part-tables"
  role_arn     = aws_iam_role.glue_role.arn
  glue_version = "5.0"

  command {
    script_location = "s3://${local.glue_assets_bucket}/scripts/etl-omc-flywheel-prod-prepare-part-tables.py"
    python_version  = "3"
  }

  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 60
  max_retries       = 0

  default_arguments = {
    "--job-language"         = "python"
    "--enable-metrics"       = "true"
    "--enable-job-insights"  = "true"
    "--spark-event-logs-path" = "s3://${local.glue_assets_bucket}/spark-event-logs/"
    "--TempDir"              = "s3://${local.glue_assets_bucket}/temp/"

    "--AWS_REGION"           = local.region
    "--DATABASE"             = var.glue_database_name
    "--WORKGROUP"            = "primary"
    "--RESULTS_S3"           = "s3://${local.analysis_bucket}/query-results/msck/"
    "--TABLE_PREFIX"         = "part_"
    "--MAX_CONCURRENCY"      = "5"
    "--POLL_INTERVAL_SEC"    = "2"
  }

  execution_property {
    max_concurrent_runs = 1
  }

  tags = local.common_tags
}


# Glue Crawlers
resource "aws_glue_crawler" "infobase_attributes_bucketed" {
  name          = "crw-omc-flywheel-prod-infobase-attributes-bucketed-cr"
  role          = aws_iam_role.glue_role.arn
  database_name = aws_glue_catalog_database.main.name
  
  s3_target {
    path = "s3://${local.data_bucket}/omc_cleanroom_data/cleanroom_tables/bucketed/infobase_attributes/"
  }
  
  recrawl_policy {
    recrawl_behavior = "CRAWL_EVERYTHING"
  }
  
  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "DEPRECATE_IN_DATABASE"
  }
  
  configuration = jsonencode({
    Version = 1.0
    CreatePartitionIndex = true
  })
  
  tags = local.common_tags
}

resource "aws_glue_crawler" "addressable_ids_bucketed" {
  name          = "crw-omc-flywheel-prod-addressable-ids-bucketed-cr"
  role          = aws_iam_role.glue_role.arn
  database_name = aws_glue_catalog_database.main.name
  table_prefix  = "bucketed_"
  
  s3_target {
    path = "s3://${local.data_bucket}/omc_cleanroom_data/cleanroom_tables/bucketed/addressable_ids/"
  }
  
  recrawl_policy {
    recrawl_behavior = "CRAWL_EVERYTHING"
  }
  
  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "DEPRECATE_IN_DATABASE"
  }
  
  configuration = jsonencode({
    Version = 1.0
    CreatePartitionIndex = true
  })
  
  tags = local.common_tags
}
