#!/usr/bin/env python3
"""
Create AWS Cleanrooms Identity Resolution Service Resources

This script creates ID namespace associations and ID mapping tables
for Cleanrooms using boto3, since Terraform AWS provider doesn't support
Cleanrooms Identity Resolution Service resources yet.
"""

import boto3
import json
import argparse
import urllib3
from typing import List, Dict, Optional
from botocore.exceptions import ClientError
from botocore.config import Config

# Default configuration
DEFAULT_REGION = "us-east-1"
DEFAULT_MEMBERSHIP_ID = "6610c9aa-9002-475c-8695-d833485741bc"


def get_existing_id_namespace_association(cleanrooms_client, membership_id: str, name: str) -> Optional[str]:
    """Check if an ID namespace association already exists and return its ID."""
    try:
        associations = cleanrooms_client.list_id_namespace_associations(membershipIdentifier=membership_id)
        for assoc in associations.get('idNamespaceAssociationSummaries', []):
            if assoc.get('name') == name:
                return assoc.get('id')
        return None
    except Exception as e:
        print(f"⚠️  Error checking for existing ID namespace association {name}: {e}")
        return None


def create_id_namespace_association(
    cleanrooms_client,
    membership_id: str,
    name: str,
    id_namespace_arn: str,
    description: str = "",
    manage_resource_policies: bool = True,
    allow_use_as_dimension_column: bool = False
) -> str:
    """Create an ID namespace association (only if it doesn't exist)."""
    # Check if already exists
    existing_id = get_existing_id_namespace_association(cleanrooms_client, membership_id, name)
    if existing_id:
        print(f"✅ ID namespace association {name} already exists (ID: {existing_id}), skipping creation")
        return existing_id
    
    try:
        response = cleanrooms_client.create_id_namespace_association(
            membershipIdentifier=membership_id,
            name=name,
            description=description,
            inputReferenceConfig={
                "inputReferenceArn": id_namespace_arn,
                "manageResourcePolicies": manage_resource_policies
            },
            idMappingConfig={
                "allowUseAsDimensionColumn": allow_use_as_dimension_column
            }
        )
        assoc_id = response['idNamespaceAssociation']['id']
        print(f"✅ Created ID namespace association: {name} (ID: {assoc_id})")
        return assoc_id
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConflictException':
            # Association was created between check and create, get its ID
            existing_id = get_existing_id_namespace_association(cleanrooms_client, membership_id, name)
            if existing_id:
                print(f"✅ Found existing ID namespace association: {name} (ID: {existing_id})")
                return existing_id
            raise Exception(f"Association {name} exists but couldn't find its ID")
        else:
            print(f"❌ Error creating ID namespace association {name}: {e}")
            raise


def get_existing_id_mapping_table(cleanrooms_client, membership_id: str, name: str) -> Optional[str]:
    """Check if an ID mapping table already exists and return its ID."""
    try:
        tables = cleanrooms_client.list_id_mapping_tables(membershipIdentifier=membership_id)
        for table in tables.get('idMappingTableSummaries', []):
            if table.get('name') == name:
                return table.get('id')
        return None
    except Exception as e:
        print(f"⚠️  Error checking for existing ID mapping table {name}: {e}")
        return None


def create_id_mapping_table(
    cleanrooms_client,
    membership_id: str,
    name: str,
    id_mapping_workflow_arn: str,
    input_sources: List[Dict[str, str]],
    description: str = "",
    manage_resource_policies: bool = True
) -> str:
    """Create an ID mapping table (only if it doesn't exist)."""
    # Check if already exists
    existing_id = get_existing_id_mapping_table(cleanrooms_client, membership_id, name)
    if existing_id:
        print(f"✅ ID mapping table {name} already exists (ID: {existing_id}), skipping creation")
        return existing_id
    
    try:
        # Build input reference properties
        input_reference_properties = {
            "idMappingTableInputSource": [
                {
                    "idNamespaceAssociationId": source['id_namespace_association_id'],
                    "type": source['type']
                }
                for source in input_sources
            ]
        }
        
        response = cleanrooms_client.create_id_mapping_table(
            membershipIdentifier=membership_id,
            name=name,
            description=description,
            inputReferenceConfig={
                "inputReferenceArn": id_mapping_workflow_arn,
                "manageResourcePolicies": manage_resource_policies
            },
            inputReferenceProperties=input_reference_properties
        )
        table_id = response['idMappingTable']['id']
        print(f"✅ Created ID mapping table: {name} (ID: {table_id})")
        return table_id
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConflictException':
            # Table was created between check and create, get its ID
            existing_id = get_existing_id_mapping_table(cleanrooms_client, membership_id, name)
            if existing_id:
                print(f"✅ Found existing ID mapping table: {name} (ID: {existing_id})")
                return existing_id
            raise Exception(f"Table {name} exists but couldn't find its ID")
        else:
            print(f"❌ Error creating ID mapping table {name}: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description='Create Cleanrooms Identity Resolution Service resources')
    parser.add_argument('--region', default=DEFAULT_REGION, help='AWS region')
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--membership-id', default=DEFAULT_MEMBERSHIP_ID, help='Cleanrooms membership ID')
    parser.add_argument('--id-namespace-name', default='ACXIdNamespace', help='ID namespace association name')
    parser.add_argument('--id-namespace-arn', required=True, help='Entity Resolution ID namespace ARN')
    parser.add_argument('--id-namespace-description', default='ACX unique customer identifiers for Clean Rooms joins', 
                       help='ID namespace association description')
    parser.add_argument('--manage-resource-policies', action='store_true', default=True,
                       help='Manage resource policies for ID namespace')
    parser.add_argument('--allow-use-as-dimension-column', action='store_true', default=False,
                       help='Allow ID namespace as dimension column')
    parser.add_argument('--id-mapping-table-name', help='ID mapping table name (optional)')
    parser.add_argument('--id-mapping-workflow-arn', help='Entity Resolution ID mapping workflow ARN')
    parser.add_argument('--id-mapping-table-description', default='', help='ID mapping table description')
    parser.add_argument('--source-namespace-association-id', help='Source ID namespace association ID')
    parser.add_argument('--target-namespace-association-id', help='Target ID namespace association ID')
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
    
    print(f"\n📊 Creating Identity Resolution Service resources...\n")
    
    # Create ID namespace association
    print(f"🔗 Creating ID namespace association: {args.id_namespace_name}\n")
    try:
        namespace_assoc_id = create_id_namespace_association(
            cleanrooms,
            membership_id=args.membership_id,
            name=args.id_namespace_name,
            id_namespace_arn=args.id_namespace_arn,
            description=args.id_namespace_description,
            manage_resource_policies=args.manage_resource_policies,
            allow_use_as_dimension_column=args.allow_use_as_dimension_column
        )
    except Exception as e:
        print(f"❌ Failed to create ID namespace association: {e}")
        return
    
    # Create ID mapping table if requested
    if args.id_mapping_table_name and args.id_mapping_workflow_arn:
        print(f"\n📋 Creating ID mapping table: {args.id_mapping_table_name}\n")
        
        # Build input sources
        input_sources = []
        if args.source_namespace_association_id:
            input_sources.append({
                'id_namespace_association_id': args.source_namespace_association_id,
                'type': 'SOURCE'
            })
        else:
            # Use the namespace association we just created as source
            input_sources.append({
                'id_namespace_association_id': namespace_assoc_id,
                'type': 'SOURCE'
            })
        
        if args.target_namespace_association_id:
            input_sources.append({
                'id_namespace_association_id': args.target_namespace_association_id,
                'type': 'TARGET'
            })
        
        if not input_sources:
            print("❌ Error: Must provide at least one input source (source or target namespace association ID)")
            return
        
        try:
            mapping_table_id = create_id_mapping_table(
                cleanrooms,
                membership_id=args.membership_id,
                name=args.id_mapping_table_name,
                id_mapping_workflow_arn=args.id_mapping_workflow_arn,
                input_sources=input_sources,
                description=args.id_mapping_table_description,
                manage_resource_policies=args.manage_resource_policies
            )
        except Exception as e:
            print(f"❌ Failed to create ID mapping table: {e}")
            return
    
    print(f"\n✅ Complete!")
    print(f"\n📋 Summary:")
    print(f"  ID Namespace Association: {args.id_namespace_name} (ID: {namespace_assoc_id})")
    if args.id_mapping_table_name:
        print(f"  ID Mapping Table: {args.id_mapping_table_name} (ID: {mapping_table_id})")


if __name__ == "__main__":
    main()

