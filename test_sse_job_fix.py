#!/usr/bin/env python3
"""
Test SSE_JOB_STORE fix for timeline job monitoring 404 errors.
Verifies that job_id is immediately accessible after timeline generation starts.
"""

import requests
import json
import time
import sys
from datetime import datetime

# Base URL
BASE_URL = "http://localhost:5000"

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")

def test_timeline_job_monitoring():
    """Test the complete workflow: POST timeline -> poll job status"""
    
    print_section("TEST: SSE_JOB_STORE Fix Verification")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Base URL: {BASE_URL}")
    
    # Step 1: Prepare minimal test payload with 2 deliverables
    print_section("Step 1: Prepare Test Payload (2 deliverables)")
    
    payload = {
        "deliverables": [
            {
                "code": "DEL-001",
                "name": "Test Deliverable 1",
                "department": "Creative",
                "rate_band": "Mid"
            },
            {
                "code": "DEL-002", 
                "name": "Test Deliverable 2",
                "department": "Strategy",
                "rate_band": "Senior"
            }
        ],
        "rfp_text": "Test RFP for minimal timeline generation",
        "project_start": "2025-11-01",
        "optimization_mode": "speed",
        "use_intelligent_scheduler": True
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    # Step 2: POST to generate timeline
    print_section("Step 2: POST /api/ai/generate_timeline")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/ai/generate_timeline",
            json=payload,
            timeout=10
        )
        elapsed = time.time() - start_time
        
        print(f"✓ Request completed in {elapsed:.2f}s")
        print(f"✓ HTTP Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"✗ FAILED: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        result = response.json()
        print(f"✓ Response: {json.dumps(result, indent=2)}")
        
        if "job_id" not in result:
            print(f"✗ FAILED: No job_id in response")
            return False
        
        job_id = result["job_id"]
        print(f"\n✓ Job ID received: {job_id}")
        
    except Exception as e:
        print(f"✗ FAILED: Error during POST request: {e}")
        return False
    
    # Step 3: Immediately poll job status
    print_section("Step 3: Poll GET /api/ai/jobs/{job_id} (Immediate)")
    
    try:
        # Poll immediately (no delay)
        poll_response = requests.get(
            f"{BASE_URL}/api/ai/jobs/{job_id}",
            timeout=5
        )
        
        print(f"✓ HTTP Status: {poll_response.status_code}")
        
        if poll_response.status_code == 404:
            print(f"✗ FAILED: Got 404 - job not found in SSE_JOB_STORE!")
            print(f"Response: {poll_response.text}")
            return False
        
        if poll_response.status_code != 200:
            print(f"✗ FAILED: Expected 200, got {poll_response.status_code}")
            print(f"Response: {poll_response.text}")
            return False
        
        job_status = poll_response.json()
        print(f"✓ Job found! Response: {json.dumps(job_status, indent=2)}")
        
        # Step 4: Verify response structure
        print_section("Step 4: Verify Response Structure")
        
        required_fields = ["job_id", "status", "progress"]
        missing_fields = [f for f in required_fields if f not in job_status]
        
        if missing_fields:
            print(f"✗ FAILED: Missing required fields: {missing_fields}")
            return False
        
        print(f"✓ job_id: {job_status.get('job_id')}")
        print(f"✓ status: {job_status.get('status')}")
        print(f"✓ progress: {job_status.get('progress')}%")
        print(f"✓ message: {job_status.get('message', 'N/A')}")
        print(f"✓ current_stage: {job_status.get('current_stage', 'N/A')}")
        
        # Step 5: Poll a few more times to see progress
        print_section("Step 5: Poll 3 More Times (1s intervals)")
        
        for i in range(1, 4):
            time.sleep(1)
            poll_response = requests.get(
                f"{BASE_URL}/api/ai/jobs/{job_id}",
                timeout=5
            )
            
            if poll_response.status_code == 200:
                status = poll_response.json()
                print(f"Poll #{i}: Status={status.get('status')}, Progress={status.get('progress')}%, Stage={status.get('current_stage', 'N/A')}")
                
                # If completed, we can stop
                if status.get('status') in ['completed', 'failed']:
                    print(f"✓ Job finished with status: {status.get('status')}")
                    break
            else:
                print(f"Poll #{i}: HTTP {poll_response.status_code}")
        
        # Final result
        print_section("TEST RESULT: SUCCESS ✓")
        print(f"✓ POST /api/ai/generate_timeline → 200 OK with job_id")
        print(f"✓ GET /api/ai/jobs/{job_id} → 200 OK with status data")
        print(f"✓ NO 404 errors - SSE_JOB_STORE fix is working!")
        print(f"✓ Job data from SSE_JOB_STORE is accessible immediately")
        
        return True
        
    except Exception as e:
        print(f"✗ FAILED: Error during polling: {e}")
        return False

if __name__ == "__main__":
    success = test_timeline_job_monitoring()
    sys.exit(0 if success else 1)
