#!/usr/bin/env python3
"""Final test to verify AI assistant polling is fixed"""
import requests
import json
import time

def test_final_fix():
    print("🎯 FINAL TEST - AI Assistant Polling Fix Verification")
    print("=" * 50)
    
    rfp_text = """Digital Marketing Campaign for Q2 2025
    We need comprehensive services including:
    - Social media strategy and management
    - Paid advertising (Google, Meta, TikTok)
    - Content creation and copywriting
    - Email marketing campaigns
    - SEO and website optimization
    - Analytics and reporting dashboards
    - Brand strategy development
    """
    
    # Submit analysis
    print("\n1️⃣ Submitting RFP for analysis...")
    response = requests.post(
        "http://localhost:5000/api/ai/analyze",
        json={
            "request_text": rfp_text,
            "mode": "fast",
            "session_id": f"final_test_{int(time.time())}",
            "strictness": "balanced"
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to start analysis: {response.status_code}")
        return False
    
    result = response.json()
    job_id = result.get("job_id")
    print(f"✅ Job started: {job_id}")
    
    # Poll for results
    print("\n2️⃣ Polling for results (testing polling mechanism)...")
    max_attempts = 10
    poll_count = 0
    
    for i in range(max_attempts):
        time.sleep(0.5)
        poll_count += 1
        
        status_resp = requests.get(f"http://localhost:5000/api/ai/jobs/{job_id}")
        if status_resp.status_code == 200:
            status = status_resp.json()
            progress = status.get("progress", 0)
            stage = status.get("current_stage", "Processing")
            
            print(f"   Poll #{poll_count}: Progress={progress}%, Stage={stage[:30]}, Status={status['status']}")
            
            if status["status"] == "completed":
                print(f"\n3️⃣ Analysis completed after {poll_count} polls!")
                
                # Check deliverables count from correct path
                deliverables_count = 0
                if 'result' in status and 'plan' in status['result']:
                    suggestions = status['result']['plan'].get('suggestions_by_department', {})
                    for dept_delivs in suggestions.values():
                        deliverables_count += len(dept_delivs)
                
                print(f"\n4️⃣ Results:")
                print(f"   - Deliverables found: {deliverables_count}")
                print(f"   - Polling worked: ✅ YES")
                print(f"   - Data returned: ✅ YES" if deliverables_count > 0 else "   - Data returned: ❌ NO")
                
                # Verify deliverables > 0
                if deliverables_count > 0:
                    print(f"\n✅ SUCCESS! Found {deliverables_count} deliverables")
                    print("✅ Polling mechanism is working correctly")
                    print("✅ UI should now update properly!")
                    return True
                else:
                    print("\n❌ FAIL: No deliverables found in response")
                    return False
                    
            elif status["status"] == "failed":
                print(f"\n❌ Analysis failed: {status.get('error')}")
                return False
    
    print(f"\n❌ Timeout after {poll_count} polls")
    return False

if __name__ == "__main__":
    success = test_final_fix()
    print("\n" + "=" * 50)
    if success:
        print("🎉 ALL TESTS PASSED - FIX VERIFIED!")
        print("The AI assistant polling is now working correctly.")
        print("Users can now see real-time progress updates!")
    else:
        print("❌ TEST FAILED - Issue still present")
        print("Please check the implementation.")