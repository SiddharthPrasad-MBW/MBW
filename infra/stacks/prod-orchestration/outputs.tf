output "step_functions_state_machine_arn" {
  description = "ARN of the Step Functions state machine"
  value       = module.orchestration.step_functions_state_machine_arn
}

output "step_functions_state_machine_name" {
  description = "Name of the Step Functions state machine"
  value       = module.orchestration.step_functions_state_machine_name
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for notifications"
  value       = module.orchestration.sns_topic_arn
}

output "manual_execution_command" {
  description = "AWS CLI command to manually trigger the state machine"
  value       = "aws stepfunctions start-execution --state-machine-arn ${module.orchestration.step_functions_state_machine_arn} --input '{\"Environment\":\"prod\",\"Job1Name\":\"etl-omc-flywheel-prod-addressable-split-and-part\",\"Job2Name\":\"etl-omc-flywheel-prod-infobase-split-and-part\",\"Job3Name\":\"etl-omc-flywheel-prod-register-part-tables\",\"Job4Name\":\"etl-omc-flywheel-prod-prepare-part-tables\",\"Job5Name\":\"etl-omc-flywheel-prod-create-part-addressable-ids-er-table\",\"Job6Name\":\"etl-omc-flywheel-prod-generate-data-monitor-report\",\"Job7Name\":\"etl-omc-flywheel-prod-generate-cleanrooms-report\",\"Job1Arguments\":{\"--SNAPSHOT_DT\":\"_NONE_\"},\"Job2Arguments\":{\"--SNAPSHOT_DT\":\"_NONE_\"},\"Job3AArguments\":{\"--DATABASE\":\"omc_flywheel_prod\",\"--S3_ROOT\":\"s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_part/addressable_ids/\",\"--TABLE_PREFIX\":\"part_\",\"--MAX_COLS\":\"100\"},\"Job3BArguments\":{\"--DATABASE\":\"omc_flywheel_prod\",\"--S3_ROOT\":\"s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_part/infobase_attributes/\",\"--TABLE_PREFIX\":\"part_\",\"--MAX_COLS\":\"100\"},\"SNSTopicArn\":\"${module.orchestration.sns_topic_arn}\"}'"
}

