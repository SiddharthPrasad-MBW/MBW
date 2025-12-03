#!/usr/bin/env python3
"""
Create AWS Cleanrooms Configured Tables from Glue Tables

This script creates configured tables, analysis rules, and associations
for Cleanrooms using boto3, since Terraform AWS provider doesn't support
Cleanrooms resources yet.
"""

import boto3
import json
import sys
import argparse
import urllib3
from typing import List, Dict, Optional
from botocore.exceptions import ClientError
from botocore.config import Config

# Default configuration
DEFAULT_REGION = "us-east-1"
DEFAULT_DATABASE = "omc_flywheel_prod"
DEFAULT_BUCKET = "omc-flywheel-data-us-east-1-prod"

# All part_ tables (excluding part_addressable_ids - not added to configured tables)
PART_TABLES = [
    "part_ibe_01", "part_ibe_01_a",
    "part_ibe_02", "part_ibe_02_a",
    "part_ibe_03", "part_ibe_03_a",
    "part_ibe_04", "part_ibe_04_a", "part_ibe_04_b",
    "part_ibe_05", "part_ibe_05_a",
    "part_ibe_06", "part_ibe_06_a",
    "part_ibe_08", "part_ibe_09",
    "part_miacs_01", "part_miacs_01_a",
    "part_miacs_02", "part_miacs_02_a", "part_miacs_02_b",
    "part_miacs_03", "part_miacs_03_a", "part_miacs_03_b",
    "part_miacs_04",
    "part_n_a", "part_n_a_a",
    "part_new_borrowers"
]


def get_glue_table_columns(glue_client, database: str, table: str) -> List[str]:
    """Get all column names from a Glue table."""
    try:
        response = glue_client.get_table(DatabaseName=database, Name=table)
        columns = response['Table']['StorageDescriptor']['Columns']
        return [col['Name'] for col in columns]
    except ClientError as e:
        print(f"❌ Error getting columns for {database}.{table}: {e}")
        raise


def create_iam_role(iam_client, role_name: str, s3_resources: List[str], tags: Dict) -> str:
    """Create IAM role for Cleanrooms to access Glue/S3."""
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "cleanrooms.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }
    
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "GlueRead",
                "Effect": "Allow",
                "Action": [
                    "glue:GetTable",
                    "glue:GetTables",
                    "glue:GetDatabase",
                    "glue:GetDatabases",
                    "glue:GetPartitions",
                    "glue:GetTableVersion",
                    "glue:GetTableVersions"
                ],
                "Resource": "*"
            },
            {
                "Sid": "S3Read",
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:GetObjectVersion",
                    "s3:ListBucket",
                    "s3:GetBucketLocation"
                ],
                "Resource": s3_resources
            }
        ]
    }
    
    try:
        # Check if role exists
        try:
            iam_client.get_role(RoleName=role_name)
            print(f"✅ IAM role {role_name} already exists")
        except iam_client.exceptions.NoSuchEntityException:
            # Create role
            iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(assume_role_policy),
                Tags=[{"Key": k, "Value": v} for k, v in tags.items()]
            )
            print(f"✅ Created IAM role: {role_name}")
        
        # Create or update policy
        policy_name = f"{role_name}-policy"
        # Get account ID from role ARN or STS
        try:
            account_id = iam_client.get_role(RoleName=role_name)['Role']['Arn'].split(':')[4]
        except:
            import boto3
            account_id = boto3.client('sts', region_name=iam_client.meta.region_name).get_caller_identity()['Account']
        
        try:
            # Try to get existing policy
            policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
            iam_client.get_policy(PolicyArn=policy_arn)
            # List existing versions
            versions = iam_client.list_policy_versions(PolicyArn=policy_arn)
            # Delete old versions if we have 5 (max limit)
            if len(versions['Versions']) >= 5:
                # Delete non-default versions (keep default)
                for version in versions['Versions']:
                    if not version['IsDefaultVersion']:
                        iam_client.delete_policy_version(
                            PolicyArn=policy_arn,
                            VersionId=version['VersionId']
                        )
            # Update policy version
            iam_client.create_policy_version(
                PolicyArn=policy_arn,
                PolicyDocument=json.dumps(policy),
                SetAsDefault=True
            )
            print(f"✅ Updated IAM policy: {policy_name}")
        except iam_client.exceptions.NoSuchEntityException:
            # Create new policy
            policy_response = iam_client.create_policy(
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy),
                Tags=[{"Key": k, "Value": v} for k, v in tags.items()]
            )
            policy_arn = policy_response['Policy']['Arn']
            print(f"✅ Created IAM policy: {policy_name}")
        
        # Attach policy to role
        try:
            iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
            print(f"✅ Attached policy to role: {role_name}")
        except ClientError as e:
            if "Duplicate" not in str(e):
                raise
        
        # Get role ARN
        role_response = iam_client.get_role(RoleName=role_name)
        return role_response['Role']['Arn']
        
    except ClientError as e:
        print(f"❌ Error creating IAM role: {e}")
        raise


def get_existing_configured_table(cleanrooms_client, name: str) -> Optional[str]:
    """Check if a configured table already exists and return its ID."""
    try:
        paginator = cleanrooms_client.get_paginator('list_configured_tables')
        for page in paginator.paginate():
            for ct in page.get('configuredTableSummaries', []):
                if ct['name'] == name:
                    return ct['id']
        return None
    except Exception as e:
        print(f"⚠️  Error checking for existing configured table {name}: {e}")
        return None


def create_configured_table(
    cleanrooms_client,
    name: str,
    description: str,
    database: str,
    table: str,
    allowed_columns: List[str],
    tags: Optional[Dict] = None
) -> str:
    """Create a Cleanrooms configured table (only if it doesn't exist)."""
    # Check if table already exists
    existing_id = get_existing_configured_table(cleanrooms_client, name)
    if existing_id:
        print(f"✅ Configured table {name} already exists (ID: {existing_id}), skipping creation")
        return existing_id
    
    try:
        response = cleanrooms_client.create_configured_table(
            name=name,
            description=description,
            tableReference={
                "glue": {
                    "databaseName": database,
                    "tableName": table
                }
            },
            allowedColumns=allowed_columns,
            analysisMethod="DIRECT_QUERY",
            tags=tags or {}
        )
        table_id = response['configuredTable']['id']
        print(f"✅ Created configured table: {name} (ID: {table_id})")
        return table_id
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConflictException':
            # Table was created between check and create, get its ID
            print(f"⚠️  Configured table {name} already exists, getting ID...")
            existing_id = get_existing_configured_table(cleanrooms_client, name)
            if existing_id:
                print(f"✅ Found existing configured table: {name} (ID: {existing_id})")
                return existing_id
            raise Exception(f"Table {name} exists but couldn't find its ID")
        else:
            print(f"❌ Error creating configured table {name}: {e}")
            raise


def create_analysis_rule(
    cleanrooms_client,
    configured_table_id: str,
    rule_type: str,
    allowed_query_providers: Optional[List[str]] = None,
    allowed_functions: Optional[List[str]] = None,
    dimension_columns: Optional[List[str]] = None,
    join_columns: Optional[List[str]] = None
):
    """Create an analysis rule for a configured table."""
    rule_type_upper = rule_type.upper()
    
    # Build analysis rule policy based on type
    if rule_type_upper == "CUSTOM":
        analysis_rule_policy = {
            "v1": {
                "custom": {
                    "allowedAnalyses": ["ANY_QUERY"],
                    "allowedAnalysisProviders": allowed_query_providers or []
                }
            }
        }
    elif rule_type_upper == "AGGREGATION":
        analysis_rule_policy = {
            "v1": {
                "aggregation": {
                    "aggregateColumns": [
                        {
                            "columnNames": dimension_columns or [],
                            "function": "ALLOWED"
                        }
                    ],
                    "dimensionColumns": dimension_columns or [],
                    "joinColumns": [],
                    "outputConstraints": [
                        {
                            "column": dimension_columns[0] if dimension_columns else "",
                            "minimum": 2,
                            "type": "COUNT_DISTINCT"
                        }
                    ],
                    "scalarFunctions": allowed_functions or ["ALL"]
                }
            }
        }
    elif rule_type_upper == "LIST":
        analysis_rule_policy = {
            "v1": {
                "list": {
                    "joinColumns": join_columns or [],
                    "listColumns": dimension_columns or [],
                    "allowedJoinOperators": ["OR"]
                }
            }
        }
    else:
        print(f"⚠️  Unknown rule type: {rule_type_upper}, skipping")
        return
    
    try:
        cleanrooms_client.create_configured_table_analysis_rule(
            configuredTableIdentifier=configured_table_id,
            analysisRuleType=rule_type_upper,
            analysisRulePolicy=analysis_rule_policy
        )
        print(f"✅ Created {rule_type_upper} analysis rule for table {configured_table_id}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConflictException':
            print(f"⚠️  {rule_type_upper} analysis rule already exists for table {configured_table_id}")
        else:
            print(f"❌ Error creating analysis rule: {e}")
            raise


def get_existing_association(cleanrooms_client, membership_id: str, configured_table_id: str) -> Optional[str]:
    """Check if a configured table is already associated with the membership and return association ID."""
    try:
        paginator = cleanrooms_client.get_paginator('list_configured_table_associations')
        for page in paginator.paginate(membershipIdentifier=membership_id):
            for assoc in page.get('configuredTableAssociationSummaries', []):
                if assoc['configuredTableId'] == configured_table_id:
                    return assoc['id']
        return None
    except Exception as e:
        print(f"⚠️  Error checking for existing association: {e}")
        return None


def create_table_association(
    cleanrooms_client,
    membership_id: str,
    configured_table_id: str,
    name: str,
    role_arn: str
) -> str:
    """Create a table association with a membership (only if not already associated)."""
    # Check if table is already associated
    existing_assoc_id = get_existing_association(cleanrooms_client, membership_id, configured_table_id)
    if existing_assoc_id:
        print(f"✅ Configured table {name} is already associated (ID: {existing_assoc_id}), skipping association creation")
        return existing_assoc_id
    
    try:
        response = cleanrooms_client.create_configured_table_association(
            membershipIdentifier=membership_id,
            configuredTableIdentifier=configured_table_id,
            name=name,
            roleArn=role_arn
        )
        association_id = response['configuredTableAssociation']['id']
        print(f"✅ Created table association: {name} (ID: {association_id})")
        return association_id
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConflictException':
            # Association was created between check and create, get its ID
            print(f"⚠️  Table association {name} already exists, getting ID...")
            existing_assoc_id = get_existing_association(cleanrooms_client, membership_id, configured_table_id)
            if existing_assoc_id:
                print(f"✅ Found existing association: {name} (ID: {existing_assoc_id})")
                return existing_assoc_id
            # Fallback: try to find by name
            paginator = cleanrooms_client.get_paginator('list_configured_table_associations')
            for page in paginator.paginate(membershipIdentifier=membership_id):
                for assoc in page.get('configuredTableAssociationSummaries', []):
                    if assoc['name'] == name:
                        return assoc['id']
            raise Exception(f"Association {name} exists but couldn't find its ID")
        else:
            print(f"❌ Error creating table association {name}: {e}")
            raise


def get_existing_collaboration_analysis_rule(
    cleanrooms_client,
    membership_id: str,
    configured_table_association_id: str
) -> bool:
    """Check if a collaboration analysis rule already exists for the association."""
    try:
        cleanrooms_client.get_configured_table_association_analysis_rule(
            membershipIdentifier=membership_id,
            configuredTableAssociationIdentifier=configured_table_association_id,
            analysisRuleType="CUSTOM"
        )
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return False
        # If it's a different error, we'll try to create and handle it
        return False
    except Exception:
        return False


def create_collaboration_analysis_rule(
    cleanrooms_client,
    membership_id: str,
    configured_table_association_id: str,
    allowed_analyses: str = "ANY",
    allowed_members: Optional[List[str]] = None
):
    """Create a collaboration analysis rule for direct analysis (only if it doesn't exist)."""
    # Check if rule already exists
    if get_existing_collaboration_analysis_rule(cleanrooms_client, membership_id, configured_table_association_id):
        print(f"✅ Collaboration analysis rule already exists for association {configured_table_association_id}, skipping creation")
        return
    
    try:
        # Build collaboration analysis rule policy
        # For collaboration analysis rules, use CUSTOM type
        # allowedResultReceivers must be 12-digit account IDs (not membership IDs)
        # If configured table doesn't allow additional analyses, omit allowedAdditionalAnalyses
        rule_policy = {
            "v1": {
                "custom": {
                    "allowedResultReceivers": allowed_members if allowed_members else []
                }
            }
        }
        
        cleanrooms_client.create_configured_table_association_analysis_rule(
            membershipIdentifier=membership_id,
            configuredTableAssociationIdentifier=configured_table_association_id,
            analysisRuleType="CUSTOM",
            analysisRulePolicy=rule_policy
        )
        print(f"✅ Created collaboration analysis rule for association {configured_table_association_id}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConflictException':
            print(f"⚠️  Collaboration analysis rule already exists for association {configured_table_association_id}")
        else:
            print(f"❌ Error creating collaboration analysis rule: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description='Create Cleanrooms configured tables')
    parser.add_argument('--region', default=DEFAULT_REGION, help='AWS region')
    parser.add_argument('--database', default=DEFAULT_DATABASE, help='Glue database name')
    parser.add_argument('--bucket', default=DEFAULT_BUCKET, help='S3 bucket name')
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--membership-id', help='Cleanrooms membership ID (optional)')
    parser.add_argument('--allowed-query-providers', nargs='+', default=[], 
                       help='AWS account IDs allowed for custom queries')
    parser.add_argument('--create-role', action='store_true', default=True,
                       help='Create IAM role for Cleanrooms access')
    parser.add_argument('--role-name', default='cleanrooms-glue-s3-access',
                       help='IAM role name')
    parser.add_argument('--tables', nargs='+', default=PART_TABLES,
                       help='List of table names to configure')
    parser.add_argument('--rule-type', default='CUSTOM',
                       choices=['CUSTOM', 'AGGREGATION', 'LIST'],
                       help='Analysis rule type')
    parser.add_argument('--no-verify-ssl', action='store_true',
                       help='Disable SSL certificate verification (not recommended)')
    
    args = parser.parse_args()
    
    # Configure boto3 clients
    if args.no_verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        import ssl
        import os
        os.environ['PYTHONHTTPSVERIFY'] = '0'
        ssl._create_default_https_context = ssl._create_unverified_context
        print("⚠️  SSL verification disabled - not recommended for production")
        config = Config(connect_timeout=60, read_timeout=60)
    else:
        config = Config()
    
    # Create AWS clients
    session = boto3.Session(profile_name=args.profile) if args.profile else boto3.Session()
    cleanrooms = session.client('cleanrooms', region_name=args.region, config=config, verify=not args.no_verify_ssl)
    glue = session.client('glue', region_name=args.region, config=config, verify=not args.no_verify_ssl)
    iam = session.client('iam', region_name=args.region, config=config, verify=not args.no_verify_ssl)
    
    # Tags
    tags = {
        "Project": "OMC Flywheel Cleanroom",
        "Environment": "Production",
        "Owner": "Data Engineering",
        "ManagedBy": "Terraform"
    }
    
    # Create IAM role if needed
    role_arn = None
    if args.create_role:
        s3_resources = [
            f"arn:aws:s3:::{args.bucket}",
            f"arn:aws:s3:::{args.bucket}/*"
        ]
        role_arn = create_iam_role(iam, args.role_name, s3_resources, tags)
    
    print(f"\n📊 Creating configured tables for {len(args.tables)} tables...\n")
    
    # Create configured tables
    table_ids = {}
    for table_name in args.tables:
        try:
            # Get columns from Glue
            columns = get_glue_table_columns(glue, args.database, table_name)
            
            # Create configured table
            table_id = create_configured_table(
                cleanrooms,
                name=table_name,
                description=f"Partitioned table {table_name} for Clean Rooms analysis",
                database=args.database,
                table=table_name,
                allowed_columns=columns,
                tags=tags
            )
            table_ids[table_name] = table_id
            
            # Create analysis rule
            create_analysis_rule(
                cleanrooms,
                configured_table_id=table_id,
                rule_type=args.rule_type,
                allowed_query_providers=args.allowed_query_providers if args.rule_type == 'CUSTOM' else None
            )
            
        except Exception as e:
            print(f"❌ Failed to create configured table {table_name}: {e}")
            continue
    
    # Get collaboration ID from membership
    collaboration_id = None
    if args.membership_id:
        try:
            membership = cleanrooms.get_membership(membershipIdentifier=args.membership_id)
            collaboration_id = membership['membership']['collaborationId']
            print(f"📋 Found collaboration ID: {collaboration_id}")
        except Exception as e:
            print(f"⚠️  Could not get collaboration ID: {e}")
    
    # Create associations if membership_id provided
    association_ids = {}
    if args.membership_id and role_arn:
        print(f"\n🔗 Creating table associations with membership {args.membership_id}...\n")
        for table_name, table_id in table_ids.items():
            try:
                assoc_id = create_table_association(
                    cleanrooms,
                    membership_id=args.membership_id,
                    configured_table_id=table_id,
                    name=f"acx_{table_name}",
                    role_arn=role_arn
                )
                association_ids[table_name] = assoc_id
            except Exception as e:
                print(f"❌ Failed to create association for {table_name}: {e}")
                continue
    
    # Create collaboration analysis rules for direct analysis
    if args.membership_id and association_ids:
        print(f"\n📝 Creating collaboration analysis rules for direct analysis...\n")
        # Get collaboration ID to determine allowed result receivers
        try:
            membership = cleanrooms.get_membership(membershipIdentifier=args.membership_id)
            collaboration_id = membership['membership']['collaborationId']
            members = cleanrooms.list_members(collaborationIdentifier=collaboration_id)
            all_account_ids = [m['accountId'] for m in members.get('memberSummaries', [])]
            # Default to the account IDs that are allowed to receive results
            # These are typically the Query Submitter and Advertiser accounts
            default_result_receivers = ["657425294073", "803109464991"]  # Query Submitter/AMC Results Receiver, Advertiser
            result_receivers = [aid for aid in default_result_receivers if aid in all_account_ids]
            if not result_receivers:
                result_receivers = all_account_ids  # Fallback to all if defaults not found
            print(f"Using result receivers: {result_receivers}\n")
        except Exception as e:
            print(f"⚠️  Could not determine result receivers, using empty list: {e}\n")
            result_receivers = []
        
        for table_name, assoc_id in association_ids.items():
            try:
                create_collaboration_analysis_rule(
                    cleanrooms,
                    membership_id=args.membership_id,
                    configured_table_association_id=assoc_id,
                    allowed_analyses="ANY",
                    allowed_members=result_receivers
                )
            except Exception as e:
                print(f"❌ Failed to create collaboration analysis rule for {table_name}: {e}")
                continue
    
    print(f"\n✅ Complete! Created {len(table_ids)} configured tables")
    if args.membership_id:
        print(f"✅ Associated tables with membership: {args.membership_id}")
    
    # Print summary
    print("\n📋 Summary:")
    print(f"  Configured Tables: {len(table_ids)}")
    print(f"  Analysis Rule Type: {args.rule_type}")
    if args.allowed_query_providers:
        print(f"  Allowed Query Providers: {', '.join(args.allowed_query_providers)}")
    if args.membership_id:
        print(f"  Membership ID: {args.membership_id}")
    if role_arn:
        print(f"  IAM Role ARN: {role_arn}")


if __name__ == "__main__":
    main()

