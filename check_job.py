import httpx
import time
import json

job_id = '53ffeb83-598b-4c89-a7e8-d56a58e05be6'
max_wait = 180

print(f"Checking job {job_id}...")
start_time = time.time()

while (time.time() - start_time) < max_wait:
    try:
        r = httpx.get(f'http://localhost:5000/api/ai/jobs/{job_id}')
        job = r.json()
        
        status = job['status']
        stage = job.get('current_stage', 'Unknown')
        elapsed = job.get('elapsed_seconds', 0)
        
        print(f"Status: {status} - {stage} (elapsed: {elapsed:.1f}s)")
        
        if status == 'completed':
            # Get the result
            r2 = httpx.get(f'http://localhost:5000/api/ai/jobs/{job_id}/result')
            result = r2.json()
            
            # Count deliverables
            plan = result.get('plan', {})
            suggestions = plan.get('suggestions_by_department', {})
            total = sum(len(items) for items in suggestions.values())
            
            print(f"\n✓ Analysis completed successfully!")
            print(f"✓ Total deliverables: {total}")
            
            # Show breakdown by department
            for dept, items in suggestions.items():
                print(f"  - {dept}: {len(items)} deliverables")
            
            break
        elif status == 'failed':
            print(f"\n✗ Job failed: {job.get('error', 'Unknown error')}")
            break
            
    except Exception as e:
        print(f"Error checking job: {e}")
    
    time.sleep(2)
else:
    print(f"\nJob did not complete within {max_wait} seconds")