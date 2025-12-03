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

variable "glue_role_name" {
  description = "Existing Glue IAM role name"
  type        = string
  default     = "omc_flywheel-prod-glue-role"
}

variable "cleanrooms_membership_id" {
  description = "Cleanrooms membership ID for reporting jobs"
  type        = string
  default     = "6610c9aa-9002-475c-8695-d833485741bc"
}


