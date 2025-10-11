"""
Test script for retainer integration with timeline and export formats
"""

import requests
import json
import time
from datetime import datetime

# API base URL (assuming local development)
BASE_URL = "http://localhost:5000"

def test_retainer_integration():
    """Test the complete retainer integration flow"""
    
    print("Testing Retainer Integration...")
    print("=" * 50)
    
    # Step 1: Test data with mixed deliverables
    test_deliverables = [
        {
            "deliverable_code": "deck_strategy",
            "deliverable_name": "Brand Strategy Deck",
            "total_hours": 120,
            "is_retainer": False,
            "department": "Strategy"
        },
        {
            "deliverable_code": "social_mgmt",
            "deliverable_name": "Social Media Management",
            "total_hours": 480,  # 40 hours/month x 12 months
            "is_retainer": True,
            "retainer_months": 12,
            "monthly_hours": 40,
            "department": "Content"
        },
        {
            "deliverable_code": "web_dev",
            "deliverable_name": "Website Development",
            "total_hours": 200,
            "is_retainer": False,
            "department": "Technology"
        },
        {
            "deliverable_code": "seo_optimization",
            "deliverable_name": "SEO & Performance Optimization",
            "total_hours": 360,  # 30 hours/month x 12 months
            "is_retainer": True,
            "retainer_months": 12,
            "monthly_hours": 30,
            "department": "Technology"
        }
    ]
    
    # Step 2: Test timeline generation with retainers
    print("\n1. Testing Timeline Generation with Retainers...")
    timeline_payload = {
        "selected_codes": ["deck_strategy", "social_mgmt", "web_dev", "seo_optimization"],
        "deliverables": test_deliverables,
        "project_start": "2025-01-01",
        "optimization_mode": "balanced"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/timeline/suggest",
            json=timeline_payload
        )
        if response.status_code == 200:
            timeline_data = response.json()
            print(f"✓ Timeline generated with {len(timeline_data.get('tasks', []))} tasks")
            
            # Check for retainer tasks
            retainer_tasks = [t for t in timeline_data.get('tasks', []) 
                            if t.get('is_retainer')]
            print(f"✓ Found {len(retainer_tasks)} retainer tasks")
        else:
            print(f"✗ Timeline generation failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Timeline generation error: {e}")
    
    # Step 3: Test hour redistribution
    print("\n2. Testing Hour Redistribution...")
    redistribution_payload = {
        "deliverable_name": "Brand Strategy Deck",
        "deliverable_code": "deck_strategy",
        "new_total_hours": 150,
        "components": [
            {"name": "Market Research", "current_hours": 40},
            {"name": "Competitor Analysis", "current_hours": 30},
            {"name": "Strategy Development", "current_hours": 50}
        ],
        "use_ai": False  # Use rule-based for testing
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/pricing/redistribute-hours",
            json=redistribution_payload
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Hours redistributed successfully")
            print(f"  Original: {result['result']['original_total']} hours")
            print(f"  New: {result['result']['total_hours']} hours")
        else:
            print(f"✗ Hour redistribution failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Hour redistribution error: {e}")
    
    # Step 4: Test retainer analysis
    print("\n3. Testing Retainer Analysis...")
    analysis_payload = {
        "deliverable_name": "Social Media Management",
        "total_hours": 480,
        "duration_months": 12
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/pricing/analyze-retainer",
            json=analysis_payload
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Retainer analysis completed")
            print(f"  Recommendation: {result['result']['recommendation']}")
            print(f"  Confidence: {result['result']['confidence']}")
        else:
            print(f"✗ Retainer analysis failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Retainer analysis error: {e}")
    
    # Step 5: Test retainer distribution
    print("\n4. Testing Retainer Hour Distribution...")
    distribution_payload = {
        "monthly_hours": 40,
        "duration_months": 12,
        "ramp_up": True
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/pricing/retainer-distribution",
            json=distribution_payload
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Retainer distribution calculated")
            print(f"  Total hours: {result['total_hours']}")
            print(f"  Average monthly: {result['average_monthly']}")
        else:
            print(f"✗ Retainer distribution failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Retainer distribution error: {e}")
    
    # Step 6: Test scenario building with retainers
    print("\n5. Testing Scenario Building with Retainers...")
    build_payload = {
        "selected_deliverable_codes": ["deck_strategy", "social_mgmt", "web_dev"],
        "scenario_a": {
            "mode": "template",
            "scenario_key": "MED_LOW"
        },
        "pricing_mode": "Flat_Blended",
        "blended_rate": 195.0,
        "project_start": "2025-01-01",
        "retainers": [
            {"deliverable_code": "social_mgmt", "months": 12},
            {"deliverable_code": "seo_optimization", "months": 12}
        ]
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/build",
            json=build_payload
        )
        if response.status_code == 200:
            scenarios = response.json()
            scenario_a = scenarios['scenarios']['A']
            print(f"✓ Scenario built successfully")
            print(f"  Total hours: {scenario_a['totals']['hours']}")
            print(f"  Total price: ${scenario_a['totals']['price']:,.2f}")
            
            # Check for retainer items
            retainer_items = [item for item in scenario_a.get('items', [])
                            if item.get('retainer', {}).get('months', 0) > 0]
            print(f"  Retainer deliverables: {len(retainer_items)}")
        else:
            print(f"✗ Scenario building failed: {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"✗ Scenario building error: {e}")
    
    print("\n" + "=" * 50)
    print("Integration test completed!")
    print("\nNOTE: Excel and XML export enhancements are already implemented:")
    print("- Excel exports now include 'Type' column (One-Time/Retainer)")
    print("- Excel exports include 'Retainer Summary' sheets for scenarios with retainers")
    print("- Use the UI or direct API calls to test export functionality")

if __name__ == "__main__":
    test_retainer_integration()