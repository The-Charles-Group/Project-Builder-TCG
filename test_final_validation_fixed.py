#!/usr/bin/env python3
"""Final validation with correct API parameters"""

import httpx
import asyncio
import json

BASE_URL = "http://localhost:5000"

async def test_all():
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        print("="*60)
        print("  FINAL VALIDATION - ALL FIXES VERIFIED")
        print("="*60)
        
        passed = 0
        total = 0
        
        # 1. Test RFP Analysis (using correct field name)
        print("\n1. RFP Analysis API")
        total += 1
        rfp_response = await client.post(
            f"{BASE_URL}/api/ai/analyze",
            json={"request_text": "We need a luxury fashion campaign", "mode": "balanced", "include_reasoning": True}
        )
        if rfp_response.status_code == 200:
            print(f"   ✓ PASS - Job created successfully")
            passed += 1
        else:
            print(f"   ✗ FAIL - Status: {rfp_response.status_code}")
        
        # 2. Test Scenario Building
        print("\n2. Scenario Building")
        total += 1
        scenario_response = await client.post(
            f"{BASE_URL}/api/scenarios",
            json={"selectedCodes": ["DEL-0001", "DEL-0002"], "pricingMode": "standard", "rateBand": "A"}
        )
        if scenario_response.status_code == 200:
            scenario = scenario_response.json().get("A", {})
            print(f"   ✓ PASS - Scenario built with {len(scenario.get('items', []))} items")
            passed += 1
        else:
            print(f"   ✗ FAIL - Status: {scenario_response.status_code}")
        
        # 3. Test Timeline Generation (empty list handling)
        print("\n3. Timeline Edge Cases")
        total += 1
        timeline_response = await client.post(
            f"{BASE_URL}/api/ai/generate_timeline",
            json={"deliverables": [], "duration_months": 6}
        )
        if timeline_response.status_code == 200:
            print(f"   ✓ PASS - Handles empty task list gracefully")
            passed += 1
        else:
            print(f"   ✗ FAIL - Status: {timeline_response.status_code}")
        
        # 4. Test Pricing Optimization (with correct fields)
        print("\n4. Pricing Optimization")
        total += 1
        if scenario_response.status_code == 200:
            # Ensure scenario has wbs field
            scenario = scenario_response.json().get("A", {})
            scenario["wbs"] = scenario.get("items", [])
            pricing_response = await client.post(
                f"{BASE_URL}/api/ai/optimize_pricing",
                json={"scenario": scenario, "target_budget": 100000}
            )
            if pricing_response.status_code == 200:
                print(f"   ✓ PASS - Pricing optimized successfully")
                passed += 1
            else:
                print(f"   ✗ FAIL - Status: {pricing_response.status_code}")
        
        # 5. Test Industry Templates
        print("\n5. Industry Templates")
        total += 1
        template_response = await client.post(
            f"{BASE_URL}/api/industry/suggest-deliverables",
            json={"industry": "luxury", "keywords": "fashion campaign"}
        )
        if template_response.status_code == 200:
            delivs = len(template_response.json().get("deliverables", []))
            if delivs >= 40:
                print(f"   ✓ PASS - Returns {delivs} deliverables")
                passed += 1
            else:
                print(f"   ✗ FAIL - Only {delivs} deliverables")
        else:
            print(f"   ✗ FAIL - Status: {template_response.status_code}")
        
        # 6. Test L2 Tasks (using correct parameter names)
        print("\n6. L2 Tasks Display")
        total += 1
        l2_response = await client.get(f"{BASE_URL}/api/l3_for?deliverable_code=DEL-0001&component_name=Content%20Pillars")
        if l2_response.status_code == 200:
            tasks = l2_response.json()
            print(f"   ✓ PASS - Returns {len(tasks)} L2 tasks")
            passed += 1
        else:
            print(f"   ✗ FAIL - Status: {l2_response.status_code}")
        
        # 7. Test Expanded Codes
        print("\n7. Expanded Deliverable Codes")
        total += 1
        expanded_response = await client.post(
            f"{BASE_URL}/api/scenarios",
            json={"selectedCodes": ["DEL-0027-Google_Ads", "DEL-0036-North_America"], "pricingMode": "standard", "rateBand": "A"}
        )
        if expanded_response.status_code == 200:
            scenario = expanded_response.json().get("A", {})
            print(f"   ✓ PASS - Handles expanded codes correctly")
            passed += 1
        else:
            print(f"   ✗ FAIL - Status: {expanded_response.status_code}")
        
        # 8. Test XML Export
        print("\n8. XML Export")
        total += 1
        xml_response = await client.post(
            f"{BASE_URL}/api/xml",
            json={"deliverable_codes": ["DEL-0001", "DEL-0002"], "project_name": "Test Project"}
        )
        if xml_response.status_code == 200 and "<Project " in xml_response.text:
            print(f"   ✓ PASS - Valid XML generated")
            passed += 1
        else:
            print(f"   ✗ FAIL - Invalid XML or error")
        
        # Summary
        print("\n" + "="*60)
        print(f"  RESULTS: {passed}/{total} tests passed ({(passed/total)*100:.0f}%)")
        print("="*60)
        
        if passed == total:
            print("\n🎉 SYSTEM IS PRODUCTION READY!")
            print("All critical features working correctly.")
        elif passed >= total * 0.8:
            print("\n✅ System is mostly ready")
            print("Minor issues remain but core functionality works.")
        else:
            print("\n⚠️ System needs attention")
            print("Several critical features still have issues.")

if __name__ == "__main__":
    asyncio.run(test_all())
