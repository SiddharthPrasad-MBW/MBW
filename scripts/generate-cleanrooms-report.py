#!/usr/bin/env python3
"""
Generate comprehensive report of part_* tables, Cleanrooms configured tables, collaboration setup, and Identity Resolution Service.

This script generates a detailed report showing:
- Glue part_* tables
- Cleanrooms configured tables
- Collaboration associations
- Analysis rules (configured table and collaboration)
- Analysis providers and result receivers
- Column counts and configuration
- Identity Resolution Service resources:
  - ID namespace associations
  - ID mapping tables
  - Entity Resolution namespaces
"""

import argparse
import json
import sys
import boto3
import csv
import io
from datetime import datetime
from botocore.config import Config
from botocore.exceptions import ClientError

def parse_args():
    parser = argparse.ArgumentParser(
        description='Generate comprehensive Cleanrooms report'
    )
    parser.add_argument(
        '--profile',
        nargs='?',
        default='',
        const='',
        help='AWS profile name (empty or omitted for Glue execution, uses IAM role)'
    )
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    parser.add_argument(
        '--database',
        default='omc_flywheel_prod',
        help='Glue database name (default: omc_flywheel_prod)'
    )
    parser.add_argument(
        '--table-prefix',
        default='part_',
        help='Table prefix to filter (default: part_)'
    )
    parser.add_argument(
        '--membership-id',
        default='6610c9aa-9002-475c-8695-d833485741bc',
        help='Cleanrooms membership ID (default: 6610c9aa-9002-475c-8695-d833485741bc)'
    )
    parser.add_argument(
        '--report-bucket',
        required=True,
        help='S3 bucket for report output'
    )
    parser.add_argument(
        '--report-prefix',
        default='cleanrooms-reports/',
        help='S3 prefix for reports (default: cleanrooms-reports/)'
    )
    parser.add_argument(
        '--output-format',
        choices=['json', 'csv', 'both'],
        default='both',
        help='Output format (default: both)'
    )
    parser.add_argument(
        '--no-verify-ssl',
        action='store_true',
        help='Disable SSL verification'
    )
    # Use parse_known_args to ignore Glue-specific arguments
    args, unknown = parser.parse_known_args()
    if unknown:
        print(f"[DEBUG] Ignoring unknown Glue arguments: {unknown}")
    return args

def get_glue_tables(glue, database, prefix):
    """Get all Glue tables matching prefix."""
    tables = []
    try:
        paginator = glue.get_paginator('get_tables')
        for page in paginator.paginate(DatabaseName=database):
            for table in page.get('TableList', []):
                if table['Name'].startswith(prefix):
                    tables.append(table)
    except Exception as e:
        print(f"Error listing Glue tables: {e}")
    return tables

def get_configured_tables(cleanrooms):
    """Get all Cleanrooms configured tables."""
    tables = []
    try:
        paginator = cleanrooms.get_paginator('list_configured_tables')
        for page in paginator.paginate():
            tables.extend(page.get('configuredTableSummaries', []))
    except Exception as e:
        print(f"Error listing configured tables: {e}")
    return tables

def get_configured_table_details(cleanrooms, table_id):
    """Get detailed information about a configured table."""
    try:
        response = cleanrooms.get_configured_table(configuredTableIdentifier=table_id)
        return response.get('configuredTable', {})
    except Exception as e:
        print(f"Error getting configured table details for {table_id}: {e}")
        return None

def get_analysis_rule(cleanrooms, table_id, rule_type='CUSTOM'):
    """Get analysis rule for a configured table."""
    try:
        response = cleanrooms.get_configured_table_analysis_rule(
            configuredTableIdentifier=table_id,
            analysisRuleType=rule_type
        )
        return response.get('analysisRule', {})
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return None
        print(f"Error getting analysis rule for {table_id}: {e}")
        return None
    except Exception as e:
        print(f"Error getting analysis rule for {table_id}: {e}")
        return None

def get_associations(cleanrooms, membership_id):
    """Get all configured table associations for a membership."""
    associations = []
    try:
        paginator = cleanrooms.get_paginator('list_configured_table_associations')
        for page in paginator.paginate(membershipIdentifier=membership_id):
            associations.extend(page.get('configuredTableAssociationSummaries', []))
    except Exception as e:
        print(f"Error listing associations: {e}")
    return associations

def get_association_details(cleanrooms, membership_id, association_id):
    """Get detailed information about an association."""
    try:
        response = cleanrooms.get_configured_table_association(
            membershipIdentifier=membership_id,
            configuredTableAssociationIdentifier=association_id
        )
        return response.get('configuredTableAssociation', {})
    except Exception as e:
        print(f"Error getting association details for {association_id}: {e}")
        return None

def get_schema_result_receivers(cleanrooms, collaboration_id, schema_name):
    """
    Return allowedResultReceivers for a schema's CUSTOM analysis rule
    (this is what the console shows as 'Results delivery -> Direct querying').
    """
    try:
        resp = cleanrooms.get_schema_analysis_rule(
            collaborationIdentifier=collaboration_id,
            name=schema_name,
            type='CUSTOM'
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return []  # no schema-level rule
        print(f"   [DEBUG] Error getting schema analysis rule for {schema_name}: {e}")
        return []
    except Exception as e:
        print(f"   [DEBUG] Error getting schema analysis rule for {schema_name}: {e}")
        return []

    # Prefer consolidatedPolicy (collaboration + member merged)
    analysis_rule = resp.get('analysisRule', {})
    consolidated = (
        analysis_rule.get('consolidatedPolicy', {})
            .get('v1', {})
            .get('custom', {})
    )
    # Fallback to collaborationPolicy if consolidated is empty
    if not consolidated:
        consolidated = (
            analysis_rule.get('collaborationPolicy', {})
                .get('v1', {})
                .get('custom', {})
        )

    result_receivers = consolidated.get('allowedResultReceivers', [])
    print(f"   [DEBUG] Schema {schema_name} result_receivers: {result_receivers}")
    return result_receivers

def get_collaboration_analysis_rule(cleanrooms, membership_id, association_id, rule_type='CUSTOM'):
    """Get collaboration analysis rule for an association."""
    try:
        # Check if method exists
        if not hasattr(cleanrooms, 'get_configured_table_association_analysis_rule'):
            print(f"   [DEBUG] get_configured_table_association_analysis_rule method does not exist")
            return None
        
        # Try the method that exists in newer boto3
        print(f"   [DEBUG] Calling get_configured_table_association_analysis_rule for association {association_id}")
        response = cleanrooms.get_configured_table_association_analysis_rule(
            membershipIdentifier=membership_id,
            configuredTableAssociationIdentifier=association_id,
            analysisRuleType=rule_type
        )
        print(f"   [DEBUG] Response keys: {list(response.keys())}")
        analysis_rule = response.get('analysisRule', {})
        print(f"   [DEBUG] analysisRule keys: {list(analysis_rule.keys()) if analysis_rule else 'None'}")
        # Return the full analysisRule, which contains 'policy'
        return analysis_rule
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        print(f"   [DEBUG] ClientError getting collaboration rule for {association_id}: {error_code} - {error_message}")
        if error_code == 'ResourceNotFoundException':
            print(f"   [DEBUG] ResourceNotFoundException - collaboration rule does not exist for {association_id}")
            return None
        # Don't silently handle other errors - print them
        print(f"   [DEBUG] ClientError details: {e}")
        return None
    except AttributeError as e:
        # Method doesn't exist in this boto3 version
        print(f"   [DEBUG] AttributeError: {e}")
        return None
    except Exception as e:
        # Print all other exceptions for debugging
        print(f"   [DEBUG] Exception getting collaboration rule for {association_id}: {type(e).__name__}: {e}")
        import traceback
        print(f"   [DEBUG] Traceback: {traceback.format_exc()}")
        return None

def get_membership_info(cleanrooms, membership_id):
    """Get membership information."""
    try:
        response = cleanrooms.get_membership(membershipIdentifier=membership_id)
        return response.get('membership', {})
    except Exception as e:
        print(f"Error getting membership info: {e}")
        return None

def get_collaboration_info(cleanrooms, collaboration_id):
    """Get collaboration information including name."""
    if not collaboration_id or collaboration_id == 'N/A':
        print(f"   ⚠️  No collaboration_id provided")
        return None
    try:
        # First try get_collaboration
        print(f"   [DEBUG] Calling get_collaboration with ID: {collaboration_id}")
        response = cleanrooms.get_collaboration(collaborationIdentifier=collaboration_id)
        collaboration = response.get('collaboration', {})
        if collaboration:
            print(f"   [DEBUG] Successfully retrieved collaboration: {collaboration.get('name', 'N/A')}")
        else:
            print(f"   [DEBUG] Response missing 'collaboration' key: {list(response.keys())}")
        return collaboration
    except Exception as e:
        print(f"   ⚠️  Error getting collaboration via get_collaboration: {type(e).__name__}: {e}")
        # Fallback: use list_collaborations and find matching one
        try:
            print(f"   Trying list_collaborations as fallback...")
            list_response = cleanrooms.list_collaborations()
            for collab in list_response.get('collaborationList', []):
                # Note: list_collaborations returns 'id' not 'collaborationId'
                if collab.get('id') == collaboration_id or collab.get('collaborationId') == collaboration_id:
                    print(f"   ✅ Found collaboration via list_collaborations: {collab.get('name')}")
                    return collab
            print(f"   ⚠️  Collaboration {collaboration_id} not found in list_collaborations")
            return None
        except Exception as e2:
            print(f"   ⚠️  Error getting collaboration via list_collaborations: {type(e2).__name__}: {e2}")
            return None

def get_membership_results_info(cleanrooms, membership_id):
    """Get results delivery information from membership."""
    try:
        resp = cleanrooms.get_membership(membershipIdentifier=membership_id)
    except Exception as e:
        print(f"   ⚠️  Error getting membership results info: {e}")
        return {
            "can_receive_results": False,
            "result_bucket": "",
            "result_prefix": "",
            "result_role_arn": ""
        }

    m = resp.get("membership", {})
    abilities = m.get("memberAbilities", [])
    can_receive = "CAN_RECEIVE_RESULTS" in abilities

    cfg = m.get("defaultResultConfiguration", {})
    s3_cfg = cfg.get("outputConfiguration", {}).get("s3", {})

    return {
        "can_receive_results": can_receive,
        "result_bucket": s3_cfg.get("bucket", ""),
        "result_prefix": s3_cfg.get("keyPrefix", ""),
        "result_role_arn": cfg.get("roleArn", "")
    }

def get_results_delivery_accounts(cleanrooms, collaboration_id):
    """Get results delivery accounts from memberships.
    
    For each member account in the collaboration, check if their membership
    has CAN_RECEIVE_RESULTS in memberAbilities and defaultResultConfiguration is set.
    """
    results_delivery_accounts = []
    try:
        # List all members in the collaboration
        print(f"   [DEBUG] Listing members for collaboration: {collaboration_id}")
        members_response = cleanrooms.list_members(collaborationIdentifier=collaboration_id)
        member_summaries = members_response.get('memberSummaries', [])
        
        print(f"   Checking {len(member_summaries)} members for results delivery capability...")
        
        if not member_summaries:
            print(f"   ⚠️  No members found in collaboration {collaboration_id}")
            return results_delivery_accounts
        
        for member in member_summaries:
            account_id = member.get('accountId')
            membership_id = member.get('membershipId')
            
            print(f"   [DEBUG] Checking member: account_id={account_id}, membership_id={membership_id}")
            
            if not account_id or not membership_id:
                print(f"   ⚠️  Skipping member with missing account_id or membership_id")
                continue
            
            try:
                # Get the membership details for this member
                print(f"   [DEBUG] Getting membership details for {membership_id}...")
                membership_response = cleanrooms.get_membership(membershipIdentifier=membership_id)
                membership_details = membership_response.get('membership', {})
                
                print(f"   [DEBUG] Membership details keys: {list(membership_details.keys())}")
                
                # Check if memberAbilities contains CAN_RECEIVE_RESULTS
                member_abilities = membership_details.get('memberAbilities', [])
                print(f"   [DEBUG] memberAbilities for {account_id}: {member_abilities}")
                has_can_receive_results = 'CAN_RECEIVE_RESULTS' in member_abilities
                
                # Check if defaultResultConfiguration is set
                default_result_config = membership_details.get('defaultResultConfiguration')
                print(f"   [DEBUG] defaultResultConfiguration for {account_id}: {default_result_config is not None} (value: {default_result_config})")
                has_default_result_config = default_result_config is not None
                
                print(f"   [DEBUG] {account_id} - has_can_receive_results: {has_can_receive_results}, has_default_result_config: {has_default_result_config}")
                
                if has_can_receive_results and has_default_result_config:
                    results_delivery_accounts.append(account_id)
                    print(f"   ✅ {account_id} can receive results")
                else:
                    print(f"   ❌ {account_id} cannot receive results (CAN_RECEIVE_RESULTS: {has_can_receive_results}, defaultResultConfiguration: {has_default_result_config})")
                    
            except Exception as e:
                # Skip if we can't get membership details for this member
                print(f"   ⚠️  Could not check membership {membership_id} for account {account_id}: {e}")
                import traceback
                print(f"   [DEBUG] Traceback: {traceback.format_exc()}")
                continue
                
    except Exception as e:
        print(f"   ⚠️  Error getting results delivery accounts: {e}")
        import traceback
        print(f"   [DEBUG] Traceback: {traceback.format_exc()}")
    
    print(f"   [DEBUG] Final results_delivery_accounts: {results_delivery_accounts}")
    return results_delivery_accounts

def get_id_namespace_associations(cleanrooms, membership_id):
    """Get all ID namespace associations for a membership."""
    associations = []
    try:
        # Debug: Check what methods are available
        print(f"   [DEBUG] Checking available Cleanrooms methods...")
        import boto3
        print(f"   [DEBUG] boto3 version: {boto3.__version__}")
        cleanrooms_methods = [m for m in dir(cleanrooms) if 'id_namespace' in m.lower() or 'idnamespace' in m.lower()]
        print(f"   [DEBUG] Cleanrooms methods with 'id_namespace' or 'idnamespace': {cleanrooms_methods}")
        # Also check for 'list' methods
        list_methods = [m for m in dir(cleanrooms) if m.startswith('list_') and not m.startswith('_')]
        print(f"   [DEBUG] All Cleanrooms 'list_' methods: {list_methods[:20]}")  # Show first 20
        
        # Try different method name variations
        method_found = False
        if hasattr(cleanrooms, 'list_id_namespace_associations'):
            method_found = True
            print(f"   [DEBUG] Found list_id_namespace_associations method")
            response = cleanrooms.list_id_namespace_associations(membershipIdentifier=membership_id)
            print(f"   [DEBUG] Response keys: {list(response.keys())}")
            summaries = response.get('idNamespaceAssociationSummaries', [])
            print(f"   [DEBUG] Found {len(summaries)} ID namespace association summaries")
            for ns in summaries:
                print(f"   [DEBUG] Processing ID namespace association: {ns.get('id')} - {ns.get('name')}")
                try:
                    if hasattr(cleanrooms, 'get_id_namespace_association'):
                        details = cleanrooms.get_id_namespace_association(
                            membershipIdentifier=membership_id,
                            idNamespaceAssociationIdentifier=ns['id']
                        )
                        assoc_data = details.get('idNamespaceAssociation', {})
                        print(f"   [DEBUG] Got association details. Keys: {list(assoc_data.keys())}")
                        associations.append(assoc_data)
                    else:
                        # If get method doesn't exist, use summary data
                        print(f"   [DEBUG] get_id_namespace_association not available, using summary data")
                        associations.append(ns)
                except Exception as e:
                    print(f"   ⚠️  Error getting ID namespace association details for {ns.get('id')}: {e}")
                    import traceback
                    print(f"   [DEBUG] Traceback: {traceback.format_exc()}")
        else:
            print("   ⚠️  list_id_namespace_associations method not available in this boto3 version")
            # Try alternative method names
            for alt_method in ['list_id_namespaces', 'list_namespace_associations']:
                if hasattr(cleanrooms, alt_method):
                    print(f"   [DEBUG] Found alternative method: {alt_method}")
                    method_found = True
                    break
    except AttributeError as e:
        print(f"   ⚠️  AttributeError: {e}")
        print("   ⚠️  ID namespace association methods not available in this boto3 version")
    except Exception as e:
        print(f"   ⚠️  Error listing ID namespace associations: {e}")
        import traceback
        print(f"   [DEBUG] Traceback: {traceback.format_exc()}")
    
    print(f"   [DEBUG] Returning {len(associations)} ID namespace associations")
    return associations

def get_id_mapping_tables(cleanrooms, membership_id):
    """Get all ID mapping tables for a membership."""
    tables = []
    try:
        if hasattr(cleanrooms, 'list_id_mapping_tables'):
            response = cleanrooms.list_id_mapping_tables(membershipIdentifier=membership_id)
            for table in response.get('idMappingTableSummaries', []):
                try:
                    if hasattr(cleanrooms, 'get_id_mapping_table'):
                        details = cleanrooms.get_id_mapping_table(
                            membershipIdentifier=membership_id,
                            idMappingTableIdentifier=table['id']
                        )
                        tables.append(details.get('idMappingTable', {}))
                except Exception as e:
                    print(f"Error getting ID mapping table details for {table.get('id')}: {e}")
    except AttributeError:
        # Method doesn't exist in this boto3 version
        pass
    except Exception as e:
        if 'object has no attribute' not in str(e):
            print(f"Error listing ID mapping tables: {e}")
    return tables

def get_entity_resolution_namespace(entity_resolution, namespace_arn):
    """Get Entity Resolution namespace details."""
    try:
        # Extract namespace name from ARN
        # ARN format: arn:aws:entityresolution:region:account:idnamespace/Name
        if namespace_arn and 'idnamespace' in namespace_arn:
            namespace_name = namespace_arn.split('/')[-1]
            if hasattr(entity_resolution, 'get_id_namespace'):
                response = entity_resolution.get_id_namespace(idNamespaceName=namespace_name)
                return response.get('idNamespace', {})
        return None
    except Exception as e:
        # Silently handle errors - namespace might not exist or method unavailable
        if 'object has no attribute' not in str(e):
            print(f"Error getting Entity Resolution namespace {namespace_arn}: {e}")
        return None

def get_schema_mapping(entity_resolution, schema_name):
    """Get Entity Resolution schema mapping details."""
    try:
        if hasattr(entity_resolution, 'get_schema_mapping'):
            response = entity_resolution.get_schema_mapping(schemaName=schema_name)
            return response.get('schemaMapping', {})
        return None
    except Exception as e:
        # Silently handle errors
        if 'object has no attribute' not in str(e) and 'ResourceNotFoundException' not in str(e):
            print(f"Error getting schema mapping {schema_name}: {e}")
        return None

def list_schema_mappings(entity_resolution):
    """List all Entity Resolution schema mappings."""
    try:
        if hasattr(entity_resolution, 'list_schema_mappings'):
            response = entity_resolution.list_schema_mappings()
            return response.get('schemaList', [])
        return []
    except Exception as e:
        if 'object has no attribute' not in str(e):
            print(f"Error listing schema mappings: {e}")
        return []

def generate_report(glue, cleanrooms, entity_resolution, args):
    """Generate comprehensive report."""
    print("=" * 80)
    print("Cleanrooms Comprehensive Report")
    print("=" * 80)
    print()
    
    # Get membership info
    print("📋 Getting membership information...")
    membership = get_membership_info(cleanrooms, args.membership_id)
    collaboration_id = membership.get('collaborationId', 'N/A') if membership else 'N/A'
    print(f"   Membership ID: {args.membership_id}")
    print(f"   Collaboration ID: {collaboration_id}")
    
    # Get collaboration info (including name)
    collaboration_name = 'N/A'
    if collaboration_id and collaboration_id != 'N/A':
        print("📋 Getting collaboration information...")
        collaboration = get_collaboration_info(cleanrooms, collaboration_id)
        if collaboration:
            collaboration_name = collaboration.get('name', 'N/A')
            print(f"   Collaboration Name: {collaboration_name}")
        else:
            print(f"   ⚠️  Could not retrieve collaboration details")
    
    # Get membership results delivery information
    print("📋 Getting membership results delivery information...")
    membership_results = get_membership_results_info(cleanrooms, args.membership_id)
    print(f"   Can receive results: {membership_results['can_receive_results']}")
    if membership_results['result_bucket']:
        print(f"   Result bucket: {membership_results['result_bucket']}")
        print(f"   Result prefix: {membership_results['result_prefix']}")
    if membership_results['result_role_arn']:
        print(f"   Result role ARN: {membership_results['result_role_arn']}")
    
    # Get results delivery accounts from memberships
    print("📋 Getting results delivery accounts from memberships...")
    results_delivery_accounts = []
    if collaboration_id and collaboration_id != 'N/A':
        results_delivery_accounts = get_results_delivery_accounts(cleanrooms, collaboration_id)
        print(f"   Found {len(results_delivery_accounts)} results delivery accounts: {results_delivery_accounts}")
    else:
        print(f"   ⚠️  No collaboration ID found, cannot get results delivery accounts")
    print()
    
    # Debug: Print results_delivery_accounts to verify it's set
    print(f"[DEBUG] results_delivery_accounts in generate_report: {results_delivery_accounts}")
    
    # Get Identity Resolution Service resources
    print("🔗 Getting Identity Resolution Service resources...")
    
    # Since boto3 in Glue doesn't have list_id_namespace_associations, get Entity Resolution resources directly
    # Known namespace name from production: ACXIdNamespace
    er_namespaces = []
    schema_mappings = []
    
    # Try to get Entity Resolution namespace directly by name
    print("   Getting Entity Resolution namespace: ACXIdNamespace...")
    try:
        if hasattr(entity_resolution, 'get_id_namespace'):
            er_ns_response = entity_resolution.get_id_namespace(idNamespaceName='ACXIdNamespace')
            if er_ns_response:
                # The response contains the data directly, not wrapped in 'idNamespace'
                # Remove ResponseMetadata and convert datetime objects to strings
                from datetime import datetime
                id_namespace_data = {}
                for k, v in er_ns_response.items():
                    if k == 'ResponseMetadata':
                        continue
                    # Convert datetime objects to ISO format strings
                    if isinstance(v, datetime):
                        id_namespace_data[k] = v.isoformat()
                    else:
                        id_namespace_data[k] = v
                er_namespaces.append(id_namespace_data)
                print(f"   ✅ Found Entity Resolution namespace: ACXIdNamespace")
        else:
            print("   ⚠️  get_id_namespace method not available")
    except Exception as e:
        print(f"   ⚠️  Error getting Entity Resolution namespace: {e}")
    
    # Try to get schema mapping directly by name
    print("   Getting Entity Resolution schema mapping: ACX_SCHEMA...")
    try:
        if hasattr(entity_resolution, 'get_schema_mapping'):
            schema_mapping_response = entity_resolution.get_schema_mapping(schemaName='ACX_SCHEMA')
            if schema_mapping_response:
                # The response contains the data directly, not wrapped in 'schemaMapping'
                # Remove ResponseMetadata and convert datetime objects to strings
                from datetime import datetime
                schema_mapping_data = {}
                for k, v in schema_mapping_response.items():
                    if k == 'ResponseMetadata':
                        continue
                    # Convert datetime objects to ISO format strings
                    if isinstance(v, datetime):
                        schema_mapping_data[k] = v.isoformat()
                    else:
                        schema_mapping_data[k] = v
                schema_mappings.append(schema_mapping_data)
                print(f"   ✅ Found schema mapping: ACX_SCHEMA")
        else:
            print("   ⚠️  get_schema_mapping method not available")
    except Exception as e:
        print(f"   ⚠️  Error getting schema mapping: {e}")
    
    # Also try the old method for ID namespace associations (in case it works)
    id_namespace_associations = get_id_namespace_associations(cleanrooms, args.membership_id)
    print(f"   Found {len(id_namespace_associations)} ID namespace associations (via Cleanrooms API)")
    
    id_mapping_tables = get_id_mapping_tables(cleanrooms, args.membership_id)
    print(f"   Found {len(id_mapping_tables)} ID mapping tables")
    
    print(f"   Found {len(er_namespaces)} Entity Resolution namespaces")
    print(f"   Found {len(schema_mappings)} schema mappings")
    print()
    
    # Get Glue tables
    print(f"📊 Getting Glue tables (prefix: {args.table_prefix})...")
    glue_tables = get_glue_tables(glue, args.database, args.table_prefix)
    print(f"   Found {len(glue_tables)} Glue tables")
    print()
    
    # Get configured tables
    print("🏢 Getting Cleanrooms configured tables...")
    configured_tables = get_configured_tables(cleanrooms)
    print(f"   Found {len(configured_tables)} configured tables")
    print()
    
    # Get associations
    print("🔗 Getting collaboration associations...")
    associations = get_associations(cleanrooms, args.membership_id)
    print(f"   Found {len(associations)} associations")
    print()
    
    # Build report data
    print("📝 Building report...")
    
    # Extract ER namespace data properly before storing
    er_namespaces_processed = []
    for ns in er_namespaces:
        # Extract inputSourceConfig (array) - note: key is 'inputSourceARN' (capital ARN)
        input_source_arn = ''
        schema_name = ''
        input_source_config = ns.get('inputSourceConfig', [])
        if isinstance(input_source_config, list) and len(input_source_config) > 0:
            first_config = input_source_config[0]
            input_source_arn = first_config.get('inputSourceARN', '')  # Note: capital ARN
            schema_name = first_config.get('schemaName', '')
        
        # Extract idMappingWorkflowProperties (array)
        id_mapping_config = {}
        id_mapping_workflow_props = ns.get('idMappingWorkflowProperties', [])
        if isinstance(id_mapping_workflow_props, list) and len(id_mapping_workflow_props) > 0:
            id_mapping_config = id_mapping_workflow_props[0]
        
        processed_ns = {
            'name': ns.get('idNamespaceName', ''),
            'arn': ns.get('idNamespaceArn', ''),
            'type': ns.get('type', ''),
            'description': ns.get('description', ''),
            'role_arn': ns.get('roleArn', ''),
            'input_source_arn': input_source_arn,
            'schema_name': schema_name,
            'id_mapping_config': id_mapping_config
        }
        er_namespaces_processed.append(processed_ns)
    
    report_data = {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'membership_id': args.membership_id,
        'collaboration_id': collaboration_id,
        'collaboration_name': collaboration_name,
        'database': args.database,
        'table_prefix': args.table_prefix,
        'summary': {
            'glue_tables_count': len(glue_tables),
            'configured_tables_count': len(configured_tables),
            'associations_count': len(associations),
            'id_namespace_associations_count': len(id_namespace_associations),
            'id_mapping_tables_count': len(id_mapping_tables),
            'entity_resolution_namespaces_count': len(er_namespaces)
        },
        'identity_resolution': {
            'id_namespace_associations': [
                {
                    'id': ns.get('id'),
                    'name': ns.get('name'),
                    'arn': ns.get('arn'),
                    'description': ns.get('description', ''),
                    'entity_resolution_namespace_arn': ns.get('inputReferenceConfig', {}).get('inputReferenceArn', ''),
                    'manage_resource_policies': ns.get('inputReferenceConfig', {}).get('manageResourcePolicies', False),
                    'allow_use_as_dimension_column': ns.get('idMappingConfig', {}).get('allowUseAsDimensionColumn', False)
                }
                for ns in id_namespace_associations
            ],
            'id_mapping_tables': [
                {
                    'id': table.get('id'),
                    'name': table.get('name'),
                    'arn': table.get('arn'),
                    'description': table.get('description', ''),
                    'input_reference_arn': table.get('inputReferenceConfig', {}).get('inputReferenceArn', ''),
                    'input_sources': [
                        {
                            'id_namespace_association_id': source.get('idNamespaceAssociationId'),
                            'type': source.get('type')
                        }
                        for source in table.get('inputReferenceProperties', {}).get('idMappingTableInputSource', [])
                    ]
                }
                for table in id_mapping_tables
            ],
            'entity_resolution_namespaces': er_namespaces_processed,
            'schema_mappings': [
                {
                    'name': sm.get('schemaName') or sm.get('name', ''),
                    'arn': sm.get('schemaArn') or sm.get('arn', ''),
                    'created_at': sm.get('createdAt', ''),
                    'updated_at': sm.get('updatedAt', ''),
                    'has_workflows': sm.get('hasWorkflows', False),
                    'mappedInputFields': sm.get('mappedInputFields', [])
                }
                for sm in schema_mappings
            ]
        },
        'membership_results_delivery': membership_results,
        'tables': []
    }
    
    # List schemas in the collaboration to understand schema naming
    schema_map = {}
    if collaboration_id and collaboration_id != 'N/A':
        try:
            print(f"   📋 Listing schemas in collaboration {collaboration_id}...")
            schemas_response = cleanrooms.list_schemas(collaborationIdentifier=collaboration_id)
            schemas = schemas_response.get('schemaList', [])
            print(f"   Found {len(schemas)} schemas")
            for schema in schemas:
                schema_name = schema.get('name', '')
                schema_arn = schema.get('schemaArn', '')
                schema_map[schema_name] = schema
                print(f"   [DEBUG] Schema: {schema_name} (ARN: {schema_arn})")
        except Exception as e:
            print(f"   ⚠️  Error listing schemas: {e}")
    
    # Create lookup maps
    configured_table_map = {ct['name']: ct for ct in configured_tables}
    association_map = {assoc['name']: assoc for assoc in associations}
    
    # Process each Glue table (exclude part_addressable_ids and part_addressable_ids_er)
    excluded_tables = {'part_addressable_ids', 'part_addressable_ids_er'}
    for glue_table in glue_tables:
        table_name = glue_table['Name']
        if table_name in excluded_tables:
            print(f"   Skipping excluded table: {table_name}...")
            continue
        print(f"   Processing {table_name}...")
        
        # Get Glue table info
        columns = glue_table.get('StorageDescriptor', {}).get('Columns', [])
        partition_keys = glue_table.get('PartitionKeys', [])
        location = glue_table.get('StorageDescriptor', {}).get('Location', 'N/A')
        
        # Get configured table info
        configured_table = configured_table_map.get(table_name)
        configured_table_id = None
        configured_table_details = None
        analysis_rule = None
        allowed_columns = []
        
        if configured_table:
            configured_table_id = configured_table['id']
            configured_table_details = get_configured_table_details(cleanrooms, configured_table_id)
            if configured_table_details:
                allowed_columns = configured_table_details.get('allowedColumns', [])
                analysis_rule = get_analysis_rule(cleanrooms, configured_table_id)
                # Debug: Print analysis rule structure for troubleshooting
                if analysis_rule:
                    if table_name in ['part_miacs_01_a', 'part_miacs_02_a']:
                        print(f"   [DEBUG] {table_name} analysis_rule keys: {list(analysis_rule.keys())}")
                        if 'policy' in analysis_rule:
                            print(f"   [DEBUG] {table_name} analysis_rule['policy'] keys: {list(analysis_rule['policy'].keys())}")
                            if 'v1' in analysis_rule['policy']:
                                print(f"   [DEBUG] {table_name} analysis_rule['policy']['v1'] keys: {list(analysis_rule['policy']['v1'].keys())}")
                                if 'custom' in analysis_rule['policy']['v1']:
                                    custom = analysis_rule['policy']['v1']['custom']
                                    print(f"   [DEBUG] {table_name} custom keys: {list(custom.keys())}")
                                    print(f"   [DEBUG] {table_name} allowedAnalysisProviders: {custom.get('allowedAnalysisProviders', 'NOT FOUND')}")
        
        # Get association info
        association_name = f"acx_{table_name}"
        association = association_map.get(association_name)
        association_id = None
        association_details = None
        collaboration_rule = None
        
        if association:
            association_id = association['id']
            association_details = get_association_details(cleanrooms, args.membership_id, association_id)
            if association_details:
                collaboration_rule = get_collaboration_analysis_rule(
                    cleanrooms, args.membership_id, association_id
                )
        
        # Get schema-level result receivers (Results delivery - Direct querying)
        # This comes from the schema analysis rule, not the collaboration rule
        # Try to find the schema name from the schema_map, or try common variations
        schema_result_receivers = []
        if collaboration_id and collaboration_id != 'N/A':
            # Try to find schema in the schema_map first
            schema_name = None
            if table_name in schema_map:
                schema_name = table_name
            elif association_name in schema_map:
                schema_name = association_name
            else:
                # Try common variations
                for possible_name in [table_name, association_name, f"acx_{table_name}"]:
                    if possible_name in schema_map:
                        schema_name = possible_name
                        break
            
            # If we found a schema name, try to get the analysis rule
            if schema_name:
                schema_result_receivers = get_schema_result_receivers(
                    cleanrooms,
                    collaboration_id,
                    schema_name
                )
            else:
                # Fallback: try both table name and association name
                for try_name in [association_name, table_name]:
                    if try_name:
                        schema_result_receivers = get_schema_result_receivers(
                            cleanrooms,
                            collaboration_id,
                            try_name
                        )
                        if schema_result_receivers:
                            break
        
        # Extract account IDs from membership ARNs if needed
        # ARN format: arn:aws:cleanrooms:region:account:membership/membership-id/configuredtableassociation/assoc-id
        # OR: just account IDs (12-digit numbers)
        result_receivers = []
        for receiver in schema_result_receivers:
            if isinstance(receiver, str):
                # Check if it's an ARN
                if receiver.startswith('arn:aws:cleanrooms:'):
                    # Extract account ID from ARN (5th component)
                    parts = receiver.split(':')
                    if len(parts) >= 5:
                        account_id = parts[4]  # Account ID is the 5th component
                        result_receivers.append(account_id)
                    else:
                        print(f"   [DEBUG] Could not parse ARN: {receiver}")
                # Check if it's already an account ID (12 digits)
                elif receiver.isdigit() and len(receiver) == 12:
                    result_receivers.append(receiver)
                else:
                    print(f"   [DEBUG] Unknown result receiver format: {receiver}")
            else:
                result_receivers.append(str(receiver))
        
        # Debug: Print for first few tables
        if table_name in ['part_miacs_01_a', 'part_miacs_02_a', 'part_ibe_01']:
            print(f"   [DEBUG] {table_name} schema_result_receivers: {schema_result_receivers}")
            print(f"   [DEBUG] {table_name} extracted result_receivers: {result_receivers}")
        
        # Extract analysis providers from configured table analysis rule
        # Structure: analysisRule['policy']['v1']['custom']['allowedAnalysisProviders']
        analysis_providers = []
        if analysis_rule:
            try:
                policy = analysis_rule.get('policy', {})
                v1 = policy.get('v1', {})
                custom_cfg = v1.get('custom')
                if custom_cfg:
                    analysis_providers = custom_cfg.get('allowedAnalysisProviders', []) or []
            except (KeyError, TypeError) as e:
                print(f"   ⚠️  Error extracting analysis providers for {table_name}: {e}")
                analysis_providers = []
        
        # Debug: Print for first few tables
        if table_name in ['part_miacs_01_a', 'part_miacs_02_a', 'part_ibe_01']:
            print(f"   [DEBUG] {table_name} analysis_providers: {analysis_providers}")
            print(f"   [DEBUG] {table_name} result_receivers: {result_receivers}")
            if collaboration_rule:
                print(f"   [DEBUG] {table_name} collaboration_rule keys: {list(collaboration_rule.keys())}")
                if 'policy' in collaboration_rule:
                    print(f"   [DEBUG] {table_name} collaboration_rule['policy'] keys: {list(collaboration_rule['policy'].keys())}")
        
        # Build table entry
        table_entry = {
            'table_name': table_name,
            'glue_table': {
                'exists': True,
                'location': location,
                'column_count': len(columns),
                'partition_keys': [pk['Name'] for pk in partition_keys],
                'columns': [col['Name'] for col in columns]
            },
            'configured_table': {
                'exists': configured_table is not None,
                'id': configured_table_id,
                'name': configured_table['name'] if configured_table else None,
                'allowed_columns_count': len(allowed_columns),
                'allowed_columns': allowed_columns,
                'analysis_method': configured_table_details.get('analysisMethod', 'N/A') if configured_table_details else 'N/A'
            },
            'analysis_rule': {
                'exists': analysis_rule is not None,
                'type': 'CUSTOM' if analysis_rule else None,
                'allowed_analysis_providers': analysis_providers
            },
            'association': {
                'exists': association is not None,
                'name': association['name'] if association else None
            },
            'collaboration_analysis_rule': {
                'exists': collaboration_rule is not None,
                'type': 'CUSTOM' if collaboration_rule else None,
                'allowed_result_receivers': result_receivers
            },
            'status': {
                'in_collaboration': association is not None,
                'ready_for_analysis': (
                    configured_table is not None and
                    analysis_rule is not None and
                    association is not None and
                    len(analysis_providers) > 0  # Must have at least one analysis provider
                )
            }
        }
        
        report_data['tables'].append(table_entry)
    
    # Sort tables by association_exists (Yes first, then No), then by table_name
    report_data['tables'].sort(key=lambda x: (
        not x['association']['exists'],  # False (Yes) comes before True (No)
        x['table_name']
    ))
    
    return report_data

def write_json_report(s3, bucket, key, data):
    """Write JSON report to S3."""
    body = json.dumps(data, indent=2).encode()
    s3.put_object(Bucket=bucket, Key=key, Body=body)
    print(f"✅ JSON report written: s3://{bucket}/{key}")

def write_csv_report(s3, bucket, key, data):
    """Write CSV reports to S3 - creates two files: tables and identity resolution."""
    print(f"[DEBUG] Writing CSV reports. Tables count: {len(data.get('tables', []))}")
    ir_data = data.get('identity_resolution', {})
    print(f"[DEBUG] Identity Resolution - ID namespace associations: {len(ir_data.get('id_namespace_associations', []))}")
    print(f"[DEBUG] Identity Resolution - ID mapping tables: {len(ir_data.get('id_mapping_tables', []))}")
    print(f"[DEBUG] Identity Resolution - ER namespaces: {len(ir_data.get('entity_resolution_namespaces', []))}")
    print(f"[DEBUG] Identity Resolution - Schema mappings: {len(ir_data.get('schema_mappings', []))}")
    
    # Debug: Print first ID namespace association if exists
    if ir_data.get('id_namespace_associations'):
        print(f"[DEBUG] First ID namespace association: {ir_data['id_namespace_associations'][0]}")
    
    # CSV 1: Configured Tables and Associations
    tables_csv = io.StringIO()
    tables_fieldnames = [
        'collaboration_name',
        'table_name',
        'glue_exists',
        'glue_column_count',
        'glue_partition_keys',
        'configured_table_exists',
        'configured_table_id',
        'configured_table_name',
        'allowed_columns_count',
        'analysis_method',
        'analysis_rule_exists',
        'Allowed Analyses for Query',
        'association_exists',
        'association_name',
        'collaboration_rule_exists',
        'in_collaboration',
        'ready_for_analysis'
    ]
    
    tables_writer = csv.DictWriter(tables_csv, fieldnames=tables_fieldnames)
    tables_writer.writeheader()
    
    # Account descriptions mapping
    account_descriptions = {
        '657425294073': 'Query Submitter/AMC Results Receiver',
        '921290734397': 'AMC Service',
        '803109464991': 'Advertiser'
    }
    
    def format_accounts_with_descriptions(account_ids):
        """Format account IDs with descriptions."""
        if not account_ids or not isinstance(account_ids, list):
            return 'N/A'
        formatted = []
        for account_id in account_ids:
            desc = account_descriptions.get(account_id, '')
            if desc:
                # Format: 6574-2529-4073 (Query Submitter/AMC Results Receiver)
                formatted_id = f"{account_id[:4]}-{account_id[4:8]}-{account_id[8:]}"
                formatted.append(f"{formatted_id} ({desc})")
            else:
                formatted.append(account_id)
        return ', '.join(formatted)
    
    tables_list = data.get('tables', [])
    print(f"[DEBUG] Processing {len(tables_list)} tables for CSV")
    
    for table in tables_list:
        # Ensure analysis_providers is always a list
        analysis_providers = table['analysis_rule'].get('allowed_analysis_providers', [])
        if not isinstance(analysis_providers, list):
            analysis_providers = []
        
        # Get result receivers
        result_receivers = table['collaboration_analysis_rule'].get('allowed_result_receivers', [])
        if not isinstance(result_receivers, list):
            result_receivers = []
        
        collaboration_name = data.get('collaboration_name', 'N/A')
        row = {
            'collaboration_name': collaboration_name,
            'table_name': table['table_name'],
            'glue_exists': 'Yes' if table['glue_table']['exists'] else 'No',
            'glue_column_count': table['glue_table']['column_count'],
            'glue_partition_keys': ', '.join(table['glue_table']['partition_keys']),
            'configured_table_exists': 'Yes' if table['configured_table']['exists'] else 'No',
            'configured_table_id': table['configured_table']['id'] or 'N/A',
            'configured_table_name': table['configured_table']['name'] or 'N/A',
            'allowed_columns_count': table['configured_table']['allowed_columns_count'],
            'analysis_method': table['configured_table']['analysis_method'],
            'analysis_rule_exists': 'Yes' if table['analysis_rule']['exists'] else 'No',
            'Allowed Analyses for Query': format_accounts_with_descriptions(analysis_providers),
            'association_exists': 'Yes' if table['association']['exists'] else 'No',
            'association_name': table['association']['name'] or 'N/A',
            'collaboration_rule_exists': 'Yes' if table['collaboration_analysis_rule']['exists'] else 'No',
            'in_collaboration': 'Yes' if table['status']['in_collaboration'] else 'No',
            'ready_for_analysis': 'Yes' if table['status']['ready_for_analysis'] else 'No'
        }
        tables_writer.writerow(row)
    
    # Write tables CSV
    # Extract prefix and build filename with collaboration name and date
    prefix = '/'.join(key.split('/')[:-1]) + '/' if '/' in key else ''
    filename = key.split('/')[-1] if '/' in key else key
    
    # Extract date from filename or use current date
    import re
    date_match = re.search(r'_(\d{8})\.csv$', filename)
    if date_match:
        date_str = date_match.group(1)
    else:
        date_str = datetime.utcnow().strftime('%Y%m%d')
    
    collaboration_name = data.get('collaboration_name', 'N/A')
    if collaboration_name and collaboration_name != 'N/A':
        # Sanitize collaboration name for filename (remove special chars, spaces)
        safe_collab_name = ''.join(c if c.isalnum() or c in ('-', '_') else '_' for c in collaboration_name)
        tables_key = f"{prefix}ACX_Cleanroom_Report_{safe_collab_name}_{date_str}_Tables.csv"
    else:
        # Use "na" in filename when collaboration name is N/A
        tables_key = f"{prefix}ACX_Cleanroom_Report_na_{date_str}_Tables.csv"
    
    s3.put_object(Bucket=bucket, Key=tables_key, Body=tables_csv.getvalue().encode())
    print(f"✅ Tables CSV report written: s3://{bucket}/{tables_key}")
    
    # CSV 2: Identity Resolution
    ir_csv = io.StringIO()
    ir_fieldnames = [
        'collaboration_name',
        'id namespace',
        'Id namespace method',
        'source db',
        'region',
        'table',
        'schema mapping',
        'unique id',
        'input field',
        'matchkey'
    ]
    
    ir_writer = csv.DictWriter(ir_csv, fieldnames=ir_fieldnames)
    ir_writer.writeheader()
    
    ir_data = data.get('identity_resolution', {})
    # Write Identity Resolution data - combine ER namespace and schema mapping info
    for er_ns in ir_data.get('entity_resolution_namespaces', []):
        # Extract information from Entity Resolution namespace
        namespace_name = er_ns.get('name', 'N/A')
        input_source_arn = er_ns.get('input_source_arn', '')
        schema_name = er_ns.get('schema_name', 'N/A')
        
        # Extract table name and database from input source ARN
        # Format: arn:aws:glue:us-east-1:239083076653:table/omc_flywheel_prod/part_addressable_ids_er
        table_name = 'N/A'
        source_db = 'N/A'
        region = 'N/A'
        if input_source_arn and 'table' in input_source_arn:
            # Extract region from ARN (4th component)
            arn_parts = input_source_arn.split(':')
            if len(arn_parts) >= 4:
                region = arn_parts[3]  # us-east-1
            
            # Extract database and table from ARN path
            path_parts = input_source_arn.split('/')
            if len(path_parts) >= 2:
                source_db = path_parts[-2]  # omc_flywheel_prod
                table_name = path_parts[-1]  # part_addressable_ids_er
        
        # Get namespace method from ID mapping config
        namespace_method = 'N/A'
        id_mapping_config = er_ns.get('id_mapping_config', {})
        if isinstance(id_mapping_config, dict) and id_mapping_config:
            id_mapping_type = id_mapping_config.get('idMappingType', '')
            if id_mapping_type:
                namespace_method = id_mapping_type.lower().replace('_', '-')
        
        # Default to 'rule-based' if we have the namespace but no explicit method
        if namespace_method == 'N/A' and namespace_name != 'N/A':
            namespace_method = 'rule-based'
        
        # Get unique id and input field/matchkey from schema mapping
        unique_id = 'N/A'
        input_field = 'N/A'
        matchkey = 'N/A'
        
        # Find matching schema mapping
        schema_mappings_list = ir_data.get('schema_mappings', [])
        for schema_mapping in schema_mappings_list:
            # Schema mapping is stored with 'name' key (from schemaName)
            sm_name = schema_mapping.get('name', '')
            if sm_name == schema_name or sm_name.upper() == schema_name.upper():
                # Look for UNIQUE_ID field and ID/STRING field with matchKey
                mapped_fields = schema_mapping.get('mappedInputFields', [])
                for field in mapped_fields:
                    field_name = field.get('fieldName', '')
                    field_type = field.get('type', '')
                    match_key = field.get('matchKey', '') or field.get('matchingKey', '')
                    
                    # Get unique id (usually row_id)
                    if field_type == 'UNIQUE_ID':
                        unique_id = field_name
                    
                    # Get input field with matchkey (ID or STRING type with matchKey)
                    if match_key and (field_type == 'ID' or field_type == 'STRING'):
                        input_field = field_name
                        matchkey = match_key
                
                break
        
        collaboration_name = data.get('collaboration_name', 'N/A')
        row_data = {
            'collaboration_name': collaboration_name,
            'id namespace': namespace_name,
            'Id namespace method': namespace_method,
            'source db': source_db,
            'region': region,
            'table': table_name,
            'schema mapping': schema_name.lower() if schema_name != 'N/A' else 'N/A',  # Convert ACX_SCHEMA to acx_schema
            'unique id': unique_id,
            'input field': input_field,
            'matchkey': matchkey
        }
        ir_writer.writerow(row_data)
    
    # Write identity resolution CSV
    # Replace the base filename with IdentityResolution suffix
    # Write Identity Resolution CSV
    # Use same prefix and naming pattern as tables CSV
    prefix = '/'.join(key.split('/')[:-1]) + '/' if '/' in key else ''
    filename = key.split('/')[-1] if '/' in key else key
    
    # Extract date from filename or use current date
    date_match = re.search(r'_(\d{8})\.csv$', filename)
    if date_match:
        date_str = date_match.group(1)
    else:
        date_str = datetime.utcnow().strftime('%Y%m%d')
    
    collaboration_name = data.get('collaboration_name', 'N/A')
    if collaboration_name and collaboration_name != 'N/A':
        # Sanitize collaboration name for filename
        safe_collab_name = ''.join(c if c.isalnum() or c in ('-', '_') else '_' for c in collaboration_name)
        ir_key = f"{prefix}ACX_Cleanroom_Report_{safe_collab_name}_{date_str}_IdentityResolution.csv"
    else:
        # Use "na" in filename when collaboration name is N/A
        ir_key = f"{prefix}ACX_Cleanroom_Report_na_{date_str}_IdentityResolution.csv"
    
    s3.put_object(Bucket=bucket, Key=ir_key, Body=ir_csv.getvalue().encode())
    print(f"✅ Identity Resolution CSV report written: s3://{bucket}/{ir_key}")

def main():
    # Debug: Print all command-line arguments
    print(f"[DEBUG] sys.argv: {sys.argv}")
    
    try:
        args = parse_args()
    except SystemExit as e:
        print(f"[DEBUG] argparse SystemExit: code={e.code}")
        raise
    
    # Debug: Print parsed arguments
    print(f"[DEBUG] Parsed arguments:")
    print(f"  --profile: '{args.profile}'")
    print(f"  --region: '{args.region}'")
    print(f"  --database: '{args.database}'")
    print(f"  --table-prefix: '{args.table_prefix}'")
    print(f"  --membership-id: '{args.membership_id}'")
    print(f"  --report-bucket: '{args.report_bucket}'")
    print(f"  --report-prefix: '{args.report_prefix}'")
    print(f"  --output-format: '{args.output_format}'")
    
    # Validate required arguments
    if not args.report_bucket or not args.report_bucket.strip():
        print("❌ ERROR: --report-bucket is required and cannot be empty")
        print("Please provide a valid S3 bucket name for report output")
        sys.exit(2)
    
    # Setup boto3 clients
    config = Config()
    if args.no_verify_ssl:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        import ssl
        import os
        os.environ['PYTHONHTTPSVERIFY'] = '0'
        ssl._create_default_https_context = ssl._create_unverified_context
    
    # Use profile if provided and not empty, otherwise use default credentials (for Glue execution)
    # Handle case where --profile is passed as empty string from Glue
    profile_value = args.profile.strip() if args.profile else ''
    if profile_value:
        session = boto3.Session(profile_name=profile_value)
    else:
        session = boto3.Session()  # Uses IAM role in Glue
    
    glue = session.client('glue', region_name=args.region, config=config)
    cleanrooms = session.client('cleanrooms', region_name=args.region, config=config)
    entity_resolution = session.client('entityresolution', region_name=args.region, config=config)
    s3 = session.client('s3', region_name=args.region, config=config)
    
    # Generate report
    report_data = generate_report(glue, cleanrooms, entity_resolution, args)
    
    # Write reports
    date_str = datetime.utcnow().strftime('%Y%m%d')
    prefix = args.report_prefix.rstrip('/') + '/'
    
    # Get collaboration name for filename
    collaboration_name = report_data.get('collaboration_name', 'N/A')
    if collaboration_name and collaboration_name != 'N/A':
        # Sanitize collaboration name for filename (remove special chars, spaces)
        safe_collab_name = ''.join(c if c.isalnum() or c in ('-', '_') else '_' for c in collaboration_name)
        file_suffix = f"{safe_collab_name}_{date_str}"
    else:
        # Use "na" in filename when collaboration name is N/A
        file_suffix = f"na_{date_str}"
    
    if args.output_format in ('json', 'both'):
        json_key = f"{prefix}ACX_Cleanroom_Report_{file_suffix}.json"
        write_json_report(s3, args.report_bucket, json_key, report_data)
    
    if args.output_format in ('csv', 'both'):
        csv_key = f"{prefix}ACX_Cleanroom_Report_{file_suffix}.csv"
        write_csv_report(s3, args.report_bucket, csv_key, report_data)
    
    # Print summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Collaboration Name: {report_data.get('collaboration_name', 'N/A')}")
    print(f"Collaboration ID: {report_data.get('collaboration_id', 'N/A')}")
    print(f"Membership ID: {report_data.get('membership_id', 'N/A')}")
    print(f"Glue Tables: {report_data['summary']['glue_tables_count']}")
    print(f"Configured Tables: {report_data['summary']['configured_tables_count']}")
    print(f"Associations: {report_data['summary']['associations_count']}")
    print(f"ID Namespace Associations: {report_data['summary']['id_namespace_associations_count']}")
    print(f"ID Mapping Tables: {report_data['summary']['id_mapping_tables_count']}")
    print(f"Entity Resolution Namespaces: {report_data['summary']['entity_resolution_namespaces_count']}")
    
    ready_count = sum(1 for t in report_data['tables'] if t['status']['ready_for_analysis'])
    print(f"Ready for Analysis: {ready_count}/{len(report_data['tables'])}")
    print()
    
    # Print Identity Resolution summary
    if report_data['identity_resolution']['id_namespace_associations']:
        print("Identity Resolution Service Resources:")
        for ns_assoc in report_data['identity_resolution']['id_namespace_associations']:
            print(f"  - ID Namespace Association: {ns_assoc['name']} ({ns_assoc['id']})")
            if ns_assoc['entity_resolution_namespace_arn']:
                print(f"    Entity Resolution Namespace: {ns_assoc['entity_resolution_namespace_arn']}")
        print()
    
    if report_data['identity_resolution']['id_mapping_tables']:
        for table in report_data['identity_resolution']['id_mapping_tables']:
            print(f"  - ID Mapping Table: {table['name']} ({table['id']})")
        print()
    
    # Print tables not ready
    not_ready = [t for t in report_data['tables'] if not t['status']['ready_for_analysis']]
    if not_ready:
        print("Tables NOT ready for analysis:")
        for table in not_ready:
            issues = []
            if not table['configured_table']['exists']:
                issues.append('Missing configured table')
            if not table['analysis_rule']['exists']:
                issues.append('Missing analysis rule')
            if not table['association']['exists']:
                issues.append('Not in collaboration')
            if not table['collaboration_analysis_rule']['exists']:
                issues.append('Missing collaboration rule')
            print(f"  - {table['table_name']}: {', '.join(issues)}")
    
    print()
    print("✅ Report generation complete!")

if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:
        # Re-raise SystemExit (from argparse) but with better error message
        if e.code == 2:
            print("\n❌ ERROR: Missing required arguments or invalid argument values")
            print("Required arguments:")
            print("  --report-bucket: S3 bucket for report output")
            print("\nExample usage:")
            print("  python generate-cleanrooms-report.py --report-bucket my-bucket")
        raise
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

