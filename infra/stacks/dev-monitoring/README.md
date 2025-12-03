# Dev Monitoring Stack

This stack manages monitoring infrastructure for the **development** environment.

## Overview

- **Environment**: Development
- **Purpose**: Data quality monitoring and alerts in dev
- **State**: Separate Terraform state from production

## Configuration

### Dev-Specific Defaults

- **Schedule**: Every 12 hours (more frequent than prod: 24 hours)
- **Retention**: 7 days (shorter than prod: 30 days)
- **Worker Count**: 1 (lower than prod: 2)
- **Timeout**: 3 minutes (shorter than prod: 5)

### Resource Names

- **Glue Database**: `omc_flywheel_dev`
- **Data Bucket**: `omc-flywheel-data-us-east-1-dev`
- **Analysis Bucket**: `omc-flywheel-dev-analysis-data`

## Usage

### Initialize

```bash
cd infra/stacks/dev-monitoring
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
  -var="data_bucket_name=my-custom-dev-bucket"
```

## Variables

See `variables.tf` for all available variables.

## Outputs

- `monitoring`: Monitoring job, SNS topic, CloudWatch dashboard, and related resources

