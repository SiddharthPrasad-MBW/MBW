#!/usr/bin/env python3
"""
Sync DEV environment with PROD configurations
This script updates DEV Glue jobs to match PROD configurations while keeping DEV-specific naming
"""

import boto3
import json
from datetime import datetime
from botocore.exceptions import ClientError

def get_prod_job_config(job_name):
    """Get production job configuration"""
    session = boto3.Session(profile_name='flywheel-prod')
    prod_client = session.client('glue', region_name='us-east-1')
    
    try:
        response = prod_client.get_job(JobName=job_name)
        return response['Job']
    except Exception as e:
        print(f"Error getting PROD job {job_name}: {e}")
        return None

def update_dev_job_config(dev_job_name, prod_config):
    """Update or create DEV job configuration based on PROD config"""
    session = boto3.Session(profile_name='flywheel-dev')
    dev_client = session.client('glue', region_name='us-east-1')
    
    try:
        # Extract key configuration from PROD
        job_config = {
            'Name': dev_job_name,
            'Role': 'arn:aws:iam::417649522250:role/omc_flywheel-dev-glue-role',  # Use DEV role ARN
            'Command': prod_config['Command'],
            'DefaultArguments': prod_config['DefaultArguments'],
            'MaxRetries': prod_config['MaxRetries'],
            'Timeout': prod_config['Timeout'],
            'WorkerType': prod_config['WorkerType'],
            'NumberOfWorkers': prod_config['NumberOfWorkers'],
            'GlueVersion': prod_config['GlueVersion'],
            'ExecutionProperty': prod_config.get('ExecutionProperty', {'MaxConcurrentRuns': 1})
        }
        
        # Update S3 paths to use dev buckets
        if 'DefaultArguments' in job_config:
            args = job_config['DefaultArguments']
            # Update S3 paths from prod to dev
            for key, value in args.items():
                if isinstance(value, str) and 'omc-flywheel-data-us-east-1-prod' in value:
                    args[key] = value.replace('omc-flywheel-data-us-east-1-prod', 'omc-flywheel-data-us-east-1-dev')
                elif isinstance(value, str) and 'omc-flywheel-prod-analysis-data' in value:
                    args[key] = value.replace('omc-flywheel-prod-analysis-data', 'omc-flywheel-dev-analysis-data')
                elif isinstance(value, str) and 'omc_flywheel_prod' in value:
                    args[key] = value.replace('omc_flywheel_prod', 'omc_flywheel_dev')
                elif isinstance(value, str) and 'aws-glue-assets-239083076653' in value:
                    args[key] = value.replace('aws-glue-assets-239083076653', 'aws-glue-assets-417649522250')
        
        # Update script locations to use dev script names and bucket
        if 'Command' in job_config and 'ScriptLocation' in job_config['Command']:
            script_location = job_config['Command']['ScriptLocation']
            # Replace script name
            if 'etl-omc-flywheel-prod-' in script_location:
                script_location = script_location.replace('etl-omc-flywheel-prod-', 'etl-omc-flywheel-dev-')
            # Replace S3 bucket
            if 'aws-glue-assets-239083076653' in script_location:
                script_location = script_location.replace('aws-glue-assets-239083076653', 'aws-glue-assets-417649522250')
            job_config['Command']['ScriptLocation'] = script_location
        
        # Check if job exists
        try:
            dev_client.get_job(JobName=dev_job_name)
            # Job exists, update it
            # Remove Name from update call
            update_config = {k: v for k, v in job_config.items() if k != 'Name'}
            dev_client.update_job(JobName=dev_job_name, JobUpdate=update_config)
            print(f"✅ Updated {dev_job_name}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                # Job doesn't exist, create it
                dev_client.create_job(**job_config)
                print(f"✅ Created {dev_job_name}")
            else:
                raise
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating/creating {dev_job_name}: {e}")
        return False

def main():
    """Main sync function"""
    print("🔄 Syncing DEV environment with PROD configurations...")
    
    # Job mappings: PROD job name -> DEV job name
    job_mappings = {
        # Bucketed pipeline jobs
        'etl-omc-flywheel-prod-infobase-split-and-bucket': 'etl-omc-flywheel-dev-infobase-split-and-bucket',
        'etl-omc-flywheel-prod-addressable-bucket': 'etl-omc-flywheel-dev-addressable-bucket',
        'etl-omc-flywheel-prod-register-staged-tables': 'etl-omc-flywheel-dev-register-staged-tables',
        'etl-omc-flywheel-prod-create-athena-bucketed-tables': 'etl-omc-flywheel-dev-create-athena-bucketed-tables',
        # Partitioned pipeline jobs (new)
        'etl-omc-flywheel-prod-infobase-split-and-part': 'etl-omc-flywheel-dev-infobase-split-and-part',
        'etl-omc-flywheel-prod-addressable-split-and-part': 'etl-omc-flywheel-dev-addressable-split-and-part',
        'etl-omc-flywheel-prod-register-part-tables': 'etl-omc-flywheel-dev-register-part-tables',
        'etl-omc-flywheel-prod-prepare-part-tables': 'etl-omc-flywheel-dev-prepare-part-tables'
    }
    
    updated_jobs = []
    failed_jobs = []
    
    for prod_job, dev_job in job_mappings.items():
        print(f"\n📋 Processing {prod_job} -> {dev_job}")
        
        # Get PROD configuration
        prod_config = get_prod_job_config(prod_job)
        if not prod_config:
            failed_jobs.append(dev_job)
            continue
        
        # Update DEV job
        if update_dev_job_config(dev_job, prod_config):
            updated_jobs.append(dev_job)
        else:
            failed_jobs.append(dev_job)
    
    # Summary
    print(f"\n📊 Sync Summary:")
    print(f"✅ Successfully updated: {len(updated_jobs)} jobs")
    print(f"❌ Failed to update: {len(failed_jobs)} jobs")
    
    if updated_jobs:
        print(f"\n✅ Updated jobs:")
        for job in updated_jobs:
            print(f"   - {job}")
    
    if failed_jobs:
        print(f"\n❌ Failed jobs:")
        for job in failed_jobs:
            print(f"   - {job}")
    
    print(f"\n🎯 Next steps:")
    print(f"1. Verify DEV job configurations")
    print(f"2. Test DEV jobs with sample data")
    print(f"3. Update DEV IAM permissions if needed")

if __name__ == "__main__":
    main()
