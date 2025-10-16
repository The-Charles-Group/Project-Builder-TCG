#!/usr/bin/env python3
"""Test the job status endpoint with a real job triggered through the API"""

import requests
import json
import time
import io

base_url = "http://localhost:5000"

def test_with_real_job():
    """Create a real job through the upload endpoint and test the status endpoint"""
    
    print("Creating a real job through the upload endpoint...")
    
    # Create a simple test RFP file
    test_rfp_content = """
    Test RFP for Digital Marketing Campaign
    
    We need a comprehensive digital marketing campaign including:
    - Social media strategy and content creation
    - Email marketing campaigns
    - SEO optimization
    - Paid advertising campaigns
    - Analytics and reporting
    
    Budget: $100,000
    Timeline: 3 months
    """
    
    # Upload the file and trigger analysis
    files = {'file': ('test_rfp.txt', io.BytesIO(test_rfp_content.encode()), 'text/plain')}
    data = {'analyze': 'true', 'mode': 'fast'}
    
    print(f"Uploading test RFP to {base_url}/api/upload_rfp")
    
    try:
        response = requests.post(f"{base_url}/api/upload_rfp", files=files, data=data)
        print(f"Upload response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("Upload response:")
            print(json.dumps(result, indent=2))
            
            if 'job_id' in result:
                job_id = result['job_id']
                print(f"\n✅ Job created successfully with ID: {job_id}")
                
                # Now test the status endpoint
                print("\n" + "="*50)
                print("Testing job status endpoint...")
                
                # Try different endpoint patterns to see which works
                endpoints = [
                    f"/api/agencydb/status/{job_id}",
                    f"/api/ai/jobs/{job_id}",
                    f"/api/jobs/{job_id}"
                ]
                
                for endpoint_path in endpoints:
                    url = f"{base_url}{endpoint_path}"
                    print(f"\nTrying: {url}")
                    
                    try:
                        status_response = requests.get(url)
                        print(f"Response status: {status_response.status_code}")
                        
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            print("Status data:")
                            print(json.dumps(status_data, indent=2))
                            print(f"✅ Endpoint {endpoint_path} works!")
                            
                            # Poll for completion (max 30 seconds)
                            print("\nPolling for job completion...")
                            max_polls = 30
                            poll_count = 0
                            
                            while poll_count < max_polls:
                                status_response = requests.get(url)
                                if status_response.status_code == 200:
                                    status_data = status_response.json()
                                    status = status_data.get('status', 'unknown')
                                    progress = status_data.get('progress', 0)
                                    
                                    print(f"Poll {poll_count+1}: Status={status}, Progress={progress}%")
                                    
                                    if status in ['completed', 'failed']:
                                        print(f"\n✅ Job finished with status: {status}")
                                        if status == 'completed' and 'data' in status_data:
                                            print(f"Deliverables count: {status_data.get('deliverables_count', 'N/A')}")
                                        break
                                else:
                                    print(f"Poll {poll_count+1}: Error {status_response.status_code}")
                                    break
                                
                                poll_count += 1
                                time.sleep(1)
                            
                            break
                        else:
                            print(f"Response: {status_response.text[:200]}")
                    except Exception as e:
                        print(f"Error: {e}")
                
            else:
                print("❌ No job_id in response")
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_with_real_job()