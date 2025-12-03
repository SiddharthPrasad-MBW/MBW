# Infrastructure Overview

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    AWS Account: 239083076653                   │
│                         Region: us-east-1                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   S3 Buckets    │    │   Glue Jobs     │    │  Glue Crawlers  │
│                 │    │                 │    │                 │
│ • Data Storage  │◄───┤ • ETL Processing│◄───┤ • Schema Discovery│
│ • Scripts       │    │ • Data Transform│    │ • Auto Catalog  │
│ • Analysis      │    │ • Cleanroom     │    │ • Partition Mgmt│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Glue Databases │
                    │                 │
                    │ • Data Catalog  │
                    │ • Schema Store  │
                    │ • Metadata Mgmt │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   IAM Role      │
                    │                 │
                    │ • Glue Service  │
                    │ • S3 Access     │
                    │ • Permissions   │
                    └─────────────────┘
```

## 📊 Resource Relationships

### Data Flow
1. **Raw Data** → S3 Buckets (`omc-flywheel-data-us-east-1-prod`)
2. **Glue Crawlers** → Discover schema and create tables
3. **Glue Jobs** → Process and transform data
4. **Glue Databases** → Store metadata and schema
5. **Processed Data** → Back to S3 for consumption

### Dependencies
- **Glue Jobs** depend on **IAM Role** for execution
- **Glue Crawlers** depend on **IAM Role** and **S3 Buckets**
- **Glue Databases** are independent but used by crawlers
- **S3 Buckets** are independent storage

## 🔧 Configuration Details

### Glue Jobs Configuration

#### Job 1: Addressable IDs Compaction
- **Purpose**: Process addressable ID data
- **Worker Type**: G.1X
- **Workers**: 8
- **Timeout**: 600 minutes
- **Script**: `etl-omc-flywheel-prod-addressable-ids-compaction.py`

#### Job 2: Infobase Attributes Compaction
- **Purpose**: Process infobase attributes data
- **Worker Type**: G.1X (downgraded from G.4X)
- **Workers**: 24
- **Timeout**: 600 minutes (reduced from 2880)
- **Script**: `etl-omc-flywheel-prod-infobase-attributes-compaction.py`

#### Job 3: Infobase Cleanroom from CSV
- **Purpose**: Create cleanroom tables from CSV
- **Worker Type**: G.1X (downgraded from G.4X)
- **Workers**: 24
- **Timeout**: 600 minutes (reduced from 2880)
- **Script**: `etl-omc-flywheel-prod-infobase-cleanroom-from-csv.py`

### S3 Bucket Configuration

#### Main Data Bucket
- **Name**: `omc-flywheel-data-us-east-1-prod`
- **Purpose**: Store raw and processed data
- **Structure**:
  - `opus/` - Raw input data
  - `omc_cleanroom_data/` - Processed data
  - `support_files/` - Configuration files

#### Glue Assets Bucket
- **Name**: `aws-glue-assets-239083076653-us-east-1`
- **Purpose**: Store Glue scripts and temporary files
- **Structure**:
  - `scripts/` - ETL scripts
  - `temporary/` - Temp processing files
  - `sparkHistoryLogs/` - Spark execution logs

#### Analysis Data Bucket
- **Name**: `omc-flywheel-prod-analysis-data`
- **Purpose**: Analysis results and temporary processing
- **Structure**:
  - `temp/` - Temporary analysis files
  - `spark-logs/` - Spark execution logs

### Glue Crawler Configuration

#### Crawler 1: Addressable IDs Compaction
- **Target**: `s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/addressable/addressable_ids_compaction_cr/`
- **Database**: `omc_flywheel_prod`
- **Schema Policy**: Update in database, log deletions

#### Crawler 2: Infobase Attributes Compaction
- **Target**: `s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/infobase_attributes/infobase_attributes_compaction_cr/`
- **Database**: `omc_flywheel_prod`
- **Schema Policy**: Update in database, log deletions

#### Crawler 3: Raw Input Addressable
- **Target**: `s3://omc-flywheel-data-us-east-1-prod/opus/addressable_ids/raw_input/`
- **Database**: `omc_flywheel_prod`
- **Table Prefix**: `addressable_`
- **Schema Policy**: Update in database, log deletions

#### Crawler 4: Raw Input Infobase
- **Target**: `s3://omc-flywheel-data-us-east-1-prod/opus/infobase_attributes/raw_input/`
- **Database**: `omc_flywheel_prod`
- **Table Prefix**: `infobase_attributes_`
- **Schema Policy**: Update in database, log deletions

## 🔒 Security Configuration

### IAM Role Permissions
The `omc_flywheel-prod-glue-role` has the following permissions:
- **Glue Service**: Full access to Glue operations
- **S3 Access**: Read/write to project buckets
- **CloudWatch Logs**: Write execution logs
- **CloudWatch Metrics**: Publish job metrics

### S3 Bucket Policies
- **Data Bucket**: Restricted access to Glue role and authorized users
- **Assets Bucket**: Glue service access for script execution
- **Analysis Bucket**: Temporary data with lifecycle policies

## 📈 Performance Optimization

### Glue Job Optimizations
- **Worker Type**: Standardized to G.1X for cost efficiency
- **Timeout**: Reduced from 48 hours to 10 hours
- **Retries**: Set to 2 for fault tolerance
- **Spark Configuration**: Optimized for data processing

### S3 Optimizations
- **Lifecycle Policies**: Automatic cleanup of temporary files
- **Storage Classes**: Intelligent tiering for cost optimization
- **Encryption**: Server-side encryption enabled

## 🔄 Data Pipeline Flow

```
Raw Data (S3) → Crawlers → Tables (Glue Catalog) → Jobs → Processed Data (S3)
     │              │              │                │              │
     │              │              │                │              │
     ▼              ▼              ▼                ▼              ▼
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  Input  │    │ Schema  │    │Metadata │    │Transform│    │ Output  │
│  Files  │    │Discovery│    │ Storage │    │ Process │    │  Files  │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
```

## 🚨 Monitoring and Alerting

### Key Metrics to Monitor
- **Glue Job Success Rate**: Track job completion rates
- **Processing Time**: Monitor job execution duration
- **Data Volume**: Track input/output data sizes
- **Error Rates**: Monitor failed job runs

### Recommended Alerts
- Job failure notifications
- Long-running job alerts
- S3 storage threshold alerts
- Crawler execution failures

## 💰 Cost Optimization

### Current Configuration
- **Worker Types**: Standardized to G.1X (cost-effective)
- **Timeouts**: Reduced to prevent unnecessary charges
- **S3 Lifecycle**: Automatic cleanup of temporary files

### Cost Monitoring
- Use AWS Cost Explorer to track spending
- Set up billing alerts for budget management
- Review resource utilization monthly

---

**Last Updated**: October 17, 2025  
**Environment**: Production  
**Account**: 239083076653
