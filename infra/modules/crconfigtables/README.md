# Cleanrooms Configured Tables Module

This Terraform module creates AWS Cleanrooms configured tables from Glue catalog tables with custom analysis rules.

## Features

- ✅ **Automatic column discovery** - Pulls all columns from Glue tables automatically
- ✅ **Custom analysis rules** - Supports CUSTOM, AGGREGATION, and LIST rule types
- ✅ **IAM role management** - Creates IAM role for Clean Rooms to access Glue/S3
- ✅ **Deferred association** - Optionally associates tables with Clean Rooms membership
- ✅ **Flexible configuration** - Supports per-table or global column selection

## Usage

### Basic Example

```hcl
module "cleanrooms_tables" {
  source = "../../modules/crconfigtables"

  create_role            = true
  membership_id          = null          # will associate later
  allowed_query_providers = ["921290734397", "657425294073"]  # AMC Service and Query Submitter
  use_all_columns        = true
  s3_resources           = [
    "arn:aws:s3:::omc-flywheel-data-us-east-1-prod",
    "arn:aws:s3:::omc-flywheel-data-us-east-1-prod/*"
  ]
  tags = {
    Project     = "OMC Flywheel Cleanroom"
    Environment = "Production"
  }

  tables = {
    part_ibe_01 = {
      description     = "IBE_01 partitioned table for Clean Rooms"
      analysis_method = "DIRECT"
      glue = {
        region   = "us-east-1"
        database = "omc_flywheel_prod"
        table    = "part_ibe_01"
      }
      rule = { type = "CUSTOM" }
    }
  }
}
```

### With Membership Association

```hcl
module "cleanrooms_tables" {
  source = "../../modules/crconfigtables"

  membership_id          = "membership-1234567890abcdef"
  allowed_query_providers = ["921290734397", "657425294073"]  # AMC Service and Query Submitter
  use_all_columns        = true
  s3_resources           = [
    "arn:aws:s3:::omc-flywheel-data-us-east-1-prod",
    "arn:aws:s3:::omc-flywheel-data-us-east-1-prod/*"
  ]

  tables = {
    # ... table definitions
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| membership_id | Clean Rooms membership ID to associate tables with | `string` | `null` | no |
| create_role | Create IAM role for Clean Rooms access | `bool` | `true` | no |
| role_arn | Existing IAM role ARN (used when create_role=false) | `string` | `null` | no |
| s3_resources | S3 ARNs Clean Rooms needs to read | `list(string)` | `[]` | yes (if create_role=true) |
| use_all_columns | Pull all columns from Glue automatically | `bool` | `true` | no |
| allowed_query_providers | AWS account IDs allowed for custom queries | `list(string)` | `[]` | no |
| tags | Common tags for all resources | `map(string)` | `{}` | no |
| tables | Map of configured tables | `map(object)` | - | yes |

## Outputs

| Name | Description |
|------|-------------|
| configured_table_ids | IDs of created configured tables |
| configured_table_association_ids | IDs of table associations (if membership_id provided) |
| role_arn | Role ARN used by Clean Rooms |
| configured_table_names | Names of created configured tables |

## Analysis Rule Types

### CUSTOM
Allows custom SQL queries from specified AWS accounts.

```hcl
rule = {
  type = "CUSTOM"
}
```

### AGGREGATION
Allows aggregation queries with specified functions and dimensions.

```hcl
rule = {
  type              = "AGGREGATION"
  allowed_functions = ["SUM", "COUNT", "AVG"]
  dimension_columns = ["customer_user_id", "date"]
}
```

### LIST
Allows list queries with join and dimension columns.

```hcl
rule = {
  type              = "LIST"
  join_columns      = ["customer_user_id"]
  dimension_columns = ["date", "region"]
}
```

## Requirements

- Terraform >= 1.0
- AWS Provider >= 5.0
- Glue tables must exist before applying this module

## Notes

- Tables are created in Cleanrooms but not associated with a membership if `membership_id` is `null`
- Association can be added later by setting `membership_id` and re-applying
- All columns are automatically discovered from Glue table schemas when `use_all_columns = true`
- S3 resources must be specified when `create_role = true` for proper IAM permissions

