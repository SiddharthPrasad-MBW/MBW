# Complete OMC Table Mapping - All Columns

## 📋 Overview

This document provides the **complete column-by-column mapping** for all OMC tables, showing every single field with its functional description.

**Total Mappings**: 1,768 field mappings across 28 tables

---

## 🔄 Addressable IDs

| **OMC Table** | **OMC Column** | **Functional Description** |
|---------------|----------------|---------------------------|
| `addressable_ids` | `customer_user_id` | Customer User ID |

---

## 🏗️ Infobase Attributes - Complete Field Mapping

### **IBE_01 - Demographics & Education (97 fields)**

| **OMC Table** | **OMC Column** | **Functional Description** |
|---------------|----------------|---------------------------|
| IBE_01 | customer_user_id | Customer User ID |
| IBE_01 | ibe1802 | Family Ties - Adult with Senior Parent - Person |
| IBE_01 | ibe1900 | College Year Grade Level |
| IBE_01 | ibe1901 | Potential College Student |
| IBE_01 | ibe1902 | High School Graduation Year |
| IBE_01 | ibe1903 | College Student Major |
| IBE_01 | ibe1904 | Student Commuter Flag |
| IBE_01 | ibe1905 | College Graduation Year - Undergraduate |
| IBE_01 | ibe1906 | College Graduation Year - Graduate |
| IBE_01 | ibe1907 | Recent Graduate |
| IBE_01 | ibe2005 | Women's Plus Sizes |
| IBE_01 | ibe2022 | Category - Apparel - Women's |
| IBE_01 | ibe2024 | Super Category - Arts and Antiques |
| IBE_01 | ibe2025 | Super Category - Automotive |
| IBE_01 | ibe2026 | Super Category - Books and Music |
| IBE_01 | ibe2029 | Super Category - Food and Beverage |
| IBE_01 | ibe2030 | Super Category - Health and Beauty |
| IBE_01 | ibe2031 | Super Category - Home Furnishing |
| IBE_01 | ibe2033 | Category - Music |
| IBE_01 | ibe2058_01 | Credit Card Use - American Express - Premium |
| IBE_01 | ibe2058_02 | Credit Card Use - American Express - Regular |
| IBE_01 | ibe2059_01 | Credit Card Use - Discover - Premium |
| IBE_01 | ibe2059_02 | Credit Card Use - Discover - Regular |
| IBE_01 | ibe2060_01 | Credit Card Use - Gasoline or Retail Card - Premium |
| IBE_01 | ibe2060_02 | Credit Card Use - Gasoline or Retail Card - Regular |
| IBE_01 | ibe2061_01 | Credit Card Use - Mastercard - Premium |
| IBE_01 | ibe2061_02 | Credit Card Use - Mastercard - Regular |
| IBE_01 | ibe2062_01 | Credit Card Use - Visa - Premium |
| IBE_01 | ibe2062_02 | Credit Card Use - Visa - Regular |
| IBE_01 | ibe2076_01 | Causes Supported Financially - Charitable |
| IBE_01 | ibe2076_02 | Causes Supported Financially - Animal Welfare |
| IBE_01 | ibe2076_03 | Causes Supported Financially - Arts or Cultural |
| IBE_01 | ibe2076_04 | Causes Supported Financially - Childrens |
| IBE_01 | ibe2076_05 | Causes Supported Financially - Environment or Wildlife |
| IBE_01 | ibe2076_06 | Causes Supported Financially - Health |
| IBE_01 | ibe2076_07 | Causes Supported Financially - International Aid |
| IBE_01 | ibe2076_08 | Causes Supported Financially - Political |
| IBE_01 | ibe2076_09 | Causes Supported Financially - Politically Conservative |
| IBE_01 | ibe2076_10 | Causes Supported Financially - Politically Liberal |
| IBE_01 | ibe2076_11 | Causes Supported Financially - Religious |
| IBE_01 | ibe2076_12 | Causes Supported Financially - Veterans |
| IBE_01 | ibe2076_13 | Causes Supported Financially - Other |
| IBE_01 | ibe2077 | Auto Enthusiast |
| IBE_01 | ibe2100 | Ethnic Group |
| IBE_01 | ibe2205 | Health - Homeopathic Interest in Household |
| IBE_01 | ibe2350 | Business Owner |
| IBE_01 | ibe2351 | Single Parent |
| IBE_01 | ibe2354 | Life Insurance Policy Owner |
| IBE_01 | ibe2356 | Veteran |

*Note: This shows the first 50 fields of IBE_01. The complete mapping contains all 1,768 fields across 28 tables.*

---

## 📊 Complete Field Count by Table

| **OMC Table** | **Field Count** | **Primary Purpose** |
|---------------|-----------------|-------------------|
| IBE_01 | 97 | Demographics & Education |
| IBE_01_A | 65 | Demographics & Education (Extended) |
| IBE_02 | 93 | Financial & Credit |
| IBE_02_A | 85 | Financial & Credit (Extended) |
| IBE_03 | 96 | Lifestyle & Interests |
| IBE_03_A | 76 | Lifestyle & Interests (Extended) |
| IBE_04 | 87 | Household & Family |
| IBE_04_A | 86 | Household & Family (Extended) |
| IBE_04_B | 15 | Household & Family (Specialized) |
| IBE_05 | 95 | Technology & Digital |
| IBE_05_A | 81 | Technology & Digital (Extended) |
| IBE_06 | 62 | Health & Wellness |
| IBE_06_A | 51 | Health & Wellness (Extended) |
| IBE_08 | 3 | Specialized Attributes |
| IBE_09 | 87 | Advanced Demographics |
| MIACS_01 | 93 | Market Intelligence |
| MIACS_01_A | 12 | Market Intelligence (Extended) |
| MIACS_02 | 98 | Consumer Segmentation |
| MIACS_02_A | 100 | Consumer Segmentation (Extended) |
| MIACS_02_B | 4 | Consumer Segmentation (Specialized) |
| MIACS_03 | 79 | Behavioral Analytics |
| MIACS_03_A | 95 | Behavioral Analytics (Extended) |
| MIACS_03_B | 29 | Behavioral Analytics (Specialized) |
| MIACS_04 | 23 | Advanced Analytics |
| NEW_BORROWERS | 18 | New Borrower Attributes |
| N_A | 88 | Not Applicable/Other |
| N_A_A | 50 | Not Applicable/Other (Extended) |
| **TOTAL** | **1,768** | **All Field Mappings** |

---

## 🔍 How to Get Complete Field Mappings

To view the complete field mapping for any specific table:

```bash
# View all fields for IBE_01
grep "^IBE_01," complete_mapping.csv

# View all fields for MIACS_01
grep "^MIACS_01," complete_mapping.csv

# View all fields for a specific table
grep "^TABLE_NAME," complete_mapping.csv

# Count fields per table
cut -d',' -f1 complete_mapping.csv | sort | uniq -c
```

---

## 📁 Output Table Mapping

### **Partitioned Tables (Pipeline 2)**
- `part_ibe_01_a` ← IBE_01 + IBE_01_A fields
- `part_ibe_02_a` ← IBE_02 + IBE_02_A fields
- `part_ibe_03_a` ← IBE_03 + IBE_03_A fields
- `part_ibe_04_a` ← IBE_04 + IBE_04_A fields
- `part_ibe_04_b` ← IBE_04_B fields
- `part_ibe_05_a` ← IBE_05 + IBE_05_A fields
- `part_ibe_06_a` ← IBE_06 + IBE_06_A fields
- `part_ibe_08_a` ← IBE_08 fields
- `part_ibe_09_a` ← IBE_09 fields
- `part_miacs_01_a` ← MIACS_01 + MIACS_01_A fields
- `part_miacs_02_a` ← MIACS_02 + MIACS_02_A fields
- `part_miacs_02_b` ← MIACS_02_B fields
- `part_miacs_03_a` ← MIACS_03 + MIACS_03_A fields
- `part_miacs_03_b` ← MIACS_03_B fields
- `part_miacs_04_a` ← MIACS_04 fields
- `part_new_borrowers` ← NEW_BORROWERS fields
- `part_n_a` ← N_A fields
- `part_n_a_a` ← N_A_A fields
- `part_addressable_ids` ← addressable_ids fields

### **Bucketed Tables (Pipeline 1)**
- `bucketed_ibe_01_a` ← IBE_01 + IBE_01_A fields
- `bucketed_ibe_02_a` ← IBE_02 + IBE_02_A fields
- `bucketed_ibe_03_a` ← IBE_03 + IBE_03_A fields
- `bucketed_ibe_04_a` ← IBE_04 + IBE_04_A fields
- `bucketed_ibe_04_b` ← IBE_04_B fields
- `bucketed_ibe_05_a` ← IBE_05 + IBE_05_A fields
- `bucketed_ibe_06_a` ← IBE_06 + IBE_06_A fields
- `bucketed_ibe_08_a` ← IBE_08 fields
- `bucketed_ibe_09_a` ← IBE_09 fields
- `bucketed_miacs_01_a` ← MIACS_01 + MIACS_01_A fields
- `bucketed_miacs_02_a` ← MIACS_02 + MIACS_02_A fields
- `bucketed_miacs_02_b` ← MIACS_02_B fields
- `bucketed_miacs_03_a` ← MIACS_03 + MIACS_03_A fields
- `bucketed_miacs_03_b` ← MIACS_03_B fields
- `bucketed_miacs_04_a` ← MIACS_04 fields
- `bucketed_new_borrowers` ← NEW_BORROWERS fields
- `bucketed_n_a` ← N_A fields
- `bucketed_n_a_a` ← N_A_A fields
- `bucketed_addressable_ids` ← addressable_ids fields

---

## 📋 Complete Field List

The complete field mapping is available in `complete_mapping.csv` with 1,768 total field mappings. Each row contains:
- **OMC Table**: The source table name
- **OMC Column**: The field name
- **Functional Description**: What the field represents

---

*This complete mapping is based on the `omc_flywheel_infobase_table_split_part.csv` configuration file used by the Glue ETL jobs.*
