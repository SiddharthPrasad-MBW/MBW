# Dev Orchestration Stack - Step Functions Input JSON

## Where the Input JSON is Defined

When executing the Step Functions state machine from the UI, you need to provide input JSON. Here's where it comes from:

### 1. EventBridge Target (if scheduled)

**Location:** `infra/modules/orchestration/main.tf` (lines 449-463)

When EventBridge triggers the execution automatically (if scheduled), it uses this input:

```hcl
input = jsonencode({
  Environment = var.environment
  Job1Name    = var.job_names.job1
  Job2Name    = var.job_names.job2
  Job3Name    = var.job_names.job3
  Job4Name    = var.job_names.job4
  Job5Name    = var.job_names.job5
  Job6Name    = var.job_names.job6
  Job7Name    = var.job_names.job7
  Job1Arguments = var.job_arguments.job1
  Job2Arguments = var.job_arguments.job2
  Job3AArguments = var.job_arguments.job3a
  Job3BArguments = var.job_arguments.job3b
  SNSTopicArn = aws_sns_topic.orchestration_notifications.arn
})
```

This is automatically generated from the stack configuration variables.

### 2. Stack Configuration (Source of Truth)

**Location:** `infra/stacks/dev-orchestration/main.tf` (lines 11-40)

This is where the actual values are defined:

```hcl
job_names = {
  job1 = "etl-omc-flywheel-dev-addressable-split-and-part"
  job2 = "etl-omc-flywheel-dev-infobase-split-and-part"
  job3 = "etl-omc-flywheel-dev-register-part-tables"
  job4 = "etl-omc-flywheel-dev-prepare-part-tables"
  job5 = "etl-omc-flywheel-dev-create-part-addressable-ids-er-table"
  job6 = "etl-omc-flywheel-dev-generate-data-monitor-report"
  job7 = "etl-omc-flywheel-dev-generate-cleanrooms-report"
}

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

**Mapping:**
- `job_names` → `Job1Name`, `Job2Name`, etc. in input JSON
- `job_arguments` → `Job1Arguments`, `Job2Arguments`, `Job3AArguments`, `Job3BArguments` in input JSON

### 3. Ready-to-Use JSON File

**Location:** `infra/stacks/dev-orchestration/execution-input.json`

This file contains the complete, ready-to-use input JSON that you can copy/paste directly into the Step Functions UI.

**Contents:**
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

## How to Use in the UI

### Step-by-Step:

1. **Open Step Functions Console**
   - Navigate to: https://console.aws.amazon.com/states/home?region=us-east-1
   - Or search for "Step Functions" in AWS Console

2. **Select Your State Machine**
   - Find: `omc-flywheel-dev-db-refresh`
   - Click on it

3. **Start Execution**
   - Click the **"Start execution"** button

4. **Provide Input**
   - In the **"Input"** field, paste the JSON from `execution-input.json`
   - Or use the Terraform output command (see below)

5. **Execute**
   - Click **"Start execution"**

### Alternative: Get Input from Terraform Output

```bash
cd infra/stacks/dev-orchestration

# Get the full command (includes the JSON)
terraform output manual_execution_command

# Or extract just the JSON part
terraform output -json | jq -r '.manual_execution_command.value' | grep -o '{.*}' | python3 -m json.tool
```

## How It All Connects

```
┌─────────────────────────────────────┐
│ Stack Configuration                 │
│ (dev-orchestration/main.tf)         │
│ - job_names                         │
│ - job_arguments                      │
└──────────────┬──────────────────────┘
               │
               ├──────────────────────┐
               │                      │
               ▼                      ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│ EventBridge Target        │  │ execution-input.json      │
│ (orchestration/main.tf)   │  │ (ready-to-use file)       │
│ - Auto-generates input    │  │ - Copy/paste for UI       │
│ - Used when scheduled     │  │ - Used for manual runs    │
└──────────────────────────┘  └──────────────────────────┘
               │                      │
               └──────────┬───────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ Step Functions        │
              │ State Machine         │
              │ (receives input JSON) │
              └───────────────────────┘
```

## Modifying the Input

### To Change Parameters:

1. **Edit Stack Configuration:**
   ```hcl
   # infra/stacks/dev-orchestration/main.tf
   job_arguments = {
     job1 = {
       "--SNAPSHOT_DT" = "2025-01-15"  # Change from _NONE_ to specific date
     }
   }
   ```

2. **Regenerate execution-input.json:**
   ```bash
   # After terraform apply, the file should be updated
   # Or manually update execution-input.json to match
   ```

3. **Apply Terraform:**
   ```bash
   terraform apply
   ```

### To Override for One Execution:

When starting execution in the UI, you can modify the JSON before pasting:

```json
{
  "Job1Arguments": {
    "--SNAPSHOT_DT": "2025-01-15"  // Override here
  },
  // ... rest of input
}
```

## Quick Reference

**Get State Machine ARN:**
```bash
terraform output step_functions_state_machine_arn
```

**Get SNS Topic ARN:**
```bash
terraform output sns_topic_arn
```

**View Current Input JSON:**
```bash
cat execution-input.json | python3 -m json.tool
```

**Console URL:**
```
https://console.aws.amazon.com/states/home?region=us-east-1#/statemachines/view/arn:aws:states:us-east-1:417649522250:stateMachine:omc-flywheel-dev-db-refresh
```

---

**Note:** The input JSON is built from the Terraform variables in your stack configuration. Always update the stack configuration first, then regenerate the execution-input.json file if needed.

