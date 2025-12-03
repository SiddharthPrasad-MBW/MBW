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
  
  # Job name prefix (environment-aware)
  job_name_prefix = "etl-omc-flywheel-${var.environment}"
  
  # Script location prefix (environment-aware)
  script_location_prefix = "s3://aws-glue-assets-${local.account_id}-${local.region}/scripts"
  
  common_tags = merge(
    {
      Project     = "OMC Flywheel Cleanroom"
      Environment = local.environment_display
      Owner       = "Data Engineering"
      ManagedBy   = "Terraform"
      Component   = "Data Processing"
    },
    var.additional_tags
  )
}

# S3 Buckets (optional - can be provided externally)
resource "aws_s3_bucket" "data_bucket" {
  count  = var.create_s3_buckets ? 1 : 0
  bucket = var.data_bucket_name
  
  tags = local.common_tags
}

resource "aws_s3_bucket" "analysis_bucket" {
  count  = var.create_s3_buckets ? 1 : 0
  bucket = var.analysis_bucket_name
  
  tags = local.common_tags
}

# Glue Database (optional - can be provided externally)
resource "aws_glue_catalog_database" "main" {
  count = var.create_glue_database ? 1 : 0
  name  = var.glue_database_name
  
  tags = local.common_tags
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

# Attach AWS Glue Service Role
resource "aws_iam_role_policy_attachment" "glue_service_role" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# Custom S3 Access Policy for Glue Role
resource "aws_iam_policy" "glue_s3_access" {
  name        = "${var.project_name}-${var.environment}-glue-role-s3-access"
  description = "S3 access policy for OMC Flywheel Glue role"
  
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
      }
    ]
  })
  
  tags = local.common_tags
}

# Attach S3 Access Policy
resource "aws_iam_role_policy_attachment" "glue_s3_access" {
  role       = aws_iam_role.glue_role.name
  policy_arn = aws_iam_policy.glue_s3_access.arn
}

# Cleanrooms Read-Only Policy for Reporting
resource "aws_iam_policy" "glue_cleanrooms_read" {
  name        = "${var.project_name}-${var.environment}-glue-role-cleanrooms-read"
  description = "Cleanrooms read-only access for reporting jobs"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cleanrooms:GetConfiguredTable",
          "cleanrooms:ListConfiguredTables",
          "cleanrooms:GetConfiguredTableAnalysisRule",
          "cleanrooms:GetConfiguredTableAssociation",
          "cleanrooms:ListConfiguredTableAssociations",
          "cleanrooms:GetConfiguredTableAssociationAnalysisRule",
          "cleanrooms:GetMembership",
          "cleanrooms:ListMemberships",
          "cleanrooms:GetCollaboration",
          "cleanrooms:ListCollaborations",
          "cleanrooms:GetSchemaAnalysisRule",
          "cleanrooms:ListSchemas",
          "cleanrooms:GetIdNamespaceAssociation",
          "cleanrooms:ListIdNamespaceAssociations",
          "cleanrooms:GetIdMappingTable",
          "cleanrooms:ListIdMappingTables",
          "entityresolution:GetIdNamespace",
          "entityresolution:ListIdNamespaces",
          "entityresolution:GetSchemaMapping",
          "entityresolution:ListSchemaMappings",
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetDatabase",
          "glue:GetDatabases"
        ]
        Resource = "*"
      }
    ]
  })
  
  tags = local.common_tags
}

# Attach Cleanrooms Read Policy
resource "aws_iam_role_policy_attachment" "glue_cleanrooms_read" {
  role       = aws_iam_role.glue_role.name
  policy_arn = aws_iam_policy.glue_cleanrooms_read.arn
}

# Glue Jobs - Bucketed Pipeline
resource "aws_glue_job" "infobase_split_and_bucket" {
  name         = "${local.job_name_prefix}-infobase-split-and-bucket"
  role_arn     = aws_iam_role.glue_role.arn
  glue_version = "5.0"

  command {
    name            = "glueetl"
    script_location = "${local.script_location_prefix}/${local.job_name_prefix}-infobase-split-and-bucket.py"
  }

  worker_type       = "G.4X"
  number_of_workers = 24
  timeout           = 2880
  max_retries       = 0

  default_arguments = {
    "--job-language"         = "python"
    "--enable-metrics"       = "true"
    "--enable-job-insights"  = "true"
    "--spark-event-logs-path" = "s3://aws-glue-assets-${local.account_id}-${local.region}/spark-event-logs/"
    "--TempDir"              = "s3://aws-glue-assets-${local.account_id}-${local.region}/temp/"

    "--SNAPSHOT_DT"          = "_NONE_"
    "--SOURCE_PATH"           = "s3://${var.data_bucket_name}/opus/infobase_attributes/raw_input/"
    "--TARGET_PATH"           = "s3://${var.data_bucket_name}/omc_cleanroom_data/split_cluster/infobase_attributes/"
    "--CSV_FILE"              = "s3://${var.data_bucket_name}/omc_cleanroom_data/omc_flywheel_infobase_table_split_part.csv"

    # Spark optimization arguments
    "--spark.sql.adaptive.skewJoin.enabled" = "true"
    "--spark.sql.adaptive.coalescePartitions.minPartitionNum" = "24"
    "--spark.sql.adaptive.coalescePartitions.initialPartitionNum" = "600"
    "--spark.sql.parquet.mergeSchema" = "false"
    "--spark.sql.parquet.enableVectorizedReader" = "true"
    "--spark.sql.parquet.compression.codec" = "snappy"
    "--spark.sql.adaptive.enabled" = "true"
    "--spark.sql.adaptive.coalescePartitions.enabled" = "true"
    "--spark.sql.adaptive.advisoryPartitionSizeInBytes" = "536870912"
    "--spark.serializer" = "org.apache.spark.serializer.KryoSerializer"
  }

  tags = local.common_tags
}

resource "aws_glue_job" "addressable_bucket" {
  name         = "${local.job_name_prefix}-addressable-bucket"
  role_arn     = aws_iam_role.glue_role.arn
  glue_version = "5.0"

  command {
    name            = "glueetl"
    script_location = "${local.script_location_prefix}/${local.job_name_prefix}-addressable-bucket.py"
  }

  worker_type       = "G.4X"
  number_of_workers = 24
  timeout           = 2880
  max_retries       = 0

  default_arguments = {
    "--job-language"         = "python"
    "--enable-metrics"       = "true"
    "--enable-job-insights"  = "true"
    "--spark-event-logs-path" = "s3://aws-glue-assets-${local.account_id}-${local.region}/spark-event-logs/"
    "--TempDir"              = "s3://aws-glue-assets-${local.account_id}-${local.region}/temp/"

    "--SNAPSHOT_DT"          = "_NONE_"
    "--SOURCE_PATH"           = "s3://${var.data_bucket_name}/opus/addressable_ids/raw_input/"
    "--TARGET_PATH"           = "s3://${var.data_bucket_name}/omc_cleanroom_data/split_cluster/addressable_ids/"
    "--CSV_FILE"              = "s3://${var.data_bucket_name}/omc_cleanroom_data/omc_flywheel_addressable_ids_table_split_part.csv"
  }

  tags = local.common_tags
}

resource "aws_glue_job" "register_staged_tables" {
  name         = "${local.job_name_prefix}-register-staged-tables"
  role_arn     = aws_iam_role.glue_role.arn
  glue_version = "5.0"

  command {
    name            = "pythonshell"
    python_version  = "3.9"
    script_location = "${local.script_location_prefix}/${local.job_name_prefix}-register-staged-tables.py"
  }

  max_capacity = 0.0625  # Python Shell jobs use max_capacity (0.0625 = 1 DPU)
  timeout      = 300
  max_retries   = 0

  default_arguments = {
    "--job-language"         = "python"
    "--enable-metrics"       = "true"
    "--enable-job-insights"  = "true"
    "--spark-event-logs-path" = "s3://aws-glue-assets-${local.account_id}-${local.region}/spark-event-logs/"
    "--TempDir"              = "s3://aws-glue-assets-${local.account_id}-${local.region}/temp/"

    "--SNAPSHOT_DT"          = "_NONE_"
    "--SOURCE_PATH"           = "s3://${var.data_bucket_name}/omc_cleanroom_data/split_cluster/"
    "--STAGED_DB"             = var.glue_database_name
    "--TABLE_PREFIX"          = "ext_"
  }

  tags = local.common_tags
}

resource "aws_glue_job" "create_athena_bucketed_tables" {
  name         = "${local.job_name_prefix}-create-athena-bucketed-tables"
  role_arn     = aws_iam_role.glue_role.arn
  glue_version = "5.0"

  command {
    name            = "pythonshell"
    python_version  = "3.9"
    script_location = "${local.script_location_prefix}/${local.job_name_prefix}-create-athena-bucketed-tables.py"
  }

  max_capacity = 0.0625  # Python Shell jobs use max_capacity (0.0625 = 1 DPU)
  timeout      = 300
  max_retries   = 0

  default_arguments = {
    "--job-language"         = "python"
    "--enable-metrics"       = "true"
    "--enable-job-insights"  = "true"
    "--spark-event-logs-path" = "s3://aws-glue-assets-${local.account_id}-${local.region}/spark-event-logs/"
    "--TempDir"              = "s3://aws-glue-assets-${local.account_id}-${local.region}/temp/"

    "--ENV"                  = var.environment
    "--AWS_REGION"           = local.region
    "--ATHENA_WORKGROUP"     = "primary"
    "--ATHENA_RESULTS_S3"    = "s3://${var.analysis_bucket_name}/query-results/"
    "--STAGED_DB"             = var.glue_database_name
    "--FINAL_DB"              = var.glue_database_name
    "--BUCKETED_BASE"         = "s3://${var.data_bucket_name}/omc_cleanroom_data/cleanroom_tables/bucketed/"
    "--BUCKET_COL"            = "customer_user_id"
    "--BUCKET_COUNT"          = "256"
    "--VERSION_SUFFIX"        = "_NONE_"
    "--TABLES_FILTER"         = ""
  }

  tags = local.common_tags
}

resource "aws_glue_job" "create_part_addressable_ids_er_table" {
  name         = "${local.job_name_prefix}-create-part-addressable-ids-er-table"
  role_arn     = aws_iam_role.glue_role.arn
  glue_version = "5.0"

  command {
    name            = "pythonshell"
    python_version  = "3.9"
    script_location = "${local.script_location_prefix}/create-part-addressable-ids-er-table.py"
  }

  max_capacity = 0.0625  # Python Shell jobs use max_capacity (0.0625 = 1 DPU)
  timeout      = 300
  max_retries  = 0

  default_arguments = {
    "--job-language"         = "python"
    "--enable-metrics"       = "true"
    "--enable-job-insights"  = "true"
    "--spark-event-logs-path" = "s3://aws-glue-assets-${local.account_id}-${local.region}/spark-event-logs/"
    "--TempDir"              = "s3://aws-glue-assets-${local.account_id}-${local.region}/temp/"

    "--ENV"                  = var.environment
    "--AWS_REGION"           = local.region
    "--ATHENA_WORKGROUP"     = "primary"
    "--ATHENA_RESULTS_S3"    = "s3://${var.analysis_bucket_name}/query-results/"
    "--DATABASE"             = var.glue_database_name
    "--AWS_PROFILE"          = ""  # Empty for Glue execution (uses IAM role)
  }

  tags = local.common_tags
}

resource "aws_glue_job" "generate_cleanrooms_report" {
  name         = "${local.job_name_prefix}-generate-cleanrooms-report"
  role_arn     = aws_iam_role.glue_role.arn
  glue_version = "5.0"

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "${local.script_location_prefix}/generate-cleanrooms-report.py"
  }

  worker_type       = "G.1X"  # Glue ETL jobs use worker_type
  number_of_workers = 2
  timeout           = 300
  max_retries       = 0

  default_arguments = {
    "--job-language"         = "python"
    "--enable-metrics"       = "true"
    "--enable-job-insights"  = "true"
    "--spark-event-logs-path" = "s3://aws-glue-assets-${local.account_id}-${local.region}/spark-event-logs/"
    "--TempDir"              = "s3://aws-glue-assets-${local.account_id}-${local.region}/temp/"

    # Note: --profile is omitted - script uses default (empty) which uses IAM role in Glue
    "--region"               = local.region
    "--database"             = var.glue_database_name
    "--table-prefix"          = "part_"
    "--membership-id"         = var.cleanrooms_membership_id
    "--report-bucket"         = var.analysis_bucket_name
    "--report-prefix"         = "cleanrooms-reports/"
    "--output-format"         = "both"
  }

  tags = local.common_tags
}

# Glue Jobs - Partitioned Pipeline
resource "aws_glue_job" "infobase_split_and_part" {
  name         = "${local.job_name_prefix}-infobase-split-and-part"
  role_arn     = aws_iam_role.glue_role.arn
  glue_version = "5.0"

  command {
    name            = "glueetl"
    script_location = "${local.script_location_prefix}/${local.job_name_prefix}-infobase-split-and-part.py"
  }

  worker_type       = "G.4X"
  number_of_workers = 24
  timeout           = 2880
  max_retries       = 0

  default_arguments = {
    "--job-language"         = "python"
    "--enable-metrics"       = "true"
    "--enable-job-insights"  = "true"
    "--enable-observability-metrics" = "true"
    "--enable-spark-ui"      = "true"
    "--enable-glue-datacatalog" = "true"
    "--job-bookmark-option" = "job-bookmark-disable"
    "--spark-event-logs-path" = "s3://aws-glue-assets-${local.account_id}-${local.region}/sparkHistoryLogs/"
    "--TempDir"              = "s3://aws-glue-assets-${local.account_id}-${local.region}/temporary/"

    "--SNAPSHOT_DT"          = "_NONE_"
    "--SOURCE_PATH"           = "s3://${var.data_bucket_name}/opus/infobase_attributes/raw_input/"
    "--TARGET_BUCKET"         = "s3://${var.data_bucket_name}/omc_cleanroom_data/split_part/infobase_attributes/"
    "--CSV_PATH"              = "s3://${var.data_bucket_name}/omc_cleanroom_data/support_files/omc_flywheel_infobase_table_split_part.csv"
    "--BUCKET_COUNT"         = "256"
    "--TARGET_FILE_MB"       = "512"

    # Spark optimization arguments
    "--spark.sql.adaptive.skewJoin.enabled" = "true"
    "--spark.sql.adaptive.coalescePartitions.minPartitionNum" = "24"
    "--spark.sql.adaptive.coalescePartitions.initialPartitionNum" = "600"
    "--spark.sql.parquet.mergeSchema" = "false"
    "--spark.sql.parquet.enableVectorizedReader" = "true"
    "--spark.sql.parquet.compression.codec" = "snappy"
    "--spark.sql.adaptive.enabled" = "true"
    "--spark.sql.adaptive.coalescePartitions.enabled" = "true"
    "--spark.sql.adaptive.advisoryPartitionSizeInBytes" = "536870912"
    "--spark.serializer" = "org.apache.spark.serializer.KryoSerializer"
  }

  tags = local.common_tags
}

resource "aws_glue_job" "addressable_split_and_part" {
  name         = "${local.job_name_prefix}-addressable-split-and-part"
  role_arn     = aws_iam_role.glue_role.arn
  glue_version = "5.0"

  command {
    name            = "glueetl"
    script_location = "${local.script_location_prefix}/${local.job_name_prefix}-addressable-split-and-part.py"
  }

  worker_type       = "G.4X"
  number_of_workers = 24
  timeout           = 2880
  max_retries       = 0

  default_arguments = {
    "--job-language"         = "python"
    "--enable-metrics"       = "true"
    "--enable-job-insights"  = "true"
    "--enable-observability-metrics" = "true"
    "--enable-spark-ui"      = "true"
    "--enable-glue-datacatalog" = "true"
    "--job-bookmark-option" = "job-bookmark-disable"
    "--spark-event-logs-path" = "s3://aws-glue-assets-${local.account_id}-${local.region}/sparkHistoryLogs/"
    "--TempDir"              = "s3://aws-glue-assets-${local.account_id}-${local.region}/temporary/"

    "--SNAPSHOT_DT"          = "_NONE_"
    "--SOURCE_PATH"           = "s3://${var.data_bucket_name}/opus/addressable_ids/raw_input/"
    "--TARGET_PATH"           = "s3://${var.data_bucket_name}/omc_cleanroom_data/split_part/addressable_ids/"
    "--BUCKET_COUNT"         = "256"
    "--TARGET_FILE_MB"       = "512"
  }

  tags = local.common_tags
}

resource "aws_glue_job" "register_part_tables" {
  name         = "${local.job_name_prefix}-register-part-tables"
  role_arn     = aws_iam_role.glue_role.arn
  glue_version = "5.0"

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "${local.script_location_prefix}/${local.job_name_prefix}-register-part-tables.py"
  }

  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 300
  max_retries       = 0

  default_arguments = {
    "--job-language"         = "python"
    "--enable-metrics"       = "true"
    "--enable-job-insights"  = "true"
    "--spark-event-logs-path" = "s3://aws-glue-assets-${local.account_id}-${local.region}/spark-event-logs/"
    "--TempDir"              = "s3://aws-glue-assets-${local.account_id}-${local.region}/temp/"

    "--DATABASE"             = var.glue_database_name
    "--S3_ROOT"              = "s3://${var.data_bucket_name}/omc_cleanroom_data/split_part/addressable_ids/"
    "--MAX_COLS"             = "100"
    "--TABLE_PREFIX"         = "part_"
  }

  execution_property {
    max_concurrent_runs = 2
  }

  tags = local.common_tags
}

resource "aws_glue_job" "prepare_part_tables" {
  name         = "${local.job_name_prefix}-prepare-part-tables"
  role_arn     = aws_iam_role.glue_role.arn
  glue_version = "5.0"

  command {
    name            = "glueetl"
    script_location = "${local.script_location_prefix}/${local.job_name_prefix}-prepare-part-tables.py"
  }

  worker_type       = "G.1X"
  number_of_workers = 5
  timeout           = 300
  max_retries       = 0

  default_arguments = {
    "--job-language"         = "python"
    "--enable-metrics"       = "true"
    "--enable-job-insights"  = "true"
    "--spark-event-logs-path" = "s3://aws-glue-assets-${local.account_id}-${local.region}/spark-event-logs/"
    "--TempDir"              = "s3://aws-glue-assets-${local.account_id}-${local.region}/temp/"

    "--DATABASE"             = var.glue_database_name
    "--TABLE_PREFIX"         = "part_"
    "--AWS_REGION"           = local.region
    "--ATHENA_WORKGROUP"     = "primary"
    "--ATHENA_RESULTS"       = "s3://${var.analysis_bucket_name}/query-results/msck/"
    # STRIP_PROJECTION and LOG_SAMPLE are optional with defaults in script
    # Can be added later if needed, script defaults to STRIP_PROJECTION=true, LOG_SAMPLE=0
    # MAX_PARTS_PER_BATCH is optional, default 100
  }

  tags = local.common_tags
}

# Glue Crawlers
resource "aws_glue_crawler" "infobase_attributes_bucketed" {
  name          = "crw-${var.project_name}-${var.environment}-infobase-attributes-bucketed-cr"
  role          = aws_iam_role.glue_role.arn
  database_name = var.glue_database_name
  
  s3_target {
    path = "s3://${var.data_bucket_name}/omc_cleanroom_data/cleanroom_tables/bucketed/infobase_attributes/"
  }
  
  tags = local.common_tags
}

resource "aws_glue_crawler" "addressable_ids_bucketed" {
  name          = "crw-${var.project_name}-${var.environment}-addressable-ids-bucketed-cr"
  role          = aws_iam_role.glue_role.arn
  database_name = var.glue_database_name
  
  s3_target {
    path = "s3://${var.data_bucket_name}/omc_cleanroom_data/cleanroom_tables/bucketed/addressable_ids/"
  }
  
  tags = local.common_tags
}
