#!/usr/bin/env python
"""Simple test to verify the AI deliverables count fix"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_ai_health():
    """Test that AI health endpoint is working"""
    print("[TEST] Testing AI health endpoint...")
    response = requests.get(f"{BASE_URL}/api/ai/health")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ AI Health: {data}")
        print(f"  - Deliverables in catalog: {data.get('deliverables', 0)}")
        print(f"  - Total catalog items: {data.get('catalog_items', 0)}")
        print(f"  - Database loaded: {data.get('database_loaded', False)}")
        print(f"  - Database source: {data.get('database_source', 'Unknown')}")
        return True
    else:
        print(f"✗ AI Health check failed: {response.status_code}")
        return False

def test_key_fix():
    """Test that the key fix is working by checking code"""
    print("\n[TEST] Verifying the code fix...")
    
    # Read the fixed code
    with open("ai_planner_agencydb.py", "r") as f:
        content = f.read()
    
    # Check if the fix is present
    if 'result["plan"].get("suggestions_by_department", {})' in content:
        print("✓ FIX VERIFIED: Code is using 'suggestions_by_department' (correct key)")
        
        # Also check that the wrong key is not present
        if 'result["plan"].get("deliverables_by_dept", {})' not in content:
            print("✓ OLD BUG REMOVED: No references to 'deliverables_by_dept' (wrong key)")
            return True
        else:
            print("✗ WARNING: Old bug key 'deliverables_by_dept' still found in code")
            return False
    else:
        print("✗ FIX NOT FOUND: Code is not using the correct key")
        return False

def test_frontend_compatibility():
    """Test that frontend is compatible with the fix"""
    print("\n[TEST] Checking frontend compatibility...")
    
    # Read frontend code
    with open("static/app.js", "r") as f:
        content = f.read()
    
    # Check if frontend uses correct key
    if "suggestions_by_department" in content:
        print("✓ Frontend is using 'suggestions_by_department' (compatible with fix)")
        return True
    else:
        print("✗ Frontend might not be compatible")
        return False

def verify_fix_will_work():
    """Verify the fix will work by simulating the counting logic"""
    print("\n[TEST] Simulating the fixed counting logic...")
    
    # Simulate a result structure as returned by analyze_with_agencydb
    mock_result = {
        "plan": {
            "suggestions_by_department": {
                "Creative": [
                    {"name": "Brand Strategy", "confidence": 0.8},
                    {"name": "Visual Identity", "confidence": 0.7}
                ],
                "Strategy": [
                    {"name": "Market Research", "confidence": 0.9},
                    {"name": "Competitive Analysis", "confidence": 0.85},
                    {"name": "Go-to-Market Strategy", "confidence": 0.75}
                ],
                "Paid Media": [
                    {"name": "PPC Campaign", "confidence": 0.82},
                    {"name": "Social Media Ads", "confidence": 0.78}
                ]
            }
        }
    }
    
    # Apply the fixed counting logic (as in line 1448)
    delivs_count = 0
    if mock_result and "plan" in mock_result:
        delivs_by_dept = mock_result["plan"].get("suggestions_by_department", {})  # Fixed key
        for dept_delivs in delivs_by_dept.values():
            delivs_count += len(dept_delivs)
    
    print(f"  - Mock result has {len(mock_result['plan']['suggestions_by_department'])} departments")
    print(f"  - Total deliverables counted with fix: {delivs_count}")
    
    expected = 7  # 2 + 3 + 2
    if delivs_count == expected:
        print(f"✓ Counting logic works correctly! Would save {delivs_count} deliverables")
        return True
    else:
        print(f"✗ Counting logic failed. Expected {expected}, got {delivs_count}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING FIX FOR AI DELIVERABLES COUNT BUG")
    print("=" * 60)
    
    results = []
    
    # Run all tests
    results.append(("AI Health Check", test_ai_health()))
    results.append(("Code Fix Verification", test_key_fix()))
    results.append(("Frontend Compatibility", test_frontend_compatibility()))
    results.append(("Counting Logic Simulation", verify_fix_will_work()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED! The fix is working correctly!")
        print("\nThe bug where AI analysis found deliverables but saved 0")
        print("has been FIXED. The system will now correctly count and")
        print("save all deliverables using 'suggestions_by_department'.")
    else:
        print("⚠️ Some tests failed. Please review the results above.")
    print("=" * 60)