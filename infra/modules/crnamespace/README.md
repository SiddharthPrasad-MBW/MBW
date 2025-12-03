# Cleanrooms Identity Resolution Service Module

This Terraform module manages AWS Cleanrooms Identity Resolution Service resources, including ID namespace associations and ID mapping tables.

## Features

- ✅ **ID Namespace Association** - Links Entity Resolution ID namespaces to Cleanrooms memberships
- ✅ **ID Mapping Table** - Creates ID mapping tables in collaboration entity resolution
- ✅ **Resource Policy Management** - Automatically manages resource policies
- ✅ **Flexible Configuration** - Supports optional ID mapping table creation

## Prerequisites

- Entity Resolution ID namespace must exist in AWS Entity Resolution Service
- Entity Resolution ID mapping workflow must exist (if creating ID mapping table)
- Cleanrooms membership must exist

## Usage

### Basic Example - ID Namespace Only

```hcl
module "cr_namespace" {
  source = "../../modules/crnamespace"

  membership_id        = "6610c9aa-9002-475c-8695-d833485741bc"
  id_namespace_name   = "ACXIdNamespace"
  id_namespace_arn    = "arn:aws:entityresolution:us-east-1:239083076653:idnamespace/ACXIdNamespace"
  id_namespace_description = "ACX unique customer identifiers for Clean Rooms joins"
  
  tags = {
    Project     = "OMC Flywheel Cleanroom"
    Environment = "Production"
  }
}
```

### Full Example - With ID Mapping Table

```hcl
module "cr_namespace" {
  source = "../../modules/crnamespace"

  membership_id        = "6610c9aa-9002-475c-8695-d833485741bc"
  id_namespace_name   = "ACXIdNamespace"
  id_namespace_arn    = "arn:aws:entityresolution:us-east-1:239083076653:idnamespace/ACXIdNamespace"
  id_namespace_description = "ACX unique customer identifiers for Clean Rooms joins"
  
  id_mapping_table_name        = "acx-real_ids"
  id_mapping_table_description = "ID mapping table for real IDs"
  id_mapping_workflow_arn      = "arn:aws:entityresolution:us-east-1:239083076653:idmappingworkflow/ACX-Real_IDS"
  
  id_mapping_table_input_sources = [
    {
      id_namespace_association_id = module.cr_namespace.id_namespace_association_id
      type                        = "SOURCE"
    },
    {
      id_namespace_association_id = "3ff4df8f-f33c-4e04-8a34-0f8974cb627d"  # AMCIdNamespace
      type                        = "TARGET"
    }
  ]
  
  tags = {
    Project     = "OMC Flywheel Cleanroom"
    Environment = "Production"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| membership_id | Clean Rooms membership ID | string | - | yes |
| id_namespace_name | Name of the ID namespace association | string | - | yes |
| id_namespace_arn | ARN of the Entity Resolution ID namespace | string | - | yes |
| id_namespace_description | Description for the ID namespace association | string | "" | no |
| manage_resource_policies | Whether Clean Rooms should manage resource policies | bool | true | no |
| allow_use_as_dimension_column | Whether the ID namespace can be used as a dimension column | bool | false | no |
| id_mapping_table_name | Name of the ID mapping table | string | null | no |
| id_mapping_table_description | Description for the ID mapping table | string | "" | no |
| id_mapping_workflow_arn | ARN of the Entity Resolution ID mapping workflow | string | null | no |
| id_mapping_table_input_sources | List of input sources for ID mapping table | list(object) | [] | no |
| tags | Common tags for all resources | map(string) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| id_namespace_association_id | ID of the ID namespace association |
| id_namespace_association_arn | ARN of the ID namespace association |
| id_namespace_association_name | Name of the ID namespace association |
| id_mapping_table_id | ID of the ID mapping table (if created) |
| id_mapping_table_arn | ARN of the ID mapping table (if created) |
| id_mapping_table_name | Name of the ID mapping table (if created) |

## Important Notes

1. **Terraform Provider Support**: The Terraform AWS provider may not fully support all Cleanrooms Identity Resolution resources. If resources fail to create, you may need to use boto3 scripts similar to configured tables.

2. **Entity Resolution Resources**: This module assumes Entity Resolution ID namespaces and workflows are created separately (outside Terraform or in a different module).

3. **Dependencies**: ID mapping tables depend on ID namespace associations. The module handles this automatically.

4. **Naming Conventions**: 
   - ID namespace associations: Use descriptive names (e.g., `ACXIdNamespace`)
   - ID mapping tables: Use lowercase with underscores (e.g., `acx-real_ids`)

## Existing Resources

If you have existing resources, you can import them:

```bash
# Import ID namespace association
terraform import module.cr_namespace.aws_cleanrooms_id_namespace_association.namespace \
  membership/6610c9aa-9002-475c-8695-d833485741bc/idnamespaceassociation/5333558b-e6b8-4557-94a4-261d20294a20

# Import ID mapping table
terraform import module.cr_namespace.aws_cleanrooms_id_mapping_table.mapping_table[0] \
  membership/6610c9aa-9002-475c-8695-d833485741bc/idmappingtable/8b7d3c1e-d7ee-4def-9d71-fe989cc09025
```

