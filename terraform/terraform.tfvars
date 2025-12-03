# Production Environment Configuration
# OMC Flywheel Cleanroom Terraform Variables

# AWS Configuration
aws_region  = "us-east-1"
aws_profile = "flywheel-prod"

# Project Configuration
environment = "prod"
project_name = "omc-flywheel-cleanroom"

# Glue Configuration
glue_database_name = "omc_flywheel_prod"
glue_role_name     = "omc_flywheel-prod-glue-role"

# S3 Bucket Configuration
data_bucket_name    = "omc-flywheel-data-us-east-1-prod"
analysis_bucket_name = "omc-flywheel-prod-analysis-data"

# Glue Job Worker Configuration
infobase_worker_type   = "G.4X"
infobase_worker_count  = 24

addressable_worker_type  = "G.4X"
addressable_worker_count = 24

register_worker_type  = "G.1X"
register_worker_count = 2

athena_worker_type  = "G.4X"
athena_worker_count = 10

# Performance Configuration
bucket_count         = 256
target_file_mb       = 512
job_timeout_minutes  = 2880

# Common Tags
common_tags = {
  Project     = "OMC Flywheel Cleanroom"
  Environment = "Production"
  ManagedBy   = "Terraform"
  Owner       = "Data Engineering"
  CostCenter  = "Data Engineering"
  Application = "Cleanroom Bucketing"
}
