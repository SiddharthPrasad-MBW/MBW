# DEV Environment Variables

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS profile for DEV environment"
  type        = string
  default     = "flywheel-dev"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

# =============================================================================
# GLUE CONFIGURATION
# =============================================================================

variable "glue_role_name" {
  description = "Name of the Glue execution role"
  type        = string
  default     = "omc_flywheel-dev-glue-role"
}

variable "glue_assets_bucket" {
  description = "S3 bucket for Glue assets (scripts, temp files)"
  type        = string
  default     = "aws-glue-assets-417649522250-us-east-1"
}

# =============================================================================
# S3 BUCKETS
# =============================================================================

variable "data_bucket" {
  description = "S3 bucket for data storage"
  type        = string
  default     = "omc-flywheel-data-us-east-1-dev"
}

variable "analysis_bucket" {
  description = "S3 bucket for analysis results"
  type        = string
  default     = "omc-flywheel-dev-analysis-data"
}

# =============================================================================
# DATABASES
# =============================================================================

variable "staged_database" {
  description = "Glue catalog database for staged tables"
  type        = string
  default     = "omc_flywheel_dev_staged"
}

variable "final_database" {
  description = "Glue catalog database for final bucketed tables"
  type        = string
  default     = "omc_flywheel_dev"
}

# =============================================================================
# ATHENA CONFIGURATION
# =============================================================================

variable "athena_workgroup" {
  description = "Athena workgroup for query execution"
  type        = string
  default     = "omc-flywheel-dev-workgroup"
}

# =============================================================================
# TAGS
# =============================================================================

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "omc-flywheel"
    Environment = "dev"
    Purpose     = "cleanroom-bucketing"
    ManagedBy   = "terraform"
  }
}
