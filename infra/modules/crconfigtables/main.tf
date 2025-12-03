terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

# Optional role for Clean Rooms to read Glue/S3
resource "aws_iam_role" "cleanrooms_access" {
  count = var.create_role ? 1 : 0

  name = "cleanrooms-glue-s3-access"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = { Service = "cleanrooms.amazonaws.com" },
      Action   = "sts:AssumeRole"
    }]
  })
  tags = var.tags
}

resource "aws_iam_policy" "cleanrooms_access" {
  count = var.create_role ? 1 : 0

  name   = "cleanrooms-glue-s3-access"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid     = "GlueRead",
        Effect  = "Allow",
        Action  = [
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetPartitions",
          "glue:GetTableVersion",
          "glue:GetTableVersions"
        ],
        Resource = "*"
      },
      {
        Sid      = "S3Read",
        Effect   = "Allow",
        Action   = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ],
        Resource = var.s3_resources
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach" {
  count      = var.create_role ? 1 : 0
  role       = aws_iam_role.cleanrooms_access[0].name
  policy_arn = aws_iam_policy.cleanrooms_access[0].arn
}

# Pull Glue table metadata
data "aws_glue_catalog_table" "this" {
  for_each      = var.tables
  database_name = each.value.glue.database
  name          = each.value.glue.table
}

# Compute allowed columns
locals {
  table_allowed_columns = {
    for k, v in var.tables :
    k => (
      var.use_all_columns
        ? [for c in data.aws_glue_catalog_table.this[k].storage_descriptor[0].columns : c.name]
        : coalesce(v.allowed_columns, [])
    )
  }

  role_arn_effective = var.create_role ? (length(aws_iam_role.cleanrooms_access) > 0 ? aws_iam_role.cleanrooms_access[0].arn : null) : var.role_arn
}

# Configured tables
resource "aws_cleanrooms_configured_table" "ct" {
  for_each        = var.tables
  name            = each.key
  description     = each.value.description
  analysis_method = each.value.analysis_method
  allowed_columns = local.table_allowed_columns[each.key]

  table_reference {
    database_name = each.value.glue.database
    table_name    = each.value.glue.table
  }

  tags = var.tags
}

# Analysis rules - Note: Analysis rules are managed separately via AWS API
# They need to be created after the configured table using boto3 or AWS CLI
# For now, we'll create the tables and rules can be added manually or via a separate script

# Deferred association (only if membership_id provided)
resource "aws_cleanrooms_configured_table_association" "assoc" {
  for_each                    = var.membership_id == null ? {} : var.tables
  name                        = "acx_${each.key}"
  membership_identifier       = var.membership_id
  configured_table_identifier = aws_cleanrooms_configured_table.ct[each.key].id
  role_arn                    = local.role_arn_effective

  depends_on = [aws_cleanrooms_configured_table.ct]
}

