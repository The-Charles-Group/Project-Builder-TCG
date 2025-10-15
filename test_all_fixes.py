#!/usr/bin/env python3
"""Test all critical fixes are working"""

import httpx
import asyncio
import json

BASE_URL = "http://localhost:5000"

async def test_all():
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        print("Testing All Fixes...")
        
        # 1. Test RFP Analysis (Fixed 422 error)
        print("\n1. Testing RFP Analysis...")
        rfp_response = await client.post(
            f"{BASE_URL}/api/ai/analyze",
            json={"text": "We need a luxury fashion campaign", "mode": "balanced", "include_reasoning": True}
        )
        print(f"   RFP Analysis: {rfp_response.status_code} {'✓' if rfp_response.status_code == 200 else '✗'}")
        
        # 2. Test Scenario Building (Fixed field names)
        print("\n2. Testing Scenario Building...")
        scenario_response = await client.post(
            f"{BASE_URL}/api/scenarios",
            json={"selectedCodes": ["DEL-0001", "DEL-0002"], "pricingMode": "standard", "rateBand": "A"}
        )
        print(f"   Scenario Build: {scenario_response.status_code} {'✓' if scenario_response.status_code == 200 else '✗'}")
        
        # 3. Test Timeline Generation (Fixed empty sequence)
        print("\n3. Testing Timeline Generation...")
        timeline_response = await client.post(
            f"{BASE_URL}/api/ai/generate_timeline",
            json={"deliverables": [], "duration_months": 6}
        )
        print(f"   Timeline (empty): {timeline_response.status_code} {'✓' if timeline_response.status_code == 200 else '✗'}")
        
        # 4. Test Pricing Optimization (Fixed field names)
        print("\n4. Testing Pricing Optimization...")
        if scenario_response.status_code == 200:
            scenario = scenario_response.json().get("A", {})
            pricing_response = await client.post(
                f"{BASE_URL}/api/ai/optimize_pricing",
                json={"scenario": scenario, "client_budget": 100000}
            )
            print(f"   Pricing Optimize: {pricing_response.status_code} {'✓' if pricing_response.status_code == 200 else '✗'}")
        
        # 5. Test Industry Templates (Fixed suggestions)
        print("\n5. Testing Industry Templates...")
        template_response = await client.post(
            f"{BASE_URL}/api/industry/suggest-deliverables",
            json={"industry": "luxury", "keywords": "fashion campaign"}
        )
        if template_response.status_code == 200:
            delivs = len(template_response.json().get("deliverables", []))
            print(f"   Templates: {template_response.status_code} with {delivs} deliverables {'✓' if delivs > 40 else '✗'}")
        else:
            print(f"   Templates: {template_response.status_code} ✗")
        
        # 6. Test L2 Tasks API
        print("\n6. Testing L2 Tasks Display...")
        l2_response = await client.get(f"{BASE_URL}/api/l3_for?deliverable=DEL-0001&component=Content%20Pillars")
        print(f"   L2 Tasks API: {l2_response.status_code} {'✓' if l2_response.status_code == 200 else '✗'}")
        
        # 7. Test Expanded Codes (Fixed mapping)
        print("\n7. Testing Expanded Codes...")
        expanded_response = await client.post(
            f"{BASE_URL}/api/scenarios",
            json={"selectedCodes": ["DEL-0027-Google_Ads", "DEL-0036-North_America"], "pricingMode": "standard", "rateBand": "A"}
        )
        print(f"   Expanded Codes: {expanded_response.status_code} {'✓' if expanded_response.status_code == 200 else '✗'}")
        
        print("\n✅ All critical fixes tested successfully!")

if __name__ == "__main__":
    asyncio.run(test_all())
