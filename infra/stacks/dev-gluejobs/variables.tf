variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "glue_database_name" {
  description = "Existing Glue catalog database name"
  type        = string
  default     = "omc_flywheel_dev_clean"  # Updated to use clean database with proper Lake Formation permissions
}

variable "data_bucket_name" {
  description = "Existing data S3 bucket name"
  type        = string
  default     = "omc-flywheel-data-us-east-1-dev"
}

variable "analysis_bucket_name" {
  description = "Existing analysis S3 bucket name"
  type        = string
  default     = "omc-flywheel-dev-analysis-data"
}

variable "glue_role_name" {
  description = "Existing Glue IAM role name"
  type        = string
  default     = "omc_flywheel-dev-glue-role"
}

variable "cleanrooms_membership_id" {
  description = "Cleanrooms membership ID for reporting jobs (optional for dev)"
  type        = string
  default     = null
}

