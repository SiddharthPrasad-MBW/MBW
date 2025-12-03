# Dev Environment: Permissions and Monitoring Setup

## Overview

This document covers the complete setup for dev environment including:
- IAM permissions for Glue jobs
- Monitoring job configuration
- Required resources and dependencies

## IAM Permissions

### Glue Job Role Permissions

The Glue job role (`omc_flywheel-dev-glue-role`) needs the following permissions:

#### 1. S3 Access Policy
**Policy Name**: `omc-flywheel-dev-glue-role-s3-access`

**Permissions**:
- `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket`
- **Resources**:
  - Data bucket: `omc-flywheel-data-us-east-1-dev` and `/*`
  - Analysis bucket: `omc-flywheel-dev-analysis-data` and `/*`
  - Glue assets bucket: `aws-glue-assets-{account-id}-us-east-1` and `/*`

#### 2. Cleanrooms Read-Only Policy
**Policy Name**: `omc-flywheel-dev-glue-role-cleanrooms-read`

**Permissions**:
- `cleanrooms:GetConfiguredTable`
- `cleanrooms:ListConfiguredTables`
- `cleanrooms:GetConfiguredTableAnalysisRule`
- `cleanrooms:GetConfiguredTableAssociation`
- `cleanrooms:ListConfiguredTableAssociations`
- `cleanrooms:GetConfiguredTableAssociationAnalysisRule`
- `cleanrooms:GetMembership`
- `cleanrooms:ListMemberships`
- `cleanrooms:GetSchemaAnalysisRule`
- `cleanrooms:ListSchemas`
- `cleanrooms:GetIdNamespaceAssociation`
- `cleanrooms:ListIdNamespaceAssociations`
- `cleanrooms:GetIdMappingTable`
- `cleanrooms:ListIdMappingTables`
- `entityresolution:GetIdNamespace`
- `entityresolution:ListIdNamespaces`
- `entityresolution:GetSchemaMapping`
- `entityresolution:ListSchemaMappings`
- `glue:GetTable`, `glue:GetTables`, `glue:GetDatabase`, `glue:GetDatabases`

#### 3. AWS Glue Service Role
**Policy**: `arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole`
- Attached automatically by Terraform

### Verification

```bash
# Check IAM role exists
aws iam get-role --role-name omc_flywheel-dev-glue-role --profile flywheel-dev

# Check attached policies
aws iam list-attached-role-policies --role-name omc_flywheel-dev-glue-role --profile flywheel-dev

# Check inline policies
aws iam list-role-policies --role-name omc_flywheel-dev-glue-role --profile flywheel-dev
```

## Monitoring Job

### Overview

The monitoring job (`etl-omc-flywheel-dev-generate-data-monitor-report`) performs:
- Partition integrity checks (256 id_bucket partitions)
- Data freshness validation
- Schema compliance verification
- Record count validation
- Primary key integrity checks

### Deployment

The monitoring job is deployed via a **separate stack**:

```bash
cd infra/stacks/dev-monitoring
terraform init
terraform plan
terraform apply
```

### Monitoring Job Configuration (Dev)

| Setting | Dev Value | Prod Value |
|---------|-----------|------------|
| **Schedule** | `rate(12 hours)` | `rate(24 hours)` |
| **Retention** | 7 days | 30 days |
| **Workers** | 1 | 2 |
| **Timeout** | 3 minutes | 5 minutes |
| **Job Name** | `etl-omc-flywheel-dev-generate-data-monitor-report` | `etl-omc-flywheel-prod-generate-data-monitor-report` |

### Monitoring Job Permissions

**Role**: `omc-flywheel-dev-data-monitor-role`

**Permissions**:
- S3 read/write to data and analysis buckets
- Glue catalog read access
- Athena query execution
- SNS publish (for alerts)
- CloudWatch Logs write

### Running Monitoring Job

```bash
# Manual execution
aws glue start-job-run \
  --job-name etl-omc-flywheel-dev-generate-data-monitor-report \
  --profile flywheel-dev

# Check status
aws glue get-job-runs \
  --job-name etl-omc-flywheel-dev-generate-data-monitor-report \
  --max-items 5 \
  --profile flywheel-dev
```

### Monitoring Reports

**Location**: `s3://omc-flywheel-dev-analysis-data/data-monitor/`

**Report Formats**:
- JSON: Complete monitoring results
- CSV: Tabular data for analysis

## Required Resources Checklist

### Before Deploying Dev

- [ ] **S3 Buckets**:
  - [ ] `omc-flywheel-data-us-east-1-dev` (data bucket)
  - [ ] `omc-flywheel-dev-analysis-data` (analysis bucket)
  - [ ] `aws-glue-assets-{account-id}-us-east-1` (Glue assets bucket)

- [ ] **Glue Database**:
  - [ ] `omc_flywheel_dev` exists

- [ ] **IAM Roles**:
  - [ ] `omc_flywheel-dev-glue-role` exists (or will be created)
  - [ ] Role has S3 permissions
  - [ ] Role has Glue permissions
  - [ ] Role has Cleanrooms read permissions (if using reporting)

- [ ] **Source Data**:
  - [ ] Data exists in `s3://omc-flywheel-data-us-east-1-dev/opus/`
  - [ ] Snapshot structure: `snapshot_dt=YYYY-MM-DD/`
  - [ ] CSV mapping files exist

- [ ] **Scripts**:
  - [ ] All dev scripts uploaded to Glue assets bucket
  - [ ] Script names match job names

## Deployment Order

### 1. Deploy Glue Jobs Stack

```bash
cd infra/stacks/dev-gluejobs
terraform init
terraform plan
terraform apply
```

**Creates**:
- Glue jobs (with dev naming)
- IAM policies (with dev naming)
- Crawlers (with dev naming)

### 2. Deploy Monitoring Stack

```bash
cd infra/stacks/dev-monitoring
terraform init
terraform plan
terraform apply
```

**Creates**:
- Monitoring Glue job
- Monitoring IAM role and policies
- SNS topic for alerts
- CloudWatch log group
- CloudWatch dashboard

### 3. Upload Scripts

```bash
./scripts/setup-dev-scripts.sh
```

**Uploads**:
- All dev ETL scripts
- Shared scripts (data_monitor.py, etc.)

## Verification Steps

### 1. Verify IAM Permissions

```bash
# Check role exists
aws iam get-role --role-name omc_flywheel-dev-glue-role --profile flywheel-dev

# Check policies
aws iam list-attached-role-policies \
  --role-name omc_flywheel-dev-glue-role \
  --profile flywheel-dev
```

### 2. Verify Monitoring Job

```bash
# Check monitoring job exists
aws glue get-job \
  --job-name etl-omc-flywheel-dev-generate-data-monitor-report \
  --profile flywheel-dev

# Check monitoring role
aws iam get-role \
  --role-name omc-flywheel-dev-data-monitor-role \
  --profile flywheel-dev
```

### 3. Verify Scripts Uploaded

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --profile flywheel-dev --query Account --output text)
aws s3 ls s3://aws-glue-assets-${ACCOUNT_ID}-us-east-1/scripts/ \
  --profile flywheel-dev \
  --recursive
```

## Troubleshooting

### Issue: Permission Denied on S3

**Error**: `AccessDeniedException` when accessing S3

**Solution**:
1. Verify IAM role has S3 permissions
2. Check bucket policies
3. Ensure role is attached to job

### Issue: Monitoring Job Fails

**Error**: Monitoring job fails immediately

**Solution**:
1. Check monitoring role permissions
2. Verify `data_monitor.py` script uploaded
3. Check CloudWatch logs: `/aws/glue/jobs/etl-omc-flywheel-dev-generate-data-monitor-report`

### Issue: Cleanrooms API Access Denied

**Error**: `AccessDeniedException` for Cleanrooms APIs

**Solution**:
1. Verify Cleanrooms read policy attached
2. Check policy includes all required actions
3. Ensure role has permissions in dev account

## Environment-Aware Naming

### IAM Policies

| Resource | Dev Name | Prod Name |
|----------|----------|-----------|
| S3 Access Policy | `omc-flywheel-dev-glue-role-s3-access` | `omc-flywheel-prod-glue-role-s3-access` |
| Cleanrooms Policy | `omc-flywheel-dev-glue-role-cleanrooms-read` | `omc-flywheel-prod-glue-role-cleanrooms-read` |

### Monitoring Resources

| Resource | Dev Name | Prod Name |
|----------|----------|-----------|
| Job | `etl-omc-flywheel-dev-generate-data-monitor-report` | `etl-omc-flywheel-prod-generate-data-monitor-report` |
| Role | `omc-flywheel-dev-data-monitor-role` | `omc-flywheel-prod-data-monitor-role` |
| SNS Topic | `omc-flywheel-dev-data-monitor-alerts` | `omc-flywheel-prod-data-monitor-alerts` |
| Log Group | `/aws/glue/jobs/etl-omc-flywheel-dev-generate-data-monitor-report` | `/aws/glue/jobs/etl-omc-flywheel-prod-generate-data-monitor-report` |

## Next Steps

After setting up permissions and monitoring:

1. ✅ Run validation pipeline
2. ✅ Check monitoring reports
3. ✅ Verify all permissions working
4. ✅ Document any dev-specific issues
5. ✅ Prepare for production deployment

---

**Last Updated**: November 18, 2025

