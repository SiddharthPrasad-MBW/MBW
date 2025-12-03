terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

locals {
  tgt_path_arn = "arn:aws:s3:::${var.target_bucket}/${trim(var.target_prefix, "/")}"
  src_path_arn = "arn:aws:s3:::${var.source_bucket}/${trim(var.source_prefix, "/")}"
  raw_src_path_arn = var.register_raw_source && var.raw_source_bucket != "" && var.raw_source_prefix != "" ? "arn:aws:s3:::${var.raw_source_bucket}/${trim(var.raw_source_prefix, "/")}" : null
}

# 0) Lake Formation default behavior (console "Data catalog settings")
# - IAM-only (Hybrid): leave defaults empty
# - LF-only: set default DB/TABLE perms (minimally to data lake admin == caller)
resource "aws_lakeformation_data_lake_settings" "defaults" {
  count = var.enable ? 1 : 0

  # Set yourself (or a platform admin role) as LF admin
  admins = [
    "arn:aws:iam::${var.account_id}:role/AWSServiceRoleForLakeFormationDataAccess" # service-linked
  ]

  dynamic "create_database_default_permissions" {
    for_each = var.lf_only_defaults ? [1] : []
    content {
      principal   = "IAM_ALLOWED_PRINCIPALS" # or a specific admin ARN
      permissions = ["ALL"]
    }
  }

  dynamic "create_table_default_permissions" {
    for_each = var.lf_only_defaults ? [1] : []
    content {
      principal   = "IAM_ALLOWED_PRINCIPALS"
      permissions = ["ALL"]
    }
  }
}

# 1) Register TARGET data location (bucketed layer only)
resource "aws_lakeformation_resource" "target" {
  count    = var.enable ? 1 : 0
  arn      = local.tgt_path_arn              # path-scoped registration
  role_arn = var.writer_principals[0]        # a role LF can assume to validate access
}

# 1b) Register SOURCE location (split_cluster - where ext_ tables point to)
resource "aws_lakeformation_resource" "source" {
  count    = var.enable ? 1 : 0
  arn      = local.src_path_arn
  role_arn = var.writer_principals[0]
}

# 1c) (Optional) Register RAW SOURCE location (opus/ data) if you want governed reads
resource "aws_lakeformation_resource" "raw_source" {
  count    = var.enable && var.register_raw_source ? 1 : 0
  arn      = local.raw_src_path_arn
  role_arn = var.writer_principals[0]
}

# 2) Ensure the Glue database exists (CTAS writes here)
resource "aws_glue_catalog_database" "db" {
  count = var.enable ? 1 : 0
  name  = var.database_name
}

# 3) Lake Formation grants
# 3a) DATA_LOCATION_ACCESS on TARGET (bucketed data) - WRITERS
resource "aws_lakeformation_permissions" "tgt_loc_writers" {
  for_each = var.enable ? toset(var.writer_principals) : []

  principal   = each.value
  permissions = ["DATA_LOCATION_ACCESS"]

  data_location {
    arn = "arn:aws:s3:::${var.target_bucket}"
  }

  depends_on = [aws_lakeformation_resource.target]
}

# 3b) DATA_LOCATION_ACCESS on TARGET (bucketed data) - READERS
resource "aws_lakeformation_permissions" "tgt_loc_readers" {
  for_each = var.enable && length(var.reader_principals) > 0 ? toset(var.reader_principals) : []

  principal   = each.value
  permissions = ["DATA_LOCATION_ACCESS"]

  data_location {
    arn = "arn:aws:s3:::${var.target_bucket}"
  }

  depends_on = [aws_lakeformation_resource.target]
}

# 3c) DATA_LOCATION_ACCESS on SOURCE (split_cluster data - where ext_ tables point) - WRITERS ONLY
resource "aws_lakeformation_permissions" "src_loc_writers" {
  for_each = var.enable ? toset(var.writer_principals) : []

  principal   = each.value
  permissions = ["DATA_LOCATION_ACCESS"]

  data_location {
    arn = "arn:aws:s3:::${var.source_bucket}"
  }

  depends_on = [aws_lakeformation_resource.source]
}

# 3d) DATA_LOCATION_ACCESS on RAW SOURCE (opus/ data) if registered - WRITERS ONLY
resource "aws_lakeformation_permissions" "raw_src_loc_writers" {
  for_each = var.enable && var.register_raw_source ? toset(var.writer_principals) : []

  principal   = each.value
  permissions = ["DATA_LOCATION_ACCESS"]

  data_location {
    arn = "arn:aws:s3:::${var.raw_source_bucket}"
  }

  depends_on = [aws_lakeformation_resource.raw_source]
}

# 3e) Database-level grants (lets CTAS create/alter/drop tables) - WRITERS ONLY
resource "aws_lakeformation_permissions" "db_admin" {
  for_each = var.enable ? toset(var.writer_principals) : []

  principal   = each.value
  permissions = ["CREATE_TABLE", "ALTER", "DROP", "DESCRIBE"]

  database {
    name = aws_glue_catalog_database.db[0].name
  }
}

# 3f) Read perms on ALL tables in the database (covers ext_* and bucketed_*) - READERS ONLY
resource "aws_lakeformation_permissions" "db_read_all_tables" {
  for_each = var.enable && length(var.reader_principals) > 0 ? toset(var.reader_principals) : []

  principal   = each.value
  permissions = ["SELECT", "DESCRIBE"]

  table {
    database_name = aws_glue_catalog_database.db[0].name
    wildcard      = true   # applies to all tables in this database
  }
}

# 3f2) Read perms on ALL tables for WRITERS (needed to read ext_* tables for CTAS)
resource "aws_lakeformation_permissions" "db_read_all_tables_writers" {
  for_each = var.enable ? toset(var.writer_principals) : []

  principal   = each.value
  permissions = ["SELECT", "DESCRIBE"]

  table {
    database_name = aws_glue_catalog_database.db[0].name
    wildcard      = true   # applies to all tables in this database
  }
}

# 3g) Write perms on ALL tables in the database (for CTAS to write bucketed tables) - WRITERS ONLY
resource "aws_lakeformation_permissions" "db_write_all_tables" {
  for_each = var.enable ? toset(var.writer_principals) : []

  principal   = each.value
  permissions = ["INSERT", "ALTER"]

  table {
    database_name = aws_glue_catalog_database.db[0].name
    wildcard      = true   # applies to all tables in this database (including bucketed_*)
  }
}
