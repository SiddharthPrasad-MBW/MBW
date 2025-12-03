# Identity Resolution Service Resource Discovery

This document contains the discovered Identity Resolution Service resources in production.

## Discovered Resources

### ID Namespace Association

- **Name**: `ACXIdNamespace`
- **ID**: `0fa7a3e6-43fb-41ad-b96b-9f2e9b6037ad` ⚠️ **UPDATED** (recreated 2025-11-13)
- **ARN**: `arn:aws:cleanrooms:us-east-1:239083076653:membership/6610c9aa-9002-475c-8695-d833485741bc/idnamespaceassociation/0fa7a3e6-43fb-41ad-b96b-9f2e9b6037ad`
- **Entity Resolution Namespace ARN**: `arn:aws:entityresolution:us-east-1:239083076653:idnamespace/ACXIdNamespace`
- **Membership ID**: `6610c9aa-9002-475c-8695-d833485741bc`
- **Collaboration ID**: `27b93e2b-5001-4b20-a47b-6aad96ec8958`
- **Description**: `ACX unique customer identifiers for Clean Rooms joins` ⚠️ **NEW**
- **Manage Resource Policies**: `true`
- **Allow Use As Dimension Column**: `false`
- **Created**: `2025-11-13 14:28:27.546000-08:00` ⚠️ **RECREATED**
- **Updated**: `2025-11-13 14:28:27.546000-08:00`

### ID Mapping Table

⚠️ **STATUS**: No ID mapping tables currently exist in the collaboration.

**Previous Configuration** (removed):
- **Name**: `acx-real_ids`
- **ID**: `8b7d3c1e-d7ee-4def-9d71-fe989cc09025` (deleted)
- **Entity Resolution Workflow**: `ACX-Real_IDS` (no longer exists)

**Note**: ID mapping table and workflow were removed. If needed, they can be recreated using the `create-cr-namespace-resources.py` script.

### Entity Resolution Resources

#### ID Namespace

- **Name**: `ACXIdNamespace`
- **ARN**: `arn:aws:entityresolution:us-east-1:239083076653:idnamespace/ACXIdNamespace`
- **Type**: `SOURCE`
- **Description**: `ACX unique customer identifiers for Clean Rooms joins`
- **Role ARN**: `arn:aws:iam::239083076653:role/omc-flywheel-prod-ER-SourceIdNamespaceRole`
- **Created**: `2025-11-13 14:24:59.494000-08:00` ⚠️ **RECREATED**
- **Updated**: `2025-11-13 14:24:59.494000-08:00`

**Input Source Config:**
- **Input Source ARN**: `arn:aws:glue:us-east-1:239083076653:table/omc_flywheel_prod/part_addressable_ids_er`
- **Schema Name**: `ACX_SCHEMA`

**ID Mapping Workflow Properties:**
- **ID Mapping Type**: `RULE_BASED`
- **Attribute Matching Model**: `ONE_TO_ONE`
- **Record Matching Models**: `["ONE_SOURCE_TO_ONE_TARGET"]`
- **Rule Definition Types**: `["TARGET"]`

**Resource Policy:**
- Allows Cleanrooms service from account `921290734397` to:
  - `entityresolution:GetIdNamespace`
  - `entityresolution:ListIdNamespaces`
  - `entityresolution:StartIdMappingJob`

#### Schema Mapping

- **Schema Name**: `ACX_SCHEMA`
- **ARN**: `arn:aws:entityresolution:us-east-1:239083076653:schemamapping/ACX_SCHEMA`
- **Created**: `2025-11-13 13:55:52.646000-08:00`
- **Updated**: `2025-11-13 13:55:52.646000-08:00`
- **Has Workflows**: `false`

**Mapped Input Fields:**
1. **Field**: `customer_user_id`
   - **Type**: `UNIQUE_ID`
   - **Match Key**: `AML`
   - **Hashed**: `false`

2. **Field**: `email`
   - **Type**: `EMAIL_ADDRESS`
   - **Match Key**: `EMAIL`
   - **Hashed**: `false`

#### ID Mapping Workflow

⚠️ **STATUS**: No ID mapping workflows currently exist.

**Previous Configuration** (removed):
- **Name**: `ACX-Real_IDS`
- **ARN**: `arn:aws:entityresolution:us-east-1:239083076653:idmappingworkflow/ACX-Real_IDS` (deleted)

**Note**: Workflow was removed. If needed, it can be recreated in Entity Resolution Service.

## IAM Resources

### Entity Resolution Role

- **Role Name**: `omc-flywheel-prod-ER-SourceIdNamespaceRole`
- **Role ARN**: `arn:aws:iam::239083076653:role/omc-flywheel-prod-ER-SourceIdNamespaceRole`
- **Created**: `2025-11-12 20:25:56+00:00`
- **Purpose**: IAM role for Entity Resolution Service to access S3 and Glue resources
- **Trust Policy**: Allows `entityresolution.amazonaws.com` service to assume the role
- **Attached Policy**: `omc-flywheel-prod-cr-entity-resolution-source`

### Entity Resolution Policy

- **Policy Name**: `omc-flywheel-prod-cr-entity-resolution-source`
- **Policy ARN**: `arn:aws:iam::239083076653:policy/omc-flywheel-prod-cr-entity-resolution-source`
- **Created**: `2025-11-12 20:24:56+00:00`
- **Last Updated**: `2025-11-14 14:13:12+00:00` ⚠️ **UPDATED**
- **Purpose**: Provides S3 and Glue access for Entity Resolution Service
- **Permissions**:
  - **S3 List/Read**:
    - `omc_cleanroom_data/identity/*` ⚠️ **NEW**
    - `omc_cleanroom_data/split_part/addressable_ids/*`
    - `omc_cleanroom_data/entity_resolution/output/*`
  - **S3 Read**:
    - `omc_cleanroom_data/identity/*` ⚠️ **NEW**
    - `omc_cleanroom_data/split_part/addressable_ids/*`
  - **S3 Write**: `omc_cleanroom_data/entity_resolution/output/*`
  - **Glue Read**: Catalog, database, and `part_addressable_ids_er` table ⚠️ **UPDATED** (was `part_addressable_ids`)

**Note**: This policy is attached to `omc-flywheel-prod-ER-SourceIdNamespaceRole` and used by Entity Resolution Service.

### Other OMC Policies Found

1. `omc-flywheel-infobase-transformation-glue-s3-policy`
2. `omc-flywheel-prod-data-monitor-policy`
3. `omc-flywheel-reference-tables-crawler-s3-policy`
4. `omc-flywheel-reference-tables-glue-s3-policy`
5. `omc-flywheel-transformed-crawler-s3-policy`
6. `omc_flywheel-prod-glue-role-s3-access`

### Roles Found

- `AWSGlueServiceRole-OMC-Flywheel` (Glue service role)
- `omc-flywheel-prod-ER-SourceIdNamespaceRole` ⚠️ **NEW** (Entity Resolution Service role)

## Naming Conventions

- **ID Namespace Association**: `ACXIdNamespace` (matches Entity Resolution namespace name)
- **ID Mapping Table**: `acx-real_ids` (lowercase with underscores, matches workflow name pattern)
- **IAM Policy**: `omc-flywheel-prod-cr-entity-resolution-source` (follows existing OMC policy naming)
- **No Conflicts**: These names are unique and don't conflict with:
  - Configured tables: `part_*`
  - Collaboration associations: `acx_part_*`
  - Other IAM resources

## Current State Summary

### Active Resources
- ✅ **ID Namespace Association**: `ACXIdNamespace` (ID: `0fa7a3e6-43fb-41ad-b96b-9f2e9b6037ad`)
- ✅ **Entity Resolution Namespace**: `ACXIdNamespace`
- ✅ **Collaboration**: Both ACX and AMC namespaces are associated

### Removed Resources
- ❌ **ID Mapping Table**: `acx-real_ids` (removed)
- ❌ **ID Mapping Workflow**: `ACX-Real_IDS` (removed)

### Changes Made

**2025-11-13:**
- ID namespace association was recreated (new ID, added description)
- Entity Resolution namespace was recreated with:
  - Type: SOURCE
  - Input source: `part_addressable_ids_er` Glue table
  - Schema mapping: `ACX_SCHEMA`
  - ID mapping workflow properties: RULE_BASED with ONE_TO_ONE matching
- Schema mapping `ACX_SCHEMA` created with fields:
  - `customer_user_id` (UNIQUE_ID, match key: AML)
  - `email` (EMAIL_ADDRESS, match key: EMAIL)
- ID mapping table and workflow were removed

**2025-11-14:**
- Entity Resolution IAM role created: `omc-flywheel-prod-ER-SourceIdNamespaceRole`
- Entity Resolution policy updated:
  - Added S3 access for `omc_cleanroom_data/identity/*` path
  - Updated Glue table reference from `part_addressable_ids` to `part_addressable_ids_er`
- Resource policy added to ID namespace allowing Cleanrooms access from account `921290734397`

## Usage

To rediscover resources:

```bash
python3 scripts/discover-cr-namespace-resources.py \
  --membership-id 6610c9aa-9002-475c-8695-d833485741bc \
  --profile flywheel-prod \
  --no-verify-ssl
```

To recreate ID mapping table (if needed):

```bash
python3 scripts/create-cr-namespace-resources.py \
  --membership-id 6610c9aa-9002-475c-8695-d833485741bc \
  --profile flywheel-prod \
  --id-namespace-name ACXIdNamespace \
  --id-namespace-arn arn:aws:entityresolution:us-east-1:239083076653:idnamespace/ACXIdNamespace \
  --id-namespace-description "ACX unique customer identifiers for Clean Rooms joins" \
  --id-mapping-table-name acx-real_ids \
  --id-mapping-workflow-arn <workflow-arn> \
  --target-namespace-association-id 3ff4df8f-f33c-4e04-8a34-0f8974cb627d \
  --no-verify-ssl
```

