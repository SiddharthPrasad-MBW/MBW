# Cleanrooms Configured Tables Module Outputs
output "cleanrooms_tables" {
  description = "Cleanrooms configured tables information"
  value = {
    configured_table_ids         = module.cleanrooms_tables.configured_table_ids
    configured_table_association_ids = module.cleanrooms_tables.configured_table_association_ids
    role_arn                     = module.cleanrooms_tables.role_arn
    configured_table_names       = module.cleanrooms_tables.configured_table_names
  }
}

output "account_info" {
  description = "AWS account and region information"
  value = {
    account_id = data.aws_caller_identity.current.account_id
    region     = data.aws_region.current.name
  }
}

