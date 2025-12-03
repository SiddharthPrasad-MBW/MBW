# DEV Environment Configuration

# AWS Configuration
aws_region  = "us-east-1"
aws_profile = "flywheel-dev"
environment = "dev"

# Glue Configuration
glue_role_name      = "omc_flywheel-dev-glue-role"
glue_assets_bucket  = "aws-glue-assets-417649522250-us-east-1"

# S3 Buckets
data_bucket     = "omc-flywheel-data-us-east-1-dev"
analysis_bucket = "omc-flywheel-dev-analysis-data"

# Databases
staged_database = "omc_flywheel_dev_staged"
final_database  = "omc_flywheel_dev"

# Athena Configuration
athena_workgroup = "omc-flywheel-dev-workgroup"

# Common Tags
common_tags = {
  Project     = "omc-flywheel"
  Environment = "dev"
  Purpose     = "cleanroom-bucketing"
  ManagedBy   = "terraform"
}
