# OMC Table Mapping Reference

## 📋 Overview

This document provides a simplified mapping of OMC tables to their columns and functional descriptions for the OMC Flywheel Cleanroom data processing.

## 🔄 Pipeline Mapping

### **Addressable IDs**
| **OMC Table** | **OMC Column** | **Functional Description** |
|---------------|----------------|---------------------------|
| `addressable_ids` | `customer_user_id` | Customer User ID |

### **Infobase Attributes (28 Tables)**

| **OMC Table** | **OMC Column** | **Functional Description** |
|---------------|----------------|---------------------------|
| **IBE_01** | `customer_user_id` | Customer User ID |
| **IBE_01** | `ibe1802` | Family Ties - Adult with Senior Parent - Person |
| **IBE_01** | `ibe1900` | College Year Grade Level |
| **IBE_01** | `ibe1901` | Potential College Student |
| **IBE_01** | `ibe1902` | High School Graduation Year |
| **IBE_01** | `ibe1903` | College Student Major |
| **IBE_01** | `ibe1904` | Student Commuter Flag |
| **IBE_01** | `ibe1905` | College Graduation Year - Undergraduate |
| **IBE_01** | `ibe1906` | College Graduation Year - Graduate |
| **IBE_01** | `ibe1907` | Recent Graduate |
| **IBE_01** | `ibe2005` | Women's Plus Sizes |
| **IBE_01** | `ibe2022` | Category - Apparel - Women's |
| **IBE_01** | `ibe2024` | Super Category - Arts and Antiques |
| **IBE_01** | `ibe2025` | Super Category - Automotive |
| **IBE_01** | `ibe2026` | Super Category - Books and Music |
| **IBE_01** | `ibe2029` | Super Category - Food and Beverage |
| **IBE_01** | `ibe2030` | Super Category - Health and Beauty |
| **IBE_01** | `ibe2031` | Super Category - Home Furnishing |
| **IBE_01** | `ibe2033` | Category - Music |
| **IBE_01** | `ibe2058_01` | Credit Card Use - American Express - Premium |
| **IBE_01** | `ibe2058_02` | Credit Card Use - American Express - Regular |
| **IBE_01** | `ibe2059_01` | Credit Card Use - Discover - Premium |
| **IBE_01** | `ibe2059_02` | Credit Card Use - Discover - Regular |
| **IBE_01** | `ibe2060_01` | Credit Card Use - Gasoline or Retail Card - Premium |
| **IBE_01** | `ibe2060_02` | Credit Card Use - Gasoline or Retail Card - Regular |
| **IBE_01** | `ibe2061_01` | Credit Card Use - Mastercard - Premium |
| **IBE_01** | `ibe2061_02` | Credit Card Use - Mastercard - Regular |
| **IBE_01** | `ibe2062_01` | Credit Card Use - Visa - Premium |
| **IBE_01** | `ibe2062_02` | Credit Card Use - Visa - Regular |
| **IBE_01** | `ibe2076_01` | Causes Supported Financially - Charitable |
| **IBE_01** | `ibe2076_02` | Causes Supported Financially - Animal Welfare |
| **IBE_01** | `ibe2076_03` | Causes Supported Financially - Arts or Cultural |
| **IBE_01** | `ibe2076_04` | Causes Supported Financially - Childrens |
| **IBE_01** | `ibe2076_05` | Causes Supported Financially - Environment or Wildlife |
| **IBE_01** | `ibe2076_06` | Causes Supported Financially - Health |
| **IBE_01** | `ibe2076_07` | Causes Supported Financially - International Aid |
| **IBE_01** | `ibe2076_08` | Causes Supported Financially - Political |
| **IBE_01** | `ibe2076_09` | Causes Supported Financially - Politically Conservative |
| **IBE_01** | `ibe2076_10` | Causes Supported Financially - Politically Liberal |
| **IBE_01** | `ibe2076_11` | Causes Supported Financially - Religious |
| **IBE_01** | `ibe2076_12` | Causes Supported Financially - Veterans |
| **IBE_01** | `ibe2076_13` | Causes Supported Financially - Other |
| **IBE_01** | `ibe2077` | Auto Enthusiast |
| **IBE_01** | `ibe2100` | Ethnic Group |
| **IBE_01** | `ibe2205` | Health - Homeopathic Interest in Household |
| **IBE_01** | `ibe2350` | Business Owner |
| **IBE_01** | `ibe2351` | Single Parent |
| **IBE_01** | `ibe2354` | Life Insurance Policy Owner |
| **IBE_01** | `ibe2356` | Veteran |

*Note: This shows a sample of IBE_01 fields. The complete mapping contains 1,768 total field mappings across all 28 tables. For the complete field list, refer to the `omc_flywheel_infobase_table_split_part.csv` file.*

## 📊 Table Summary

| **OMC Table** | **Field Count** | **Primary Purpose** |
|---------------|-----------------|-------------------|
| `IBE_01` | 97 | Demographics & Education |
| `IBE_01_A` | 65 | Demographics & Education (Extended) |
| `IBE_02` | 93 | Financial & Credit |
| `IBE_02_A` | 85 | Financial & Credit (Extended) |
| `IBE_03` | 96 | Lifestyle & Interests |
| `IBE_03_A` | 76 | Lifestyle & Interests (Extended) |
| `IBE_04` | 87 | Household & Family |
| `IBE_04_A` | 86 | Household & Family (Extended) |
| `IBE_04_B` | 15 | Household & Family (Specialized) |
| `IBE_05` | 95 | Technology & Digital |
| `IBE_05_A` | 81 | Technology & Digital (Extended) |
| `IBE_06` | 62 | Health & Wellness |
| `IBE_06_A` | 51 | Health & Wellness (Extended) |
| `IBE_08` | 3 | Specialized Attributes |
| `IBE_09` | 87 | Advanced Demographics |
| `MIACS_01` | 93 | Market Intelligence |
| `MIACS_01_A` | 12 | Market Intelligence (Extended) |
| `MIACS_02` | 98 | Consumer Segmentation |
| `MIACS_02_A` | 100 | Consumer Segmentation (Extended) |
| `MIACS_02_B` | 4 | Consumer Segmentation (Specialized) |
| `MIACS_03` | 79 | Behavioral Analytics |
| `MIACS_03_A` | 95 | Behavioral Analytics (Extended) |
| `MIACS_03_B` | 29 | Behavioral Analytics (Specialized) |
| `MIACS_04` | 23 | Advanced Analytics |
| `NEW_BORROWERS` | 18 | New Borrower Attributes |
| `N_A` | 88 | Not Applicable/Other |
| `N_A_A` | 50 | Not Applicable/Other (Extended) |

## 🎯 Output Tables

### **Partitioned Tables (Pipeline 2)**
- `part_ibe_01_a`, `part_ibe_02_a`, `part_ibe_03_a`, etc.
- `part_miacs_01_a`, `part_miacs_02_a`, `part_miacs_03_a`, etc.
- `part_addressable_ids`

### **Bucketed Tables (Pipeline 1)**
- `bucketed_ibe_01_a`, `bucketed_ibe_02_a`, `bucketed_ibe_03_a`, etc.
- `bucketed_miacs_01_a`, `bucketed_miacs_02_a`, `bucketed_miacs_03_a`, etc.
- `bucketed_addressable_ids`

---

## 📋 Complete Field Mapping

To get the complete field mapping for all tables, you can extract it from the CSV file:

```bash
# Download the complete mapping file
aws s3 cp s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/support_files/omc_flywheel_infobase_table_split_part.csv . --profile flywheel-prod

# Extract just the OMC table, column, and description
cut -d',' -f1,2,3 omc_flywheel_infobase_table_split_part.csv > omc_mapping.csv

# View specific table fields
grep "^IBE_01," omc_mapping.csv
grep "^MIACS_01," omc_mapping.csv
```

## 🔍 Field Categories

The fields fall into several main categories:
- **Demographics**: Age, gender, ethnicity, education
- **Financial**: Credit card usage, income, spending patterns
- **Lifestyle**: Interests, hobbies, causes supported
- **Household**: Family structure, home ownership
- **Technology**: Digital behavior, online activity
- **Health**: Wellness interests, medical conditions
- **Market Intelligence**: Consumer segmentation, behavioral analytics

---

*This mapping is based on the `omc_flywheel_infobase_table_split_part.csv` configuration file used by the Glue ETL jobs.*
