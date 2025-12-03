variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "glue_database_name" {
  description = "Name of the Glue catalog database"
  type        = string
  default     = "omc_flywheel_dev"
}

variable "data_bucket_name" {
  description = "Name of the main data S3 bucket"
  type        = string
  default     = "omc-flywheel-data-us-east-1-dev"
}

variable "cleanrooms_membership_id" {
  description = "Clean Rooms membership ID to associate tables with. Leave null to defer association."
  type        = string
  default     = null
}

variable "cleanrooms_allowed_query_providers" {
  description = "AWS account IDs allowed to submit custom queries. Default includes AMC Service (921290734397) and Query Submitter/AMC Results Receiver (657425294073)."
  type        = list(string)
  default     = ["921290734397", "657425294073"]
}

