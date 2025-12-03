# NOTE: Outputs are commented out because Terraform resources are not yet supported
# Use the discovery script to get these values: scripts/discover-cr-namespace-resources.py

# output "id_namespace_association_id" {
#   value       = aws_cleanrooms_id_namespace_association.namespace.id
#   description = "ID of the ID namespace association"
# }

# output "id_namespace_association_arn" {
#   value       = aws_cleanrooms_id_namespace_association.namespace.arn
#   description = "ARN of the ID namespace association"
# }

# output "id_namespace_association_name" {
#   value       = aws_cleanrooms_id_namespace_association.namespace.name
#   description = "Name of the ID namespace association"
# }

# output "id_mapping_table_id" {
#   value       = var.id_mapping_table_name != null ? aws_cleanrooms_id_mapping_table.mapping_table[0].id : null
#   description = "ID of the ID mapping table (if created)"
# }

# output "id_mapping_table_arn" {
#   value       = var.id_mapping_table_name != null ? aws_cleanrooms_id_mapping_table.mapping_table[0].arn : null
#   description = "ARN of the ID mapping table (if created)"
# }

# output "id_mapping_table_name" {
#   value       = var.id_mapping_table_name
#   description = "Name of the ID mapping table (if created)"
# }

# Placeholder outputs for documentation
output "id_namespace_association_id" {
  value       = "Use scripts/discover-cr-namespace-resources.py to get actual ID"
  description = "ID of the ID namespace association (use discovery script)"
}

output "id_mapping_table_id" {
  value       = var.id_mapping_table_name != null ? "Use scripts/discover-cr-namespace-resources.py to get actual ID" : null
  description = "ID of the ID mapping table (use discovery script)"
}

