#!/usr/bin/env python3
"""Direct test of RFP analysis through browser interaction"""
import time
import requests

# Read test RFP
with open('test_rfps/tech_rfp.txt', 'r') as f:
    rfp_text = f.read()

# Test analysis through browser simulation
print("Testing RFP Analysis...")

# 1. Analyze RFP
url = "http://localhost:5000/api/ai/analyze" 
payload = {
    "request_text": rfp_text[:1000],  # Use shorter text for faster testing
    "mode": "fast",
    "tier": "mini",
    "strictness": "balanced"
}

resp = requests.post(url, json=payload)
if resp.status_code == 200:
    data = resp.json()
    job_id = data['job_id']
    print(f"✅ Job started: {job_id}")
    
    # Wait for completion
    for i in range(30):
        time.sleep(1)
        status_resp = requests.get(f"http://localhost:5000/api/ai/status/{job_id}")
        if status_resp.status_code == 200:
            status = status_resp.json()
            if status['status'] == 'completed':
                print(f"✅ Analysis complete!")
                
                # Extract result structure
                result = status.get('result', {})
                print(f"\nResult structure:")
                print(f"  Keys: {list(result.keys())}")
                
                if 'plan' in result:
                    plan = result['plan']
                    print(f"  Plan keys: {list(plan.keys())}")
                    
                    # Look for deliverables in departments
                    if 'departments' in plan:
                        departments = plan['departments']
                        print(f"  Departments: {list(departments.keys())}")
                        
                        # Extract deliverable codes
                        all_deliverables = []
                        for dept_name, dept_data in departments.items():
                            if 'deliverables' in dept_data:
                                for deliv in dept_data['deliverables']:
                                    all_deliverables.append(deliv.get('code', 'unknown'))
                        
                        print(f"\n✅ Found {len(all_deliverables)} deliverables")
                        print(f"   Sample codes: {all_deliverables[:5]}")
                        
                        # Test building scenario with these codes
                        if all_deliverables:
                            build_url = "http://localhost:5000/api/build"
                            build_payload = {
                                "selected_deliverable_codes": all_deliverables[:5],
                                "pricing_mode": "Flat_Blended",
                                "scenario_a": {
                                    "complexity": "Advanced",
                                    "tier": "T3_HighVolume"
                                }
                            }
                            
                            build_resp = requests.post(build_url, json=build_payload)
                            if build_resp.status_code == 200:
                                scenario = build_resp.json()
                                print(f"\n✅ Scenario built successfully!")
                                print(f"   Total hours: {scenario.get('scenario_a', {}).get('total_hours', 0)}")
                                print(f"   Total price: ${scenario.get('scenario_a', {}).get('total_price', 0):,.2f}")
                            else:
                                print(f"\n❌ Build failed: {build_resp.status_code}")
                                print(build_resp.text[:500])
                break
            elif status['status'] == 'failed':
                print(f"❌ Analysis failed: {status.get('error')}")
                break
else:
    print(f"❌ Failed to start: {resp.status_code}")
    print(resp.text)
