variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, prod, etc.)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "omc-flywheel"
}

variable "glue_database_name" {
  description = "Name of the Glue catalog database"
  type        = string
}

variable "data_bucket_name" {
  description = "Name of the main data S3 bucket"
  type        = string
}

variable "analysis_bucket_name" {
  description = "Name of the analysis S3 bucket"
  type        = string
}

variable "glue_role_name" {
  description = "Name of the Glue IAM role"
  type        = string
}

variable "create_s3_buckets" {
  description = "Whether to create S3 buckets (set to false if buckets already exist)"
  type        = bool
  default     = true
}

variable "create_glue_database" {
  description = "Whether to create Glue database (set to false if database already exists)"
  type        = bool
  default     = true
}

variable "create_iam_role" {
  description = "Whether to create IAM role (set to false if role already exists)"
  type        = bool
  default     = true
}

variable "worker_count" {
  description = "Default number of workers for Glue jobs"
  type        = number
  default     = 10
}

variable "timeout_minutes" {
  description = "Default timeout in minutes for Glue jobs"
  type        = number
  default     = 60
}

variable "max_retries" {
  description = "Maximum number of retries for Glue jobs"
  type        = number
  default     = 0
}

variable "enable_bucketed_pipeline" {
  description = "Enable the bucketed data pipeline"
  type        = bool
  default     = true
}

variable "enable_partitioned_pipeline" {
  description = "Enable the partitioned data pipeline"
  type        = bool
  default     = true
}

variable "enable_crawlers" {
  description = "Enable Glue crawlers for data discovery"
  type        = bool
  default     = true
}

variable "bucket_count" {
  description = "Number of buckets for data partitioning"
  type        = number
  default     = 256
}

variable "cleanrooms_membership_id" {
  description = "Cleanrooms membership ID for reporting jobs"
  type        = string
  default     = "6610c9aa-9002-475c-8695-d833485741bc"
}

variable "athena_workgroup" {
  description = "Athena workgroup for queries"
  type        = string
  default     = "primary"
}

variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
