# Lake Formation UI - Step-by-Step Grant Permissions

## Step-by-Step Instructions

### Step 1: Select Principal Type
- ✅ **Principals** (already selected)

### Step 2: Choose Principals
- Click **"IAM users and roles"**
- Click **"Add one or more IAM users or roles"**
- Search for or select: `omc_flywheel-dev-glue-role`
- Click to add it

### Step 3: Choose Resource Method
- Select **"Named Data Catalog resources"** (NOT "Resources matched by LF-Tags")
- This should show options for databases and tables

### Step 4: Select Database
**If database shows in dropdown:**
- Under **Databases**, select `omc_flywheel_dev`

**If database DOESN'T show (this is your issue):**
- Try typing `omc_flywheel_dev` manually in the search/input field
- OR proceed to Step 5 to grant table permissions first (workaround)

### Step 5: Grant Database Permissions
- Under **Database permissions**, check:
  - ✅ **Create table**
  - ✅ **Alter**
  - ✅ **Drop**
  - ✅ **Describe**
- Click **Grant**

### Step 6: Grant Table Permissions (Separate Grant)
Go back and create a second grant:

1. Click **Grant** again
2. Select **Principals** → **IAM users and roles** → Add `omc_flywheel-dev-glue-role`
3. Select **"Named Data Catalog resources"**
4. Under **Tables**:
   - **Database**: Select or type `omc_flywheel_dev`
   - **Table**: Select **"All tables"** or enter `*` for wildcard
5. Under **Table permissions**, check:
   - ✅ **Select**
   - ✅ **Alter**
   - ✅ **Drop**
   - ✅ **Describe**
6. Click **Grant**

## If Database Still Doesn't Show

### Option A: Register Database First
1. Go to **Lake Formation** → **Databases** (left sidebar)
2. Click **Register database** or **Add database**
3. Enter: `omc_flywheel_dev`
4. Click **Register**
5. Go back to **Permissions** → **Grant** and try again

### Option B: Use CLI (Most Reliable)
If the UI continues to not show the database, use CLI with admin access:

```bash
bash /tmp/lf-grant-simple.sh <admin-aws-profile>
```

Or run these commands manually with an admin profile:

```bash
export AWS_PROFILE=<admin-profile>
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Grant CREATE_TABLE on database
aws lakeformation grant-permissions \
  --region us-east-1 \
  --principal "{\"DataLakePrincipalIdentifier\":\"arn:aws:iam::${ACCOUNT_ID}:role/omc_flywheel-dev-glue-role\"}" \
  --resource "{\"Database\":{\"CatalogId\":\"${ACCOUNT_ID}\",\"Name\":\"omc_flywheel_dev\"}}" \
  --permissions CREATE_TABLE

# Grant ALTER, DROP, SELECT on all tables
aws lakeformation grant-permissions \
  --region us-east-1 \
  --principal "{\"DataLakePrincipalIdentifier\":\"arn:aws:iam::${ACCOUNT_ID}:role/omc_flywheel-dev-glue-role\"}" \
  --resource "{\"Table\":{\"CatalogId\":\"${ACCOUNT_ID}\",\"DatabaseName\":\"omc_flywheel_dev\",\"TableWildcard\":{}}}" \
  --permissions ALTER DROP SELECT
```

## Verification

After granting, you should see in **Lake Formation → Permissions → Data permissions**:
- Principal: `omc_flywheel-dev-glue-role`
- Resource: Database `omc_flywheel_dev` → CREATE_TABLE, ALTER, DROP, DESCRIBE
- Resource: Tables in `omc_flywheel_dev` (wildcard) → ALTER, DROP, SELECT

