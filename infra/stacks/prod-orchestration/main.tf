terraform {
  required_version = ">= 1.0"
  
  backend "s3" {
    # Configure backend in terraform.tfvars or via CLI
  }
}

module "orchestration" {
  source = "../../modules/orchestration"
  
  environment = "prod"
  
  job_names = {
    job1 = "etl-omc-flywheel-prod-addressable-split-and-part"
    job2 = "etl-omc-flywheel-prod-infobase-split-and-part"
    job3 = "etl-omc-flywheel-prod-register-part-tables"
    job4 = "etl-omc-flywheel-prod-prepare-part-tables"
    job5 = "etl-omc-flywheel-prod-create-part-addressable-ids-er-table"
    job6 = "etl-omc-flywheel-prod-generate-data-monitor-report"
    job7 = "etl-omc-flywheel-prod-generate-cleanrooms-report"
  }
  
  job_arguments = {
    job1 = {
      "--SNAPSHOT_DT" = "_NONE_"
    }
    job2 = {
      "--SNAPSHOT_DT" = "_NONE_"
    }
    job3a = {
      "--DATABASE"     = "omc_flywheel_prod"
      "--S3_ROOT"      = "s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_part/addressable_ids/"
      "--TABLE_PREFIX" = "part_"
      "--MAX_COLS"     = "100"
    }
    job3b = {
      "--DATABASE"     = "omc_flywheel_prod"
      "--S3_ROOT"      = "s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_part/infobase_attributes/"
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

