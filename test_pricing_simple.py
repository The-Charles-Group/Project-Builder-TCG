#!/usr/bin/env python3
"""
Simple test for pricing optimization endpoint
Tests the /api/ai/optimize_pricing endpoint directly with hardcoded scenarios
"""

import json
import httpx
from datetime import datetime

BASE_URL = "http://localhost:5000"

def print_test_header(title):
    print("\n" + "="*60)
    print(title.center(60))
    print("="*60 + "\n")

def create_test_scenario():
    """Create a simple test scenario with hardcoded WBS items"""
    return {
        "wbs": [
            {
                "Deliverable_Code": "DECK001",
                "Deliverable": "Brand Strategy Deck",
                "Component": "Research",
                "Task": "Market Analysis",
                "Hours": 40,
                "Rate": 200,
                "Price": 8000,
                "Seniority": "Senior"
            },
            {
                "Deliverable_Code": "DECK001", 
                "Deliverable": "Brand Strategy Deck",
                "Component": "Development",
                "Task": "Strategy Development",
                "Hours": 60,
                "Rate": 250,
                "Price": 15000,
                "Seniority": "Director"
            },
            {
                "Deliverable_Code": "CREATIVE001",
                "Deliverable": "Creative Campaign",
                "Component": "Design",
                "Task": "Visual Design",
                "Hours": 80,
                "Rate": 175,
                "Price": 14000,
                "Seniority": "Mid"
            },
            {
                "Deliverable_Code": "CREATIVE001",
                "Deliverable": "Creative Campaign", 
                "Component": "Production",
                "Task": "Asset Production",
                "Hours": 100,
                "Rate": 150,
                "Price": 15000,
                "Seniority": "Mid"
            },
            {
                "Deliverable_Code": "PAID001",
                "Deliverable": "Paid Media Management",
                "Component": "Setup",
                "Task": "Campaign Setup",
                "Hours": 30,
                "Rate": 175,
                "Price": 5250,
                "Seniority": "Senior"
            },
            {
                "Deliverable_Code": "PAID001",
                "Deliverable": "Paid Media Management",
                "Component": "Management",
                "Task": "Ongoing Management",
                "Hours": 120,
                "Rate": 150,
                "Price": 18000,
                "Seniority": "Mid"
            }
        ],
        "total_price": 75250
    }

def test_budget_optimization():
    """Test pricing optimization with different budget targets"""
    print_test_header("PRICING OPTIMIZATION TESTS")
    
    scenario = create_test_scenario()
    original_total = sum(float(item["Price"]) for item in scenario["wbs"])
    print(f"Original Total Price: ${original_total:,.2f}")
    
    # Test different budget targets
    test_cases = [
        {
            "name": "Low Budget ($100K)",
            "target_budget": 100000,
            "expected": "Should increase prices from $75K to $100K"
        },
        {
            "name": "Very Low Budget ($50K)", 
            "target_budget": 50000,
            "expected": "Should decrease prices from $75K to $50K"
        },
        {
            "name": "High Budget ($500K)",
            "target_budget": 500000,
            "expected": "Should increase prices significantly"
        },
        {
            "name": "With Company Size - Startup",
            "target_budget": 100000,
            "company_size": "startup",
            "expected": "Should apply startup discount"
        },
        {
            "name": "With Urgency - Rush",
            "target_budget": 100000,
            "urgency": "rush",
            "expected": "Should apply rush premium"
        },
        {
            "name": "With Industry Multiplier - Luxury",
            "target_budget": 100000,
            "industry_multiplier": 1.5,
            "expected": "Should apply luxury multiplier"
        },
        {
            "name": "Combined Factors",
            "target_budget": 200000,
            "company_size": "enterprise",
            "urgency": "rush", 
            "industry_multiplier": 1.3,
            "expected": "Should combine all factors"
        },
        {
            "name": "Edge Case - Very Low Budget ($10K)",
            "target_budget": 10000,
            "expected": "Should either optimize or return error for minimum viable"
        }
    ]
    
    passed = 0
    failed = 0
    
    with httpx.Client(timeout=30.0) as client:
        for test_case in test_cases:
            print(f"\nTest: {test_case['name']}")
            print(f"Expected: {test_case['expected']}")
            
            # Build request
            request_data = {
                "scenario": scenario,
                "target_budget": test_case["target_budget"],
                "maintain_quality_tiers": True
            }
            
            # Add optional parameters
            if "company_size" in test_case:
                request_data["company_size"] = test_case["company_size"]
            if "urgency" in test_case:
                request_data["urgency"] = test_case["urgency"]
            if "industry_multiplier" in test_case:
                request_data["industry_multiplier"] = test_case["industry_multiplier"]
            
            try:
                # Call the API
                response = client.post(
                    f"{BASE_URL}/api/ai/optimize_pricing",
                    json=request_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    optimized_total = result.get("total_price", 0)
                    optimization_details = result.get("optimization_details", {})
                    
                    print(f"  Target Budget: ${test_case['target_budget']:,.2f}")
                    print(f"  Achieved Total: ${optimized_total:,.2f}")
                    print(f"  Original Total: ${optimization_details.get('original_total', 0):,.2f}")
                    print(f"  Optimization Ratio: {optimization_details.get('optimization_ratio', 0):.2f}x")
                    
                    # Check if optimization worked
                    variance = abs(optimized_total - test_case['target_budget'])
                    variance_pct = (variance / test_case['target_budget']) * 100 if test_case['target_budget'] > 0 else 0
                    
                    if variance_pct <= 1:  # Within 1% of target
                        print(f"  ✓ PASSED - Within 1% of target (variance: {variance_pct:.2f}%)")
                        passed += 1
                    else:
                        print(f"  ✗ FAILED - Variance too high: {variance_pct:.2f}%")
                        failed += 1
                        
                    # Show sample of optimized rates
                    if result.get("wbs"):
                        print("  Sample optimized rates:")
                        for item in result["wbs"][:3]:  # Show first 3
                            print(f"    - {item.get('Task', 'Unknown')}: ${item.get('Rate', 0):.2f}/hr (was ${scenario['wbs'][0]['Rate']}/hr)")
                            
                elif response.status_code == 400:
                    error_data = response.json()
                    error_msg = error_data.get("error", error_data.get("detail", "Unknown error"))
                    
                    if "Budget too low" in error_msg:
                        min_viable = error_data.get("minimum_viable", 0)
                        print(f"  ⚠ Budget too low - Minimum viable: ${min_viable:,.2f}")
                        if test_case["name"].startswith("Edge Case"):
                            print(f"  ✓ PASSED - Correctly rejected very low budget")
                            passed += 1
                        else:
                            print(f"  ✗ FAILED - Should have been able to optimize")
                            failed += 1
                    else:
                        print(f"  ✗ FAILED - Error: {error_msg}")
                        failed += 1
                else:
                    print(f"  ✗ FAILED - Unexpected status code: {response.status_code}")
                    print(f"  Response: {response.text}")
                    failed += 1
                    
            except Exception as e:
                print(f"  ✗ FAILED - Exception: {str(e)}")
                failed += 1
    
    # Print summary
    print_test_header("TEST SUMMARY")
    print(f"Total Tests: {passed + failed}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n✓ ALL TESTS PASSED!")
    else:
        print(f"\n✗ {failed} tests failed")
    
    return passed, failed

if __name__ == "__main__":
    print("Starting Pricing Optimization Simple Tests")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing endpoint: {BASE_URL}/api/ai/optimize_pricing")
    
    passed, failed = test_budget_optimization()
    
    # Save results
    results = {
        "timestamp": datetime.now().isoformat(),
        "passed": passed,
        "failed": failed,
        "endpoint": f"{BASE_URL}/api/ai/optimize_pricing"
    }
    
    with open("test_pricing_simple_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to test_pricing_simple_results.json")