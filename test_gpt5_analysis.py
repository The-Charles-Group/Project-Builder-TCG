#!/usr/bin/env python3
"""
Comprehensive Test Suite for GPT-5 RFP Analysis
Tests document processing, deliverable extraction, AI intelligence, and error handling
"""

import os
import sys
import json
import time
import psutil
import asyncio
import httpx
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import traceback
import tempfile
from pathlib import Path

# Test configuration
API_BASE_URL = "http://localhost:5000"
TIMEOUT = 300  # 5 minutes timeout for large documents
TEST_RFP_DIR = "test_rfps"

# Expected thresholds
MIN_DELIVERABLES_GPT5 = 15  # Minimum for GPT-5 intelligent analysis
MIN_COMPONENTS_PER_DELIVERABLE = 2
MIN_CONFIDENCE_SCORE = 0.7

class TestResult:
    """Track test results with metrics"""
    def __init__(self, name: str):
        self.name = name
        self.status = "pending"
        self.start_time = None
        self.end_time = None
        self.duration = 0
        self.memory_before = 0
        self.memory_after = 0
        self.result = {}
        self.error = None
        self.warnings = []
        
    def start(self):
        self.start_time = time.time()
        self.memory_before = psutil.Process().memory_info().rss / 1024 / 1024
        print(f"\n🔄 Running: {self.name}")
        
    def complete(self, status: str, result: Dict = None, error: str = None):
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.memory_after = psutil.Process().memory_info().rss / 1024 / 1024
        self.status = status
        self.result = result or {}
        self.error = error
        
        emoji = "✅" if status == "passed" else "❌" if status == "failed" else "⚠️"
        print(f"{emoji} {self.name}: {status}")
        print(f"   Duration: {self.duration:.2f}s | Memory: {self.memory_after - self.memory_before:.1f}MB")
        if error:
            print(f"   Error: {error}")

class GPT5AnalysisTester:
    """Comprehensive GPT-5 RFP Analysis Testing"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        self.test_results = []
        self.summary = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "total_duration": 0,
            "total_memory": 0
        }
        
    async def test_text_rfp_analysis(self) -> TestResult:
        """Test basic text RFP analysis"""
        test = TestResult("Text RFP Analysis")
        test.start()
        
        try:
            # Test with different complexity RFPs
            test_files = [
                "minimal_rfp.txt",
                "complex_rfp.txt",
                "enterprise_tech_rfp.txt",
                "luxury_fashion_campaign_rfp.txt"
            ]
            
            for filename in test_files:
                filepath = Path(TEST_RFP_DIR) / filename
                if not filepath.exists():
                    test.warnings.append(f"Test file {filename} not found")
                    continue
                    
                with open(filepath, 'r') as f:
                    content = f.read()
                    
                response = await self.client.post(
                    f"{API_BASE_URL}/api/suggest_by_text",
                    json={"text": content}
                )
                
                if response.status_code != 200:
                    raise Exception(f"API returned {response.status_code}")
                    
                data = response.json()
                deliverables = data.get("deliverables", [])
                
                # Validate results
                if len(deliverables) < MIN_DELIVERABLES_GPT5:
                    test.warnings.append(f"{filename}: Only {len(deliverables)} deliverables (expected {MIN_DELIVERABLES_GPT5}+)")
                    
                # Check for components
                components_count = sum(len(d.get("components", [])) for d in deliverables)
                if components_count < len(deliverables) * MIN_COMPONENTS_PER_DELIVERABLE:
                    test.warnings.append(f"{filename}: Insufficient components ({components_count})")
                    
                print(f"   ✓ {filename}: {len(deliverables)} deliverables, {components_count} components")
                
            test.complete("passed" if not test.warnings else "warning", {"warnings": test.warnings})
            
        except Exception as e:
            test.complete("failed", error=str(e))
            
        return test
        
    async def test_file_upload_analysis(self) -> TestResult:
        """Test file upload analysis (PDF, DOCX, TXT)"""
        test = TestResult("File Upload Analysis")
        test.start()
        
        try:
            # Create test files in different formats
            test_content = """
            DIGITAL TRANSFORMATION PROJECT RFP
            
            We need a comprehensive digital strategy including:
            1. Website redesign with e-commerce
            2. Mobile app development
            3. Social media management
            4. Email marketing automation
            5. Analytics and reporting dashboards
            
            Timeline: 6 months
            Budget: $500,000
            """
            
            # Test text file upload
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(test_content)
                txt_file = f.name
                
            with open(txt_file, 'rb') as f:
                files = {'file': ('test_rfp.txt', f, 'text/plain')}
                response = await self.client.post(
                    f"{API_BASE_URL}/api/suggest_by_file",
                    files=files
                )
                
            os.unlink(txt_file)
            
            if response.status_code != 200:
                raise Exception(f"File upload failed: {response.status_code}")
                
            data = response.json()
            deliverables = data.get("deliverables", [])
            
            if len(deliverables) < 5:
                test.warnings.append(f"File upload produced only {len(deliverables)} deliverables")
                
            test.complete("passed", {"deliverables_count": len(deliverables)})
            
        except Exception as e:
            test.complete("failed", error=str(e))
            
        return test
        
    async def test_industry_specific_analysis(self) -> TestResult:
        """Test industry-specific RFP analysis"""
        test = TestResult("Industry-Specific Analysis")
        test.start()
        
        try:
            industries = {
                "luxury_fashion": "Paris Fashion Week runway show production with influencer partnerships",
                "technology": "Cloud migration and microservices architecture implementation",
                "healthcare": "Patient portal development with telehealth integration",
                "real_estate": "Property launch campaign with virtual tours and broker events",
                "beauty": "Product launch with clinical studies and influencer seeding",
                "retail": "Omnichannel campaign with loyalty program integration"
            }
            
            results = {}
            for industry, brief in industries.items():
                response = await self.client.post(
                    f"{API_BASE_URL}/api/suggest_by_text",
                    json={"text": brief}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    deliverables = data.get("deliverables", [])
                    
                    # Check if industry-relevant deliverables are present
                    deliverable_names = [d.get("name", "").lower() for d in deliverables]
                    relevant_count = sum(1 for name in deliverable_names 
                                       if any(keyword in name for keyword in industry.split("_")))
                    
                    results[industry] = {
                        "total": len(deliverables),
                        "relevant": relevant_count,
                        "percentage": (relevant_count / len(deliverables) * 100) if deliverables else 0
                    }
                    
                    print(f"   ✓ {industry}: {len(deliverables)} deliverables, {relevant_count} industry-specific")
                    
            test.complete("passed", results)
            
        except Exception as e:
            test.complete("failed", error=str(e))
            
        return test
        
    async def test_ai_intelligence_features(self) -> TestResult:
        """Test GPT-5 intelligence: understanding context, inferring needs"""
        test = TestResult("AI Intelligence Features")
        test.start()
        
        try:
            # Test vague requirements interpretation
            vague_brief = """
            We're launching something big next quarter. Need help with the digital stuff 
            and making sure people know about it. Also need to track if it's working.
            """
            
            response = await self.client.post(
                f"{API_BASE_URL}/api/suggest_by_text",
                json={"text": vague_brief}
            )
            
            if response.status_code != 200:
                raise Exception("Failed to process vague brief")
                
            data = response.json()
            deliverables = data.get("deliverables", [])
            
            # GPT-5 should infer: launch campaign, digital marketing, analytics
            expected_categories = ["strategy", "digital", "analytics", "creative"]
            found_categories = set()
            
            for d in deliverables:
                category = d.get("category", "").lower()
                for expected in expected_categories:
                    if expected in category:
                        found_categories.add(expected)
                        
            intelligence_score = len(found_categories) / len(expected_categories)
            
            if intelligence_score < 0.5:
                test.warnings.append(f"Low intelligence score: {intelligence_score:.2f}")
                
            print(f"   Intelligence score: {intelligence_score:.2f} ({len(found_categories)}/{len(expected_categories)} categories inferred)")
            
            test.complete("passed" if intelligence_score >= 0.5 else "warning", 
                         {"intelligence_score": intelligence_score})
            
        except Exception as e:
            test.complete("failed", error=str(e))
            
        return test
        
    async def test_error_handling_and_fallback(self) -> TestResult:
        """Test error handling and fallback mechanisms"""
        test = TestResult("Error Handling & Fallback")
        test.start()
        
        try:
            test_cases = []
            
            # Test 1: Empty input
            response = await self.client.post(
                f"{API_BASE_URL}/api/suggest_by_text",
                json={"text": ""}
            )
            test_cases.append(("empty_input", response.status_code in [200, 400]))
            
            # Test 2: Extremely long input
            long_text = "Digital transformation project. " * 1000
            response = await self.client.post(
                f"{API_BASE_URL}/api/suggest_by_text",
                json={"text": long_text},
                timeout=60
            )
            test_cases.append(("long_input", response.status_code == 200))
            
            # Test 3: Special characters
            special_text = "Project with special chars: @#$%^&*() and émojis 🚀"
            response = await self.client.post(
                f"{API_BASE_URL}/api/suggest_by_text",
                json={"text": special_text}
            )
            test_cases.append(("special_chars", response.status_code == 200))
            
            # Test 4: Non-English content
            non_english = "Projet de transformation numérique pour notre entreprise"
            response = await self.client.post(
                f"{API_BASE_URL}/api/suggest_by_text",
                json={"text": non_english}
            )
            test_cases.append(("non_english", response.status_code == 200))
            
            passed = sum(1 for _, result in test_cases if result)
            total = len(test_cases)
            
            for name, result in test_cases:
                emoji = "✓" if result else "✗"
                print(f"   {emoji} {name}: {'passed' if result else 'failed'}")
                
            test.complete("passed" if passed == total else "warning", 
                         {"passed": passed, "total": total})
            
        except Exception as e:
            test.complete("failed", error=str(e))
            
        return test
        
    async def test_performance_and_concurrency(self) -> TestResult:
        """Test performance under load and concurrent requests"""
        test = TestResult("Performance & Concurrency")
        test.start()
        
        try:
            # Prepare test data
            test_brief = "Need a complete digital marketing campaign with website, social media, and analytics"
            
            # Test single request timing
            start = time.time()
            response = await self.client.post(
                f"{API_BASE_URL}/api/suggest_by_text",
                json={"text": test_brief}
            )
            single_duration = time.time() - start
            
            # Test concurrent requests
            concurrent_count = 5
            start = time.time()
            tasks = [
                self.client.post(
                    f"{API_BASE_URL}/api/suggest_by_text",
                    json={"text": test_brief}
                )
                for _ in range(concurrent_count)
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            concurrent_duration = time.time() - start
            
            # Count successful responses
            successful = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 200)
            
            # Performance metrics
            avg_time_concurrent = concurrent_duration / concurrent_count
            speedup = single_duration / avg_time_concurrent if avg_time_concurrent > 0 else 1
            
            print(f"   Single request: {single_duration:.2f}s")
            print(f"   {concurrent_count} concurrent: {concurrent_duration:.2f}s total, {avg_time_concurrent:.2f}s avg")
            print(f"   Speedup factor: {speedup:.2f}x")
            print(f"   Success rate: {successful}/{concurrent_count}")
            
            test.complete(
                "passed" if successful == concurrent_count else "warning",
                {
                    "single_duration": single_duration,
                    "concurrent_duration": concurrent_duration,
                    "speedup": speedup,
                    "success_rate": successful / concurrent_count
                }
            )
            
        except Exception as e:
            test.complete("failed", error=str(e))
            
        return test
        
    async def run_all_tests(self):
        """Run all GPT-5 analysis tests"""
        print("\n" + "="*70)
        print("GPT-5 RFP ANALYSIS TEST SUITE")
        print("="*70)
        
        tests = [
            self.test_text_rfp_analysis(),
            self.test_file_upload_analysis(),
            self.test_industry_specific_analysis(),
            self.test_ai_intelligence_features(),
            self.test_error_handling_and_fallback(),
            self.test_performance_and_concurrency()
        ]
        
        for test_coro in tests:
            test_result = await test_coro
            self.test_results.append(test_result)
            self.summary["total"] += 1
            
            if test_result.status == "passed":
                self.summary["passed"] += 1
            elif test_result.status == "failed":
                self.summary["failed"] += 1
            else:
                self.summary["warnings"] += 1
                
            self.summary["total_duration"] += test_result.duration
            self.summary["total_memory"] += (test_result.memory_after - test_result.memory_before)
            
        await self.client.aclose()
        
    def print_summary(self):
        """Print test summary report"""
        print("\n" + "="*70)
        print("TEST SUMMARY - GPT-5 RFP ANALYSIS")
        print("="*70)
        
        print(f"Total Tests: {self.summary['total']}")
        print(f"Passed: {self.summary['passed']} ✅")
        print(f"Failed: {self.summary['failed']} ❌")
        print(f"Warnings: {self.summary['warnings']} ⚠️")
        print(f"Success Rate: {(self.summary['passed'] / self.summary['total'] * 100):.1f}%")
        print(f"Total Duration: {self.summary['total_duration']:.2f}s")
        print(f"Memory Usage: {self.summary['total_memory']:.1f}MB")
        
        if self.summary["failed"] > 0:
            print("\n⚠️ FAILED TESTS:")
            for test in self.test_results:
                if test.status == "failed":
                    print(f"  - {test.name}: {test.error}")
                    
        if self.summary["warnings"] > 0:
            print("\n⚠️ TESTS WITH WARNINGS:")
            for test in self.test_results:
                if test.status == "warning":
                    print(f"  - {test.name}")
                    if test.warnings:
                        for warning in test.warnings:
                            print(f"    • {warning}")
                            
        return self.summary

async def main():
    """Main test runner"""
    tester = GPT5AnalysisTester()
    
    try:
        # Check if server is running
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/api/load")
            if response.status_code != 200:
                print("❌ Server not responding. Please start the FastAPI server first.")
                return
                
        await tester.run_all_tests()
        summary = tester.print_summary()
        
        # Return exit code based on results
        if summary["failed"] > 0:
            sys.exit(1)
        elif summary["warnings"] > 0:
            sys.exit(0)
        else:
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())