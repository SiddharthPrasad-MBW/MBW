# Variables for OMC Flywheel Cleanroom Production Terraform Configuration

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS profile to use for authentication"
  type        = string
  default     = "flywheel-prod"
}

variable "glue_database_name" {
  description = "Name of the Glue catalog database"
  type        = string
  default     = "omc_flywheel_prod"
}

variable "glue_role_name" {
  description = "Name of the IAM role for Glue jobs"
  type        = string
  default     = "omc_flywheel-prod-glue-role"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "omc-flywheel-cleanroom"
}

# S3 Bucket Configuration
variable "data_bucket_name" {
  description = "Name of the main data S3 bucket"
  type        = string
  default     = "omc-flywheel-data-us-east-1-prod"
}

variable "analysis_bucket_name" {
  description = "Name of the analysis S3 bucket for Athena results"
  type        = string
  default     = "omc-flywheel-prod-analysis-data"
}

# Glue Job Configuration
variable "infobase_worker_type" {
  description = "Worker type for infobase split and bucket job"
  type        = string
  default     = "G.4X"
}

variable "infobase_worker_count" {
  description = "Number of workers for infobase split and bucket job"
  type        = number
  default     = 24
}

variable "addressable_worker_type" {
  description = "Worker type for addressable bucket job"
  type        = string
  default     = "G.4X"
}

variable "addressable_worker_count" {
  description = "Number of workers for addressable bucket job"
  type        = number
  default     = 24
}

variable "register_worker_type" {
  description = "Worker type for register staged tables job"
  type        = string
  default     = "G.1X"
}

variable "register_worker_count" {
  description = "Number of workers for register staged tables job"
  type        = number
  default     = 2
}

variable "athena_worker_type" {
  description = "Worker type for create Athena bucketed tables job"
  type        = string
  default     = "G.4X"
}

variable "athena_worker_count" {
  description = "Number of workers for create Athena bucketed tables job"
  type        = number
  default     = 10
}

# Performance Configuration
variable "bucket_count" {
  description = "Number of buckets for bucketing"
  type        = number
  default     = 256
}

variable "target_file_mb" {
  description = "Target file size in MB"
  type        = number
  default     = 512
}

variable "job_timeout_minutes" {
  description = "Job timeout in minutes"
  type        = number
  default     = 2880
}

# Tags
variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "OMC Flywheel Cleanroom"
    Environment = "Production"
    ManagedBy   = "Terraform"
    Owner       = "Data Engineering"
  }
}
