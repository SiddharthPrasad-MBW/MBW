variable "membership_id" {
  description = "Clean Rooms membership ID to associate tables with. If null, associations are skipped."
  type        = string
  default     = null
}

variable "create_role" {
  description = "Create an IAM role for Clean Rooms to access Glue/S3. Set false to provide role_arn."
  type        = bool
  default     = true
}

variable "role_arn" {
  description = "Existing IAM role ARN for Clean Rooms to access Glue/S3 (used when create_role=false)."
  type        = string
  default     = null
}

variable "s3_resources" {
  description = "S3 ARNs (bucket and prefixes) Clean Rooms needs to read when create_role=true."
  type        = list(string)
  default     = []
}

variable "use_all_columns" {
  description = "If true, pull all column names from Glue; ignore per-table allowed_columns."
  type        = bool
  default     = true
}

variable "allowed_query_providers" {
  description = "AWS account IDs allowed to submit custom queries (CUSTOM rule). Default includes AMC Service (921290734397) and Query Submitter/AMC Results Receiver (657425294073)."
  type        = list(string)
  default     = ["921290734397", "657425294073"]
}

variable "tags" {
  description = "Common tags for all resources."
  type        = map(string)
  default     = {}
}

variable "tables" {
  description = "Map of configured tables. Keys become configured-table names."
  type = map(object({
    description     = string
    analysis_method = string
    allowed_columns = optional(list(string))
    glue = object({
      region   = string
      database = string
      table    = string
    })
    rule = object({
      type              = string
      allowed_functions = optional(list(string))
      dimension_columns = optional(list(string))
      join_columns      = optional(list(string))
    })
  }))
}

