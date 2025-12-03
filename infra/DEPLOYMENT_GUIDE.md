# Lake Formation Infrastructure Deployment Guide

This guide walks through deploying the new modular Lake Formation infrastructure for the OMC Flywheel Cleanroom solution.

## 🎯 Overview

The new infrastructure provides:
- **Toggle-able Lake Formation** for safe production deployment
- **Path-scoped registration** (only `.../bucketed/` paths)
- **Environment separation** (dev/prod configurations)
- **Hybrid mode** (IAM + Lake Formation) by default
- **Writer/Reader separation** (Glue roles vs Cleanroom consumers)

## 📋 Prerequisites

- Terraform >= 1.0
- AWS CLI configured with appropriate permissions
- Access to both dev and prod AWS accounts
- Lake Formation admin permissions
- **Consumer role created**: `omc-flywheel-*-cleanroom-consumer` (can be created after Terraform deployment)

## 🚀 Deployment Steps

### Step 0: Create Consumer Role (Optional - Can be done after deployment)

Before deploying Terraform, you can optionally create the Cleanroom consumer role. See [Consumer Role IAM Policies](CONSUMER_ROLE_IAM_POLICIES.md) for detailed instructions.

**Quick Setup:**
```bash
# Create the role
aws iam create-role \
  --role-name omc_flywheel-dev-cleanroom-consumer \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"athena.amazonaws.com"},"Action":"sts:AssumeRole"}]}' \
  --profile flywheel-dev

# Terraform will grant Lake Formation permissions automatically when deployed
```

### Step 1: Development Environment

```bash
# Navigate to dev environment
cd infra/envs/dev

# Initialize Terraform
terraform init

# Review planned changes
terraform plan

# Apply configuration
terraform apply
```

**Expected Output:**
- Lake Formation data lake settings configured
- S3 paths registered:
  - `s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_cluster/` (source)
  - `s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/cleanroom_tables/bucketed/` (target)
- Glue database `omc_flywheel_dev` created
- Write permissions granted to `omc_flywheel-dev-glue-role` (writer)
- Read permissions granted to `omc_flywheel-dev-cleanroom-consumer` (reader)

### Step 2: Test CTAS Operations

```bash
# Test the bucketed table creation job
aws glue start-job-run \
  --job-name etl-omc-flywheel-dev-create-athena-bucketed-tables \
  --arguments '{"--TABLES_FILTER": "ibe_01_a"}' \
  --region us-east-1 \
  --profile flywheel-dev
```

**Verify Success:**
- Job completes without Lake Formation errors
- Bucketed table `bucketed_ibe_01_a` created in Glue catalog
- Data written to S3 path under Lake Formation governance

### Step 3: Production Environment (Dry Run)

```bash
# Navigate to prod environment
cd infra/envs/prod

# Initialize Terraform
terraform init

# Review planned changes (should show no changes with enable = false)
terraform plan
```

**Expected Output:**
- No resources created (because `enable = false`)
- Configuration ready for future deployment

### Step 4: Production Deployment (When Ready)

```bash
# Enable Lake Formation in prod
# Edit infra/envs/prod/main.tf and set enable = true

# Apply configuration
terraform apply
```

**Expected Output:**
- Lake Formation data lake settings configured
- S3 paths registered:
  - `s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_cluster/` (source)
  - `s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/cleanroom_tables/bucketed/` (target)
- Glue database `omc_flywheel_prod` created
- Write permissions granted to `omc_flywheel-prod-glue-role` (writer)
- Read permissions granted to `omc_flywheel-prod-cleanroom-consumer` (reader)

### Step 5: Production Testing

```bash
# Test with small dataset first
aws glue start-job-run \
  --job-name etl-omc-flywheel-prod-create-athena-bucketed-tables \
  --arguments '{"--TABLES_FILTER": "ibe_01_a"}' \
  --region us-east-1 \
  --profile flywheel-prod
```

## 🔧 Configuration Options

### Environment Variables

#### Dev Environment (`infra/envs/dev/main.tf`)
```hcl
module "lakeformation" {
  # ... other settings ...
  
  enable           = true   # Lake Formation enabled for testing
  lf_only_defaults = false  # IAM-only defaults (hybrid mode)
}
```

#### Prod Environment (`infra/envs/prod/main.tf`)
```hcl
module "lakeformation" {
  # ... other settings ...
  
  enable           = false  # Disabled until ready to cut over
  lf_only_defaults = false  # IAM-only defaults (hybrid mode)
}
```

### Advanced Configuration

#### Enable Source Path Registration
```hcl
register_source = true
source_bucket   = "omc-flywheel-data-us-east-1-dev"
source_prefix   = "omc_cleanroom_data/cleanroom_tables/split_cluster/"
```

#### Switch to LF-Only Mode
```hcl
lf_only_defaults = true  # All operations require LF permissions
```

#### Add Additional Principals
```hcl
writer_principals = [
  "arn:aws:iam::ACCOUNT_ID:role/omc_flywheel-dev-glue-role"
]

reader_principals = [
  "arn:aws:iam::ACCOUNT_ID:role/omc_flywheel-dev-cleanroom-consumer",
  "arn:aws:iam::ACCOUNT_ID:role/athena-exec-role",
  "arn:aws:iam::ACCOUNT_ID:role/cleanroom-access-role"
]
```

## 🔍 Validation

### Check Lake Formation Registration

```bash
# List registered resources
aws lakeformation list-resources --region us-east-1

# Should show:
# arn:aws:s3:::omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/cleanroom_tables/bucketed
```

### Check Permissions

```bash
# List permissions for Writer role (Glue job role)
aws lakeformation list-permissions \
  --principal "arn:aws:iam::ACCOUNT_ID:role/omc_flywheel-dev-glue-role" \
  --region us-east-1

# List permissions for Reader role (Cleanroom consumer)
aws lakeformation list-permissions \
  --principal "arn:aws:iam::ACCOUNT_ID:role/omc_flywheel-dev-cleanroom-consumer" \
  --region us-east-1
```

### Check Glue Database

```bash
# Verify database exists
aws glue get-database --name omc_flywheel_dev --region us-east-1
```

## 🚨 Rollback Plan

### Disable Lake Formation

```hcl
# Set enable = false in main.tf
enable = false
```

```bash
# Apply changes
terraform apply
```

This will:
- Remove Lake Formation permissions
- Unregister S3 paths
- Keep Glue database (no data loss)
- Revert to IAM-only access

### Emergency Access

If Lake Formation blocks critical operations:

1. **Immediate**: Set `enable = false` and apply
2. **Investigate**: Check permission grants and principals
3. **Fix**: Adjust permissions or add missing principals
4. **Re-enable**: Set `enable = true` after fixes

## 📊 Monitoring

### CloudWatch Metrics

Monitor these metrics after deployment:
- Glue job success/failure rates
- Athena query performance
- S3 access patterns

### Key Alerts

Set up alerts for:
- Glue job failures
- Lake Formation permission errors
- S3 access denied errors

## 🔐 Security Considerations

### Principle of Least Privilege

- Grant only necessary permissions
- Use path-scoped registration (not bucket-wide)
- Regularly audit permission grants

### Access Patterns

- **Dev**: Full permissions for testing
- **Prod**: Minimal permissions for production workloads
- **Cleanroom**: Separate role with read-only access

### Compliance

- Document all permission grants
- Maintain audit trail of changes
- Regular security reviews

## 📚 Troubleshooting

### Common Issues

**"Insufficient Lake Formation permissions"**
- Verify `enable = true`
- Check DATA_LOCATION_ACCESS grants
- Ensure Glue role in principals list

**"Resource does not exist"**
- Check S3 path registration
- Verify bucket and prefix exist
- Review Lake Formation resource list

**"Access denied"**
- Check IAM permissions
- Verify Lake Formation grants
- Review data lake settings

### Debug Commands

```bash
# Check current caller identity
aws sts get-caller-identity

# List all Lake Formation resources
aws lakeformation list-resources

# Check specific permissions
aws lakeformation list-permissions --principal <PRINCIPAL_ARN>

# Verify Glue database
aws glue get-database --name <DATABASE_NAME>
```

## ✅ Success Criteria

Deployment is successful when:

- [ ] Dev environment deploys without errors
- [ ] CTAS operations work in dev environment
- [ ] Bucketed tables created successfully
- [ ] Data written to governed S3 paths
- [ ] Prod environment ready for deployment
- [ ] Rollback plan tested and documented

## 📞 Support

For issues or questions:
- Check [Troubleshooting Guide](../docs/TROUBLESHOOTING.md)
- Review [Current Process Flow](../docs/CURRENT_PROCESS_FLOW.md)
- Contact the data engineering team

---

**Deployment Guide Version**: 1.0  
**Last Updated**: October 2025  
**Next Review**: After production deployment
