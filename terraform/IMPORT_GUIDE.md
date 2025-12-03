# Import Existing Resources Guide

Since the production resources already exist, you need to import them into Terraform state before managing them.

## Quick Import (Automated)

Run the automated import script:
```bash
cd terraform
./import_detailed.sh
```

## Manual Import (Step by Step)

If you prefer to import manually or if the automated script fails:

### 1. Import Glue Database
```bash
terraform import aws_glue_catalog_database.main omc_flywheel_prod
```

### 2. Import IAM Role
```bash
terraform import aws_iam_role.glue_role omc_flywheel-prod-glue-role
```

### 3. Import IAM Role Policy
```bash
terraform import aws_iam_role_policy.glue_s3_access omc_flywheel-prod-glue-role:omc_flywheel-prod-glue-role-s3-access
```

### 4. Import IAM Role Policy Attachment
```bash
terraform import aws_iam_role_policy_attachment.glue_service_role omc_flywheel-prod-glue-role/arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole
```

### 5. Import S3 Buckets (if they exist)
```bash
# Check if buckets exist first
aws s3api head-bucket --bucket omc-flywheel-data-us-east-1-prod
aws s3api head-bucket --bucket omc-flywheel-prod-analysis-data

# Import if they exist
terraform import aws_s3_bucket.data_bucket omc-flywheel-data-us-east-1-prod
terraform import aws_s3_bucket.analysis_bucket omc-flywheel-prod-analysis-data
```

### 6. Import Glue Jobs
```bash
terraform import aws_glue_job.infobase_split_and_bucket etl-omc-flywheel-prod-infobase-split-and-bucket
terraform import aws_glue_job.addressable_bucket etl-omc-flywheel-prod-addressable-bucket
terraform import aws_glue_job.register_staged_tables etl-omc-flywheel-prod-register-staged-tables
terraform import aws_glue_job.create_athena_bucketed_tables etl-omc-flywheel-prod-create-athena-bucketed-tables
```

### 7. Import Glue Crawlers
```bash
terraform import aws_glue_crawler.infobase_attributes_bucketed crw-omc-flywheel-prod-infobase-attributes-bucketed-cr
terraform import aws_glue_crawler.addressable_ids_bucketed crw-omc-flywheel-prod-addressable-ids-bucketed-cr
```

## Verify Import

After importing, run:
```bash
terraform plan
```

You should see:
- **0 to add** (no new resources)
- **0 to change** (resources match configuration)
- **0 to destroy** (no resources to remove)

If you see changes, they might be:
- **Configuration drift** - Terraform config differs from actual resources
- **Missing resources** - Some resources weren't imported
- **Extra resources** - Resources exist that aren't in Terraform config

## Troubleshooting

### Import Errors
- **Resource not found**: Resource doesn't exist or name is wrong
- **Already managed**: Resource is already in Terraform state
- **Permission denied**: Check AWS credentials and permissions

### Configuration Drift
If `terraform plan` shows changes after import:
1. **Review the differences** - Are they intentional?
2. **Update Terraform config** to match existing resources
3. **Apply changes** if you want to modify resources

### Missing Resources
If some resources can't be imported:
1. **Check resource names** in AWS console
2. **Verify permissions** for resource access
3. **Create missing resources** with Terraform if needed

## After Import

Once all resources are imported and `terraform plan` shows no changes:

1. **Commit the state** to version control (if using remote state)
2. **Use Terraform** for future changes
3. **Monitor resources** with `terraform show`
4. **Apply changes** with `terraform apply`

## State Management

- **Local state**: Stored in `terraform.tfstate`
- **Remote state**: Consider using S3 backend for team collaboration
- **State locking**: Use DynamoDB for state locking in production

## Best Practices

1. **Backup state** before major changes
2. **Review plans** before applying
3. **Use workspaces** for different environments
4. **Tag resources** consistently
5. **Document changes** in commit messages
