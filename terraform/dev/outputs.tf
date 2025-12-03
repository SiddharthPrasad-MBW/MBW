# DEV Environment Outputs

output "glue_jobs" {
  description = "Glue job names"
  value = {
    infobase_split_and_bucket     = aws_glue_job.infobase_split_and_bucket.name
    addressable_bucket           = aws_glue_job.addressable_bucket.name
    register_staged_tables       = aws_glue_job.register_staged_tables.name
    create_athena_bucketed_tables = aws_glue_job.create_athena_bucketed_tables.name
  }
}

output "glue_crawlers" {
  description = "Glue crawler names"
  value = {
    infobase_attributes_bucketed = aws_glue_crawler.infobase_attributes_bucketed.name
    addressable_ids_bucketed     = aws_glue_crawler.addressable_ids_bucketed.name
  }
}

output "iam_role" {
  description = "Glue execution role"
  value = {
    name = aws_iam_role.glue_role.name
    arn  = aws_iam_role.glue_role.arn
  }
}

output "s3_buckets" {
  description = "S3 bucket names"
  value = {
    data_bucket     = aws_s3_bucket.data_bucket.bucket
    analysis_bucket  = aws_s3_bucket.analysis_bucket.bucket
  }
}

output "glue_databases" {
  description = "Glue catalog databases"
  value = {
    final_database = aws_glue_catalog_database.final_database.name
  }
}

output "environment_info" {
  description = "Environment information"
  value = {
    environment = var.environment
    region      = var.aws_region
    profile     = var.aws_profile
  }
}
