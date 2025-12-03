# Collaboration Association Process Cleanup

**Date:** November 21, 2025  
**Status:** Cleanup Plan

## Summary

After successfully fixing association names and creating collaboration analysis rules, we've identified areas to clean up and improve the collaboration association process.

## Current State

### ✅ What's Working

1. **`fix-collaboration-associations.py`** - One-time fix script
   - ✅ Dynamic discovery of `part_*` tables
   - ✅ Excludes `n_a` tables automatically
   - ✅ Two-phase approach (delete all, create all)
   - ✅ Uses correct role: `cleanrooms-glue-s3-access`
   - ✅ Fully idempotent

2. **`add-collaboration-analysis-rules.py`** - Creates collaboration rules
   - ✅ Works correctly
   - ✅ Handles result receivers

3. **`manage-collaboration-invites.py`** - Main collaboration management script
   - ✅ Default role is correct: `cleanrooms-glue-s3-access`
   - ✅ Has code to create collaboration analysis rules
   - ⚠️ Needs improvements (see below)

## Issues to Fix

### 1. `manage-collaboration-invites.py` - Table Discovery

**Current:** `get_configured_tables()` returns ALL configured tables

**Problem:** Should only return `part_*` tables (excluding `n_a` tables) to match the standard workflow

**Fix:**
```python
def get_configured_tables(self) -> List[Dict]:
    """Get all existing configured tables starting with 'part_' (excluding n_a tables)."""
    EXCLUDED_TABLES = ['part_n_a', 'part_n_a_a']
    
    tables = []
    paginator = self.cleanrooms.get_paginator('list_configured_tables')
    for page in paginator.paginate():
        for table in page.get('configuredTableSummaries', []):
            table_name = table.get('name', '')
            # Filter: must start with "part_" and not be excluded
            if (table_name.startswith('part_') and 
                table_name not in EXCLUDED_TABLES):
                tables.append({
                    'id': table.get('configuredTableId'),
                    'arn': table.get('configuredTableArn'),
                    'name': table_name,
                    'analysisMethod': table.get('analysisMethod')
                })
    
    # Sort alphabetically
    tables.sort(key=lambda x: x['name'])
    return tables
```

### 2. `manage-collaboration-invites.py` - Collaboration Analysis Rules

**Current:** Uses default result receivers `["657425294073", "803109464991"]` which may not exist in all collaborations

**Problem:** For test collaborations (like ACXDevToProd_Test_Collab), these accounts don't exist, causing rules to fail

**Fix:** Use the other member account in the collaboration (not the data provider account):
```python
# Get collaboration members to determine result receivers
membership = cleanrooms.get_membership(membershipIdentifier=membership_id)
collaboration_id = membership['membership']['collaborationId']
members = cleanrooms.list_members(collaborationIdentifier=collaboration_id)
all_account_ids = [m['accountId'] for m in members.get('memberSummaries', [])]

# Use the other member account (not our account)
our_account_id = sts.get_caller_identity()['Account']
result_receivers = [aid for aid in all_account_ids if aid != our_account_id]

if not result_receivers:
    # Fallback: use all members (shouldn't happen)
    result_receivers = all_account_ids
```

### 3. `manage-collaboration-invites.py` - Two-Phase Approach

**Current:** Creates associations one-by-one, checking if they exist first

**Problem:** If associations have wrong names, they won't be fixed automatically

**Option A:** Add a `--fix-names` flag that uses two-phase approach
**Option B:** Make two-phase the default for new collaborations
**Option C:** Keep current approach but add verification step

**Recommendation:** Option A - Add `--fix-names` flag for when you need to fix existing associations

### 4. Quota Management

**Current:** No explicit quota checking

**Problem:** Script might try to create more than 25 associations

**Fix:** Add quota check and limit:
```python
MAX_ASSOCIATIONS = 25  # AWS quota limit

tables = self.get_configured_tables()
if len(tables) > MAX_ASSOCIATIONS:
    print(f"⚠️  Found {len(tables)} tables, limiting to {MAX_ASSOCIATIONS} (quota)")
    tables = tables[:MAX_ASSOCIATIONS]
```

## Recommended Cleanup Actions

### Priority 1: Critical Fixes

1. **Update `get_configured_tables()` to filter `part_*` tables**
   - Ensures only standard tables are associated
   - Excludes `n_a` tables automatically

2. **Fix collaboration analysis rules result receivers**
   - Use other member account instead of hardcoded defaults
   - Works for all collaboration types

### Priority 2: Improvements

3. **Add quota checking**
   - Prevents errors when > 25 tables exist
   - Provides clear warning

4. **Add `--fix-names` flag**
   - Allows fixing existing associations with wrong names
   - Uses two-phase approach when needed

### Priority 3: Documentation

5. **Update `COLLABORATION_PROCESS_FLOW.md`**
   - Document the correct workflow
   - Include two-phase approach option
   - Document quota limits

6. **Update `COLLABORATION_MANAGEMENT.md`**
   - Update examples with correct role name
   - Add troubleshooting for direct analysis status
   - Document collaboration analysis rules requirement

## Clean Workflow (After Cleanup)

### For New Collaborations

```bash
# 1. Accept invitation
python3 scripts/manage-collaboration-invites.py accept \
    --collaboration-id <id> \
    --auto-associate \
    --profile flywheel-prod

# This will:
# - Accept invitation
# - Discover all part_* tables (excluding n_a)
# - Create associations with correct names (acx_<table_name>)
# - Create collaboration analysis rules automatically
# - Limit to 25 associations (quota)
```

### For Fixing Existing Associations

```bash
# Use the fix script (one-time)
python3 scripts/fix-collaboration-associations.py \
    --membership-id <id> \
    --profile flywheel-prod

# Or use manage script with fix flag (after cleanup)
python3 scripts/manage-collaboration-invites.py associate \
    --membership-id <id> \
    --fix-names \
    --profile flywheel-prod
```

## Script Roles

### `manage-collaboration-invites.py`
- **Purpose:** Main script for managing collaborations
- **Use for:** Accepting invites, associating resources to NEW collaborations
- **Status:** Needs cleanup (filter tables, fix result receivers)

### `fix-collaboration-associations.py`
- **Purpose:** One-time fix for existing associations
- **Use for:** Fixing wrong association names in existing collaborations
- **Status:** ✅ Complete and working

### `add-collaboration-analysis-rules.py`
- **Purpose:** Create collaboration analysis rules
- **Use for:** Adding rules to associations (usually auto-done by manage script)
- **Status:** ✅ Working, but result receivers need improvement

## Testing Checklist

After cleanup, verify:

- [ ] `get_configured_tables()` only returns `part_*` tables
- [ ] `n_a` tables are excluded
- [ ] Quota limit (25) is enforced
- [ ] Collaboration analysis rules use correct result receivers
- [ ] Direct analysis status becomes "READY" after rules are created
- [ ] Script is idempotent (can run multiple times safely)

## Next Steps

1. Update `manage-collaboration-invites.py` with Priority 1 fixes
2. Test with a new collaboration
3. Update documentation
4. Mark `fix-collaboration-associations.py` as "one-time fix only"

---

**Last Updated:** November 21, 2025

