#!/bin/bash
# Script to update dev environment via Terraform
# This updates Glue jobs, IAM policies, monitoring, and Cleanrooms configuration

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_DIR="/Users/patrick.spann/Documents/acx_omc_flywheel_cr"
STACKS_DIR="${BASE_DIR}/infra/stacks"
REGION="us-east-1"
AWS_PROFILE="${AWS_PROFILE:-flywheel-dev}"  # Use flywheel-dev profile

# Stacks to update (in order)
STACKS=(
    "dev-gluejobs"
    "dev-monitoring"
    "dev-crconfigtables"
)

# Function to run terraform commands
run_terraform() {
    local stack_dir=$1
    local command=$2
    local description=$3
    
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}📦 Stack: ${stack_dir}${NC}"
    echo -e "${BLUE}🔧 Command: ${description}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    cd "${STACKS_DIR}/${stack_dir}"
    
    # Export AWS profile for all terraform commands
    export AWS_PROFILE="${AWS_PROFILE}"
    
    case "$command" in
        "init")
            echo -e "${BLUE}▶️  Initializing Terraform (Profile: ${AWS_PROFILE})...${NC}"
            terraform init
            ;;
        "plan")
            echo -e "${BLUE}▶️  Planning changes (Profile: ${AWS_PROFILE})...${NC}"
            terraform plan -out=tfplan
            ;;
        "apply")
            echo -e "${BLUE}▶️  Applying changes (Profile: ${AWS_PROFILE})...${NC}"
            if [ -f "tfplan" ]; then
                terraform apply tfplan
                rm -f tfplan
            else
                terraform apply -auto-approve
            fi
            ;;
        "validate")
            echo -e "${BLUE}▶️  Validating configuration (Profile: ${AWS_PROFILE})...${NC}"
            terraform validate
            ;;
        *)
            echo -e "${RED}❌ Unknown command: ${command}${NC}"
            return 1
            ;;
    esac
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ ${description} completed successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ ${description} failed${NC}"
        return 1
    fi
}

# Main execution
main() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║   Dev Environment Terraform Update                       ║"
    echo "║   Updating Glue Jobs, IAM Policies, Monitoring, etc.    ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"
    
    echo -e "${BLUE}📋 Stacks to update:${NC}"
    for stack in "${STACKS[@]}"; do
        echo -e "  • ${stack}"
    done
    echo ""
    echo -e "${BLUE}🔐 AWS Profile: ${AWS_PROFILE}${NC}"
    echo -e "${BLUE}🌍 Region: ${REGION}${NC}"
    echo ""
    
    # Check if we're in the right directory
    if [ ! -d "${STACKS_DIR}" ]; then
        echo -e "${RED}❌ Error: Stacks directory not found: ${STACKS_DIR}${NC}"
        exit 1
    fi
    
    # Ask for confirmation
    read -p "Continue with Terraform update? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}⏸️  Update cancelled${NC}"
        exit 0
    fi
    
    # Step 1: Validate all stacks
    echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Step 1: Validating Terraform Configuration${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    for stack in "${STACKS[@]}"; do
        run_terraform "$stack" "validate" "Validation" || {
            echo -e "${RED}❌ Validation failed for ${stack}${NC}"
            exit 1
        }
    done
    
    # Step 2: Initialize all stacks
    echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Step 2: Initializing Terraform${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    for stack in "${STACKS[@]}"; do
        run_terraform "$stack" "init" "Initialization" || {
            echo -e "${RED}❌ Initialization failed for ${stack}${NC}"
            exit 1
        }
    done
    
    # Step 3: Plan changes for all stacks
    echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Step 3: Planning Changes${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    for stack in "${STACKS[@]}"; do
        run_terraform "$stack" "plan" "Planning" || {
            echo -e "${RED}❌ Planning failed for ${stack}${NC}"
            exit 1
        }
    done
    
    # Step 4: Review plans
    echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}📋 Review Plans${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    echo -e "${BLUE}Plans have been generated for each stack.${NC}"
    echo -e "${BLUE}Review the plans above before applying.${NC}\n"
    
    read -p "Apply all changes? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}⏸️  Apply cancelled. Plans are saved in each stack directory.${NC}"
        exit 0
    fi
    
    # Step 5: Apply changes
    echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Step 4: Applying Changes${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    for stack in "${STACKS[@]}"; do
        run_terraform "$stack" "apply" "Application" || {
            echo -e "${RED}❌ Application failed for ${stack}${NC}"
            echo -e "${YELLOW}⚠️  Previous stacks may have been updated. Review state.${NC}"
            exit 1
        }
    done
    
    # Success summary
    echo -e "\n${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   ✅ Dev Environment Update Completed Successfully!      ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}\n"
    
    echo -e "${BLUE}📊 Updated Stacks:${NC}"
    for stack in "${STACKS[@]}"; do
        echo -e "  ✅ ${stack}"
    done
    
    echo -e "\n${BLUE}📋 Next Steps:${NC}"
    echo -e "  • Verify Glue jobs in AWS Console"
    echo -e "  • Check IAM roles and policies"
    echo -e "  • Review monitoring configuration"
    echo -e "  • Test job execution with run-dev-flow.sh"
    echo ""
}

# Run main function
main "$@"

