#!/bin/bash
# Setup Dev Scripts - Copy and rename production scripts for dev environment
# This script helps prepare scripts for dev environment deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up dev scripts...${NC}\n"

# Get AWS account ID for dev
echo "Getting dev account information..."
ACCOUNT_ID=$(aws sts get-caller-identity --profile flywheel-dev --query Account --output text 2>/dev/null || echo "")
if [ -z "$ACCOUNT_ID" ]; then
    echo -e "${YELLOW}Warning: Could not get dev account ID. You may need to set AWS_PROFILE=flywheel-dev${NC}"
    read -p "Enter dev account ID: " ACCOUNT_ID
fi

GLUE_BUCKET="aws-glue-assets-${ACCOUNT_ID}-us-east-1"
echo -e "Dev Account ID: ${GREEN}${ACCOUNT_ID}${NC}"
echo -e "Glue Assets Bucket: ${GREEN}${GLUE_BUCKET}${NC}\n"

# List of scripts that need dev versions
declare -A SCRIPTS=(
    ["etl-omc-flywheel-prod-infobase-split-and-bucket.py"]="etl-omc-flywheel-dev-infobase-split-and-bucket.py"
    ["etl-omc-flywheel-prod-addressable-bucket.py"]="etl-omc-flywheel-dev-addressable-bucket.py"
    ["register-staged-tables.py"]="etl-omc-flywheel-dev-register-staged-tables.py"
    ["create-athena-bucketed-tables.py"]="etl-omc-flywheel-dev-create-athena-bucketed-tables.py"
    ["etl-omc-flywheel-prod-infobase-split-and-part.py"]="etl-omc-flywheel-dev-infobase-split-and-part.py"
    ["etl-omc-flywheel-prod-addressable-split-and-part.py"]="etl-omc-flywheel-dev-addressable-split-and-part.py"
    ["etl-omc-flywheel-prod-register-part-tables.py"]="etl-omc-flywheel-dev-register-part-tables.py"
    ["etl-omc-flywheel-prod-prepare-part-tables.py"]="etl-omc-flywheel-dev-prepare-part-tables.py"
)

# Shared scripts (no environment in name)
SHARED_SCRIPTS=(
    "create-part-addressable-ids-er-table.py"
    "create-all-part-tables-er.py"
    "generate-cleanrooms-report.py"
)

echo -e "${GREEN}Step 1: Creating dev script copies${NC}\n"

# Create dev versions of scripts
for prod_script in "${!SCRIPTS[@]}"; do
    dev_script="${SCRIPTS[$prod_script]}"
    
    if [ ! -f "$SCRIPT_DIR/$prod_script" ]; then
        # Try alternative source names
        alt_source=$(echo "$prod_script" | sed 's/etl-omc-flywheel-prod-//')
        if [ -f "$SCRIPT_DIR/$alt_source" ]; then
            prod_script="$alt_source"
        else
            echo -e "${YELLOW}⚠️  Source not found: $prod_script${NC}"
            continue
        fi
    fi
    
    if [ -f "$SCRIPT_DIR/$dev_script" ]; then
        echo -e "⏭️  Already exists: $dev_script"
    else
        echo -e "📝 Creating: $dev_script from $prod_script"
        cp "$SCRIPT_DIR/$prod_script" "$SCRIPT_DIR/$dev_script"
        
        # Replace hardcoded 'prod' with 'dev' in the script (if any)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' 's/omc-flywheel-prod/omc-flywheel-dev/g' "$SCRIPT_DIR/$dev_script"
            sed -i '' 's/omc_flywheel_prod/omc_flywheel_dev/g' "$SCRIPT_DIR/$dev_script"
            sed -i '' 's/"prod"/"dev"/g' "$SCRIPT_DIR/$dev_script"
            sed -i '' "s/'prod'/'dev'/g" "$SCRIPT_DIR/$dev_script"
        else
            # Linux
            sed -i 's/omc-flywheel-prod/omc-flywheel-dev/g' "$SCRIPT_DIR/$dev_script"
            sed -i 's/omc_flywheel_prod/omc_flywheel_dev/g' "$SCRIPT_DIR/$dev_script"
            sed -i 's/"prod"/"dev"/g' "$SCRIPT_DIR/$dev_script"
            sed -i "s/'prod'/'dev'/g" "$SCRIPT_DIR/$dev_script"
        fi
    fi
done

echo -e "\n${GREEN}Step 2: Uploading scripts to S3${NC}\n"

# Upload dev scripts
for prod_script in "${!SCRIPTS[@]}"; do
    dev_script="${SCRIPTS[$prod_script]}"
    
    if [ -f "$SCRIPT_DIR/$dev_script" ]; then
        echo -e "📤 Uploading: $dev_script"
        aws s3 cp "$SCRIPT_DIR/$dev_script" \
            "s3://${GLUE_BUCKET}/scripts/${dev_script}" \
            --profile flywheel-dev 2>/dev/null || {
            echo -e "${RED}❌ Failed to upload $dev_script${NC}"
            echo -e "   Make sure AWS_PROFILE=flywheel-dev is set and you have S3 write permissions"
        }
    fi
done

# Upload shared scripts
echo -e "\n${GREEN}Step 3: Uploading shared scripts${NC}\n"
for script in "${SHARED_SCRIPTS[@]}"; do
    if [ -f "$SCRIPT_DIR/$script" ]; then
        echo -e "📤 Uploading: $script"
        aws s3 cp "$SCRIPT_DIR/$script" \
            "s3://${GLUE_BUCKET}/scripts/${script}" \
            --profile flywheel-dev 2>/dev/null || {
            echo -e "${YELLOW}⚠️  Failed to upload $script (may already exist)${NC}"
        }
    else
        echo -e "${YELLOW}⚠️  Script not found: $script${NC}"
    fi
done

echo -e "\n${GREEN}✅ Dev script setup complete!${NC}\n"
echo -e "Next steps:"
echo -e "1. Review the dev scripts in: ${SCRIPT_DIR}"
echo -e "2. Deploy infrastructure: cd infra/stacks/dev-gluejobs && terraform apply"
echo -e "3. Run validation pipeline (see docs/DEV_SETUP_AND_VALIDATION.md)"

