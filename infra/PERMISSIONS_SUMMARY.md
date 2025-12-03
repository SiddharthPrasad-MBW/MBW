# Lake Formation Permissions Summary

## 📋 **Permission Model Overview**

The Lake Formation module implements a **separation of concerns** model with distinct **Writer** and **Reader** principals:

- **Writer Principals**: Glue job roles with full permissions for CTAS operations
- **Reader Principals**: Cleanroom consumers with read-only access to bucketed tables

## 🔐 **Writer Principals (Glue Job Roles)**

### **Database-Level Permissions**

| Permission | Purpose | Applies To |
|------------|---------|------------|
| `CREATE_TABLE` | Create new tables (bucketed_*) | Database |
| `ALTER` | Modify table schemas | Database |
| `DROP` | Delete tables | Database |
| `DESCRIBE` | View table metadata | Database |

### **Table-Level Permissions (Wildcard - All Tables)**

| Permission | Purpose | Applies To |
|------------|---------|------------|
| `SELECT` | Read data from tables | All tables (ext_* and bucketed_*) |
| `DESCRIBE` | View table structure | All tables (ext_* and bucketed_*) |
| `INSERT` | Write data to tables | All tables (including bucketed_*) |
| `ALTER` | Modify table metadata | All tables |

### **Data Location Permissions**

| Permission | Purpose | Applies To |
|------------|---------|------------|
| `DATA_LOCATION_ACCESS` | Access S3 data | Source bucket (split_cluster/) |
| `DATA_LOCATION_ACCESS` | Access S3 data | Target bucket (bucketed/) |

**Writer Roles**:
- `omc_flywheel-dev-glue-role` (development)
- `omc_flywheel-prod-glue-role` (production)

## 📖 **Reader Principals (Cleanroom Consumers)**

### **Table-Level Permissions (Wildcard - All Tables)**

| Permission | Purpose | Applies To |
|------------|---------|------------|
| `SELECT` | Read data from tables | All tables (bucketed_*) |
| `DESCRIBE` | View table structure | All tables (bucketed_*) |

### **Data Location Permissions**

| Permission | Purpose | Applies To |
|------------|---------|------------|
| `DATA_LOCATION_ACCESS` | Access S3 data | Target bucket (bucketed/) only |

### **Reader Restrictions**

**Reader Roles CANNOT**:
- ❌ CREATE_TABLE, ALTER, DROP tables
- ❌ INSERT data into tables
- ❌ Write to data buckets
- ❌ Access source data (split_cluster/, opus/)

**Reader Roles**:
- `omc_flywheel-dev-cleanroom-consumer` (development)
- `omc_flywheel-prod-cleanroom-consumer` (production)

## 🔄 **CTAS Operation Flow**

### **Writer Role: Reading from ext_* Tables**
1. ✅ **SELECT** permission (via wildcard) - allows reading data
2. ✅ **DESCRIBE** permission (via wildcard) - allows table structure access
3. ✅ **DATA_LOCATION_ACCESS** on source bucket - allows S3 access

### **Writer Role: Writing to bucketed_* Tables**
1. ✅ **CREATE_TABLE** permission (database-level) - allows creating table
2. ✅ **INSERT** permission (via wildcard) - allows writing data
3. ✅ **ALTER** permission (via wildcard) - allows modifying table during creation
4. ✅ **DATA_LOCATION_ACCESS** on target bucket - allows S3 write access

### **Reader Role: Reading from bucketed_* Tables**
1. ✅ **SELECT** permission (via wildcard) - allows reading data
2. ✅ **DESCRIBE** permission (via wildcard) - allows table structure access
3. ✅ **DATA_LOCATION_ACCESS** on target bucket - allows S3 read access

## ✅ **Coverage Summary**

### **ext_* Tables (Source Tables)**

**Writer Access**:
- ✅ **SELECT** - Can read data for CTAS
- ✅ **DESCRIBE** - Can access table structure
- ✅ **DATA_LOCATION_ACCESS** - Can access underlying S3 data

**Reader Access**:
- ❌ No access (readers don't need source tables)

### **bucketed_* Tables (Target Tables)**

**Writer Access**:
- ✅ **CREATE_TABLE** - Can create tables via CTAS
- ✅ **INSERT** - Can write data during CTAS
- ✅ **ALTER** - Can modify table structure
- ✅ **DROP** - Can delete/recreate tables
- ✅ **SELECT** - Can read back data (for verification)
- ✅ **DESCRIBE** - Can access table structure
- ✅ **DATA_LOCATION_ACCESS** - Can write to S3 location

**Reader Access**:
- ✅ **SELECT** - Can read data for analytics
- ✅ **DESCRIBE** - Can access table structure
- ✅ **DATA_LOCATION_ACCESS** - Can read from S3 location
- ❌ **No CREATE_TABLE** - Cannot create tables
- ❌ **No INSERT** - Cannot write data
- ❌ **No ALTER/DROP** - Cannot modify tables

## 🎯 **Permission Model**

### **Wildcard Approach**
- Uses `wildcard = true` to apply permissions to all tables
- Simpler than enumerating individual tables
- Automatically covers new tables created in the database

### **Principle of Least Privilege**
- **Writers**: Full permissions needed for CTAS operations
- **Readers**: Minimal permissions for read-only access
- **Separation**: Clear distinction between data producers and consumers

### **Security Considerations**
- Wildcard applies to ALL tables in the database
- Writers have INSERT on ext_* tables (harmless for external tables)
- Readers have no write permissions whatsoever
- Permissions are scoped to the specific database only

## 🔍 **Verification**

To verify permissions are correctly applied:

```bash
# Check permissions for Writer role (Glue job role)
aws lakeformation list-permissions \
  --principal "arn:aws:iam::ACCOUNT_ID:role/omc_flywheel-dev-glue-role" \
  --region us-east-1 --profile flywheel-dev

# Should show:
# - Database: CREATE_TABLE, ALTER, DROP, DESCRIBE
# - Table (wildcard): SELECT, DESCRIBE, INSERT, ALTER
# - Data Location: DATA_LOCATION_ACCESS (source and target buckets)

# Check permissions for Reader role (Cleanroom consumer)
aws lakeformation list-permissions \
  --principal "arn:aws:iam::ACCOUNT_ID:role/omc_flywheel-dev-cleanroom-consumer" \
  --region us-east-1 --profile flywheel-dev

# Should show:
# - Table (wildcard): SELECT, DESCRIBE only
# - Data Location: DATA_LOCATION_ACCESS (target bucket only)
```

## 📚 **Related Documentation**

- [Lake Formation Infrastructure README](README.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Consumer Role IAM Policies](CONSUMER_ROLE_IAM_POLICIES.md)
- [Testing Plan](../LAKE_FORMATION_FIX_TESTING_PLAN.md)

---

**Last Updated**: October 28, 2025  
**Status**: Permissions configured with writer/reader separation  
**Coverage**: ✅ Writers (full access) + Readers (read-only)