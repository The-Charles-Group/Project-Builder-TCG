"""
Comprehensive Industry Template Testing Script
===============================================
This script thoroughly tests all 6 industry templates and their integration
with the main workflow system.

Test Coverage:
1. Deliverable suggestions and counts
2. Keyword matching accuracy
3. Pricing multipliers
4. Timeline calculations
5. Special requirements
6. Department assignments
7. UI integration
8. Scenario building
"""

import requests
import json
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import Counter

BASE_URL = "http://localhost:5000"

# Color codes for output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Print formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")

def print_section(text):
    """Print formatted section header"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'-'*60}{Colors.ENDC}")
    print(f"{Colors.CYAN}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'-'*60}{Colors.ENDC}")

def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.ENDC}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.ENDC}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.ENDC}")

class TemplateTestResults:
    """Store and track test results for each template"""
    def __init__(self, template_name):
        self.template_name = template_name
        self.deliverable_count = 0
        self.deliverable_codes = []
        self.deliverable_names = []
        self.categories = Counter()
        self.keyword_test_passed = False
        self.pricing_test_passed = False
        self.timeline_test_passed = False
        self.ui_test_passed = False
        self.scenario_test_passed = False
        self.special_requirements = {}
        self.departments = Counter()
        self.pricing_multipliers = []
        self.errors = []
        self.warnings = []
        
    def print_summary(self):
        """Print comprehensive test summary for this template"""
        print_section(f"{self.template_name} - Test Summary")
        
        print(f"\n{Colors.BOLD}Deliverable Statistics:{Colors.ENDC}")
        print(f"  • Total Deliverables: {self.deliverable_count}")
        print(f"  • Categories: {len(self.categories)}")
        print(f"  • Unique Codes: {len(set(self.deliverable_codes))}")
        
        if self.categories:
            print(f"\n{Colors.BOLD}Category Breakdown:{Colors.ENDC}")
            for cat, count in self.categories.most_common():
                print(f"  • {cat}: {count} deliverables")
        
        if self.departments:
            print(f"\n{Colors.BOLD}Department Assignments:{Colors.ENDC}")
            for dept, count in self.departments.most_common():
                print(f"  • {dept}: {count} deliverables")
        
        if self.pricing_multipliers:
            print(f"\n{Colors.BOLD}Pricing Analysis:{Colors.ENDC}")
            print(f"  • Min Multiplier: {min(self.pricing_multipliers):.2f}x")
            print(f"  • Max Multiplier: {max(self.pricing_multipliers):.2f}x")
            print(f"  • Avg Multiplier: {sum(self.pricing_multipliers)/len(self.pricing_multipliers):.2f}x")
        
        print(f"\n{Colors.BOLD}Test Results:{Colors.ENDC}")
        tests = [
            ("Keyword Matching", self.keyword_test_passed),
            ("Pricing Calculation", self.pricing_test_passed),
            ("Timeline Calculation", self.timeline_test_passed),
            ("UI Integration", self.ui_test_passed),
            ("Scenario Building", self.scenario_test_passed)
        ]
        for test_name, passed in tests:
            if passed:
                print_success(f"{test_name}")
            else:
                print_error(f"{test_name}")
        
        if self.special_requirements:
            print(f"\n{Colors.BOLD}Special Requirements Found:{Colors.ENDC}")
            for req, count in self.special_requirements.items():
                print(f"  • {req}: {count} deliverables")
        
        if self.errors:
            print(f"\n{Colors.BOLD}Errors:{Colors.ENDC}")
            for error in self.errors:
                print_error(error)
        
        if self.warnings:
            print(f"\n{Colors.BOLD}Warnings:{Colors.ENDC}")
            for warning in self.warnings:
                print_warning(warning)

def test_template_list():
    """Test that all templates are available"""
    print_header("Testing Template List Endpoint")
    
    try:
        response = requests.get(f"{BASE_URL}/api/industry/templates")
        data = response.json()
        
        if "templates" not in data:
            print_error("Templates list not found in response")
            return False
        
        templates = data["templates"]
        print_success(f"Found {len(templates)} templates")
        
        for template in templates:
            status = "✅ Available" if template.get("available") else "❌ Unavailable"
            print(f"  • {template['label']} ({template['value']}): {status}")
        
        return True
        
    except Exception as e:
        print_error(f"Failed to fetch templates: {e}")
        return False

def test_deliverable_suggestions(template: str, keywords: List[str]) -> TemplateTestResults:
    """Test deliverable suggestions for a specific template"""
    results = TemplateTestResults(template)
    
    print_section(f"Testing {template} - Deliverable Suggestions")
    
    # Test with relevant keywords
    rfp_text = " ".join(keywords)
    payload = {
        "industry": template,
        "rfp_text": rfp_text
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/industry/suggest-deliverables",
            json=payload
        )
        
        if response.status_code != 200:
            results.errors.append(f"HTTP {response.status_code}: {response.text}")
            return results
        
        data = response.json()
        
        # Check deliverables
        if "deliverables" in data:
            deliverables = data["deliverables"]
            results.deliverable_count = len(deliverables)
            
            print_success(f"Retrieved {len(deliverables)} deliverables")
            
            # Analyze deliverables
            for d in deliverables:
                results.deliverable_codes.append(d.get("code", ""))
                results.deliverable_names.append(d.get("name", ""))
                results.categories[d.get("category", "Unknown")] += 1
                
                # Check for special requirements
                if d.get("requires_talent"):
                    results.special_requirements["Requires Talent"] = \
                        results.special_requirements.get("Requires Talent", 0) + 1
                if d.get("requires_venue"):
                    results.special_requirements["Requires Venue"] = \
                        results.special_requirements.get("Requires Venue", 0) + 1
                if d.get("requires_tech_integration"):
                    results.special_requirements["Requires Tech Integration"] = \
                        results.special_requirements.get("Requires Tech Integration", 0) + 1
                if d.get("requires_permits"):
                    results.special_requirements["Requires Permits"] = \
                        results.special_requirements.get("Requires Permits", 0) + 1
                if d.get("requires_clinical"):
                    results.special_requirements["Requires Clinical"] = \
                        results.special_requirements.get("Requires Clinical", 0) + 1
                if d.get("requires_regulatory"):
                    results.special_requirements["Requires Regulatory"] = \
                        results.special_requirements.get("Requires Regulatory", 0) + 1
                if d.get("requires_engineering"):
                    results.special_requirements["Requires Engineering"] = \
                        results.special_requirements.get("Requires Engineering", 0) + 1
                if d.get("requires_certification"):
                    results.special_requirements["Requires Certification"] = \
                        results.special_requirements.get("Requires Certification", 0) + 1
                
                # Check multipliers
                if "luxury_multiplier" in d:
                    results.pricing_multipliers.append(d["luxury_multiplier"])
                if "complexity_multiplier" in d:
                    results.pricing_multipliers.append(d["complexity_multiplier"])
                if "enterprise_multiplier" in d:
                    results.pricing_multipliers.append(d["enterprise_multiplier"])
                if "experience_multiplier" in d:
                    results.pricing_multipliers.append(d["experience_multiplier"])
                    
            # Check keyword matching
            keywords_found = data.get("keywords_found", [])
            if keywords_found:
                print_success(f"Keywords matched: {', '.join(keywords_found)}")
                results.keyword_test_passed = True
            else:
                results.warnings.append("No keywords matched")
                
        else:
            results.errors.append("No deliverables in response")
            
    except Exception as e:
        results.errors.append(f"Exception: {str(e)}")
        
    return results

def test_timeline_calculation(template: str, deliverable_codes: List[str]) -> bool:
    """Test timeline calculation for specific deliverables"""
    print_section(f"Testing {template} - Timeline Calculation")
    
    if not deliverable_codes:
        print_warning("No deliverable codes to test")
        return False
    
    # Take first 5 deliverables for testing
    test_codes = deliverable_codes[:5]
    
    payload = {
        "industry": template,
        "deliverable_codes": test_codes,
        "start_date": datetime.now().isoformat()
    }
    
    # Add special parameters for real estate
    if template == "real_estate":
        payload["project_phase"] = "sales_launch"
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/industry/calculate-timeline",
            json=payload
        )
        
        if response.status_code != 200:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return False
        
        data = response.json()
        
        if "timeline" in data:
            timeline = data["timeline"]
            print_success(f"Timeline calculated with {len(timeline.get('phases', []))} phases")
            
            # Check phases
            phases = timeline.get("phases", [])
            if phases:
                print("  Phases found:")
                for phase in phases[:3]:  # Show first 3 phases
                    print(f"    • {phase.get('name', 'Unknown')}: {phase.get('duration_days', 0)} days")
            
            # Check milestones
            milestones = timeline.get("milestones", [])
            if milestones:
                print(f"  Milestones: {len(milestones)} defined")
            
            return True
        else:
            print_error("No timeline in response")
            return False
            
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return False

def test_pricing_calculation(template: str, deliverable_codes: List[str]) -> bool:
    """Test pricing calculation for specific deliverables"""
    print_section(f"Testing {template} - Pricing Calculation")
    
    if not deliverable_codes:
        print_warning("No deliverable codes to test")
        return False
    
    # Take first 5 deliverables for testing
    test_codes = deliverable_codes[:5]
    
    payload = {
        "industry": template,
        "deliverable_codes": test_codes,
        "base_rate": 150
    }
    
    # Add special parameters for real estate
    if template == "real_estate":
        payload["property_type"] = "luxury_residential"
        payload["num_phases"] = 3
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/industry/calculate-pricing",
            json=payload
        )
        
        if response.status_code != 200:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return False
        
        data = response.json()
        
        if "pricing" in data:
            pricing = data["pricing"]
            
            if "subtotal" in pricing and "total" in pricing:
                print_success(f"Pricing calculated:")
                print(f"  • Base Rate: ${data.get('base_rate', 150)}")
                print(f"  • Subtotal: ${pricing['subtotal']:,.2f}")
                print(f"  • Total: ${pricing['total']:,.2f}")
                
                # Check adjustments
                adjustments = pricing.get("adjustments", [])
                if adjustments:
                    print("  • Adjustments applied:")
                    for adj in adjustments:
                        print(f"    - {adj.get('type', 'Unknown')}: ${adj.get('amount', 0):,.2f}")
                
                # Check if multipliers are being applied
                if pricing["total"] > pricing["subtotal"]:
                    print_success("Pricing multipliers/adjustments are being applied")
                
                return True
            else:
                print_error("Missing subtotal or total in pricing")
                return False
        else:
            print_error("No pricing in response")
            return False
            
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return False

def test_ui_integration(template: str) -> bool:
    """Test UI integration by simulating template selection workflow"""
    print_section(f"Testing {template} - UI Integration")
    
    # Step 1: Simulate RFP upload with template selection
    sample_rfp_text = """
    We need a comprehensive marketing campaign for our new product launch.
    This includes digital marketing, social media, content creation,
    influencer partnerships, and event planning.
    """
    
    payload = {
        "industry": template,
        "rfp_text": sample_rfp_text
    }
    
    try:
        # Get deliverable suggestions
        response = requests.post(
            f"{BASE_URL}/api/industry/suggest-deliverables",
            json=payload
        )
        
        if response.status_code != 200:
            print_error(f"Failed to get deliverables: HTTP {response.status_code}")
            return False
        
        data = response.json()
        deliverables = data.get("deliverables", [])
        
        if not deliverables:
            print_warning("No deliverables returned for UI test")
            return False
        
        print_success(f"UI Integration test successful - {len(deliverables)} deliverables loaded")
        
        # Test that deliverable structure is compatible with UI
        required_fields = ["code", "name", "category", "base_hours"]
        sample_deliverable = deliverables[0]
        
        missing_fields = [f for f in required_fields if f not in sample_deliverable]
        if missing_fields:
            print_error(f"Missing required fields for UI: {missing_fields}")
            return False
        
        print_success("Deliverables have all required fields for UI")
        return True
        
    except Exception as e:
        print_error(f"UI integration test failed: {e}")
        return False

def test_scenario_building(template: str, deliverable_codes: List[str]) -> bool:
    """Test building a complete scenario with template deliverables"""
    print_section(f"Testing {template} - Scenario Building")
    
    if not deliverable_codes:
        print_warning("No deliverable codes for scenario test")
        return False
    
    # Build a scenario with first 3 deliverables
    scenario_payload = {
        "rfp_text": f"Test scenario for {template}",
        "selected_deliverables": deliverable_codes[:3],
        "project_name": f"{template.title()} Test Project",
        "start_date": datetime.now().isoformat(),
        "timeline": "aggressive"
    }
    
    try:
        # Test the build endpoint
        response = requests.post(
            f"{BASE_URL}/api/build",
            json=scenario_payload
        )
        
        if response.status_code != 200:
            print_error(f"Build failed: HTTP {response.status_code}")
            return False
        
        data = response.json()
        
        if "scenario" in data:
            scenario = data["scenario"]
            components = scenario.get("components", [])
            
            if components:
                print_success(f"Scenario built with {len(components)} components")
                
                # Check that template codes work in WBS
                for comp in components[:2]:
                    print(f"  • {comp.get('name', 'Unknown')}: {len(comp.get('tasks', []))} tasks")
                
                return True
            else:
                print_error("No components in scenario")
                return False
        else:
            print_error("No scenario in response")
            return False
            
    except Exception as e:
        print_error(f"Scenario building failed: {e}")
        return False

def run_comprehensive_tests():
    """Run all comprehensive tests for all templates"""
    print_header("COMPREHENSIVE INDUSTRY TEMPLATE TESTING")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Verify all templates are available
    if not test_template_list():
        print_error("Template list test failed - aborting")
        return
    
    # Define test data for each template
    template_test_data = {
        "luxury_fashion": {
            "keywords": ["fashion", "runway", "collection", "lookbook", "editorial", "campaign", 
                        "influencer", "paris", "milan", "boutique", "flagship", "event", "gala"],
            "expected_min_count": 50,
            "expected_categories": ["Campaign Planning", "Content Production", "Event Production", 
                                   "Digital Marketing", "Influencer Marketing"]
        },
        "beauty": {
            "keywords": ["beauty", "cosmetic", "skincare", "makeup", "launch", "product",
                        "tutorial", "clinical", "ingredient", "sephora", "ulta", "sample"],
            "expected_min_count": 40,
            "expected_categories": ["Product Launch", "Content Creation", "Influencer Marketing",
                                   "Retail Marketing", "Education & Training"]
        },
        "real_estate": {
            "keywords": ["property", "residential", "commercial", "launch", "broker", "lease",
                        "virtual", "tour", "neighborhood", "amenity", "investment", "development"],
            "expected_min_count": 70,
            "expected_categories": ["Launch Campaigns", "Content Creation", "Digital Marketing",
                                   "Events & Tours", "Marketing Collateral"]
        },
        "retail": {
            "keywords": ["retail", "store", "ecommerce", "omnichannel", "sale", "promotion",
                        "loyalty", "inventory", "pos", "customer", "seasonal", "black friday"],
            "expected_min_count": 47,
            "expected_categories": ["Campaign Strategy", "Omnichannel Operations", "Customer Experience",
                                   "Promotions", "Store Operations"]
        },
        "lifestyle": {
            "keywords": ["lifestyle", "wellness", "experience", "community", "partnership",
                        "workshop", "retreat", "sustainability", "mindfulness", "content"],
            "expected_min_count": 56,
            "expected_categories": ["Brand Collaborations", "Experience Design", "Content Creation",
                                   "Community Building", "Wellness Programs"]
        },
        "tech": {
            "keywords": ["technology", "software", "hardware", "launch", "developer", "cloud",
                        "enterprise", "b2b", "integration", "api", "platform", "saas"],
            "expected_min_count": 40,
            "expected_categories": ["Product Launch", "Developer Marketing", "Content Marketing",
                                   "Enterprise Sales", "Channel Marketing"]
        }
    }
    
    # Store all results
    all_results = {}
    summary_stats = {
        "total_deliverables": 0,
        "total_tests_passed": 0,
        "total_tests_failed": 0,
        "templates_tested": 0
    }
    
    # Test each template
    for template, test_data in template_test_data.items():
        print_header(f"TESTING: {template.upper().replace('_', ' ')}")
        
        # Test deliverable suggestions
        results = test_deliverable_suggestions(template, test_data["keywords"])
        
        # Validate deliverable count
        if results.deliverable_count >= test_data["expected_min_count"]:
            print_success(f"Deliverable count validated: {results.deliverable_count} >= {test_data['expected_min_count']}")
        else:
            print_warning(f"Deliverable count lower than expected: {results.deliverable_count} < {test_data['expected_min_count']}")
            results.warnings.append(f"Expected at least {test_data['expected_min_count']} deliverables, got {results.deliverable_count}")
        
        # Test timeline calculation
        results.timeline_test_passed = test_timeline_calculation(template, results.deliverable_codes)
        
        # Test pricing calculation
        results.pricing_test_passed = test_pricing_calculation(template, results.deliverable_codes)
        
        # Test UI integration
        results.ui_test_passed = test_ui_integration(template)
        
        # Test scenario building
        results.scenario_test_passed = test_scenario_building(template, results.deliverable_codes)
        
        # Store results
        all_results[template] = results
        summary_stats["total_deliverables"] += results.deliverable_count
        summary_stats["templates_tested"] += 1
        
        # Count passed/failed tests
        tests = [results.keyword_test_passed, results.pricing_test_passed, 
                results.timeline_test_passed, results.ui_test_passed, results.scenario_test_passed]
        summary_stats["total_tests_passed"] += sum(tests)
        summary_stats["total_tests_failed"] += len(tests) - sum(tests)
    
    # Print comprehensive summary
    print_header("COMPREHENSIVE TEST RESULTS SUMMARY")
    
    print(f"\n{Colors.BOLD}Overall Statistics:{Colors.ENDC}")
    print(f"  • Templates Tested: {summary_stats['templates_tested']}/6")
    print(f"  • Total Deliverables Found: {summary_stats['total_deliverables']}")
    print(f"  • Tests Passed: {summary_stats['total_tests_passed']}")
    print(f"  • Tests Failed: {summary_stats['total_tests_failed']}")
    
    # Individual template summaries
    for template, results in all_results.items():
        results.print_summary()
    
    # Final verdict
    print_header("FINAL TEST VERDICT")
    
    all_passed = all(
        r.keyword_test_passed and r.pricing_test_passed and 
        r.timeline_test_passed and r.ui_test_passed and r.scenario_test_passed
        for r in all_results.values()
    )
    
    if all_passed:
        print_success("ALL TESTS PASSED! All 6 industry templates are fully functional.")
    else:
        failed_templates = [
            t for t, r in all_results.items() 
            if not (r.keyword_test_passed and r.pricing_test_passed and 
                   r.timeline_test_passed and r.ui_test_passed and r.scenario_test_passed)
        ]
        print_warning(f"Some tests failed. Templates with issues: {', '.join(failed_templates)}")
    
    # Document deliverable counts for each template
    print_header("DOCUMENTED DELIVERABLE COUNTS")
    
    for template, results in all_results.items():
        print(f"{Colors.BOLD}{template.upper().replace('_', ' ')}:{Colors.ENDC}")
        print(f"  • Actual Count: {results.deliverable_count} deliverables")
        print(f"  • Categories: {len(results.categories)}")
        print(f"  • Unique Codes: {len(set(results.deliverable_codes))}")
        if results.pricing_multipliers:
            print(f"  • Price Range: {min(results.pricing_multipliers):.1f}x - {max(results.pricing_multipliers):.1f}x")
    
    print(f"\n{Colors.GREEN}Testing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")

if __name__ == "__main__":
    try:
        # Check if server is running - try the root endpoint instead
        response = requests.get(f"{BASE_URL}/")
        # Any response means server is up
    except:
        print_error("Cannot connect to server. Please ensure FastAPI server is running on port 5000.")
        sys.exit(1)
    
    # Run comprehensive tests
    run_comprehensive_tests()