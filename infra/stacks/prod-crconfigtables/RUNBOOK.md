# Cleanrooms Configured Tables - Runbook

This runbook provides step-by-step instructions for managing Cleanrooms configured tables, including adding membership associations and partner AWS accounts.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Adding Membership Association](#adding-membership-association)
- [Analysis Provider Configuration](#analysis-provider-configuration)
- [Column Management](#column-management)
- [Verification Steps](#verification-steps)
- [Updating Existing Configuration](#updating-existing-configuration)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Access
- AWS CLI configured with `flywheel-prod` profile
- Terraform >= 1.0 installed
- Access to AWS Cleanrooms console
- IAM permissions to manage Cleanrooms resources

### Required Information
Before starting, gather:
- **Cleanrooms Membership ID**: From AWS Cleanrooms console (format: `membership-xxxxxxxxxxxx`)
- **Partner AWS Account IDs**: List of AWS account IDs allowed to submit queries
- **Glue Database Name**: `omc_flywheel_prod` (default)
- **S3 Bucket Name**: `omc-flywheel-data-us-east-1-prod` (default)

### Verify Current State
```bash
cd infra/stacks/prod-crconfigtables
terraform init
terraform plan
```

---

## Initial Setup

### Step 1: Initialize Terraform (First Time Only)

```bash
cd infra/stacks/prod-crconfigtables
terraform init
```

### Step 2: Review Current Configuration

```bash
# Check current variables
cat variables.tf

# Check what will be created
terraform plan
```

### Step 3: Apply Without Membership (Safe Initial State)

This creates all configured tables but does NOT associate them with a membership:

```bash
terraform apply
```

**Expected Output:**
- ✅ 28 configured tables created
- ✅ IAM role created (`cleanrooms-glue-s3-access`)
- ✅ CUSTOM analysis rules configured
- ⚠️ No membership associations (safe to proceed)

---

## Adding Membership Association

### Step 1: Get Cleanrooms Membership ID

#### Option A: From AWS Console
1. Navigate to **AWS Cleanrooms** console
2. Go to **Collaborations** or **Memberships**
3. Find your membership
4. Copy the **Membership ID** (format: `membership-xxxxxxxxxxxx`)

#### Option B: From AWS CLI
```bash
aws cleanrooms list-memberships \
  --profile flywheel-prod \
  --region us-east-1 \
  --query 'membershipSummaries[*].{MembershipId:membershipId,Name:name}' \
  --output table
```

### Step 2: Apply with Membership ID

```bash
terraform apply \
  -var="cleanrooms_membership_id=membership-xxxxxxxxxxxx"
```

**Expected Output:**
- ✅ All configured tables associated with membership
- ✅ Association IDs created for each table
- ✅ Tables now available in Cleanrooms collaboration

### Step 3: Verify Association

```bash
# Check Terraform outputs
terraform output cleanrooms_tables

# Or verify via AWS CLI
aws cleanrooms list-configured-table-associations \
  --membership-identifier membership-xxxxxxxxxxxx \
  --profile flywheel-prod \
  --region us-east-1 \
  --output table
```

**Note:** Association names use the `acx_` prefix convention (e.g., `acx_part_ibe_01`, `acx_part_miacs_04`). This provides clear identification of Acxiom-managed collaboration associations.

---

## Analysis Provider Configuration

### Current Default Providers

All configured tables use the following analysis providers by default:
- **`921290734397`** - AMC Service (defines analyses/queries)
- **`657425294073`** - Query Submitter/AMC Results Receiver (runs analyses and receives results)

### Verifying Analysis Providers

To verify all tables have the correct analysis providers:
```bash
python3 scripts/verify-collaboration-table-config.py \
  --membership-id 6610c9aa-9002-475c-8695-d833485741bc \
  --profile flywheel-prod
```

This script checks:
- All tables have both analysis providers configured
- No extra providers are present
- Collaboration analysis rules have correct result receivers

### Updating Analysis Providers

To update all configured tables to use specific analysis providers:
```bash
python3 scripts/update-configured-table-analysis-providers.py \
  --profile flywheel-prod \
  --membership-id 6610c9aa-9002-475c-8695-d833485741bc
```

**Options:**
- `--verify-only` - Only verify, don't make changes
- `--dry-run` - Show what would be done without making changes
- `--table <name>` - Process only a specific table

---

## Adding Partner AWS Accounts (Legacy)

### Step 1: Gather Partner Account IDs

Collect AWS account IDs from your partners:
- Format: 12-digit number (e.g., `123456789012`)
- Multiple accounts: Use comma-separated list

**Example:**
```
Partner 1: 123456789012
Partner 2: 987654321098
Partner 3: 555555555555
```

### Step 2: Update Terraform Variables

#### Option A: Command Line (Recommended)
```bash
terraform apply \
  -var="cleanrooms_membership_id=membership-xxxxxxxxxxxx" \
  -var='cleanrooms_allowed_query_providers=["921290734397","657425294073"]'
```

**Default Analysis Providers:**
- `921290734397` - AMC Service (defines analyses/queries)
- `657425294073` - Query Submitter/AMC Results Receiver (runs analyses and receives results)

**Note:** The Terraform default now includes both providers. You only need to override if you want different providers.

#### Option B: Terraform Variables File
Create or update `terraform.tfvars`:
```hcl
cleanrooms_membership_id = "membership-xxxxxxxxxxxx"
cleanrooms_allowed_query_providers = [
  "921290734397",  # AMC Service
  "657425294073"   # Query Submitter/AMC Results Receiver
]
```

Then apply:
```bash
terraform apply -var-file=terraform.tfvars
```

### Step 3: Verify Partner Accounts

```bash
# Check analysis rules
aws cleanrooms get-configured-table-analysis-rule \
  --configured-table-identifier <table-id> \
  --analysis-rule-type CUSTOM \
  --profile flywheel-prod \
  --region us-east-1 \
  --query 'analysisRule.custom.allowedQueryProviders' \
  --output table
```

---

## Complete Workflow Example

### Scenario: Adding New Collaboration

```bash
# 1. Navigate to stack directory
cd infra/stacks/prod-crconfigtables

# 2. Initialize (if first time)
terraform init

# 3. Get membership ID
MEMBERSHIP_ID=$(aws cleanrooms list-memberships \
  --profile flywheel-prod \
  --region us-east-1 \
  --query 'membershipSummaries[0].membershipId' \
  --output text)

echo "Membership ID: $MEMBERSHIP_ID"

# 4. Apply with membership and partner accounts
terraform apply \
  -var="cleanrooms_membership_id=$MEMBERSHIP_ID" \
  -var='cleanrooms_allowed_query_providers=["921290734397","657425294073"]'

# 5. Verify outputs
terraform output cleanrooms_tables
```

---

## Verification Steps

### 1. Verify Configured Tables

```bash
# List all configured tables
aws cleanrooms list-configured-tables \
  --profile flywheel-prod \
  --region us-east-1 \
  --query 'configuredTableSummaries[*].{Name:name,Id:configuredTableId}' \
  --output table
```

### 2. Verify Table Associations

```bash
# List associations for a membership
aws cleanrooms list-configured-table-associations \
  --membership-identifier membership-xxxxxxxxxxxx \
  --profile flywheel-prod \
  --region us-east-1 \
  --output table
```

### 3. Verify Analysis Rules

```bash
# Check CUSTOM rule for a specific table
aws cleanrooms get-configured-table-analysis-rule \
  --configured-table-identifier <table-id> \
  --analysis-rule-type CUSTOM \
  --profile flywheel-prod \
  --region us-east-1 \
  --output json | jq '.analysisRule.custom.allowedQueryProviders'
```

### 4. Verify IAM Role

```bash
# Check IAM role exists
aws iam get-role \
  --role-name cleanrooms-glue-s3-access \
  --profile flywheel-prod \
  --output json | jq '.Role.RoleName'
```

### 5. Verify Terraform State

```bash
# List all resources in state
terraform state list

# Show specific resource
terraform state show module.cleanrooms_tables.aws_cleanrooms_configured_table.ct[\"part_ibe_01\"]
```

---

## Association Naming Convention

### Current Naming Standard

All collaboration associations use the `acx_` prefix convention:
- **Format**: `acx_{table_name}`
- **Examples**: 
  - `acx_part_ibe_01`
  - `acx_part_miacs_04`
  - `acx_part_new_borrowers`

### Migrating Existing Associations

If you have associations using the old naming convention (`part_*-assoc`), use the migration script:

```bash
# Preview changes (dry-run)
python3 scripts/refresh-collaboration-associations.py \
  --membership-id <membership-id> \
  --profile flywheel-prod \
  --dry-run \
  --no-verify-ssl

# Perform migration
python3 scripts/refresh-collaboration-associations.py \
  --membership-id <membership-id> \
  --profile flywheel-prod \
  --no-verify-ssl
```

The script will:
1. Delete old collaboration analysis rules
2. Delete old associations
3. Create new associations with `acx_` prefix
4. Recreate collaboration analysis rules

**Note:** The script is idempotent and safe to run multiple times.

---

## Updating Existing Configuration

### Verifying Analysis Providers

Use the verification script to check all tables:
```bash
python3 scripts/verify-collaboration-table-config.py \
  --membership-id 6610c9aa-9002-475c-8695-d833485741bc \
  --profile flywheel-prod
```

### Updating Analysis Providers

To update all configured tables to use specific analysis providers:
```bash
python3 scripts/update-configured-table-analysis-providers.py \
  --profile flywheel-prod \
  --membership-id 6610c9aa-9002-475c-8695-d833485741bc
```

**Current Default Providers:**
- `921290734397` - AMC Service
- `657425294073` - Query Submitter/AMC Results Receiver

### Adding More Partner Accounts

```bash
# Add new account to existing list
terraform apply \
  -var="cleanrooms_membership_id=membership-xxxxxxxxxxxx" \
  -var='cleanrooms_allowed_query_providers=["921290734397","657425294073","NEW_ACCOUNT_ID"]'
```

**Note:** After updating Terraform, you'll need to update existing configured tables using the Python script:
```bash
python3 scripts/update-configured-table-analysis-providers.py \
  --profile flywheel-prod \
  --membership-id <membership-id>
```

### Changing Membership

```bash
# Update to new membership ID
terraform apply \
  -var="cleanrooms_membership_id=membership-NEW_ID" \
  -var='cleanrooms_allowed_query_providers=["921290734397","657425294073"]'
```

### Removing Partner Accounts

```bash
# Remove accounts by updating list (remove account from array)
terraform apply \
  -var="cleanrooms_membership_id=membership-xxxxxxxxxxxx" \
  -var='cleanrooms_allowed_query_providers=["921290734397"]'  # Removed other accounts
```

**Note:** After updating Terraform, update existing configured tables using the Python script.

---

## Column Management

### Column Count Limits

Cleanrooms configured tables have a limit of 100 columns. If a Glue table has more than 100 columns (including partition keys), columns will be truncated.

**Solution:** Exclude specific columns that are not needed for Cleanrooms analysis.

**Example:** `part_miacs_02_a` had 101 columns (100 regular + 1 partition key `id_bucket`). The solution was to:
1. Exclude `miacs_11_054` (not needed for analysis)
2. Include `id_bucket` (partition key needed for queries)

**Fixing Column Issues:**
```bash
python3 scripts/fix-miacs-02-a-columns.py \
  --profile flywheel-prod \
  --table part_miacs_02_a \
  --exclude-columns miacs_11_054
```

**Note:** This requires deleting and recreating the configured table, so it will temporarily remove the table from the collaboration.

### Excluded Columns

The following columns are excluded from configured tables:
- `id_bucket` - Partition key, excluded by default (but can be included if needed)
- `miacs_11_054` - Excluded from `part_miacs_02_a` to allow `id_bucket` inclusion

---

## Troubleshooting

### Association Naming Issues

**Problem:** Associations not using `acx_` prefix convention

**Solution:** Run the migration script:
```bash
python3 scripts/refresh-collaboration-associations.py \
  --membership-id <membership-id> \
  --profile flywheel-prod \
  --no-verify-ssl
```

### Direct Analysis Not Ready

**Problem:** Table shows "not ready" for direct analysis

**Solution:** Verify both analysis rules are configured:
1. **Configured Table Analysis Rule** must have `allowedAnalysisProviders` set
   - Required providers: `921290734397` (AMC Service) and `657425294073` (Query Submitter)
   - Verify with: `python3 scripts/verify-collaboration-table-config.py`
2. **Collaboration Analysis Rule** must have `allowedResultReceivers` set
   - Required receivers: `657425294073` (Query Submitter) and `803109464991` (Advertiser)
3. **Empty allowedAnalysisProviders** - The list cannot be empty

Check with:
```bash
# Check configured table rule
aws cleanrooms get-configured-table-analysis-rule \
  --configured-table-identifier <table-id> \
  --analysis-rule-type CUSTOM \
  --profile flywheel-prod

# Check collaboration rule
aws cleanrooms get-configured-table-association-analysis-rule \
  --membership-identifier <membership-id> \
  --configured-table-association-identifier <assoc-id> \
  --analysis-rule-type CUSTOM \
  --profile flywheel-prod
```

## Troubleshooting (Legacy)

### Error: Membership Not Found

**Symptom:**
```
Error: creating Cleanrooms Configured Table Association: InvalidInputException: Membership not found
```

**Solution:**
1. Verify membership ID is correct:
   ```bash
   aws cleanrooms list-memberships --profile flywheel-prod --region us-east-1
   ```
2. Ensure membership exists in the same AWS account
3. Check membership status is `ACTIVE`

### Error: Table Already Exists

**Symptom:**
```
Error: creating Cleanrooms Configured Table: ConflictException: Table already exists
```

**Solution:**
1. Import existing table into Terraform state:
   ```bash
   terraform import module.cleanrooms_tables.aws_cleanrooms_configured_table.ct[\"part_ibe_01\"] <table-id>
   ```
2. Or remove existing table manually and re-apply

### Error: IAM Role Permission Denied

**Symptom:**
```
Error: creating IAM Role: AccessDenied
```

**Solution:**
1. Verify you have IAM permissions
2. Check if role already exists:
   ```bash
   aws iam get-role --role-name cleanrooms-glue-s3-access --profile flywheel-prod
   ```
3. If exists, set `create_role = false` and provide `role_arn`

### Error: S3 Access Denied

**Symptom:**
```
Error: Clean Rooms cannot access S3 bucket
```

**Solution:**
1. Verify S3 bucket ARN in `s3_resources` variable
2. Check IAM role has correct S3 permissions
3. Verify bucket policy allows Clean Rooms role access

### Error: Glue Table Not Found

**Symptom:**
```
Error: reading Glue Catalog Table: EntityNotFoundException
```

**Solution:**
1. Verify table exists in Glue:
   ```bash
   aws glue get-table \
     --database-name omc_flywheel_prod \
     --name part_ibe_01 \
     --profile flywheel-prod \
     --region us-east-1
   ```
2. Ensure table name matches exactly (case-sensitive)
3. Check database name is correct

---

## Best Practices

### 1. Start Without Membership
- Always apply initially without `membership_id` (null)
- This creates tables safely without associations
- Add membership later when ready

### 2. Use Terraform Variables File
- Create `terraform.tfvars` for sensitive values
- Add to `.gitignore` if containing sensitive data
- Use separate files per environment

### 3. Version Control
- Commit Terraform code changes
- Do NOT commit `terraform.tfvars` with sensitive data
- Use separate branches for different configurations

### 4. Incremental Updates
- Add partner accounts incrementally
- Test with one account first
- Verify before adding more

### 5. Regular Verification
- Periodically verify table associations
- Check analysis rules are correct
- Monitor Cleanrooms console for issues

---

## Quick Reference Commands

### Initialize
```bash
cd infra/stacks/prod-crconfigtables
terraform init
```

### Plan (Dry Run)
```bash
terraform plan \
  -var="cleanrooms_membership_id=membership-xxxxxxxxxxxx" \
  -var='cleanrooms_allowed_query_providers=["921290734397","657425294073"]'
```

### Apply
```bash
terraform apply \
  -var="cleanrooms_membership_id=membership-xxxxxxxxxxxx" \
  -var='cleanrooms_allowed_query_providers=["921290734397","657425294073"]'
```

### Show Outputs
```bash
terraform output cleanrooms_tables
```

### List State
```bash
terraform state list
```

### Destroy (Use with Caution!)
```bash
terraform destroy \
  -var="cleanrooms_membership_id=membership-xxxxxxxxxxxx"
```

---

## Support and Documentation

- **AWS Cleanrooms Documentation**: https://docs.aws.amazon.com/cleanrooms/
- **Terraform AWS Provider**: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
- **Module README**: `infra/modules/crconfigtables/README.md`

---

**Last Updated**: 2025-10-31  
**Version**: 1.0  
**Maintained By**: Data Engineering Team

