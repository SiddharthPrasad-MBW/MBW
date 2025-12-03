#!/bin/bash
# Disable Lake Formation in dev by removing all permissions
# This makes Lake Formation inert and forces fallback to IAM + S3

set -e

export AWS_PROFILE=flywheel-dev
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region || echo "us-east-1")

echo "=========================================="
echo "Disabling Lake Formation for Dev"
echo "Account: $ACCOUNT_ID"
echo "Region: $REGION"
echo "=========================================="
echo ""

# Step 1: Remove all LF Data Lake Administrators (keep root)
echo "Step 1: Removing all LF Data Lake Administrators..."
aws lakeformation put-data-lake-settings \
  --data-lake-settings "{\"DataLakeAdmins\":[{\"DataLakePrincipalIdentifier\":\"arn:aws:iam::${ACCOUNT_ID}:root\"}]}"

echo "✅ Step 1 complete: Only root admin remains"
echo ""

# Step 2: Remove ALL LF permissions
echo "Step 2: Removing all LF permissions..."
PERM_COUNT=$(aws lakeformation list-permissions --max-results 1000 --query 'PrincipalResourcePermissions | length(@)' --output text)

if [ "$PERM_COUNT" -gt 0 ]; then
  echo "Found $PERM_COUNT permissions to revoke..."
  
  # Get all permissions
  aws lakeformation list-permissions --max-results 1000 \
    --query 'PrincipalResourcePermissions[]' \
    --output json > /tmp/lf_perms.json
  
  # Revoke each permission
  jq -c '.[]' /tmp/lf_perms.json | while read -r perm; do
    PRINCIPAL=$(echo "$perm" | jq -r '.Principal.DataLakePrincipalIdentifier')
    RESOURCE_TYPE=$(echo "$perm" | jq -r '.Resource | keys[0]')
    
    if [ "$RESOURCE_TYPE" = "Database" ]; then
      DB_NAME=$(echo "$perm" | jq -r '.Resource.Database.Name')
      PERMS=$(echo "$perm" | jq -r '.Permissions[]')
      echo "Revoking permissions for $PRINCIPAL on database $DB_NAME..."
      aws lakeformation revoke-permissions \
        --principal "{\"DataLakePrincipalIdentifier\":\"$PRINCIPAL\"}" \
        --resource "{\"Database\":{\"Name\":\"$DB_NAME\"}}" \
        --permissions $PERMS 2>/dev/null || true
    elif [ "$RESOURCE_TYPE" = "Table" ]; then
      DB_NAME=$(echo "$perm" | jq -r '.Resource.Table.DatabaseName')
      TABLE_NAME=$(echo "$perm" | jq -r '.Resource.Table.Name // "ALL_TABLES"')
      PERMS=$(echo "$perm" | jq -r '.Permissions[]')
      if [ "$TABLE_NAME" = "ALL_TABLES" ]; then
        echo "Revoking permissions for $PRINCIPAL on all tables in $DB_NAME..."
        aws lakeformation revoke-permissions \
          --principal "{\"DataLakePrincipalIdentifier\":\"$PRINCIPAL\"}" \
          --resource "{\"Table\":{\"DatabaseName\":\"$DB_NAME\",\"TableWildcard\":{}}}" \
          --permissions $PERMS 2>/dev/null || true
      else
        echo "Revoking permissions for $PRINCIPAL on table $DB_NAME.$TABLE_NAME..."
        aws lakeformation revoke-permissions \
          --principal "{\"DataLakePrincipalIdentifier\":\"$PRINCIPAL\"}" \
          --resource "{\"Table\":{\"DatabaseName\":\"$DB_NAME\",\"Name\":\"$TABLE_NAME\"}}" \
          --permissions $PERMS 2>/dev/null || true
      fi
    elif [ "$RESOURCE_TYPE" = "DataLocation" ]; then
      LOCATION_ARN=$(echo "$perm" | jq -r '.Resource.DataLocation.ResourceArn')
      PERMS=$(echo "$perm" | jq -r '.Permissions[]')
      echo "Revoking data location permissions for $PRINCIPAL on $LOCATION_ARN..."
      aws lakeformation revoke-permissions \
        --principal "{\"DataLakePrincipalIdentifier\":\"$PRINCIPAL\"}" \
        --resource "{\"DataLocation\":{\"ResourceArn\":\"$LOCATION_ARN\"}}" \
        --permissions $PERMS 2>/dev/null || true
    fi
  done
  
  rm -f /tmp/lf_perms.json
else
  echo "No permissions found to revoke"
fi

echo "✅ Step 2 complete: All permissions revoked"
echo ""

# Step 3: Deregister all resources
echo "Step 3: Deregistering all LF resources..."
RESOURCES=$(aws lakeformation list-resources --query 'ResourceInfoList[].ResourceArn' --output text)

if [ -n "$RESOURCES" ]; then
  echo "$RESOURCES" | while read -r resource_arn; do
    if [ -n "$resource_arn" ]; then
      echo "Deregistering resource: $resource_arn"
      aws lakeformation deregister-resource --resource-arn "$resource_arn" 2>/dev/null || true
    fi
  done
else
  echo "No resources found to deregister"
fi

echo "✅ Step 3 complete: All resources deregistered"
echo ""

# Step 4: Set Data Access Mode to Hybrid (optional but recommended)
echo "Step 4: Setting Data Access Mode to Hybrid..."
aws lakeformation put-data-lake-settings \
  --data-lake-settings '{
    "DataLakeAdmins": [{"DataLakePrincipalIdentifier": "arn:aws:iam::'${ACCOUNT_ID}':root"}],
    "CreateDatabaseDefaultPermissions": [{"Principal": {"DataLakePrincipalIdentifier": "IAM_ALLOWED_PRINCIPALS"}, "Permissions": ["ALL"]}],
    "CreateTableDefaultPermissions": [{"Principal": {"DataLakePrincipalIdentifier": "IAM_ALLOWED_PRINCIPALS"}, "Permissions": ["ALL"]}]
  }' 2>/dev/null || true

echo "✅ Step 4 complete: Data Access Mode set to Hybrid"
echo ""

# Step 5: Validate
echo "Step 5: Validating Lake Formation is disabled..."
REMAINING_PERMS=$(aws lakeformation list-permissions --max-results 100 --query 'PrincipalResourcePermissions | length(@)' --output text)
REMAINING_RESOURCES=$(aws lakeformation list-resources --query 'ResourceInfoList | length(@)' --output text)

echo ""
echo "=========================================="
echo "Validation Results:"
echo "=========================================="
echo "Remaining permissions: $REMAINING_PERMS"
echo "Remaining resources: $REMAINING_RESOURCES"
echo ""

if [ "$REMAINING_PERMS" -eq 0 ] && [ "$REMAINING_RESOURCES" -eq 0 ]; then
  echo "✅ SUCCESS: Lake Formation is now disabled!"
  echo "   Glue jobs will now use IAM + S3 permissions only"
else
  echo "⚠️  WARNING: Some permissions or resources may remain"
  echo "   You may need to manually clean up remaining items"
fi

echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo "1. Re-run your register-part-tables job"
echo "2. Verify tables are created successfully"
echo "3. Test with: aws glue get-tables --database-name omc_flywheel_dev"
echo ""

