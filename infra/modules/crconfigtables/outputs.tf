output "configured_table_ids" {
  value       = { for k, v in aws_cleanrooms_configured_table.ct : k => v.id }
  description = "IDs of created configured tables."
}

output "configured_table_association_ids" {
  value       = { for k, v in aws_cleanrooms_configured_table_association.assoc : k => v.id }
  description = "IDs of table associations (if membership_id provided)."
}

output "role_arn" {
  value       = var.create_role ? aws_iam_role.cleanrooms_access[0].arn : var.role_arn
  description = "Role ARN used by Clean Rooms."
}

output "configured_table_names" {
  value       = { for k, v in aws_cleanrooms_configured_table.ct : k => v.name }
  description = "Names of created configured tables."
}

