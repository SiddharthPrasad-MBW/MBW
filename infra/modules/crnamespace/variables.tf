variable "membership_id" {
  description = "Clean Rooms membership ID to associate ID namespace with"
  type        = string
}

variable "id_namespace_name" {
  description = "Name of the ID namespace association (e.g., ACXIdNamespace)"
  type        = string
}

variable "id_namespace_arn" {
  description = "ARN of the Entity Resolution ID namespace"
  type        = string
}

variable "id_namespace_description" {
  description = "Description for the ID namespace association"
  type        = string
  default     = ""
}

variable "manage_resource_policies" {
  description = "Whether Clean Rooms should manage resource policies for the ID namespace"
  type        = bool
  default     = true
}

variable "allow_use_as_dimension_column" {
  description = "Whether the ID namespace can be used as a dimension column"
  type        = bool
  default     = false
}

variable "id_mapping_table_name" {
  description = "Name of the ID mapping table (e.g., acx-real_ids)"
  type        = string
  default     = null
}

variable "id_mapping_table_description" {
  description = "Description for the ID mapping table"
  type        = string
  default     = ""
}

variable "id_mapping_workflow_arn" {
  description = "ARN of the Entity Resolution ID mapping workflow"
  type        = string
  default     = null
}

variable "id_mapping_table_input_sources" {
  description = "List of input sources for the ID mapping table. Each source should have idNamespaceAssociationId and type (SOURCE/TARGET)"
  type = list(object({
    id_namespace_association_id = string
    type                       = string
  }))
  default = []
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}

