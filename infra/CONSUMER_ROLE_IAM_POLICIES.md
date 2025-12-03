# IAM Policies for Cleanroom Consumer Role

This document contains IAM policy templates for the Cleanroom consumer role (`omc-flywheel-*-cleanroom-consumer`) that provides read-only access to bucketed tables.

## 📋 **Policy 1: Data Prefix Read-Only (Dev)**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListBucketBucketed",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::omc-flywheel-data-us-east-1-dev",
      "Condition": {
        "StringLike": {
          "s3:prefix": "omc_cleanroom_data/cleanroom_tables/bucketed/*"
        }
      }
    },
    {
      "Sid": "ReadBucketedOnly",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:GetObjectTagging"],
      "Resource": "arn:aws:s3:::omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/cleanroom_tables/bucketed/*"
    }
  ]
}
```

## 📋 **Policy 1: Data Prefix Read-Only (Prod)**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListBucketBucketed",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::omc-flywheel-data-us-east-1-prod",
      "Condition": {
        "StringLike": {
          "s3:prefix": "omc_cleanroom_data/cleanroom_tables/bucketed/*"
        }
      }
    },
    {
      "Sid": "ReadBucketedOnly",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:GetObjectTagging"],
      "Resource": "arn:aws:s3:::omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/cleanroom_tables/bucketed/*"
    }
  ]
}
```

## 📋 **Policy 2: Athena Results Write (Dev)**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AthenaResultsWrite",
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::omc-flywheel-dev-analysis-data",
        "arn:aws:s3:::omc-flywheel-dev-analysis-data/query-results/cleanroom/*"
      ]
    },
    {
      "Sid": "AthenaAPI",
      "Effect": "Allow",
      "Action": [
        "athena:StartQueryExecution",
        "athena:GetQueryExecution",
        "athena:GetQueryResults",
        "athena:ListWorkGroups",
        "athena:GetWorkGroup",
        "athena:StopQueryExecution"
      ],
      "Resource": "*"
    },
    {
      "Sid": "GlueCatalogRead",
      "Effect": "Allow",
      "Action": [
        "glue:GetDatabase",
        "glue:GetDatabases",
        "glue:GetTable",
        "glue:GetTables",
        "glue:GetPartitions"
      ],
      "Resource": "*"
    }
  ]
}
```

## 📋 **Policy 2: Athena Results Write (Prod)**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AthenaResultsWrite",
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::omc-flywheel-prod-analysis-data",
        "arn:aws:s3:::omc-flywheel-prod-analysis-data/query-results/cleanroom/*"
      ]
    },
    {
      "Sid": "AthenaAPI",
      "Effect": "Allow",
      "Action": [
        "athena:StartQueryExecution",
        "athena:GetQueryExecution",
        "athena:GetQueryResults",
        "athena:ListWorkGroups",
        "athena:GetWorkGroup",
        "athena:StopQueryExecution"
      ],
      "Resource": "*"
    },
    {
      "Sid": "GlueCatalogRead",
      "Effect": "Allow",
      "Action": [
        "glue:GetDatabase",
        "glue:GetDatabases",
        "glue:GetTable",
        "glue:GetTables",
        "glue:GetPartitions"
      ],
      "Resource": "*"
    }
  ]
}
```

## 🔧 **How to Apply These Policies**

### **Step 1: Create the Consumer Role**

```bash
# Dev environment
aws iam create-role \
  --role-name omc_flywheel-dev-cleanroom-consumer \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {
        "Service": "athena.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }]
  }' \
  --region us-east-1 \
  --profile flywheel-dev
```

### **Step 2: Create and Attach Policies**

```bash
# Create data read policy
aws iam create-policy \
  --policy-name omc-flywheel-dev-cleanroom-data-read \
  --policy-document file://consumer-policy-data-read-dev.json \
  --region us-east-1 \
  --profile flywheel-dev

# Create Athena results write policy
aws iam create-policy \
  --policy-name omc-flywheel-dev-cleanroom-athena-results \
  --policy-document file://consumer-policy-athena-dev.json \
  --region us-east-1 \
  --profile flywheel-dev

# Attach policies to role
aws iam attach-role-policy \
  --role-name omc_flywheel-dev-cleanroom-consumer \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/omc-flywheel-dev-cleanroom-data-read \
  --region us-east-1 \
  --profile flywheel-dev

aws iam attach-role-policy \
  --role-name omc_flywheel-dev-cleanroom-consumer \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/omc-flywheel-dev-cleanroom-athena-results \
  --region us-east-1 \
  --profile flywheel-dev
```

## 🔐 **Permission Summary**

### **What the Consumer Role CAN Do:**
- ✅ **Query Cleanroom**: Read data from `bucketed_*` tables (via Lake Formation SELECT permission)
- ✅ **Access Athena Results**: Read and write query results to Athena results bucket
- ✅ **Execute Athena Queries**: Full Athena API access for query execution
- ✅ **Access Glue Catalog**: Read metadata (DESCRIBE tables, databases, partitions)
- ✅ **S3 Data Access**: Read bucketed data directly from S3 (for data access patterns)

### **What the Consumer Role CANNOT Do:**
- ❌ CREATE_TABLE, ALTER, DROP tables
- ❌ INSERT data into bucketed tables
- ❌ Write to data buckets (only read)
- ❌ Access source data (split_cluster/, opus/)

## 🎯 **Cleanroom Access**

### **Querying Bucketed Tables**

The consumer role can query `bucketed_*` tables through:
1. **Lake Formation SELECT Permission**: Granted via Terraform module (wildcard on all tables)
2. **S3 Data Access**: Direct read access to bucketed data via IAM policy
3. **Glue Catalog Access**: Read table schemas and metadata

### **Athena Query Execution**

The consumer role can:
- **Start Query Executions**: Run queries against bucketed tables
- **Get Query Results**: Retrieve query results from Athena API
- **Access Results in S3**: Read/write query results to `query-results/cleanroom/*` prefix
- **List WorkGroups**: Discover available Athena workgroups
- **Stop Queries**: Cancel running queries if needed

### **Usage Example**

```bash
# Using the consumer role to query bucketed tables
aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM omc_flywheel_dev.bucketed_ibe_01_a" \
  --result-configuration "OutputLocation=s3://omc-flywheel-dev-analysis-data/query-results/cleanroom/" \
  --work-group primary \
  --region us-east-1 \
  --profile flywheel-dev

# Configure Athena workgroup to use consumer role
# (Requires workgroup configuration with role ARN)
```

### **Cleanroom Integration**

To use this role in Cleanroom:
1. **Configure Athena Workgroup**: Set workgroup to use `omc_flywheel-*-cleanroom-consumer` role
2. **Verify Lake Formation Permissions**: Ensure Terraform has granted SELECT permissions
3. **Test Query**: Execute test query against `bucketed_*` tables
4. **Access Results**: Query results available in S3 results bucket

## 📚 **Related Documentation**

- [Lake Formation Infrastructure README](infra/README.md)
- [Permissions Summary](infra/PERMISSIONS_SUMMARY.md)
- [Deployment Guide](infra/DEPLOYMENT_GUIDE.md)

---

**Last Updated**: October 28, 2025  
**Status**: Ready for role creation  
**Coverage**: Read-only access to bucketed tables + Athena query execution
