output "step_functions_state_machine_arn" {
  description = "ARN of the Step Functions state machine"
  value       = aws_sfn_state_machine.db_refresh.arn
}

output "step_functions_state_machine_name" {
  description = "Name of the Step Functions state machine"
  value       = aws_sfn_state_machine.db_refresh.name
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for notifications"
  value       = aws_sns_topic.orchestration_notifications.arn
}

output "sns_topic_name" {
  description = "Name of the SNS topic"
  value       = aws_sns_topic.orchestration_notifications.name
}

output "eventbridge_rule_arn" {
  description = "ARN of the EventBridge rule (if scheduled execution is enabled)"
  value       = var.enable_scheduled_execution ? aws_cloudwatch_event_rule.monthly_schedule[0].arn : null
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.step_functions.arn
}

