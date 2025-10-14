#!/usr/bin/env python
"""Test script to verify AI analysis saves deliverables correctly"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_ai_analysis():
    """Test that AI analysis correctly saves deliverables to job result"""
    
    print("[TEST] Starting AI analysis test...")
    
    # Sample request text for testing
    request_text = """
    We need a comprehensive digital marketing campaign for a new product launch.
    The campaign should include:
    - Social media strategy across all major platforms
    - Content creation and management
    - Paid media campaigns
    - SEO optimization
    - Email marketing
    - Website development and updates
    - Analytics and reporting
    - Brand strategy and positioning
    - Creative assets development
    - Influencer partnerships
    - Community management
    - Performance tracking
    """
    
    # Start AI analysis job
    print("[TEST] Submitting AI analysis request...")
    response = requests.post(
        f"{BASE_URL}/api/ai/analyze",
        json={
            "request_text": request_text,
            "strictness": "balanced"
        }
    )
    
    if response.status_code != 200:
        print(f"[TEST FAILED] Request failed with status {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    result = response.json()
    job_id = result.get("job_id")
    print(f"[TEST] Job started with ID: {job_id}")
    
    # Poll for job completion
    max_attempts = 60  # Wait up to 60 seconds
    for i in range(max_attempts):
        time.sleep(1)
        
        status_response = requests.get(f"{BASE_URL}/api/ai/status/{job_id}")  # Fixed endpoint path
        if status_response.status_code != 200:
            print(f"[TEST FAILED] Status check failed: {status_response.status_code}")
            return False
        
        status_data = status_response.json()
        status = status_data.get("status")
        print(f"[TEST] Job status: {status} - {status_data.get('current_stage', '')}")
        
        if status == "completed":
            # Result is embedded in status response when completed
            result_data = status_data.get("result", {})
            
            # Check if result contains deliverables
            if "plan" in result_data and "suggestions_by_department" in result_data["plan"]:
                suggestions = result_data["plan"]["suggestions_by_department"]
                
                # Count total deliverables
                total_deliverables = sum(len(dept_delivs) for dept_delivs in suggestions.values())
                
                print(f"\n[TEST SUCCESS] ✓ AI Analysis returned {total_deliverables} deliverables")
                
                # Show breakdown by department
                for dept, delivs in suggestions.items():
                    print(f"  - {dept}: {len(delivs)} deliverables")
                    # Show first few deliverable names
                    for j, deliv in enumerate(delivs[:3]):
                        print(f"    • {deliv.get('name', deliv.get('title', 'Unknown'))}")
                    if len(delivs) > 3:
                        print(f"    ... and {len(delivs) - 3} more")
                
                # Check diagnostics
                diagnostics = result_data.get("diagnostics", {})
                print(f"\n[TEST DIAGNOSTICS]")
                print(f"  - Catalog items: {diagnostics.get('catalog_items', 0)}")
                print(f"  - Candidates considered: {diagnostics.get('candidates_considered', 0)}")
                print(f"  - Deliverables selected: {diagnostics.get('deliverables_selected', 0)}")
                print(f"  - Deliverables in plan: {diagnostics.get('deliverables_in_plan', 0)}")
                print(f"  - Tasks AI selected: {diagnostics.get('tasks_ai_selected', 0)}")
                print(f"  - Rescue triggered: {diagnostics.get('rescue_triggered', False)}")
                
                # Verify the fix worked
                if total_deliverables > 0:
                    print(f"\n✅ [TEST PASSED] The fix is working! AI analysis is now correctly saving {total_deliverables} deliverables.")
                    return True
                else:
                    print("\n❌ [TEST FAILED] No deliverables found in result. The bug may not be fully fixed.")
                    return False
            else:
                print("[TEST FAILED] Result structure is missing expected fields")
                print(f"Result keys: {result_data.keys()}")
                if "plan" in result_data:
                    print(f"Plan keys: {result_data['plan'].keys()}")
                return False
            
        elif status == "failed":
            error = status_data.get("error", "Unknown error")
            print(f"[TEST FAILED] Job failed with error: {error}")
            return False
    
    print("[TEST FAILED] Job timed out after 60 seconds")
    return False

if __name__ == "__main__":
    # Run the test
    try:
        success = test_ai_analysis()
        if success:
            print("\n🎉 Fix verified successfully!")
        else:
            print("\n⚠️ Fix verification failed. Please check the logs.")
    except Exception as e:
        print(f"\n[TEST ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()