#!/bin/bash
# Script to fix hardcoded environment values
# This is a one-time migration script

ENV_FILE="infra/modules/gluejobs/main.tf"

# Replace all hardcoded job names
sed -i.bak 's/"etl-omc-flywheel-prod-/'"${local.job_name_prefix}"'-/g' "$ENV_FILE"

# Replace all hardcoded script locations
sed -i.bak 's|s3://aws-glue-assets-${local.account_id}-${local.region}/scripts/etl-omc-flywheel-prod-|${local.script_location_prefix}/${local.job_name_prefix}-|g' "$ENV_FILE"

# Replace hardcoded ENV arguments
sed -i.bak 's/"--ENV".*=.*"prod"/"--ENV" = var.environment/g' "$ENV_FILE"

echo "Fixed hardcoded values in $ENV_FILE"
echo "Backup created: ${ENV_FILE}.bak"

