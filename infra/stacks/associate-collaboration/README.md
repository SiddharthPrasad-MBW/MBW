# Associate Resources to Collaboration

This stack associates existing Cleanrooms resources (configured tables and ID namespace) to a collaboration membership.

## Quick Start

### Step 1: Discover Existing Tables

```bash
cd scripts
python3 discover-configured-tables.py --filter "part_" --profile flywheel-prod
```

**Note:** The script automatically filters for `part_*` tables and excludes `n_a` tables. It also limits to 25 tables (AWS quota).

This will output Terraform HCL format like:

```hcl
existing_configured_tables = {
  "abc-123-def" = {
    name = "part_ibe_01"
  }
  "def-456-ghi" = {
    name = "part_ibe_02"
  }
  # ... more tables
}
```

### Step 2: Create terraform.tfvars

Create `infra/stacks/associate-collaboration/terraform.tfvars`:

```hcl
membership_id = "e50c6d1d-68a6-4aa8-9cad-df9a5a30bd90"

# Paste the output from Step 1 here
existing_configured_tables = {
  "abc-123-def" = {
    name = "part_ibe_01"
  }
  # ... all discovered tables
}
```

### Step 3: Apply Terraform

```bash
cd infra/stacks/associate-collaboration
terraform init
terraform plan
terraform apply
```

## What This Does

1. **Associates Configured Tables**: 
   - Automatically discovers `part_*` tables (excludes `n_a` tables)
   - Limits to 25 associations (AWS quota)
   - Creates associations with names: `acx_<table_name>`
   - Creates collaboration analysis rules automatically
   - Uses role: `cleanrooms-glue-s3-access`
2. **Associates ID Namespace**: Associates ACXIdNamespace to the membership (via script since Terraform doesn't support it yet)

## Variables

| Name | Description | Required |
|------|-------------|----------|
| membership_id | Clean Rooms membership ID | Yes |
| existing_configured_tables | Map of table_id -> {name: table_name} | Yes |
| id_namespace_arn | ID namespace ARN | No (defaults to ACXIdNamespace) |
| id_namespace_name | ID namespace name | No (defaults to ACXIdNamespace) |
| role_name | IAM role name | No (defaults to cleanrooms-glue-s3-access) |
| aws_profile | AWS profile | No (defaults to flywheel-prod) |
| aws_region | AWS region | No (defaults to us-east-1) |

## Verification

After applying, verify associations:

```bash
# Check table associations
aws cleanrooms list-configured-table-associations \
  --membership-identifier <membership-id> \
  --profile flywheel-prod

# Check ID namespace association
aws cleanrooms list-id-namespace-associations \
  --membership-identifier <membership-id> \
  --profile flywheel-prod
```

