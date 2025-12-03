#!/bin/bash
# Detailed import script for existing production resources
# This script imports existing resources and handles IAM policies

set -e

echo "🔄 Starting detailed import of existing production resources..."

# Set AWS profile
export AWS_PROFILE=flywheel-prod

# Get account ID for resource ARNs
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "📋 Account ID: $ACCOUNT_ID"

# Import Glue Database
echo "📊 Importing Glue database..."
terraform import aws_glue_catalog_database.main omc_flywheel_prod || echo "⚠️  Database may already be imported"

# Import IAM Role
echo "🔐 Importing IAM role..."
terraform import aws_iam_role.glue_role omc_flywheel-prod-glue-role || echo "⚠️  Role may already be imported"

# Import IAM Role Policy (using the role name and policy name)
echo "📜 Importing IAM role policy..."
terraform import aws_iam_role_policy.glue_s3_access omc_flywheel-prod-glue-role:omc_flywheel-prod-glue-role-s3-access || echo "⚠️  Policy may already be imported"

# Import IAM Role Policy Attachment
echo "🔗 Importing IAM role policy attachment..."
terraform import aws_iam_role_policy_attachment.glue_service_role omc_flywheel-prod-glue-role/arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole || echo "⚠️  Policy attachment may already be imported"

# Import S3 Buckets (skip if they don't exist)
echo "🪣 Checking and importing S3 buckets..."
aws s3api head-bucket --bucket omc-flywheel-data-us-east-1-prod 2>/dev/null && \
  terraform import aws_s3_bucket.data_bucket omc-flywheel-data-us-east-1-prod || \
  echo "⚠️  Data bucket doesn't exist or not accessible"

aws s3api head-bucket --bucket omc-flywheel-prod-analysis-data 2>/dev/null && \
  terraform import aws_s3_bucket.analysis_bucket omc-flywheel-prod-analysis-data || \
  echo "⚠️  Analysis bucket doesn't exist or not accessible"

# Import Glue Jobs
echo "⚙️  Importing Glue jobs..."
terraform import aws_glue_job.infobase_split_and_bucket etl-omc-flywheel-prod-infobase-split-and-bucket || echo "⚠️  Job may already be imported"
terraform import aws_glue_job.addressable_bucket etl-omc-flywheel-prod-addressable-bucket || echo "⚠️  Job may already be imported"
terraform import aws_glue_job.register_staged_tables etl-omc-flywheel-prod-register-staged-tables || echo "⚠️  Job may already be imported"
terraform import aws_glue_job.create_athena_bucketed_tables etl-omc-flywheel-prod-create-athena-bucketed-tables || echo "⚠️  Job may already be imported"

# Import Glue Crawlers
echo "🕷️  Importing Glue crawlers..."
terraform import aws_glue_crawler.infobase_attributes_bucketed crw-omc-flywheel-prod-infobase-attributes-bucketed-cr || echo "⚠️  Crawler may already be imported"
terraform import aws_glue_crawler.addressable_ids_bucketed crw-omc-flywheel-prod-addressable-ids-bucketed-cr || echo "⚠️  Crawler may already be imported"

echo "✅ Import process completed!"
echo "🔍 Running terraform plan to check for any remaining differences..."

# Run terraform plan to see what's left
terraform plan -detailed-exitcode
PLAN_EXIT_CODE=$?

if [ $PLAN_EXIT_CODE -eq 0 ]; then
    echo "🎉 Perfect! All resources are in sync - no changes needed."
elif [ $PLAN_EXIT_CODE -eq 2 ]; then
    echo "📝 Some resources have differences. Review the plan above."
    echo "💡 You may need to run 'terraform apply' to sync the configuration."
else
    echo "❌ Error running terraform plan. Check the output above."
fi

echo "📋 Summary:"
echo "   - Glue Database: Imported"
echo "   - IAM Role & Policies: Imported" 
echo "   - S3 Buckets: Checked and imported if they exist"
echo "   - Glue Jobs: Imported"
echo "   - Glue Crawlers: Imported"
echo ""
echo "💡 Next steps:"
echo "   1. Review 'terraform plan' output"
echo "   2. Run 'terraform apply' if needed to sync configuration"
echo "   3. Use 'terraform output' to see resource information"
