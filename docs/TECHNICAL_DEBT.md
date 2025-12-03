# Technical Debt & Future Improvements

This document tracks known technical debt and improvements needed in the codebase.

## Script Hardcoding Issues

### Account ID Hardcoding in Production Scripts

**Status:** ⚠️ **Pending**

**Issue:**
Production ETL scripts have hardcoded AWS account IDs in the Glue assets bucket paths:
- `scripts/etl-omc-flywheel-prod-addressable-split-and-part.py` - Line 140
- `scripts/etl-omc-flywheel-prod-infobase-split-and-part.py` - Line 192
- `scripts/etl-omc-flywheel-prod-addressable-bucket.py` - Line 168
- `scripts/etl-omc-flywheel-prod-infobase-split-and-bucket.py` - Line 209

**Current State:**
- Hardcoded: `aws-glue-assets-239083076653-us-east-1` (prod account ID)

**Solution:**
Update to use dynamic account ID lookup (already implemented in dev):
```python
# Get account ID dynamically
sts_client = boto3.client('sts')
account_id = sts_client.get_caller_identity()['Account']
region = boto3.Session().region_name or 'us-east-1'
glue_bucket = f"aws-glue-assets-{account_id}-{region}"
```

**Benefits:**
- Environment-agnostic scripts
- Easier to promote code between environments
- No manual account ID updates needed

**Dev Status:**
✅ **Completed** - All dev scripts updated to use dynamic account ID lookup

**Action Required:**
1. Update prod scripts to use dynamic account ID
2. Test in dev first (already done)
3. Upload updated scripts to prod S3
4. Verify prod jobs work correctly

**Priority:** Medium (works currently, but limits portability)

---

## Terraform Limitations

### Cleanrooms Table Associations

**Status:** ⚠️ **Workaround in Place**

**Issue:**
Terraform AWS provider does not support `aws_cleanrooms_configured_table_association` resource type.

**Current Workaround:**
- Python scripts (`manage-collaboration-invites.py`, `manage-multiple-collaborations.py`) handle associations
- Terraform creates configured tables, but associations are managed separately

**Future:**
- Monitor Terraform provider updates for Cleanrooms support
- Consider CloudFormation if support becomes available

---

## Environment Configuration

### Deprecated Terraform Attributes

**Status:** ⚠️ **Low Priority**

**Issue:**
Terraform configuration uses deprecated `data.aws_region.current.name` attribute.

**Impact:**
- Warning messages during Terraform operations
- No functional impact currently

**Action:**
- Update to use `data.aws_region.current.id` when convenient
- Low priority - warnings only

---

## Script Maintenance

### Shared Scripts vs Environment-Specific

**Status:** ✅ **Current Approach Working**

**Note:**
Some scripts are shared (no environment in name):
- `create-part-addressable-ids-er-table.py`
- `create-all-part-tables-er.py`
- `generate-cleanrooms-report.py`
- `data_monitor.py`

These use environment variables (`ENV`, `AWS_REGION`) for configuration, which is the correct approach.

---

*Last Updated: 2025-01-XX*
*Maintained by: Data Engineering Team*

