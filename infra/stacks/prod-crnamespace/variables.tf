variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "cleanrooms_membership_id" {
  description = "Clean Rooms membership ID"
  type        = string
  default     = "6610c9aa-9002-475c-8695-d833485741bc"
}

variable "id_namespace_name" {
  description = "Name of the ID namespace association"
  type        = string
  default     = "ACXIdNamespace"
}

variable "id_namespace_arn" {
  description = "ARN of the Entity Resolution ID namespace"
  type        = string
  default     = "arn:aws:entityresolution:us-east-1:239083076653:idnamespace/ACXIdNamespace"
}

variable "id_mapping_table_name" {
  description = "Name of the ID mapping table"
  type        = string
  default     = "acx-real_ids"
}

variable "id_mapping_workflow_arn" {
  description = "ARN of the Entity Resolution ID mapping workflow"
  type        = string
  default     = "arn:aws:entityresolution:us-east-1:239083076653:idmappingworkflow/ACX-Real_IDS"
}

variable "target_id_namespace_association_id" {
  description = "ID of the target ID namespace association (e.g., AMCIdNamespace)"
  type        = string
  default     = "3ff4df8f-f33c-4e04-8a34-0f8974cb627d"  # AMCIdNamespace (unchanged)
}

variable "id_namespace_description" {
  description = "Description for the ID namespace association"
  type        = string
  default     = "ACX unique customer identifiers for Clean Rooms joins"
}

