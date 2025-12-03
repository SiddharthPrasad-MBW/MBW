# Step Functions Job Parameters Reference

## Where to View Job Parameters

### 1. **AWS Step Functions Console** (Visual & Interactive)

**Access:**
1. Go to AWS Console → Step Functions
2. Click on state machine: `omc-flywheel-dev-db-refresh`
3. Click "Definition" tab to see the full JSON definition
4. Click on any state in the visual graph to see its parameters

**What you'll see:**
- Visual workflow diagram
- Parameters for each step
- Input/output paths
- Retry configurations

**URL Format:**
```
https://console.aws.amazon.com/states/home?region=us-east-1#/statemachines/view/arn:aws:states:us-east-1:417649522250:stateMachine:omc-flywheel-dev-db-refresh
```

### 2. **Terraform Code** (Source of Truth)

**Location:** `infra/modules/orchestration/main.tf`

The Step Functions definition is in the `aws_sfn_state_machine.db_refresh` resource, starting around line 162.

**Key Sections:**
- **Step 1 (Parallel Split Jobs)**: Lines 170-226
  - `Step1A_AddressableSplitAndPart`: Uses `$.Job1Arguments`
  - `Step1B_InfobaseSplitAndPart`: Uses `$.Job2Arguments`

- **Step 2 (Register Part Tables)**: Lines 227-290
  - `Step2A_RegisterAddressableIds`: Uses `$.Job3AArguments`
  - `Step2B_RegisterInfobaseAttributes`: Uses `$.Job3BArguments`

- **Step 3 (Prepare Part Tables)**: Lines 291-310
  - Uses `$.Job4Name` (no arguments)

- **Step 4 (Create ER Table)**: Lines 311-330
  - Uses `$.Job5Name` (no arguments)

- **Step 5 (Parallel Reporting)**: Lines 331-350
  - `Step5A_DataMonitorReport`: Uses `$.Job6Name`
  - `Step5B_CleanroomsReport`: Uses `$.Job7Name`

### 3. **Stack Configuration** (Where Parameters Are Set)

**Dev:** `infra/stacks/dev-orchestration/main.tf`

```hcl
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
```

### 4. **Execution Input** (What Gets Passed to State Machine)

When Step Functions executes, it receives input like this:

```json
{
  "Environment": "dev",
  "Job1Name": "etl-omc-flywheel-dev-addressable-split-and-part",
  "Job2Name": "etl-omc-flywheel-dev-infobase-split-and-part",
  "Job3Name": "etl-omc-flywheel-dev-register-part-tables",
  "Job4Name": "etl-omc-flywheel-dev-prepare-part-tables",
  "Job5Name": "etl-omc-flywheel-dev-create-part-addressable-ids-er-table",
  "Job6Name": "etl-omc-flywheel-dev-generate-data-monitor-report",
  "Job7Name": "etl-omc-flywheel-dev-generate-cleanrooms-report",
  "Job1Arguments": {
    "--SNAPSHOT_DT": "_NONE_"
  },
  "Job2Arguments": {
    "--SNAPSHOT_DT": "_NONE_"
  },
  "Job3AArguments": {
    "--DATABASE": "omc_flywheel_dev_clean",
    "--S3_ROOT": "s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_part/addressable_ids/",
    "--TABLE_PREFIX": "part_",
    "--MAX_COLS": "100"
  },
  "Job3BArguments": {
    "--DATABASE": "omc_flywheel_dev_clean",
    "--S3_ROOT": "s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_part/infobase_attributes/",
    "--TABLE_PREFIX": "part_",
    "--MAX_COLS": "100"
  },
  "SNSTopicArn": "arn:aws:sns:us-east-1:417649522250:omc-flywheel-dev-db-refresh-notifications"
}
```

**View in Console:**
1. Go to Step Functions → Your state machine
2. Click on an execution
3. Click "Input" tab to see what was passed in
4. Click on any step → "Input" to see what that step received

### 5. **AWS CLI** (Programmatic Access)

```bash
# Get state machine definition
aws stepfunctions describe-state-machine \
  --state-machine-arn <ARN> \
  --query 'definition' \
  --output json | python3 -m json.tool

# Get execution input
aws stepfunctions describe-execution \
  --execution-arn <EXECUTION_ARN> \
  --query 'input' \
  --output json | python3 -m json.tool

# Get step input/output
aws stepfunctions get-execution-history \
  --execution-arn <EXECUTION_ARN> \
  --query 'events[?type==`TaskStateEntered`].{step: stateEnteredEventDetails.name, input: stateEnteredEventDetails.input}' \
  --output json
```

## Parameter Mapping

### How Parameters Flow

1. **Terraform Stack** (`dev-orchestration/main.tf`)
   - Defines `job_arguments` map
   - Passed to module

2. **EventBridge Target** (if scheduled)
   - Formats input JSON
   - Passes to Step Functions

3. **Step Functions State Machine**
   - Receives input JSON
   - Each step uses JSONPath to extract:
     - `$.Job1Name` → Job name
     - `$.Job1Arguments` → Job arguments map
     - `$.Job3AArguments` → Register tables (addressable_ids) arguments
     - `$.Job3BArguments` → Register tables (infobase_attributes) arguments

4. **Glue Job Execution**
   - Step Functions calls `glue:startJobRun.sync`
   - Passes `JobName` and `Arguments` to Glue
   - Glue job receives arguments as `--PARAMETER_NAME value`

## Current Parameters by Step

### Step 1: Addressable Split and Part
- **Job Name:** `$.Job1Name`
- **Arguments:** `$.Job1Arguments`
  - `--SNAPSHOT_DT`: `_NONE_` (auto-discover)

### Step 1: Infobase Split and Part
- **Job Name:** `$.Job2Name`
- **Arguments:** `$.Job2Arguments`
  - `--SNAPSHOT_DT`: `_NONE_` (auto-discover)

### Step 2: Register Part Tables (Addressable IDs)
- **Job Name:** `$.Job3Name`
- **Arguments:** `$.Job3AArguments`
  - `--DATABASE`: `omc_flywheel_dev_clean`
  - `--S3_ROOT`: `s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_part/addressable_ids/`
  - `--TABLE_PREFIX`: `part_`
  - `--MAX_COLS`: `100`

### Step 2: Register Part Tables (Infobase Attributes)
- **Job Name:** `$.Job3Name`
- **Arguments:** `$.Job3BArguments`
  - `--DATABASE`: `omc_flywheel_dev_clean`
  - `--S3_ROOT`: `s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_part/infobase_attributes/`
  - `--TABLE_PREFIX`: `part_`
  - `--MAX_COLS`: `100`

### Step 3: Prepare Part Tables
- **Job Name:** `$.Job4Name`
- **Arguments:** None (uses job defaults)

### Step 4: Create ER Table
- **Job Name:** `$.Job5Name`
- **Arguments:** None (uses job defaults)

### Step 5: Data Monitor Report
- **Job Name:** `$.Job6Name`
- **Arguments:** None (uses job defaults)

### Step 5: Cleanrooms Report
- **Job Name:** `$.Job7Name`
- **Arguments:** None (uses job defaults)

## Modifying Parameters

### To Change Parameters

1. **Edit Terraform Stack:**
   ```hcl
   # infra/stacks/dev-orchestration/main.tf
   job_arguments = {
     job1 = {
       "--SNAPSHOT_DT" = "2025-01-15"  # Specific date instead of _NONE_
     }
     # ... other jobs
   }
   ```

2. **Apply Changes:**
   ```bash
   cd infra/stacks/dev-orchestration
   terraform plan
   terraform apply
   ```

3. **For Manual Execution:**
   - Modify the input JSON when starting execution
   - Or use the manual execution command from outputs

### To Override for One Execution

When manually starting an execution, you can override parameters:

```bash
aws stepfunctions start-execution \
  --state-machine-arn <ARN> \
  --input '{
    "Environment": "dev",
    "Job1Name": "etl-omc-flywheel-dev-addressable-split-and-part",
    "Job1Arguments": {
      "--SNAPSHOT_DT": "2025-01-15"  # Override here
    },
    # ... rest of input
  }'
```

## Quick Reference

**View in Console:**
```
https://console.aws.amazon.com/states/home?region=us-east-1#/statemachines/view/arn:aws:states:us-east-1:417649522250:stateMachine:omc-flywheel-dev-db-refresh
```

**Get ARN:**
```bash
cd infra/stacks/dev-orchestration
terraform output step_functions_state_machine_arn
```

**View Definition:**
```bash
aws stepfunctions describe-state-machine \
  --state-machine-arn $(terraform output -raw step_functions_state_machine_arn) \
  --query 'definition' \
  --output json | python3 -m json.tool
```

---

**Last Updated:** 2025-01-XX

