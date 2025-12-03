output "registered_target_arn" {
  value       = var.enable ? aws_lakeformation_resource.target[0].arn : null
  description = "Registered LF S3 target path ARN (bucketed data)"
}

output "registered_source_arn" {
  value       = var.enable ? aws_lakeformation_resource.source[0].arn : null
  description = "Registered LF S3 source path ARN (split_cluster data - where ext_ tables point)"
}

output "registered_raw_source_arn" {
  value       = var.enable && var.register_raw_source ? aws_lakeformation_resource.raw_source[0].arn : null
  description = "Registered LF S3 raw source path ARN (opus/ data)"
}

output "database_name" {
  value       = var.enable ? aws_glue_catalog_database.db[0].name : null
  description = "Glue database name"
}

output "lake_formation_enabled" {
  value       = var.enable
  description = "Whether Lake Formation is enabled for this environment"
}

output "lf_only_mode" {
  value       = var.lf_only_defaults
  description = "Whether Lake Formation only mode is enabled"
}
