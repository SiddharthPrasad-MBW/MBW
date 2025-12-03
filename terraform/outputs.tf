# Outputs for OMC Flywheel Cleanroom Production Terraform Configuration

output "glue_database_name" {
  description = "Name of the Glue catalog database"
  value       = aws_glue_catalog_database.main.name
}

output "glue_role_arn" {
  description = "ARN of the Glue IAM role"
  value       = aws_iam_role.glue_role.arn
}

output "data_bucket_name" {
  description = "Name of the main data S3 bucket"
  value       = aws_s3_bucket.data_bucket.bucket
}

output "analysis_bucket_name" {
  description = "Name of the analysis S3 bucket"
  value       = aws_s3_bucket.analysis_bucket.bucket
}

output "glue_jobs" {
  description = "List of Glue job names"
  value = {
    infobase_split_and_bucket = aws_glue_job.infobase_split_and_bucket.name
    addressable_bucket        = aws_glue_job.addressable_bucket.name
    register_staged_tables    = aws_glue_job.register_staged_tables.name
    create_athena_bucketed    = aws_glue_job.create_athena_bucketed_tables.name
    infobase_split_and_part   = aws_glue_job.infobase_split_and_part.name
    addressable_split_and_part = aws_glue_job.addressable_split_and_part.name
    register_part_tables      = aws_glue_job.register_part_tables.name
    prepare_part_tables       = aws_glue_job.prepare_part_tables.name
  }
}

output "glue_crawlers" {
  description = "List of Glue crawler names"
  value = {
    infobase_attributes = aws_glue_crawler.infobase_attributes_bucketed.name
    addressable_ids     = aws_glue_crawler.addressable_ids_bucketed.name
  }
}

output "s3_paths" {
  description = "Key S3 paths for the solution"
  value = {
    source_infobase     = "s3://${aws_s3_bucket.data_bucket.bucket}/opus/infobase_attributes/raw_input/"
    source_addressable  = "s3://${aws_s3_bucket.data_bucket.bucket}/opus/addressable_ids/raw_input/"
    target_infobase     = "s3://${aws_s3_bucket.data_bucket.bucket}/omc_cleanroom_data/split_cluster/infobase_attributes/"
    target_addressable  = "s3://${aws_s3_bucket.data_bucket.bucket}/omc_cleanroom_data/split_cluster/addressable_ids/"
    bucketed_infobase   = "s3://${aws_s3_bucket.data_bucket.bucket}/omc_cleanroom_data/cleanroom_tables/bucketed/infobase_attributes/"
    bucketed_addressable = "s3://${aws_s3_bucket.data_bucket.bucket}/omc_cleanroom_data/cleanroom_tables/bucketed/addressable_ids/"
    athena_results      = "s3://${aws_s3_bucket.analysis_bucket.bucket}/query-results/"
  }
}

output "account_info" {
  description = "AWS account and region information"
  value = {
    account_id = data.aws_caller_identity.current.account_id
    region     = data.aws_region.current.name
  }
}
