#!/bin/bash
# Import existing DEV resources into Terraform state

set -e

echo "🔄 Importing existing DEV resources into Terraform state..."

# Set AWS profile
export AWS_PROFILE=flywheel-dev

# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "📋 Account ID: $ACCOUNT_ID"

# =============================================================================
# GLUE JOBS
# =============================================================================

echo "📋 Importing Glue Jobs..."

# Infobase Split and Bucket Job
echo "  - etl-omc-flywheel-dev-infobase-split-and-bucket"
terraform import aws_glue_job.infobase_split_and_bucket etl-omc-flywheel-dev-infobase-split-and-bucket

# Addressable Bucket Job
echo "  - etl-omc-flywheel-dev-addressable-bucket"
terraform import aws_glue_job.addressable_bucket etl-omc-flywheel-dev-addressable-bucket

# Register Staged Tables Job
echo "  - etl-omc-flywheel-dev-register-staged-tables"
terraform import aws_glue_job.register_staged_tables etl-omc-flywheel-dev-register-staged-tables

# Create Athena Bucketed Tables Job
echo "  - etl-omc-flywheel-dev-create-athena-bucketed-tables"
terraform import aws_glue_job.create_athena_bucketed_tables etl-omc-flywheel-dev-create-athena-bucketed-tables

# =============================================================================
# GLUE CRAWLERS
# =============================================================================

echo "📋 Importing Glue Crawlers..."

# Infobase Attributes Bucketed Crawler
echo "  - crw-omc-flywheel-dev-infobase-attributes-bucketed-cr"
terraform import aws_glue_crawler.infobase_attributes_bucketed crw-omc-flywheel-dev-infobase-attributes-bucketed-cr

# Addressable IDs Bucketed Crawler
echo "  - crw-omc-flywheel-dev-addressable-ids-bucketed-cr"
terraform import aws_glue_crawler.addressable_ids_bucketed crw-omc-flywheel-dev-addressable-ids-bucketed-cr

# =============================================================================
# IAM ROLE
# =============================================================================

echo "📋 Importing IAM Role..."

# Glue Role
echo "  - omc_flywheel-dev-glue-role"
terraform import aws_iam_role.glue_role omc_flywheel-dev-glue-role

# IAM Role Policy Attachment
echo "  - IAM role policy attachment"
terraform import aws_iam_role_policy_attachment.glue_s3_access "omc_flywheel-dev-glue-role/arn:aws:iam::${ACCOUNT_ID}:policy/omc_flywheel-dev-glue-role-s3-access"

# =============================================================================
# S3 BUCKETS
# =============================================================================

echo "📋 Importing S3 Buckets..."

# Data Bucket
echo "  - omc-flywheel-data-us-east-1-dev"
terraform import aws_s3_bucket.data_bucket omc-flywheel-data-us-east-1-dev

# Analysis Bucket
echo "  - omc-flywheel-dev-analysis-data"
terraform import aws_s3_bucket.analysis_bucket omc-flywheel-dev-analysis-data

# =============================================================================
# GLUE CATALOG DATABASE
# =============================================================================

echo "📋 Importing Glue Catalog Database..."

# Final Database
echo "  - omc_flywheel_dev"
terraform import aws_glue_catalog_database.final_database "${ACCOUNT_ID}:omc_flywheel_dev"

echo "✅ Import completed successfully!"
echo ""
echo "🎯 Next steps:"
echo "1. Run 'terraform plan' to verify the import"
echo "2. Check for any configuration drift"
echo "3. Update configurations if needed"
