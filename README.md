# OMC Flywheel Cleanroom Bucketing Solution

This repository contains the production-ready AWS Glue ETL jobs for the OMC Flywheel Cleanroom bucketing solution. The solution optimizes data processing performance by implementing dynamic file sizing and Hive bucketing for analytical queries.

## 🚀 **Recent Updates**

### **Entity Resolution Service Integration (January 2025)**
- ✅ **Identity Resolution Service**: Full Terraform module and stack for Cleanrooms Identity Resolution
- ✅ **ER Table Creation**: Automated creation of `_er` tables for all part_* tables via Glue jobs
- ✅ **Schema Mapping Generation**: Automatic generation of Entity Resolution schema mapping JSON files
- ✅ **Resource Discovery**: Scripts to discover and document existing Entity Resolution resources
- ✅ **Column Management**: Fixed column truncation issues in configured tables (part_miacs_02_a)

### **Analysis Provider Updates (January 2025)**
- ✅ **Dual Provider Support**: All 27 configured tables now support both analysis providers
  - `921290734397` (AMC Service)
  - `657425294073` (Query Submitter/AMC Results Receiver)
- ✅ **Terraform Defaults**: Updated Terraform variable defaults to include both providers
- ✅ **Verification Tools**: Scripts to verify and update analysis provider configurations

### **Variable-Driven Infrastructure & Dev Environment (November 2025)**
- ✅ **Variable-Driven Modules**: All Terraform modules now environment-agnostic
- ✅ **Development Stacks**: Complete dev environment stacks for Glue jobs, monitoring, and Cleanrooms
- ✅ **AWS Cleanrooms Integration**: Full support for configured tables, analysis rules, and associations
- ✅ **Environment Separation**: Clean separation between dev and prod with variable-driven approach
- ✅ **Documentation**: [Terraform Variable Strategy](infra/TERRAFORM_VARIABLE_STRATEGY.md) ⭐

### **Lake Formation Infrastructure (October 2025)**
- ✅ **Modular Terraform Structure**: Clean, toggle-able Lake Formation setup
- ✅ **Source Data Path Fix**: Properly handles `ext_*` tables for CTAS operations
- ✅ **Environment Separation**: Safe dev/prod configurations
- ✅ **Writer/Reader Separation**: Distinct permissions for Glue roles vs Cleanroom consumers
- ✅ **Comprehensive Testing Plan**: [Lake Formation Fix Testing Plan](LAKE_FORMATION_FIX_TESTING_PLAN.md)
- ✅ **Operational Runbook**: [Lake Formation Setup Runbook](infra/LAKE_FORMATION_SETUP_RUNBOOK.md) ⭐

### **Production Deployment (October 2025)**
- ✅ **4 Production Glue Jobs** deployed and tested
- ✅ **Bucketed Tables Created**: `bucketed_ibe_01_a`, `bucketed_ibe_02_a`
- ✅ **Performance Optimized**: 4-8x improvement for analytical queries
- ✅ **Lake Formation Issues Resolved**: CTAS operations working correctly

## 🏗️ Architecture Overview

The solution consists of **two parallel data processing pipelines** that create Cleanroom-ready tables:

### **Pipeline 1: Bucketed Tables** (Original)
1. **Split & Bucket Job** - Process raw data and create bucketed parquet files in `split_cluster/`
2. **Create External Tables** - Register external Glue tables (`ext_*`) pointing to split_cluster data
3. **Create Athena Bucketed Tables** - Generate true Hive bucketed tables (`bucketed_*`) using Athena CTAS

### **Pipeline 2: Partitioned Tables** (New)
1. **Split & Part Job** - Process raw data and create partitioned parquet files in `split_part/`
2. **Register Part Tables** - Register external Glue tables (`part_*`) pointing to split_part data
3. **Prepare Part Tables** - Run MSCK REPAIR on partitioned tables for optimal query performance

**📋 Complete Flow Documentation**: See [Production Run Sequence](docs/PRODUCTION_RUN_SEQUENCE.md) for detailed step-by-step instructions.

## 📁 Directory Structure

```
acx_omc_flywheel_cr/
├── scripts/                          # Glue ETL job scripts and utilities
│   ├── etl-omc-flywheel-dev-*.py     # Development job scripts
│   ├── etl-omc-flywheel-prod-*.py    # Production job scripts
│   ├── register-staged-tables.py     # Table registration script
│   ├── create-cleanrooms-configured-tables.py  # Cleanrooms table management
│   ├── add-collaboration-analysis-rules.py     # Cleanrooms analysis rules
│   ├── refresh-collaboration-associations.py   # Migrate association naming
│   ├── verify-collaboration-table-config.py    # Verify table configurations
│   ├── update-configured-table-analysis-providers.py  # Update analysis providers
│   ├── create-all-part-tables-er.py  # Create _er tables for Entity Resolution
│   ├── create-part-addressable-ids-er-table.py # Create addressable_ids_er table
│   ├── generate-entity-resolution-schema-mappings.py  # Generate ER schema mappings
│   ├── discover-cr-namespace-resources.py  # Discover Entity Resolution resources
│   ├── create-cr-namespace-resources.py  # Create Entity Resolution resources
│   └── sync_dev_with_prod.py         # Dev/prod sync utility
├── infra/                           # Terraform infrastructure
│   ├── modules/                     # Reusable Terraform modules
│   │   ├── gluejobs/                # Glue jobs module (variable-driven)
│   │   ├── monitoring/              # Monitoring module (variable-driven)
│   │   ├── crconfigtables/          # Cleanrooms configured tables module
│   │   ├── crnamespace/             # Cleanrooms Identity Resolution Service module
│   │   └── lakeformation/           # Lake Formation module
│   ├── stacks/                      # Environment-specific stacks
│   │   ├── dev-gluejobs/            # Dev Glue jobs stack
│   │   ├── dev-monitoring/          # Dev monitoring stack
│   │   ├── dev-crconfigtables/      # Dev Cleanrooms stack
│   │   ├── prod-gluejobs/           # Prod Glue jobs stack
│   │   ├── prod-monitoring/         # Prod monitoring stack
│   │   ├── prod-crconfigtables/     # Prod Cleanrooms stack
│   │   └── prod-crnamespace/       # Prod Identity Resolution Service stack
│   ├── envs/dev/                    # Development environment (legacy)
│   ├── envs/prod/                   # Production environment (legacy)
│   ├── TERRAFORM_VARIABLE_STRATEGY.md  # Variable-driven approach documentation
│   └── README.md                    # Infrastructure documentation
├── docs/                            # Documentation
│   ├── CURRENT_PROCESS_FLOW.md      # Process flow documentation
│   ├── PRODUCTION_RUN_SEQUENCE.md  # Production run instructions
│   └── API_REFERENCE.md            # API documentation
├── requirements.txt                 # Python dependencies
├── Makefile                         # Build automation
├── LAKE_FORMATION_FIX_TESTING_PLAN.md # Testing plan for Lake Formation fix
└── README.md                        # This file
```

## 🚀 Key Features

### Dynamic File Sizing
- Automatically calculates optimal file count based on actual data size
- Prevents over-partitioning and improves query performance
- Uses `repartition()` and `coalesce()` for efficient data distribution

### Snapshot Tracking
- Auto-discovers latest `snapshot_dt` from source data
- Manual override capability for reprocessing specific dates
- Propagates snapshot information through the entire pipeline
- Stores metadata in S3 for downstream job consumption

### Hive Bucketing
- Creates true Hive bucketed tables using Athena CTAS
- Optimizes join performance in Cleanroom queries
- Supports 256 buckets with `customer_user_id` as bucket key

### Partitioned Tables
- Creates partitioned tables for time-series data
- Uses MSCK REPAIR for automatic partition discovery
- Optimizes query performance for date-range filters

### Environment Support
- Separate dev and production configurations
- Environment-specific S3 buckets and IAM roles
- Consistent parameter handling across environments

## 📋 Production Jobs

### 1. Split and Bucket Jobs
- **Dev**: `etl-omc-flywheel-dev-infobase-split-and-bucket`
- **Dev**: `etl-omc-flywheel-dev-addressable-bucket`
- **Prod**: `etl-omc-flywheel-prod-infobase-split-and-bucket`
- **Prod**: `etl-omc-flywheel-prod-addressable-bucket`

**Purpose**: Process raw data with dynamic file sizing and bucketing
**Key Features**:
- S3A protocol for Spark compatibility
- Column name standardization
- Snapshot date auto-discovery
- Dynamic file sizing based on data volume

### 2. Register Staged Tables
- **Dev**: `etl-omc-flywheel-dev-register-staged-tables`
- **Prod**: `etl-omc-flywheel-prod-register-staged-tables`

**Purpose**: Create external tables in Glue Catalog from S3 parquet files
**Key Features**:
- Reads snapshot metadata from S3
- Adds snapshot information to table comments
- Supports both infobase_attributes and addressable_ids

### 3. Create Athena Bucketed Tables
- **Dev**: `etl-omc-flywheel-dev-create-athena-bucketed-tables`
- **Prod**: `etl-omc-flywheel-prod-create-athena-bucketed-tables`

**Purpose**: Generate true Hive bucketed tables using Athena CTAS
**Key Features**:
- Creates 256-bucket Hive tables
- Includes snapshot information in table comments
- Supports table filtering for testing
- Optimized for G.4X workers (10 workers)

## 🔧 Configuration

### Required Parameters
All jobs support these standard parameters:
- `--ENV`: Environment (dev/prod)
- `--SNAPSHOT_DT`: Snapshot date (default: `_NONE_` for auto-discovery)
- `--SOURCE_PATH`: Source S3 path
- `--TARGET_PATH`: Target S3 path

### Job-Specific Parameters
- **Athena Jobs**: `--TABLES_FILTER` (default: `_NONE_` for all tables)
- **Register Jobs**: `--STAGED_DB`, `--FINAL_DB`
- **Athena Jobs**: `--BUCKET_COUNT`, `--BUCKET_COL`

## 📊 Performance Optimizations

### Spark Configuration
- **Worker Type**: G.4X (production), G.1X (development)
- **Workers**: 10 (production), 2 (development)
- **Glue Version**: 5.0
- **Timeout**: 60 minutes

### File Sizing Logic
```python
# Calculate optimal file count based on data size
target_files = max(1, int(table_size_gb * 2))  # 2 files per GB
target_files = min(target_files, 256)  # Cap at 256 files
```

### Bucketing Strategy
- **Bucket Count**: 256 buckets
- **Bucket Key**: `customer_user_id`
- **File Format**: Parquet with Snappy compression

## 🔐 Security & Permissions

### IAM Roles
- **Dev**: `omc_flywheel-dev-glue-role`
- **Prod**: `omc_flywheel-prod-glue-role`

### Required Permissions
- S3: Read/write access to data buckets
- Athena: Query execution and result storage
- Glue: Catalog table management
- CloudWatch: Logging and metrics

## 📚 Documentation

- **[Process Flow](docs/CURRENT_PROCESS_FLOW.md)** - Detailed process flow and architecture
- **[Production Run Sequence](docs/PRODUCTION_RUN_SEQUENCE.md)** - Step-by-step production execution
- **[API Reference](docs/API_REFERENCE.md)** - API documentation and examples

## 🚀 Quick Start

### Development
```bash
# Run development jobs
aws glue start-job-run --job-name etl-omc-flywheel-dev-infobase-split-and-bucket
aws glue start-job-run --job-name etl-omc-flywheel-dev-addressable-bucket
aws glue start-job-run --job-name etl-omc-flywheel-dev-register-staged-tables
aws glue start-job-run --job-name etl-omc-flywheel-dev-create-athena-bucketed-tables
```

### Production
```bash
# Run production jobs
aws glue start-job-run --job-name etl-omc-flywheel-prod-infobase-split-and-bucket
aws glue start-job-run --job-name etl-omc-flywheel-prod-addressable-bucket
aws glue start-job-run --job-name etl-omc-flywheel-prod-register-staged-tables
aws glue start-job-run --job-name etl-omc-flywheel-prod-create-athena-bucketed-tables
```

## 🔍 Monitoring

### CloudWatch Logs
- Job execution logs: `/aws-glue/jobs/logs-v2/`
- Error tracking and debugging
- Performance metrics

### Key Metrics
- Job execution time
- Data processing volume
- File count optimization
- Error rates and retries

## 📈 Performance Results

### Before Optimization
- Fixed file counts (often over-partitioned)
- No bucketing for join optimization
- Manual snapshot management
- Inconsistent column naming

### After Optimization
- Dynamic file sizing (2 files per GB)
- 256-bucket Hive tables for join performance
- Automated snapshot tracking
- Standardized column naming
- 4-8x performance improvement for analytical queries

## 🛠️ Maintenance

### Monthly Runs
- Auto-discovery of latest snapshot dates
- Reprocessing capability for specific dates
- Idempotent operations for safe reruns

### Troubleshooting
- Check CloudWatch logs for errors
- Verify S3 permissions and paths
- Monitor Athena query performance
- Validate table schemas and data quality

## 📞 Support

For issues or questions:
1. Check CloudWatch logs for error details
2. Review job parameters and S3 paths
3. Verify IAM permissions
4. Consult documentation in `docs/` directory

---

**Last Updated**: October 2025  
**Version**: Production Ready  
**Environment**: AWS Glue 5.0, Spark 3.x