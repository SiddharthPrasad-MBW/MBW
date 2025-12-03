#!/bin/bash
# Import existing production resources into Terraform state
# This script imports the existing OMC Flywheel Cleanroom production resources

set -e

echo "🔄 Importing existing production resources into Terraform state..."

# Set AWS profile
export AWS_PROFILE=flywheel-prod

# Import Glue Database
echo "📊 Importing Glue database..."
terraform import aws_glue_catalog_database.main omc_flywheel_prod

# Import IAM Role
echo "🔐 Importing IAM role..."
terraform import aws_iam_role.glue_role omc_flywheel-prod-glue-role

# Import S3 Buckets (if they exist)
echo "🪣 Importing S3 buckets..."
terraform import aws_s3_bucket.data_bucket omc-flywheel-data-us-east-1-prod || echo "⚠️  Data bucket may not exist or already managed"
terraform import aws_s3_bucket.analysis_bucket omc-flywheel-prod-analysis-data || echo "⚠️  Analysis bucket may not exist or already managed"

# Import Glue Jobs
echo "⚙️  Importing Glue jobs..."
terraform import aws_glue_job.infobase_split_and_bucket etl-omc-flywheel-prod-infobase-split-and-bucket
terraform import aws_glue_job.addressable_bucket etl-omc-flywheel-prod-addressable-bucket
terraform import aws_glue_job.register_staged_tables etl-omc-flywheel-prod-register-staged-tables
terraform import aws_glue_job.create_athena_bucketed_tables etl-omc-flywheel-prod-create-athena-bucketed-tables

# Import Glue Crawlers
echo "🕷️  Importing Glue crawlers..."
terraform import aws_glue_crawler.infobase_attributes_bucketed crw-omc-flywheel-prod-infobase-attributes-bucketed-cr
terraform import aws_glue_crawler.addressable_ids_bucketed crw-omc-flywheel-prod-addressable-ids-bucketed-cr

echo "✅ Import completed! Running terraform plan to verify..."
terraform plan

echo "🎉 All existing resources have been imported into Terraform state!"
echo "💡 You can now use 'terraform plan' and 'terraform apply' to manage these resources."
