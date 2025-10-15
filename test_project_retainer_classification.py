"""
Comprehensive Tests for PROJECT vs RETAINER Classification with All Cadence Options
================================================================================

Tests the classification system for distinguishing between:
- PROJECT: One-time engagements with fixed scope and defined start/end dates
- RETAINER: Ongoing engagements with various cadences (monthly, quarterly, semi-annual, annual)

Author: Agency Project Builder Test Suite
Date: October 2025
"""

import os
import sys
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import httpx
import pytest
from colorama import init, Fore, Style

# Initialize colorama for colored output
init(autoreset=True)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000")
TIMEOUT = 30.0

# Test Data - RFP Scenarios for Different Engagement Types
# =========================================================

# PROJECT-type RFP (One-time engagement with clear deliverables)
PROJECT_RFP = """
We are seeking an agency partner for a comprehensive brand refresh and website redesign project. 
This is a one-time engagement with the following deliverables:

1. Brand Strategy Document - Complete brand positioning, values, and messaging framework
2. Visual Identity System - New logo, color palette, typography, and brand guidelines
3. Website Design & Development - Full redesign and development of corporate website (20-25 pages)
4. Marketing Collateral - Design of business cards, letterhead, and presentation templates
5. Launch Campaign Strategy - Go-to-market strategy for brand unveiling

Project Timeline: 3-4 months from kickoff to launch
Budget: $250,000 - $350,000
Success Criteria: Completed deliverables, brand launch by Q2 2025
"""

# RETAINER-type RFP (Ongoing monthly services)
MONTHLY_RETAINER_RFP = """
We need a digital marketing agency for ongoing monthly marketing services starting January 2025:

Monthly Services Required:
- Social Media Management: Daily posting, community management, monthly reporting
- Paid Media Management: Google Ads, Facebook/Instagram ads, monthly optimization
- Content Creation: 8-10 blog posts per month, 20+ social posts monthly
- Email Marketing: Weekly newsletters, monthly campaign management
- SEO Optimization: Ongoing keyword research, monthly technical audits
- Analytics & Reporting: Monthly performance reports and quarterly business reviews

Contract Duration: 12-month retainer with monthly renewal
Monthly Budget: $25,000 - $30,000
Performance Reviews: Monthly check-ins, quarterly deep-dives
"""

# QUARTERLY RETAINER RFP (Quarterly business review cycle)
QUARTERLY_RETAINER_RFP = """
Seeking strategic consulting partner for quarterly business planning and execution:

Quarterly Deliverables:
- Quarterly Business Reviews (QBRs) - In-depth performance analysis and strategy adjustments
- Market Research Reports - Quarterly competitive analysis and market trends
- Campaign Planning - Quarterly integrated marketing campaign development
- Budget Optimization - Quarterly media spend review and reallocation
- Team Training - Quarterly workshops and capability building sessions

Engagement Model: Quarterly retainer with 3-month planning cycles
Quarterly Budget: $75,000 - $100,000
Review Cadence: Major QBRs every 3 months, monthly status updates
"""

# SEMI-ANNUAL RETAINER RFP (Semi-annual campaign cycles)
SEMIANNUAL_RETAINER_RFP = """
Looking for creative agency for bi-annual seasonal campaign development:

Semi-Annual Requirements:
- Spring/Summer Campaign (Jan-June): Full creative development, production, and launch
- Fall/Winter Campaign (July-Dec): Complete campaign refresh and holiday promotions
- Seasonal Product Photography: Twice yearly photoshoots
- Retail Partner Materials: Semi-annual dealer/retailer toolkit updates
- Trade Show Support: Major presence at two annual industry events

Cadence: Semi-annual retainer aligned with retail seasons
Semi-Annual Budget: $200,000 per season
Major Milestones: Campaign launches in March and September
"""

# ANNUAL RETAINER RFP (Annual planning and strategy)
ANNUAL_RETAINER_RFP = """
Enterprise client seeking annual strategic planning and brand stewardship:

Annual Engagement Scope:
- Annual Brand Strategy & Planning: Yearly strategic planning session and roadmap
- Annual Report Design & Production: Complete annual report creation
- Annual Conference & Event Support: Major annual user conference and roadshow
- Annual Brand Health Study: Comprehensive annual brand tracking research
- Annual Creative Refresh: Yearly update of all brand materials and guidelines

Contract: Annual retainer with yearly renewal
Annual Budget: $500,000 - $750,000
Review Points: Annual planning in Q4, mid-year review in Q2
"""

# HYBRID RFP (Mix of project and retainer work)
HYBRID_RFP = """
We need both immediate project work and ongoing support:

Immediate Projects (Q1 2025):
- Website Redesign: Complete overhaul of corporate website
- Brand Guidelines: Comprehensive brand book development
- Launch Video: 3-minute brand anthem video production

Ongoing Retainer Services (Starting Q2 2025):
- Monthly Social Media Management: Daily posting and community management
- Quarterly Campaign Development: Seasonal marketing campaigns
- Annual Strategy Planning: Yearly brand and marketing strategy sessions
- Weekly Content Creation: Blog posts, social content, email newsletters

Initial Project Budget: $150,000
Monthly Retainer Budget: $20,000 (12-month commitment)
"""

# Test Deliverables for Classification
# =====================================

TEST_DELIVERABLES_PROJECT = [
    {"code": "brand_strategy", "name": "Brand Strategy Document", "expected_type": "PROJECT"},
    {"code": "logo_design", "name": "Logo Design and Visual Identity", "expected_type": "PROJECT"},
    {"code": "website_build", "name": "Website Development", "expected_type": "PROJECT"},
    {"code": "brand_guidelines", "name": "Brand Guidelines Creation", "expected_type": "PROJECT"},
    {"code": "launch_campaign", "name": "Launch Campaign Strategy", "expected_type": "PROJECT"},
    {"code": "setup_analytics", "name": "Analytics Setup and Configuration", "expected_type": "PROJECT"},
    {"code": "audit_seo", "name": "SEO Audit and Recommendations", "expected_type": "PROJECT"},
    {"code": "migration_platform", "name": "Platform Migration Project", "expected_type": "PROJECT"}
]

TEST_DELIVERABLES_RETAINER = [
    {"code": "social_management", "name": "Social Media Management", "expected_type": "RETAINER"},
    {"code": "ppc_management", "name": "PPC Campaign Management", "expected_type": "RETAINER"},
    {"code": "content_monthly", "name": "Monthly Content Creation", "expected_type": "RETAINER"},
    {"code": "seo_ongoing", "name": "Ongoing SEO Optimization", "expected_type": "RETAINER"},
    {"code": "reporting_monthly", "name": "Monthly Performance Reporting", "expected_type": "RETAINER"},
    {"code": "community_mgmt", "name": "Community Management", "expected_type": "RETAINER"},
    {"code": "email_marketing", "name": "Email Marketing Management", "expected_type": "RETAINER"},
    {"code": "maintenance_web", "name": "Website Maintenance and Updates", "expected_type": "RETAINER"}
]

# Test Class
# ==========

class TestProjectRetainerClassification:
    def __init__(self):
        self.client = None
        self.test_results = []
        self.passed = 0
        self.failed = 0
        
    async def setup(self):
        """Initialize HTTP client and verify server is running"""
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT))
        
        # Verify server is running
        try:
            response = await self.client.get(f"{API_BASE_URL}/api/ai/health")
            if response.status_code != 200:
                raise Exception(f"Server health check failed: {response.status_code}")
            print(f"{Fore.GREEN}✅ Server is running and healthy{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}❌ Failed to connect to server: {e}{Style.RESET_ALL}")
            raise
    
    async def teardown(self):
        """Cleanup HTTP client"""
        if self.client:
            await self.client.aclose()
    
    async def test_project_classification(self):
        """Test 1: PROJECT Classification for One-time Engagements"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"TEST 1: PROJECT CLASSIFICATION - ONE-TIME ENGAGEMENTS")
        print(f"{'='*80}{Style.RESET_ALL}")
        
        # Test with PROJECT-type RFP
        response = await self.client.post(
            f"{API_BASE_URL}/api/ai/analyze_project_retainer",
            json={
                "rfp_text": PROJECT_RFP,
                "deliverables": TEST_DELIVERABLES_PROJECT
            }
        )
        
        if response.status_code != 200:
            self.failed += 1
            print(f"{Fore.RED}❌ API call failed: {response.status_code}{Style.RESET_ALL}")
            return
        
        result = response.json()
        suggestions = result.get("suggestions", {})
        method = result.get("method", "unknown")
        
        print(f"\n{Fore.YELLOW}Method used: {method}{Style.RESET_ALL}")
        print(f"\n{Fore.WHITE}Classification Results for PROJECT-type RFP:{Style.RESET_ALL}")
        
        correct = 0
        total = len(TEST_DELIVERABLES_PROJECT)
        
        for deliverable in TEST_DELIVERABLES_PROJECT:
            code = deliverable["code"]
            name = deliverable["name"]
            expected = deliverable["expected_type"]
            
            suggestion = suggestions.get(code, {})
            predicted = suggestion.get("type", "UNKNOWN")
            confidence = suggestion.get("confidence", 0)
            reasoning = suggestion.get("reasoning", "No reasoning provided")
            
            is_correct = predicted == expected
            if is_correct:
                correct += 1
                status_icon = "✅"
                color = Fore.GREEN
            else:
                status_icon = "❌"
                color = Fore.RED
            
            print(f"\n{status_icon} {name}")
            print(f"   Expected: {expected} | Predicted: {color}{predicted}{Style.RESET_ALL}")
            print(f"   Confidence: {confidence:.2f}")
            print(f"   Reasoning: {reasoning[:100]}...")
        
        accuracy = (correct / total) * 100
        print(f"\n{Fore.CYAN}Accuracy: {accuracy:.1f}% ({correct}/{total} correct){Style.RESET_ALL}")
        
        if accuracy >= 75:
            self.passed += 1
            print(f"{Fore.GREEN}✅ PROJECT classification test PASSED{Style.RESET_ALL}")
        else:
            self.failed += 1
            print(f"{Fore.RED}❌ PROJECT classification test FAILED{Style.RESET_ALL}")
        
        self.test_results.append({
            "test": "PROJECT Classification",
            "accuracy": accuracy,
            "passed": accuracy >= 75
        })
    
    async def test_monthly_retainer_classification(self):
        """Test 2: RETAINER Classification - Monthly Cadence"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"TEST 2: MONTHLY RETAINER CLASSIFICATION")
        print(f"{'='*80}{Style.RESET_ALL}")
        
        response = await self.client.post(
            f"{API_BASE_URL}/api/ai/analyze_project_retainer",
            json={
                "rfp_text": MONTHLY_RETAINER_RFP,
                "deliverables": TEST_DELIVERABLES_RETAINER
            }
        )
        
        if response.status_code != 200:
            self.failed += 1
            print(f"{Fore.RED}❌ API call failed: {response.status_code}{Style.RESET_ALL}")
            return
        
        result = response.json()
        suggestions = result.get("suggestions", {})
        
        print(f"\n{Fore.WHITE}Classification Results for MONTHLY RETAINER RFP:{Style.RESET_ALL}")
        
        correct = 0
        total = len(TEST_DELIVERABLES_RETAINER)
        
        for deliverable in TEST_DELIVERABLES_RETAINER:
            code = deliverable["code"]
            name = deliverable["name"]
            expected = deliverable["expected_type"]
            
            suggestion = suggestions.get(code, {})
            predicted = suggestion.get("type", "UNKNOWN")
            confidence = suggestion.get("confidence", 0)
            
            is_correct = predicted == expected
            if is_correct:
                correct += 1
                status_icon = "✅"
            else:
                status_icon = "❌"
            
            print(f"{status_icon} {name}: {predicted} (confidence: {confidence:.2f})")
        
        accuracy = (correct / total) * 100
        print(f"\n{Fore.CYAN}Accuracy: {accuracy:.1f}% ({correct}/{total} correct){Style.RESET_ALL}")
        
        if accuracy >= 75:
            self.passed += 1
            print(f"{Fore.GREEN}✅ MONTHLY RETAINER classification test PASSED{Style.RESET_ALL}")
        else:
            self.failed += 1
            print(f"{Fore.RED}❌ MONTHLY RETAINER classification test FAILED{Style.RESET_ALL}")
        
        self.test_results.append({
            "test": "Monthly Retainer Classification",
            "accuracy": accuracy,
            "passed": accuracy >= 75
        })
    
    async def test_quarterly_retainer_classification(self):
        """Test 3: RETAINER Classification - Quarterly Cadence"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"TEST 3: QUARTERLY RETAINER CLASSIFICATION")
        print(f"{'='*80}{Style.RESET_ALL}")
        
        # Define quarterly-specific deliverables
        quarterly_deliverables = [
            {"code": "qbr_planning", "name": "Quarterly Business Review Planning", "expected_type": "RETAINER"},
            {"code": "market_research", "name": "Quarterly Market Research Reports", "expected_type": "RETAINER"},
            {"code": "campaign_quarterly", "name": "Quarterly Campaign Development", "expected_type": "RETAINER"},
            {"code": "budget_review", "name": "Quarterly Budget Optimization", "expected_type": "RETAINER"}
        ]
        
        response = await self.client.post(
            f"{API_BASE_URL}/api/ai/analyze_project_retainer",
            json={
                "rfp_text": QUARTERLY_RETAINER_RFP,
                "deliverables": quarterly_deliverables
            }
        )
        
        if response.status_code != 200:
            self.failed += 1
            print(f"{Fore.RED}❌ API call failed: {response.status_code}{Style.RESET_ALL}")
            return
        
        result = response.json()
        suggestions = result.get("suggestions", {})
        
        print(f"\n{Fore.WHITE}Classification Results for QUARTERLY RETAINER RFP:{Style.RESET_ALL}")
        
        correct = 0
        total = len(quarterly_deliverables)
        
        for deliverable in quarterly_deliverables:
            code = deliverable["code"]
            name = deliverable["name"]
            expected = deliverable["expected_type"]
            
            suggestion = suggestions.get(code, {})
            predicted = suggestion.get("type", "UNKNOWN")
            confidence = suggestion.get("confidence", 0)
            
            is_correct = predicted == expected
            if is_correct:
                correct += 1
                status_icon = "✅"
            else:
                status_icon = "❌"
            
            print(f"{status_icon} {name}: {predicted} (confidence: {confidence:.2f})")
        
        accuracy = (correct / total) * 100
        print(f"\n{Fore.CYAN}Accuracy: {accuracy:.1f}% ({correct}/{total} correct){Style.RESET_ALL}")
        
        if accuracy >= 75:
            self.passed += 1
            print(f"{Fore.GREEN}✅ QUARTERLY RETAINER classification test PASSED{Style.RESET_ALL}")
        else:
            self.failed += 1
            print(f"{Fore.RED}❌ QUARTERLY RETAINER classification test FAILED{Style.RESET_ALL}")
        
        self.test_results.append({
            "test": "Quarterly Retainer Classification",
            "accuracy": accuracy,
            "passed": accuracy >= 75
        })
    
    async def test_hybrid_classification(self):
        """Test 4: HYBRID Classification - Mix of PROJECT and RETAINER"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"TEST 4: HYBRID CLASSIFICATION - MIX OF PROJECT & RETAINER")
        print(f"{'='*80}{Style.RESET_ALL}")
        
        # Mix of project and retainer deliverables
        hybrid_deliverables = [
            {"code": "website_redesign", "name": "Website Redesign", "expected_type": "PROJECT"},
            {"code": "brand_book", "name": "Brand Guidelines Development", "expected_type": "PROJECT"},
            {"code": "launch_video", "name": "Launch Video Production", "expected_type": "PROJECT"},
            {"code": "social_ongoing", "name": "Monthly Social Media Management", "expected_type": "RETAINER"},
            {"code": "campaign_quarterly", "name": "Quarterly Campaign Development", "expected_type": "RETAINER"},
            {"code": "content_weekly", "name": "Weekly Content Creation", "expected_type": "RETAINER"}
        ]
        
        response = await self.client.post(
            f"{API_BASE_URL}/api/ai/analyze_project_retainer",
            json={
                "rfp_text": HYBRID_RFP,
                "deliverables": hybrid_deliverables
            }
        )
        
        if response.status_code != 200:
            self.failed += 1
            print(f"{Fore.RED}❌ API call failed: {response.status_code}{Style.RESET_ALL}")
            return
        
        result = response.json()
        suggestions = result.get("suggestions", {})
        
        print(f"\n{Fore.WHITE}Classification Results for HYBRID RFP:{Style.RESET_ALL}")
        
        correct = 0
        total = len(hybrid_deliverables)
        project_correct = 0
        retainer_correct = 0
        project_total = sum(1 for d in hybrid_deliverables if d["expected_type"] == "PROJECT")
        retainer_total = sum(1 for d in hybrid_deliverables if d["expected_type"] == "RETAINER")
        
        for deliverable in hybrid_deliverables:
            code = deliverable["code"]
            name = deliverable["name"]
            expected = deliverable["expected_type"]
            
            suggestion = suggestions.get(code, {})
            predicted = suggestion.get("type", "UNKNOWN")
            confidence = suggestion.get("confidence", 0)
            
            is_correct = predicted == expected
            if is_correct:
                correct += 1
                if expected == "PROJECT":
                    project_correct += 1
                else:
                    retainer_correct += 1
                status_icon = "✅"
            else:
                status_icon = "❌"
            
            print(f"{status_icon} {name}: Expected={expected}, Predicted={predicted} (conf={confidence:.2f})")
        
        overall_accuracy = (correct / total) * 100
        project_accuracy = (project_correct / project_total * 100) if project_total > 0 else 0
        retainer_accuracy = (retainer_correct / retainer_total * 100) if retainer_total > 0 else 0
        
        print(f"\n{Fore.CYAN}Overall Accuracy: {overall_accuracy:.1f}%{Style.RESET_ALL}")
        print(f"  PROJECT Accuracy: {project_accuracy:.1f}% ({project_correct}/{project_total})")
        print(f"  RETAINER Accuracy: {retainer_accuracy:.1f}% ({retainer_correct}/{retainer_total})")
        
        if overall_accuracy >= 75:
            self.passed += 1
            print(f"{Fore.GREEN}✅ HYBRID classification test PASSED{Style.RESET_ALL}")
        else:
            self.failed += 1
            print(f"{Fore.RED}❌ HYBRID classification test FAILED{Style.RESET_ALL}")
        
        self.test_results.append({
            "test": "Hybrid Classification",
            "overall_accuracy": overall_accuracy,
            "project_accuracy": project_accuracy,
            "retainer_accuracy": retainer_accuracy,
            "passed": overall_accuracy >= 75
        })
    
    async def test_cadence_pricing_impact(self):
        """Test 5: Verify Cadence Impact on Pricing and Timeline"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"TEST 5: CADENCE IMPACT ON PRICING AND TIMELINE")
        print(f"{'='*80}{Style.RESET_ALL}")
        
        # Test retainer distribution for different cadences
        from ai_pricing_optimizer import calculate_retainer_distribution
        
        test_cases = [
            {"name": "Monthly", "months": 12, "monthly_hours": 100},
            {"name": "Quarterly", "months": 12, "monthly_hours": 300},  # 300 hours per quarter
            {"name": "Semi-Annual", "months": 12, "monthly_hours": 600},  # 600 hours per 6 months
            {"name": "Annual", "months": 12, "monthly_hours": 1200}  # 1200 hours annually
        ]
        
        print(f"\n{Fore.WHITE}Testing Hour Distribution for Different Cadences:{Style.RESET_ALL}")
        
        for case in test_cases:
            distribution = calculate_retainer_distribution(
                monthly_hours=case["monthly_hours"] / case["months"] if case["name"] != "Monthly" else case["monthly_hours"],
                duration_months=case["months"],
                ramp_up=True
            )
            
            total_hours = sum(distribution.values())
            print(f"\n{Fore.YELLOW}{case['name']} Cadence:{Style.RESET_ALL}")
            print(f"  Base Hours: {case['monthly_hours']}")
            print(f"  Total Distributed Hours: {total_hours:.1f}")
            print(f"  First 3 months (with ramp-up): {list(distribution.values())[:3]}")
            print(f"  Monthly Average: {total_hours/12:.1f} hours")
        
        # Test pricing calculations for different cadences
        print(f"\n{Fore.WHITE}Testing Pricing for Different Cadences:{Style.RESET_ALL}")
        
        hourly_rate = 150
        for case in test_cases:
            monthly_cost = (case["monthly_hours"] / 12) * hourly_rate if case["name"] != "Monthly" else case["monthly_hours"] * hourly_rate
            
            if case["name"] == "Monthly":
                print(f"\n{Fore.YELLOW}Monthly Retainer:{Style.RESET_ALL}")
                print(f"  Monthly Rate: ${monthly_cost:,.2f}")
                print(f"  Annual Value: ${monthly_cost * 12:,.2f}")
            elif case["name"] == "Quarterly":
                print(f"\n{Fore.YELLOW}Quarterly Retainer:{Style.RESET_ALL}")
                print(f"  Quarterly Rate: ${monthly_cost * 3:,.2f}")
                print(f"  Annual Value: ${monthly_cost * 12:,.2f}")
            elif case["name"] == "Semi-Annual":
                print(f"\n{Fore.YELLOW}Semi-Annual Retainer:{Style.RESET_ALL}")
                print(f"  Semi-Annual Rate: ${monthly_cost * 6:,.2f}")
                print(f"  Annual Value: ${monthly_cost * 12:,.2f}")
            else:  # Annual
                print(f"\n{Fore.YELLOW}Annual Retainer:{Style.RESET_ALL}")
                print(f"  Annual Rate: ${monthly_cost * 12:,.2f}")
        
        self.passed += 1
        print(f"\n{Fore.GREEN}✅ Cadence pricing impact test completed{Style.RESET_ALL}")
        
        self.test_results.append({
            "test": "Cadence Pricing Impact",
            "passed": True
        })
    
    async def test_mode_switching(self):
        """Test 6: Test Switching Between PROJECT and RETAINER Modes"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"TEST 6: MODE SWITCHING - PROJECT TO RETAINER")
        print(f"{'='*80}{Style.RESET_ALL}")
        
        # First, classify as PROJECT
        deliverable = {"code": "campaign_dev", "name": "Campaign Development"}
        
        print(f"\n{Fore.WHITE}Testing mode switch for: {deliverable['name']}{Style.RESET_ALL}")
        
        # Test with PROJECT context
        response1 = await self.client.post(
            f"{API_BASE_URL}/api/ai/analyze_project_retainer",
            json={
                "rfp_text": "We need a one-time campaign development for our product launch in Q2 2025.",
                "deliverables": [deliverable]
            }
        )
        
        result1 = response1.json()
        type1 = result1.get("suggestions", {}).get(deliverable["code"], {}).get("type")
        conf1 = result1.get("suggestions", {}).get(deliverable["code"], {}).get("confidence", 0)
        
        print(f"\nWith PROJECT context:")
        print(f"  Classification: {type1} (confidence: {conf1:.2f})")
        
        # Test with RETAINER context
        response2 = await self.client.post(
            f"{API_BASE_URL}/api/ai/analyze_project_retainer",
            json={
                "rfp_text": "We need ongoing monthly campaign development for the next 12 months with new campaigns every month.",
                "deliverables": [deliverable]
            }
        )
        
        result2 = response2.json()
        type2 = result2.get("suggestions", {}).get(deliverable["code"], {}).get("type")
        conf2 = result2.get("suggestions", {}).get(deliverable["code"], {}).get("confidence", 0)
        
        print(f"\nWith RETAINER context:")
        print(f"  Classification: {type2} (confidence: {conf2:.2f})")
        
        # Check if the system correctly switches modes based on context
        if type1 == "PROJECT" and type2 == "RETAINER":
            self.passed += 1
            print(f"\n{Fore.GREEN}✅ Mode switching test PASSED - System correctly adapts to context{Style.RESET_ALL}")
            success = True
        else:
            self.failed += 1
            print(f"\n{Fore.RED}❌ Mode switching test FAILED - System did not adapt to context{Style.RESET_ALL}")
            success = False
        
        self.test_results.append({
            "test": "Mode Switching",
            "project_classification": type1,
            "retainer_classification": type2,
            "passed": success
        })
    
    async def test_retainer_pricing_periods(self):
        """Test 7: Validate Retainer Pricing for Different Periods"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"TEST 7: RETAINER PRICING VALIDATION")
        print(f"{'='*80}{Style.RESET_ALL}")
        
        # Test the analyze_retainer endpoint
        test_deliverable = {
            "name": "Social Media Management",
            "total_hours": 1200  # Annual hours
        }
        
        response = await self.client.post(
            f"{API_BASE_URL}/api/pricing/analyze-retainer",
            json={
                "deliverable_name": test_deliverable["name"],
                "total_hours": test_deliverable["total_hours"],
                "duration_months": 12,
                "rfp_context": MONTHLY_RETAINER_RFP
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n{Fore.WHITE}Retainer Analysis Results:{Style.RESET_ALL}")
            print(f"  Recommendation: {result.get('recommendation', 'N/A')}")
            print(f"  Confidence: {result.get('confidence', 0):.2f}")
            print(f"  Monthly Hours: {result.get('monthly_hours', 0):.1f}")
            print(f"  Total Hours: {result.get('total_hours', 0)}")
            
            reasoning = result.get('reasoning', [])
            if reasoning:
                print(f"\n{Fore.YELLOW}Reasoning:{Style.RESET_ALL}")
                for reason in reasoning[:3]:
                    print(f"  • {reason}")
            
            # Calculate pricing for different periods
            hourly_rate = 150
            monthly_hours = result.get('monthly_hours', 0)
            
            print(f"\n{Fore.WHITE}Pricing by Period (at ${hourly_rate}/hour):{Style.RESET_ALL}")
            print(f"  Monthly: ${monthly_hours * hourly_rate:,.2f}")
            print(f"  Quarterly: ${monthly_hours * 3 * hourly_rate:,.2f}")
            print(f"  Semi-Annual: ${monthly_hours * 6 * hourly_rate:,.2f}")
            print(f"  Annual: ${monthly_hours * 12 * hourly_rate:,.2f}")
            
            self.passed += 1
            print(f"\n{Fore.GREEN}✅ Retainer pricing validation PASSED{Style.RESET_ALL}")
            passed = True
        else:
            self.failed += 1
            print(f"\n{Fore.RED}❌ Retainer pricing validation FAILED: {response.status_code}{Style.RESET_ALL}")
            passed = False
        
        self.test_results.append({
            "test": "Retainer Pricing Validation",
            "passed": passed
        })
    
    async def run_all_tests(self):
        """Run all comprehensive tests"""
        print(f"\n{Fore.MAGENTA}{'='*80}")
        print(f"PROJECT vs RETAINER CLASSIFICATION TEST SUITE")
        print(f"Testing all engagement types and cadence options")
        print(f"{'='*80}{Style.RESET_ALL}\n")
        
        try:
            await self.setup()
            
            # Run all tests
            await self.test_project_classification()
            await self.test_monthly_retainer_classification()
            await self.test_quarterly_retainer_classification()
            await self.test_hybrid_classification()
            await self.test_cadence_pricing_impact()
            await self.test_mode_switching()
            await self.test_retainer_pricing_periods()
            
            # Print summary
            print(f"\n{Fore.MAGENTA}{'='*80}")
            print(f"TEST SUMMARY")
            print(f"{'='*80}{Style.RESET_ALL}\n")
            
            total_tests = self.passed + self.failed
            pass_rate = (self.passed / total_tests * 100) if total_tests > 0 else 0
            
            print(f"{Fore.GREEN}Passed: {self.passed}{Style.RESET_ALL}")
            print(f"{Fore.RED}Failed: {self.failed}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Pass Rate: {pass_rate:.1f}%{Style.RESET_ALL}")
            
            print(f"\n{Fore.YELLOW}Detailed Results:{Style.RESET_ALL}")
            for i, result in enumerate(self.test_results, 1):
                test_name = result.get("test", "Unknown")
                passed = result.get("passed", False)
                icon = "✅" if passed else "❌"
                print(f"{i}. {icon} {test_name}")
                
                # Print accuracy if available
                if "accuracy" in result:
                    print(f"   Accuracy: {result['accuracy']:.1f}%")
                elif "overall_accuracy" in result:
                    print(f"   Overall: {result['overall_accuracy']:.1f}%")
                    print(f"   PROJECT: {result.get('project_accuracy', 0):.1f}%")
                    print(f"   RETAINER: {result.get('retainer_accuracy', 0):.1f}%")
            
            if pass_rate >= 70:
                print(f"\n{Fore.GREEN}🎉 TEST SUITE PASSED!{Style.RESET_ALL}")
                return True
            else:
                print(f"\n{Fore.RED}⚠️ TEST SUITE NEEDS IMPROVEMENT{Style.RESET_ALL}")
                return False
            
        except Exception as e:
            print(f"\n{Fore.RED}❌ Fatal error during testing: {e}{Style.RESET_ALL}")
            return False
        finally:
            await self.teardown()

# Main execution
async def main():
    """Main test runner"""
    tester = TestProjectRetainerClassification()
    success = await tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    # Run the test suite
    asyncio.run(main())