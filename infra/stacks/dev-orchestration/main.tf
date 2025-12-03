terraform {
  required_version = ">= 1.0"
  # Backend configuration can be added later if needed
}

module "orchestration" {
  source = "../../modules/orchestration"
  
  environment = "dev"
  
  job_names = {
    job1 = "etl-omc-flywheel-dev-addressable-split-and-part"
    job2 = "etl-omc-flywheel-dev-infobase-split-and-part"
    job3 = "etl-omc-flywheel-dev-register-part-tables"
    job4 = "etl-omc-flywheel-dev-prepare-part-tables"
    job5 = "etl-omc-flywheel-dev-create-part-addressable-ids-er-table"
    job6 = "etl-omc-flywheel-dev-generate-data-monitor-report"
    job7 = "etl-omc-flywheel-dev-generate-cleanrooms-report"
  }
  
  job_arguments = {
    job1 = {
      "--SNAPSHOT_DT" = "_NONE_"
    }
    job2 = {
      "--SNAPSHOT_DT" = "_NONE_"
    }
    job3a = {
      "--DATABASE"     = "omc_flywheel_dev_clean"
      "--S3_ROOT"      = "s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_part/addressable_ids/"
      "--TABLE_PREFIX" = "part_"
      "--MAX_COLS"     = "100"
    }
    job3b = {
      "--DATABASE"     = "omc_flywheel_dev_clean"
      "--S3_ROOT"      = "s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_part/infobase_attributes/"
      "--TABLE_PREFIX" = "part_"
      "--MAX_COLS"     = "100"
    }
  }
  
  enable_scheduled_execution = var.enable_scheduled_execution
  schedule_expression        = var.schedule_expression
  notification_emails        = var.notification_emails
  log_retention_days         = var.log_retention_days
  
  tags = var.tags
}

