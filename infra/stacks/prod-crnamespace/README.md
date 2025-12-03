# Production Cleanrooms Identity Resolution Service Stack

This stack manages Identity Resolution Service resources for the production Cleanrooms collaboration, including ID namespace associations and ID mapping tables.

## Resources Managed

- **ID Namespace Association**: `ACXIdNamespace`
  - Links Entity Resolution ID namespace to Cleanrooms membership
  - References: `arn:aws:entityresolution:us-east-1:239083076653:idnamespace/ACXIdNamespace`
  - Description: `ACX unique customer identifiers for Clean Rooms joins`
  - Current ID: `0fa7a3e6-43fb-41ad-b96b-9f2e9b6037ad` (updated 2025-11-13)

- **ID Mapping Table**: ⚠️ **Not Currently Configured**
  - Previously: `acx-real_ids` (removed)
  - Can be recreated if needed using the create script

## Prerequisites

1. **Entity Resolution Resources** (must exist):
   - ID Namespace: `ACXIdNamespace` ✅ (exists)
   - ID Mapping Workflow: ⚠️ Not currently configured (can be created if needed)

2. **Cleanrooms Membership**: `6610c9aa-9002-475c-8695-d833485741bc` ✅

3. **Target ID Namespace**: AMC's ID namespace association must exist in the collaboration ✅
   - AMCIdNamespace ID: `3ff4df8f-f33c-4e04-8a34-0f8974cb627d`

## ⚠️  Important: Terraform Provider Limitation

**The Terraform AWS provider does NOT currently support Cleanrooms Identity Resolution Service resources.**

Use the Python scripts to manage these resources:
- `scripts/create-cr-namespace-resources.py` - Create/update resources
- `scripts/discover-cr-namespace-resources.py` - Discover existing resources

## Usage

### Using Python Scripts (Current Method)

#### Discover Existing Resources

```bash
python3 scripts/discover-cr-namespace-resources.py \
  --membership-id 6610c9aa-9002-475c-8695-d833485741bc \
  --profile flywheel-prod \
  --no-verify-ssl
```

#### Create/Update Resources

```bash
# Create/update ID namespace association only (current state)
python3 scripts/create-cr-namespace-resources.py \
  --membership-id 6610c9aa-9002-475c-8695-d833485741bc \
  --profile flywheel-prod \
  --id-namespace-name ACXIdNamespace \
  --id-namespace-arn arn:aws:entityresolution:us-east-1:239083076653:idnamespace/ACXIdNamespace \
  --id-namespace-description "ACX unique customer identifiers for Clean Rooms joins" \
  --no-verify-ssl

# To add ID mapping table (if workflow exists):
# python3 scripts/create-cr-namespace-resources.py \
#   --membership-id 6610c9aa-9002-475c-8695-d833485741bc \
#   --profile flywheel-prod \
#   --id-namespace-name ACXIdNamespace \
#   --id-namespace-arn arn:aws:entityresolution:us-east-1:239083076653:idnamespace/ACXIdNamespace \
#   --id-namespace-description "ACX unique customer identifiers for Clean Rooms joins" \
#   --id-mapping-table-name acx-real_ids \
#   --id-mapping-workflow-arn <workflow-arn> \
#   --source-namespace-association-id 0fa7a3e6-43fb-41ad-b96b-9f2e9b6037ad \
#   --target-namespace-association-id 3ff4df8f-f33c-4e04-8a34-0f8974cb627d \
#   --no-verify-ssl
```

### Using Terraform (Future - When Provider Support is Added)

#### Initialize

```bash
cd infra/stacks/prod-crnamespace
terraform init
```

#### Plan (Dry Run)

```bash
terraform plan
```

#### Apply

```bash
terraform apply
```

#### Import Existing Resources

If resources already exist in AWS, import them (when provider support is added):

```bash
# Import ID namespace association
terraform import module.cr_namespace.aws_cleanrooms_id_namespace_association.namespace \
  membership/6610c9aa-9002-475c-8695-d833485741bc/idnamespaceassociation/5333558b-e6b8-4557-94a4-261d20294a20

# Import ID mapping table
terraform import module.cr_namespace.aws_cleanrooms_id_mapping_table.mapping_table[0] \
  membership/6610c9aa-9002-475c-8695-d833485741bc/idmappingtable/8b7d3c1e-d7ee-4def-9d71-fe989cc09025
```

## Verification

### Check ID Namespace Association

```bash
aws cleanrooms get-id-namespace-association \
  --membership-identifier 6610c9aa-9002-475c-8695-d833485741bc \
  --id-namespace-association-identifier 5333558b-e6b8-4557-94a4-261d20294a20 \
  --profile flywheel-prod \
  --region us-east-1
```

### Check ID Mapping Table

```bash
aws cleanrooms get-id-mapping-table \
  --membership-identifier 6610c9aa-9002-475c-8695-d833485741bc \
  --id-mapping-table-identifier 8b7d3c1e-d7ee-4def-9d71-fe989cc09025 \
  --profile flywheel-prod \
  --region us-east-1
```

### List All Resources

```bash
# List ID namespace associations
aws cleanrooms list-id-namespace-associations \
  --membership-identifier 6610c9aa-9002-475c-8695-d833485741bc \
  --profile flywheel-prod \
  --region us-east-1

# List ID mapping tables
aws cleanrooms list-id-mapping-tables \
  --membership-identifier 6610c9aa-9002-475c-8695-d833485741bc \
  --profile flywheel-prod \
  --region us-east-1
```

## IAM Resources

### Entity Resolution Role

The Entity Resolution Service uses a dedicated IAM role:

- **Role Name**: `omc-flywheel-prod-ER-SourceIdNamespaceRole`
- **Role ARN**: `arn:aws:iam::239083076653:role/omc-flywheel-prod-ER-SourceIdNamespaceRole`
- **Trust Policy**: Allows `entityresolution.amazonaws.com` to assume the role
- **Attached Policy**: `omc-flywheel-prod-cr-entity-resolution-source`

This role is referenced in the Entity Resolution namespace configuration and provides access to:
- S3 paths: `identity/*`, `split_part/addressable_ids/*`, `entity_resolution/output/*`
- Glue table: `part_addressable_ids_er`

## Important Notes

1. **Terraform Provider Support**: The Terraform AWS provider may not fully support all Cleanrooms Identity Resolution resources. If you encounter errors, you may need to use boto3 scripts similar to configured tables.

2. **Dependencies**: 
   - ID mapping table depends on ID namespace association
   - Target ID namespace (AMC) must exist before creating ID mapping table
   - Entity Resolution namespace requires IAM role: `omc-flywheel-prod-ER-SourceIdNamespaceRole`

3. **Naming**: 
   - ID namespace association: `ACXIdNamespace` (matches existing)
   - ID mapping table: `acx-real_ids` (matches existing)
   - IAM role: `omc-flywheel-prod-ER-SourceIdNamespaceRole` (Entity Resolution)

4. **No Conflicts**: This stack uses unique names that don't conflict with other resources:
   - Module name: `cr_namespace` (different from `crconfigtables`)
   - Stack directory: `prod-crnamespace` (different from `prod-crconfigtables`)

## Troubleshooting

### Error: Resource Not Found

If Entity Resolution resources don't exist:
1. Create ID namespace in Entity Resolution Service console
2. Create ID mapping workflow in Entity Resolution Service console
3. Update ARNs in `variables.tf` if different

### Error: Provider Doesn't Support Resource

If Terraform provider doesn't support the resource:
1. Check AWS provider version (requires >= 5.0)
2. May need to use boto3 script for resource management
3. See `scripts/` directory for examples

### Error: Target ID Namespace Not Found

If target ID namespace association doesn't exist:
1. Verify AMC has created their ID namespace association
2. Get the association ID from collaboration
3. Update `target_id_namespace_association_id` in `variables.tf`

