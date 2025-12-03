variable "membership_id" {
  description = "Clean Rooms membership ID to associate resources with"
  type        = string
}

variable "existing_configured_tables" {
  description = "Map of existing configured tables: table_id -> {name: table_name}. Discover using: python3 scripts/discover-configured-tables.py --filter 'part_'"
  type = map(object({
    name = string
  }))
}

variable "id_namespace_arn" {
  description = "ARN of the Entity Resolution ID namespace"
  type        = string
  default     = "arn:aws:entityresolution:us-east-1:239083076653:idnamespace/ACXIdNamespace"
}

variable "id_namespace_name" {
  description = "Name of the ID namespace association"
  type        = string
  default     = "ACXIdNamespace"
}

variable "role_name" {
  description = "Name of the IAM role for Clean Rooms to access Glue/S3"
  type        = string
  default     = "cleanrooms-glue-s3-access"
}

variable "aws_profile" {
  description = "AWS profile to use for API calls"
  type        = string
  default     = "flywheel-prod"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

