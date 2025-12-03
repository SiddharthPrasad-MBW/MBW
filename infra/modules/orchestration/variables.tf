variable "environment" {
  description = "Environment name (dev, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "Environment must be 'dev' or 'prod'"
  }
}

variable "job_names" {
  description = "Map of Glue job names for the 7-step process"
  type = object({
    job1 = string # addressable-split-and-part
    job2 = string # infobase-split-and-part
    job3 = string # register-part-tables
    job4 = string # prepare-part-tables
    job5 = string # create-part-addressable-ids-er-table
    job6 = string # generate-data-monitor-report
    job7 = string # generate-cleanrooms-report
  })
}

variable "job_arguments" {
  description = "Map of job arguments for each job"
  type = object({
    job1 = map(string) # addressable-split-and-part arguments
    job2 = map(string) # infobase-split-and-part arguments
    job3a = map(string) # register-part-tables (addressable_ids context)
    job3b = map(string) # register-part-tables (infobase_attributes context)
  })
  default = {
    job1 = {
      "--SNAPSHOT_DT" = "_NONE_"
    }
    job2 = {
      "--SNAPSHOT_DT" = "_NONE_"
    }
    job3a = {
      "--DATABASE"     = ""
      "--S3_ROOT"      = ""
      "--TABLE_PREFIX" = "part_"
      "--MAX_COLS"     = "100"
    }
    job3b = {
      "--DATABASE"     = ""
      "--S3_ROOT"      = ""
      "--TABLE_PREFIX" = "part_"
      "--MAX_COLS"     = "100"
    }
  }
}

variable "enable_scheduled_execution" {
  description = "Enable EventBridge scheduled execution"
  type        = bool
  default     = true
}

variable "schedule_expression" {
  description = "EventBridge schedule expression (e.g., 'cron(0 2 1 * ? *)' for 2 AM on 1st of month)"
  type        = string
  default     = "cron(0 2 1 * ? *)" # 2 AM UTC on 1st of every month
}

variable "notification_emails" {
  description = "List of email addresses to receive SNS notifications"
  type        = list(string)
  default     = []
}

variable "sns_kms_key_id" {
  description = "KMS key ID for SNS topic encryption (optional)"
  type        = string
  default     = null
}

variable "cloudwatch_kms_key_id" {
  description = "KMS key ID for CloudWatch logs encryption (optional)"
  type        = string
  default     = null
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}

