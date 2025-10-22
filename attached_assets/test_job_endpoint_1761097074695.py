#!/usr/bin/env python3
"""Test script to verify the /api/agencydb/status/{job_id} endpoint"""

import requests
import json
from ai_planner_agencydb import AIAnalysisJob, AIJobStatus, AI_JOB_STORE

# Test the endpoint locally
base_url = "http://localhost:5000"

def test_job_endpoint():
    """Test the job status endpoint with a sample job"""
    
    # Create a test job directly in AI_JOB_STORE
    test_job_id = "test_job_123"
    test_job = AIAnalysisJob(
        job_id=test_job_id,
        status=AIJobStatus.RUNNING,
        total_chunks=10,
        processed_chunks=5,
        current_stage="Processing deliverables..."
    )
    AI_JOB_STORE[test_job_id] = test_job
    
    print(f"Created test job: {test_job_id}")
    print(f"Job status: {test_job.status.value}")
    print(f"Progress: {test_job.processed_chunks}/{test_job.total_chunks} chunks")
    
    # Test the endpoint
    endpoint = f"{base_url}/api/agencydb/status/{test_job_id}"
    print(f"\nTesting endpoint: {endpoint}")
    
    try:
        response = requests.get(endpoint)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Response data:")
            print(json.dumps(data, indent=2))
            
            # Verify response format
            assert data["job_id"] == test_job_id
            assert data["status"] == "processing"  # Should be mapped from RUNNING
            assert data["progress"] == 50  # Should be 5/10 * 100
            assert data["message"] == "Processing deliverables..."
            
            print("\n✅ Test PASSED: Endpoint returns correct job status!")
            
        else:
            print(f"❌ Test FAILED: Endpoint returned {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Test FAILED with error: {e}")
        
    finally:
        # Clean up test job
        if test_job_id in AI_JOB_STORE:
            del AI_JOB_STORE[test_job_id]
            print(f"\nCleaned up test job: {test_job_id}")
    
    # Now test with completed job
    print("\n" + "="*50)
    print("Testing with completed job...")
    
    test_job_id_2 = "test_job_completed"
    test_job_2 = AIAnalysisJob(
        job_id=test_job_id_2,
        status=AIJobStatus.COMPLETED,
        total_chunks=10,
        processed_chunks=10,
        current_stage="Analysis complete",
        result={"Creative": [{"name": "Test Deliverable", "hours": 10}]}
    )
    AI_JOB_STORE[test_job_id_2] = test_job_2
    
    endpoint_2 = f"{base_url}/api/agencydb/status/{test_job_id_2}"
    print(f"Testing endpoint: {endpoint_2}")
    
    try:
        response = requests.get(endpoint_2)
        if response.status_code == 200:
            data = response.json()
            print("Response data:")
            print(json.dumps(data, indent=2))
            
            assert data["status"] == "completed"
            assert data["progress"] == 100
            assert "data" in data
            assert data["deliverables_count"] == 1
            
            print("\n✅ Test PASSED: Completed job returns correct data!")
        else:
            print(f"❌ Test FAILED: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Test FAILED: {e}")
        
    finally:
        if test_job_id_2 in AI_JOB_STORE:
            del AI_JOB_STORE[test_job_id_2]
    
    # Test with non-existent job
    print("\n" + "="*50)
    print("Testing with non-existent job (should return 404)...")
    
    fake_job_id = "fake_job_999"
    endpoint_3 = f"{base_url}/api/agencydb/status/{fake_job_id}"
    print(f"Testing endpoint: {endpoint_3}")
    
    response = requests.get(endpoint_3)
    if response.status_code == 404:
        print(f"✅ Test PASSED: Non-existent job correctly returns 404")
    else:
        print(f"❌ Test FAILED: Expected 404, got {response.status_code}")

if __name__ == "__main__":
    test_job_endpoint()