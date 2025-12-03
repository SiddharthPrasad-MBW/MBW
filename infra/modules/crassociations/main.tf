terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
    null = {
      source  = "hashicorp/null"
      version = ">= 3.0"
    }
  }
}

# Data source to get existing configured tables
# Note: AWS provider doesn't have a data source to list all configured tables
# So we'll use a script to discover them and pass both IDs and names via variable

# Get IAM role ARN for associations
data "aws_iam_role" "cleanrooms_access" {
  name = var.role_name
}

# Associate existing configured tables and ID namespace using script
# (Terraform AWS provider support for associations is inconsistent)
resource "null_resource" "associate_resources" {
  triggers = {
    membership_id     = var.membership_id
    id_namespace_arn  = var.id_namespace_arn
    id_namespace_name = var.id_namespace_name
    role_arn          = data.aws_iam_role.cleanrooms_access.arn
    # Trigger on table count change
    table_count       = length(var.existing_configured_tables)
    # Trigger on any table ID change
    table_ids         = join(",", sort(keys(var.existing_configured_tables)))
  }

  provisioner "local-exec" {
    command = <<-EOT
      # Extract table IDs from the map
      TABLE_IDS=$(echo '${jsonencode(keys(var.existing_configured_tables))}' | jq -r '.[]' | tr '\n' ' ')
      
      # Associate tables and ID namespace
      # path.root is the stack directory, go up to workspace root
      cd ${path.root}/../../.. && \
      export PYTHONHTTPSVERIFY=0 && \
      python3 scripts/manage-collaboration-invites.py associate \
        --membership-id ${var.membership_id} \
        --table-ids $TABLE_IDS \
        --role-arn "${data.aws_iam_role.cleanrooms_access.arn}" \
        --id-namespace-arn "${var.id_namespace_arn}" \
        --id-namespace-name "${var.id_namespace_name}" \
        --profile ${var.aws_profile} \
        --region ${var.aws_region} \
        --no-verify-ssl || true
    EOT
  }
}

