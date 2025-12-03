terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
    null = {
      source  = "hashicorp/null"
      version = ">= 3.0"
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

# Associate existing resources to collaboration membership
module "associate_resources" {
  source = "../../modules/crassociations"

  membership_id = var.membership_id
  
  # Discover tables using: python3 scripts/discover-configured-tables.py --filter "part_"
  existing_configured_tables = var.existing_configured_tables
  
  id_namespace_arn  = var.id_namespace_arn
  id_namespace_name = var.id_namespace_name
  
  role_name  = var.role_name
  aws_profile = var.aws_profile
  aws_region  = local.region
  
  tags = local.common_tags
}

