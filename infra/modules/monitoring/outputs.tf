output "data_monitor_job_name" {
  description = "Name of the data monitoring Glue job"
  value       = aws_glue_job.data_monitor.name
}

output "data_monitor_job_arn" {
  description = "ARN of the data monitoring Glue job"
  value       = aws_glue_job.data_monitor.arn
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for monitoring alerts"
  value       = aws_sns_topic.data_monitor_alerts.arn
}

output "cloudwatch_dashboard_url" {
  description = "URL to the CloudWatch dashboard"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.data_monitor.dashboard_name}"
}

output "monitoring_role_arn" {
  description = "ARN of the IAM role for the monitoring job"
  value       = aws_iam_role.data_monitor_role.arn
}

output "log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.data_monitor.name
}

output "report_s3_location" {
  description = "S3 location where monitoring reports are stored"
  value       = "s3://${var.analysis_bucket_name}/data-monitor/"
}
