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
  description = "Name of the Glue database to monitor"
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

variable "monitoring_schedule" {
  description = "CloudWatch Events schedule for automatic monitoring runs"
  type        = string
  default     = "rate(24 hours)"
}

variable "alert_email" {
  description = "Email address for monitoring alerts (optional)"
  type        = string
  default     = ""
}

variable "retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "worker_count" {
  description = "Number of workers for the monitoring job"
  type        = number
  default     = 2
}

variable "timeout_minutes" {
  description = "Job timeout in minutes"
  type        = number
  default     = 5
}

variable "enable_file_size_check" {
  description = "Enable file size hygiene checks"
  type        = bool
  default     = false
}

variable "count_tolerance_percent" {
  description = "Tolerance percentage for record count validation (0 = exact match)"
  type        = number
  default     = 0
}

variable "freshness_window_days" {
  description = "Data freshness window in days"
  type        = number
  default     = 45
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

variable "pk_column" {
  description = "Primary key column name for data quality checks (e.g., customer_user_id)"
  type        = string
  default     = "customer_user_id"
}

variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
