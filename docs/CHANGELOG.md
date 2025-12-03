# Changelog

All notable changes to the ACX OMC Flywheel P0 infrastructure project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.0] - 2025-01-XX

### Added
- **Entity Resolution Service Integration**
  - Created Terraform module and stack for Cleanrooms Identity Resolution Service (CR Namespace)
  - Added scripts for discovering and managing Entity Resolution resources
  - Created `scripts/discover-cr-namespace-resources.py` for resource discovery
  - Created `scripts/create-cr-namespace-resources.py` for resource management
  - Documented existing Entity Resolution Service resources in production

- **Entity Resolution Table Creation**
  - Created `scripts/create-all-part-tables-er.py` to generate `_er` tables for all part_* tables
  - Created `scripts/create-part-addressable-ids-er-table.py` for addressable_ids ER table
  - Added Glue jobs: `etl-omc-flywheel-prod-create-all-part-tables-er` and `etl-omc-flywheel-prod-create-part-addressable-ids-er-table`
  - ER tables map `customer_user_id` to `row_id` for Entity Resolution Service

- **Schema Mapping Generation**
  - Created `scripts/generate-entity-resolution-schema-mappings.py` to automatically generate schema mapping JSON files
  - Supports all part_*_er tables with automatic column discovery
  - Excludes `id_bucket` and `miacs_11_054` columns as configured
  - Generates JSON files ready for `aws entityresolution create-schema-mapping`

- **Verification and Management Scripts**
  - Created `scripts/verify-collaboration-table-config.py` to verify all tables have consistent configuration
  - Created `scripts/update-configured-table-analysis-providers.py` to update analysis providers across all tables
  - Created `scripts/fix-miacs-01-a-association-name.py` to fix association naming
  - Created `scripts/fix-miacs-02-a-columns.py` to fix configured table columns

### Changed
- **Analysis Provider Configuration**
  - Updated all 27 configured tables to include both analysis providers:
    - `921290734397` (AMC Service)
    - `657425294073` (Query Submitter/AMC Results Receiver)
  - Updated Terraform defaults to include both providers in `allowed_query_providers`
  - All tables now consistently allow queries from both accounts

- **Association Naming Fix**
  - Fixed `part_miacs_01_a` association name from `part_miacs_01_a` to `acx_part_miacs_01_a`
  - All 25 collaboration associations now follow `acx_` prefix convention

- **Configured Table Columns**
  - Fixed `part_miacs_02_a` configured table to exclude `miacs_11_054` and include `id_bucket`
  - Table now has 100 columns (99 regular + 1 partition key) instead of 101
  - Prevents column truncation in Cleanrooms configured tables

### Fixed
- **Privacy Budget Template Handling**
  - Updated scripts to handle privacy budget templates that block association deletion
  - Scripts now automatically delete privacy budget templates before deleting associations

- **Column Count Management**
  - Resolved issue where tables with 101 columns (100 regular + 1 partition key) were truncating partition keys
  - Solution: Exclude specific columns (e.g., `miacs_11_054`) to stay within 100-column limit

## [2.2.2] - 2025-11-12

### Changed
- **Cleanrooms Collaboration Association Naming**
  - Updated association naming convention from `part_*-assoc` to `acx_part_*`
  - All 25 collaboration associations migrated to new naming convention
  - New naming provides clear Acxiom (ACX) prefix for better identification
  - Removed `-assoc` suffix for cleaner naming

### Added
- **Migration Script for Association Naming**
  - Created `scripts/refresh-collaboration-associations.py` for migrating existing associations
  - Script is fully idempotent and safe to run multiple times
  - Supports dry-run mode for previewing changes
  - Handles collaboration analysis rule recreation during migration

### Fixed
- **Direct Analysis Configuration**
  - Fixed `acx_part_new_borrowers` direct analysis readiness
  - Updated configured table analysis rules to include `allowedAnalysisProviders` account ID
  - Ensures all tables are properly configured for direct analysis queries

## [2.2.1] - 2025-11-06

### Fixed
- **Cleanrooms Scripts - Duplicate Prevention**
  - Added duplicate detection for configured tables before creation
  - Added duplicate detection for table associations before creation
  - Added duplicate detection for collaboration analysis rules before creation
  - Scripts now check for existing resources using pagination to handle large numbers of tables
  - `create-cleanrooms-configured-tables.py` is now idempotent and safe to run multiple times
  - `add-collaboration-analysis-rules.py` now skips existing rules instead of failing

### Improved
- **Cleanrooms Scripts - Idempotency**
  - All Cleanrooms management scripts are now fully idempotent
  - Scripts check for existing resources before attempting creation
  - Prevents accidental duplicate resource creation
  - Improved error handling with clear messages when resources already exist

## [2.2.0] - 2025-11-06

### Added
- **Variable-Driven Terraform Modules**
  - Made all modules environment-agnostic using `var.environment` for tags
  - Added `additional_tags` variable to all modules for custom tagging
  - Modules now automatically capitalize environment names (prod → Production, dev → Development)
  - Created `TERRAFORM_VARIABLE_STRATEGY.md` documenting the approach

- **Development Environment Stacks**
  - Created `infra/stacks/dev-gluejobs/` for dev Glue jobs
  - Created `infra/stacks/dev-monitoring/` for dev monitoring
  - Created `infra/stacks/dev-crconfigtables/` for dev Cleanrooms configured tables
  - All dev stacks use dev-specific resource names and configurations

- **AWS Cleanrooms Integration**
  - Created `scripts/create-cleanrooms-configured-tables.py` for managing Cleanrooms configured tables
  - Created `scripts/add-collaboration-analysis-rules.py` for adding collaboration analysis rules
  - Supports creating configured tables, analysis rules, and table associations
  - Handles IAM role creation with policy version management
  - Supports all 28 `part_` tables for Cleanrooms analysis

- **Dev-Specific Configurations**
  - Lower worker counts (5 vs 10 for prod)
  - Shorter timeouts (30 min vs 60 min for prod)
  - More retries for testing (2 vs 1 for prod)
  - More frequent monitoring (12 hours vs 24 hours for prod)
  - Shorter log retention (7 days vs 30 days for prod)

### Changed
- **Terraform Modules**
  - `modules/gluejobs`: Now uses `var.environment` in tags instead of hardcoded "Production"
  - `modules/monitoring`: Now uses `var.environment` in tags instead of hardcoded "Production"
  - `modules/crconfigtables`: Already variable-driven via `var.tags` (documented)

- **Production Stacks**
  - Updated to pass `environment = "prod"` to modules
  - Added comments explaining variable-driven approach
  - Maintained backward compatibility with existing resources

### Fixed
- **Cleanrooms Collaboration Analysis Rules**
  - Fixed API parameter structure for `create_configured_table_association_analysis_rule`
  - Corrected `allowedResultReceivers` to use 12-digit account IDs (not membership IDs)
  - Removed unsupported `allowedAdditionalAnalyses` parameter when not needed
  - Successfully created analysis rules for all 25 table associations

## [2.1.0] - 2025-10-31

### Added
- **Dynamic Partition Overwrite for Split-and-Part Jobs**
  - Added `spark.sql.sources.partitionOverwriteMode` = "dynamic" to split-and-part jobs
  - Enables incremental partition updates - only replaces partitions being written
  - Added parallel partition discovery configuration for faster processing
  - Applied to `etl-omc-flywheel-prod-infobase-split-and-part` and `etl-omc-flywheel-prod-addressable-split-and-part`

- **Enhanced Data Monitor**
  - Comprehensive partition detection with debug logging
  - Improved error handling with detailed diagnostics
  - Better partition count validation and reporting

### Changed
- **Split-and-Part Job Scripts**
  - Added dynamic partition overwrite configuration after `id_bucket` column creation
  - Configured parallel partition discovery for improved performance
  - Scripts now stored in repository: `etl-omc-flywheel-prod-infobase-split-and-part.py` and `etl-omc-flywheel-prod-addressable-split-and-part.py`

- **Prepare Part Tables Job**
  - Migrated from Python Shell to Spark job for better performance
  - Uses Glue API for table creation/updates instead of Spark SQL DDL
  - Supports fallback partition discovery via S3 listing if Athena MSCK fails
  - Added support for stripping partition projection properties

- **Data Monitor Script**
  - Enhanced partition detection with detailed debug logging
  - Improved error messages and diagnostics
  - Better handling of partition value extraction from Glue API

### Fixed
- **Data Monitor Partition Detection**
  - Removed unsupported `ProjectionExpression` parameter from Glue `get_partitions` API call
  - Fixed `ParamValidationError` that was preventing partition discovery
  - All 256 partitions now correctly detected and validated

- **Prepare Part Tables Script**
  - Fixed Spark SQL limitations by using Glue API for DDL operations
  - Resolved table recreation issues with proper Glue API calls
  - Improved partition registration with fallback mechanisms

## [2.0.0] - 2025-01-15

### Added
- **Dual Pipeline Architecture**
  - **Pipeline 1: Bucketed Tables** - Original Cleanroom-optimized solution
  - **Pipeline 2: Partitioned Tables** - New time-series optimized solution
  - Both pipelines run in parallel for different use cases

- **New Glue Jobs (4)**
  - `etl-omc-flywheel-prod-infobase-split-and-part` - Creates partitioned infobase data
  - `etl-omc-flywheel-prod-addressable-split-and-part` - Creates partitioned addressable data
  - `etl-omc-flywheel-prod-register-part-tables` - Registers external part tables
  - `etl-omc-flywheel-prod-prepare-part-tables` - Runs MSCK REPAIR on partitioned tables

- **Partitioned Data Processing**
  - Time-series optimized data layout in `split_part/` directory
  - Automatic partition discovery with MSCK REPAIR
  - Optimized for date-range queries and analytics

- **Enhanced Script Management**
  - All scripts renamed to match Glue job naming convention (`etl-omc-flywheel-prod-*`)
  - Optional argument handling for improved flexibility
  - Concurrent MSCK REPAIR execution with configurable limits

### Changed
- **Terraform Configuration**
  - Updated to manage both bucketed and partitioned pipelines
  - Corrected data paths: `split_cluster/` for bucketed, `split_part/` for partitioned
  - Updated CSV file references to use `split_part.csv` instead of `split_lowercase.csv`
  - Standardized Glue job configurations and removed deprecated `execution_class`

- **Documentation Updates**
  - Updated README.md to reflect dual pipeline architecture
  - Enhanced PRODUCTION_RUN_SEQUENCE.md with both pipeline workflows
  - Added partitioned table features to key features section

### Fixed
- **Script Argument Handling**
  - Made `TABLES_CSV`, `MAX_CONCURRENCY`, and `POLL_INTERVAL_SEC` truly optional
  - Improved error handling for missing optional parameters

- **Terraform State Synchronization**
  - Imported all existing Glue jobs into Terraform state
  - Aligned Terraform configuration with actual production resources
  - Eliminated configuration drift between desired and actual state

## [1.0.0] - 2025-10-17

### Added
- **Initial Infrastructure as Code Setup**
  - Complete reverse engineering of production environment
  - All 13 AWS resources imported into Terraform state
  - Comprehensive documentation and operational guides

- **Glue Jobs (3)**
  - `etl-omc-flywheel-prod-addressable-ids-compaction`
  - `etl-omc-flywheel-prod-infobase-attributes-compaction`
  - `etl-omc-flywheel-prod-infobase-cleanroom-from-csv`

- **Glue Crawlers (4)**
  - `crw-omc-flywheel-prod-addressable_ids-compaction-cr`
  - `crw-omc-flywheel-prod-infobase_attributes-compaction-cr`
  - `crw-omc-flywheel-prod-raw-input-addressable`
  - `crw-omc-flywheel-prod-raw-input-infobase`

- **Glue Databases (2)**
  - `omc_flywheel_prod` - Main production data catalog
  - `default` - Default Glue database

- **IAM Role (1)**
  - `omc_flywheel-prod-glue-role` - Service role for Glue operations

- **S3 Buckets (3)**
  - `omc-flywheel-data-us-east-1-prod` - Main data storage
  - `aws-glue-assets-239083076653-us-east-1` - Glue scripts and assets
  - `omc-flywheel-prod-analysis-data` - Analysis and temporary data

- **Documentation**
  - `README.md` - Project overview and quick start guide
  - `INFRASTRUCTURE_OVERVIEW.md` - Detailed architecture and configuration
  - `OPERATIONS_GUIDE.md` - Daily operations and maintenance procedures
  - `DEPLOYMENT_GUIDE.md` - Deployment procedures and CI/CD integration
  - `TROUBLESHOOTING.md` - Common issues and emergency procedures
  - `REVERSE_ENGINEERING_GUIDE.md` - Complete reverse engineering process

- **Scripts**
  - `audit_prod_resources.py` - AWS resource discovery
  - `create_imports_from_discovered.py` - Terraform import generation
  - `real_aws_audit.py` - Live AWS environment auditing
  - `setup_p0_project.sh` - Project structure setup

### Changed
- **Resource Configuration**
  - Standardized worker types to G.1X for cost optimization
  - Reduced job timeouts from 48 hours to 10 hours
  - Updated retry configuration to 2 attempts
  - Standardized tagging across all resources

- **Performance Optimizations**
  - Downgraded worker types from G.4X to G.1X
  - Reduced timeout values for cost efficiency
  - Optimized Spark configurations
  - Updated S3 paths for better organization

### Fixed
- **Partitioning Issues**
  - Resolved `ALL_PARTITION_COLUMNS_NOT_ALLOWED` error in addressable IDs compaction job
  - Removed explicit partitioning logic as requested
  - Simplified repartitioning to use default coalesce

- **Import Issues**
  - Fixed duplicate resource configuration errors
  - Corrected Glue database import format (catalog-id:database-name)
  - Updated crawler names to match actual AWS resources
  - Resolved S3 bucket import conflicts

### Security
- **IAM Permissions**
  - Implemented least privilege access for Glue service role
  - Configured appropriate S3 bucket policies
  - Set up CloudWatch logging for all operations

- **Resource Tagging**
  - Applied consistent tagging strategy across all resources
  - Added security and compliance tags
  - Implemented cost allocation tags

### Infrastructure
- **State Management**
  - Initial setup with local state (S3 backend recommended for production)
  - All resources successfully imported and managed
  - No destructive changes planned

- **Monitoring**
  - CloudWatch metrics configuration
  - Log aggregation setup
  - Alert configuration recommendations

## [0.1.0] - 2025-10-17 (Pre-Release)

### Added
- **Project Structure**
  - Created `acx_omc_flywheel_p0` directory structure
  - Set up Terraform environment directories
  - Created documentation framework

- **Discovery Process**
  - Initial AWS resource discovery
  - Manual resource identification
  - Import script generation

### Changed
- **Development Process**
  - Moved from manual infrastructure management to Infrastructure as Code
  - Established version control for infrastructure
  - Created standardized deployment procedures

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2025-10-17 | Initial production-ready release with complete infrastructure |
| 0.1.0 | 2025-10-17 | Pre-release with basic project structure |

## Future Roadmap

### Planned Features
- **Multi-Environment Support**
  - Development environment setup
  - Staging environment configuration
  - Environment-specific variable management

- **Enhanced Monitoring**
  - CloudWatch dashboards
  - Automated alerting
  - Performance metrics collection

- **Security Enhancements**
  - S3 backend for state management
  - DynamoDB state locking
  - Enhanced IAM policies

- **CI/CD Integration**
  - GitHub Actions workflows
  - GitLab CI pipelines
  - Automated testing

### Known Issues
- **State Management**
  - Currently using local state (not recommended for production)
  - Need to implement S3 backend with DynamoDB locking

- **Monitoring**
  - Limited CloudWatch dashboards
  - Need automated alerting setup
  - Performance metrics collection needs enhancement

### Technical Debt
- **Documentation**
  - Need to add more detailed troubleshooting scenarios
  - Performance tuning guide needs expansion
  - Security best practices documentation

- **Code Quality**
  - Terraform modules need to be created for reusability
  - Variable validation needs enhancement
  - Output documentation needs improvement

---

**Maintainer**: Data Engineering Team  
**Last Updated**: October 17, 2025  
**Next Review**: November 17, 2025
