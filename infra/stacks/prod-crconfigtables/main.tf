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

# Cleanrooms Configured Tables Module (separate state)
module "cleanrooms_tables" {
  source = "../../modules/crconfigtables"

  create_role            = true
  membership_id          = var.cleanrooms_membership_id
  allowed_query_providers = var.cleanrooms_allowed_query_providers
  use_all_columns        = true
  s3_resources           = [
    "arn:aws:s3:::${var.data_bucket_name}",
    "arn:aws:s3:::${var.data_bucket_name}/*"
  ]
  tags = local.common_tags

  tables = {
    for table_name in [
      "part_ibe_01", "part_ibe_01_a",
      "part_ibe_02", "part_ibe_02_a",
      "part_ibe_03", "part_ibe_03_a",
      "part_ibe_04", "part_ibe_04_a", "part_ibe_04_b",
      "part_ibe_05", "part_ibe_05_a",
      "part_ibe_06", "part_ibe_06_a",
      "part_ibe_08", "part_ibe_09",
      "part_miacs_01", "part_miacs_01_a",
      "part_miacs_02", "part_miacs_02_a", "part_miacs_02_b",
      "part_miacs_03", "part_miacs_03_a", "part_miacs_03_b",
      "part_miacs_04",
      "part_n_a", "part_n_a_a",
      "part_new_borrowers"
    ] :
    table_name => {
      description     = "Partitioned table ${table_name} for Clean Rooms analysis"
      analysis_method = "DIRECT"
      glue = {
        region   = local.region
        database = var.glue_database_name
        table    = table_name
      }
      rule = {
        type = "CUSTOM"
      }
    }
  }
}

