# Production Flow Validation

## User's Stated Flow
1. `addressable_split_and_part`
2. `infobase_split_and_part`
3. `prepare-part_tables`
4. `create part-addressableid-er table`
5. `generate data monitor`
6. `generate cleanroom report`

## Documented Production Flow (from PRODUCTION_RUN_SEQUENCE.md)

### Partitioned Tables Pipeline:
1. **Step 1: Infobase Split and Part** (`etl-omc-flywheel-prod-infobase-split-and-part`)
2. **Step 2: Addressable IDs Split and Part** (`etl-omc-flywheel-prod-addressable-split-and-part`)
3. **Step 3: Register Part Tables** (`etl-omc-flywheel-prod-register-part-tables`) ⚠️ **MISSING FROM USER'S FLOW**
4. **Step 4: Prepare Part Tables** (`etl-omc-flywheel-prod-prepare-part-tables`)
5. **Reporting: Generate Cleanrooms Report** (`etl-omc-flywheel-prod-generate-cleanrooms-report`)

## Validation Results

### ✅ Correct Steps:
- ✅ `addressable_split_and_part` - Exists (can run simultaneously with infobase)
- ✅ `infobase_split_and_part` - Exists (can run simultaneously with addressable)
- ✅ `prepare-part_tables` - Exists (Step 4 in docs, matches user's Step 3)
- ✅ `generate cleanroom report` - Exists (matches user's Step 6)

### ⚠️ Missing from User's Flow:
- ❌ **`register-part-tables`** - This is Step 3 in documented flow but missing from user's list
  - **Purpose**: Creates the **initial** external Glue tables (`part_*`) pointing to `split_part/` data
  - **What it does**: Reads parquet files, infers schema, creates table definitions in Glue catalog
  - **Required**: Yes - needed before `prepare-part-tables` can work
  - **Job**: `etl-omc-flywheel-prod-register-part-tables`

### 📝 Key Distinction:
- **`register-part-tables`**: Creates the **initial table definitions** in Glue catalog (table must not exist)
- **`prepare-part-tables`**: **Assumes tables already exist**, then:
  - Ensures tables are partitioned by `id_bucket`
  - Runs `MSCK REPAIR TABLE` to register missing partitions
  - Does NOT create the initial table - only repairs/updates existing tables

### ❓ Unclear Steps:
- ❓ `create part-addressableid-er table` - User's Step 4
  - **Possible Job**: `etl-omc-flywheel-prod-create-part-addressable-ids-er-table`
  - **Purpose**: Creates Entity Resolution table for addressable IDs
  - **When to run**: After `prepare-part-tables` (makes sense)
  - **Status**: Job exists in Terraform module

- ❓ `generate data monitor` - User's Step 5
  - **Possible Job**: `etl-omc-flywheel-prod-generate-data-monitor-report`
  - **Purpose**: Monitors data quality, partition integrity, freshness
  - **When to run**: After tables are prepared (makes sense)
  - **Status**: Job exists in monitoring module (not in gluejobs module)

## Recommended Corrected Flow

### Option 1: Complete Flow (All Steps)
1. `infobase_split_and_part` (or `addressable_split_and_part` first - order may not matter)
2. `addressable_split_and_part` (or `infobase_split_and_part` second)
3. **`register-part-tables`** ⚠️ **ADD THIS STEP**
4. `prepare-part_tables`
5. `create-part-addressable-ids-er-table` (if needed for ER workflows)
6. `generate-data-monitor-report` (optional monitoring)
7. `generate-cleanrooms-report`

### Option 2: User's Flow with Missing Step Added
1. `addressable_split_and_part`
2. `infobase_split_and_part`
3. **`register-part-tables`** ⚠️ **ADD THIS STEP**
4. `prepare-part_tables`
5. `create-part-addressable-ids-er-table`
6. `generate-data-monitor-report`
7. `generate-cleanrooms-report`

## Order Dependencies

### Critical Dependencies:
- `register-part-tables` **MUST** run before `prepare-part-tables`
  - Reason: `prepare-part-tables` runs `MSCK REPAIR TABLE` on `part_*` tables
  - If tables don't exist, `MSCK REPAIR` will fail

- `prepare-part-tables` **MUST** run before ER table creation
  - Reason: ER tables depend on `part_*` tables being properly partitioned

### Order Flexibility:
- `infobase_split_and_part` and `addressable_split_and_part` can run in either order
  - They process different data sources independently
  - Both must complete before `register-part-tables`

## Job Names (Production)

1. `etl-omc-flywheel-prod-addressable-split-and-part`
2. `etl-omc-flywheel-prod-infobase-split-and-part`
3. `etl-omc-flywheel-prod-register-part-tables` ⚠️ **MISSING FROM USER'S FLOW**
4. `etl-omc-flywheel-prod-prepare-part-tables`
5. `etl-omc-flywheel-prod-create-part-addressable-ids-er-table`
6. `etl-omc-flywheel-prod-generate-data-monitor-report` (from monitoring module)
7. `etl-omc-flywheel-prod-generate-cleanrooms-report`

## Summary

**User's flow is missing the `register-part-tables` step**, which is critical for creating the Glue catalog tables before `prepare-part-tables` can run `MSCK REPAIR`.

**Recommended action**: Add `register-part-tables` as Step 3 (or Step 3.5) between the split jobs and `prepare-part-tables`.

