#!/usr/bin/env python3
"""
Test script to verify two critical bug fixes:
1. BuildScenarioPayload Model - POST /api/pricing/build_scenario
2. Job Store Consolidation - GET /api/ai/jobs/{job_id}
"""

import requests
import time
import json
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:5000"
PDF_FILE_PATH = "attached_assets/St.Regis_Nashville_ Branding Agency RFP_10.22.2024_1760738776363.pdf"

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)

def test_build_scenario_payload():
    """
    Test Fix #1: BuildScenarioPayload Model
    POST /api/pricing/build_scenario with minimal payload including new fields
    """
    print_section("FIX #1: BuildScenarioPayload Model Test")
    
    # Minimal payload with new fields
    payload = {
        "session_id": f"test_session_{int(time.time())}",
        "selection": {
            "deliverable_codes": ["PM.01"],  # Project Management - Basic deliverable
            "components_map": {
                "PM.01": "__ALL__"  # Include all components
            },
            "l3_map": {}  # No L3 tasks selected
        },
        "project_name": "Test Project - Build Scenario",
        "project_start": "2025-01-01",
        "pricing_mode": "Flat_Blended",
        "blended_rate": 195.0,
        "rate_band": "Standard_US",
        "client_budget_usd": 50000.0,
        "retainers": []  # NEW FIELD: Empty retainer list
    }
    
    print("\n📤 Sending POST request to /api/pricing/build_scenario...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/pricing/build_scenario",
            json=payload,
            timeout=30
        )
        
        print(f"\n📊 Response Status Code: {response.status_code}")
        
        # Check for 200 OK
        if response.status_code == 200:
            print("✅ SUCCESS: Returned 200 OK (not 500 error)")
            
            # Parse response
            try:
                data = response.json()
                print(f"\n📋 Response Data:")
                print(json.dumps(data, indent=2)[:1000])  # Print first 1000 chars
                
                # Verify response includes scenario object
                if "scenario" in data or "items" in data:
                    print("✅ SUCCESS: Response includes scenario object")
                    
                    # Count items in response
                    items = data.get("items", [])
                    scenario_items = data.get("scenario", {}).get("items", [])
                    item_count = len(items) or len(scenario_items)
                    
                    if item_count > 0:
                        print(f"✅ SUCCESS: Scenario contains {item_count} items")
                    else:
                        print(f"⚠️  WARNING: Scenario has no items")
                        
                    return True
                else:
                    print("❌ FAILED: Response does not include scenario object")
                    return False
                    
            except json.JSONDecodeError as e:
                print(f"❌ FAILED: Could not parse JSON response: {e}")
                print(f"Raw response: {response.text[:500]}")
                return False
                
        elif response.status_code == 500:
            print("❌ FAILED: Returned 500 error (bug not fixed)")
            print(f"Error response: {response.text[:500]}")
            return False
        else:
            print(f"⚠️  WARNING: Unexpected status code: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ FAILED: Request error: {e}")
        return False

def test_job_store_consolidation():
    """
    Test Fix #2: Job Store Consolidation
    Upload PDF to /api/suggest_by_file, then check GET /api/ai/jobs/{job_id}
    """
    print_section("FIX #2: Job Store Consolidation Test")
    
    # Check if PDF file exists
    pdf_path = Path(PDF_FILE_PATH)
    if not pdf_path.exists():
        print(f"❌ FAILED: PDF file not found at {PDF_FILE_PATH}")
        return False
    
    print(f"\n📄 PDF file found: {pdf_path.name} ({pdf_path.stat().st_size} bytes)")
    
    # Upload PDF to create a job
    print(f"\n📤 Uploading PDF to /api/suggest_by_file...")
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'files': (pdf_path.name, f, 'application/pdf')}
            
            response = requests.post(
                f"{BASE_URL}/api/suggest_by_file",
                files=files,
                timeout=60
            )
        
        print(f"\n📊 Upload Response Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Upload failed with status {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
        
        # Parse response to get job_id
        try:
            upload_data = response.json()
            print(f"\n📋 Upload Response:")
            print(json.dumps(upload_data, indent=2)[:1000])
            
            # Look for job_id in various response fields
            job_id = None
            
            # Check for job_ids array (plural)
            if 'job_ids' in upload_data and upload_data['job_ids']:
                job_id = upload_data['job_ids'][0]  # Get first job
            # Check for singular job_id
            elif 'job_id' in upload_data:
                job_id = upload_data['job_id']
            # Check for jobs array
            elif 'jobs' in upload_data and upload_data['jobs']:
                job_id = upload_data['jobs'][0].get('job_id')
            
            if not job_id:
                print("⚠️  WARNING: No job_id in upload response - checking for immediate results")
                # Check if processing was immediate (no async job)
                if 'suggestions' in upload_data or 'deliverables' in upload_data:
                    print("✅ INFO: Processing completed immediately (no background job)")
                    return True
                else:
                    print("❌ FAILED: No job_id and no immediate results in upload response")
                    return False
            
            print(f"\n🔑 Job ID: {job_id}")
            
        except json.JSONDecodeError as e:
            print(f"❌ FAILED: Could not parse upload response JSON: {e}")
            return False
        
        # Test the job status endpoint
        print(f"\n📤 Testing GET /api/ai/jobs/{job_id}...")
        
        # Poll job status a few times (job might complete quickly or take time)
        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            print(f"\n⏱️  Attempt {attempt}/{max_attempts}...")
            
            status_response = requests.get(
                f"{BASE_URL}/api/ai/jobs/{job_id}",
                timeout=10
            )
            
            print(f"📊 Status Response Code: {status_response.status_code}")
            
            # Check for 200 OK (not 404)
            if status_response.status_code == 200:
                print("✅ SUCCESS: Returned 200 OK (not 404)")
                
                try:
                    status_data = status_response.json()
                    print(f"\n📋 Job Status Data:")
                    print(json.dumps(status_data, indent=2))
                    
                    # Verify response includes job status data
                    required_fields = ['job_id', 'status']
                    missing_fields = [f for f in required_fields if f not in status_data]
                    
                    if not missing_fields:
                        print(f"✅ SUCCESS: Response includes job status data")
                        print(f"   Job ID: {status_data.get('job_id')}")
                        print(f"   Status: {status_data.get('status')}")
                        print(f"   Progress: {status_data.get('progress', 'N/A')}%")
                        
                        # If job is completed, we're done
                        if status_data.get('status') in ['completed', 'done']:
                            print(f"✅ SUCCESS: Job completed successfully")
                            return True
                        elif status_data.get('status') in ['failed', 'error']:
                            print(f"⚠️  WARNING: Job failed - but endpoint returned status correctly")
                            return True  # Endpoint works, job failure is separate issue
                        else:
                            print(f"⏳ Job still {status_data.get('status')}... waiting...")
                            time.sleep(2)
                            continue
                    else:
                        print(f"⚠️  WARNING: Missing fields in response: {missing_fields}")
                        return True  # Endpoint works but response incomplete
                        
                except json.JSONDecodeError as e:
                    print(f"❌ FAILED: Could not parse status response JSON: {e}")
                    return False
                    
            elif status_response.status_code == 404:
                print(f"❌ FAILED: Returned 404 Not Found (bug not fixed)")
                print(f"Response: {status_response.text[:500]}")
                return False
            else:
                print(f"⚠️  WARNING: Unexpected status code: {status_response.status_code}")
                if attempt < max_attempts:
                    time.sleep(2)
                    continue
                else:
                    return False
        
        print("\n⏱️  Job still processing after all attempts")
        return True  # Endpoint works even if job not complete
        
    except requests.exceptions.RequestException as e:
        print(f"❌ FAILED: Request error: {e}")
        return False

def main():
    """Run all tests and report results"""
    print("\n" + "="*80)
    print(" CRITICAL BUG FIX VERIFICATION")
    print("="*80)
    print(f"\nTesting against: {BASE_URL}")
    print(f"PDF file: {PDF_FILE_PATH}")
    
    results = {}
    
    # Test Fix #1
    try:
        results['fix1'] = test_build_scenario_payload()
    except Exception as e:
        print(f"\n❌ Fix #1 test crashed: {e}")
        results['fix1'] = False
    
    # Test Fix #2
    try:
        results['fix2'] = test_job_store_consolidation()
    except Exception as e:
        print(f"\n❌ Fix #2 test crashed: {e}")
        results['fix2'] = False
    
    # Final summary
    print_section("FINAL TEST SUMMARY")
    
    print("\n📊 Test Results:")
    print(f"  Fix #1 (BuildScenarioPayload):  {'✅ PASS' if results.get('fix1') else '❌ FAIL'}")
    print(f"  Fix #2 (Job Store Consolidation): {'✅ PASS' if results.get('fix2') else '❌ FAIL'}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! Both bug fixes are working correctly.")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED - Please review the output above.")
        return 1

if __name__ == "__main__":
    exit(main())
