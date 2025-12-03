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
  region     = data.aws_region.current.id
  account_id = data.aws_caller_identity.current.account_id

  common_tags = {
    Project     = "OMC Flywheel Cleanroom"
    Environment = "Production"
    Owner       = "Data Engineering"
    ManagedBy   = "Terraform"
  }
}

# Cleanrooms Identity Resolution Service Module
# 
# ⚠️  NOTE: Terraform AWS provider does NOT support Cleanrooms Identity Resolution Service resources yet.
# Use scripts/create-cr-namespace-resources.py to manage these resources instead.
#
# This module structure is provided for future use when Terraform provider support is added.
# Uncomment the module block below when provider support is available:
#
# module "cr_namespace" {
#   source = "../../modules/crnamespace"
#
#   membership_id            = var.cleanrooms_membership_id
#   id_namespace_name        = var.id_namespace_name
#   id_namespace_arn         = var.id_namespace_arn
#   id_namespace_description = var.id_namespace_description
#   
#   manage_resource_policies      = true
#   allow_use_as_dimension_column = false
#
#   # ID Mapping Table Configuration
#   id_mapping_table_name        = var.id_mapping_table_name
#   id_mapping_table_description = "ID mapping table for real IDs in entity resolution"
#   id_mapping_workflow_arn       = var.id_mapping_workflow_arn
#
#   # Input sources: SOURCE (ACX) and TARGET (AMC)
#   # Note: The source ID namespace association will be created by this module
#   # The target (AMC) association ID must be provided as it's created by another account
#   id_mapping_table_input_sources = [
#     {
#       id_namespace_association_id = module.cr_namespace.id_namespace_association_id
#       type                        = "SOURCE"
#     },
#     {
#       id_namespace_association_id = var.target_id_namespace_association_id
#       type                        = "TARGET"
#     }
#   ]
#
#   tags = local.common_tags
# }
