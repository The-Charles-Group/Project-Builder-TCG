#!/usr/bin/env python3
"""Test that directly checks the job store"""
import sys
import json
sys.path.insert(0, '.')

# Import the AI planner module
from ai_planner_agencydb import AI_JOB_STORE

# Check if there are any jobs
print(f"Jobs in store: {list(AI_JOB_STORE.keys())}")

# Get the most recent job
if AI_JOB_STORE:
    job_id = list(AI_JOB_STORE.keys())[-1]
    job = AI_JOB_STORE[job_id]
    
    print(f"\nJob ID: {job_id}")
    print(f"Status: {job.status}")
    print(f"Has result: {job.result is not None}")
    
    if job.result:
        # Check the structure
        print("\nResult structure:")
        print(f"  - Top level keys: {list(job.result.keys()) if isinstance(job.result, dict) else 'Not a dict'}")
        
        if 'plan' in job.result:
            print(f"  - Plan keys: {list(job.result['plan'].keys())}")
            
            if 'suggestions_by_department' in job.result['plan']:
                suggestions = job.result['plan']['suggestions_by_department']
                total = sum(len(d) for d in suggestions.values())
                print(f"  - Deliverables in suggestions_by_department: {total}")
            
            if 'deliverables' in job.result['plan']:
                print(f"  - Deliverables in plan.deliverables: {len(job.result['plan']['deliverables'])}")
else:
    print("No jobs in store")