# Dev Glue Jobs Stack

This stack manages Glue jobs for the **development** environment.

## Overview

- **Environment**: Development
- **Purpose**: ETL jobs for data processing in dev
- **State**: Separate Terraform state from production

## Configuration

### Dev-Specific Defaults

- **Worker Count**: 5 (lower than prod: 10)
- **Timeout**: 30 minutes (shorter than prod: 60)
- **Max Retries**: 2 (more than prod: 1, for testing)

### Resource Names

- **Glue Database**: `omc_flywheel_dev`
- **Data Bucket**: `omc-flywheel-data-us-east-1-dev`
- **Analysis Bucket**: `omc-flywheel-dev-analysis-data`
- **Glue Role**: `omc_flywheel-dev-glue-role`

## Usage

### Initialize

```bash
cd infra/stacks/dev-gluejobs
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

- `glue_jobs`: All Glue jobs and crawlers created by the module

