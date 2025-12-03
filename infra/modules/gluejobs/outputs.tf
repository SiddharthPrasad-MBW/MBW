# Glue Database
output "glue_database_name" {
  description = "Name of the Glue catalog database"
  value       = var.glue_database_name
}

output "glue_database_arn" {
  description = "ARN of the Glue catalog database (if created)"
  value       = var.create_glue_database ? aws_glue_catalog_database.main[0].arn : null
}

# IAM Role
output "glue_role_arn" {
  description = "ARN of the Glue IAM role"
  value       = aws_iam_role.glue_role.arn
}

output "glue_role_name" {
  description = "Name of the Glue IAM role"
  value       = aws_iam_role.glue_role.name
}

# S3 Buckets
output "data_bucket_name" {
  description = "Name of the main data S3 bucket"
  value       = var.data_bucket_name
}

output "data_bucket_arn" {
  description = "ARN of the main data S3 bucket (if created)"
  value       = var.create_s3_buckets ? aws_s3_bucket.data_bucket[0].arn : null
}

output "analysis_bucket_name" {
  description = "Name of the analysis S3 bucket"
  value       = var.analysis_bucket_name
}

output "analysis_bucket_arn" {
  description = "ARN of the analysis S3 bucket (if created)"
  value       = var.create_s3_buckets ? aws_s3_bucket.analysis_bucket[0].arn : null
}

# Glue Jobs - Bucketed Pipeline
output "bucketed_pipeline_jobs" {
  description = "Glue jobs for the bucketed data pipeline"
  value = {
    infobase_split_and_bucket = aws_glue_job.infobase_split_and_bucket.name
    addressable_bucket        = aws_glue_job.addressable_bucket.name
    register_staged_tables    = aws_glue_job.register_staged_tables.name
    create_athena_bucketed    = aws_glue_job.create_athena_bucketed_tables.name
  }
}

# Glue Jobs - Partitioned Pipeline
output "partitioned_pipeline_jobs" {
  description = "Glue jobs for the partitioned data pipeline"
  value = {
    infobase_split_and_part   = aws_glue_job.infobase_split_and_part.name
    addressable_split_and_part = aws_glue_job.addressable_split_and_part.name
    register_part_tables      = aws_glue_job.register_part_tables.name
    prepare_part_tables       = aws_glue_job.prepare_part_tables.name
  }
}

# All Glue Jobs
output "all_glue_jobs" {
  description = "All Glue job names"
  value = merge(
    var.enable_bucketed_pipeline ? { infobase_split_and_bucket = aws_glue_job.infobase_split_and_bucket.name } : {},
    var.enable_bucketed_pipeline ? { addressable_bucket = aws_glue_job.addressable_bucket.name } : {},
    var.enable_bucketed_pipeline ? { register_staged_tables = aws_glue_job.register_staged_tables.name } : {},
    var.enable_bucketed_pipeline ? { create_athena_bucketed = aws_glue_job.create_athena_bucketed_tables.name } : {},
    var.enable_partitioned_pipeline ? { infobase_split_and_part = aws_glue_job.infobase_split_and_part.name } : {},
    var.enable_partitioned_pipeline ? { addressable_split_and_part = aws_glue_job.addressable_split_and_part.name } : {},
    var.enable_partitioned_pipeline ? { register_part_tables = aws_glue_job.register_part_tables.name } : {},
    var.enable_partitioned_pipeline ? { prepare_part_tables = aws_glue_job.prepare_part_tables.name } : {},
    { create_part_addressable_ids_er_table = aws_glue_job.create_part_addressable_ids_er_table.name },
    { generate_cleanrooms_report = aws_glue_job.generate_cleanrooms_report.name }
  )
}

# Glue Crawlers
output "glue_crawlers" {
  description = "Glue crawler names"
  value = var.enable_crawlers ? {
    infobase_attributes = aws_glue_crawler.infobase_attributes_bucketed.name
    addressable_ids     = aws_glue_crawler.addressable_ids_bucketed.name
  } : {}
}

# S3 Paths
output "s3_paths" {
  description = "Key S3 paths for the solution"
  value = {
    # Source data paths
    source_infobase     = "s3://${var.data_bucket_name}/opus/infobase_attributes/raw_input/"
    source_addressable  = "s3://${var.data_bucket_name}/opus/addressable_ids/raw_input/"
    
    # Bucketed pipeline paths
    bucketed_infobase   = "s3://${var.data_bucket_name}/omc_cleanroom_data/split_cluster/infobase_attributes/"
    bucketed_addressable = "s3://${var.data_bucket_name}/omc_cleanroom_data/split_cluster/addressable_ids/"
    bucketed_tables     = "s3://${var.data_bucket_name}/omc_cleanroom_data/cleanroom_tables/bucketed/"
    
    # Partitioned pipeline paths
    partitioned_infobase   = "s3://${var.data_bucket_name}/omc_cleanroom_data/split_part/infobase_attributes/"
    partitioned_addressable = "s3://${var.data_bucket_name}/omc_cleanroom_data/split_part/addressable_ids/"
    
    # Analysis paths
    athena_results = "s3://${var.analysis_bucket_name}/query-results/"
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
