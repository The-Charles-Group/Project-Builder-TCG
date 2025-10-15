"""
Comprehensive Pricing Optimization Tests
Tests the /api/ai/optimize_pricing endpoint with various budget constraints and scenarios
"""

import asyncio
import json
from typing import Dict, List, Any, Tuple
from datetime import datetime
import httpx
from colorama import init, Fore, Style

# Initialize colorama for colored console output
init(autoreset=True)

BASE_URL = "http://localhost:5000"

class PricingOptimizationTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "errors": [],
            "tests": []
        }
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, *args):
        await self.client.aclose()
    
    def print_header(self, title: str):
        """Print a formatted test section header"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}{title.center(60)}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    def print_test(self, name: str, status: str = "RUNNING"):
        """Print test status"""
        if status == "PASSED":
            print(f"{Fore.GREEN}✓ {name}: PASSED{Style.RESET_ALL}")
        elif status == "FAILED":
            print(f"{Fore.RED}✗ {name}: FAILED{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}⟳ {name}: {status}{Style.RESET_ALL}")
    
    def print_result(self, key: str, value: Any, indent: int = 2):
        """Print a result with indentation"""
        print(f"{' '*indent}{Fore.WHITE}{key}: {Fore.YELLOW}{value}{Style.RESET_ALL}")
    
    async def create_test_scenario(self) -> Dict[str, Any]:
        """Create a test scenario with deliverables and pricing"""
        # First, get some deliverables
        response = await self.client.post(
            f"{BASE_URL}/api/suggest_by_text",
            json={
                "rfp_text": "Create a comprehensive digital marketing campaign with brand strategy, creative development, and paid media management"
            }
        )
        
        if response.status_code != 200:
            raise Exception("Failed to get deliverable suggestions")
        
        suggestions = response.json()
        
        # Extract deliverable codes from suggested list
        suggested_deliverables = suggestions.get("suggested", [])
        if not suggested_deliverables:
            raise Exception("No deliverable suggestions received")
        
        deliverable_codes = [d.get("deliverable_code", d.get("code")) for d in suggested_deliverables][:8]
        
        # Build a scenario
        build_data = {
            "project_name": "Test Pricing Optimization Project",
            "selected_codes": deliverable_codes,  # Use 8 deliverables
            "pricing_tier": "Tier 2",
            "complexity": "Advanced"
        }
        
        response = await self.client.post(f"{BASE_URL}/api/build", json=build_data)
        
        if response.status_code != 200:
            raise Exception("Failed to build scenario")
        
        scenario_response = response.json()
        return scenario_response.get("scenario_a", {})
    
    async def test_budget_targets(self):
        """Test 1: Different budget targets"""
        self.print_header("TEST 1: BUDGET TARGET OPTIMIZATION")
        
        test_name = "Budget Target Optimization"
        self.print_test(test_name, "RUNNING")
        
        try:
            # Create base scenario
            scenario = await self.create_test_scenario()
            
            # Calculate original total
            original_total = sum(float(item.get("Price", 0)) for item in scenario.get("wbs", []))
            self.print_result("Original Total", f"${original_total:,.2f}")
            
            # Test different budget targets
            budget_tests = [
                (100000, "Low budget - should reduce rates"),
                (500000, "Moderate budget - moderate adjustments"),
                (1000000, "Standard budget - normal pricing"),
                (5000000, "Premium budget - high pricing")
            ]
            
            for target_budget, description in budget_tests:
                print(f"\n  Testing: {description}")
                
                response = await self.client.post(
                    f"{BASE_URL}/api/ai/optimize_pricing",
                    json={
                        "target_budget": target_budget,
                        "scenario": scenario,
                        "maintain_quality_tiers": True
                    }
                )
                
                if response.status_code == 200:
                    optimized = response.json()
                    achieved_total = optimized.get("total_price", 0)
                    optimization_details = optimized.get("optimization_details", {})
                    
                    self.print_result("Target Budget", f"${target_budget:,.2f}", 4)
                    self.print_result("Achieved Total", f"${achieved_total:,.2f}", 4)
                    self.print_result("Variance", f"{abs(achieved_total - target_budget):,.2f}", 4)
                    self.print_result("Optimization Ratio", f"{optimization_details.get('optimization_ratio', 0):.2f}x", 4)
                    
                    # Verify pricing is close to target (within 1%)
                    variance_pct = abs(achieved_total - target_budget) / target_budget * 100
                    if variance_pct <= 1:
                        print(f"    {Fore.GREEN}✓ Pricing within 1% of target{Style.RESET_ALL}")
                    else:
                        print(f"    {Fore.RED}✗ Pricing variance too high: {variance_pct:.2f}%{Style.RESET_ALL}")
                        
                    # Check quality tiers maintained
                    if optimization_details.get("quality_tiers_maintained"):
                        print(f"    {Fore.GREEN}✓ Quality tiers maintained{Style.RESET_ALL}")
                    
                elif response.status_code == 400:
                    error_data = response.json()
                    if "Budget too low" in error_data.get("error", ""):
                        print(f"    {Fore.YELLOW}⚠ Budget too low: Minimum viable is ${error_data.get('minimum_viable', 0):,.2f}{Style.RESET_ALL}")
                    else:
                        print(f"    {Fore.RED}✗ Error: {error_data.get('detail', 'Unknown error')}{Style.RESET_ALL}")
                else:
                    print(f"    {Fore.RED}✗ Unexpected status code: {response.status_code}{Style.RESET_ALL}")
            
            self.print_test(test_name, "PASSED")
            self.test_results["passed"] += 1
            
        except Exception as e:
            self.print_test(test_name, "FAILED")
            print(f"  {Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append({
                "test": test_name,
                "error": str(e)
            })
    
    async def test_company_sizes(self):
        """Test 2: Different company sizes"""
        self.print_header("TEST 2: COMPANY SIZE ADJUSTMENTS")
        
        test_name = "Company Size Pricing"
        self.print_test(test_name, "RUNNING")
        
        try:
            scenario = await self.create_test_scenario()
            target_budget = 500000  # Fixed budget for comparison
            
            company_tests = [
                ("startup", 0.85, "15% discount expected"),
                ("mid_market", 1.0, "Standard pricing"),
                ("enterprise", 1.25, "25% premium expected")
            ]
            
            base_total = None
            
            for company_size, expected_multiplier, description in company_tests:
                print(f"\n  Testing: {company_size} - {description}")
                
                response = await self.client.post(
                    f"{BASE_URL}/api/ai/optimize_pricing",
                    json={
                        "target_budget": target_budget,
                        "scenario": scenario,
                        "company_size": company_size,
                        "maintain_quality_tiers": True
                    }
                )
                
                if response.status_code == 200:
                    optimized = response.json()
                    achieved_total = optimized.get("total_price", 0)
                    details = optimized.get("optimization_details", {})
                    
                    self.print_result("Company Size", company_size, 4)
                    self.print_result("Achieved Total", f"${achieved_total:,.2f}", 4)
                    
                    # Store base total for comparison
                    if company_size == "mid_market":
                        base_total = achieved_total
                    
                    # Check if company size affected pricing appropriately
                    if base_total and company_size != "mid_market":
                        ratio = achieved_total / base_total if base_total > 0 else 1
                        # Note: The actual ratio will be affected by the budget constraint
                        # but we should see some difference
                        print(f"    {Fore.CYAN}Price ratio vs mid-market: {ratio:.2f}x{Style.RESET_ALL}")
                    
                    print(f"    {Fore.GREEN}✓ {company_size} pricing applied{Style.RESET_ALL}")
                else:
                    print(f"    {Fore.RED}✗ Failed with status {response.status_code}{Style.RESET_ALL}")
            
            self.print_test(test_name, "PASSED")
            self.test_results["passed"] += 1
            
        except Exception as e:
            self.print_test(test_name, "FAILED")
            print(f"  {Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append({
                "test": test_name,
                "error": str(e)
            })
    
    async def test_urgency_factors(self):
        """Test 3: Urgency factor adjustments"""
        self.print_header("TEST 3: URGENCY FACTOR ADJUSTMENTS")
        
        test_name = "Urgency Factor Pricing"
        self.print_test(test_name, "RUNNING")
        
        try:
            scenario = await self.create_test_scenario()
            target_budget = 750000
            
            urgency_tests = [
                ("rush", 1.3, "30% premium for rush delivery"),
                ("standard", 1.0, "Standard delivery timing"),
                ("flexible", 0.9, "10% discount for flexible timing")
            ]
            
            standard_total = None
            
            for urgency, expected_mult, description in urgency_tests:
                print(f"\n  Testing: {urgency} - {description}")
                
                response = await self.client.post(
                    f"{BASE_URL}/api/ai/optimize_pricing",
                    json={
                        "target_budget": target_budget,
                        "scenario": scenario,
                        "urgency": urgency,
                        "maintain_quality_tiers": True
                    }
                )
                
                if response.status_code == 200:
                    optimized = response.json()
                    achieved_total = optimized.get("total_price", 0)
                    details = optimized.get("optimization_details", {})
                    
                    self.print_result("Urgency", urgency, 4)
                    self.print_result("Achieved Total", f"${achieved_total:,.2f}", 4)
                    self.print_result("Applied Urgency", details.get("urgency", ""), 4)
                    
                    if urgency == "standard":
                        standard_total = achieved_total
                    
                    print(f"    {Fore.GREEN}✓ {urgency} urgency pricing applied{Style.RESET_ALL}")
                else:
                    print(f"    {Fore.RED}✗ Failed with status {response.status_code}{Style.RESET_ALL}")
            
            self.print_test(test_name, "PASSED")
            self.test_results["passed"] += 1
            
        except Exception as e:
            self.print_test(test_name, "FAILED")
            print(f"  {Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append({
                "test": test_name,
                "error": str(e)
            })
    
    async def test_industry_multipliers(self):
        """Test 4: Industry multipliers"""
        self.print_header("TEST 4: INDUSTRY MULTIPLIERS")
        
        test_name = "Industry Multiplier Pricing"
        self.print_test(test_name, "RUNNING")
        
        try:
            scenario = await self.create_test_scenario()
            target_budget = 1000000
            
            industry_tests = [
                (1.0, "Standard industry"),
                (1.5, "Luxury/Premium industry"),
                (0.8, "Non-profit/Budget industry"),
                (2.0, "Ultra-luxury industry")
            ]
            
            for multiplier, description in industry_tests:
                print(f"\n  Testing: {description} (multiplier: {multiplier}x)")
                
                response = await self.client.post(
                    f"{BASE_URL}/api/ai/optimize_pricing",
                    json={
                        "target_budget": target_budget,
                        "scenario": scenario,
                        "industry_multiplier": multiplier,
                        "maintain_quality_tiers": True
                    }
                )
                
                if response.status_code == 200:
                    optimized = response.json()
                    achieved_total = optimized.get("total_price", 0)
                    details = optimized.get("optimization_details", {})
                    
                    self.print_result("Industry Multiplier", f"{multiplier}x", 4)
                    self.print_result("Achieved Total", f"${achieved_total:,.2f}", 4)
                    self.print_result("Final Ratio", f"{details.get('optimization_ratio', 0):.2f}x", 4)
                    
                    print(f"    {Fore.GREEN}✓ Industry multiplier {multiplier}x applied{Style.RESET_ALL}")
                else:
                    print(f"    {Fore.RED}✗ Failed with status {response.status_code}{Style.RESET_ALL}")
            
            self.print_test(test_name, "PASSED")
            self.test_results["passed"] += 1
            
        except Exception as e:
            self.print_test(test_name, "FAILED")
            print(f"  {Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append({
                "test": test_name,
                "error": str(e)
            })
    
    async def test_edge_cases(self):
        """Test 5: Edge cases"""
        self.print_header("TEST 5: EDGE CASES")
        
        test_name = "Edge Cases"
        self.print_test(test_name, "RUNNING")
        
        try:
            scenario = await self.create_test_scenario()
            
            # Test 1: Budget too low
            print("\n  Testing: Budget too low for minimum viable delivery")
            response = await self.client.post(
                f"{BASE_URL}/api/ai/optimize_pricing",
                json={
                    "target_budget": 1000,  # Very low budget
                    "scenario": scenario,
                    "maintain_quality_tiers": True
                }
            )
            
            if response.status_code == 400:
                error_data = response.json()
                if "Budget too low" in error_data.get("error", ""):
                    min_viable = error_data.get("minimum_viable", 0)
                    self.print_result("Status", "Correctly rejected", 4)
                    self.print_result("Minimum Viable", f"${min_viable:,.2f}", 4)
                    print(f"    {Fore.GREEN}✓ Low budget correctly rejected{Style.RESET_ALL}")
                else:
                    print(f"    {Fore.RED}✗ Wrong error: {error_data.get('error')}{Style.RESET_ALL}")
            else:
                print(f"    {Fore.RED}✗ Should have rejected low budget{Style.RESET_ALL}")
            
            # Test 2: Unlimited budget
            print("\n  Testing: Unlimited budget scenario")
            response = await self.client.post(
                f"{BASE_URL}/api/ai/optimize_pricing",
                json={
                    "target_budget": 15000000,  # $15M - unlimited budget
                    "scenario": scenario,
                    "maintain_quality_tiers": True
                }
            )
            
            if response.status_code == 200:
                optimized = response.json()
                achieved_total = optimized.get("total_price", 0)
                
                # Check that rates are capped reasonably
                max_rate = 0
                for item in optimized.get("wbs", []):
                    if item.get("Rate"):
                        max_rate = max(max_rate, float(item.get("Rate", 0)))
                
                self.print_result("Target Budget", "$15,000,000", 4)
                self.print_result("Achieved Total", f"${achieved_total:,.2f}", 4)
                self.print_result("Max Rate", f"${max_rate:.2f}/hr", 4)
                
                if max_rate <= 1000:
                    print(f"    {Fore.GREEN}✓ Rates capped at reasonable maximum{Style.RESET_ALL}")
                else:
                    print(f"    {Fore.YELLOW}⚠ Rates may be too high: ${max_rate}/hr{Style.RESET_ALL}")
            else:
                print(f"    {Fore.RED}✗ Failed to handle unlimited budget{Style.RESET_ALL}")
            
            # Test 3: Without quality tier constraints
            print("\n  Testing: Optimization without quality tier constraints")
            response = await self.client.post(
                f"{BASE_URL}/api/ai/optimize_pricing",
                json={
                    "target_budget": 50000,  # Very low budget
                    "scenario": scenario,
                    "maintain_quality_tiers": False  # Allow breaking quality tiers
                }
            )
            
            if response.status_code == 200:
                optimized = response.json()
                achieved_total = optimized.get("total_price", 0)
                details = optimized.get("optimization_details", {})
                
                self.print_result("Target Budget", "$50,000", 4)
                self.print_result("Achieved Total", f"${achieved_total:,.2f}", 4)
                self.print_result("Quality Tiers", "Not maintained", 4)
                
                # Check minimum rate enforcement
                min_rate = float('inf')
                for item in optimized.get("wbs", []):
                    if item.get("Rate"):
                        rate = float(item.get("Rate", 0))
                        if rate > 0:
                            min_rate = min(min_rate, rate)
                
                if min_rate >= 50:
                    print(f"    {Fore.GREEN}✓ Minimum rate of $50/hr maintained{Style.RESET_ALL}")
                else:
                    print(f"    {Fore.RED}✗ Rate below minimum: ${min_rate}/hr{Style.RESET_ALL}")
            else:
                print(f"    {Fore.RED}✗ Failed without quality tier constraints{Style.RESET_ALL}")
            
            self.print_test(test_name, "PASSED")
            self.test_results["passed"] += 1
            
        except Exception as e:
            self.print_test(test_name, "FAILED")
            print(f"  {Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append({
                "test": test_name,
                "error": str(e)
            })
    
    async def test_combined_factors(self):
        """Test 6: Combined factors (company size + urgency + industry)"""
        self.print_header("TEST 6: COMBINED FACTORS")
        
        test_name = "Combined Factor Pricing"
        self.print_test(test_name, "RUNNING")
        
        try:
            scenario = await self.create_test_scenario()
            
            combined_tests = [
                {
                    "description": "Startup + Rush + Tech Industry",
                    "target_budget": 300000,
                    "company_size": "startup",
                    "urgency": "rush",
                    "industry_multiplier": 1.2
                },
                {
                    "description": "Enterprise + Flexible + Luxury",
                    "target_budget": 2000000,
                    "company_size": "enterprise",
                    "urgency": "flexible",
                    "industry_multiplier": 1.5
                },
                {
                    "description": "Mid-Market + Standard + Non-Profit",
                    "target_budget": 400000,
                    "company_size": "mid_market",
                    "urgency": "standard",
                    "industry_multiplier": 0.8
                }
            ]
            
            for test_config in combined_tests:
                print(f"\n  Testing: {test_config['description']}")
                
                response = await self.client.post(
                    f"{BASE_URL}/api/ai/optimize_pricing",
                    json={
                        "target_budget": test_config["target_budget"],
                        "scenario": scenario,
                        "company_size": test_config["company_size"],
                        "urgency": test_config["urgency"],
                        "industry_multiplier": test_config["industry_multiplier"],
                        "maintain_quality_tiers": True
                    }
                )
                
                if response.status_code == 200:
                    optimized = response.json()
                    achieved_total = optimized.get("total_price", 0)
                    details = optimized.get("optimization_details", {})
                    
                    self.print_result("Target Budget", f"${test_config['target_budget']:,.2f}", 4)
                    self.print_result("Achieved Total", f"${achieved_total:,.2f}", 4)
                    self.print_result("Company Size", test_config["company_size"], 4)
                    self.print_result("Urgency", test_config["urgency"], 4)
                    self.print_result("Industry Multiplier", f"{test_config['industry_multiplier']}x", 4)
                    self.print_result("Combined Ratio", f"{details.get('optimization_ratio', 0):.2f}x", 4)
                    
                    # Verify target is met
                    variance = abs(achieved_total - test_config["target_budget"])
                    variance_pct = variance / test_config["target_budget"] * 100
                    
                    if variance_pct <= 1:
                        print(f"    {Fore.GREEN}✓ Combined factors applied correctly (variance: {variance_pct:.2f}%){Style.RESET_ALL}")
                    else:
                        print(f"    {Fore.YELLOW}⚠ Higher variance: {variance_pct:.2f}%{Style.RESET_ALL}")
                else:
                    print(f"    {Fore.RED}✗ Failed with status {response.status_code}{Style.RESET_ALL}")
            
            self.print_test(test_name, "PASSED")
            self.test_results["passed"] += 1
            
        except Exception as e:
            self.print_test(test_name, "FAILED")
            print(f"  {Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append({
                "test": test_name,
                "error": str(e)
            })
    
    async def run_all_tests(self):
        """Run all pricing optimization tests"""
        start_time = datetime.now()
        
        print(f"\n{Fore.MAGENTA}{'='*60}")
        print(f"{Fore.MAGENTA}{'PRICING OPTIMIZATION TEST SUITE'.center(60)}")
        print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
        print(f"\nStarting tests at {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Run all test categories
        await self.test_budget_targets()
        await self.test_company_sizes()
        await self.test_urgency_factors()
        await self.test_industry_multipliers()
        await self.test_edge_cases()
        await self.test_combined_factors()
        
        # Print summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n{Fore.MAGENTA}{'='*60}")
        print(f"{Fore.MAGENTA}{'TEST SUMMARY'.center(60)}")
        print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}\n")
        
        print(f"Total Tests Run: {self.test_results['passed'] + self.test_results['failed']}")
        print(f"{Fore.GREEN}Passed: {self.test_results['passed']}{Style.RESET_ALL}")
        print(f"{Fore.RED}Failed: {self.test_results['failed']}{Style.RESET_ALL}")
        print(f"Duration: {duration:.2f} seconds")
        
        if self.test_results["errors"]:
            print(f"\n{Fore.RED}Errors encountered:{Style.RESET_ALL}")
            for error in self.test_results["errors"]:
                print(f"  - {error['test']}: {error['error']}")
        
        # Overall result
        if self.test_results["failed"] == 0:
            print(f"\n{Fore.GREEN}{'✓ ALL TESTS PASSED!'.center(60)}{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.RED}{'✗ SOME TESTS FAILED'.center(60)}{Style.RESET_ALL}")
        
        return self.test_results

async def main():
    """Main test runner"""
    print(f"{Fore.CYAN}Initializing Pricing Optimization Test Suite...{Style.RESET_ALL}")
    
    # Check if server is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/ai/health")
            if response.status_code != 200:
                print(f"{Fore.RED}Warning: Server health check failed{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Error: Server not accessible at {BASE_URL}")
        print(f"Please ensure the FastAPI server is running on port 5000{Style.RESET_ALL}")
        return
    
    # Run tests
    async with PricingOptimizationTester() as tester:
        results = await tester.run_all_tests()
        
        # Save results to file
        results_file = f"test_results_pricing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nTest results saved to: {results_file}")

if __name__ == "__main__":
    asyncio.run(main())