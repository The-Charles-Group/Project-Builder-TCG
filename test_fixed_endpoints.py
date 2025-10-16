#!/usr/bin/env python3
"""Test script for fixed API endpoints"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_endpoint(name, method, path, data=None):
    """Test an endpoint and print results"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Method: {method} {path}")
    if data:
        print(f"Payload: {json.dumps(data, indent=2)}")
    
    try:
        if method == "POST":
            response = requests.post(f"{BASE_URL}{path}", json=data)
        else:
            response = requests.get(f"{BASE_URL}{path}")
        
        print(f"Status: {response.status_code}")
        if response.status_code < 400:
            print("✅ Success!")
            if response.headers.get('content-type', '').startswith('application/json'):
                print(f"Response: {json.dumps(response.json(), indent=2)[:500]}...")
            else:
                print(f"Response: File download ({response.headers.get('content-type')})")
        else:
            print(f"❌ Error: {response.text[:500]}")
    except Exception as e:
        print(f"❌ Connection error: {e}")

def main():
    print("Testing Fixed API Endpoints")
    print("="*60)
    
    # Test 1: /api/pricing/retainer_suggest
    test_endpoint(
        "Retainer Suggest",
        "POST",
        "/api/pricing/retainer_suggest",
        {
            "deliverable_codes": ["DEL-001", "DEL-002"],
            "rfp_text": "We need ongoing social media management and monthly SEO optimization"
        }
    )
    
    # Test 2: /api/pricing/redistribute-hours (simple format)
    test_endpoint(
        "Redistribute Hours (Simple Format)",
        "POST", 
        "/api/pricing/redistribute-hours",
        {
            "deliverable_code": "DEL-001",
            "total_hours": 100
        }
    )
    
    # Test 3: /api/pricing/redistribute-hours (complex format)
    test_endpoint(
        "Redistribute Hours (Complex Format)",
        "POST",
        "/api/pricing/redistribute-hours",
        {
            "deliverable_code": "DEL-001",
            "deliverable_name": "Brand Strategy",
            "new_total_hours": 100,
            "components": [
                {"name": "Research", "current_hours": 30},
                {"name": "Development", "current_hours": 50},
                {"name": "Documentation", "current_hours": 20}
            ]
        }
    )
    
    # Test 4: /api/export (with 'scenarios' plural)
    test_endpoint(
        "Export with 'scenarios' (plural)",
        "POST",
        "/api/export",
        {
            "scenarios": {
                "A": {
                    "items": [
                        {
                            "deliverable_code": "DEL-001",
                            "deliverable": "Test Deliverable",
                            "hours": 10,
                            "blended_rate": 195,
                            "price": 1950
                        }
                    ]
                }
            },
            "file_format": "xlsx",
            "project_name": "Test Project"
        }
    )
    
    # Test 5: /api/export (with 'scenario' singular)
    test_endpoint(
        "Export with 'scenario' (singular)",
        "POST",
        "/api/export",
        {
            "scenario": {
                "items": [
                    {
                        "deliverable_code": "DEL-001",
                        "deliverable": "Test Deliverable",
                        "hours": 10,
                        "blended_rate": 195,
                        "price": 1950
                    }
                ]
            },
            "file_format": "csv",
            "project_name": "Test Project"
        }
    )
    
    # Test 6: /api/export/xml (POST)
    test_endpoint(
        "Export XML (POST endpoint)",
        "POST",
        "/api/export/xml",
        {
            "scenarios": {
                "A": {
                    "items": [
                        {
                            "deliverable_code": "DEL-001",
                            "deliverable": "Test Deliverable",
                            "hours": 10,
                            "blended_rate": 195,
                            "price": 1950
                        }
                    ]
                }
            },
            "project_name": "Test Project XML"
        }
    )
    
    print("\n" + "="*60)
    print("✅ All endpoint tests completed!")
    print("="*60)

if __name__ == "__main__":
    main()