#!/usr/bin/env python3
"""
Discover and Document Cleanrooms Identity Resolution Service Resources

This script discovers existing Identity Resolution Service resources in AWS
and generates Terraform import commands and configuration.
"""

import boto3
import argparse
import urllib3
import ssl
import os
import json
from botocore.exceptions import ClientError
from botocore.config import Config

# Disable SSL verification if needed
def setup_ssl_bypass():
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    os.environ['PYTHONHTTPSVERIFY'] = '0'
    ssl._create_default_https_context = ssl._create_unverified_context


def discover_resources(cleanrooms_client, entity_resolution_client, membership_id):
    """Discover all Identity Resolution Service resources."""
    results = {
        'id_namespace_associations': [],
        'id_mapping_tables': [],
        'entity_resolution_namespaces': [],
        'entity_resolution_workflows': []
    }
    
    # Get membership and collaboration
    try:
        membership = cleanrooms_client.get_membership(membershipIdentifier=membership_id)
        collaboration_id = membership['membership']['collaborationId']
        print(f'📋 Membership ID: {membership_id}')
        print(f'📋 Collaboration ID: {collaboration_id}\n')
    except Exception as e:
        print(f'❌ Error getting membership: {e}')
        return results
    
    # 1. Discover ID namespace associations
    print('1. Discovering ID Namespace Associations...')
    try:
        ns_assocs = cleanrooms_client.list_id_namespace_associations(membershipIdentifier=membership_id)
        for ns in ns_assocs.get('idNamespaceAssociationSummaries', []):
            try:
                details = cleanrooms_client.get_id_namespace_association(
                    membershipIdentifier=membership_id,
                    idNamespaceAssociationIdentifier=ns['id']
                )
                ns_data = details.get('idNamespaceAssociation', {})
                results['id_namespace_associations'].append({
                    'id': ns_data.get('id'),
                    'name': ns_data.get('name'),
                    'arn': ns_data.get('arn'),
                    'input_reference_arn': ns_data.get('inputReferenceConfig', {}).get('inputReferenceArn'),
                    'manage_resource_policies': ns_data.get('inputReferenceConfig', {}).get('manageResourcePolicies'),
                    'allow_use_as_dimension_column': ns_data.get('idMappingConfig', {}).get('allowUseAsDimensionColumn'),
                    'description': ns_data.get('description', '')
                })
                print(f'   ✅ {ns_data.get("name")}: {ns_data.get("id")}')
            except Exception as e:
                print(f'   ⚠️  Error getting details for {ns.get("id")}: {e}')
    except Exception as e:
        print(f'   ❌ Error: {e}')
    
    print()
    
    # 2. Discover ID mapping tables
    print('2. Discovering ID Mapping Tables...')
    try:
        mapping_tables = cleanrooms_client.list_id_mapping_tables(membershipIdentifier=membership_id)
        for table in mapping_tables.get('idMappingTableSummaries', []):
            try:
                details = cleanrooms_client.get_id_mapping_table(
                    membershipIdentifier=membership_id,
                    idMappingTableIdentifier=table['id']
                )
                table_data = details.get('idMappingTable', {})
                input_sources = []
                for source in table_data.get('inputReferenceProperties', {}).get('idMappingTableInputSource', []):
                    input_sources.append({
                        'id_namespace_association_id': source.get('idNamespaceAssociationId'),
                        'type': source.get('type')
                    })
                
                results['id_mapping_tables'].append({
                    'id': table_data.get('id'),
                    'name': table_data.get('name'),
                    'arn': table_data.get('arn'),
                    'input_reference_arn': table_data.get('inputReferenceConfig', {}).get('inputReferenceArn'),
                    'manage_resource_policies': table_data.get('inputReferenceConfig', {}).get('manageResourcePolicies'),
                    'input_sources': input_sources,
                    'description': table_data.get('description', '')
                })
                print(f'   ✅ {table_data.get("name")}: {table_data.get("id")}')
            except Exception as e:
                print(f'   ⚠️  Error getting details for {table.get("id")}: {e}')
    except Exception as e:
        print(f'   ❌ Error: {e}')
    
    print()
    
    # 3. Discover Entity Resolution namespaces
    print('3. Discovering Entity Resolution ID Namespaces...')
    try:
        namespaces = entity_resolution_client.list_id_namespaces()
        for ns in namespaces.get('idNamespaceSummaries', []):
            results['entity_resolution_namespaces'].append({
                'name': ns.get('idNamespaceName'),
                'arn': ns.get('idNamespaceArn')
            })
            print(f'   ✅ {ns.get("idNamespaceName")}: {ns.get("idNamespaceArn")}')
    except Exception as e:
        print(f'   ❌ Error: {e}')
    
    print()
    
    # 4. Discover Entity Resolution workflows
    print('4. Discovering Entity Resolution ID Mapping Workflows...')
    try:
        workflows = entity_resolution_client.list_id_mapping_workflows()
        for wf in workflows.get('workflowSummaries', []):
            results['entity_resolution_workflows'].append({
                'name': wf.get('workflowName'),
                'arn': wf.get('workflowArn')
            })
            print(f'   ✅ {wf.get("workflowName")}: {wf.get("workflowArn")}')
    except Exception as e:
        print(f'   ❌ Error: {e}')
    
    return results


def generate_terraform_imports(results, membership_id):
    """Generate Terraform import commands."""
    print('\n' + '=' * 60)
    print('TERRAFORM IMPORT COMMANDS')
    print('=' * 60)
    print()
    
    print('# ID Namespace Associations:')
    for ns in results['id_namespace_associations']:
        print(f'terraform import module.cr_namespace.aws_cleanrooms_id_namespace_association.namespace \\')
        print(f'  membership/{membership_id}/idnamespaceassociation/{ns["id"]}')
        print()
    
    print('# ID Mapping Tables:')
    for i, table in enumerate(results['id_mapping_tables']):
        print(f'terraform import module.cr_namespace.aws_cleanrooms_id_mapping_table.mapping_table[{i}] \\')
        print(f'  membership/{membership_id}/idmappingtable/{table["id"]}')
        print()


def generate_terraform_config(results):
    """Generate Terraform configuration snippet."""
    print('\n' + '=' * 60)
    print('TERRAFORM CONFIGURATION SNIPPET')
    print('=' * 60)
    print()
    
    if results['id_namespace_associations']:
        ns = results['id_namespace_associations'][0]
        print('# ID Namespace Association Configuration:')
        print(f'id_namespace_name = "{ns["name"]}"')
        print(f'id_namespace_arn  = "{ns["input_reference_arn"]}"')
        print(f'manage_resource_policies = {str(ns["manage_resource_policies"]).lower()}')
        print(f'allow_use_as_dimension_column = {str(ns["allow_use_as_dimension_column"]).lower()}')
        print()
    
    if results['id_mapping_tables']:
        table = results['id_mapping_tables'][0]
        print('# ID Mapping Table Configuration:')
        print(f'id_mapping_table_name = "{table["name"]}"')
        print(f'id_mapping_workflow_arn = "{table["input_reference_arn"]}"')
        print()
        print('# Input Sources:')
        for source in table['input_sources']:
            print(f'#   - {source["type"]}: {source["id_namespace_association_id"]}')
        print()


def main():
    parser = argparse.ArgumentParser(description='Discover Cleanrooms Identity Resolution Service resources')
    parser.add_argument('--membership-id', required=True, help='Cleanrooms membership ID')
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--no-verify-ssl', action='store_true', help='Disable SSL certificate verification')
    parser.add_argument('--output-json', help='Output results to JSON file')
    
    args = parser.parse_args()
    
    # Configure SSL if needed
    if args.no_verify_ssl:
        setup_ssl_bypass()
        config = Config(connect_timeout=60, read_timeout=60)
    else:
        config = Config()
    
    # Create AWS clients
    session = boto3.Session(profile_name=args.profile) if args.profile else boto3.Session()
    cleanrooms = session.client('cleanrooms', region_name=args.region, config=config, verify=not args.no_verify_ssl)
    
    # Try to create Entity Resolution client
    try:
        entity_resolution = session.client('entityresolution', region_name=args.region, config=config, verify=not args.no_verify_ssl)
    except Exception as e:
        print(f'⚠️  Entity Resolution client not available: {e}')
        entity_resolution = None
    
    # Discover resources
    results = discover_resources(cleanrooms, entity_resolution, args.membership_id)
    
    # Generate outputs
    generate_terraform_imports(results, args.membership_id)
    generate_terraform_config(results)
    
    # Output JSON if requested
    if args.output_json:
        with open(args.output_json, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f'\n✅ Results saved to {args.output_json}')


if __name__ == "__main__":
    main()

