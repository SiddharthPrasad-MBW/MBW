# Collaboration Invitation Management Guide

## Overview

This guide explains how to programmatically manage AWS Cleanrooms collaboration invitations and automatically associate existing resources (configured tables and ID namespaces) to new collaborations.

## Problem Statement

When receiving 10+ collaboration invitations, manually:
1. Accepting each invitation
2. Associating configured tables
3. Associating ID namespace

...becomes time-consuming and error-prone.

## Solution

We provide two Python scripts to automate this process:

1. **`manage-collaboration-invites.py`** - Core script for individual operations
2. **`manage-multiple-collaborations.py`** - High-level script for managing 10+ collaborations

## Prerequisites

### Required Resources

Before using these scripts, ensure you have:

1. **Configured Tables** - Already created in Cleanrooms
   - Check: `aws cleanrooms list-configured-tables --profile flywheel-prod`

2. **ID Namespace** - Entity Resolution namespace exists
   - Default: `ACXIdNamespace`
   - ARN: `arn:aws:entityresolution:us-east-1:239083076653:idnamespace/ACXIdNamespace`

3. **IAM Role** - For Cleanrooms to access Glue/S3
   - Default: `cleanrooms-glue-s3-access`
   - Must have permissions for Glue tables and S3 buckets

### Required Permissions

Your AWS credentials need:
- `cleanrooms:*` - Full Cleanrooms access
- `glue:GetTable`, `glue:GetTables` - Read Glue catalog
- `iam:GetRole` - Read IAM role ARN
- `entityresolution:GetIdNamespace` - Read Entity Resolution namespace

## Quick Start

### 1. List Pending Invitations

```bash
python3 scripts/manage-collaboration-invites.py list \
    --profile flywheel-prod
```

**Output:**
```
📋 Found 3 pending invitation(s):

  Collaboration: AMC Collaboration
    ID: 27b93e2b-5001-4b20-a47b-6aad96ec8958
    Creator: AMC (921290734397)
    Membership ID: 6610c9aa-9002-475c-8695-d833485741bc
    Created: 2025-11-18T10:00:00Z
```

### 2. Accept Single Invitation

```bash
python3 scripts/manage-collaboration-invites.py accept \
    --collaboration-id 27b93e2b-5001-4b20-a47b-6aad96ec8958 \
    --profile flywheel-prod \
    --auto-associate
```

This will:
- ✅ Accept the invitation
- ✅ Associate all configured tables
- ✅ Associate the ID namespace

### 3. Accept All Pending Invitations

```bash
python3 scripts/manage-collaboration-invites.py accept-all \
    --profile flywheel-prod \
    --auto-associate
```

### 4. Associate Resources to Existing Membership

If you've already accepted an invitation manually:

```bash
python3 scripts/manage-collaboration-invites.py associate \
    --membership-id 6610c9aa-9002-475c-8695-d833485741bc \
    --profile flywheel-prod
```

## Managing 10+ Collaborations

For managing multiple collaborations, use the configuration-based approach:

### Step 1: Initialize Configuration

```bash
python3 scripts/manage-multiple-collaborations.py init-config \
    --config collaboration-config.json
```

This creates a `collaboration-config.json` file with default settings.

### Step 2: Process All Pending Invitations

```bash
python3 scripts/manage-multiple-collaborations.py process-invites \
    --config collaboration-config.json \
    --profile flywheel-prod
```

This will:
1. List all pending invitations from AWS
2. Accept each invitation
3. Add to configuration file
4. Auto-associate tables and namespace
5. Update configuration with results

### Step 3: Sync All Active Collaborations

To ensure all active collaborations have resources associated:

```bash
python3 scripts/manage-multiple-collaborations.py sync-all \
    --config collaboration-config.json \
    --profile flywheel-prod
```

### Step 4: List Managed Collaborations

```bash
python3 scripts/manage-multiple-collaborations.py list \
    --config collaboration-config.json
```

### Step 5: Manually Add Collaboration

If you need to add a collaboration that was accepted outside the script:

```bash
python3 scripts/manage-multiple-collaborations.py add \
    --membership-id 6610c9aa-9002-475c-8695-d833485741bc \
    --name "AMC Collaboration" \
    --collaboration-id 27b93e2b-5001-4b20-a47b-6aad96ec8958 \
    --config collaboration-config.json
```

## Configuration File Structure

The `collaboration-config.json` file structure:

```json
{
  "defaults": {
    "region": "us-east-1",
    "role_name": "cleanrooms-glue-s3-access",
    "id_namespace_name": "ACXIdNamespace",
    "id_namespace_arn": "arn:aws:entityresolution:us-east-1:239083076653:idnamespace/ACXIdNamespace",
    "table_prefix": "part_",
    "database": "omc_flywheel_prod",
    "allowed_query_providers": [
      "921290734397",
      "657425294073"
    ]
  },
  "collaborations": [
    {
      "name": "AMC Collaboration",
      "collaboration_id": "27b93e2b-5001-4b20-a47b-6aad96ec8958",
      "membership_id": "6610c9aa-9002-475c-8695-d833485741bc",
      "status": "active",
      "auto_associate_tables": true,
      "auto_associate_namespace": true,
      "allowed_query_providers": [
        "921290734397",
        "657425294073"
      ],
      "notes": "Primary AMC collaboration"
    }
  ],
  "pending_invitations": []
}
```

## What Gets Associated

### Configured Tables

All existing configured tables are associated with the naming convention:
- **Association Name**: `acx_{table_name}`
- **Example**: Table `part_ibe_01` → Association `acx_part_ibe_01`

The script:
1. Lists all configured tables
2. Creates associations for each table
3. Skips if association already exists (idempotent)

### ID Namespace

The default ID namespace is associated:
- **Name**: `ACXIdNamespace`
- **ARN**: From configuration file
- **Description**: "ACX unique customer identifiers for Clean Rooms joins"

## Integration with Terraform

### Option 1: Use Scripts Only

For new collaborations, use the scripts to:
1. Accept invitations
2. Associate resources

Terraform continues to manage the base resources (configured tables, IAM roles).

### Option 2: Hybrid Approach

1. **Terraform** manages:
   - Configured tables creation
   - IAM roles
   - Base infrastructure

2. **Scripts** manage:
   - Invitation acceptance
   - Table associations (per membership)
   - Namespace associations (per membership)

### Option 3: Terraform with Multiple Stacks

For each new collaboration, you could create a new Terraform stack:

```bash
# Create stack for new collaboration
cp -r infra/stacks/prod-crconfigtables infra/stacks/prod-crconfigtables-collab2

# Update variables
cd infra/stacks/prod-crconfigtables-collab2
terraform init
terraform apply -var="cleanrooms_membership_id=<new-membership-id>"
```

**Note**: This approach scales poorly for 10+ collaborations.

## Workflow Examples

### Scenario 1: New Collaboration Invitation

```bash
# 1. List pending invitations
python3 scripts/manage-collaboration-invites.py list --profile flywheel-prod

# 2. Accept and auto-associate (gets membership ID automatically)
python3 scripts/manage-collaboration-invites.py accept \
    --collaboration-id <id> \
    --profile flywheel-prod \
    --auto-associate

# This will:
# - Accept the invitation
# - Discover all part_* tables (excluding n_a tables)
# - Limit to 25 tables (quota)
# - Create associations with names: acx_<table_name>
# - Create collaboration analysis rules automatically
# - Associate ID namespace

# 3. Verify
aws cleanrooms list-configured-table-associations \
    --membership-identifier <membership-id> \
    --profile flywheel-prod
```

**Note:** The script automatically:
- Filters for `part_*` tables only (excludes `part_n_a`, `part_n_a_a`)
- Limits to 25 associations (AWS quota)
- Uses correct role: `cleanrooms-glue-s3-access`
- Creates collaboration analysis rules with correct result receivers

### Scenario 2: Bulk Processing (10+ Invitations)

```bash
# 1. Initialize config (first time only)
python3 scripts/manage-multiple-collaborations.py init-config

# 2. Process all pending invitations
python3 scripts/manage-multiple-collaborations.py process-invites \
    --config collaboration-config.json \
    --profile flywheel-prod

# 3. Verify all collaborations
python3 scripts/manage-multiple-collaborations.py list \
    --config collaboration-config.json
```

### Scenario 3: Associate to Existing Membership

If you have an existing membership and need to associate resources:

```bash
# Associate resources to existing membership
python3 scripts/manage-collaboration-invites.py associate \
    --membership-id <membership-id> \
    --profile flywheel-prod

# This will:
# - Discover all part_* tables (excluding n_a)
# - Create associations (skips if already exist)
# - Create collaboration analysis rules
# - Associate ID namespace
```

### Scenario 4: Fix Existing Associations (One-Time)

If associations have wrong names (using table IDs instead of names):

```bash
# Use the fix script (one-time operation)
python3 scripts/fix-collaboration-associations.py \
    --membership-id <membership-id> \
    --profile flywheel-prod

# This will:
# - Delete all existing associations
# - Recreate with correct names (acx_<table_name>)
# - Limit to 25 tables (quota)
```

### Scenario 5: Sync Existing Collaborations

If you've added new configured tables and need to associate them to all existing collaborations:

```bash
# Sync all active collaborations
python3 scripts/manage-multiple-collaborations.py sync-all \
    --config collaboration-config.json \
    --profile flywheel-prod
```

## Troubleshooting

### Error: "Membership not found"

**Cause**: Invitation not yet accepted or membership ID incorrect.

**Solution**:
1. Verify invitation status: `aws cleanrooms list-memberships`
2. Accept invitation manually if needed
3. Use correct membership ID

### Error: "Association already exists"

**Status**: ✅ Normal - Script is idempotent and skips existing associations.

### Error: "Could not find IAM role"

**Cause**: IAM role doesn't exist or wrong name.

**Solution**:
1. Check role exists: `aws iam get-role --role-name cleanrooms-glue-s3-access`
2. Update default role name in script or config file
3. Create role via Terraform if missing

### Error: "ID namespace not found"

**Cause**: Entity Resolution namespace doesn't exist.

**Solution**:
1. Verify namespace: `aws entityresolution get-id-namespace --id-namespace-name ACXIdNamespace`
2. Update ARN in configuration file if different
3. Create namespace if missing

### Invitation Acceptance Fails

**Note**: AWS Cleanrooms API may not support programmatic invitation acceptance in all cases.

**Workaround**:
1. Accept invitation manually in AWS Console
2. Get membership ID: `aws cleanrooms list-memberships`
3. Use `associate` command to add resources

## Best Practices

1. **Always verify before bulk operations**
   ```bash
   # List first
   python3 scripts/manage-collaboration-invites.py list --profile flywheel-prod
   ```

2. **Use configuration file for 5+ collaborations**
   - Easier to track and manage
   - Can be version controlled
   - Supports bulk operations

3. **Regular syncs**
   - Run `sync-all` after adding new configured tables
   - Ensures all collaborations have latest resources

4. **Monitor associations**
   ```bash
   # Check associations for a membership
   aws cleanrooms list-configured-table-associations \
       --membership-identifier <membership-id> \
       --profile flywheel-prod
   ```

5. **Version control configuration**
   - Commit `collaboration-config.json` to git
   - Track collaboration changes over time

## Limitations

1. **Invitation Acceptance**: AWS API may require manual acceptance in some cases
2. **Analysis Rules**: Scripts don't create collaboration analysis rules (use separate scripts)
3. **ID Mapping Tables**: Not automatically created (use `create-cr-namespace-resources.py`)

## Related Scripts

- `create-cr-namespace-resources.py` - Create ID namespace associations and mapping tables
- `add-collaboration-analysis-rules.py` - Add collaboration analysis rules
- `verify-collaboration-table-config.py` - Verify table configurations

## Next Steps

1. **Automate with CI/CD**: Add scripts to deployment pipeline
2. **Scheduled Syncs**: Run `sync-all` periodically via cron/Lambda
3. **Monitoring**: Track collaboration status and associations
4. **Alerting**: Notify on failed associations or pending invitations

---

**Last Updated**: November 18, 2025  
**Scripts**: `manage-collaboration-invites.py`, `manage-multiple-collaborations.py`

