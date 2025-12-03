# Data Mapping Reference - OMC Flywheel Cleanroom

## 📋 Overview

This document provides comprehensive mapping information for the OMC Flywheel Cleanroom data processing pipelines, showing how input data maps to partitioned tables and the field-level transformations.

## 🔄 Pipeline Architecture

### **Pipeline 1: Bucketed Tables** (Original)
- **Purpose**: Cleanroom-optimized bucketed tables for join performance
- **Output**: `bucketed_*` tables in `split_cluster/` directory
- **Use Case**: Cleanroom queries requiring fast joins

### **Pipeline 2: Partitioned Tables** (New)
- **Purpose**: Time-series optimized partitioned tables
- **Output**: `part_*` tables in `split_part/` directory  
- **Use Case**: Analytics and date-range queries

---

## 📊 Addressable IDs Mapping

### **Simple 1:1 Mapping**
The addressable_ids data has a straightforward mapping:

| **Input** | **Output Table** | **Description** |
|-----------|------------------|-----------------|
| `addressable_ids` raw data | `part_addressable_ids` | Customer addressable ID mappings |
| `addressable_ids` raw data | `bucketed_addressable_ids` | Customer addressable ID mappings (bucketed) |

**Field Mapping:**
- **Input**: Single column from raw addressable_ids data
- **Output**: Same column structure in both partitioned and bucketed tables
- **Partition Key**: `snapshot_dt` (for partitioned tables)
- **Bucket Key**: `customer_user_id` (for bucketed tables)

---

## 🏗️ Infobase Attributes Mapping

### **Complex 28-Table Mapping**
The infobase_attributes data is split into 28 different tables based on business logic:

| **OMC Table** | **Partitioned Table** | **Bucketed Table** | **Record Count** | **Description** |
|---------------|------------------------|-------------------|------------------|-----------------|
| `IBE_01` | `part_ibe_01_a` | `bucketed_ibe_01_a` | 97 fields | Demographics & Education |
| `IBE_01_A` | `part_ibe_01_a` | `bucketed_ibe_01_a` | 65 fields | Demographics & Education (Extended) |
| `IBE_02` | `part_ibe_02_a` | `bucketed_ibe_02_a` | 93 fields | Financial & Credit |
| `IBE_02_A` | `part_ibe_02_a` | `bucketed_ibe_02_a` | 85 fields | Financial & Credit (Extended) |
| `IBE_03` | `part_ibe_03_a` | `bucketed_ibe_03_a` | 96 fields | Lifestyle & Interests |
| `IBE_03_A` | `part_ibe_03_a` | `bucketed_ibe_03_a` | 76 fields | Lifestyle & Interests (Extended) |
| `IBE_04` | `part_ibe_04_a` | `bucketed_ibe_04_a` | 87 fields | Household & Family |
| `IBE_04_A` | `part_ibe_04_a` | `bucketed_ibe_04_a` | 86 fields | Household & Family (Extended) |
| `IBE_04_B` | `part_ibe_04_b` | `bucketed_ibe_04_b` | 15 fields | Household & Family (Specialized) |
| `IBE_05` | `part_ibe_05_a` | `bucketed_ibe_05_a` | 95 fields | Technology & Digital |
| `IBE_05_A` | `part_ibe_05_a` | `bucketed_ibe_05_a` | 81 fields | Technology & Digital (Extended) |
| `IBE_06` | `part_ibe_06_a` | `bucketed_ibe_06_a` | 62 fields | Health & Wellness |
| `IBE_06_A` | `part_ibe_06_a` | `bucketed_ibe_06_a` | 51 fields | Health & Wellness (Extended) |
| `IBE_08` | `part_ibe_08_a` | `bucketed_ibe_08_a` | 3 fields | Specialized Attributes |
| `IBE_09` | `part_ibe_09_a` | `bucketed_ibe_09_a` | 87 fields | Advanced Demographics |
| `MIACS_01` | `part_miacs_01_a` | `bucketed_miacs_01_a` | 93 fields | Market Intelligence |
| `MIACS_01_A` | `part_miacs_01_a` | `bucketed_miacs_01_a` | 12 fields | Market Intelligence (Extended) |
| `MIACS_02` | `part_miacs_02_a` | `bucketed_miacs_02_a` | 98 fields | Consumer Segmentation |
| `MIACS_02_A` | `part_miacs_02_a` | `bucketed_miacs_02_a` | 100 fields | Consumer Segmentation (Extended) |
| `MIACS_02_B` | `part_miacs_02_b` | `bucketed_miacs_02_b` | 4 fields | Consumer Segmentation (Specialized) |
| `MIACS_03` | `part_miacs_03_a` | `bucketed_miacs_03_a` | 79 fields | Behavioral Analytics |
| `MIACS_03_A` | `part_miacs_03_a` | `bucketed_miacs_03_a` | 95 fields | Behavioral Analytics (Extended) |
| `MIACS_03_B` | `part_miacs_03_b` | `bucketed_miacs_03_b` | 29 fields | Behavioral Analytics (Specialized) |
| `MIACS_04` | `part_miacs_04_a` | `bucketed_miacs_04_a` | 23 fields | Advanced Analytics |
| `NEW_BORROWERS` | `part_new_borrowers` | `bucketed_new_borrowers` | 18 fields | New Borrower Attributes |
| `N_A` | `part_n_a` | `bucketed_n_a` | 88 fields | Not Applicable/Other |
| `N_A_A` | `part_n_a_a` | `bucketed_n_a_a` | 50 fields | Not Applicable/Other (Extended) |

---

## 🔧 Field-Level Mapping Details

### **Common Field Transformations**

| **Source Field** | **Target Field** | **Transformation** | **Description** |
|------------------|------------------|-------------------|-----------------|
| `CUSTOMER_USER_ID` | `customer_user_id` | Lowercase conversion | Primary key field |
| `IBE1802` | `ibe1802` | Direct mapping | Family Ties - Adult with Senior Parent |
| `IBE1900` | `ibe1900` | Direct mapping | College Year Grade Level |
| `IBE1901` | `ibe1901` | Direct mapping | Potential College Student |
| `IBE1902` | `ibe1902` | Direct mapping | High School Graduation Year |
| `IBE1903` | `ibe1903` | Direct mapping | College Student Major |
| `IBE1904` | `ibe1904` | Direct mapping | Student Commuter Flag |
| `IBE1905` | `ibe1905` | Direct mapping | College Graduation Year - Undergraduate |
| `IBE1906` | `ibe1906` | Direct mapping | College Graduation Year - Graduate |

### **Element Number Mapping**
Each field has an associated element number for reference:

| **Field** | **Element Number** | **Function Description** |
|-----------|-------------------|-------------------------|
| `customer_user_id` | `CUSTOMER_BASE_ID` | Customer User ID |
| `ibe1802` | `1802` | Family Ties - Adult with Senior Parent - Person |
| `ibe1900` | `1900` | College Year Grade Level |
| `ibe1901` | `1901` | Potential College Student |
| `ibe1902` | `1902` | High School Graduation Year |
| `ibe1903` | `1903` | College Student Major |
| `ibe1904` | `1904` | Student Commuter Flag |
| `ibe1905` | `1905` | College Graduation Year - Undergraduate |
| `ibe1906` | `1906` | College Graduation Year - Graduate |

---

## 📁 Data Path Structure

### **Partitioned Tables (Pipeline 2)**
```
s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_part/
├── infobase_attributes/
│   ├── IBE_01/
│   │   └── snapshot_dt=2024-01-15/
│   │       ├── part-00000.parquet
│   │       └── part-00001.parquet
│   ├── IBE_02/
│   │   └── snapshot_dt=2024-01-15/
│   └── ...
└── addressable_ids/
    └── snapshot_dt=2024-01-15/
        └── part-00000.parquet
```

### **Bucketed Tables (Pipeline 1)**
```
s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_cluster/
├── infobase_attributes/
│   ├── IBE_01/
│   │   └── v=20240115T120000Z/
│   │       ├── bucket-00000.parquet
│   │       ├── bucket-00001.parquet
│   │       └── ... (256 buckets)
│   └── ...
└── addressable_ids/
    └── v=20240115T120000Z/
        ├── bucket-00000.parquet
        └── ... (256 buckets)
```

---

## 🎯 Table Naming Conventions

### **Partitioned Tables**
- **Prefix**: `part_`
- **Pattern**: `part_{omc_table_name}_{suffix}`
- **Examples**: `part_ibe_01_a`, `part_miacs_02_b`, `part_addressable_ids`

### **Bucketed Tables**
- **Prefix**: `bucketed_`
- **Pattern**: `bucketed_{omc_table_name}_{suffix}`
- **Examples**: `bucketed_ibe_01_a`, `bucketed_miacs_02_b`, `bucketed_addressable_ids`

### **External Tables (Intermediate)**
- **Prefix**: `ext_`
- **Pattern**: `ext_{omc_table_name}_{suffix}`
- **Examples**: `ext_ibe_01_a`, `ext_miacs_02_b`, `ext_addressable_ids`

---

## 🔍 Query Examples

### **Partitioned Table Queries**
```sql
-- Query specific date range
SELECT * FROM omc_flywheel_prod.part_ibe_01_a 
WHERE snapshot_dt = '2024-01-15';

-- Query multiple tables with date filter
SELECT * FROM omc_flywheel_prod.part_ibe_01_a a
JOIN omc_flywheel_prod.part_ibe_02_a b 
ON a.customer_user_id = b.customer_user_id
WHERE a.snapshot_dt = '2024-01-15';
```

### **Bucketed Table Queries**
```sql
-- Cleanroom-optimized joins
SELECT * FROM omc_flywheel_prod.bucketed_ibe_01_a a
JOIN omc_flywheel_prod.bucketed_ibe_02_a b 
ON a.customer_user_id = b.customer_user_id;
```

---

## 📈 Performance Characteristics

### **Partitioned Tables**
- **Optimized for**: Date-range queries, time-series analytics
- **Partition Key**: `snapshot_dt`
- **Query Performance**: Fast for date filters, slower for cross-partition joins
- **Storage**: Efficient for historical data

### **Bucketed Tables**
- **Optimized for**: Join operations, Cleanroom queries
- **Bucket Key**: `customer_user_id` (256 buckets)
- **Query Performance**: Fast joins, optimized for Cleanroom
- **Storage**: More storage overhead due to bucketing

---

## 🛠️ Maintenance Operations

### **MSCK REPAIR (Partitioned Tables)**
```bash
# Run MSCK REPAIR on all partitioned tables
aws glue start-job-run --job-name etl-omc-flywheel-prod-prepare-part-tables
```

### **Table Registration**
```bash
# Register external tables for partitioned data
aws glue start-job-run --job-name etl-omc-flywheel-prod-register-part-tables

# Register external tables for bucketed data  
aws glue start-job-run --job-name etl-omc-flywheel-prod-register-staged-tables
```

---

## 📋 Summary

This mapping document provides complete visibility into:
- ✅ **28 infobase tables** with field-level mappings
- ✅ **1 addressable_ids table** with simple mapping
- ✅ **Dual pipeline architecture** (partitioned vs bucketed)
- ✅ **Field transformations** and element number mappings
- ✅ **Data path structures** for both pipelines
- ✅ **Query examples** and performance characteristics
- ✅ **Maintenance operations** for ongoing management

The mapping ensures data lineage transparency and supports both analytical queries (partitioned) and Cleanroom operations (bucketed).
