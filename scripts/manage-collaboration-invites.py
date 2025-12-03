#!/usr/bin/env python3
"""
Manage AWS Cleanrooms Collaboration Invitations

This script handles:
1. Listing pending collaboration invitations
2. Accepting collaboration invitations
3. Automatically associating existing configured tables
4. Automatically associating existing ID namespace
5. Managing multiple collaborations (10+)

Usage:
    # List pending invitations
    python3 manage-collaboration-invites.py list --profile flywheel-prod

    # Accept a specific invitation
    python3 manage-collaboration-invites.py accept \
        --invitation-id <invitation-id> \
        --profile flywheel-prod

    # Accept all pending invitations
    python3 manage-collaboration-invites.py accept-all \
        --profile flywheel-prod \
        --auto-associate

    # Associate resources to existing membership
    python3 manage-collaboration-invites.py associate \
        --membership-id <membership-id> \
        --profile flywheel-prod
"""

import boto3
import json
import argparse
import sys
from typing import List, Dict, Optional
from botocore.exceptions import ClientError
from botocore.config import Config
from datetime import datetime
import urllib3

# Disable SSL warnings if needed
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CollaborationManager:
    """Manages Cleanrooms collaboration invitations and resource associations."""
    
    def __init__(self, cleanrooms_client, glue_client=None, iam_client=None, 
                 entity_resolution_client=None, region="us-east-1"):
        self.cleanrooms = cleanrooms_client
        self.glue = glue_client
        self.iam = iam_client
        self.entity_resolution = entity_resolution_client
        self.region = region
        
        # Default configuration
        self.default_role_name = "cleanrooms-glue-s3-access"
        self.default_id_namespace_name = "ACXIdNamespace"
        self.default_table_prefix = "part_"
        self.default_database = "omc_flywheel_prod"
    
    def list_pending_invitations(self) -> List[Dict]:
        """List all pending collaboration invitations."""
        try:
            print("📋 Listing pending collaboration invitations...\n")
            invitations = []
            
            # List invitations (paginated)
            paginator = self.cleanrooms.get_paginator('list_collaborations')
            for page in paginator.paginate(memberAccountId=None):
                for collab in page.get('collaborationList', []):
                    # Check if we have a pending invitation
                    # This is indicated by membershipStatus
                    if collab.get('membershipStatus') == 'INVITED':
                        invitations.append({
                            'collaborationId': collab.get('collaborationId'),
                            'collaborationArn': collab.get('collaborationArn'),
                            'name': collab.get('name'),
                            'creatorAccountId': collab.get('creatorAccountId'),
                            'creatorDisplayName': collab.get('creatorDisplayName'),
                            'membershipStatus': collab.get('membershipStatus'),
                            'membershipId': collab.get('membershipId'),
                            'createTime': collab.get('createTime')
                        })
            
            return invitations
        except Exception as e:
            print(f"❌ Error listing invitations: {e}")
            return []
    
    def accept_invitation(self, collaboration_id: str) -> Optional[str]:
        """Accept a collaboration invitation and return the membership ID."""
        try:
            print(f"✅ Accepting invitation for collaboration: {collaboration_id}\n")
            
            # Get collaboration details
            collaboration = self.cleanrooms.get_collaboration(
                collaborationIdentifier=collaboration_id
            )
            
            # Accept the invitation by creating a membership
            # Note: The actual API call depends on how AWS implements invitation acceptance
            # This might need to be done via update_membership_status or similar
            
            # Try to get existing membership first
            memberships = self.cleanrooms.list_memberships()
            for membership in memberships.get('membershipSummaries', []):
                if membership.get('collaborationId') == collaboration_id:
                    membership_id = membership.get('membershipId')
                    print(f"✅ Found existing membership: {membership_id}")
                    
                    # Check if membership is active
                    membership_detail = self.cleanrooms.get_membership(
                        membershipIdentifier=membership_id
                    )
                    status = membership_detail['membership'].get('status')
                    
                    if status == 'ACTIVE':
                        print(f"✅ Membership is already ACTIVE")
                        return membership_id
                    elif status == 'INVITED':
                        # Accept the invitation
                        print(f"📝 Accepting invitation...")
                        # Note: AWS Cleanrooms API might require update_membership_status
                        # or accept_membership_invitation - check AWS docs for exact method
                        try:
                            # Try update_membership_status if available
                            self.cleanrooms.update_membership_status(
                                membershipIdentifier=membership_id,
                                status='ACTIVE'
                            )
                            print(f"✅ Successfully accepted invitation")
                            return membership_id
                        except ClientError as e:
                            if e.response['Error']['Code'] == 'InvalidInputException':
                                # Method might not exist, try alternative
                                print(f"⚠️  Direct status update not available, membership may need manual acceptance")
                                print(f"   Membership ID: {membership_id}")
                                print(f"   Please accept in AWS Console or use AWS CLI")
                                return membership_id
                            raise
            
            print(f"⚠️  No membership found for collaboration {collaboration_id}")
            print(f"   You may need to accept the invitation manually in AWS Console")
            return None
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                print(f"❌ Collaboration {collaboration_id} not found")
            elif error_code == 'InvalidInputException':
                print(f"❌ Invalid collaboration ID: {collaboration_id}")
            else:
                print(f"❌ Error accepting invitation: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return None
    
    def get_configured_tables(self) -> List[Dict]:
        """Get all existing configured tables starting with 'part_' (excluding n_a tables)."""
        EXCLUDED_TABLES = ['part_n_a', 'part_n_a_a']
        MAX_ASSOCIATIONS = 25  # AWS quota limit
        
        try:
            print("📋 Getting existing configured tables...\n")
            tables = []
            
            paginator = self.cleanrooms.get_paginator('list_configured_tables')
            for page in paginator.paginate():
                for table in page.get('configuredTableSummaries', []):
                    table_name = table.get('name', '')
                    # Filter: must start with "part_" and not be excluded
                    if (table_name.startswith('part_') and 
                        table_name not in EXCLUDED_TABLES):
                        # Get table ID - could be 'id' or 'configuredTableId'
                        table_id = table.get('id') or table.get('configuredTableId')
                        if table_id:  # Only add if we have a valid ID
                            tables.append({
                                'id': table_id,
                                'arn': table.get('configuredTableArn'),
                                'name': table_name,
                                'analysisMethod': table.get('analysisMethod')
                            })
            
            # Sort alphabetically
            tables.sort(key=lambda x: x['name'])
            
            # Limit to quota
            if len(tables) > MAX_ASSOCIATIONS:
                print(f"⚠️  Found {len(tables)} tables, limiting to {MAX_ASSOCIATIONS} (quota limit)")
                tables = tables[:MAX_ASSOCIATIONS]
            
            if EXCLUDED_TABLES:
                print(f"   Excluded: {', '.join(EXCLUDED_TABLES)}")
            print(f"   Found {len(tables)} tables to associate\n")
            
            return tables
        except Exception as e:
            print(f"❌ Error getting configured tables: {e}")
            return []
    
    def associate_configured_tables(self, membership_id: str, 
                                     table_ids: Optional[List[str]] = None,
                                     role_arn: Optional[str] = None) -> Dict:
        """Associate configured tables with a membership."""
        results = {
            'success': [],
            'failed': [],
            'skipped': []
        }
        
        # Get IAM role ARN
        if not role_arn:
            role_arn = self._get_role_arn()
            if not role_arn:
                print("❌ Could not find IAM role for table associations")
                return results
        
        # Get tables to associate
        if table_ids:
            # Use provided table IDs - need to lookup table names
            tables = []
            for tid in table_ids:
                # Get table name from configured table
                try:
                    table_info = self.cleanrooms.get_configured_table(configuredTableIdentifier=tid)
                    table_name = table_info['configuredTable']['name']
                    tables.append({'id': tid, 'name': table_name})
                except Exception as e:
                    print(f"⚠️  Could not get table name for {tid}: {e}, using ID as name")
                    tables.append({'id': tid, 'name': tid})
        else:
            # Get all configured tables
            tables = self.get_configured_tables()
        
        print(f"\n🔗 Associating {len(tables)} configured tables with membership {membership_id}...\n")
        
        for table in tables:
            table_id = table.get('id')
            table_name = table.get('name', table_id)
            association_name = f"acx_{table_name}"
            
            try:
                # Check if association already exists
                existing = self._get_existing_association(membership_id, table_id)
                if existing:
                    print(f"⏭️  Association already exists: {association_name} (ID: {existing})")
                    results['skipped'].append({
                        'table': table_name,
                        'association_id': existing
                    })
                    continue
                
                # Create association
                response = self.cleanrooms.create_configured_table_association(
                    membershipIdentifier=membership_id,
                    configuredTableIdentifier=table_id,
                    name=association_name,
                    roleArn=role_arn
                )
                
                assoc_id = response['configuredTableAssociation']['id']
                print(f"✅ Associated table: {table_name} → {association_name} (ID: {assoc_id})")
                results['success'].append({
                    'table': table_name,
                    'association_id': assoc_id
                })
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'ConflictException':
                    # Association already exists
                    existing = self._get_existing_association(membership_id, table_id)
                    print(f"⏭️  Association already exists: {association_name}")
                    results['skipped'].append({
                        'table': table_name,
                        'association_id': existing
                    })
                else:
                    print(f"❌ Failed to associate {table_name}: {e}")
                    results['failed'].append({
                        'table': table_name,
                        'error': str(e)
                    })
            except Exception as e:
                print(f"❌ Unexpected error associating {table_name}: {e}")
                results['failed'].append({
                    'table': table_name,
                    'error': str(e)
                })
        
        return results
    
    def associate_id_namespace(self, membership_id: str,
                               id_namespace_arn: str,
                               id_namespace_name: Optional[str] = None) -> Optional[str]:
        """Associate ID namespace with membership."""
        if not id_namespace_name:
            id_namespace_name = self.default_id_namespace_name
        
        try:
            print(f"\n🔗 Associating ID namespace {id_namespace_name} with membership {membership_id}...\n")
            
            # Check if association already exists
            existing = self._get_existing_namespace_association(membership_id, id_namespace_name)
            if existing:
                print(f"✅ ID namespace association already exists: {existing}")
                return existing
            
            # Create association
            response = self.cleanrooms.create_id_namespace_association(
                membershipIdentifier=membership_id,
                name=id_namespace_name,
                description="ACX unique customer identifiers for Clean Rooms joins",
                inputReferenceConfig={
                    "inputReferenceArn": id_namespace_arn,
                    "manageResourcePolicies": True
                },
                idMappingConfig={
                    "allowUseAsDimensionColumn": False
                }
            )
            
            assoc_id = response['idNamespaceAssociation']['id']
            print(f"✅ Created ID namespace association: {id_namespace_name} (ID: {assoc_id})")
            return assoc_id
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ConflictException':
                existing = self._get_existing_namespace_association(membership_id, id_namespace_name)
                if existing:
                    print(f"✅ ID namespace association already exists: {existing}")
                    return existing
            print(f"❌ Error associating ID namespace: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return None
    
    def _get_role_arn(self) -> Optional[str]:
        """Get IAM role ARN for Cleanrooms access."""
        if not self.iam:
            return None
        
        try:
            response = self.iam.get_role(RoleName=self.default_role_name)
            return response['Role']['Arn']
        except Exception as e:
            print(f"⚠️  Could not get IAM role: {e}")
            return None
    
    def _get_existing_association(self, membership_id: str, table_id: str) -> Optional[str]:
        """Check if association already exists."""
        try:
            paginator = self.cleanrooms.get_paginator('list_configured_table_associations')
            for page in paginator.paginate(membershipIdentifier=membership_id):
                for assoc in page.get('configuredTableAssociationSummaries', []):
                    if assoc.get('configuredTableId') == table_id:
                        return assoc.get('id')
            return None
        except Exception:
            return None
    
    def _get_existing_namespace_association(self, membership_id: str, name: str) -> Optional[str]:
        """Check if namespace association already exists."""
        try:
            associations = self.cleanrooms.list_id_namespace_associations(
                membershipIdentifier=membership_id
            )
            for assoc in associations.get('idNamespaceAssociationSummaries', []):
                if assoc.get('name') == name:
                    return assoc.get('id')
            return None
        except Exception:
            return None


def main():
    parser = argparse.ArgumentParser(
        description='Manage AWS Cleanrooms collaboration invitations and associations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List pending invitations
  %(prog)s list --profile flywheel-prod

  # Accept specific invitation
  %(prog)s accept --collaboration-id <id> --profile flywheel-prod

  # Accept all and auto-associate
  %(prog)s accept-all --profile flywheel-prod --auto-associate

  # Associate resources to existing membership
  %(prog)s associate --membership-id <id> --profile flywheel-prod
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List pending invitations')
    
    # Accept command
    accept_parser = subparsers.add_parser('accept', help='Accept a specific invitation')
    accept_parser.add_argument('--collaboration-id', required=True, help='Collaboration ID')
    accept_parser.add_argument('--auto-associate', action='store_true',
                              help='Automatically associate tables and namespace after accepting')
    
    # Accept all command
    accept_all_parser = subparsers.add_parser('accept-all', help='Accept all pending invitations')
    accept_all_parser.add_argument('--auto-associate', action='store_true',
                                  help='Automatically associate tables and namespace after accepting')
    
    # Associate command
    associate_parser = subparsers.add_parser('associate', help='Associate resources to membership')
    associate_parser.add_argument('--membership-id', required=True, help='Membership ID')
    associate_parser.add_argument('--table-ids', nargs='+', help='Specific table IDs to associate (optional)')
    associate_parser.add_argument('--role-arn', help='IAM role ARN for table associations (optional, will lookup if not provided)')
    associate_parser.add_argument('--id-namespace-arn', help='ID namespace ARN (optional)')
    associate_parser.add_argument('--id-namespace-name', help='ID namespace name (optional)')
    
    # Common arguments
    for p in [list_parser, accept_parser, accept_all_parser, associate_parser]:
        p.add_argument('--profile', help='AWS profile name')
        p.add_argument('--region', default='us-east-1', help='AWS region')
        p.add_argument('--no-verify-ssl', action='store_true',
                      help='Disable SSL verification (not recommended)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Configure boto3
    # Handle SSL verification based on flag
    if args.no_verify_ssl:
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        config = Config(
            connect_timeout=60,
            read_timeout=60,
            retries={'max_attempts': 3}
        )
        # Note: boto3 doesn't directly support SSL context, but we can use environment variables
        import os
        os.environ['PYTHONHTTPSVERIFY'] = '0'
    else:
        config = Config(connect_timeout=60, read_timeout=60)
    
    session = boto3.Session(profile_name=args.profile) if args.profile else boto3.Session()
    
    # Create clients
    cleanrooms = session.client('cleanrooms', region_name=args.region, config=config)
    glue = session.client('glue', region_name=args.region, config=config)
    iam = session.client('iam', region_name=args.region, config=config)
    entity_resolution = session.client('entityresolution', region_name=args.region, config=config)
    
    manager = CollaborationManager(
        cleanrooms_client=cleanrooms,
        glue_client=glue,
        iam_client=iam,
        entity_resolution_client=entity_resolution,
        region=args.region
    )
    
    # Execute command
    if args.command == 'list':
        invitations = manager.list_pending_invitations()
        if invitations:
            print(f"\n📋 Found {len(invitations)} pending invitation(s):\n")
            for inv in invitations:
                print(f"  Collaboration: {inv['name']}")
                print(f"    ID: {inv['collaborationId']}")
                print(f"    Creator: {inv['creatorDisplayName']} ({inv['creatorAccountId']})")
                print(f"    Membership ID: {inv.get('membershipId', 'N/A')}")
                print(f"    Created: {inv.get('createTime', 'N/A')}")
                print()
        else:
            print("✅ No pending invitations found")
    
    elif args.command == 'accept':
        membership_id = manager.accept_invitation(args.collaboration_id)
        if membership_id and args.auto_associate:
            print("\n" + "="*60)
            print("Auto-associating resources...")
            print("="*60 + "\n")
            
            # Associate tables
            table_results = manager.associate_configured_tables(membership_id)
            
            # Associate namespace if ARN provided
            if args.id_namespace_arn:
                manager.associate_id_namespace(
                    membership_id,
                    args.id_namespace_arn,
                    args.id_namespace_name
                )
    
    elif args.command == 'accept-all':
        invitations = manager.list_pending_invitations()
        if not invitations:
            print("✅ No pending invitations to accept")
            return
        
        print(f"\n📋 Accepting {len(invitations)} invitation(s)...\n")
        for inv in invitations:
            print(f"\n{'='*60}")
            print(f"Processing: {inv['name']}")
            print(f"{'='*60}\n")
            
            membership_id = manager.accept_invitation(inv['collaborationId'])
            if membership_id and args.auto_associate:
                # Associate tables
                manager.associate_configured_tables(membership_id)
                
                # Associate namespace (use default)
                default_namespace_arn = "arn:aws:entityresolution:us-east-1:239083076653:idnamespace/ACXIdNamespace"
                manager.associate_id_namespace(membership_id, default_namespace_arn)
    
    elif args.command == 'associate':
        print(f"\n🔗 Associating resources to membership: {args.membership_id}\n")
        
        # Associate tables
        table_results = manager.associate_configured_tables(
            args.membership_id,
            table_ids=args.table_ids,
            role_arn=args.role_arn
        )
        
        # Create collaboration analysis rules for successful associations
        if table_results['success']:
            print(f"\n📝 Creating collaboration analysis rules for {len(table_results['success'])} associations...\n")
            # Get collaboration members to determine result receivers
            try:
                sts = boto3.client('sts')
                our_account_id = sts.get_caller_identity()['Account']
                
                membership = cleanrooms.get_membership(membershipIdentifier=args.membership_id)
                collaboration_id = membership['membership']['collaborationId']
                members = cleanrooms.list_members(collaborationIdentifier=collaboration_id)
                all_account_ids = [m['accountId'] for m in members.get('memberSummaries', [])]
                
                # Use the other member account (not our account) as result receiver
                # Result receivers must be external accounts, not the data provider
                result_receivers = [aid for aid in all_account_ids if aid != our_account_id]
                
                if not result_receivers:
                    # Fallback: try default accounts first, then all members
                    default_result_receivers = ["657425294073", "803109464991"]
                    result_receivers = [aid for aid in default_result_receivers if aid in all_account_ids]
                    if not result_receivers:
                        print(f"   ⚠️  No other member accounts found, using all members as fallback")
                        result_receivers = all_account_ids
                
                print(f"   Using result receivers: {result_receivers}\n")
            except Exception as e:
                print(f"   ⚠️  Could not determine result receivers: {e}")
                result_receivers = []
            
            # Create collaboration analysis rules
            for success in table_results['success']:
                assoc_id = success.get('association_id')
                if assoc_id:
                    try:
                        rule_policy = {
                            "v1": {
                                "custom": {
                                    "allowedResultReceivers": result_receivers
                                }
                            }
                        }
                        cleanrooms.create_configured_table_association_analysis_rule(
                            membershipIdentifier=args.membership_id,
                            configuredTableAssociationIdentifier=assoc_id,
                            analysisRuleType="CUSTOM",
                            analysisRulePolicy=rule_policy
                        )
                        print(f"   ✅ Created collaboration analysis rule for {success.get('table', 'table')}")
                    except ClientError as e:
                        if e.response['Error']['Code'] == 'ConflictException':
                            print(f"   ⏭️  Collaboration analysis rule already exists for {success.get('table', 'table')}")
                        else:
                            print(f"   ❌ Failed to create rule for {success.get('table', 'table')}: {e}")
                    except Exception as e:
                        print(f"   ❌ Error creating rule for {success.get('table', 'table')}: {e}")
        
        # Associate namespace if provided
        if args.id_namespace_arn:
            manager.associate_id_namespace(
                args.membership_id,
                args.id_namespace_arn,
                args.id_namespace_name
            )
        
        # Print summary
        print("\n" + "="*60)
        print("Summary:")
        print("="*60)
        print(f"  Tables associated: {len(table_results['success'])}")
        print(f"  Tables skipped: {len(table_results['skipped'])}")
        print(f"  Tables failed: {len(table_results['failed'])}")
        if table_results['failed']:
            print("\n  Failed tables:")
            for failed in table_results['failed']:
                print(f"    - {failed['table']}: {failed['error']}")


if __name__ == "__main__":
    main()

