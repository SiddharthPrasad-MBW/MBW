# Dev Cleanrooms Configured Tables Stack

This stack manages Cleanrooms configured tables for the **development** environment.

## Overview

- **Environment**: Development
- **Purpose**: Configured tables for Clean Rooms analysis in dev
- **State**: Separate Terraform state from production

## Configuration

### Dev-Specific Defaults

- **Glue Database**: `omc_flywheel_dev` (vs prod: `omc_flywheel_prod`)
- **Data Bucket**: `omc-flywheel-data-us-east-1-dev` (vs prod: `omc-flywheel-data-us-east-1-prod`)
- **IAM Role**: `cleanrooms-glue-s3-access` (shared name, but separate resources per environment)

### Tables Configured

All 28 `part_` tables are configured:
- `part_addressable_ids`
- `part_ibe_01` through `part_ibe_09` (and variants)
- `part_miacs_01` through `part_miacs_04` (and variants)
- `part_n_a`, `part_n_a_a`
- `part_new_borrowers`

## Usage

### Initialize

```bash
cd infra/stacks/dev-crconfigtables
terraform init
```

### Plan

```bash
terraform plan
```

### Apply

```bash
terraform apply
```

### Override Variables

Create a `terraform.tfvars` file or pass variables:

```bash
terraform apply \
  -var="glue_database_name=my_custom_dev_db" \
  -var="data_bucket_name=my-custom-dev-bucket" \
  -var="cleanrooms_membership_id=your-membership-id"
```

## Variables

See `variables.tf` for all available variables.

### Required Variables

- `cleanrooms_membership_id`: Clean Rooms membership ID (can be null to defer association)

### Optional Variables

- `cleanrooms_allowed_query_providers`: List of AWS account IDs allowed to submit queries
- `glue_database_name`: Defaults to `omc_flywheel_dev`
- `data_bucket_name`: Defaults to `omc-flywheel-data-us-east-1-dev`

## Outputs

- `cleanrooms_tables`: All configured tables and associations
- `account_info`: AWS account and region information

## Important Notes

### Terraform Limitations

The AWS Terraform provider has limited support for Cleanrooms resources:
- ✅ **Supported**: Configured tables, IAM roles
- ❌ **Not Supported**: Analysis rules, table associations (use Python script instead)

### Using Python Script for Full Setup

For complete setup including analysis rules and associations, use the Python script:

```bash
cd scripts
python3 create-cleanrooms-configured-tables.py \
  --profile flywheel-dev \
  --database omc_flywheel_dev \
  --bucket omc-flywheel-data-us-east-1-dev \
  --membership-id <dev-membership-id> \
  --allowed-query-providers <account-ids>
```

### Adding Collaboration Analysis Rules

After creating configured tables and associations, add collaboration analysis rules:

```bash
cd scripts
python3 add-collaboration-analysis-rules.py \
  --profile flywheel-dev \
  --membership-id <dev-membership-id> \
  --allowed-analyses ANY
```

## Dev vs Prod Comparison

| Setting | Dev | Prod |
|---------|-----|------|
| Glue Database | `omc_flywheel_dev` | `omc_flywheel_prod` |
| Data Bucket | `omc-flywheel-data-us-east-1-dev` | `omc-flywheel-data-us-east-1-prod` |
| Tables | Same 28 tables | Same 28 tables |
| IAM Role | `cleanrooms-glue-s3-access` | `cleanrooms-glue-s3-access` |

