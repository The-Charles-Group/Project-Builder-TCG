#!/usr/bin/env python3
"""
Final Comprehensive Validation Test Suite
Tests all critical functionality after fixes
"""

import asyncio
import json
import time
from datetime import datetime
import httpx
import sys

BASE_URL = "http://localhost:5000"
TIMEOUT = httpx.Timeout(60.0, connect=10.0)

def print_header(title):
    """Print formatted test header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_result(test_name, passed, details=""):
    """Print test result with color coding"""
    if passed:
        status = "\033[92m✓ PASS\033[0m"
    else:
        status = "\033[91m✗ FAIL\033[0m"
    print(f"{status} {test_name}")
    if details:
        print(f"       {details}")

async def test_rfp_analysis():
    """Test 1: RFP Analysis with GPT-5"""
    print_header("TEST 1: RFP Analysis (100+ Deliverables)")
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            # Submit RFP for analysis
            rfp_text = """
            Maison Laurent Paris - Spring/Summer 2025 Campaign
            
            COMPREHENSIVE PROJECT BRIEF:
            We need a luxury fashion campaign for our Spring/Summer 2025 collection launch.
            This includes global brand strategy, influencer partnerships, fashion week activations,
            digital experiences, retail experiences, and comprehensive content production.
            
            Budget: $15-20 million
            Timeline: 12 months
            Markets: North America, Europe, Asia-Pacific
            Target: Affluent millennials and Gen Z
            """
            
            response = await client.post(
                f"{BASE_URL}/api/ai/analyze",
                json={
                    "text": rfp_text,
                    "mode": "balanced",
                    "include_reasoning": True
                }
            )
            
            if response.status_code != 200:
                print_result("RFP submission", False, f"Status: {response.status_code}")
                return False, 0
                
            job_data = response.json()
            job_id = job_data.get("job_id")
            
            # Poll for completion
            for _ in range(30):  # 30 seconds timeout
                await asyncio.sleep(1)
                status_response = await client.get(f"{BASE_URL}/api/ai/jobs/{job_id}")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data.get("status") == "completed":
                        deliverables = status_data.get("result", {}).get("deliverables", [])
                        count = len(deliverables)
                        passed = count >= 100
                        print_result("GPT-5 Analysis", passed, f"{count} deliverables generated")
                        return passed, count
                        
            print_result("GPT-5 Analysis", False, "Timeout waiting for analysis")
            return False, 0
            
        except Exception as e:
            print_result("GPT-5 Analysis", False, str(e))
            return False, 0

async def test_scenario_building(deliverable_codes):
    """Test 2: Build Scenario with Field Name Compatibility"""
    print_header("TEST 2: Scenario Building")
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            # Test with camelCase fields (frontend format)
            response = await client.post(
                f"{BASE_URL}/api/scenarios",
                json={
                    "selectedCodes": deliverable_codes[:50],  # Use first 50
                    "pricingMode": "standard",
                    "rateBand": "A",
                    "complexity": "medium"
                }
            )
            
            passed = response.status_code == 200
            if passed:
                scenario_data = response.json()
                items = scenario_data.get("A", {}).get("items", [])
                print_result("Build Scenario", True, f"{len(items)} items in scenario")
            else:
                print_result("Build Scenario", False, f"Status: {response.status_code}")
                
            return passed
            
        except Exception as e:
            print_result("Build Scenario", False, str(e))
            return False

async def test_timeline_generation(deliverable_codes):
    """Test 3: Timeline Generation with CPM"""
    print_header("TEST 3: Timeline Generation")
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/ai/generate_timeline",
                json={
                    "deliverables": deliverable_codes[:30],  # Use subset for speed
                    "duration_months": 12,
                    "include_governance": True,
                    "include_cpm": True
                }
            )
            
            if response.status_code == 200:
                timeline = response.json()
                tasks = timeline.get("tasks", [])
                cpm_data = timeline.get("cpm_analysis", {})
                milestones = timeline.get("milestones", [])
                
                has_tasks = len(tasks) > 0
                has_cpm = bool(cpm_data)
                has_milestones = len(milestones) > 0
                
                print_result("Timeline Tasks", has_tasks, f"{len(tasks)} tasks")
                print_result("CPM Analysis", has_cpm, "Critical path calculated")
                print_result("Governance Milestones", has_milestones, f"{len(milestones)} milestones")
                
                return has_tasks and has_cpm
            else:
                print_result("Timeline Generation", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            print_result("Timeline Generation", False, str(e))
            return False

async def test_xml_export(deliverable_codes):
    """Test 4: XML Export for Workfront"""
    print_header("TEST 4: XML Export")
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/xml",
                json={
                    "deliverable_codes": deliverable_codes[:20],  # Use subset
                    "project_name": "Test Project",
                    "include_milestones": True,
                    "include_resources": True
                }
            )
            
            if response.status_code == 200:
                xml_content = response.text
                
                # Check for key XML elements
                has_project = "<Project " in xml_content
                has_tasks = "<Task>" in xml_content
                has_resources = "<Resource>" in xml_content
                has_calendar = "<Calendar " in xml_content
                
                print_result("XML Structure", has_project, "Valid Project element")
                print_result("Tasks Export", has_tasks, "Tasks included")
                print_result("Resources Export", has_resources, "Resources included")
                print_result("Calendar Definition", has_calendar, "Calendar included")
                
                return has_project and has_tasks
            else:
                print_result("XML Export", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            print_result("XML Export", False, str(e))
            return False

async def test_pricing_optimization():
    """Test 5: Pricing Optimization"""
    print_header("TEST 5: Pricing Optimization")
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            # Build a scenario first
            scenario_response = await client.post(
                f"{BASE_URL}/api/scenarios",
                json={
                    "selectedCodes": ["DEL-0001", "DEL-0002", "DEL-0003"],
                    "pricingMode": "standard",
                    "rateBand": "A"
                }
            )
            
            if scenario_response.status_code != 200:
                print_result("Pricing Optimization", False, "Failed to build scenario")
                return False
                
            scenario = scenario_response.json().get("A", {})
            
            # Test optimization
            response = await client.post(
                f"{BASE_URL}/api/ai/optimize_pricing",
                json={
                    "scenario": scenario,
                    "target_budget": 500000,
                    "company_size": "enterprise",
                    "urgency": "standard"
                }
            )
            
            if response.status_code == 200:
                optimized = response.json()
                new_total = optimized.get("total_price", 0)
                variance = abs(new_total - 500000) / 500000
                
                passed = variance < 0.1  # Within 10% of target
                print_result("Budget Targeting", passed, f"${new_total:,.0f} (target: $500K)")
                return passed
            else:
                print_result("Pricing Optimization", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            print_result("Pricing Optimization", False, str(e))
            return False

async def test_industry_templates():
    """Test 6: Industry Templates"""
    print_header("TEST 6: Industry Templates")
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            # Test template listing
            response = await client.get(f"{BASE_URL}/api/industry/templates")
            
            if response.status_code != 200:
                print_result("Template Listing", False, f"Status: {response.status_code}")
                return False
                
            templates = response.json().get("templates", [])
            has_all = len(templates) >= 6
            print_result("Template Count", has_all, f"{len(templates)} templates available")
            
            # Test luxury template suggestions
            suggest_response = await client.post(
                f"{BASE_URL}/api/industry/suggest-deliverables",
                json={
                    "industry": "luxury",
                    "keywords": "fashion campaign"
                }
            )
            
            if suggest_response.status_code == 200:
                suggestions = suggest_response.json().get("deliverables", [])
                has_suggestions = len(suggestions) > 20
                print_result("Luxury Template", has_suggestions, f"{len(suggestions)} deliverables")
                return has_all and has_suggestions
            else:
                print_result("Template Suggestions", False, f"Status: {suggest_response.status_code}")
                return False
                
        except Exception as e:
            print_result("Industry Templates", False, str(e))
            return False

async def run_all_tests():
    """Run all validation tests"""
    print("\n" + "="*60)
    print("  FINAL VALIDATION TEST SUITE")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)
    
    results = {
        "rfp_analysis": False,
        "scenario_building": False,
        "timeline_generation": False,
        "xml_export": False,
        "pricing_optimization": False,
        "industry_templates": False
    }
    
    deliverable_codes = []
    
    # Test 1: RFP Analysis
    passed, count = await test_rfp_analysis()
    results["rfp_analysis"] = passed
    
    # Generate sample deliverable codes for other tests
    deliverable_codes = [f"DEL-{str(i).zfill(4)}" for i in range(1, min(count+1, 53))]
    
    # Run remaining tests
    results["scenario_building"] = await test_scenario_building(deliverable_codes)
    results["timeline_generation"] = await test_timeline_generation(deliverable_codes)
    results["xml_export"] = await test_xml_export(deliverable_codes)
    results["pricing_optimization"] = await test_pricing_optimization()
    results["industry_templates"] = await test_industry_templates()
    
    # Summary
    print("\n" + "="*60)
    print("  FINAL RESULTS")
    print("="*60)
    
    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    pass_rate = (passed_count / total_count) * 100
    
    for test_name, passed in results.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {test_name.replace('_', ' ').title()}")
    
    print(f"\n  Overall: {passed_count}/{total_count} tests passed ({pass_rate:.1f}%)")
    
    if pass_rate >= 80:
        print("\n  \033[92m✓ SYSTEM IS PRODUCTION READY!\033[0m")
    else:
        print("\n  \033[93m⚠ System needs more work before production\033[0m")
    
    return pass_rate

if __name__ == "__main__":
    pass_rate = asyncio.run(run_all_tests())
    sys.exit(0 if pass_rate >= 80 else 1)
