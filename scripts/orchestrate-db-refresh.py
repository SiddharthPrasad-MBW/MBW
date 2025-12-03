#!/usr/bin/env python3
"""
Database Refresh Orchestrator
Automates the 7-step database refresh process for partitioned tables pipeline.

This script provides better error handling, logging, and flexibility compared to bash scripts.

Usage:
    python3 scripts/orchestrate-db-refresh.py --env dev [--dry-run] [--skip-steps=1,2] [--snapshot-dt=YYYY-MM-DD]
    python3 scripts/orchestrate-db-refresh.py --env prod [--dry-run] [--skip-steps=1,2] [--snapshot-dt=YYYY-MM-DD]
"""

import argparse
import boto3
import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from botocore.exceptions import ClientError, BotoCoreError


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color


class GlueJobOrchestrator:
    """Orchestrates Glue job execution for database refresh"""
    
    # Job definitions for 7-step process
    # For steps with multiple contexts, use 'contexts' key with list of parameter sets
    JOB_DEFINITIONS = {
        'dev': {
            1: {
                'name': 'etl-omc-flywheel-dev-addressable-split-and-part',
                'description': 'Addressable IDs Split and Part',
                'timeout': 3600,
                'parallel_with': [2],
                'contexts': None
            },
            2: {
                'name': 'etl-omc-flywheel-dev-infobase-split-and-part',
                'description': 'Infobase Split and Part',
                'timeout': 3600,
                'parallel_with': [1],
                'contexts': None
            },
            3: {
                'name': 'etl-omc-flywheel-dev-register-part-tables',
                'description': 'Register Part Tables',
                'timeout': 1800,
                'parallel_with': [],
                'contexts': [
                    {
                        'name': 'addressable_ids',
                        'parameters': {
                            'DATABASE': 'omc_flywheel_dev_clean',
                            'S3_ROOT': 's3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_part/addressable_ids/',
                            'TABLE_PREFIX': 'part_',
                            'MAX_COLS': '100'
                        }
                    },
                    {
                        'name': 'infobase_attributes',
                        'parameters': {
                            'DATABASE': 'omc_flywheel_dev_clean',
                            'S3_ROOT': 's3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_part/infobase_attributes/',
                            'TABLE_PREFIX': 'part_',
                            'MAX_COLS': '100'
                        }
                    }
                ]
            },
            4: {
                'name': 'etl-omc-flywheel-dev-prepare-part-tables',
                'description': 'Prepare Part Tables',
                'timeout': 1800,
                'parallel_with': [],
                'contexts': None
            },
            5: {
                'name': 'etl-omc-flywheel-dev-create-part-addressable-ids-er-table',
                'description': 'Create Part Addressable IDs ER Table',
                'timeout': 1800,
                'parallel_with': [],
                'contexts': None
            },
            6: {
                'name': 'etl-omc-flywheel-dev-generate-data-monitor-report',
                'description': 'Generate Data Monitor Report',
                'timeout': 600,
                'parallel_with': [],
                'contexts': None
            },
            7: {
                'name': 'etl-omc-flywheel-dev-generate-cleanrooms-report',
                'description': 'Generate Cleanrooms Report',
                'timeout': 600,
                'parallel_with': [],
                'contexts': None
            }
        },
        'prod': {
            1: {
                'name': 'etl-omc-flywheel-prod-addressable-split-and-part',
                'description': 'Addressable IDs Split and Part',
                'timeout': 3600,
                'parallel_with': [2],
                'contexts': None
            },
            2: {
                'name': 'etl-omc-flywheel-prod-infobase-split-and-part',
                'description': 'Infobase Split and Part',
                'timeout': 3600,
                'parallel_with': [1],
                'contexts': None
            },
            3: {
                'name': 'etl-omc-flywheel-prod-register-part-tables',
                'description': 'Register Part Tables',
                'timeout': 1800,
                'parallel_with': [],
                'contexts': [
                    {
                        'name': 'addressable_ids',
                        'parameters': {
                            'DATABASE': 'omc_flywheel_prod',
                            'S3_ROOT': 's3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_part/addressable_ids/',
                            'TABLE_PREFIX': 'part_',
                            'MAX_COLS': '100'
                        }
                    },
                    {
                        'name': 'infobase_attributes',
                        'parameters': {
                            'DATABASE': 'omc_flywheel_prod',
                            'S3_ROOT': 's3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_part/infobase_attributes/',
                            'TABLE_PREFIX': 'part_',
                            'MAX_COLS': '100'
                        }
                    }
                ]
            },
            4: {
                'name': 'etl-omc-flywheel-prod-prepare-part-tables',
                'description': 'Prepare Part Tables',
                'timeout': 1800,
                'parallel_with': [],
                'contexts': None
            },
            5: {
                'name': 'etl-omc-flywheel-prod-create-part-addressable-ids-er-table',
                'description': 'Create Part Addressable IDs ER Table',
                'timeout': 1800,
                'parallel_with': [],
                'contexts': None
            },
            6: {
                'name': 'etl-omc-flywheel-prod-generate-data-monitor-report',
                'description': 'Generate Data Monitor Report',
                'timeout': 600,
                'parallel_with': [],
                'contexts': None
            },
            7: {
                'name': 'etl-omc-flywheel-prod-generate-cleanrooms-report',
                'description': 'Generate Cleanrooms Report',
                'timeout': 600,
                'parallel_with': [],
                'contexts': None
            }
        }
    }
    
    def __init__(self, env: str, region: str = 'us-east-1', aws_profile: Optional[str] = None, 
                 dry_run: bool = False, skip_steps: List[int] = None, snapshot_dt: Optional[str] = None):
        self.env = env
        self.region = region
        self.dry_run = dry_run
        self.skip_steps = skip_steps or []
        self.snapshot_dt = snapshot_dt
        self.start_time = time.time()
        
        # Initialize AWS clients
        session = boto3.Session(profile_name=aws_profile) if aws_profile else boto3.Session()
        self.glue_client = session.client('glue', region_name=region)
        
        # Validate environment
        if env not in self.JOB_DEFINITIONS:
            raise ValueError(f"Invalid environment: {env}. Must be 'dev' or 'prod'")
        
        self.jobs = self.JOB_DEFINITIONS[env]
    
    def print_header(self):
        """Print script header"""
        print(f"{Colors.GREEN}")
        print("╔══════════════════════════════════════════════════════════╗")
        print(f"║   Database Refresh Orchestrator                         ║")
        print(f"║   Environment: {self.env.upper():<40} ║")
        print(f"║   7-Step Partitioned Tables Pipeline                    ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print(f"{Colors.NC}\n")
        
        print(f"{Colors.BLUE}📋 Configuration:{Colors.NC}")
        print(f"   Environment: {self.env}")
        print(f"   Region: {self.region}")
        if self.dry_run:
            print(f"   {Colors.CYAN}Mode: DRY RUN (no jobs will be executed){Colors.NC}")
        if self.skip_steps:
            print(f"   {Colors.YELLOW}Skipping steps: {','.join(map(str, self.skip_steps))}{Colors.NC}")
        if self.snapshot_dt:
            print(f"   Snapshot Date: {self.snapshot_dt}")
        print()
        
        print(f"{Colors.BLUE}📋 Workflow Steps:{Colors.NC}")
        for step_num, job_def in self.jobs.items():
            parallel_info = ""
            if job_def['parallel_with']:
                parallel_info = f" (parallel with step {job_def['parallel_with'][0]})"
            
            contexts_info = ""
            if job_def.get('contexts'):
                contexts_info = f"\n     - Runs {len(job_def['contexts'])} times in parallel:"
                for ctx in job_def['contexts']:
                    s3_root = ctx['parameters'].get('S3_ROOT', '').split('/')[-2] if 'S3_ROOT' in ctx['parameters'] else ''
                    contexts_info += f"\n       • {ctx['name']} (S3_ROOT: {s3_root})"
            
            print(f"  {step_num}. {job_def['name']}{parallel_info}{contexts_info}")
        print()
    
    def check_job_exists(self, job_name: str) -> bool:
        """Check if a Glue job exists"""
        try:
            self.glue_client.get_job(JobName=job_name)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                return False
            raise
    
    def start_job(self, job_name: str, job_args: Optional[Dict] = None) -> Optional[str]:
        """Start a Glue job and return the run ID"""
        if not self.check_job_exists(job_name):
            print(f"{Colors.RED}❌ Job not found: {job_name}{Colors.NC}")
            return None
        
        if self.dry_run:
            print(f"{Colors.CYAN}🔍 DRY RUN: Would start job: {job_name}{Colors.NC}")
            if job_args:
                print(f"{Colors.CYAN}   With arguments: {json.dumps(job_args)}{Colors.NC}")
            return "dry-run-run-id"
        
        try:
            kwargs = {'JobName': job_name}
            if job_args:
                # Format parameters with -- prefix for Glue
                kwargs['Arguments'] = {f"--{k}": str(v) for k, v in job_args.items()}
            
            response = self.glue_client.start_job_run(**kwargs)
            run_id = response['JobRunId']
            return run_id
        except ClientError as e:
            print(f"{Colors.RED}❌ Failed to start job {job_name}: {e}{Colors.NC}")
            return None
    
    def wait_for_job(self, job_name: str, run_id: str, timeout: int) -> Tuple[bool, Optional[str]]:
        """Wait for a job to complete and return (success, error_message)"""
        if self.dry_run and run_id == "dry-run-run-id":
            print(f"{Colors.CYAN}🔍 DRY RUN: Would wait for job completion{Colors.NC}")
            return True, None
        
        print(f"{Colors.BLUE}⏳ Waiting for job: {job_name}{Colors.NC}")
        print(f"{Colors.CYAN}   Run ID: {run_id}{Colors.NC}")
        
        elapsed = 0
        last_status = None
        poll_interval = 30
        
        while elapsed < timeout:
            try:
                response = self.glue_client.get_job_run(JobName=job_name, RunId=run_id)
                status = response['JobRun']['JobRunState']
                
                if status != last_status:
                    if status == 'SUCCEEDED':
                        print(f"{Colors.GREEN}✅ Job completed successfully: {job_name}{Colors.NC}")
                        return True, None
                    elif status in ['FAILED', 'ERROR', 'TIMEOUT']:
                        error_msg = response['JobRun'].get('ErrorMessage', 'Unknown error')
                        error_string = response['JobRun'].get('ErrorString', '')
                        print(f"{Colors.RED}❌ Job failed: {job_name} (Status: {status}){Colors.NC}")
                        print(f"{Colors.YELLOW}📋 Error: {error_msg}{Colors.NC}")
                        if error_string:
                            print(f"{Colors.YELLOW}   Details: {error_string}{Colors.NC}")
                        return False, error_msg
                    elif status in ['RUNNING', 'STARTING']:
                        print(f"{Colors.BLUE}⏳ Job running... ({elapsed}s elapsed){Colors.NC}")
                    elif status in ['STOPPING', 'STOPPED']:
                        print(f"{Colors.YELLOW}⚠️  Job stopped: {job_name}{Colors.NC}")
                        return False, "Job was stopped"
                    else:
                        print(f"{Colors.YELLOW}⚠️  Status: {status} ({elapsed}s elapsed){Colors.NC}")
                    
                    last_status = status
                
                time.sleep(poll_interval)
                elapsed += poll_interval
                
            except ClientError as e:
                print(f"{Colors.RED}❌ Error checking job status: {e}{Colors.NC}")
                return False, str(e)
        
        print(f"{Colors.RED}❌ Job timed out after {timeout}s: {job_name}{Colors.NC}")
        return False, "Job timed out"
    
    def run_step(self, step_num: int) -> bool:
        """Run a single step (handles both single and multiple contexts)"""
        if step_num in self.skip_steps:
            print(f"{Colors.YELLOW}⏭️  Skipping step {step_num} (--skip-steps){Colors.NC}")
            return True
        
        job_def = self.jobs[step_num]
        job_name = job_def['name']
        step_name = job_def['description']
        timeout = job_def['timeout']
        contexts = job_def.get('contexts')
        
        # If step has multiple contexts, run them in parallel
        if contexts and len(contexts) > 0:
            return self.run_step_with_contexts(step_num, job_name, step_name, timeout, contexts)
        
        # Single context - run normally
        print(f"\n{Colors.GREEN}{'━' * 50}{Colors.NC}")
        print(f"{Colors.GREEN}🚀 Step {step_num}: {step_name}{Colors.NC}")
        print(f"{Colors.GREEN}📝 Job: {job_name}{Colors.NC}")
        print(f"{Colors.GREEN}{'━' * 50}{Colors.NC}\n")
        
        # Prepare job arguments
        job_args = {}
        if self.snapshot_dt:
            job_args['SNAPSHOT_DT'] = self.snapshot_dt
        
        # Start job
        print(f"{Colors.BLUE}▶️  Starting job: {job_name}{Colors.NC}")
        run_id = self.start_job(job_name, job_args if job_args else None)
        
        if not run_id:
            return False
        
        if not self.dry_run:
            print(f"{Colors.GREEN}✅ Job started successfully{Colors.NC}")
            print(f"{Colors.CYAN}   Run ID: {run_id}{Colors.NC}")
            print(f"{Colors.CYAN}   Monitor: aws glue get-job-run --job-name \"{job_name}\" --run-id \"{run_id}\"{Colors.NC}")
        
        # Wait for completion
        success, error = self.wait_for_job(job_name, run_id, timeout)
        
        if success:
            print(f"{Colors.GREEN}✅ Step {step_num} completed: {step_name}{Colors.NC}")
            return True
        else:
            print(f"{Colors.RED}❌ Step {step_num} failed: {step_name}{Colors.NC}")
            return False
    
    def run_step_with_contexts(self, step_num: int, job_name: str, step_name: str, 
                               timeout: int, contexts: List[Dict]) -> bool:
        """Run a step with multiple contexts in parallel"""
        print(f"\n{Colors.GREEN}{'━' * 50}{Colors.NC}")
        print(f"{Colors.GREEN}🚀 Step {step_num}: {step_name} (Multiple Contexts){Colors.NC}")
        print(f"{Colors.GREEN}📝 Job: {job_name}{Colors.NC}")
        print(f"{Colors.GREEN}{'━' * 50}{Colors.NC}\n")
        
        if self.dry_run:
            print(f"{Colors.CYAN}🔍 DRY RUN: Would start {len(contexts)} job runs in parallel{Colors.NC}")
            for ctx in contexts:
                print(f"{Colors.CYAN}   Context: {ctx['name']}{Colors.NC}")
                print(f"{Colors.CYAN}   Parameters: {json.dumps(ctx['parameters'])}{Colors.NC}")
            return True
        
        # Start all jobs in parallel
        print(f"{Colors.BLUE}▶️  Starting {len(contexts)} job runs in parallel...{Colors.NC}")
        run_ids = []
        context_names = []
        
        for ctx in contexts:
            context_name = ctx['name']
            params = ctx['parameters'].copy()
            
            # Add snapshot_dt if provided
            if self.snapshot_dt:
                params['SNAPSHOT_DT'] = self.snapshot_dt
            
            print(f"{Colors.BLUE}   Starting: {context_name}{Colors.NC}")
            run_id = self.start_job(job_name, params)
            
            if not run_id:
                print(f"{Colors.RED}❌ Failed to start job for context: {context_name}{Colors.NC}")
                return False
            
            run_ids.append(run_id)
            context_names.append(context_name)
            print(f"{Colors.GREEN}✅ Started {context_name} (Run ID: {run_id}){Colors.NC}")
        
        # Wait for all to complete
        print(f"\n{Colors.BLUE}⏳ Waiting for all job runs to complete...{Colors.NC}")
        all_succeeded = True
        
        for i, (run_id, context_name) in enumerate(zip(run_ids, context_names)):
            print(f"{Colors.CYAN}   Waiting for: {context_name}{Colors.NC}")
            success, error = self.wait_for_job(job_name, run_id, timeout)
            if not success:
                print(f"{Colors.RED}❌ Workflow stopped: Step {step_num} ({context_name}) failed{Colors.NC}")
                all_succeeded = False
        
        if all_succeeded:
            print(f"{Colors.GREEN}✅ Step {step_num} completed: All contexts succeeded{Colors.NC}\n")
        
        return all_succeeded
    
    def run_parallel_steps(self, step_nums: List[int]) -> bool:
        """Run multiple steps in parallel"""
        if any(step in self.skip_steps for step in step_nums):
            print(f"{Colors.YELLOW}⏭️  Skipping parallel steps {step_nums} (--skip-steps){Colors.NC}")
            return True
        
        print(f"\n{Colors.GREEN}{'━' * 50}{Colors.NC}")
        print(f"{Colors.GREEN}🚀 Steps {','.join(map(str, step_nums))}: Parallel Execution{Colors.NC}")
        print(f"{Colors.GREEN}{'━' * 50}{Colors.NC}\n")
        
        if self.dry_run:
            print(f"{Colors.CYAN}🔍 DRY RUN: Would start jobs in parallel{Colors.NC}")
            return True
        
        # Start all jobs
        print(f"{Colors.BLUE}▶️  Starting jobs in parallel...{Colors.NC}")
        run_ids = {}
        job_args = {}
        if self.snapshot_dt:
            job_args['SNAPSHOT_DT'] = self.snapshot_dt
        
        for step_num in step_nums:
            job_def = self.jobs[step_num]
            job_name = job_def['name']
            run_id = self.start_job(job_name, job_args if job_args else None)
            if run_id:
                run_ids[step_num] = (job_name, run_id)
                print(f"{Colors.GREEN}✅ Job {step_num} started: {job_name} (Run ID: {run_id}){Colors.NC}")
            else:
                return False
        
        # Wait for all jobs to complete
        print(f"\n{Colors.BLUE}⏳ Waiting for all jobs to complete...{Colors.NC}")
        all_succeeded = True
        
        for step_num, (job_name, run_id) in run_ids.items():
            job_def = self.jobs[step_num]
            success, error = self.wait_for_job(job_name, run_id, job_def['timeout'])
            if not success:
                all_succeeded = False
                print(f"{Colors.RED}❌ Workflow stopped: Step {step_num} ({job_name}) failed{Colors.NC}")
        
        if all_succeeded:
            print(f"{Colors.GREEN}✅ All parallel jobs completed successfully{Colors.NC}\n")
        
        return all_succeeded
    
    def execute(self) -> bool:
        """Execute the complete workflow"""
        self.print_header()
        
        if not self.dry_run:
            response = input("Continue with workflow execution? (y/n): ")
            if response.lower() != 'y':
                print(f"{Colors.YELLOW}⏸️  Execution cancelled{Colors.NC}")
                return False
        
        # Steps 1 & 2: Run in parallel
        if not self.run_parallel_steps([1, 2]):
            return False
        
        # Steps 3-7: Run sequentially
        for step_num in range(3, 8):
            if not self.run_step(step_num):
                return False
        
        # Print summary
        duration = int(time.time() - self.start_time)
        minutes = duration // 60
        seconds = duration % 60
        
        print(f"\n{Colors.GREEN}{'═' * 50}{Colors.NC}")
        print(f"{Colors.GREEN}✅ Database Refresh Completed Successfully!{Colors.NC}")
        print(f"{Colors.GREEN}⏱️  Total Duration: {minutes}m {seconds}s{Colors.NC}")
        print(f"{Colors.GREEN}{'═' * 50}{Colors.NC}\n")
        
        print(f"{Colors.BLUE}📊 Next Steps:{Colors.NC}")
        if self.env == 'dev':
            print("  • Review job logs in CloudWatch")
            print("  • Verify data in S3: s3://omc-flywheel-data-us-east-1-dev/omc_cleanroom_data/split_part/")
            print("  • Check Glue tables in database: omc_flywheel_dev_clean")
            print("  • Review reports:")
            print("    - Data Monitor: s3://omc-flywheel-dev-analysis-data/data-monitor-reports/")
            print("    - Cleanrooms: s3://omc-flywheel-dev-analysis-data/cleanrooms-reports/")
        else:
            print("  • Review job logs in CloudWatch")
            print("  • Verify data in S3: s3://omc-flywheel-data-us-east-1-prod/omc_cleanroom_data/split_part/")
            print("  • Check Glue tables in database: omc_flywheel_prod")
            print("  • Review reports:")
            print("    - Data Monitor: s3://omc-flywheel-prod-analysis-data/data-monitor-reports/")
            print("    - Cleanrooms: s3://omc-flywheel-prod-analysis-data/cleanrooms-reports/")
        print()
        
        return True


def main():
    parser = argparse.ArgumentParser(
        description='Orchestrate 7-step database refresh process',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dev environment, dry run
  python3 scripts/orchestrate-db-refresh.py --env dev --dry-run
  
  # Dev environment, skip steps 1 and 2
  python3 scripts/orchestrate-db-refresh.py --env dev --skip-steps 1,2
  
  # Prod environment with specific snapshot date
  python3 scripts/orchestrate-db-refresh.py --env prod --snapshot-dt 2025-01-15
        """
    )
    
    parser.add_argument('--env', required=True, choices=['dev', 'prod'],
                       help='Environment (dev or prod)')
    parser.add_argument('--region', default='us-east-1',
                       help='AWS region (default: us-east-1)')
    parser.add_argument('--aws-profile',
                       help='AWS profile to use (default: flywheel-{env})')
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run mode (no jobs will be executed)')
    parser.add_argument('--skip-steps',
                       help='Comma-separated list of step numbers to skip (e.g., 1,2)')
    parser.add_argument('--snapshot-dt',
                       help='Snapshot date in YYYY-MM-DD format (overrides auto-discovery)')
    
    args = parser.parse_args()
    
    # Parse skip steps
    skip_steps = []
    if args.skip_steps:
        try:
            skip_steps = [int(s.strip()) for s in args.skip_steps.split(',')]
        except ValueError:
            print(f"{Colors.RED}❌ Invalid skip-steps format. Use comma-separated numbers (e.g., 1,2){Colors.NC}")
            sys.exit(1)
    
    # Determine AWS profile
    aws_profile = args.aws_profile or f"flywheel-{args.env}"
    
    try:
        orchestrator = GlueJobOrchestrator(
            env=args.env,
            region=args.region,
            aws_profile=aws_profile,
            dry_run=args.dry_run,
            skip_steps=skip_steps,
            snapshot_dt=args.snapshot_dt
        )
        
        success = orchestrator.execute()
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"{Colors.RED}❌ Error: {e}{Colors.NC}")
        sys.exit(1)


if __name__ == '__main__':
    main()

