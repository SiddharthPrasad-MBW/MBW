# OMC Flywheel Infrastructure as Code

This directory contains the complete Terraform infrastructure for the OMC Flywheel Cleanroom solution, organized into reusable modules and environment-specific deployments.

## 🏗️ Architecture Overview

The infrastructure follows a **modular design** with reusable components:

```
infra/
├── modules/
│   ├── gluejobs/              # 🔄 Reusable Glue Jobs Module
│   ├── monitoring/            # 📊 Reusable Monitoring Module
│   ├── crconfigtables/        # 🏢 Cleanrooms Configured Tables Module
│   ├── crnamespace/           # 🔗 Cleanrooms Identity Resolution Service Module
│   └── lakeformation/         # 🔐 Reusable Lake Formation Module
├── stacks/
│   ├── dev-gluejobs/          # 🧪 Dev Glue Jobs Stack
│   ├── dev-monitoring/        # 🧪 Dev Monitoring Stack
│   ├── dev-crconfigtables/    # 🧪 Dev Cleanrooms Stack
│   ├── prod-gluejobs/         # 🚀 Prod Glue Jobs Stack
│   ├── prod-monitoring/       # 🚀 Prod Monitoring Stack
│   ├── prod-crconfigtables/  # 🚀 Prod Cleanrooms Stack
│   └── prod-crnamespace/      # 🚀 Prod Identity Resolution Stack
└── envs/
    ├── dev/                   # 🧪 Development Environment (legacy)
    └── prod/                  # 🚀 Production Environment (legacy)
```

## 📊 Module Details

### **1. Glue Jobs Module** (`modules/gluejobs/`)
**Purpose**: Reusable data processing and ETL pipelines

**Features**:
- **Pipeline 1: Bucketed Tables** (Original Cleanroom-optimized)
- **Pipeline 2: Partitioned Tables** (New time-series optimized)
- **Configurable Infrastructure**: S3 buckets, Glue database, IAM roles
- **Flexible Deployment**: Can create or use existing resources
- **Environment-Aware**: Supports dev/prod configurations

### **2. Monitoring Module** (`modules/monitoring/`)
**Purpose**: Reusable data quality monitoring and alerting

**Features**:
- **Comprehensive Monitoring**: Record counts, key quality, schema validation
- **Alerting**: SNS topics and CloudWatch dashboards
- **Configurable**: Monitoring frequency, retention, thresholds
- **Environment-Aware**: Different settings for dev/prod

### **3. Cleanrooms Configured Tables Module** (`modules/crconfigtables/`)
**Purpose**: Reusable Cleanrooms configured tables and associations

**Features**:
- **Automatic Column Discovery**: Pulls all columns from Glue tables
- **Analysis Rules**: Supports CUSTOM, AGGREGATION, and LIST rule types
- **Membership Associations**: Links tables to Cleanrooms memberships
- **IAM Role Management**: Creates roles for Cleanrooms access
- **Default Analysis Providers**: `921290734397` (AMC Service) and `657425294073` (Query Submitter)

### **4. Cleanrooms Identity Resolution Module** (`modules/crnamespace/`)
**Purpose**: Cleanrooms Identity Resolution Service resources

**Features**:
- **ID Namespace Associations**: Links Entity Resolution ID namespaces to Cleanrooms
- **ID Mapping Tables**: Manages ID mapping tables for collaborations
- **Note**: Terraform resources are commented out (AWS provider doesn't support yet)
- **Boto3 Scripts**: Use `scripts/discover-cr-namespace-resources.py` and `scripts/create-cr-namespace-resources.py`

### **5. Lake Formation Module** (`modules/lakeformation/`)
**Purpose**: Reusable data governance and permissions

**Features**:
- **Path-Scoped Registration**: S3 locations for data governance
- **Writer/Reader Separation**: Different permissions for different roles
- **Flexible Configuration**: Can enable/disable features per environment
- **Reusable**: Same module for dev and prod

## 🏗️ Environment Details

### **Development Environment** (`envs/dev/`)
**Purpose**: Development and testing

**Configuration**:
- **Smaller Scale**: Fewer workers, shorter timeouts
- **More Frequent Monitoring**: 6-hour intervals
- **Lenient Quality Checks**: 5% tolerance, shorter retention
- **Test Data**: Smaller bucket counts (64 vs 256)

### **Production Environment** (`envs/prod/`)
**Purpose**: Production workloads

**Configuration**:
- **Full Scale**: 10 workers, longer timeouts
- **Daily Monitoring**: 24-hour intervals
- **Strict Quality Checks**: 0% tolerance, longer retention
- **Production Data**: Full bucket counts (256)

## 🚀 Deployment Guide

### **Prerequisites**
1. AWS CLI configured with appropriate permissions
2. Terraform >= 1.0 installed
3. All Glue job scripts uploaded to S3

### **Deployment Order**
1. **Development Environment** (Test first)
2. **Production Environment** (After validation)

### **Quick Deploy**

```bash
# Deploy Development Environment
cd envs/dev
terraform init
terraform plan
terraform apply

# Deploy Production Environment (after dev validation)
cd ../prod
terraform init
terraform plan
terraform apply
```

## 🔧 Configuration Management

### **Environment-Specific Settings**
Each environment has its own `terraform.tfvars`:
- `dev/terraform.tfvars` - Development environment configuration
- `prod/terraform.tfvars` - Production environment configuration

### **Module Configuration**
Each module has its own variables that can be customized:
- `modules/gluejobs/variables.tf` - Glue jobs configuration
- `modules/monitoring/variables.tf` - Monitoring configuration
- `modules/lakeformation/variables.tf` - Lake Formation configuration

## 📈 Benefits of This Structure

### **1. Modular Design**
- **Reusable Components**: Modules can be used across environments
- **Consistent Configuration**: Same modules, different parameters
- **Easy Maintenance**: Update modules once, affects all environments

### **2. Environment Separation**
- **Dev/Prod Isolation**: Completely separate environments
- **Independent Lifecycles**: Deploy/update each environment independently
- **Different Configurations**: Optimized settings per environment

### **3. Scalability**
- **Easy to Add Environments**: Just create new env directory
- **Module Reusability**: Use same modules across environments
- **Flexible Configuration**: Override module settings per environment

### **4. Maintainability**
- **Single Source of Truth**: Modules define infrastructure patterns
- **Consistent Naming**: Environment-aware resource naming
- **Clear Dependencies**: Explicit module dependencies

## 🔄 Pipeline Management

### **Enable/Disable Pipelines**
```bash
# Disable partitioned pipeline
cd envs/gluejobs
terraform apply -var="enable_partitioned_pipeline=false"

# Disable monitoring
cd ../monitoring
terraform destroy
```

### **Environment Promotion**
```bash
# Deploy to dev first
cd envs/dev
terraform apply

# Test and validate
# Then promote to prod
cd ../prod
terraform apply
```

## 📊 Monitoring and Observability

### **CloudWatch Dashboards**
- **Glue Jobs**: Job execution metrics and logs
- **Monitoring**: Data quality metrics and alerts
- **Lake Formation**: Permission and access metrics

### **S3 Data Locations**
- **Raw Data**: `s3://omc-flywheel-data-us-east-1-prod/opus/`
- **Processed Data**: `s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/`
- **Analysis Results**: `s3://omc-flywheel-prod-analysis-data/`
- **Monitoring Reports**: `s3://omc-flywheel-prod-analysis-data/data-monitor/`

## 🔗 Integration Points

### **Between Environments**
- Glue jobs write to S3 paths registered in Lake Formation
- Monitoring reads from Glue tables created by Glue jobs
- Lake Formation controls access to data processed by Glue jobs

### **External Dependencies**
- Glue job scripts must be uploaded to S3 before deployment
- Lake Formation requires existing S3 buckets and Glue databases
- Monitoring requires existing Glue tables to monitor

## 📋 Maintenance

### **Regular Tasks**
1. **Monitor job execution** via CloudWatch
2. **Review data quality reports** from monitoring
3. **Update Lake Formation permissions** as needed
4. **Scale workers** based on data volume

### **Troubleshooting**
- Check CloudWatch logs for job failures
- Review S3 data paths for missing data
- Validate Lake Formation permissions
- Test monitoring alerts

## 🎯 Next Steps

1. **Deploy Glue Jobs** environment
2. **Configure Lake Formation** permissions
3. **Set up Monitoring** alerts
4. **Test end-to-end** pipeline
5. **Document operational procedures**

---

For detailed instructions on each environment, see the individual README files in each directory.