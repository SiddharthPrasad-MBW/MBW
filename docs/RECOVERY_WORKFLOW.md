# Step Functions Recovery Workflow

## Overview

When a Step Functions execution fails, you have two options:
1. **Restart the entire workflow** (wastes time if early steps already completed)
2. **Resume from the failed step** using local scripts (recommended)

This guide covers how to identify failures and resume efficiently.

## Understanding Step Functions Limitations

**Important:** Step Functions does **not** support resuming from a failed step. Each execution is independent and always starts from the beginning.

**Time Impact:**
- Steps 1 & 2 (split jobs) take ~1 hour each
- If Step 5 fails, restarting would waste ~2 hours rerunning Steps 1-4
- **Solution:** Use local scripts to skip completed steps

## Step-by-Step Recovery Process

### Step 1: Identify the Failure

#### Option A: Check Step Functions Console

1. Navigate to AWS Step Functions console
2. Select state machine: `omc-flywheel-{env}-db-refresh`
3. Click on the failed execution
4. Review the visual workflow:
   - ✅ Green = Completed successfully
   - ❌ Red = Failed
   - ⏸️ Gray = Not executed (stopped before reaching)

**Example:**
```
Step1_ParallelSplitJobs: ✅ (completed)
Step2_RegisterPartTables: ✅ (completed)
Step3_PreparePartTables: ❌ (failed)
Step4_CreateERTable: ⏸️ (not executed)
```

#### Option B: Check SNS Notification Email

If you're subscribed to notifications, you'll receive an email with:
- Which step failed
- Error message
- Execution ARN

#### Option C: Check CloudWatch Logs

```bash
# View Step Functions execution logs
aws logs tail /aws/vendedlogs/states/omc-flywheel-dev-db-refresh --follow \
  --profile flywheel-dev

# Filter for errors
aws logs filter-log-events \
  --log-group-name /aws/vendedlogs/states/omc-flywheel-dev-db-refresh \
  --filter-pattern "ERROR" \
  --profile flywheel-dev
```

### Step 2: Determine Which Steps Completed

**Completed Steps:**
- ✅ All steps **before** the failed step completed successfully
- ✅ Steps that show "SUCCEEDED" in the execution graph

**Failed Step:**
- ❌ The step that shows "FAILED" or "TIMED_OUT"
- Check error details for root cause

**Not Executed:**
- ⏸️ All steps **after** the failed step were not executed

### Step 3: Fix the Underlying Issue

Before resuming, **fix the root cause**:

1. **Check Glue Job Logs:**
   ```bash
   # Get the failed job run ID from Step Functions output
   # Then check Glue job logs
   aws glue get-job-run \
     --job-name <JOB_NAME> \
     --run-id <RUN_ID> \
     --profile flywheel-dev
   ```

2. **Common Issues:**
   - **Data issues:** Missing source data, corrupted files
   - **Permission issues:** IAM role missing permissions
   - **Resource limits:** Glue job timeout, insufficient DPUs
   - **Schema issues:** Table schema mismatch, partition errors

3. **Verify the Fix:**
   - Test the fix manually if possible
   - Ensure data/configuration is correct

### Step 4: Resume Using Local Scripts

Once the issue is fixed, use local scripts to resume from the failed step.

#### Dev Environment

```bash
# Example: Steps 1-3 completed, Step 4 failed
# Resume from Step 4 (skip steps 1, 2, 3)
./scripts/run-dev-db-refresh.sh --skip-steps=1,2,3

# Example: Steps 1-5 completed, Step 6 failed
# Resume from Step 6 (skip steps 1, 2, 3, 4, 5)
./scripts/run-dev-db-refresh.sh --skip-steps=1,2,3,4,5
```

#### Production Environment

```bash
# Set AWS profile
export AWS_PROFILE=flywheel-prod

# Example: Steps 1-4 completed, Step 5 failed
# Resume from Step 5 (skip steps 1, 2, 3, 4)
./scripts/run-prod-db-refresh.sh --skip-steps=1,2,3,4
```

#### Step Mapping Reference

| Step | Description | Job Name Pattern |
|------|-------------|------------------|
| 1 | Addressable Split and Part | `*-addressable-split-and-part` |
| 2 | Infobase Split and Part | `*-infobase-split-and-part` |
| 3 | Register Part Tables | `*-register-part-tables` |
| 4 | Prepare Part Tables | `*-prepare-part-tables` |
| 5 | Create ER Table | `*-create-part-addressable-ids-er-table` |
| 6 | Data Monitor Report | `*-generate-data-monitor-report` |
| 7 | Cleanrooms Report | `*-generate-cleanrooms-report` |

**Note:** Step 3 runs twice in parallel (addressable_ids and infobase_attributes contexts). If Step 3 fails, check which context failed.

### Step 5: Verify Recovery

After resuming:

1. **Monitor the script output** for real-time status
2. **Check Step Functions console** (if you want to track in AWS)
3. **Verify outputs:**
   - Data in S3 (for data processing steps)
   - Reports generated (for reporting steps)
   - Tables created/updated (for table creation steps)

## Common Failure Scenarios

### Scenario 1: Step 1 or 2 Fails (Split Jobs)

**Time Impact:** Low (early failure, minimal time wasted)

**Recovery:**
```bash
# If Step 1 failed, just rerun (no skip needed)
./scripts/run-dev-db-refresh.sh

# If Step 2 failed, skip Step 1
./scripts/run-dev-db-refresh.sh --skip-steps=1
```

**Common Causes:**
- Source data missing or corrupted
- S3 permissions issue
- Glue job timeout (increase timeout if needed)

### Scenario 2: Step 3 Fails (Register Part Tables)

**Time Impact:** Medium (~1-2 hours wasted if Steps 1-2 completed)

**Recovery:**
```bash
# Skip Steps 1 and 2 (the 1-hour split jobs)
./scripts/run-dev-db-refresh.sh --skip-steps=1,2
```

**Common Causes:**
- S3 path incorrect
- Database doesn't exist
- Table prefix conflict
- Schema inference issues

**Note:** Step 3 runs twice (addressable_ids and infobase_attributes). Check which context failed.

### Scenario 3: Step 4 Fails (Prepare Part Tables)

**Time Impact:** High (~2 hours wasted if Steps 1-3 completed)

**Recovery:**
```bash
# Skip Steps 1, 2, 3 (saves ~2 hours)
./scripts/run-dev-db-refresh.sh --skip-steps=1,2,3
```

**Common Causes:**
- Tables not registered (Step 3 didn't complete)
- Partition detection issues
- MSCK REPAIR failures
- Lake Formation permissions

### Scenario 4: Step 5 Fails (Create ER Table)

**Time Impact:** High (~2-3 hours wasted if Steps 1-4 completed)

**Recovery:**
```bash
# Skip Steps 1, 2, 3, 4 (saves ~2-3 hours)
./scripts/run-dev-db-refresh.sh --skip-steps=1,2,3,4
```

**Common Causes:**
- ER pipeline not configured
- ID namespace issues
- Schema mapping errors
- Cleanrooms permissions

### Scenario 5: Step 6 or 7 Fails (Reporting)

**Time Impact:** Very High (~2-3 hours wasted if Steps 1-5 completed)

**Recovery:**
```bash
# Skip Steps 1, 2, 3, 4, 5 (saves ~2-3 hours)
./scripts/run-dev-db-refresh.sh --skip-steps=1,2,3,4,5
```

**Common Causes:**
- Report generation script errors
- S3 write permissions
- Data quality issues (for data monitor report)
- Cleanrooms API issues (for cleanrooms report)

## Best Practices

### 1. Always Fix Root Cause First

**Don't skip this step!** Resuming without fixing the issue will just fail again.

### 2. Verify Data/State Before Resuming

For data processing steps, verify:
- Source data exists and is correct
- Previous step outputs are valid
- Tables/partitions are in expected state

### 3. Use Dry Run for Testing

Before resuming, test with dry run:
```bash
./scripts/run-dev-db-refresh.sh --skip-steps=1,2,3 --dry-run
```

### 4. Monitor Recovery Execution

Watch the script output to ensure:
- Correct steps are being skipped
- Jobs start successfully
- No unexpected errors

### 5. Document Failures

Keep a log of:
- Which step failed
- Root cause
- Fix applied
- Recovery time saved

This helps identify patterns and improve reliability.

## Time Savings Examples

| Failed Step | Steps to Skip | Time Saved |
|-------------|---------------|------------|
| Step 1 | None | 0 hours |
| Step 2 | Step 1 | ~1 hour |
| Step 3 | Steps 1, 2 | ~2 hours |
| Step 4 | Steps 1, 2, 3 | ~2 hours |
| Step 5 | Steps 1, 2, 3, 4 | ~2-3 hours |
| Step 6 | Steps 1, 2, 3, 4, 5 | ~2-3 hours |
| Step 7 | Steps 1, 2, 3, 4, 5, 6 | ~2-3 hours |

**Note:** Time estimates assume:
- Steps 1 & 2: ~1 hour each (parallel execution)
- Steps 3-5: ~10-30 minutes each
- Steps 6 & 7: ~5-10 minutes each

## Alternative: Full Restart

If you prefer to restart the entire workflow (not recommended for late failures):

### Via Step Functions Console

1. Navigate to Step Functions console
2. Select state machine
3. Click "Start execution"
4. Use the same input JSON
5. Click "Start execution"

### Via AWS CLI

```bash
# Get state machine ARN
terraform output -json -chdir=infra/stacks/dev-orchestration | \
  jq -r '.step_functions_state_machine_arn.value'

# Start execution
aws stepfunctions start-execution \
  --state-machine-arn <STATE_MACHINE_ARN> \
  --input file://infra/stacks/dev-orchestration/execution-input.json \
  --profile flywheel-dev
```

## Troubleshooting Recovery

### Issue: Script Still Runs Skipped Steps

**Check:** Verify `--skip-steps` format is correct (comma-separated, no spaces)

**Fix:**
```bash
# Correct
--skip-steps=1,2,3

# Incorrect
--skip-steps="1, 2, 3"  # Spaces cause issues
--skip-steps 1,2,3      # Missing equals sign
```

### Issue: Job Fails Immediately After Resume

**Check:**
1. Did you fix the root cause?
2. Is the data/state from previous steps still valid?
3. Are there dependency issues?

**Fix:** Review error logs and verify prerequisites

### Issue: Step 3 Context Confusion

**Remember:** Step 3 runs twice:
- Context A: `addressable_ids` (S3_ROOT: `split_part/addressable_ids/`)
- Context B: `infobase_attributes` (S3_ROOT: `split_part/infobase_attributes/`)

If one context fails, you may need to:
1. Check which context failed
2. Verify the specific S3 path
3. Re-run only that context if possible

## Summary

**Recovery Workflow:**
1. ✅ Identify failure in Step Functions console
2. ✅ Determine which steps completed
3. ✅ Fix root cause
4. ✅ Resume using local scripts with `--skip-steps`
5. ✅ Verify recovery success

**Key Benefit:** Save 1-3 hours by skipping completed steps instead of restarting the entire workflow.

**When to Use:**
- ✅ Any failure after Step 1 (saves time)
- ✅ Especially valuable for failures in Steps 4-7 (saves 2-3 hours)

**When Not to Use:**
- ❌ Step 1 fails (no time to save)
- ❌ Root cause not fixed (will fail again)
- ❌ Data/state corrupted (need full refresh)

