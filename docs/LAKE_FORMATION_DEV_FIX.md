# Fixing Lake Formation Permissions in Dev

## Problem
The `register-part-tables` job is failing with:
```
Insufficient Lake Formation permission(s): Required Create Table on omc_flywheel_dev
```

**Note:** The database `omc_flywheel_dev` exists, but Lake Formation permissions are blocking:
- Viewing the database (you may see "Insufficient Lake Formation permission(s)" when trying to list it)
- Creating tables in the database
- Altering/dropping tables

Even though `IAM_ALLOWED_PRINCIPALS` is set to ALL permissions, Lake Formation is still blocking because the database was created before that setting, so explicit permissions must be granted.

## Solution: Grant Explicit Permissions

**Option 1: AWS CLI (requires admin access)**

Run these commands with an admin AWS profile:

```bash
export AWS_PROFILE=<admin-profile>
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Step 1: Grant CREATE_TABLE on database
aws lakeformation grant-permissions \
  --region us-east-1 \
  --principal "{\"DataLakePrincipalIdentifier\":\"arn:aws:iam::${ACCOUNT_ID}:role/omc_flywheel-dev-glue-role\"}" \
  --resource "{\"Database\":{\"CatalogId\":\"${ACCOUNT_ID}\",\"Name\":\"omc_flywheel_dev\"}}" \
  --permissions CREATE_TABLE

# Step 2: Grant ALTER, DROP, SELECT on all tables (wildcard)
aws lakeformation grant-permissions \
  --region us-east-1 \
  --principal "{\"DataLakePrincipalIdentifier\":\"arn:aws:iam::${ACCOUNT_ID}:role/omc_flywheel-dev-glue-role\"}" \
  --resource "{\"Table\":{\"CatalogId\":\"${ACCOUNT_ID}\",\"DatabaseName\":\"omc_flywheel_dev\",\"TableWildcard\":{}}}" \
  --permissions ALTER DROP SELECT

# Step 3: Verify permissions
aws lakeformation list-permissions \
  --principal "{\"DataLakePrincipalIdentifier\":\"arn:aws:iam::${ACCOUNT_ID}:role/omc_flywheel-dev-glue-role\"}" \
  --resource "{\"Database\":{\"Name\":\"omc_flywheel_dev\"}}"
```

**Option 2: AWS Console (if CLI access is limited)**

**Important:** If databases don't show up in the Console dropdown, try these workarounds:

### Workaround A: Manually enter database name in "Grant on table"

Even if the database doesn't show in the dropdown, you can manually type it:

1. Go to **Lake Formation Console** → **Permissions** → **Data permissions**
2. Click **Grant**
3. Select **Grant on table**
4. Under **Principals**, add: `omc_flywheel-dev-glue-role` (or search for it)
5. Under **Table**:
   - **Database**: Manually type `omc_flywheel_dev` (even if it doesn't show in dropdown)
   - **Table**: Select **All tables** or enter `*` for wildcard
6. Select permissions:
   - ✅ ALTER
   - ✅ DROP
   - ✅ SELECT
   - ✅ CREATE_TABLE
7. Click **Grant**

### Workaround B: Register database first, then grant

If databases still don't show, try granting table permissions first:

1. Go to **Lake Formation Console** → **Permissions** → **Data permissions**
2. Click **Grant**
3. Select **Grant on table**
4. Under **Principals**, add: `omc_flywheel-dev-glue-role`
5. Under **Table**, manually enter:
   - **Database**: `omc_flywheel_dev`
   - **Table**: Select **All tables** or use wildcard `*`
6. Select permissions:
   - ✅ ALTER
   - ✅ DROP
   - ✅ SELECT
   - ✅ CREATE_TABLE
7. Click **Grant**

### Workaround C: Register database first, then grant

If the database isn't showing, register it first:

1. Go to **Lake Formation Console** → **Databases**
2. Click **Register database** (or "Add database")
3. Enter database name: `omc_flywheel_dev`
4. Click **Register**
5. After registration, go back to **Permissions** → **Data permissions** → **Grant**
6. Now the database should appear in the dropdown
7. Grant permissions as described below

### Step 1: Grant Database Permissions

**Note:** If the database still doesn't show after registration, you MUST use CLI (Option 1) with an admin profile.

1. Go to **Lake Formation Console** → **Permissions** → **Data permissions**
2. Click **Grant**
3. Select **Grant on database**
4. Choose database: `omc_flywheel_dev` (should appear if registered)
5. Under **Principals**, add: `omc_flywheel-dev-glue-role`
6. Select permissions:
   - ✅ CREATE_TABLE
   - ✅ ALTER
   - ✅ DROP
   - ✅ DESCRIBE
7. Click **Grant**

1. Go to **Lake Formation Console** → **Permissions** → **Data permissions**
2. Click **Grant**
3. Select **Database**
4. Choose database: `omc_flywheel_dev`
5. Under **Principals**, add: `omc_flywheel-dev-glue-role`
6. Select permissions:
   - ✅ CREATE_TABLE
   - ✅ ALTER
   - ✅ DROP
   - ✅ DESCRIBE
7. Click **Grant**

### Step 2: Grant Table Permissions (Wildcard)

1. Still in **Lake Formation Console** → **Permissions** → **Data permissions**
2. Click **Grant**
3. Select **Table**
4. Choose database: `omc_flywheel_dev`
5. Select **All tables** (wildcard)
6. Under **Principals**, add: `omc_flywheel-dev-glue-role`
7. Select permissions:
   - ✅ ALTER
   - ✅ DESCRIBE
   - ✅ DROP
   - ✅ SELECT
   - ✅ INSERT
   - ✅ CREATE_TABLE
8. Click **Grant**

### Step 3: Verify Permissions

After granting via Console, you should see in **Lake Formation → Data permissions**:
- Principal: `arn:aws:iam::417649522250:role/omc_flywheel-dev-glue-role`
- Resource: Database `omc_flywheel_dev` → CREATE_TABLE
- Resource: Tables in `omc_flywheel_dev` (wildcard) → ALTER, DROP, SELECT

### Step 4: Re-run the Job

Once permissions are granted, re-run:
```bash
aws glue start-job-run --job-name etl-omc-flywheel-dev-register-part-tables
```

## Alternative: Use Root Account via Console

If you have root/admin access:

1. Go to **Lake Formation Console** → **Administrative roles and users**
2. Temporarily add your admin user/role as a Data Lake Administrator
3. Grant permissions as above
4. Remove admin access if desired

## Why This Is Needed

The `IAM_ALLOWED_PRINCIPALS` setting only applies to **new** databases and tables created **after** the setting. For existing databases like `omc_flywheel_dev`, explicit permissions must be granted.

