#!/bin/bash
# Step-by-step dev flow execution script
# This script runs the production workflow in dev environment to validate processes

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENV="dev"
REGION="us-east-1"
JOB_PREFIX="etl-omc-flywheel-${ENV}"

# Job names (environment-aware)
JOB_1="${JOB_PREFIX}-addressable-split-and-part"
JOB_2="${JOB_PREFIX}-infobase-split-and-part"
JOB_3="${JOB_PREFIX}-register-part-tables"  # Creates initial table definitions
JOB_4="${JOB_PREFIX}-prepare-part-tables"    # Ensures partitioning and runs MSCK REPAIR
JOB_5="${JOB_PREFIX}-create-part-addressable-ids-er-table"
JOB_6="etl-omc-flywheel-${ENV}-generate-data-monitor-report"  # Data Monitor (from monitoring module)
JOB_7="${JOB_PREFIX}-generate-cleanrooms-report"

# Function to wait for job completion
wait_for_job() {
    local job_name=$1
    local run_id=$2
    local max_wait=${3:-3600}  # Default 1 hour max wait
    
    echo -e "${BLUE}⏳ Waiting for job: ${job_name} (Run ID: ${run_id})${NC}"
    
    local elapsed=0
    local status=""
    
    while [ $elapsed -lt $max_wait ]; do
        status=$(aws glue get-job-run \
            --job-name "$job_name" \
            --run-id "$run_id" \
            --query 'JobRun.JobRunState' \
            --output text \
            --region "$REGION" 2>/dev/null || echo "UNKNOWN")
        
        case "$status" in
            "SUCCEEDED")
                echo -e "${GREEN}✅ Job completed successfully: ${job_name}${NC}"
                return 0
                ;;
            "FAILED"|"ERROR"|"TIMEOUT")
                echo -e "${RED}❌ Job failed: ${job_name} (Status: ${status})${NC}"
                echo -e "${YELLOW}📋 Getting job logs...${NC}"
                aws glue get-job-run \
                    --job-name "$job_name" \
                    --run-id "$run_id" \
                    --region "$REGION" \
                    --query 'JobRun' \
                    --output json | jq '.ErrorMessage, .ErrorString' 2>/dev/null || true
                return 1
                ;;
            "RUNNING"|"STARTING")
                echo -e "${BLUE}⏳ Job still running... (${elapsed}s elapsed)${NC}"
                sleep 30
                elapsed=$((elapsed + 30))
                ;;
            *)
                echo -e "${YELLOW}⚠️  Unknown status: ${status}, waiting...${NC}"
                sleep 10
                elapsed=$((elapsed + 10))
                ;;
        esac
    done
    
    echo -e "${RED}❌ Job timed out after ${max_wait}s: ${job_name}${NC}"
    return 1
}

# Function to start a job and wait for completion
run_job() {
    local job_name=$1
    local step_name=$2
    local max_wait=${3:-3600}
    
    echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🚀 Step: ${step_name}${NC}"
    echo -e "${GREEN}📝 Job: ${job_name}${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    # Check if job exists
    if ! aws glue get-job --job-name "$job_name" --region "$REGION" &>/dev/null; then
        echo -e "${RED}❌ Job not found: ${job_name}${NC}"
        echo -e "${YELLOW}💡 Make sure Terraform has been applied for dev environment${NC}"
        return 1
    fi
    
    # Start the job
    echo -e "${BLUE}▶️  Starting job: ${job_name}${NC}"
    local run_id=$(aws glue start-job-run \
        --job-name "$job_name" \
        --region "$REGION" \
        --query 'JobRunId' \
        --output text)
    
    if [ -z "$run_id" ] || [ "$run_id" == "None" ]; then
        echo -e "${RED}❌ Failed to start job: ${job_name}${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ Job started successfully (Run ID: ${run_id})${NC}"
    
    # Wait for completion
    if wait_for_job "$job_name" "$run_id" "$max_wait"; then
        echo -e "${GREEN}✅ Step completed: ${step_name}${NC}"
        return 0
    else
        echo -e "${RED}❌ Step failed: ${step_name}${NC}"
        return 1
    fi
}

# Main execution
main() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║   Dev Environment Workflow Validation                    ║"
    echo "║   Recreating Production Flow in Dev                      ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"
    
    echo -e "${BLUE}📋 Workflow Steps:${NC}"
    echo -e "  1. ${JOB_1} (can run simultaneously with step 2)"
    echo -e "  2. ${JOB_2} (can run simultaneously with step 1)"
    echo -e "  3. ${JOB_3} (creates initial table definitions)"
    echo -e "  4. ${JOB_4} (ensures partitioning, runs MSCK REPAIR)"
    echo -e "  5. ${JOB_5} (Entity Resolution table)"
    echo -e "  6. ${JOB_6} (Data Monitor)"
    echo -e "  7. ${JOB_7} (Cleanrooms Report)"
    echo ""
    
    read -p "Continue with workflow execution? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}⏸️  Execution cancelled${NC}"
        exit 0
    fi
    
    # Step 1 & 2: Split jobs (can run simultaneously)
    echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🚀 Steps 1 & 2: Split Jobs (Parallel Execution)${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    echo -e "${BLUE}▶️  Starting both split jobs simultaneously...${NC}"
    RUN_ID_1=$(aws glue start-job-run --job-name "$JOB_1" --region "$REGION" --query 'JobRunId' --output text)
    RUN_ID_2=$(aws glue start-job-run --job-name "$JOB_2" --region "$REGION" --query 'JobRunId' --output text)
    
    if [ -z "$RUN_ID_1" ] || [ "$RUN_ID_1" == "None" ] || [ -z "$RUN_ID_2" ] || [ "$RUN_ID_2" == "None" ]; then
        echo -e "${RED}❌ Failed to start one or both split jobs${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Both jobs started:${NC}"
    echo -e "   ${JOB_1} (Run ID: ${RUN_ID_1})"
    echo -e "   ${JOB_2} (Run ID: ${RUN_ID_2})"
    
    # Wait for both to complete
    echo -e "\n${BLUE}⏳ Waiting for both split jobs to complete...${NC}"
    wait_for_job "$JOB_1" "$RUN_ID_1" 3600 || {
        echo -e "${RED}❌ Workflow stopped: ${JOB_1} failed${NC}"
        exit 1
    }
    wait_for_job "$JOB_2" "$RUN_ID_2" 3600 || {
        echo -e "${RED}❌ Workflow stopped: ${JOB_2} failed${NC}"
        exit 1
    }
    echo -e "${GREEN}✅ Both split jobs completed successfully${NC}\n"
    
    # Step 3: Register Part Tables (creates initial table definitions)
    run_job "$JOB_3" "3. Register Part Tables" 1800 || {
        echo -e "${RED}❌ Workflow stopped at Step 3${NC}"
        exit 1
    }
    
    # Step 4: Prepare Part Tables (ensures partitioning, runs MSCK REPAIR)
    run_job "$JOB_4" "4. Prepare Part Tables" 1800 || {
        echo -e "${RED}❌ Workflow stopped at Step 4${NC}"
        exit 1
    }
    
    # Step 5: Create Part Addressable IDs ER Table
    run_job "$JOB_5" "5. Create Part Addressable IDs ER Table" 1800 || {
        echo -e "${RED}❌ Workflow stopped at Step 5${NC}"
        exit 1
    }
    
    # Step 6: Generate Data Monitor Report
    run_job "$JOB_6" "6. Generate Data Monitor Report" 600 || {
        echo -e "${RED}❌ Workflow stopped at Step 6${NC}"
        exit 1
    }
    
    # Step 7: Generate Cleanrooms Report
    run_job "$JOB_7" "7. Generate Cleanrooms Report" 600 || {
        echo -e "${RED}❌ Workflow stopped at Step 7${NC}"
        exit 1
    }
    
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   ✅ Workflow Completed Successfully!                    ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}\n"
    
    echo -e "${BLUE}📊 Next Steps:${NC}"
    echo -e "  • Review job logs in CloudWatch"
    echo -e "  • Verify data in S3: s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_part/"
    echo -e "  • Check Glue tables in database: omc_flywheel_dev"
    echo -e "  • Review Cleanrooms report in: s3://omc-flywheel-dev-analysis-data/cleanrooms-reports/"
    echo -e "  • Run data_monitor.py manually if needed"
    echo ""
}

# Run main function
main "$@"

