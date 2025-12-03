# Entity Resolution Service Configuration

This document details the complete configuration of AWS Entity Resolution Service resources for the OMC Flywheel Cleanroom project.

## ID Namespace: ACXIdNamespace

### Basic Information

- **Name**: `ACXIdNamespace`
- **ARN**: `arn:aws:entityresolution:us-east-1:239083076653:idnamespace/ACXIdNamespace`
- **Type**: `SOURCE`
- **Description**: `ACX unique customer identifiers for Clean Rooms joins`
- **IAM Role**: `arn:aws:iam::239083076653:role/omc-flywheel-prod-ER-SourceIdNamespaceRole`
- **Created**: `2025-11-13 14:24:59.494000-08:00`
- **Updated**: `2025-11-13 14:24:59.494000-08:00`

### Input Source Configuration

The ID namespace reads from a Glue table:

- **Input Source ARN**: `arn:aws:glue:us-east-1:239083076653:table/omc_flywheel_prod/part_addressable_ids_er`
- **Schema Name**: `ACX_SCHEMA` (references the schema mapping below)

### ID Mapping Workflow Properties

- **ID Mapping Type**: `RULE_BASED`
- **Attribute Matching Model**: `ONE_TO_ONE`
- **Record Matching Models**: `["ONE_SOURCE_TO_ONE_TARGET"]`
- **Rule Definition Types**: `["TARGET"]`

This configuration means:
- One source record matches to one target record
- Matching is done using rules defined by the target (AMC)
- Attributes are matched one-to-one

### Resource Policy

The ID namespace has a resource policy that allows Cleanrooms service access:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCleanRoomsAMC",
      "Effect": "Allow",
      "Principal": { "Service": "cleanrooms.amazonaws.com" },
      "Action": [
        "entityresolution:GetIdNamespace",
        "entityresolution:ListIdNamespaces",
        "entityresolution:StartIdMappingJob"
      ],
      "Resource": "arn:aws:entityresolution:us-east-1:239083076653:idnamespace/ACXIdNamespace",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "921290734397"
        }
      }
    }
  ]
}
```

This policy allows the Cleanrooms service from account `921290734397` to:
- Get ID namespace details
- List ID namespaces
- Start ID mapping jobs

## Schema Mapping: ACX_SCHEMA

### Basic Information

- **Schema Name**: `ACX_SCHEMA`
- **ARN**: `arn:aws:entityresolution:us-east-1:239083076653:schemamapping/ACX_SCHEMA`
- **Created**: `2025-11-13 13:55:52.646000-08:00`
- **Updated**: `2025-11-13 13:55:52.646000-08:00`
- **Has Workflows**: `false`

### Mapped Input Fields

The schema defines two fields for identity matching:

#### 1. customer_user_id

- **Field Name**: `customer_user_id`
- **Type**: `UNIQUE_ID`
- **Match Key**: `AML`
- **Hashed**: `false`

**Purpose**: Unique customer identifier used for matching. The match key `AML` indicates this is used for identity resolution matching.

#### 2. email

- **Field Name**: `email`
- **Type**: `EMAIL_ADDRESS`
- **Match Key**: `EMAIL`
- **Hashed**: `false`

**Purpose**: Email address used as an additional matching attribute. The match key `EMAIL` indicates this field is used for email-based matching.

## Integration with Cleanrooms

### Cleanrooms ID Namespace Association

The Entity Resolution ID namespace is associated with the Cleanrooms membership:

- **Association Name**: `ACXIdNamespace`
- **Association ID**: `0fa7a3e6-43fb-41ad-b96b-9f2e9b6037ad`
- **Membership ID**: `6610c9aa-9002-475c-8695-d833485741bc`
- **Collaboration ID**: `27b93e2b-5001-4b20-a47b-6aad96ec8958`

This association allows the Cleanrooms collaboration to use the Entity Resolution Service for identity matching between ACX and AMC data.

## IAM Role Configuration

The Entity Resolution Service uses the IAM role `omc-flywheel-prod-ER-SourceIdNamespaceRole` to access:

- **S3 Paths**:
  - `omc_cleanroom_data/identity/*` (read)
  - `omc_cleanroom_data/split_part/addressable_ids/*` (read)
  - `omc_cleanroom_data/entity_resolution/output/*` (write)

- **Glue Table**: `part_addressable_ids_er` (read)

See `RESOURCE_DISCOVERY.md` for full IAM policy details.

## Usage

### Querying ID Namespace

```bash
aws entityresolution get-id-namespace \
  --id-namespace-name ACXIdNamespace \
  --profile flywheel-prod \
  --region us-east-1
```

### Querying Schema Mapping

```bash
aws entityresolution get-schema-mapping \
  --schema-name ACX_SCHEMA \
  --profile flywheel-prod \
  --region us-east-1
```

### Creating ID Mapping Jobs

ID mapping jobs can be started through Cleanrooms when both source and target ID namespaces are configured in the collaboration.

## Notes

- The ID namespace is configured as a `SOURCE` type, meaning it provides source data for matching
- The target (AMC) ID namespace must be configured separately in their account
- The schema mapping defines the structure of identity data used for matching
- The `part_addressable_ids_er` Glue table contains the actual identity data referenced by the namespace

