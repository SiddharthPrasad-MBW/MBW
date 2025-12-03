# Terraform Variable Strategy

## Overview

This document outlines the variable-driven approach for Terraform modules and stacks to support multiple environments (dev, prod) while maintaining environment-specific stacks.

## Architecture

### Modules (Reusable)
- **Location**: `infra/modules/`
- **Purpose**: Environment-agnostic, reusable components
- **Variables**: Accept environment-specific values via variables
- **Tags**: Use `var.environment` (automatically capitalized for display)

### Stacks (Environment-Specific)
- **Location**: `infra/stacks/`
- **Purpose**: Environment-specific configurations that use modules
- **Naming**: `{env}-{component}` (e.g., `prod-gluejobs`, `prod-monitoring`)
- **Variables**: Pass environment-specific values to modules

## Variable-Driven Principles

### 1. Modules Should Be Environment-Agnostic

**✅ Good:**
```hcl
locals {
  environment_display = title(var.environment)  # "prod" -> "Production"
  
  common_tags = merge(
    {
      Environment = local.environment_display
      Project     = "OMC Flywheel Cleanroom"
    },
    var.additional_tags
  )
}
```

**❌ Bad:**
```hcl
locals {
  common_tags = {
    Environment = "Production"  # Hardcoded!
  }
}
```

### 2. Stacks Pass Environment Values

**✅ Good:**
```hcl
module "glue_jobs" {
  source = "../../modules/gluejobs"
  
  environment  = "prod"  # Explicitly set
  aws_region   = "us-east-1"
  project_name = "omc-flywheel"
}
```

### 3. Use `additional_tags` for Custom Tags

Modules accept an `additional_tags` variable for environment-specific or custom tags:

```hcl
module "glue_jobs" {
  # ... other variables ...
  
  additional_tags = {
    CostCenter = "DataEngineering"
    Team       = "OMC"
    ManagedBy  = "Terraform"
  }
}
```

## Current Module Structure

### `modules/gluejobs`
- **Variables**: `environment`, `project_name`, `additional_tags`
- **Tags**: Uses `var.environment` (capitalized) + `var.additional_tags`
- **Usage**: Used by `stacks/prod-gluejobs`

### `modules/monitoring`
- **Variables**: `environment`, `project_name`, `additional_tags`
- **Tags**: Uses `var.environment` (capitalized) + `var.additional_tags`
- **Usage**: Used by `stacks/prod-monitoring`

### `modules/crconfigtables`
- **Variables**: `tags` (already variable-driven)
- **Usage**: Used by `stacks/prod-crconfigtables` and `stacks/dev-crconfigtables`
- **Status**: ✅ Variable-driven (stacks pass environment-specific tags)

## Creating New Environments

To create a new environment (e.g., `dev`):

1. **Create a new stack** in `infra/stacks/`:
   ```bash
   infra/stacks/dev-gluejobs/
   infra/stacks/dev-monitoring/
   ```

2. **Set environment-specific variables**:
   ```hcl
   module "glue_jobs" {
     source = "../../modules/gluejobs"
     
     environment  = "dev"  # Different from prod
     aws_region   = "us-east-1"
     project_name = "omc-flywheel"
     
     # Environment-specific resource names
     glue_database_name = "omc_flywheel_dev"
     data_bucket_name   = "omc-flywheel-data-us-east-1-dev"
   }
   ```

3. **Modules automatically adapt**:
   - Tags will show `Environment = "Development"` (capitalized)
   - Resource names use `var.environment` if used in naming

## Benefits

1. **Reusability**: Modules work for any environment
2. **Consistency**: Same module code across environments
3. **Maintainability**: Changes to modules benefit all environments
4. **Flexibility**: Stacks can override defaults per environment
5. **Clarity**: Environment-specific values are explicit in stacks

## Migration Path

### Completed ✅
- [x] `modules/gluejobs`: Uses `var.environment` in tags
- [x] `modules/monitoring`: Uses `var.environment` in tags
- [x] Both modules accept `additional_tags` variable

### Future Work 🔄
- [x] Create `stacks/dev-gluejobs` and `stacks/dev-monitoring` ✅
- [x] Create `stacks/dev-crconfigtables` ✅
- [x] `modules/crconfigtables` already variable-driven (uses `var.tags`) ✅
- [x] Document environment-specific variable defaults in stack READMEs ✅

## Example: Dev Environment (Already Created ✅)

Dev stacks have been created at:
- `infra/stacks/dev-gluejobs/`
- `infra/stacks/dev-monitoring/`
- `infra/stacks/dev-crconfigtables/`

### Dev Configuration

```hcl
# infra/stacks/dev-gluejobs/main.tf
module "glue_jobs" {
  source = "../../modules/gluejobs"
  
  environment  = "dev"  # Automatically tags as "Development"
  project_name = "omc-flywheel"
  
  # Dev-specific resources
  glue_database_name = "omc_flywheel_dev"
  data_bucket_name   = "omc-flywheel-data-us-east-1-dev"
  
  # Dev-specific configuration
  worker_count    = 5      # Lower than prod (10)
  timeout_minutes = 30     # Shorter than prod (60)
  max_retries     = 2      # More than prod (1) for testing
}
```

The module automatically:
- Tags resources with `Environment = "Development"`
- Uses dev-specific resource names
- Applies dev-specific configuration

### Dev vs Prod Comparison

| Setting | Dev | Prod |
|---------|-----|------|
| Worker Count | 5 | 10 |
| Timeout (min) | 30 | 60 |
| Max Retries | 2 | 1 |
| Monitoring Schedule | 12 hours | 24 hours |
| Log Retention | 7 days | 30 days |

