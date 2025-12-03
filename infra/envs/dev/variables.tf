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

variable "analysis_bucket_name" {
  description = "Name of the analysis S3 bucket"
  type        = string
  default     = "omc-flywheel-dev-analysis-data"
}
