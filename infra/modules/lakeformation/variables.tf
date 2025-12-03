variable "region" {
  description = "AWS region"
  type        = string
}

variable "account_id" {
  description = "AWS account ID"
  type        = string
}

variable "env" {
  description = "Environment name (dev or prod)"
  type        = string
  validation {
    condition     = contains(["dev", "prod"], var.env)
    error_message = "Environment must be either 'dev' or 'prod'."
  }
}

# The Glue database where CTAS tables live (e.g., omc_flywheel_dev / _prod)
variable "database_name" {
  description = "Glue database name for CTAS tables"
  type        = string
}

# S3 bucket and prefix to govern (target layer only)
variable "target_bucket" {
  description = "S3 bucket name for target data (e.g., omc-flywheel-data-us-east-1-dev)"
  type        = string
}

variable "target_prefix" {
  description = "S3 prefix for target data (e.g., omc_cleanroom_data/cleanroom_tables/bucketed/)"
  type        = string
}

# Source data paths (for ext_ tables that CTAS reads from)
variable "source_bucket" {
  description = "S3 bucket name for source data (where ext_ tables point to)"
  type        = string
}

variable "source_prefix" {
  description = "S3 prefix for source data (where ext_ tables point to)"
  type        = string
}

# Optional: register additional source prefix for raw input data
variable "register_raw_source" {
  description = "Whether to register raw source prefix (opus/ data)"
  type        = bool
  default     = false
}

variable "raw_source_bucket" {
  description = "S3 bucket name for raw source data (opus/ paths)"
  type        = string
  default     = ""
}

variable "raw_source_prefix" {
  description = "S3 prefix for raw source data (opus/ paths)"
  type        = string
  default     = ""
}

# Writer principals (Glue job roles - can CREATE_TABLE/ALTER/DROP and write to bucketed/)
variable "writer_principals" {
  description = "List of IAM principal ARNs with write permissions (Glue job roles)"
  type        = list(string)
}

# Reader principals (Cleanroom consumers - SELECT/DESCRIBE only, no CTAS, no writes)
variable "reader_principals" {
  description = "List of IAM principal ARNs with read-only permissions (Cleanroom users, Athena, BI)"
  type        = list(string)
  default     = []
}

# Mode toggles
# Keep IAM-only defaults by default (Hybrid). Switch to true later for LF-only defaults.
variable "lf_only_defaults" {
  description = "Whether to use Lake Formation only defaults (vs IAM-only hybrid)"
  type        = bool
  default     = false
}

# Whether to actually register/grant (helps dry-run in PROD)
variable "enable" {
  description = "Whether to enable Lake Formation registration and grants"
  type        = bool
  default     = true
}
