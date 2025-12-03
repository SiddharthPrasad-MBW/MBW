#!/usr/bin/env python3
"""
Manage Multiple AWS Cleanrooms Collaborations

This script provides a higher-level interface for managing 10+ collaborations
using a configuration file. It handles:
- Accepting multiple invitations
- Associating resources to multiple memberships
- Tracking collaboration status
- Bulk operations

Usage:
    # Initialize configuration file
    python3 manage-multiple-collaborations.py init-config

    # Process all pending invitations
    python3 manage-multiple-collaborations.py process-invites \
        --config collaboration-config.json \
        --profile flywheel-prod

    # Sync all collaborations (associate resources)
    python3 manage-multiple-collaborations.py sync-all \
        --config collaboration-config.json \
        --profile flywheel-prod

    # Add new collaboration manually
    python3 manage-multiple-collaborations.py add \
        --membership-id <id> \
        --config collaboration-config.json
"""

import json
import argparse
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional
import boto3
from botocore.config import Config

# Import the manager class from the other script
# We'll import it dynamically to avoid circular dependencies
def get_collaboration_manager(cleanrooms_client, glue_client=None, iam_client=None, 
                             entity_resolution_client=None, region="us-east-1"):
    """Import and return CollaborationManager class."""
    import importlib.util
    script_path = Path(__file__).parent / "manage-collaboration-invites.py"
    spec = importlib.util.spec_from_file_location("manage_collaboration_invites", script_path)
    manage_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(manage_module)
    return manage_module.CollaborationManager(
        cleanrooms_client=cleanrooms_client,
        glue_client=glue_client,
        iam_client=iam_client,
        entity_resolution_client=entity_resolution_client,
        region=region
    )


class MultiCollaborationManager:
    """Manages multiple Cleanrooms collaborations using a configuration file."""
    
    def __init__(self, config_path: str, manager=None):
        self.config_path = Path(config_path)
        self.manager = manager
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            return self._default_config()
        
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return self._default_config()
    
    def _save_config(self):
        """Save configuration to JSON file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving config: {e}")
    
    def _default_config(self) -> Dict:
        """Return default configuration structure."""
        return {
            "defaults": {
                "region": "us-east-1",
                "role_name": "cleanrooms-glue-s3-access",
                "id_namespace_name": "ACXIdNamespace",
                "id_namespace_arn": "arn:aws:entityresolution:us-east-1:239083076653:idnamespace/ACXIdNamespace",
                "table_prefix": "part_",
                "database": "omc_flywheel_prod",
                "allowed_query_providers": ["921290734397", "657425294073"]
            },
            "collaborations": [],
            "pending_invitations": []
        }
    
    def process_pending_invitations(self, auto_associate: bool = True):
        """Process all pending invitations from config and AWS."""
        print("📋 Processing pending invitations...\n")
        
        # Get invitations from AWS
        aws_invitations = self.manager.list_pending_invitations()
        
        # Update config with current invitations
        self.config['pending_invitations'] = [
            {
                'collaboration_id': inv['collaborationId'],
                'name': inv['name'],
                'creator_account_id': inv['creatorAccountId'],
                'create_time': str(inv.get('createTime', ''))
            }
            for inv in aws_invitations
        ]
        
        if not aws_invitations:
            print("✅ No pending invitations found")
            self._save_config()
            return
        
        print(f"Found {len(aws_invitations)} pending invitation(s)\n")
        
        # Process each invitation
        for inv in aws_invitations:
            print(f"\n{'='*60}")
            print(f"Processing: {inv['name']}")
            print(f"{'='*60}\n")
            
            membership_id = self.manager.accept_invitation(inv['collaborationId'])
            
            if membership_id:
                # Add to collaborations list
                collaboration_entry = {
                    'name': inv['name'],
                    'collaboration_id': inv['collaborationId'],
                    'membership_id': membership_id,
                    'status': 'active',
                    'auto_associate_tables': auto_associate,
                    'auto_associate_namespace': auto_associate,
                    'allowed_query_providers': self.config['defaults']['allowed_query_providers'],
                    'notes': f"Auto-accepted from invitation"
                }
                
                # Check if already exists
                existing = next(
                    (c for c in self.config['collaborations'] 
                     if c.get('membership_id') == membership_id),
                    None
                )
                
                if not existing:
                    self.config['collaborations'].append(collaboration_entry)
                    print(f"✅ Added to collaborations list")
                else:
                    print(f"⏭️  Already in collaborations list")
                
                # Auto-associate if requested
                if auto_associate:
                    print("\n🔗 Auto-associating resources...")
                    self.manager.associate_configured_tables(membership_id)
                    self.manager.associate_id_namespace(
                        membership_id,
                        self.config['defaults']['id_namespace_arn'],
                        self.config['defaults']['id_namespace_name']
                    )
        
        # Remove processed invitations
        self.config['pending_invitations'] = []
        self._save_config()
        print(f"\n✅ Processed {len(aws_invitations)} invitation(s)")
    
    def sync_all_collaborations(self):
        """Sync resources for all active collaborations."""
        active_collabs = [
            c for c in self.config['collaborations']
            if c.get('status') == 'active'
        ]
        
        if not active_collabs:
            print("✅ No active collaborations to sync")
            return
        
        print(f"🔄 Syncing {len(active_collabs)} active collaboration(s)...\n")
        
        for collab in active_collabs:
            membership_id = collab.get('membership_id')
            if not membership_id:
                print(f"⚠️  Skipping {collab.get('name')}: No membership ID")
                continue
            
            print(f"\n{'='*60}")
            print(f"Syncing: {collab.get('name')}")
            print(f"{'='*60}\n")
            
            # Associate tables if enabled
            if collab.get('auto_associate_tables', True):
                self.manager.associate_configured_tables(membership_id)
            
            # Associate namespace if enabled
            if collab.get('auto_associate_namespace', True):
                self.manager.associate_id_namespace(
                    membership_id,
                    self.config['defaults']['id_namespace_arn'],
                    self.config['defaults']['id_namespace_name']
                )
        
        print(f"\n✅ Synced {len(active_collabs)} collaboration(s)")
    
    def add_collaboration(self, membership_id: str, name: str = None, 
                         collaboration_id: str = None):
        """Manually add a collaboration to the config."""
        entry = {
            'membership_id': membership_id,
            'name': name or f"Collaboration {membership_id}",
            'collaboration_id': collaboration_id,
            'status': 'active',
            'auto_associate_tables': True,
            'auto_associate_namespace': True,
            'allowed_query_providers': self.config['defaults']['allowed_query_providers'],
            'notes': 'Manually added'
        }
        
        # Check if exists
        existing = next(
            (c for c in self.config['collaborations'] 
             if c.get('membership_id') == membership_id),
            None
        )
        
        if existing:
            print(f"⚠️  Collaboration already exists: {existing.get('name')}")
            return
        
        self.config['collaborations'].append(entry)
        self._save_config()
        print(f"✅ Added collaboration: {entry['name']}")
    
    def list_collaborations(self):
        """List all collaborations in config."""
        collabs = self.config.get('collaborations', [])
        
        if not collabs:
            print("📋 No collaborations configured")
            return
        
        print(f"\n📋 Configured Collaborations ({len(collabs)}):\n")
        for i, collab in enumerate(collabs, 1):
            print(f"{i}. {collab.get('name', 'Unknown')}")
            print(f"   Membership ID: {collab.get('membership_id', 'N/A')}")
            print(f"   Status: {collab.get('status', 'unknown')}")
            print(f"   Auto-associate: Tables={collab.get('auto_associate_tables', False)}, "
                  f"Namespace={collab.get('auto_associate_namespace', False)}")
            if collab.get('notes'):
                print(f"   Notes: {collab.get('notes')}")
            print()


def main():
    parser = argparse.ArgumentParser(
        description='Manage multiple AWS Cleanrooms collaborations',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    # Init config
    init_parser = subparsers.add_parser('init-config', 
                                        help='Initialize configuration file')
    init_parser.add_argument('--config', default='collaboration-config.json',
                            help='Config file path')
    
    # Process invites
    process_parser = subparsers.add_parser('process-invites',
                                          help='Process all pending invitations')
    process_parser.add_argument('--config', default='collaboration-config.json',
                               help='Config file path')
    process_parser.add_argument('--no-auto-associate', action='store_true',
                               help='Do not auto-associate resources')
    
    # Sync all
    sync_parser = subparsers.add_parser('sync-all',
                                       help='Sync all active collaborations')
    sync_parser.add_argument('--config', default='collaboration-config.json',
                            help='Config file path')
    
    # Add collaboration
    add_parser = subparsers.add_parser('add',
                                      help='Add collaboration manually')
    add_parser.add_argument('--membership-id', required=True,
                          help='Membership ID')
    add_parser.add_argument('--name', help='Collaboration name')
    add_parser.add_argument('--collaboration-id', help='Collaboration ID')
    add_parser.add_argument('--config', default='collaboration-config.json',
                           help='Config file path')
    
    # List
    list_parser = subparsers.add_parser('list',
                                       help='List all collaborations')
    list_parser.add_argument('--config', default='collaboration-config.json',
                           help='Config file path')
    
    # Common args
    for p in [process_parser, sync_parser]:
        p.add_argument('--profile', help='AWS profile')
        p.add_argument('--region', default='us-east-1', help='AWS region')
        p.add_argument('--no-verify-ssl', action='store_true',
                      help='Disable SSL verification')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize config if needed
    if args.command == 'init-config':
        config_path = Path(args.config)
        if config_path.exists():
            print(f"⚠️  Config file already exists: {config_path}")
            response = input("Overwrite? (y/N): ")
            if response.lower() != 'y':
                return
        
        manager = MultiCollaborationManager(str(config_path), None)
        manager._save_config()
        print(f"✅ Created config file: {config_path}")
        return
    
    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        print("Run 'init-config' first")
        sys.exit(1)
    
    # Create AWS clients for commands that need them
    if args.command in ['process-invites', 'sync-all']:
        config = Config(connect_timeout=60, read_timeout=60)
        session = boto3.Session(profile_name=args.profile) if args.profile else boto3.Session()
        
        cleanrooms = session.client('cleanrooms', region_name=args.region, config=config)
        glue = session.client('glue', region_name=args.region, config=config)
        iam = session.client('iam', region_name=args.region, config=config)
        entity_resolution = session.client('entityresolution', region_name=args.region, config=config)
        
        manager = get_collaboration_manager(
            cleanrooms_client=cleanrooms,
            glue_client=glue,
            iam_client=iam,
            entity_resolution_client=entity_resolution,
            region=args.region
        )
    else:
        manager = None
    
    multi_manager = MultiCollaborationManager(str(config_path), manager)
    
    # Execute command
    if args.command == 'process-invites':
        multi_manager.process_pending_invitations(
            auto_associate=not args.no_auto_associate
        )
    elif args.command == 'sync-all':
        multi_manager.sync_all_collaborations()
    elif args.command == 'add':
        multi_manager.add_collaboration(
            args.membership_id,
            args.name,
            args.collaboration_id
        )
    elif args.command == 'list':
        multi_manager.list_collaborations()


if __name__ == "__main__":
    main()

