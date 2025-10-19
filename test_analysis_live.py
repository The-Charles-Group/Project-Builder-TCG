#!/usr/bin/env python3
"""Test the AI analysis flow directly"""
import requests
import json
import time

def test_analysis():
    print("🚀 Testing AI Analysis Flow...")
    
    # Test RFP content
    rfp_text = """REQUEST FOR PROPOSAL
    Digital Marketing Campaign for Q2 2025
    
    We need a comprehensive marketing strategy including:
    - Social media management across all platforms
    - Paid media campaigns (Google, Meta, TikTok)
    - Content creation and strategy development
    - Email marketing campaigns
    - Website optimization and SEO
    - Analytics and reporting dashboards
    - Brand strategy and positioning
    
    Budget: $100,000 - $150,000
    Timeline: 3 months
    """
    
    # Submit analysis
    print("\n📤 Submitting RFP for analysis...")
    response = requests.post(
        "http://localhost:5000/api/ai/analyze",
        json={
            "request_text": rfp_text,
            "mode": "fast",
            "session_id": f"test_{int(time.time())}",
            "strictness": "balanced"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        job_id = result.get("job_id")
        print(f"✅ Analysis started! Job ID: {job_id}")
        
        # Poll for results
        print("\n⏳ Polling for results...")
        max_attempts = 30
        for i in range(max_attempts):
            time.sleep(1)
            
            status_resp = requests.get(f"http://localhost:5000/api/ai/jobs/{job_id}")
            if status_resp.status_code == 200:
                status = status_resp.json()
                progress = status.get("progress", 0)
                stage = status.get("current_stage", "Processing")
                
                print(f"   [{i+1}/30] Progress: {progress}% - {stage}")
                
                if status["status"] == "completed":
                    print(f"\n🎉 Analysis Complete!")
                    # Count deliverables properly from result->plan->suggestions_by_department
                    delivs_count = 0
                    if 'result' in status and 'plan' in status['result']:
                        suggestions = status['result']['plan'].get('suggestions_by_department', {})
                        for dept_delivs in suggestions.values():
                            delivs_count += len(dept_delivs)
                    print(f"   - Deliverables found: {delivs_count}")
                    print(f"   - Status: {status['status']}")
                    print(f"   - Progress: {status.get('progress', 0)}%")
                    return True
                elif status["status"] == "failed":
                    print(f"\n❌ Analysis Failed: {status.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"   [{i+1}/30] Job not found (status: {status_resp.status_code})")
        
        print("\n⏱️ Analysis timed out after 30 seconds")
        return False
    else:
        print(f"❌ Failed to start analysis: {response.status_code}")
        print(f"   Error: {response.text}")
        return False

if __name__ == "__main__":
    success = test_analysis()
    if success:
        print("\n✅ TEST PASSED - Analysis flow working correctly!")
    else:
        print("\n❌ TEST FAILED - Analysis flow has issues")