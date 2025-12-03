# API Reference

## 🏗️ Terraform Resources

### Glue Jobs

#### `aws_glue_job.job_omc_flywheel_prod_addressable_ids_compaction`
```hcl
resource "aws_glue_job" "job_omc_flywheel_prod_addressable_ids_compaction" {
  name              = "etl-omc-flywheel-prod-addressable-ids-compaction"
  role_arn          = "arn:aws:iam::239083076653:role/omc_flywheel-prod-glue-role"
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 8
  max_retries       = 2
  timeout           = 600

  command {
    name            = "glueetl"
    script_location = "s3://aws-glue-assets-239083076653-us-east-1/scripts/etl-omc-flywheel-prod-addressable-ids-compaction.py"
    python_version  = "3"
  }

  default_arguments = {
    "--TempDir"                      = "s3://aws-glue-assets-239083076653-us-east-1/temporary/"
    "--enable-glue-datacatalog"      = "true"
    "--enable-observability-metrics" = "true"
    "--spark-event-logs-path"        = "s3://aws-glue-assets-239083076653-us-east-1/sparkHistoryLogs/"
  }

  tags = {
    Environment = "prod"
    ManagedBy   = "terraform"
    Owner       = "data-team"
    Project     = "acx-omc-flywheel-p0"
    Purpose     = "reverse-engineered-infrastructure"
  }
}
```

#### `aws_glue_job.job_omc_flywheel_prod_infobase_attributes_compaction`
```hcl
resource "aws_glue_job" "job_omc_flywheel_prod_infobase_attributes_compaction" {
  name              = "etl-omc-flywheel-prod-infobase-attributes-compaction"
  role_arn          = "arn:aws:iam::239083076653:role/omc_flywheel-prod-glue-role"
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 24
  max_retries       = 2
  timeout           = 600

  command {
    name            = "glueetl"
    script_location = "s3://aws-glue-assets-239083076653-us-east-1/scripts/etl-omc-flywheel-prod-infobase-attributes-compaction.py"
    python_version  = "3"
  }

  default_arguments = {
    "--TempDir"                      = "s3://aws-glue-assets-239083076653-us-east-1/temporary/"
    "--enable-glue-datacatalog"      = "true"
    "--enable-observability-metrics" = "true"
    "--spark-event-logs-path"        = "s3://aws-glue-assets-239083076653-us-east-1/sparkHistoryLogs/"
  }

  tags = {
    Environment = "prod"
    ManagedBy   = "terraform"
    Owner       = "data-team"
    Project     = "acx-omc-flywheel-p0"
    Purpose     = "reverse-engineered-infrastructure"
  }
}
```

#### `aws_glue_job.job_omc_prod_infobase_cleanroom_from_csv`
```hcl
resource "aws_glue_job" "job_omc_prod_infobase_cleanroom_from_csv" {
  name              = "etl-omc-flywheel-prod-infobase-cleanroom-from-csv"
  role_arn          = "arn:aws:iam::239083076653:role/omc_flywheel-prod-glue-role"
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 24
  max_retries       = 2
  timeout           = 600

  command {
    name            = "glueetl"
    script_location = "s3://aws-glue-assets-239083076653-us-east-1/scripts/etl-omc-prod-infobase-cleanroom-from-csv.py"
    python_version  = "3"
  }

  default_arguments = {
    "--TempDir"                      = "s3://aws-glue-assets-239083076653-us-east-1/temporary/"
    "--enable-glue-datacatalog"      = "true"
    "--enable-observability-metrics" = "true"
    "--spark-event-logs-path"        = "s3://aws-glue-assets-239083076653-us-east-1/sparkHistoryLogs/"
  }

  tags = {
    Environment = "prod"
    ManagedBy   = "terraform"
    Owner       = "data-team"
    Project     = "acx-omc-flywheel-p0"
    Purpose     = "reverse-engineered-infrastructure"
  }
}
```

### Glue Crawlers

#### `aws_glue_crawler.crawler_omc_flywheel_prod_addressable_real_ids`
```hcl
resource "aws_glue_crawler" "crawler_omc_flywheel_prod_addressable_real_ids" {
  name          = "crw-omc-flywheel-prod-addressable_ids-compaction-cr"
  role          = "arn:aws:iam::239083076653:role/omc_flywheel-prod-glue-role"
  database_name = "omc_flywheel_prod"

  s3_target {
    path = "s3://omc-flywheel-data-us-east-1-prod/opus/"
  }

  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "LOG"
  }

  tags = {
    Environment = "prod"
    ManagedBy   = "terraform"
    Owner       = "data-team"
    Project     = "acx-omc-flywheel-p0"
    Purpose     = "reverse-engineered-infrastructure"
  }
}
```

#### `aws_glue_crawler.crawler_omc_flywheel_prod_infobase_attributes`
```hcl
resource "aws_glue_crawler" "crawler_omc_flywheel_prod_infobase_attributes" {
  name          = "crw-omc-flywheel-prod-infobase_attributes-compaction-cr"
  role          = "arn:aws:iam::239083076653:role/omc_flywheel-prod-glue-role"
  database_name = "omc_flywheel_prod"

  s3_target {
    path = "s3://omc-flywheel-data-us-east-1-prod/opus/"
  }

  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "LOG"
  }

  tags = {
    Environment = "prod"
    ManagedBy   = "terraform"
    Owner       = "data-team"
    Project     = "acx-omc-flywheel-p0"
    Purpose     = "reverse-engineered-infrastructure"
  }
}
```

#### `aws_glue_crawler.crawler_omc_flywheel_prod_reference_tables`
```hcl
resource "aws_glue_crawler" "crawler_omc_flywheel_prod_reference_tables" {
  name          = "crw-omc-flywheel-prod-raw-input-addressable"
  role          = "arn:aws:iam::239083076653:role/omc_flywheel-prod-glue-role"
  database_name = "omc_flywheel_prod"

  s3_target {
    path = "s3://omc-flywheel-data-us-east-1-prod/opus/"
  }

  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "LOG"
  }

  tags = {
    Environment = "prod"
    ManagedBy   = "terraform"
    Owner       = "data-team"
    Project     = "acx-omc-flywheel-p0"
    Purpose     = "reverse-engineered-infrastructure"
  }
}
```

#### `aws_glue_crawler.crawler_omc_flywheel_prod_transformed`
```hcl
resource "aws_glue_crawler" "crawler_omc_flywheel_prod_transformed" {
  name          = "crw-omc-flywheel-prod-raw-input-infobase"
  role          = "arn:aws:iam::239083076653:role/omc_flywheel-prod-glue-role"
  database_name = "omc_flywheel_prod"

  s3_target {
    path = "s3://omc-flywheel-data-us-east-1-prod/opus/"
  }

  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "LOG"
  }

  tags = {
    Environment = "prod"
    ManagedBy   = "terraform"
    Owner       = "data-team"
    Project     = "acx-omc-flywheel-p0"
    Purpose     = "reverse-engineered-infrastructure"
  }
}
```

### Glue Databases

#### `aws_glue_catalog_database.omc_flywheel_prod`
```hcl
resource "aws_glue_catalog_database" "omc_flywheel_prod" {
  name        = "omc_flywheel_prod"
  description = "CSE OMC Flywheel production data catalog for Clean Rooms"

  tags = {
    Environment = "prod"
    ManagedBy   = "terraform"
    Owner       = "data-team"
    Project     = "acx-omc-flywheel-p0"
    Purpose     = "reverse-engineered-infrastructure"
  }
}
```

#### `aws_glue_catalog_database.default`
```hcl
resource "aws_glue_catalog_database" "default" {
  name = "default"

  tags = {
    Environment = "prod"
    ManagedBy   = "terraform"
    Owner       = "data-team"
    Project     = "acx-omc-flywheel-p0"
    Purpose     = "reverse-engineered-infrastructure"
  }
}
```

### IAM Role

#### `aws_iam_role.glue_role`
```hcl
resource "aws_iam_role" "glue_role" {
  name = "omc_flywheel-prod-glue-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = "prod"
    ManagedBy   = "terraform"
    Owner       = "data-team"
    Project     = "acx-omc-flywheel-p0"
    Purpose     = "reverse-engineered-infrastructure"
  }
}
```

### S3 Buckets

#### `aws_s3_bucket.omc_flywheel_data_us_east_1_prod`
```hcl
resource "aws_s3_bucket" "omc_flywheel_data_us_east_1_prod" {
  bucket = "omc-flywheel-data-us-east-1-prod"

  tags = {
    Environment = "prod"
    ManagedBy   = "terraform"
    Owner       = "data-team"
    Project     = "acx-omc-flywheel-p0"
    Purpose     = "reverse-engineered-infrastructure"
  }
}
```

#### `aws_s3_bucket.aws_glue_assets_239083076653_us_east_1`
```hcl
resource "aws_s3_bucket" "aws_glue_assets_239083076653_us_east_1" {
  bucket = "aws-glue-assets-239083076653-us-east-1"

  tags = {
    Environment = "prod"
    ManagedBy   = "terraform"
    Owner       = "data-team"
    Project     = "acx-omc-flywheel-p0"
    Purpose     = "reverse-engineered-infrastructure"
  }
}
```

#### `aws_s3_bucket.omc_flywheel_prod_analysis_data`
```hcl
resource "aws_s3_bucket" "omc_flywheel_prod_analysis_data" {
  bucket = "omc-flywheel-prod-analysis-data"

  tags = {
    Environment = "prod"
    ManagedBy   = "terraform"
    Owner       = "data-team"
    Project     = "acx-omc-flywheel-p0"
    Purpose     = "reverse-engineered-infrastructure"
  }
}
```

## 🔧 Terraform Variables

### Required Variables
```hcl
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "acx-omc-flywheel-p0"
}

variable "owner" {
  description = "Resource owner"
  type        = string
  default     = "data-team"
}
```

### Optional Variables
```hcl
variable "worker_count" {
  description = "Number of Glue workers"
  type        = number
  default     = 24
}

variable "worker_type" {
  description = "Glue worker type"
  type        = string
  default     = "G.1X"
}

variable "timeout" {
  description = "Job timeout in minutes"
  type        = number
  default     = 600
}

variable "max_retries" {
  description = "Maximum job retries"
  type        = number
  default     = 2
}
```

## 📊 Terraform Outputs

### Glue Job Outputs
```hcl
output "glue_jobs" {
  description = "Glue job names and ARNs"
  value = {
    addressable_ids = {
      name = aws_glue_job.job_omc_flywheel_prod_addressable_ids_compaction.name
      arn  = aws_glue_job.job_omc_flywheel_prod_addressable_ids_compaction.arn
    }
    infobase_attributes = {
      name = aws_glue_job.job_omc_flywheel_prod_infobase_attributes_compaction.name
      arn  = aws_glue_job.job_omc_flywheel_prod_infobase_attributes_compaction.arn
    }
    cleanroom_csv = {
      name = aws_glue_job.job_omc_prod_infobase_cleanroom_from_csv.name
      arn  = aws_glue_job.job_omc_prod_infobase_cleanroom_from_csv.arn
    }
  }
}
```

### S3 Bucket Outputs
```hcl
output "s3_buckets" {
  description = "S3 bucket names and ARNs"
  value = {
    data_bucket = {
      name = aws_s3_bucket.omc_flywheel_data_us_east_1_prod.bucket
      arn  = aws_s3_bucket.omc_flywheel_data_us_east_1_prod.arn
    }
    assets_bucket = {
      name = aws_s3_bucket.aws_glue_assets_239083076653_us_east_1.bucket
      arn  = aws_s3_bucket.aws_glue_assets_239083076653_us_east_1.arn
    }
    analysis_bucket = {
      name = aws_s3_bucket.omc_flywheel_prod_analysis_data.bucket
      arn  = aws_s3_bucket.omc_flywheel_prod_analysis_data.arn
    }
  }
}
```

### IAM Role Outputs
```hcl
output "iam_role" {
  description = "IAM role ARN"
  value = {
    name = aws_iam_role.glue_role.name
    arn  = aws_iam_role.glue_role.arn
  }
}
```

## 🚀 AWS CLI Commands

### Glue Job Management
```bash
# List all jobs
aws glue get-jobs

# Get specific job
aws glue get-job --job-name etl-omc-flywheel-prod-addressable-ids-compaction

# Start job run
aws glue start-job-run --job-name etl-omc-flywheel-prod-addressable-ids-compaction

# Get job run status
aws glue get-job-run --job-name etl-omc-flywheel-prod-addressable-ids-compaction --run-id <run-id>

# Stop job run
aws glue stop-job-run --job-name etl-omc-flywheel-prod-addressable-ids-compaction --run-id <run-id>
```

### Crawler Management
```bash
# List crawlers
aws glue get-crawlers

# Get specific crawler
aws glue get-crawler --name crw-omc-flywheel-prod-addressable_ids-compaction-cr

# Start crawler
aws glue start-crawler --name crw-omc-flywheel-prod-addressable_ids-compaction-cr

# Get crawler runs
aws glue get-crawler-runs --crawler-name crw-omc-flywheel-prod-addressable_ids-compaction-cr
```

### S3 Management
```bash
# List bucket contents
aws s3 ls s3://omc-flywheel-data-us-east-1-prod/ --recursive

# Copy files to bucket
aws s3 cp local-file.py s3://aws-glue-assets-239083076653-us-east-1/scripts/

# Sync directories
aws s3 sync ./scripts/ s3://aws-glue-assets-239083076653-us-east-1/scripts/
```

### Database Management
```bash
# List databases
aws glue get-databases

# Get specific database
aws glue get-database --name omc_flywheel_prod

# List tables in database
aws glue get-tables --database-name omc_flywheel_prod

# Get table schema
aws glue get-table --database-name omc_flywheel_prod --name <table-name>
```

## 📈 Monitoring Commands

### CloudWatch Metrics
```bash
# Get job success rate
aws cloudwatch get-metric-statistics \
  --namespace AWS/Glue \
  --metric-name JobRunSuccess \
  --dimensions Name=JobName,Value=etl-omc-flywheel-prod-addressable-ids-compaction \
  --statistics Average \
  --start-time 2025-10-16T00:00:00Z \
  --end-time 2025-10-17T00:00:00Z \
  --period 3600

# Get job duration
aws cloudwatch get-metric-statistics \
  --namespace AWS/Glue \
  --metric-name JobRunDuration \
  --dimensions Name=JobName,Value=etl-omc-flywheel-prod-addressable-ids-compaction \
  --statistics Average \
  --start-time 2025-10-16T00:00:00Z \
  --end-time 2025-10-17T00:00:00Z \
  --period 3600
```

### Log Analysis
```bash
# Get job logs
aws logs get-log-events \
  --log-group-name /aws-glue/jobs/logs-v2 \
  --log-stream-name <stream-name>

# Filter error logs
aws logs filter-log-events \
  --log-group-name /aws-glue/jobs/logs-v2 \
  --filter-pattern "ERROR" \
  --start-time $(date -d '24 hours ago' +%s)000
```

## 🔒 Security Commands

### IAM Management
```bash
# Get role details
aws iam get-role --role-name omc_flywheel-prod-glue-role

# List role policies
aws iam list-attached-role-policies --role-name omc_flywheel-prod-glue-role

# Get role policy
aws iam get-role-policy --role-name omc_flywheel-prod-glue-role --policy-name <policy-name>
```

### S3 Security
```bash
# Get bucket policy
aws s3api get-bucket-policy --bucket omc-flywheel-data-us-east-1-prod

# Get bucket ACL
aws s3api get-bucket-acl --bucket omc-flywheel-data-us-east-1-prod

# Check bucket encryption
aws s3api get-bucket-encryption --bucket omc-flywheel-data-us-east-1-prod
```

---

**Last Updated**: October 17, 2025  
**Terraform Version**: >= 1.0  
**AWS Provider**: ~> 5.60
