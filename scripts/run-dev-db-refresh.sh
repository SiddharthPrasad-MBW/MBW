#!/bin/bash
# Dev Environment Database Refresh Automation
# Automates the 7-step database refresh process for partitioned tables pipeline
#
# Usage:
#   ./scripts/run-dev-db-refresh.sh [--dry-run] [--skip-steps=1,2] [--snapshot-dt=YYYY-MM-DD]
#
# Steps:
#   1. addressable-split-and-part (can run in parallel with step 2)
#   2. infobase-split-and-part (can run in parallel with step 1)
#   3. register-part-tables (creates initial table definitions)
#   4. prepare-part-tables (ensures partitioning, runs MSCK REPAIR)
#   5. create-part-addressable-ids-er-table (Entity Resolution table)
#   6. generate-data-monitor-report (Data quality monitoring)
#   7. generate-cleanrooms-report (Cleanrooms status report)

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
ENV="dev"
REGION="us-east-1"
AWS_PROFILE="${AWS_PROFILE:-flywheel-dev}"
JOB_PREFIX="etl-omc-flywheel-${ENV}"

# Job names (7-step process)
JOB_1="${JOB_PREFIX}-addressable-split-and-part"
JOB_2="${JOB_PREFIX}-infobase-split-and-part"
JOB_3="${JOB_PREFIX}-register-part-tables"
JOB_4="${JOB_PREFIX}-prepare-part-tables"
JOB_5="${JOB_PREFIX}-create-part-addressable-ids-er-table"
JOB_6="etl-omc-flywheel-${ENV}-generate-data-monitor-report"
JOB_7="${JOB_PREFIX}-generate-cleanrooms-report"

# Job configurations with context (for jobs that need multiple runs)
# Format: STEP_NUM:JOB_NAME:PARAMETER_SET_NAME:PARAMETERS_JSON
JOB_CONFIGS=(
    "3:${JOB_3}:addressable_ids:{\"--DATABASE\":\"omc_flywheel_dev_clean\",\"--S3_ROOT\":\"s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_part/addressable_ids/\",\"--TABLE_PREFIX\":\"part_\",\"--MAX_COLS\":\"100\"}"
    "3:${JOB_3}:infobase_attributes:{\"--DATABASE\":\"omc_flywheel_dev_clean\",\"--S3_ROOT\":\"s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_part/infobase_attributes/\",\"--TABLE_PREFIX\":\"part_\",\"--MAX_COLS\":\"100\"}"
)

# Parse command line arguments
DRY_RUN=false
SKIP_STEPS=""
SNAPSHOT_DT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-steps=*)
            SKIP_STEPS="${1#*=}"
            shift
            ;;
        --snapshot-dt=*)
            SNAPSHOT_DT="${1#*=}"
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Usage: $0 [--dry-run] [--skip-steps=1,2] [--snapshot-dt=YYYY-MM-DD]"
            exit 1
            ;;
    esac
done

# Check if step should be skipped
should_skip_step() {
    local step=$1
    if [[ "$SKIP_STEPS" == *"$step"* ]]; then
        return 0
    fi
    return 1
}

# Function to wait for job completion
wait_for_job() {
    local job_name=$1
    local run_id=$2
    local max_wait=${3:-3600}  # Default 1 hour max wait
    
    echo -e "${BLUE}⏳ Waiting for job: ${job_name}${NC}"
    echo -e "${CYAN}   Run ID: ${run_id}${NC}"
    
    local elapsed=0
    local status=""
    local last_status=""
    
    while [ $elapsed -lt $max_wait ]; do
        status=$(aws glue get-job-run \
            --job-name "$job_name" \
            --run-id "$run_id" \
            --query 'JobRun.JobRunState' \
            --output text \
            --region "$REGION" \
            --profile "$AWS_PROFILE" 2>/dev/null || echo "UNKNOWN")
        
        # Only print status if it changed
        if [ "$status" != "$last_status" ]; then
            case "$status" in
                "SUCCEEDED")
                    echo -e "${GREEN}✅ Job completed successfully: ${job_name}${NC}"
                    return 0
                    ;;
                "FAILED"|"ERROR"|"TIMEOUT")
                    echo -e "${RED}❌ Job failed: ${job_name} (Status: ${status})${NC}"
                    echo -e "${YELLOW}📋 Getting error details...${NC}"
                    aws glue get-job-run \
                        --job-name "$job_name" \
                        --run-id "$run_id" \
                        --region "$REGION" \
                        --profile "$AWS_PROFILE" \
                        --query 'JobRun.[ErrorMessage, ErrorString]' \
                        --output json 2>/dev/null || true
                    return 1
                    ;;
                "RUNNING"|"STARTING")
                    echo -e "${BLUE}⏳ Job running... (${elapsed}s elapsed)${NC}"
                    ;;
                "STOPPING"|"STOPPED")
                    echo -e "${YELLOW}⚠️  Job stopped: ${job_name}${NC}"
                    return 1
                    ;;
                *)
                    echo -e "${YELLOW}⚠️  Status: ${status} (${elapsed}s elapsed)${NC}"
                    ;;
            esac
            last_status="$status"
        fi
        
        sleep 30
        elapsed=$((elapsed + 30))
    done
    
    echo -e "${RED}❌ Job timed out after ${max_wait}s: ${job_name}${NC}"
    return 1
}

# Function to get job configs for a step
get_job_configs_for_step() {
    local step_num=$1
    local configs=()
    for config in "${JOB_CONFIGS[@]}"; do
        local config_step=$(echo "$config" | cut -d':' -f1)
        if [ "$config_step" = "$step_num" ]; then
            configs+=("$config")
        fi
    done
    echo "${configs[@]}"
}

# Function to start a job and wait for completion
run_job() {
    local job_name=$1
    local step_name=$2
    local step_num=$3
    local max_wait=${4:-3600}
    local job_args=${5:-""}
    local context_name=${6:-""}
    
    echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🚀 Step ${step_num}: ${step_name}${NC}"
    if [ -n "$context_name" ]; then
        echo -e "${GREEN}📌 Context: ${context_name}${NC}"
    fi
    echo -e "${GREEN}📝 Job: ${job_name}${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    # Check if step should be skipped
    if should_skip_step "$step_num"; then
        echo -e "${YELLOW}⏭️  Skipping step ${step_num} (--skip-steps)${NC}"
        return 0
    fi
    
    # Check if job exists
    if ! aws glue get-job --job-name "$job_name" --region "$REGION" --profile "$AWS_PROFILE" &>/dev/null; then
        echo -e "${RED}❌ Job not found: ${job_name}${NC}"
        echo -e "${YELLOW}💡 Verify the job exists in AWS Glue${NC}"
        return 1
    fi
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${CYAN}🔍 DRY RUN: Would start job: ${job_name}${NC}"
        if [ -n "$context_name" ]; then
            echo -e "${CYAN}   Context: ${context_name}${NC}"
        fi
        if [ -n "$job_args" ]; then
            echo -e "${CYAN}   With arguments: ${job_args}${NC}"
        fi
        return 0
    fi
    
    # Start the job
    echo -e "${BLUE}▶️  Starting job: ${job_name}${NC}"
    if [ -n "$context_name" ]; then
        echo -e "${CYAN}   Context: ${context_name}${NC}"
    fi
    
    local start_cmd="aws glue start-job-run --job-name \"$job_name\" --region \"$REGION\" --profile \"$AWS_PROFILE\""
    if [ -n "$job_args" ]; then
        start_cmd="${start_cmd} --arguments '${job_args}'"
    fi
    
    local run_id=$(eval "$start_cmd" --query 'JobRunId' --output text)
    
    if [ -z "$run_id" ] || [ "$run_id" == "None" ]; then
        echo -e "${RED}❌ Failed to start job: ${job_name}${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ Job started successfully${NC}"
    echo -e "${CYAN}   Run ID: ${run_id}${NC}"
    echo -e "${CYAN}   Monitor: aws glue get-job-run --job-name \"$job_name\" --run-id \"$run_id\" --profile \"$AWS_PROFILE\"${NC}"
    
    # Wait for completion
    if wait_for_job "$job_name" "$run_id" "$max_wait"; then
        if [ -n "$context_name" ]; then
            echo -e "${GREEN}✅ Step ${step_num} (${context_name}) completed: ${step_name}${NC}"
        else
            echo -e "${GREEN}✅ Step ${step_num} completed: ${step_name}${NC}"
        fi
        return 0
    else
        if [ -n "$context_name" ]; then
            echo -e "${RED}❌ Step ${step_num} (${context_name}) failed: ${step_name}${NC}"
        else
            echo -e "${RED}❌ Step ${step_num} failed: ${step_name}${NC}"
        fi
        return 1
    fi
}

# Function to run a step with multiple contexts (parallel execution)
run_step_with_contexts() {
    local step_num=$1
    local step_name=$2
    local max_wait=${3:-1800}
    
    # Get all configs for this step
    local configs=($(get_job_configs_for_step "$step_num"))
    
    if [ ${#configs[@]} -eq 0 ]; then
        # No special configs, run normally
        local job_name_var="JOB_${step_num}"
        local job_name="${!job_name_var}"
        run_job "$job_name" "$step_name" "$step_num" "$max_wait"
        return $?
    fi
    
    # Multiple configs found - run in parallel
    echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🚀 Step ${step_num}: ${step_name} (Multiple Contexts)${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    if should_skip_step "$step_num"; then
        echo -e "${YELLOW}⏭️  Skipping step ${step_num} (--skip-steps)${NC}"
        return 0
    fi
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${CYAN}🔍 DRY RUN: Would start ${#configs[@]} job runs in parallel${NC}"
        for config in "${configs[@]}"; do
            local context=$(echo "$config" | cut -d':' -f3)
            local params=$(echo "$config" | cut -d':' -f4-)
            echo -e "${CYAN}   Context: ${context}${NC}"
            echo -e "${CYAN}   Parameters: ${params}${NC}"
        done
        return 0
    fi
    
    # Start all jobs in parallel
    echo -e "${BLUE}▶️  Starting ${#configs[@]} job runs in parallel...${NC}"
    local run_ids=()
    local contexts=()
    local job_names=()
    
    for config in "${configs[@]}"; do
        local job_name=$(echo "$config" | cut -d':' -f2)
        local context=$(echo "$config" | cut -d':' -f3)
        local params=$(echo "$config" | cut -d':' -f4-)
        
        echo -e "${BLUE}   Starting: ${context}${NC}"
        local start_cmd="aws glue start-job-run --job-name \"$job_name\" --region \"$REGION\" --profile \"$AWS_PROFILE\" --arguments '${params}'"
        local run_id=$(eval "$start_cmd" --query 'JobRunId' --output text)
        
        if [ -z "$run_id" ] || [ "$run_id" == "None" ]; then
            echo -e "${RED}❌ Failed to start job for context: ${context}${NC}"
            return 1
        fi
        
        run_ids+=("$run_id")
        contexts+=("$context")
        job_names+=("$job_name")
        echo -e "${GREEN}✅ Started ${context} (Run ID: ${run_id})${NC}"
    done
    
    # Wait for all to complete
    echo -e "\n${BLUE}⏳ Waiting for all job runs to complete...${NC}"
    local failed=false
    
    for i in "${!run_ids[@]}"; do
        local run_id="${run_ids[$i]}"
        local context="${contexts[$i]}"
        local job_name="${job_names[$i]}"
        
        echo -e "${CYAN}   Waiting for: ${context}${NC}"
        if ! wait_for_job "$job_name" "$run_id" "$max_wait"; then
            echo -e "${RED}❌ Workflow stopped: Step ${step_num} (${context}) failed${NC}"
            failed=true
        fi
    done
    
    if [ "$failed" = true ]; then
        return 1
    fi
    
    echo -e "${GREEN}✅ Step ${step_num} completed: All contexts succeeded${NC}\n"
    return 0
}

# Main execution
main() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║   Dev Environment Database Refresh Automation           ║"
    echo "║   7-Step Partitioned Tables Pipeline                    ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"
    
    echo -e "${BLUE}📋 Configuration:${NC}"
    echo -e "   Environment: ${ENV}"
    echo -e "   Region: ${REGION}"
    echo -e "   AWS Profile: ${AWS_PROFILE}"
    if [ "$DRY_RUN" = true ]; then
        echo -e "   ${CYAN}Mode: DRY RUN (no jobs will be executed)${NC}"
    fi
    if [ -n "$SKIP_STEPS" ]; then
        echo -e "   ${YELLOW}Skipping steps: ${SKIP_STEPS}${NC}"
    fi
    if [ -n "$SNAPSHOT_DT" ]; then
        echo -e "   Snapshot Date: ${SNAPSHOT_DT}"
    fi
    echo ""
    
    echo -e "${BLUE}📋 Workflow Steps:${NC}"
    echo -e "  1. ${JOB_1} (can run simultaneously with step 2)"
    echo -e "  2. ${JOB_2} (can run simultaneously with step 1)"
    echo -e "  3. ${JOB_3} (creates initial table definitions)"
    echo -e "     - Runs twice in parallel:"
    echo -e "       • addressable_ids (S3_ROOT: split_part/addressable_ids/)"
    echo -e "       • infobase_attributes (S3_ROOT: split_part/infobase_attributes/)"
    echo -e "  4. ${JOB_4} (ensures partitioning, runs MSCK REPAIR)"
    echo -e "  5. ${JOB_5} (Entity Resolution table)"
    echo -e "  6. ${JOB_6} (Data Monitor)"
    echo -e "  7. ${JOB_7} (Cleanrooms Report)"
    echo ""
    
    if [ "$DRY_RUN" = false ]; then
        read -p "Continue with workflow execution? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}⏸️  Execution cancelled${NC}"
            exit 0
        fi
    fi
    
    local start_time=$(date +%s)
    
    # Step 1 & 2: Split jobs (can run simultaneously)
    echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🚀 Steps 1 & 2: Split Jobs (Parallel Execution)${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    if ! should_skip_step "1" && ! should_skip_step "2"; then
        if [ "$DRY_RUN" = true ]; then
            echo -e "${CYAN}🔍 DRY RUN: Would start both jobs simultaneously${NC}"
        else
            echo -e "${BLUE}▶️  Starting both split jobs simultaneously...${NC}"
            
            local args_1=""
            local args_2=""
            if [ -n "$SNAPSHOT_DT" ]; then
                args_1="{\"--SNAPSHOT_DT\": \"${SNAPSHOT_DT}\"}"
                args_2="{\"--SNAPSHOT_DT\": \"${SNAPSHOT_DT}\"}"
            fi
            
            local run_id_1=""
            local run_id_2=""
            
            if ! should_skip_step "1"; then
                if [ -n "$args_1" ]; then
                    run_id_1=$(aws glue start-job-run --job-name "$JOB_1" --region "$REGION" --profile "$AWS_PROFILE" --arguments "$args_1" --query 'JobRunId' --output text)
                else
                    run_id_1=$(aws glue start-job-run --job-name "$JOB_1" --region "$REGION" --profile "$AWS_PROFILE" --query 'JobRunId' --output text)
                fi
            fi
            
            if ! should_skip_step "2"; then
                if [ -n "$args_2" ]; then
                    run_id_2=$(aws glue start-job-run --job-name "$JOB_2" --region "$REGION" --profile "$AWS_PROFILE" --arguments "$args_2" --query 'JobRunId' --output text)
                else
                    run_id_2=$(aws glue start-job-run --job-name "$JOB_2" --region "$REGION" --profile "$AWS_PROFILE" --query 'JobRunId' --output text)
                fi
            fi
            
            if [ -n "$run_id_1" ] && [ "$run_id_1" != "None" ]; then
                echo -e "${GREEN}✅ Job 1 started: ${JOB_1} (Run ID: ${run_id_1})${NC}"
            fi
            if [ -n "$run_id_2" ] && [ "$run_id_2" != "None" ]; then
                echo -e "${GREEN}✅ Job 2 started: ${JOB_2} (Run ID: ${run_id_2})${NC}"
            fi
            
            # Wait for both to complete
            echo -e "\n${BLUE}⏳ Waiting for both split jobs to complete...${NC}"
            
            local failed=false
            if [ -n "$run_id_1" ] && [ "$run_id_1" != "None" ]; then
                if ! wait_for_job "$JOB_1" "$run_id_1" 3600; then
                    echo -e "${RED}❌ Workflow stopped: ${JOB_1} failed${NC}"
                    failed=true
                fi
            fi
            
            if [ -n "$run_id_2" ] && [ "$run_id_2" != "None" ]; then
                if ! wait_for_job "$JOB_2" "$run_id_2" 3600; then
                    echo -e "${RED}❌ Workflow stopped: ${JOB_2} failed${NC}"
                    failed=true
                fi
            fi
            
            if [ "$failed" = true ]; then
                exit 1
            fi
            
            echo -e "${GREEN}✅ Both split jobs completed successfully${NC}\n"
        fi
    else
        echo -e "${YELLOW}⏭️  Skipping steps 1 & 2 (--skip-steps)${NC}\n"
    fi
    
    # Step 3: Register Part Tables (runs twice with different S3_ROOT - parallel)
    run_step_with_contexts "3" "Register Part Tables" 1800 || {
        echo -e "${RED}❌ Workflow stopped at Step 3${NC}"
        exit 1
    }
    
    # Step 4: Prepare Part Tables
    run_job "$JOB_4" "Prepare Part Tables" "4" 1800 || {
        echo -e "${RED}❌ Workflow stopped at Step 4${NC}"
        exit 1
    }
    
    # Step 5: Create Part Addressable IDs ER Table
    run_job "$JOB_5" "Create Part Addressable IDs ER Table" "5" 1800 || {
        echo -e "${RED}❌ Workflow stopped at Step 5${NC}"
        exit 1
    }
    
    # Step 6: Generate Data Monitor Report
    run_job "$JOB_6" "Generate Data Monitor Report" "6" 600 || {
        echo -e "${RED}❌ Workflow stopped at Step 6${NC}"
        exit 1
    }
    
    # Step 7: Generate Cleanrooms Report
    run_job "$JOB_7" "Generate Cleanrooms Report" "7" 600 || {
        echo -e "${RED}❌ Workflow stopped at Step 7${NC}"
        exit 1
    }
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    echo -e "\n${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   ✅ Database Refresh Completed Successfully!            ║${NC}"
    echo -e "${GREEN}║   ⏱️  Total Duration: ${minutes}m ${seconds}s                          ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}\n"
    
    echo -e "${BLUE}📊 Next Steps:${NC}"
    echo -e "  • Review job logs in CloudWatch"
    echo -e "  • Verify data in S3: s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_part/"
    echo -e "  • Check Glue tables in database: omc_flywheel_dev_clean"
    echo -e "  • Review reports:"
    echo -e "    - Data Monitor: s3://omc-flywheel-dev-analysis-data/data-monitor-reports/"
    echo -e "    - Cleanrooms: s3://omc-flywheel-dev-analysis-data/cleanrooms-reports/"
    echo ""
}

# Run main function
main "$@"

