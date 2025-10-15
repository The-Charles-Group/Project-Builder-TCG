#!/usr/bin/env python
"""
Comprehensive Industry Templates Test Suite
Tests all 6 industry templates across all API endpoints
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import sys

# Base URL for API
BASE_URL = "http://localhost:5000"

# Test results storage
test_results = {
    "templates_endpoint": {},
    "suggest_deliverables": {},
    "calculate_timeline": {},
    "calculate_pricing": {},
    "edge_cases": {},
    "errors": []
}

# Industry-specific test keywords
INDUSTRY_KEYWORDS = {
    "luxury_fashion": [
        "fashion show", "paris fashion week", "spring summer collection", 
        "lookbook", "editorial campaign", "influencer", "celebrity ambassador",
        "flagship store", "heritage brand", "haute couture", "ready to wear"
    ],
    "beauty": [
        "product launch", "skincare", "makeup collection", "tutorial",
        "clinical study", "dermatologist", "sephora", "ulta", "clean beauty",
        "sustainable packaging", "influencer seeding", "masterclass"
    ],
    "real_estate": [
        "property launch", "residential development", "commercial office",
        "virtual tour", "broker event", "model home", "lease up",
        "mixed use", "pre construction", "sales center", "investment deck"
    ],
    "retail": [
        "omnichannel campaign", "black friday", "holiday season",
        "loyalty program", "store opening", "ecommerce", "BOPIS",
        "inventory management", "POS system", "pop up store"
    ],
    "lifestyle": [
        "brand partnership", "wellness retreat", "community event",
        "sustainable living", "mindfulness", "food beverage",
        "travel hospitality", "home design", "workshop", "experience design"
    ],
    "technology": [
        "product launch", "software release", "cloud migration",
        "developer conference", "beta testing", "API documentation",
        "trade show", "CES", "SaaS platform", "hardware device"
    ]
}

def test_templates_endpoint():
    """Test /api/industry/templates endpoint"""
    print("\n" + "="*60)
    print("Testing /api/industry/templates endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/api/industry/templates")
        data = response.json()
        
        if response.status_code == 200:
            templates = data.get("templates", [])
            print(f"✓ Endpoint responded with {len(templates)} templates")
            
            # Check all 6 templates are present
            expected_templates = ["luxury_fashion", "beauty", "real_estate", "retail", "lifestyle", "technology"]
            found_templates = [t["value"] for t in templates]
            
            for expected in expected_templates:
                if expected in found_templates:
                    print(f"✓ Found template: {expected}")
                else:
                    print(f"✗ Missing template: {expected}")
                    test_results["errors"].append(f"Missing template: {expected}")
            
            test_results["templates_endpoint"] = {
                "status": "success",
                "templates_found": len(templates),
                "templates": templates
            }
            
            # Display template metadata
            print("\nTemplate Metadata:")
            for template in templates:
                print(f"  - {template['label']}: Available={template.get('available', False)}")
        else:
            print(f"✗ Failed with status {response.status_code}")
            test_results["templates_endpoint"]["status"] = "failed"
            test_results["errors"].append(f"Templates endpoint failed with status {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        test_results["templates_endpoint"]["status"] = "error"
        test_results["errors"].append(f"Templates endpoint error: {str(e)}")

def test_suggest_deliverables(industry: str, keywords: List[str]):
    """Test /api/industry/suggest-deliverables for a specific industry"""
    print(f"\n--- Testing {industry} deliverables ---")
    
    try:
        # Test with keywords
        payload = {
            "industry": industry,
            "rfp_text": " ".join(keywords)
        }
        
        response = requests.post(
            f"{BASE_URL}/api/industry/suggest-deliverables",
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            deliverables = data.get("deliverables", [])
            keywords_found = data.get("keywords_found", [])
            
            print(f"  Keywords sent: {len(keywords)}")
            print(f"  Keywords found: {keywords_found[:5]}...")  # Show first 5
            print(f"  ✓ Deliverables returned: {len(deliverables)}")
            
            if len(deliverables) < 40:
                print(f"  ⚠ Warning: Only {len(deliverables)} deliverables (expected 40-70)")
                test_results["errors"].append(f"{industry}: Low deliverable count ({len(deliverables)})")
            
            # Store results
            if industry not in test_results["suggest_deliverables"]:
                test_results["suggest_deliverables"][industry] = {}
            
            test_results["suggest_deliverables"][industry]["with_keywords"] = {
                "status": "success",
                "count": len(deliverables),
                "keywords_found": keywords_found,
                "sample_deliverables": deliverables[:3] if deliverables else []
            }
            
            # Display sample deliverables
            if deliverables:
                print(f"  Sample deliverables:")
                for deliv in deliverables[:3]:
                    print(f"    - {deliv.get('code', 'N/A')}: {deliv.get('name', 'N/A')} (Hours: {deliv.get('base_hours', 'N/A')})")
            
        else:
            print(f"  ✗ Failed with status {response.status_code}")
            test_results["suggest_deliverables"][industry] = {"status": "failed"}
            test_results["errors"].append(f"{industry} suggest deliverables failed: {response.status_code}")
            
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        test_results["suggest_deliverables"][industry] = {"status": "error", "error": str(e)}
        test_results["errors"].append(f"{industry} suggest deliverables error: {str(e)}")
    
    # Test without keywords (empty RFP)
    try:
        print(f"  Testing empty RFP...")
        payload = {
            "industry": industry,
            "rfp_text": ""
        }
        
        response = requests.post(
            f"{BASE_URL}/api/industry/suggest-deliverables",
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            deliverables = data.get("deliverables", [])
            print(f"  ✓ Empty RFP returned: {len(deliverables)} deliverables")
            
            test_results["suggest_deliverables"][industry]["without_keywords"] = {
                "status": "success",
                "count": len(deliverables)
            }
    except Exception as e:
        print(f"  ✗ Empty RFP test error: {str(e)}")

def test_calculate_timeline(industry: str):
    """Test /api/industry/calculate-timeline for a specific industry"""
    print(f"\n--- Testing {industry} timeline calculation ---")
    
    try:
        # First get some deliverable codes
        payload = {
            "industry": industry,
            "rfp_text": " ".join(INDUSTRY_KEYWORDS[industry][:5])
        }
        
        response = requests.post(
            f"{BASE_URL}/api/industry/suggest-deliverables",
            json=payload
        )
        
        if response.status_code == 200:
            deliverables = response.json().get("deliverables", [])
            if deliverables:
                # Take first 5 deliverable codes for timeline test
                deliverable_codes = [d["code"] for d in deliverables[:5]]
                
                # Test timeline calculation
                timeline_payload = {
                    "industry": industry,
                    "deliverable_codes": deliverable_codes,
                    "start_date": datetime.now().isoformat()
                }
                
                # Add industry-specific parameters
                if industry == "real_estate":
                    timeline_payload["project_phase"] = "sales_launch"
                
                timeline_response = requests.post(
                    f"{BASE_URL}/api/industry/calculate-timeline",
                    json=timeline_payload
                )
                
                if timeline_response.status_code == 200:
                    timeline_data = timeline_response.json()
                    timeline = timeline_data.get("timeline", {})
                    
                    print(f"  ✓ Timeline calculated for {len(deliverable_codes)} deliverables")
                    print(f"  Duration: {timeline.get('duration_weeks', 'N/A')} weeks")
                    print(f"  Phases: {len(timeline.get('phases', []))}")
                    
                    # Check for proper phases
                    phases = timeline.get("phases", [])
                    if phases:
                        print("  Phase breakdown:")
                        for phase in phases[:3]:  # Show first 3 phases
                            print(f"    - {phase.get('name', 'N/A')}: {phase.get('duration_weeks', 'N/A')} weeks")
                    
                    test_results["calculate_timeline"][industry] = {
                        "status": "success",
                        "duration_weeks": timeline.get("duration_weeks"),
                        "phase_count": len(phases)
                    }
                else:
                    print(f"  ✗ Timeline calculation failed: {timeline_response.status_code}")
                    test_results["calculate_timeline"][industry] = {"status": "failed"}
                    test_results["errors"].append(f"{industry} timeline calculation failed")
                
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        test_results["calculate_timeline"][industry] = {"status": "error", "error": str(e)}
        test_results["errors"].append(f"{industry} timeline error: {str(e)}")

def test_calculate_pricing(industry: str):
    """Test /api/industry/calculate-pricing for a specific industry"""
    print(f"\n--- Testing {industry} pricing calculation ---")
    
    try:
        # First get some deliverable codes
        payload = {
            "industry": industry,
            "rfp_text": " ".join(INDUSTRY_KEYWORDS[industry][:5])
        }
        
        response = requests.post(
            f"{BASE_URL}/api/industry/suggest-deliverables",
            json=payload
        )
        
        if response.status_code == 200:
            deliverables = response.json().get("deliverables", [])
            if deliverables:
                # Take first 5 deliverable codes for pricing test
                deliverable_codes = [d["code"] for d in deliverables[:5]]
                
                # Test with different base rates
                base_rates = [150, 250]  # Normal and premium rates
                
                for base_rate in base_rates:
                    pricing_payload = {
                        "industry": industry,
                        "deliverable_codes": deliverable_codes,
                        "base_rate": base_rate
                    }
                    
                    # Add industry-specific parameters
                    if industry == "real_estate":
                        pricing_payload["property_type"] = "luxury"
                        pricing_payload["num_phases"] = 2
                    
                    pricing_response = requests.post(
                        f"{BASE_URL}/api/industry/calculate-pricing",
                        json=pricing_payload
                    )
                    
                    if pricing_response.status_code == 200:
                        pricing_data = pricing_response.json()
                        pricing = pricing_data.get("pricing", {})
                        
                        print(f"  ✓ Pricing at ${base_rate}/hr:")
                        print(f"    Subtotal: ${pricing.get('subtotal', 0):,.0f}")
                        # Calculate total adjustments from list
                        adjustments_total = 0
                        adjustments = pricing.get("adjustments", [])
                        if isinstance(adjustments, list):
                            adjustments_total = sum(adj.get("amount", 0) for adj in adjustments)
                        elif isinstance(adjustments, dict):
                            adjustments_total = adjustments.get("total", 0)
                        print(f"    Adjustments: ${adjustments_total:,.0f}")
                        print(f"    Total: ${pricing.get('total', 0):,.0f}")
                        
                        # Check for multipliers being applied
                        adjustments = pricing.get("adjustments", {})
                        if adjustments:
                            print(f"    Multipliers applied: {list(adjustments.keys())}")
                        
                        if industry not in test_results["calculate_pricing"]:
                            test_results["calculate_pricing"][industry] = {}
                        
                        test_results["calculate_pricing"][industry][f"rate_{base_rate}"] = {
                            "status": "success",
                            "total": pricing.get("total", 0),
                            "has_adjustments": bool(adjustments)
                        }
                    else:
                        print(f"  ✗ Pricing calculation failed at ${base_rate}/hr")
                        test_results["errors"].append(f"{industry} pricing failed at ${base_rate}/hr")
                
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        test_results["calculate_pricing"][industry] = {"status": "error", "error": str(e)}
        test_results["errors"].append(f"{industry} pricing error: {str(e)}")

def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n" + "="*60)
    print("Testing Edge Cases")
    print("="*60)
    
    edge_case_results = {}
    
    # Test 1: Mixed industry keywords
    print("\n1. Mixed Industry Keywords Test (fashion + technology)")
    try:
        payload = {
            "industry": "luxury_fashion",
            "rfp_text": "fashion show with virtual reality technology and livestreaming digital runway"
        }
        response = requests.post(f"{BASE_URL}/api/industry/suggest-deliverables", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Handled mixed keywords - returned {len(data.get('deliverables', []))} deliverables")
            edge_case_results["mixed_keywords"] = "passed"
        else:
            print(f"  ✗ Failed with status {response.status_code}")
            edge_case_results["mixed_keywords"] = "failed"
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        edge_case_results["mixed_keywords"] = "error"
    
    # Test 2: Invalid industry selection
    print("\n2. Invalid Industry Selection Test")
    try:
        payload = {
            "industry": "invalid_industry",
            "rfp_text": "test text"
        }
        response = requests.post(f"{BASE_URL}/api/industry/suggest-deliverables", json=payload)
        data = response.json()
        if "error" in data or "message" in data:
            print(f"  ✓ Properly handled invalid industry: {data.get('message', data.get('error'))}")
            edge_case_results["invalid_industry"] = "passed"
        else:
            print(f"  ✗ Did not properly handle invalid industry")
            edge_case_results["invalid_industry"] = "failed"
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        edge_case_results["invalid_industry"] = "error"
    
    # Test 3: Empty industry selection
    print("\n3. Empty Industry Selection Test")
    try:
        payload = {
            "industry": "",
            "rfp_text": "test text"
        }
        response = requests.post(f"{BASE_URL}/api/industry/suggest-deliverables", json=payload)
        data = response.json()
        if "error" in data or "message" in data:
            print(f"  ✓ Properly handled empty industry: {data.get('message', data.get('error'))}")
            edge_case_results["empty_industry"] = "passed"
        else:
            print(f"  ✗ Did not properly handle empty industry")
            edge_case_results["empty_industry"] = "failed"
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        edge_case_results["empty_industry"] = "error"
    
    # Test 4: Very large text input
    print("\n4. Large Text Input Test")
    try:
        large_text = " ".join(INDUSTRY_KEYWORDS["luxury_fashion"] * 100)  # Very large input
        payload = {
            "industry": "luxury_fashion",
            "rfp_text": large_text[:10000]  # Limit to 10k chars
        }
        response = requests.post(f"{BASE_URL}/api/industry/suggest-deliverables", json=payload)
        if response.status_code == 200:
            print(f"  ✓ Handled large text input successfully")
            edge_case_results["large_text"] = "passed"
        else:
            print(f"  ✗ Failed with large text: {response.status_code}")
            edge_case_results["large_text"] = "failed"
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        edge_case_results["large_text"] = "error"
    
    # Test 5: Special characters and unicode
    print("\n5. Special Characters Test")
    try:
        payload = {
            "industry": "beauty",
            "rfp_text": "Launch für Schönheit products with émoji 🌸 and spëcial cháracters"
        }
        response = requests.post(f"{BASE_URL}/api/industry/suggest-deliverables", json=payload)
        if response.status_code == 200:
            print(f"  ✓ Handled special characters successfully")
            edge_case_results["special_chars"] = "passed"
        else:
            print(f"  ✗ Failed with special characters: {response.status_code}")
            edge_case_results["special_chars"] = "failed"
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        edge_case_results["special_chars"] = "error"
    
    test_results["edge_cases"] = edge_case_results

def test_template_switching():
    """Test switching between templates to ensure no data contamination"""
    print("\n" + "="*60)
    print("Testing Template Switching (No Data Contamination)")
    print("="*60)
    
    try:
        # Test quick succession of different industries
        industries = ["luxury_fashion", "beauty", "real_estate"]
        previous_deliverables = None
        
        for industry in industries:
            payload = {
                "industry": industry,
                "rfp_text": "product launch campaign"  # Generic text
            }
            response = requests.post(f"{BASE_URL}/api/industry/suggest-deliverables", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                deliverables = data.get("deliverables", [])
                
                print(f"\n{industry}:")
                print(f"  Deliverables: {len(deliverables)}")
                
                if deliverables:
                    # Check that deliverables are industry-specific
                    first_code = deliverables[0].get("code", "")
                    print(f"  First deliverable code: {first_code}")
                    
                    # Verify industry prefix in codes
                    if industry == "luxury_fashion" and not first_code.startswith("LF"):
                        print(f"  ⚠ Warning: Expected LF prefix for luxury_fashion")
                        test_results["errors"].append(f"Wrong prefix for {industry}")
                    elif industry == "beauty" and not first_code.startswith("BT"):
                        print(f"  ⚠ Warning: Expected BT prefix for beauty")
                        test_results["errors"].append(f"Wrong prefix for {industry}")
                    elif industry == "real_estate" and not first_code.startswith("RE"):
                        print(f"  ⚠ Warning: Expected RE prefix for real_estate")
                        test_results["errors"].append(f"Wrong prefix for {industry}")
                    else:
                        print(f"  ✓ Correct industry prefix")
                    
                    # Check for contamination
                    if previous_deliverables:
                        overlap = set(d["code"] for d in deliverables) & set(d["code"] for d in previous_deliverables)
                        if overlap:
                            print(f"  ⚠ Warning: Found overlapping deliverables: {overlap}")
                            test_results["errors"].append(f"Data contamination between industries: {overlap}")
                        else:
                            print(f"  ✓ No data contamination detected")
                    
                    previous_deliverables = deliverables
                    
    except Exception as e:
        print(f"Error in template switching test: {str(e)}")
        test_results["errors"].append(f"Template switching error: {str(e)}")

def generate_report():
    """Generate final test report"""
    print("\n" + "="*60)
    print("FINAL TEST REPORT")
    print("="*60)
    
    # Summary
    print("\n📊 Test Summary:")
    print(f"  Total Errors: {len(test_results['errors'])}")
    
    # Template availability
    print("\n✅ Template Availability:")
    if test_results.get("templates_endpoint", {}).get("templates"):
        for template in test_results["templates_endpoint"]["templates"]:
            status = "✓" if template.get("available") else "✗"
            print(f"  {status} {template['label']}")
    
    # Deliverable counts per industry
    print("\n📦 Deliverables Count by Industry:")
    for industry, data in test_results.get("suggest_deliverables", {}).items():
        if "with_keywords" in data:
            count = data["with_keywords"].get("count", 0)
            status = "✓" if 40 <= count <= 70 else "⚠"
            print(f"  {status} {industry}: {count} deliverables")
    
    # Timeline tests
    print("\n⏱ Timeline Calculation:")
    for industry, data in test_results.get("calculate_timeline", {}).items():
        if data.get("status") == "success":
            print(f"  ✓ {industry}: {data.get('duration_weeks')} weeks, {data.get('phase_count')} phases")
        else:
            print(f"  ✗ {industry}: {data.get('status', 'failed')}")
    
    # Pricing tests
    print("\n💰 Pricing Calculation:")
    for industry, data in test_results.get("calculate_pricing", {}).items():
        if isinstance(data, dict) and "rate_150" in data:
            has_adj = data["rate_150"].get("has_adjustments", False)
            status = "✓" if has_adj else "⚠"
            print(f"  {status} {industry}: Adjustments applied = {has_adj}")
    
    # Edge cases
    print("\n🔧 Edge Cases:")
    for case, result in test_results.get("edge_cases", {}).items():
        status = "✓" if result == "passed" else "✗"
        print(f"  {status} {case}: {result}")
    
    # Errors
    if test_results["errors"]:
        print("\n❌ Errors Found:")
        for error in test_results["errors"]:
            print(f"  - {error}")
    else:
        print("\n✅ No errors found!")
    
    # Save detailed results
    with open("test_results.json", "w") as f:
        json.dump(test_results, f, indent=2, default=str)
    print("\n📝 Detailed results saved to test_results.json")

def main():
    """Main test execution"""
    print("🚀 Starting Comprehensive Industry Template Tests")
    print(f"Testing against: {BASE_URL}")
    
    # Test 1: Templates endpoint
    test_templates_endpoint()
    
    # Test 2-5: For each industry
    print("\n" + "="*60)
    print("Testing Individual Industries")
    print("="*60)
    
    for industry in INDUSTRY_KEYWORDS.keys():
        print(f"\n{'='*40}")
        print(f"Testing {industry.upper()}")
        print(f"{'='*40}")
        
        # Test suggest deliverables
        test_suggest_deliverables(industry, INDUSTRY_KEYWORDS[industry])
        
        # Test timeline calculation
        test_calculate_timeline(industry)
        
        # Test pricing calculation
        test_calculate_pricing(industry)
    
    # Test edge cases
    test_edge_cases()
    
    # Test template switching
    test_template_switching()
    
    # Generate final report
    generate_report()

if __name__ == "__main__":
    main()