# Production Run Sequence - Dual Pipeline Solution

## 🎯 **Overview**
This document outlines the run sequence for both data processing pipelines:
1. **Bucketed Tables Pipeline** - Original solution for Cleanroom-optimized bucketed tables
2. **Partitioned Tables Pipeline** - New solution for time-series partitioned tables

## 📋 **Prerequisites**
- ✅ Production Glue role updated with full S3/Athena permissions
- ✅ All production scripts updated with latest changes
- ✅ Source data available in S3 with `snapshot_dt` structure

## 🔄 **Pipeline 1: Bucketed Tables (Original)**

### **Step 1: Infobase Split and Bucket**
```bash
aws glue start-job-run \
  --job-name etl-omc-flywheel-prod-infobase-split-and-bucket \
  --arguments '{
    "--SNAPSHOT_DT": "_NONE_",
    "--SOURCE_PATH": "s3://omc-flywheel-data-us-east-1-prod/opus/infobase_attributes/raw_input/",
    "--TARGET_PATH": "s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_cluster/infobase_attributes/",
    "--CSV_FILE": "s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/omc_flywheel_infobase_table_split_lowercase.csv"
  }'
```

**What it does:**
- ✅ Auto-discovers latest `snapshot_dt` from source path
- ✅ Reads infobase_attributes data with column name handling (`Customer_User_id` → `customer_user_id`)
- ✅ Applies S3A protocol conversion (`s3://` → `s3a://`)
- ✅ Creates subdirectories: `IBE_01/`, `IBE_02/`, etc.
- ✅ Writes metadata: `metadata/snapshot_dt.txt`
- ✅ Uses dynamic file sizing per table

**Expected Output:**
```
split_cluster/infobase_attributes/
├── IBE_01/                    # Parquet files
├── IBE_02/
├── ...
└── metadata/
    └── snapshot_dt.txt        # Snapshot date
```

---

### **Step 2: Addressable IDs Bucket**
```bash
aws glue start-job-run \
  --job-name etl-omc-flywheel-prod-addressable-bucket \
  --arguments '{
    "--SNAPSHOT_DT": "_NONE_",
    "--SOURCE_PATH": "s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/addressable/addressable_ids_compaction_cr/",
    "--TARGET_PATH": "s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_cluster/addressable_ids/"
  }'
```

**What it does:**
- ✅ Auto-discovers latest `snapshot_dt` from source path
- ✅ Reads addressable_ids data with column name handling
- ✅ Applies S3A protocol conversion
- ✅ Creates subdirectory: `addressable_ids/addressable_ids/`
- ✅ Writes metadata: `metadata/snapshot_dt.txt`
- ✅ Uses dynamic file sizing (not hardcoded)

**Expected Output:**
```
split_cluster/addressable_ids/
├── addressable_ids/           # Parquet files
│   ├── part-00000-xxx.parquet
│   └── ...
└── metadata/
    └── snapshot_dt.txt        # Snapshot date
```

---

### **Step 3: Register Staged Tables**

#### **3a: Register Infobase Tables**
```bash
aws glue start-job-run \
  --job-name etl-omc-flywheel-prod-register-staged-tables \
  --arguments '{
    "--DATABASE": "omc_flywheel_prod",
    "--S3_ROOT": "s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_cluster/infobase_attributes/",
    "--TABLE_PREFIX": "ext_",
    "--MAX_COLS": "100"
  }'
```

#### **3b: Register Addressable Tables**
```bash
aws glue start-job-run \
  --job-name etl-omc-flywheel-prod-register-staged-tables \
  --arguments '{
    "--DATABASE": "omc_flywheel_prod",
    "--S3_ROOT": "s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_cluster/addressable_ids/",
    "--TABLE_PREFIX": "ext_",
    "--MAX_COLS": "100"
  }'
```

**What it does:**
- ✅ Creates external tables: `ext_ibe_01`, `ext_ibe_02`, etc.
- ✅ Creates external table: `ext_addressable_ids`
- ✅ Points to correct subdirectories (no metadata conflicts)
- ✅ Reads `snapshot_dt` from metadata files
- ✅ Adds table comments with snapshot information

**Expected Tables:**
```
omc_flywheel_prod.ext_ibe_01          → s3://.../split_cluster/infobase_attributes/IBE_01/
omc_flywheel_prod.ext_ibe_02          → s3://.../split_cluster/infobase_attributes/IBE_02/
...
omc_flywheel_prod.ext_addressable_ids → s3://.../split_cluster/addressable_ids/addressable_ids/
```

---

### **Step 4: Create Athena Bucketed Tables**

#### **4a: Create All Tables (Full Run)**
```bash
aws glue start-job-run \
  --job-name etl-omc-flywheel-prod-create-athena-bucketed-tables \
  --arguments '{
    "--ATHENA_WORKGROUP": "primary",
    "--BUCKET_COUNT": "256",
    "--BUCKET_COL": "customer_user_id",
    "--STAGED_DB": "omc_flywheel_prod",
    "--FINAL_DB": "omc_flywheel_prod",
    "--BUCKETED_BASE": "s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/cleanroom_tables/bucketed/",
    "--ATHENA_RESULTS_S3": "s3://omc-flywheel-prod-analysis-data/query-results/"
  }'
```

#### **4b: Create Specific Tables (Faster Testing)**
```bash
aws glue start-job-run \
  --job-name etl-omc-flywheel-prod-create-athena-bucketed-tables \
  --arguments '{
    "--ATHENA_WORKGROUP": "primary",
    "--BUCKET_COUNT": "256",
    "--BUCKET_COL": "customer_user_id",
    "--STAGED_DB": "omc_flywheel_prod",
    "--FINAL_DB": "omc_flywheel_prod",
    "--BUCKETED_BASE": "s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/cleanroom_tables/bucketed/",
    "--ATHENA_RESULTS_S3": "s3://omc-flywheel-prod-analysis-data/query-results/",
    "--TABLES_FILTER": "addressable_ids,ibe_01,ibe_02"
  }'
```

**What it does:**
- ✅ Creates bucketed tables: `bucketed_ibe_01`, `bucketed_ibe_02`, etc.
- ✅ Creates bucketed table: `bucketed_addressable_ids`
- ✅ Uses Hive bucketing (256 buckets by `customer_user_id`)
- ✅ Includes snapshot information in table comments
- ✅ Optimized for Cleanroom join performance

**Expected Tables:**
```
omc_flywheel_prod.bucketed_ibe_01
omc_flywheel_prod.bucketed_ibe_02
...
omc_flywheel_prod.bucketed_addressable_ids
```

---

## 🔄 **Pipeline 2: Partitioned Tables (New)**

### **Step 1: Infobase Split and Part**
```bash
aws glue start-job-run \
  --job-name etl-omc-flywheel-prod-infobase-split-and-part \
  --arguments '{
    "--SNAPSHOT_DT": "_NONE_",
    "--SOURCE_PATH": "s3://omc-flywheel-data-us-east-1-prod/opus/infobase_attributes/raw_input/",
    "--TARGET_PATH": "s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_part/infobase_attributes/",
    "--CSV_FILE": "s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/omc_flywheel_infobase_table_split_part.csv"
  }'
```

**What it does:**
- ✅ Creates partitioned parquet files in `split_part/` directory
- ✅ Optimizes for time-series queries with date partitioning
- ✅ Uses same column handling and S3A protocol as bucketed pipeline
- ✅ **Dynamic partition overwrite mode** - Only replaces partitions being written (enables incremental updates)
- ✅ **Parallel partition discovery** - Speeds up partition discovery and repair operations

### **Step 2: Addressable IDs Split and Part**
```bash
aws glue start-job-run \
  --job-name etl-omc-flywheel-prod-addressable-split-and-part \
  --arguments '{
    "--SNAPSHOT_DT": "_NONE_",
    "--SOURCE_PATH": "s3://omc-flywheel-data-us-east-1-prod/opus/addressable_ids/raw_input/",
    "--TARGET_PATH": "s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_part/addressable_ids/",
    "--CSV_FILE": "s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/omc_flywheel_addressable_ids_table_split_part.csv"
  }'
```

### **Step 3: Register Part Tables**
```bash
aws glue start-job-run \
  --job-name etl-omc-flywheel-prod-register-part-tables \
  --arguments '{
    "--SNAPSHOT_DT": "_NONE_",
    "--SOURCE_PATH": "s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_part/",
    "--STAGED_DB": "omc_flywheel_prod",
    "--TABLE_PREFIX": "part_"
  }'
```

**What it does:**
- ✅ Creates external Glue tables (`part_*`) pointing to `split_part/` data
- ✅ Enables Athena queries on partitioned data

### **Step 4: Prepare Part Tables**
```bash
aws glue start-job-run \
  --job-name etl-omc-flywheel-prod-prepare-part-tables \
  --arguments '{
    "--AWS_REGION": "us-east-1",
    "--DATABASE": "omc_flywheel_prod",
    "--WORKGROUP": "primary",
    "--RESULTS_S3": "s3://aws-athena-query-results-us-east-1-<account>/msck/",
    "--TABLE_PREFIX": "part_",
    "--MAX_CONCURRENCY": "5",
    "--POLL_INTERVAL_SEC": "2"
  }'
```

**What it does:**
- ✅ Runs `MSCK REPAIR TABLE` on all `part_*` tables
- ✅ Discovers and registers new partitions automatically
- ✅ Optimizes query performance for date-range filters

**Expected Output:**
```
split_part/
├── infobase_attributes/
│   ├── IBE_01/
│   │   └── snapshot_dt=2024-01-15/  # Partitioned by date
│   ├── IBE_02/
│   └── ...
└── addressable_ids/
    └── snapshot_dt=2024-01-15/      # Partitioned by date
```

**Final Tables:**
```
omc_flywheel_prod.part_ibe_01_a
omc_flywheel_prod.part_ibe_02_a
...
omc_flywheel_prod.part_addressable_ids
```

---

## 🎯 **Key Improvements in This Sequence**

### **1. Column Name Handling**
- ✅ Automatically handles `Customer_User_id` → `customer_user_id` conversion
- ✅ Consistent column naming across all tables

### **2. S3A Protocol**
- ✅ Converts `s3://` to `s3a://` for Spark compatibility
- ✅ Prevents "No such file or directory" errors

### **3. Snapshot Tracking**
- ✅ Auto-discovers latest `snapshot_dt` from source paths
- ✅ Manual override available with `--SNAPSHOT_DT=YYYY-MM-DD`
- ✅ Propagates snapshot information to final tables

### **4. Dynamic File Sizing**
- ✅ Calculates optimal file count per table based on actual data size
- ✅ No more hardcoded file counts

### **5. Subdirectory Structure**
- ✅ Consistent structure for both infobase and addressable data
- ✅ Prevents metadata conflicts with Athena

### **6. Performance Optimizations**
- ✅ G.4X workers with 8 workers for faster processing
- ✅ Table filtering for faster testing
- ✅ Optimized for Cleanroom join performance

---

## 📊 **Reporting & Monitoring**

### **Step: Generate Cleanrooms Report**

```bash
aws glue start-job-run \
  --job-name etl-omc-flywheel-prod-generate-cleanrooms-report
```

**What it does:**
- ✅ Retrieves all Glue tables with `part_` prefix
- ✅ Fetches Cleanrooms configured tables and associations
- ✅ Extracts analysis rules and provider information
- ✅ Retrieves Identity Resolution Service resources (ID namespaces, schema mappings)
- ✅ Generates comprehensive reports in JSON and CSV formats

**Expected Output:**
```
s3://omc-flywheel-prod-analysis-data/cleanrooms-reports/
├── ACX_Cleanroom_Report_YYYYMMDD_HHMMSS.json
├── ACX_Cleanroom_Report_YYYYMMDD_HHMMSS_Tables.csv
└── ACX_Cleanroom_Report_YYYYMMDD_HHMMSS_IdentityResolution.csv
```

**Report Contents**:
- **Tables Report**: Table status, associations, analysis providers, ready for analysis
- **Identity Resolution Report**: ID namespace, schema mapping, unique ID, input field, matchkey

**When to Run**:
- After creating/updating configured tables
- After modifying associations
- After Identity Resolution Service changes
- Regular audits (monthly/quarterly)

---

## ⏱️ **Expected Runtime**

| Step | Duration | Notes |
|------|----------|-------|
| Infobase Split | 15-20 min | 26 tables, dynamic sizing |
| Addressable Bucket | 5-10 min | 1 table, dynamic sizing |
| Register Tables | 2-3 min | Fast metadata operations |
| Create Bucketed | 20-25 min | All tables (full run) |
| Create Bucketed | 2-3 min | Filtered tables (testing) |
| Generate Cleanrooms Report | 1-2 min | Fast read-only operations |

**Total Full Run**: ~45-60 minutes
**Total Testing Run**: ~25-35 minutes
**Reporting**: ~1-2 minutes (can run independently)

---

## 🚨 **Troubleshooting**

### **Common Issues:**
1. **Column Name Errors**: Check for `Customer_User_id` vs `customer_user_id`
2. **S3 Protocol Errors**: Ensure S3A conversion is working
3. **Permission Errors**: Verify Glue role has all S3/Athena permissions
4. **Metadata Conflicts**: Ensure subdirectory structure is correct

### **Monitoring:**
- Check CloudWatch logs for each job
- Monitor S3 bucket usage and file counts
- Verify table creation in Glue Catalog
- Test Athena queries on bucketed tables

---

## ✅ **Success Criteria**

1. **All external tables created** in Glue Catalog
2. **All bucketed tables created** with proper bucketing
3. **Snapshot information** included in table comments
4. **No permission errors** in job logs
5. **Cleanroom joins** perform significantly better
6. **File counts** are optimized per table size

---

*Last Updated: 2025-11-18*
*Version: 2.1 - Added Cleanrooms Reporting*
