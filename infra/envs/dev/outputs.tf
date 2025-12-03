# Core Infrastructure
output "glue_database_name" {
  description = "Name of the Glue catalog database"
  value       = aws_glue_catalog_database.main.name
}

output "data_bucket_name" {
  description = "Name of the main data S3 bucket"
  value       = aws_s3_bucket.data_bucket.bucket
}

output "analysis_bucket_name" {
  description = "Name of the analysis S3 bucket"
  value       = aws_s3_bucket.analysis_bucket.bucket
}

# Glue Jobs Module Outputs
output "glue_jobs" {
  description = "Glue jobs information"
  value = {
    bucketed_pipeline    = module.glue_jobs.bucketed_pipeline_jobs
    partitioned_pipeline = module.glue_jobs.partitioned_pipeline_jobs
    all_jobs            = module.glue_jobs.all_glue_jobs
    crawlers            = module.glue_jobs.glue_crawlers
    glue_role_arn       = module.glue_jobs.glue_role_arn
  }
}

# Monitoring Module Outputs
output "monitoring" {
  description = "Monitoring infrastructure information"
  value = {
    job_name           = module.monitoring.data_monitor_job_name
    job_arn           = module.monitoring.data_monitor_job_arn
    sns_topic_arn     = module.monitoring.sns_topic_arn
    dashboard_url     = module.monitoring.cloudwatch_dashboard_url
    monitoring_role   = module.monitoring.monitoring_role_arn
    log_group         = module.monitoring.log_group_name
    report_location   = module.monitoring.report_s3_location
  }
}

# Lake Formation Module Outputs
output "lake_formation" {
  description = "Lake Formation infrastructure information"
  value = {
    target_path_arn = module.lake_formation.target_path_arn
    source_path_arn = module.lake_formation.source_path_arn
    raw_source_path_arn = module.lake_formation.raw_source_path_arn
  }
}

# S3 Paths
output "s3_paths" {
  description = "Key S3 paths for the solution"
  value = {
    # Source data paths
    source_infobase     = "s3://${aws_s3_bucket.data_bucket.bucket}/opus/infobase_attributes/raw_input/"
    source_addressable  = "s3://${aws_s3_bucket.data_bucket.bucket}/opus/addressable_ids/raw_input/"
    
    # Bucketed pipeline paths
    bucketed_infobase   = "s3://${aws_s3_bucket.data_bucket.bucket}/omc_cleanroom_data/split_cluster/infobase_attributes/"
    bucketed_addressable = "s3://${aws_s3_bucket.data_bucket.bucket}/omc_cleanroom_data/split_cluster/addressable_ids/"
    bucketed_tables     = "s3://${aws_s3_bucket.data_bucket.bucket}/omc_cleanroom_data/cleanroom_tables/bucketed/"
    
    # Partitioned pipeline paths
    partitioned_infobase   = "s3://${aws_s3_bucket.data_bucket.bucket}/omc_cleanroom_data/split_part/infobase_attributes/"
    partitioned_addressable = "s3://${aws_s3_bucket.data_bucket.bucket}/omc_cleanroom_data/split_part/addressable_ids/"
    
    # Analysis paths
    athena_results = "s3://${aws_s3_bucket.analysis_bucket.bucket}/query-results/"
    monitoring_reports = "s3://${aws_s3_bucket.analysis_bucket.bucket}/data-monitor/"
  }
}

# Account Information
output "account_info" {
  description = "AWS account and region information"
  value = {
    account_id = data.aws_caller_identity.current.account_id
    region     = data.aws_region.current.name
  }
}
