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

# Lake Formation Module Outputs
output "lake_formation" {
  description = "Lake Formation infrastructure information"
  value = {
    target_path_arn = module.lake_formation.registered_target_arn
    source_path_arn = module.lake_formation.registered_source_arn
    raw_source_path_arn = module.lake_formation.registered_raw_source_arn
    database_name = module.lake_formation.database_name
    enabled = module.lake_formation.lake_formation_enabled
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
