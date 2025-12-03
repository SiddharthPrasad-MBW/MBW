# Cleanrooms Resource Associations Module

This Terraform module associates existing Cleanrooms resources (configured tables and ID namespace) to a collaboration membership.

## Features

- ✅ **Associate Existing Configured Tables** - Associates all provided configured table IDs to a membership
- ✅ **Associate ID Namespace** - Associates the EXISTING ACXIdNamespace to the membership (does NOT create a new namespace, only creates the association link)
- ✅ **Idempotent** - Safe to run multiple times
- ✅ **Automatic Discovery** - Can be used with a script to discover all `part_*` tables

## Prerequisites

- Existing configured tables must already exist in Cleanrooms
- IAM role `cleanrooms-glue-s3-access` must exist
- Entity Resolution ID namespace must exist
- Membership ID must be provided

## Usage

**Note:** This module uses `null_resource` with `local-exec` because Terraform's AWS provider has inconsistent support for Cleanrooms associations.

**Important:** The `manage-collaboration-invites.py` script automatically:
- Discovers `part_*` tables dynamically (excludes `n_a` tables)
- Limits to 25 associations (AWS quota)
- Creates associations with correct names: `acx_<table_name>`
- Creates collaboration analysis rules automatically
- Uses role: `cleanrooms-glue-s3-access`

### Basic Example

```hcl
module "associate_resources" {
  source = "../../modules/crassociations"

  membership_id = "e50c6d1d-68a6-4aa8-9cad-df9a5a30bd90"
  
  # Map of existing configured tables (discovered via script)
  existing_configured_tables = {
    "table-id-1" = {
      name = "part_ibe_01"
    }
    "table-id-2" = {
      name = "part_ibe_02"
    }
  }
  
  id_namespace_arn  = "arn:aws:entityresolution:us-east-1:239083076653:idnamespace/ACXIdNamespace"
  id_namespace_name = "ACXIdNamespace"
  
  aws_profile = "flywheel-prod"
  aws_region  = "us-east-1"
}
```

### With Script Discovery

First, discover all `part_*` configured tables:

```bash
python3 scripts/discover-configured-tables.py --filter "part_" --profile flywheel-prod
```

This outputs Terraform HCL format. Copy the output into your `terraform.tfvars`:

```hcl
existing_configured_tables = {
  "table-id-1" = {
    name = "part_ibe_01"
  }
  "table-id-2" = {
    name = "part_ibe_02"
  }
  # ... more tables
}
```

Then use in Terraform:

```hcl
module "associate_resources" {
  source = "../../modules/crassociations"

  membership_id = "e50c6d1d-68a6-4aa8-9cad-df9a5a30bd90"
  existing_configured_tables = var.existing_configured_tables
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| membership_id | Clean Rooms membership ID | string | - | yes |
| existing_configured_tables | Map of table_id -> {name: table_name} | map(object) | {} | yes |
| id_namespace_arn | ARN of Entity Resolution ID namespace | string | (default ACXIdNamespace) | no |
| id_namespace_name | Name of ID namespace association | string | "ACXIdNamespace" | no |
| role_name | IAM role name for Clean Rooms access | string | "cleanrooms-glue-s3-access" | no |
| aws_profile | AWS profile for API calls | string | "flywheel-prod" | no |
| aws_region | AWS region | string | "us-east-1" | no |

## Outputs

| Name | Description |
|------|-------------|
| table_association_ids | Map of table association IDs |
| table_association_names | Map of table association names |
| role_arn | IAM role ARN used |

## Workflow

1. **Discover Tables**: Run script to get all `part_*` configured table IDs
2. **Apply Terraform**: Pass membership_id and table IDs to module
3. **Verify**: Check associations in AWS Console or via CLI

## Notes

- **ID Namespace**: The script associates the EXISTING ACXIdNamespace (does NOT create a new namespace). It only creates the association link between the existing namespace and the membership.
- ID namespace association uses a `null_resource` with `local-exec` because Terraform AWS provider doesn't support `aws_cleanrooms_id_namespace_association` yet
- Table associations are managed via script (Terraform provider support is inconsistent)
- The script will skip associations that already exist (idempotent)

