variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "glue_database_name" {
  description = "Existing Glue catalog database name"
  type        = string
  default     = "omc_flywheel_prod"
}

variable "data_bucket_name" {
  description = "Existing data S3 bucket name"
  type        = string
  default     = "omc-flywheel-data-us-east-1-prod"
}

variable "analysis_bucket_name" {
  description = "Existing analysis S3 bucket name"
  type        = string
  default     = "omc-flywheel-prod-analysis-data"
}

