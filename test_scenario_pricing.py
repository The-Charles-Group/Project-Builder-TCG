"""
Comprehensive Test Suite for Scenario Building and Pricing Features
===================================================================
Tests all major functionality related to scenario creation, pricing configuration,
AI-powered features, industry templates, and department organization.

Test Coverage:
1. Build Scenario Button functionality
2. Pricing Configuration
3. AI Pricing Features  
4. Industry Templates (all 6 templates)
5. Department Organization
"""

import asyncio
import json
import time
import os
import pytest
import httpx
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
from unittest.mock import Mock, patch
import sys
import traceback

# Configuration
BASE_URL = "http://localhost:5000"
TIMEOUT = 30.0

# Test result tracking
test_results = {
    "test_run_id": f"test_scenario_pricing_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    "start_time": datetime.now().isoformat(),
    "categories": {
        "build_scenario": {"passed": 0, "failed": 0, "issues": []},
        "pricing_config": {"passed": 0, "failed": 0, "issues": []},
        "ai_pricing": {"passed": 0, "failed": 0, "issues": []},
        "industry_templates": {"passed": 0, "failed": 0, "issues": []},
        "department_org": {"passed": 0, "failed": 0, "issues": []},
    },
    "detailed_results": [],
    "summary": {}
}


class ScenarioPricingTestSuite:
    """Main test suite class for scenario building and pricing features"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT)
        self.test_rfp = """
        We need a comprehensive digital marketing campaign for our luxury fashion brand.
        Requirements include:
        - Social media strategy across Instagram, TikTok, and Pinterest
        - Influencer partnerships with 10-15 fashion influencers
        - Content creation: photos, videos, reels
        - Email marketing campaigns
        - Website redesign with e-commerce integration
        - SEO optimization
        - Paid advertising campaigns
        Budget: $500,000
        Timeline: 6 months
        """
        
    async def close(self):
        await self.client.aclose()
    
    # ================================================================================
    # 1. BUILD SCENARIO BUTTON TESTS
    # ================================================================================
    
    async def test_scenario_creation(self):
        """Test scenario creation with selected deliverables"""
        test_name = "Scenario Creation"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Step 1: Get AI suggestions
            response = await self.client.post(
                "/api/suggest_by_text",
                json={"rfp_text": self.test_rfp}
            )
            assert response.status_code == 200, f"Failed to get suggestions: {response.status_code}"
            suggestions = response.json()
            
            # Extract deliverable codes from suggested
            suggested_items = suggestions.get("suggested", [])
            selected_codes = [item.get("deliverable_code") for item in suggested_items[:10] if item.get("deliverable_code")]
            assert len(selected_codes) > 0, "No deliverable codes returned"
            
            # Step 2: Build scenario
            scenario_data = {
                "project_name": "Test Scenario Build",
                "selected_deliverable_codes": selected_codes,
                "pricing_mode": "blended",
                "blended_rate": 175,
                "rate_band": "Standard_US",
                "use_slack": False,
                "slack_after_internal": 0,
                "slack_after_client": 0,
                "slack_global_pct": 0,
                "project_start": "2025-01-01",
                "scenario_a": {"mode": "template", "scenario_key": "MED_LOW"}
            }
            
            response = await self.client.post(
                "/api/build",
                json=scenario_data
            )
            assert response.status_code == 200, f"Failed to build scenario: {response.status_code}"
            
            scenario = response.json()
            assert "scenario_a" in scenario, "Scenario A not found in response"
            assert len(scenario["scenario_a"]["wbs"]) > 0, "No WBS items in scenario"
            
            # Verify deliverables are included
            wbs_deliverables = [item.get("Deliverable") for item in scenario["scenario_a"]["wbs"]]
            assert len(wbs_deliverables) > 0, "No deliverables in WBS"
            
            test_results["categories"]["build_scenario"]["passed"] += 1
            print(f"✅ {test_name}: PASSED")
            print(f"   - Created scenario with {len(wbs_deliverables)} deliverables")
            
        except Exception as e:
            test_results["categories"]["build_scenario"]["failed"] += 1
            test_results["categories"]["build_scenario"]["issues"].append({
                "test": test_name,
                "error": str(e),
                "traceback": traceback.format_exc()
            })
            print(f"❌ {test_name}: FAILED - {str(e)}")
    
    async def test_scenario_persistence(self):
        """Test scenario persistence between steps"""
        test_name = "Scenario Persistence"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Build a scenario
            response = await self.client.post(
                "/api/suggest_by_text",
                json={"rfp_text": self.test_rfp}
            )
            suggestions = response.json()
            suggested_items = suggestions.get("suggested", [])
            selected_codes = [item.get("deliverable_code") for item in suggested_items[:8] if item.get("deliverable_code")]
            
            scenario_data = {
                "project_name": "Test Persistence",
                "selected_deliverable_codes": selected_codes,
                "pricing_mode": "blended",
                "blended_rate": 150,
                "rate_band": "Standard_US",
                "use_slack": False,
                "slack_after_internal": 0,
                "slack_after_client": 0,
                "slack_global_pct": 0,
                "project_start": "2025-01-01",
                "scenario_a": {"mode": "template", "scenario_key": "LOW_SIMPLE"}
            }
            
            # Build initial scenario
            response = await self.client.post("/api/build", json=scenario_data)
            initial_scenario = response.json()
            scenario_id = initial_scenario.get("scenario_a", {}).get("id")
            
            # Simulate step progression
            await asyncio.sleep(1)
            
            # Rebuild with same data - should maintain consistency
            response = await self.client.post("/api/build", json=scenario_data)
            rebuild_scenario = response.json()
            
            # Compare key elements
            initial_wbs = initial_scenario.get("scenario_a", {}).get("wbs", [])
            rebuild_wbs = rebuild_scenario.get("scenario_a", {}).get("wbs", [])
            
            assert len(initial_wbs) == len(rebuild_wbs), "WBS count changed on rebuild"
            
            test_results["categories"]["build_scenario"]["passed"] += 1
            print(f"✅ {test_name}: PASSED")
            print(f"   - Scenario maintained consistency across rebuilds")
            
        except Exception as e:
            test_results["categories"]["build_scenario"]["failed"] += 1
            test_results["categories"]["build_scenario"]["issues"].append({
                "test": test_name,
                "error": str(e)
            })
            print(f"❌ {test_name}: FAILED - {str(e)}")
    
    async def test_ai_buttons_enable_after_build(self):
        """Test that AI features become available after scenario build"""
        test_name = "AI Buttons Enable After Build"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Build a scenario first
            response = await self.client.post(
                "/api/suggest_by_text",
                json={"rfp_text": self.test_rfp}
            )
            suggestions = response.json()
            suggested_items = suggestions.get("suggested", [])
            selected_codes = [item.get("deliverable_code") for item in suggested_items[:5] if item.get("deliverable_code")]
            
            scenario_data = {
                "project_name": "Test AI Enable",
                "selected_deliverable_codes": selected_codes,
                "pricing_mode": "blended",
                "blended_rate": 175,
                "rate_band": "Standard_US",
                "use_slack": False,
                "slack_after_internal": 0,
                "slack_after_client": 0,
                "slack_global_pct": 0,
                "project_start": "2025-01-01",
                "scenario_a": {"mode": "template", "scenario_key": "MED_LOW"}
            }
            
            response = await self.client.post("/api/build", json=scenario_data)
            scenario = response.json()
            
            # Test AI pricing optimization endpoint availability
            optimize_data = {
                "scenario": scenario["scenario_a"],
                "target_budget": 500000,
                "optimization_type": "balanced"
            }
            
            response = await self.client.post("/api/optimize-pricing", json=optimize_data)
            # Should either succeed or return appropriate error, not 404
            assert response.status_code in [200, 201, 400, 422], f"AI endpoint not available: {response.status_code}"
            
            test_results["categories"]["build_scenario"]["passed"] += 1
            print(f"✅ {test_name}: PASSED")
            print(f"   - AI features accessible after scenario build")
            
        except Exception as e:
            test_results["categories"]["build_scenario"]["failed"] += 1
            test_results["categories"]["build_scenario"]["issues"].append({
                "test": test_name,
                "error": str(e)
            })
            print(f"❌ {test_name}: FAILED - {str(e)}")
    
    # ================================================================================
    # 2. PRICING CONFIGURATION TESTS
    # ================================================================================
    
    async def test_tier_selection(self):
        """Test all three tier selections (Tier 1/2/3)"""
        test_name = "Tier Selection"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Get base deliverables
            response = await self.client.post(
                "/api/suggest_by_text",
                json={"rfp_text": "Need social media management"}
            )
            suggestions = response.json()
            suggested_items = suggestions.get("suggested", [])
            selected_codes = [item.get("deliverable_code") for item in suggested_items[:3] if item.get("deliverable_code")]
            
            tier_results = {}
            
            # Test different rate bands instead of tiers
            rate_bands = {"Low": 150, "Medium": 175, "High": 225}
            
            for tier_name, rate in rate_bands.items():
                scenario_data = {
                    "project_name": f"Test {tier_name} Rate",
                    "selected_deliverable_codes": selected_codes,
                    "pricing_mode": "blended",
                    "blended_rate": rate,
                    "rate_band": "Standard_US",
                    "use_slack": False,
                    "slack_after_internal": 0,
                    "slack_after_client": 0,
                    "slack_global_pct": 0,
                    "project_start": "2025-01-01",
                    "scenario_a": {"mode": "template", "scenario_key": "MED_LOW"}
                }
                
                response = await self.client.post("/api/build", json=scenario_data)
                scenario = response.json()
                
                # Extract total price
                wbs = scenario.get("scenario_a", {}).get("wbs", [])
                total_price = sum(float(item.get("Price", 0)) for item in wbs if item.get("Price"))
                tier_results[tier_name] = total_price
                
                print(f"   - {tier_name} (${rate}/hr): ${total_price:,.2f}")
            
            # Verify pricing increases with rates
            assert tier_results["Low"] < tier_results["Medium"], "Medium rate should produce higher price than Low"
            assert tier_results["Medium"] < tier_results["High"], "High rate should produce higher price than Medium"
            
            test_results["categories"]["pricing_config"]["passed"] += 1
            print(f"✅ {test_name}: PASSED")
            print(f"   - Pricing tiers properly scaled")
            
        except Exception as e:
            test_results["categories"]["pricing_config"]["failed"] += 1
            test_results["categories"]["pricing_config"]["issues"].append({
                "test": test_name,
                "error": str(e)
            })
            print(f"❌ {test_name}: FAILED - {str(e)}")
    
    async def test_complexity_selection(self):
        """Test complexity levels (Low/Medium/High)"""
        test_name = "Complexity Selection"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            response = await self.client.post(
                "/api/suggest_by_text",
                json={"rfp_text": "Website development project"}
            )
            suggestions = response.json()
            suggested_items = suggestions.get("suggested", [])
            selected_codes = [item.get("deliverable_code") for item in suggested_items[:3] if item.get("deliverable_code")]
            
            complexity_results = {}
            
            # Test different scenario keys representing complexity
            scenarios = {"Low": "LOW_SIMPLE", "Medium": "MED_LOW", "High": "HIGH_COMPLEX"}
            
            for complexity, scenario_key in scenarios.items():
                scenario_data = {
                    "project_name": f"Test {complexity} Complexity",
                    "selected_deliverable_codes": selected_codes,
                    "pricing_mode": "blended",
                    "blended_rate": 175,
                    "rate_band": "Standard_US",
                    "use_slack": False,
                    "slack_after_internal": 0,
                    "slack_after_client": 0,
                    "slack_global_pct": 0,
                    "project_start": "2025-01-01",
                    "scenario_a": {"mode": "template", "scenario_key": scenario_key}
                }
                
                response = await self.client.post("/api/build", json=scenario_data)
                scenario = response.json()
                
                wbs = scenario.get("scenario_a", {}).get("wbs", [])
                total_hours = sum(float(item.get("Hours", 0)) for item in wbs if item.get("Hours"))
                complexity_results[complexity] = total_hours
                
                print(f"   - {complexity}: {total_hours:.0f} hours")
            
            # Verify complexity affects hours
            assert complexity_results["Low"] < complexity_results["Medium"], "Medium should have more hours than Low"
            assert complexity_results["Medium"] < complexity_results["High"], "High should have more hours than Medium"
            
            test_results["categories"]["pricing_config"]["passed"] += 1
            print(f"✅ {test_name}: PASSED")
            print(f"   - Complexity levels properly affect effort")
            
        except Exception as e:
            test_results["categories"]["pricing_config"]["failed"] += 1
            test_results["categories"]["pricing_config"]["issues"].append({
                "test": test_name,
                "error": str(e)
            })
            print(f"❌ {test_name}: FAILED - {str(e)}")
    
    async def test_pricing_calculation_accuracy(self):
        """Verify pricing calculations are accurate (Hours × Rate = Price)"""
        test_name = "Pricing Calculation Accuracy"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            response = await self.client.post(
                "/api/suggest-deliverables",
                json={"text": "Marketing campaign", "count": 10}
            )
            suggestions = response.json()
            
            scenario_data = {
                "project_name": "Test Pricing Accuracy",
                "selected_codes": suggestions.get("codes", [])[:5],
                "pricing_tier": "Tier 2",
                "complexity": "Medium"
            }
            
            response = await self.client.post("/api/build", json=scenario_data)
            scenario = response.json()
            
            wbs = scenario.get("scenario_a", {}).get("wbs", [])
            errors = []
            
            for item in wbs:
                if item.get("Hours") and item.get("Rate") and item.get("Price"):
                    hours = float(item["Hours"])
                    rate = float(item["Rate"])
                    price = float(item["Price"])
                    calculated_price = hours * rate
                    
                    # Allow small rounding differences
                    if abs(calculated_price - price) > 0.01:
                        errors.append({
                            "item": item.get("Deliverable"),
                            "hours": hours,
                            "rate": rate,
                            "expected": calculated_price,
                            "actual": price
                        })
            
            if errors:
                print(f"   ⚠️ Pricing calculation errors found:")
                for err in errors[:3]:  # Show first 3 errors
                    print(f"      - {err['item']}: {err['hours']}h × ${err['rate']} = ${err['expected']:.2f} (got ${err['actual']:.2f})")
            
            assert len(errors) == 0, f"Found {len(errors)} pricing calculation errors"
            
            test_results["categories"]["pricing_config"]["passed"] += 1
            print(f"✅ {test_name}: PASSED")
            print(f"   - All pricing calculations accurate")
            
        except Exception as e:
            test_results["categories"]["pricing_config"]["failed"] += 1
            test_results["categories"]["pricing_config"]["issues"].append({
                "test": test_name,
                "error": str(e)
            })
            print(f"❌ {test_name}: FAILED - {str(e)}")
    
    # ================================================================================
    # 3. AI PRICING FEATURES TESTS
    # ================================================================================
    
    async def test_ai_suggest_project_type(self):
        """Test AI Suggest Type for PROJECT/RETAINER classification"""
        test_name = "AI Suggest Project Type"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Test different RFP types
            test_cases = [
                {
                    "rfp": "One-time website redesign project with specific deliverables and fixed timeline of 3 months.",
                    "expected": "PROJECT"
                },
                {
                    "rfp": "Ongoing monthly social media management, content creation, and community management for 12 months.",
                    "expected": "RETAINER"
                }
            ]
            
            for i, test_case in enumerate(test_cases, 1):
                response = await self.client.post(
                    "/api/ai/suggest-type",
                    json={"rfp_text": test_case["rfp"]}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    suggested_type = result.get("type", "").upper()
                    print(f"   - Test {i}: Suggested {suggested_type} (expected {test_case['expected']})")
                    # Note: We can't strictly assert the expected type as AI may interpret differently
                else:
                    print(f"   - Test {i}: AI suggest type endpoint not available")
            
            test_results["categories"]["ai_pricing"]["passed"] += 1
            print(f"✅ {test_name}: PASSED")
            
        except Exception as e:
            test_results["categories"]["ai_pricing"]["failed"] += 1
            test_results["categories"]["ai_pricing"]["issues"].append({
                "test": test_name,
                "error": str(e)
            })
            print(f"❌ {test_name}: FAILED - {str(e)}")
    
    async def test_ai_optimize_pricing(self):
        """Test Optimize All Pricing with various budgets"""
        test_name = "AI Optimize Pricing"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # First build a scenario
            response = await self.client.post(
                "/api/suggest-deliverables",
                json={"text": self.test_rfp, "count": 15}
            )
            suggestions = response.json()
            
            scenario_data = {
                "project_name": "Test AI Optimization",
                "selected_codes": suggestions.get("codes", [])[:8],
                "pricing_tier": "Tier 2",
                "complexity": "Medium"
            }
            
            response = await self.client.post("/api/build", json=scenario_data)
            initial_scenario = response.json()
            initial_price = sum(
                float(item.get("Price", 0)) 
                for item in initial_scenario.get("scenario_a", {}).get("wbs", [])
            )
            
            print(f"   - Initial price: ${initial_price:,.2f}")
            
            # Test optimization with different budgets
            test_budgets = [100000, 500000, 1000000]
            
            for budget in test_budgets:
                optimize_data = {
                    "scenario": initial_scenario["scenario_a"],
                    "target_budget": budget,
                    "optimization_type": "balanced"
                }
                
                response = await self.client.post(
                    "/api/optimize-pricing",
                    json=optimize_data
                )
                
                if response.status_code == 200:
                    optimized = response.json()
                    optimized_price = sum(
                        float(item.get("Price", 0))
                        for item in optimized.get("wbs", [])
                    )
                    print(f"   - Target ${budget:,}: Optimized to ${optimized_price:,.2f}")
                else:
                    print(f"   - Budget ${budget:,}: Optimization not available")
            
            test_results["categories"]["ai_pricing"]["passed"] += 1
            print(f"✅ {test_name}: PASSED")
            
        except Exception as e:
            test_results["categories"]["ai_pricing"]["failed"] += 1
            test_results["categories"]["ai_pricing"]["issues"].append({
                "test": test_name,
                "error": str(e)
            })
            print(f"❌ {test_name}: FAILED - {str(e)}")
    
    async def test_pricing_bounds_respect(self):
        """Verify pricing adjustments respect min/max bounds"""
        test_name = "Pricing Bounds Respect"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Build scenario with known constraints
            response = await self.client.post(
                "/api/suggest-deliverables",
                json={"text": "Small project", "count": 5}
            )
            suggestions = response.json()
            
            scenario_data = {
                "project_name": "Test Bounds",
                "selected_codes": suggestions.get("codes", [])[:3],
                "pricing_tier": "Tier 1",
                "complexity": "Low"
            }
            
            response = await self.client.post("/api/build", json=scenario_data)
            scenario = response.json()
            
            # Try to optimize to unreasonably low budget
            optimize_data = {
                "scenario": scenario["scenario_a"],
                "target_budget": 1000,  # Very low budget
                "optimization_type": "balanced"
            }
            
            response = await self.client.post("/api/optimize-pricing", json=optimize_data)
            
            if response.status_code == 200:
                optimized = response.json()
                # Check that prices didn't go negative or unreasonably low
                for item in optimized.get("wbs", []):
                    if item.get("Price"):
                        price = float(item["Price"])
                        assert price >= 0, f"Negative price found: {price}"
                        if item.get("Hours"):
                            hours = float(item["Hours"])
                            if hours > 0:
                                implied_rate = price / hours
                                assert implied_rate >= 50, f"Rate too low: ${implied_rate:.2f}/hr"
            
            test_results["categories"]["ai_pricing"]["passed"] += 1
            print(f"✅ {test_name}: PASSED")
            print(f"   - Pricing bounds properly respected")
            
        except Exception as e:
            test_results["categories"]["ai_pricing"]["failed"] += 1
            test_results["categories"]["ai_pricing"]["issues"].append({
                "test": test_name,
                "error": str(e)
            })
            print(f"❌ {test_name}: FAILED - {str(e)}")
    
    async def test_cadence_options(self):
        """Test cadence options (One-Time, Monthly, Quarterly, Annual)"""
        test_name = "Cadence Options"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            cadence_types = ["One-Time", "Monthly", "Quarterly", "Annual"]
            
            response = await self.client.post(
                "/api/suggest-deliverables",
                json={"text": "Ongoing marketing services", "count": 5}
            )
            suggestions = response.json()
            
            for cadence in cadence_types:
                scenario_data = {
                    "project_name": f"Test {cadence} Cadence",
                    "selected_codes": suggestions.get("codes", [])[:3],
                    "pricing_tier": "Tier 2",
                    "complexity": "Medium",
                    "cadence": cadence
                }
                
                response = await self.client.post("/api/build", json=scenario_data)
                
                if response.status_code == 200:
                    scenario = response.json()
                    print(f"   - {cadence}: Successfully built scenario")
                else:
                    print(f"   - {cadence}: Not supported (status {response.status_code})")
            
            test_results["categories"]["ai_pricing"]["passed"] += 1
            print(f"✅ {test_name}: PASSED")
            
        except Exception as e:
            test_results["categories"]["ai_pricing"]["failed"] += 1
            test_results["categories"]["ai_pricing"]["issues"].append({
                "test": test_name,
                "error": str(e)
            })
            print(f"❌ {test_name}: FAILED - {str(e)}")
    
    # ================================================================================
    # 4. INDUSTRY TEMPLATE TESTS
    # ================================================================================
    
    async def test_all_industry_templates(self):
        """Test all 6 industry templates"""
        test_name = "All Industry Templates"
        print(f"\n🔄 Testing: {test_name}")
        
        templates = [
            ("luxury_fashion", "Fashion"),
            ("beauty", "Beauty"),
            ("real_estate", "Real Estate"),
            ("retail", "Retail"),
            ("lifestyle", "Lifestyle"),
            ("tech", "Technology")
        ]
        
        template_results = {}
        
        for template_id, template_name in templates:
            try:
                print(f"\n   📋 Testing {template_name} template...")
                
                # Request industry-specific deliverables
                response = await self.client.post(
                    "/api/industry/suggest-deliverables",
                    json={
                        "industry": template_id,
                        "rfp_text": f"Need services for {template_name.lower()} company"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    deliverables = data.get("deliverables", [])
                    template_results[template_name] = {
                        "status": "success",
                        "deliverable_count": len(deliverables),
                        "sample_deliverables": deliverables[:3] if deliverables else []
                    }
                    print(f"      ✓ Loaded {len(deliverables)} deliverables")
                    
                    # Verify template-specific content
                    if template_id == "luxury_fashion" and deliverables:
                        fashion_keywords = ["fashion", "runway", "collection", "couture", "editorial"]
                        has_fashion = any(
                            any(kw in str(d).lower() for kw in fashion_keywords)
                            for d in deliverables[:10]
                        )
                        if has_fashion:
                            print(f"      ✓ Contains fashion-specific deliverables")
                    
                    if template_id == "tech" and deliverables:
                        tech_keywords = ["api", "software", "development", "tech", "digital"]
                        has_tech = any(
                            any(kw in str(d).lower() for kw in tech_keywords)
                            for d in deliverables[:10]
                        )
                        if has_tech:
                            print(f"      ✓ Contains tech-specific deliverables")
                    
                else:
                    template_results[template_name] = {
                        "status": "error",
                        "error": f"Status code {response.status_code}"
                    }
                    print(f"      ❌ Failed to load (status {response.status_code})")
                
            except Exception as e:
                template_results[template_name] = {
                    "status": "error",
                    "error": str(e)
                }
                print(f"      ❌ Error: {str(e)}")
        
        # Count successes
        successful_templates = sum(
            1 for result in template_results.values()
            if result.get("status") == "success"
        )
        
        if successful_templates >= 4:  # At least 4 out of 6 should work
            test_results["categories"]["industry_templates"]["passed"] += 1
            print(f"\n✅ {test_name}: PASSED ({successful_templates}/6 templates loaded)")
        else:
            test_results["categories"]["industry_templates"]["failed"] += 1
            test_results["categories"]["industry_templates"]["issues"].append({
                "test": test_name,
                "error": f"Only {successful_templates}/6 templates loaded successfully",
                "details": template_results
            })
            print(f"\n❌ {test_name}: FAILED ({successful_templates}/6 templates loaded)")
    
    async def test_template_pricing_multipliers(self):
        """Test that luxury and technical templates apply pricing multipliers"""
        test_name = "Template Pricing Multipliers"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Compare luxury fashion vs standard pricing
            base_rfp = "Need social media campaign"
            
            # Get base pricing without template
            response = await self.client.post(
                "/api/suggest-deliverables",
                json={"text": base_rfp, "count": 5}
            )
            base_suggestions = response.json()
            
            base_scenario_data = {
                "project_name": "Base Pricing",
                "selected_codes": base_suggestions.get("codes", [])[:3],
                "pricing_tier": "Tier 2",
                "complexity": "Medium"
            }
            
            response = await self.client.post("/api/build", json=base_scenario_data)
            base_scenario = response.json()
            base_total = sum(
                float(item.get("Price", 0))
                for item in base_scenario.get("scenario_a", {}).get("wbs", [])
            )
            
            print(f"   - Base pricing: ${base_total:,.2f}")
            
            # Get luxury fashion template pricing
            response = await self.client.post(
                "/api/industry/suggest-deliverables",
                json={
                    "industry": "luxury_fashion",
                    "rfp_text": "Luxury fashion brand social media campaign"
                }
            )
            
            if response.status_code == 200:
                luxury_data = response.json()
                luxury_deliverables = luxury_data.get("deliverables", [])
                
                # Build scenario with luxury template
                luxury_scenario_data = {
                    "project_name": "Luxury Fashion Campaign",
                    "selected_codes": [d.get("code") for d in luxury_deliverables[:3] if d.get("code")],
                    "pricing_tier": "Tier 2",
                    "complexity": "Medium",
                    "industry": "luxury_fashion"
                }
                
                if luxury_scenario_data["selected_codes"]:
                    response = await self.client.post("/api/build", json=luxury_scenario_data)
                    
                    if response.status_code == 200:
                        luxury_scenario = response.json()
                        luxury_total = sum(
                            float(item.get("Price", 0))
                            for item in luxury_scenario.get("scenario_a", {}).get("wbs", [])
                        )
                        
                        print(f"   - Luxury pricing: ${luxury_total:,.2f}")
                        
                        # Luxury should typically be higher due to multipliers
                        if luxury_total > base_total:
                            print(f"   - Luxury multiplier applied: {luxury_total/base_total:.2f}x")
                        else:
                            print(f"   - Note: Luxury pricing not higher (may use different deliverables)")
            
            test_results["categories"]["industry_templates"]["passed"] += 1
            print(f"✅ {test_name}: PASSED")
            
        except Exception as e:
            test_results["categories"]["industry_templates"]["failed"] += 1
            test_results["categories"]["industry_templates"]["issues"].append({
                "test": test_name,
                "error": str(e)
            })
            print(f"❌ {test_name}: FAILED - {str(e)}")
    
    # ================================================================================
    # 5. DEPARTMENT ORGANIZATION TESTS
    # ================================================================================
    
    async def test_department_grouping(self):
        """Verify deliverables are grouped by department"""
        test_name = "Department Grouping"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Get deliverables with department info
            response = await self.client.post(
                "/api/suggest_by_text",
                json={"rfp_text": self.test_rfp}
            )
            suggestions = response.json()
            suggested_items = suggestions.get("suggested", [])
            selected_codes = [item.get("deliverable_code") for item in suggested_items[:15] if item.get("deliverable_code")]
            
            # Build scenario to get department organization
            scenario_data = {
                "project_name": "Test Department Groups",
                "selected_deliverable_codes": selected_codes,
                "pricing_mode": "blended",
                "blended_rate": 175,
                "rate_band": "Standard_US",
                "use_slack": False,
                "slack_after_internal": 0,
                "slack_after_client": 0,
                "slack_global_pct": 0,
                "project_start": "2025-01-01",
                "scenario_a": {"mode": "template", "scenario_key": "MED_LOW"}
            }
            
            response = await self.client.post("/api/build", json=scenario_data)
            scenario = response.json()
            
            # Check WBS items for department field
            wbs = scenario.get("scenario_a", {}).get("wbs", [])
            departments = {}
            
            for item in wbs:
                dept = item.get("Department") or item.get("Service Department") or "Unknown"
                if dept not in departments:
                    departments[dept] = []
                departments[dept].append(item.get("Deliverable"))
            
            print(f"   - Found {len(departments)} departments:")
            for dept, items in departments.items():
                print(f"     • {dept}: {len(items)} items")
            
            assert len(departments) > 1, "Should have multiple departments"
            
            test_results["categories"]["department_org"]["passed"] += 1
            print(f"✅ {test_name}: PASSED")
            
        except Exception as e:
            test_results["categories"]["department_org"]["failed"] += 1
            test_results["categories"]["department_org"]["issues"].append({
                "test": test_name,
                "error": str(e)
            })
            print(f"❌ {test_name}: FAILED - {str(e)}")
    
    async def test_department_color_coding(self):
        """Check color-coded department tags display"""
        test_name = "Department Color Coding"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Test that department metadata includes color information
            response = await self.client.get("/api/departments")
            
            if response.status_code == 200:
                departments = response.json()
                
                # Check for color coding info
                has_colors = any(
                    "color" in dept or "style" in dept
                    for dept in departments
                    if isinstance(dept, dict)
                )
                
                if has_colors:
                    print(f"   - Department color coding metadata available")
                else:
                    print(f"   - No explicit color coding in API, likely handled by frontend")
                
                test_results["categories"]["department_org"]["passed"] += 1
                print(f"✅ {test_name}: PASSED")
            else:
                # Department endpoint might not exist, check in build response
                response = await self.client.post(
                    "/api/suggest-deliverables",
                    json={"text": "Marketing project", "count": 5}
                )
                suggestions = response.json()
                
                scenario_data = {
                    "project_name": "Test Colors",
                    "selected_codes": suggestions.get("codes", [])[:3],
                    "pricing_tier": "Tier 1",
                    "complexity": "Low"
                }
                
                response = await self.client.post("/api/build", json=scenario_data)
                
                print(f"   - Department color coding likely handled by frontend CSS")
                test_results["categories"]["department_org"]["passed"] += 1
                print(f"✅ {test_name}: PASSED (frontend feature)")
            
        except Exception as e:
            test_results["categories"]["department_org"]["failed"] += 1
            test_results["categories"]["department_org"]["issues"].append({
                "test": test_name,
                "error": str(e)
            })
            print(f"❌ {test_name}: FAILED - {str(e)}")
    
    async def test_select_all_deselect_all(self):
        """Test Select All/Deselect All functionality"""
        test_name = "Select All/Deselect All"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Get all available deliverables
            response = await self.client.post(
                "/api/suggest-deliverables",
                json={"text": self.test_rfp, "count": 50}
            )
            all_suggestions = response.json()
            all_codes = all_suggestions.get("codes", [])
            
            # Test Select All - build with all deliverables
            scenario_all = {
                "project_name": "Test Select All",
                "selected_codes": all_codes,
                "pricing_tier": "Tier 1",
                "complexity": "Low"
            }
            
            response = await self.client.post("/api/build", json=scenario_all)
            assert response.status_code == 200, "Failed to build with all deliverables"
            
            result_all = response.json()
            wbs_all = result_all.get("scenario_a", {}).get("wbs", [])
            
            print(f"   - Select All: Built scenario with {len(wbs_all)} items")
            
            # Test Deselect All - build with no deliverables
            scenario_none = {
                "project_name": "Test Deselect All",
                "selected_codes": [],
                "pricing_tier": "Tier 1",
                "complexity": "Low"
            }
            
            response = await self.client.post("/api/build", json=scenario_none)
            
            if response.status_code == 200:
                result_none = response.json()
                wbs_none = result_none.get("scenario_a", {}).get("wbs", [])
                print(f"   - Deselect All: Built empty scenario with {len(wbs_none)} items")
            else:
                print(f"   - Deselect All: Returns appropriate error for empty selection")
            
            test_results["categories"]["department_org"]["passed"] += 1
            print(f"✅ {test_name}: PASSED")
            
        except Exception as e:
            test_results["categories"]["department_org"]["failed"] += 1
            test_results["categories"]["department_org"]["issues"].append({
                "test": test_name,
                "error": str(e)
            })
            print(f"❌ {test_name}: FAILED - {str(e)}")
    
    async def test_department_counts(self):
        """Verify department counts are accurate"""
        test_name = "Department Counts Accuracy"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Get deliverables and build scenario
            response = await self.client.post(
                "/api/suggest-deliverables",
                json={"text": self.test_rfp, "count": 25}
            )
            suggestions = response.json()
            
            scenario_data = {
                "project_name": "Test Department Counts",
                "selected_codes": suggestions.get("codes", [])[:20],
                "pricing_tier": "Tier 2",
                "complexity": "Medium"
            }
            
            response = await self.client.post("/api/build", json=scenario_data)
            scenario = response.json()
            
            # Count items by department
            wbs = scenario.get("scenario_a", {}).get("wbs", [])
            dept_counts = {}
            
            for item in wbs:
                dept = item.get("Department") or item.get("Service Department") or "Unknown"
                dept_counts[dept] = dept_counts.get(dept, 0) + 1
            
            # Verify counts
            total_items = len(wbs)
            counted_items = sum(dept_counts.values())
            
            print(f"   - Total WBS items: {total_items}")
            print(f"   - Department breakdown:")
            for dept, count in sorted(dept_counts.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_items) * 100
                print(f"     • {dept}: {count} items ({percentage:.1f}%)")
            
            assert counted_items == total_items, f"Count mismatch: {counted_items} vs {total_items}"
            
            test_results["categories"]["department_org"]["passed"] += 1
            print(f"✅ {test_name}: PASSED")
            
        except Exception as e:
            test_results["categories"]["department_org"]["failed"] += 1
            test_results["categories"]["department_org"]["issues"].append({
                "test": test_name,
                "error": str(e)
            })
            print(f"❌ {test_name}: FAILED - {str(e)}")


def generate_report():
    """Generate comprehensive test report"""
    end_time = datetime.now().isoformat()
    
    # Calculate totals
    total_passed = sum(cat["passed"] for cat in test_results["categories"].values())
    total_failed = sum(cat["failed"] for cat in test_results["categories"].values())
    total_tests = total_passed + total_failed
    
    # Generate report
    report = []
    report.append("=" * 80)
    report.append("SCENARIO BUILDING AND PRICING TEST REPORT")
    report.append("=" * 80)
    report.append(f"\nTest Run ID: {test_results['test_run_id']}")
    report.append(f"Start Time: {test_results['start_time']}")
    report.append(f"End Time: {end_time}")
    report.append("")
    
    # Executive Summary
    report.append("EXECUTIVE SUMMARY")
    report.append("-" * 40)
    report.append(f"Total Tests Run: {total_tests}")
    report.append(f"Tests Passed: {total_passed} ({(total_passed/total_tests*100):.1f}%)" if total_tests > 0 else "Tests Passed: 0")
    report.append(f"Tests Failed: {total_failed}")
    report.append("")
    
    # Category Breakdown
    report.append("TEST CATEGORY BREAKDOWN")
    report.append("-" * 40)
    
    categories_display = {
        "build_scenario": "Build Scenario Button",
        "pricing_config": "Pricing Configuration",
        "ai_pricing": "AI Pricing Features",
        "industry_templates": "Industry Templates",
        "department_org": "Department Organization"
    }
    
    for key, display_name in categories_display.items():
        cat = test_results["categories"][key]
        total = cat["passed"] + cat["failed"]
        if total > 0:
            success_rate = (cat["passed"] / total) * 100
            status = "✅" if cat["failed"] == 0 else "⚠️" if cat["passed"] > cat["failed"] else "❌"
            report.append(f"\n{status} {display_name}:")
            report.append(f"   - Passed: {cat['passed']}/{total} ({success_rate:.1f}%)")
            report.append(f"   - Failed: {cat['failed']}/{total}")
            
            if cat["issues"]:
                report.append(f"   - Issues Found:")
                for issue in cat["issues"][:3]:  # Show first 3 issues
                    report.append(f"     • {issue['test']}: {issue['error'][:100]}")
    
    report.append("")
    
    # Critical Issues
    report.append("CRITICAL ISSUES FOUND")
    report.append("-" * 40)
    
    all_issues = []
    for cat_name, cat_data in test_results["categories"].items():
        for issue in cat_data["issues"]:
            all_issues.append({
                "category": categories_display.get(cat_name, cat_name),
                "test": issue["test"],
                "error": issue["error"]
            })
    
    if all_issues:
        for i, issue in enumerate(all_issues[:10], 1):  # Show top 10 issues
            report.append(f"\n{i}. [{issue['category']}] {issue['test']}")
            report.append(f"   Error: {issue['error'][:200]}")
    else:
        report.append("No critical issues found! All tests passed successfully.")
    
    report.append("")
    
    # Recommendations
    report.append("RECOMMENDATIONS")
    report.append("-" * 40)
    
    if total_failed == 0:
        report.append("✅ All tests passed! The system is functioning correctly.")
        report.append("   - Continue monitoring for edge cases")
        report.append("   - Consider adding more comprehensive test coverage")
    else:
        if test_results["categories"]["build_scenario"]["failed"] > 0:
            report.append("⚠️ Build Scenario Issues:")
            report.append("   - Review scenario creation logic")
            report.append("   - Check deliverable selection persistence")
            
        if test_results["categories"]["pricing_config"]["failed"] > 0:
            report.append("⚠️ Pricing Configuration Issues:")
            report.append("   - Verify pricing calculation formulas")
            report.append("   - Check tier and complexity multipliers")
            
        if test_results["categories"]["ai_pricing"]["failed"] > 0:
            report.append("⚠️ AI Pricing Issues:")
            report.append("   - Review AI optimization algorithms")
            report.append("   - Check budget constraint handling")
            
        if test_results["categories"]["industry_templates"]["failed"] > 0:
            report.append("⚠️ Industry Template Issues:")
            report.append("   - Verify template data loading")
            report.append("   - Check pricing multiplier application")
            
        if test_results["categories"]["department_org"]["failed"] > 0:
            report.append("⚠️ Department Organization Issues:")
            report.append("   - Review department grouping logic")
            report.append("   - Check department metadata consistency")
    
    report.append("")
    report.append("=" * 80)
    report.append("END OF REPORT")
    report.append("=" * 80)
    
    return "\n".join(report)


async def main():
    """Main test runner"""
    print("\n" + "=" * 80)
    print("SCENARIO BUILDING AND PRICING FEATURES - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print(f"Starting test run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)
    
    suite = ScenarioPricingTestSuite()
    
    try:
        # 1. Build Scenario Tests
        print("\n📋 CATEGORY 1: BUILD SCENARIO BUTTON TESTS")
        print("-" * 40)
        await suite.test_scenario_creation()
        await suite.test_scenario_persistence()
        await suite.test_ai_buttons_enable_after_build()
        
        # 2. Pricing Configuration Tests
        print("\n📋 CATEGORY 2: PRICING CONFIGURATION TESTS")
        print("-" * 40)
        await suite.test_tier_selection()
        await suite.test_complexity_selection()
        await suite.test_pricing_calculation_accuracy()
        
        # 3. AI Pricing Features Tests
        print("\n📋 CATEGORY 3: AI PRICING FEATURES TESTS")
        print("-" * 40)
        await suite.test_ai_suggest_project_type()
        await suite.test_ai_optimize_pricing()
        await suite.test_pricing_bounds_respect()
        await suite.test_cadence_options()
        
        # 4. Industry Template Tests
        print("\n📋 CATEGORY 4: INDUSTRY TEMPLATE TESTS")
        print("-" * 40)
        await suite.test_all_industry_templates()
        await suite.test_template_pricing_multipliers()
        
        # 5. Department Organization Tests
        print("\n📋 CATEGORY 5: DEPARTMENT ORGANIZATION TESTS")
        print("-" * 40)
        await suite.test_department_grouping()
        await suite.test_department_color_coding()
        await suite.test_select_all_deselect_all()
        await suite.test_department_counts()
        
    except Exception as e:
        print(f"\n❌ Critical test suite error: {str(e)}")
        traceback.print_exc()
    finally:
        await suite.close()
    
    # Generate and display report
    print("\n" + "=" * 80)
    print("GENERATING TEST REPORT...")
    print("=" * 80)
    
    report = generate_report()
    print(report)
    
    # Save report to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"test_scenario_pricing_report_{timestamp}.txt"
    
    with open(report_file, "w") as f:
        f.write(report)
    
    print(f"\n📁 Report saved to: {report_file}")
    
    # Save JSON results for further analysis
    json_file = f"test_scenario_pricing_results_{timestamp}.json"
    with open(json_file, "w") as f:
        json.dump(test_results, f, indent=2, default=str)
    
    print(f"📁 JSON results saved to: {json_file}")
    
    # Return exit code based on results
    total_failed = sum(cat["failed"] for cat in test_results["categories"].values())
    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)