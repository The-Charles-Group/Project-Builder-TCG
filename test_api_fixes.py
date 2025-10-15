#!/usr/bin/env python3
"""
Test script to verify the API fixes for the three failing endpoints.
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_rfp_analysis():
    """Test /api/ai/analyze endpoint"""
    print("\n1. Testing RFP Analysis (/api/ai/analyze)...")
    
    # Test with correct field name: request_text
    payload = {
        "request_text": "We need a comprehensive digital marketing campaign including social media strategy, content creation, and SEO optimization.",
        "mode": "fast",  # Use fast mode for quicker testing
        "tier": "mini"
    }
    
    response = requests.post(f"{BASE_URL}/api/ai/analyze", json=payload)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Success! Job ID: {data.get('job_id')}")
    else:
        print(f"   ✗ Error: {response.text}")
    
    return response.status_code == 200

def test_l3_for():
    """Test /api/l3_for endpoint"""
    print("\n2. Testing L3_for (/api/l3_for)...")
    
    # Test with correct parameter names: deliverable_code and component_name
    params = {
        "deliverable_code": "website",  # Example deliverable code
        "component_name": "design"      # Example component name
    }
    
    response = requests.get(f"{BASE_URL}/api/l3_for", params=params)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Success! Items: {len(data.get('items', []))}")
    else:
        print(f"   ✗ Error: {response.text}")
    
    return response.status_code == 200

def test_pricing_optimization():
    """Test /api/ai/optimize_pricing endpoint"""
    print("\n3. Testing Pricing Optimization (/api/ai/optimize_pricing)...")
    
    # Create a sample scenario with WBS items
    sample_wbs = [
        {
            "Task": "Strategy Development",
            "Hours": 40,
            "Price": 6000,
            "Rate": 150,
            "Seniority": "Senior",
            "Role": "Strategist"
        },
        {
            "Task": "Content Creation",
            "Hours": 80,
            "Price": 8000,
            "Rate": 100,
            "Seniority": "Mid",
            "Role": "Content Creator"
        },
        {
            "Task": "SEO Implementation",
            "Hours": 60,
            "Price": 7200,
            "Rate": 120,
            "Seniority": "Mid",
            "Role": "SEO Specialist"
        }
    ]
    
    # Test with correct field names and structure
    payload = {
        "target_budget": 20000,  # Target budget
        "scenario": {
            "wbs": sample_wbs,  # WBS items
            "total_price": 21200,
            "total_hours": 180
        },
        "company_size": "mid_market",
        "urgency": "standard",
        "maintain_quality_tiers": True
    }
    
    response = requests.post(f"{BASE_URL}/api/ai/optimize_pricing", json=payload)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Success! Optimized pricing received")
    else:
        print(f"   ✗ Error: {response.text}")
    
    return response.status_code == 200

def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing API Fixes")
    print("=" * 60)
    
    results = []
    
    # Test each endpoint
    results.append(("RFP Analysis", test_rfp_analysis()))
    results.append(("L3_for", test_l3_for()))
    results.append(("Pricing Optimization", test_pricing_optimization()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary:")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All tests passed successfully!")
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")
    
    return all_passed

if __name__ == "__main__":
    main()