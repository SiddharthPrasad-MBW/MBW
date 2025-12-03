# Current Process Flow - OMC Flywheel Bucketing Solution

## Overview

This document outlines the complete data processing pipeline for the OMC Flywheel bucketing solution, including the new snapshot date tracking functionality.

## Architecture

### Data Flow Pipeline

```
1. Raw Input Data
   ↓
2. Split & Bucket Job (Auto-discover or manual snapshot)
   ↓
3. Register Staged Tables Job
   ↓
4. Create Athena Bucketed Tables Job
   ↓
5. Final Bucketed Tables (Ready for Cleanroom)
```

## Detailed Process Flow

### 1. Source Data Structure
```
s3://omc-flywheel-data-us-east-1-{env}/omc_cleanroom_data/
├── infobase_attributes/raw_input/
│   └── snapshot_dt=2025-10-22/  ← Latest snapshot data
│       ├── IBE_01/
│       ├── IBE_04/
│       └── MIACS_01/
└── addressable/addressable_ids_compaction_cr/
    └── snapshot_dt=2025-10-22/
```

### 2. Split & Bucket Job (`etl-omc-flywheel-{env}-infobase-split-and-bucket`)

**Purpose**: Process raw input data and create bucketed parquet files

**Input**: 
- Source: `s3://bucket/infobase_attributes/raw_input/`
- CSV mapping: `omc_flywheel_infobase_table_split_lowercase.csv`

**Process**:
1. **Auto-discover latest snapshot** (default behavior)
   - Scans `raw_input/` for `snapshot_dt=*` directories
   - Selects the latest date (lexicographically sorted)
   - Example: Finds `snapshot_dt=2025-10-22` as latest

2. **Manual override** (for reprocessing)
   - Use `--SNAPSHOT_DT "2025-10-15"` parameter
   - Processes specific snapshot date

3. **Data Processing**:
   - Reads source data from `raw_input/snapshot_dt={date}/`
   - Applies column mappings from CSV
   - Calculates optimal file sizes per table
   - Creates bucketed parquet files by `customer_user_id`

**Output**:
```
s3://bucket/omc_cleanroom_data/split_cluster/infobase_attributes/
├── IBE_01/          ← Bucketed parquet files
├── IBE_04/          ← Bucketed parquet files  
├── MIACS_01/        ← Bucketed parquet files
└── metadata/
    └── snapshot_dt.txt  ← "2025-10-22"
```

**Key Features**:
- ✅ **Dynamic file sizing**: IBE_01 (~36 files), IBE_04 (~48 files), MIACS_01 (~96 files)
- ✅ **256-bucket bucketing** by `customer_user_id`
- ✅ **Snapshot tracking**: Writes metadata file for downstream jobs
- ✅ **Size-based optimization**: Matches production bucket job logic

### 3. Register Staged Tables Job (`etl-omc-flywheel-{env}-register-staged-tables`)

**Purpose**: Create external tables in Glue catalog from bucketed parquet files

**Input**: 
- S3 Root: `s3://bucket/omc_cleanroom_data/split_cluster/infobase_attributes/`
- Reads metadata: `metadata/snapshot_dt.txt`

**Process**:
1. **Read snapshot metadata** from `metadata/snapshot_dt.txt`
2. **Discover tables** in S3 (handles both subfolder and direct file structures)
3. **Create Glue tables** with snapshot tracking in comments

**Output**:
```
Glue Catalog Tables:
├── ext_ibe_01       ← Comment: "Bucketed table created from snapshot_dt=2025-10-22"
├── ext_ibe_04       ← Comment: "Bucketed table created from snapshot_dt=2025-10-22"
├── ext_miacs_01     ← Comment: "Bucketed table created from snapshot_dt=2025-10-22"
└── ext_addressable_ids ← Comment: "Bucketed table created from snapshot_dt=2025-10-22"
```

**Key Features**:
- ✅ **Flexible table discovery**: Handles both subfolder and direct file structures
- ✅ **Snapshot tracking**: Table comments show source snapshot date
- ✅ **Automatic registration**: Creates external tables for all discovered data

### 4. Create Athena Bucketed Tables Job (`etl-omc-flywheel-{env}-create-athena-bucketed-tables`)

**Purpose**: Create true Hive bucketed tables using Athena CTAS

**Input**:
- Staged tables: `ext_ibe_01`, `ext_ibe_04`, etc.
- Bucketed base: `s3://bucket/omc_cleanroom_data/cleanroom_tables/bucketed/`
- Reads metadata: `metadata/snapshot_dt.txt`

**Process**:
1. **Read snapshot metadata** from bucketed base
2. **Create CTAS statements** with bucketing configuration
3. **Execute Athena queries** to create final tables

**Output**:
```
Final Bucketed Tables:
├── bucketed_ibe_01       ← Comment: "Bucketed table created from snapshot_dt=2025-10-22"
├── bucketed_ibe_04       ← Comment: "Bucketed table created from snapshot_dt=2025-10-22"
├── bucketed_miacs_01     ← Comment: "Bucketed table created from snapshot_dt=2025-10-22"
└── bucketed_addressable_ids ← Comment: "Bucketed table created from snapshot_dt=2025-10-22"
```

**Key Features**:
- ✅ **True Hive bucketing**: Uses `bucketed_by` and `bucket_count` properties
- ✅ **Performance optimized**: G.2X workers, 8 workers (4-8x faster than before)
- ✅ **Snapshot tracking**: Final tables show source snapshot date
- ✅ **Cleanroom ready**: Optimized for join performance

## Job Configurations

### Split & Bucket Job
- **Workers**: G.4X, 24 workers (96 DPU)
- **Timeout**: 48 hours
- **Parameters**:
  - `--SOURCE_PATH`: Base path to raw_input
  - `--TARGET_BUCKET`: Output location
  - `--SNAPSHOT_DT`: Optional manual override
  - `--BUCKET_COUNT`: 256
  - `--TARGET_FILE_MB`: 512

### Register Staged Tables Job
- **Workers**: G.1X, 2 workers (2 DPU)
- **Timeout**: 1 hour
- **Parameters**:
  - `--S3_ROOT`: Path to split_cluster data
  - `--DATABASE`: Target Glue database
  - `--TABLE_PREFIX`: "ext_"

### Create Athena Bucketed Tables Job
- **Workers**: G.2X, 8 workers (64 DPU) - **Performance optimized**
- **Timeout**: 1 hour
- **Parameters**:
  - `--STAGED_DB`: Source database
  - `--FINAL_DB`: Target database
  - `--BUCKETED_BASE`: Output S3 location
  - `--BUCKET_COUNT`: 256
  - `--BUCKET_COL`: "customer_user_id"

## Usage Examples

### Automated Production Run (Monthly)
```bash
# Auto-discovers latest snapshot_dt
aws glue start-job-run --job-name etl-omc-flywheel-prod-infobase-split-and-bucket
aws glue start-job-run --job-name etl-omc-flywheel-prod-register-staged-tables
aws glue start-job-run --job-name etl-omc-flywheel-prod-create-athena-bucketed-tables
```

### Manual Reprocessing (Specific Date)
```bash
# Process specific snapshot
aws glue start-job-run --job-name etl-omc-flywheel-prod-infobase-split-and-bucket \
  --arguments '{"--SNAPSHOT_DT":"2025-10-15"}'
aws glue start-job-run --job-name etl-omc-flywheel-prod-register-staged-tables
aws glue start-job-run --job-name etl-omc-flywheel-prod-create-athena-bucketed-tables
```

### Addressable IDs Processing
```bash
# Process addressable_ids separately
aws glue start-job-run --job-name etl-omc-flywheel-prod-addressable-bucket
```

## Snapshot Tracking

### Metadata Flow
1. **Split & Bucket Job**: Writes `metadata/snapshot_dt.txt` with discovered/selected date
2. **Register Job**: Reads metadata and adds to table comments
3. **Athena Job**: Reads metadata and adds to final table comments

### S3 Metadata Structure
```
s3://bucket/omc_cleanroom_data/
├── split_cluster/infobase_attributes/
│   └── metadata/snapshot_dt.txt  ← "2025-10-22"
└── cleanroom_tables/bucketed/
    └── metadata/snapshot_dt.txt  ← "2025-10-22"
```

## Performance Optimizations

### File Sizing Strategy
- **IBE_01** (17.4GB): ~36 files (512MB each)
- **IBE_04** (19.9GB): ~48 files (512MB each)  
- **MIACS_01** (34GB): ~96 files (512MB each)

### Worker Optimizations
- **Split & Bucket**: G.4X, 24 workers (96 DPU)
- **Register**: G.1X, 2 workers (2 DPU)
- **Athena**: G.2X, 8 workers (64 DPU) - **4-8x faster than before**

## Environment Support

### Development
- **Account**: 417649522250
- **S3**: `omc-flywheel-data-us-east-1-dev`
- **Database**: `omc_flywheel_dev`

### Production  
- **Account**: 239083076653
- **S3**: `omc-flywheel-data-us-east-1-prod`
- **Database**: `omc_flywheel_prod`

## Cleanroom Integration

The final bucketed tables are optimized for Cleanroom join performance:
- ✅ **256-bucket bucketing** by `customer_user_id`
- ✅ **Consistent bucketing** across all joinable tables
- ✅ **Optimal file sizes** for query performance
- ✅ **Snapshot tracking** for data lineage

### Cleanrooms Reporting

**Job**: `etl-omc-flywheel-prod-generate-cleanrooms-report`

**Purpose**: Generate comprehensive reports on Cleanrooms resources, configured tables, associations, and Identity Resolution Service setup.

**Input**:
- Cleanrooms membership ID
- Glue database and table prefix
- Report output S3 bucket

**Process**:
1. Retrieves all Glue tables matching the prefix
2. Fetches Cleanrooms configured tables and associations
3. Extracts analysis rules and provider information
4. Retrieves Identity Resolution Service resources (ID namespaces, schema mappings)
5. Generates comprehensive reports in JSON and CSV formats

**Output**:
```
s3://omc-flywheel-prod-analysis-data/cleanrooms-reports/
├── ACX_Cleanroom_Report_YYYYMMDD_HHMMSS.json
├── ACX_Cleanroom_Report_YYYYMMDD_HHMMSS_Tables.csv
└── ACX_Cleanroom_Report_YYYYMMDD_HHMMSS_IdentityResolution.csv
```

**Report Contents**:
- **Tables Report**: Table name, configured table status, association status, analysis providers, ready for analysis status
- **Identity Resolution Report**: ID namespace, method, source database, region, table, schema mapping, unique ID, input field, matchkey

**Key Features**:
- ✅ **Comprehensive coverage**: All configured tables and associations
- ✅ **Identity Resolution integration**: Full details on ER namespaces and schema mappings
- ✅ **Analysis provider tracking**: Shows which accounts can query each table
- ✅ **Dual format output**: JSON for programmatic access, CSV for analysis

**Usage**:
```bash
aws glue start-job-run --job-name etl-omc-flywheel-prod-generate-cleanrooms-report
```

**Configuration**:
- **Workers**: G.1X, 2 workers (Glue ETL job)
- **Timeout**: 1 hour
- **Default Parameters**:
  - `--membership-id`: 6610c9aa-9002-475c-8695-d833485741bc
  - `--database`: omc_flywheel_prod
  - `--table-prefix`: part_
  - `--report-bucket`: omc-flywheel-prod-analysis-data
  - `--report-prefix`: cleanrooms-reports/

### Identity Resolution Service

The solution integrates with AWS Entity Resolution Service for identity matching:

- ✅ **ID Namespace**: `ACXIdNamespace` - Defines unique customer identifiers
- ✅ **Schema Mapping**: `ACX_SCHEMA` - Maps table columns to identity fields
- ✅ **ID Mapping Tables**: Links different identifiers within collaborations
- ✅ **ER Tables**: `part_*_er` tables created for Entity Resolution workflows

**ER Table Creation**:
- Automated via `create-all-part-tables-er.py` script
- Creates `_er` versions of all `part_*` tables
- Includes `row_id` and `customer_user_id` columns
- Optimized for identity resolution workflows

## Monitoring & Troubleshooting

### Key Log Messages
- `📅 Auto-discovered snapshot_dt: 2025-10-22`
- `📅 Manual snapshot_dt: 2025-10-15`
- `📅 Wrote snapshot_dt=2025-10-22 to metadata/snapshot_dt.txt`
- `✅ Created bucketed_ibe_01 with snapshot_dt=2025-10-22`

### Common Issues
1. **No snapshots found**: Check `raw_input/` directory structure
2. **Metadata not found**: Verify previous job completed successfully
3. **Permission errors**: Ensure Glue role has S3 and Athena permissions

## Next Steps

1. **Test the complete pipeline** in dev environment
2. **Validate snapshot tracking** works correctly
3. **Deploy to production** for monthly runs
4. **Monitor performance** and optimize as needed
