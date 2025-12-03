variable "enable_scheduled_execution" {
  description = "Enable EventBridge scheduled execution"
  type        = bool
  default     = true # Enabled by default in prod
}

variable "schedule_expression" {
  description = "EventBridge schedule expression"
  type        = string
  default     = "cron(0 2 1 * ? *)" # 2 AM UTC on 1st of every month
}

variable "notification_emails" {
  description = "List of email addresses to receive SNS notifications"
  type        = list(string)
  default     = []
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 90 # Longer retention in prod
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}

