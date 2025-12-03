output "table_association_info" {
  description = "Information about table associations (managed via script)"
  value = {
    membership_id = var.membership_id
    table_count   = length(var.existing_configured_tables)
    tables        = var.existing_configured_tables
  }
}

output "role_arn" {
  description = "IAM role ARN used for associations"
  value       = data.aws_iam_role.cleanrooms_access.arn
}

