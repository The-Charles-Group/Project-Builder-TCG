#!/usr/bin/env python3
"""Test to see the full response structure"""
import requests
import json
import time

def test_full_response():
    print("🔍 Testing Full Response Structure...")
    
    rfp_text = "We need a digital marketing campaign with social media, paid advertising, and content creation"
    
    # Submit analysis
    print("\n📤 Submitting RFP...")
    response = requests.post(
        "http://localhost:5000/api/ai/analyze",
        json={
            "request_text": rfp_text,
            "mode": "fast",
            "session_id": f"debug_{int(time.time())}",
            "strictness": "balanced"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        job_id = result.get("job_id")
        print(f"✅ Job ID: {job_id}")
        
        # Wait for completion
        print("\n⏳ Waiting for completion...")
        time.sleep(2)
        
        # Get full response
        status_resp = requests.get(f"http://localhost:5000/api/ai/jobs/{job_id}")
        if status_resp.status_code == 200:
            full_response = status_resp.json()
            
            print("\n📊 Full Response Structure:")
            print(json.dumps(full_response, indent=2))
            
            # Check if result exists
            if "result" in full_response:
                result = full_response["result"]
                print(f"\n✅ Result exists with keys: {list(result.keys())}")
                
                if "plan" in result:
                    plan = result["plan"]
                    print(f"   Plan keys: {list(plan.keys())}")
                    
                    if "suggestions_by_department" in plan:
                        suggestions = plan["suggestions_by_department"]
                        total_delivs = sum(len(d) for d in suggestions.values())
                        print(f"   Total deliverables in suggestions_by_department: {total_delivs}")
                    
                    if "deliverables" in plan:
                        print(f"   Deliverables key exists with {len(plan['deliverables'])} items")
            else:
                print("\n❌ No 'result' key in response!")
                
if __name__ == "__main__":
    test_full_response()