# Cleanrooms Identity Resolution Service Resources
# 
# ⚠️  IMPORTANT: The Terraform AWS provider does NOT currently support Cleanrooms Identity Resolution Service resources.
# These resources must be managed via boto3 scripts (see scripts/create-cr-namespace-resources.py).
#
# This module structure is provided for future use when Terraform provider support is added.
# For now, use the Python script to manage these resources.

# ID Namespace Association
# Links an Entity Resolution ID namespace to a Cleanrooms membership
# NOTE: This resource type is not yet supported by the Terraform AWS provider
# Uncomment when provider support is added:
#
# resource "aws_cleanrooms_id_namespace_association" "namespace" {
#   membership_identifier = var.membership_id
#   name                  = var.id_namespace_name
#   description           = var.id_namespace_description
#
#   input_reference_config {
#     input_reference_arn    = var.id_namespace_arn
#     manage_resource_policies = var.manage_resource_policies
#   }
#
#   id_mapping_config {
#     allow_use_as_dimension_column = var.allow_use_as_dimension_column
#   }
#
#   tags = var.tags
# }

# ID Mapping Table
# Creates an ID mapping table in the collaboration's entity resolution
# Only create if id_mapping_table_name is provided
# NOTE: This resource type is not yet supported by the Terraform AWS provider
# Uncomment when provider support is added:
#
# resource "aws_cleanrooms_id_mapping_table" "mapping_table" {
#   count = var.id_mapping_table_name != null ? 1 : 0
#
#   membership_identifier = var.membership_id
#   name                  = var.id_mapping_table_name
#   description           = var.id_mapping_table_description
#
#   input_reference_config {
#     input_reference_arn    = var.id_mapping_workflow_arn
#     manage_resource_policies = var.manage_resource_policies
#   }
#
#   dynamic "input_reference_properties" {
#     for_each = length(var.id_mapping_table_input_sources) > 0 ? [1] : []
#     content {
#       dynamic "id_mapping_table_input_source" {
#         for_each = var.id_mapping_table_input_sources
#         content {
#           id_namespace_association_id = id_mapping_table_input_source.value.id_namespace_association_id
#           type                        = id_mapping_table_input_source.value.type
#         }
#       }
#     }
#   }
#
#   tags = var.tags
#
#   depends_on = [aws_cleanrooms_id_namespace_association.namespace]
# }
