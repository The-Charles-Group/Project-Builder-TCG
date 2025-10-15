#!/usr/bin/env python3
"""
Comprehensive GPT-5 RFP Analysis Test Suite
Tests the /api/ai/analyze endpoint with various scenarios
"""

import os
import json
import time
import asyncio
import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import statistics

# Test configuration
API_BASE_URL = "http://localhost:5000"
TIMEOUT = 300  # 5 minutes timeout for complex analyses

class GPT5AnalysisTester:
    def __init__(self):
        self.results = {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "test_details": []
        }
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        
    async def analyze_rfp(self, rfp_text: str, name: str, mode: str = "deep", tier: str = "thinking") -> Dict[str, Any]:
        """Submit RFP for analysis and wait for results"""
        start_time = time.time()
        
        try:
            # Start analysis job
            print(f"\n{'='*80}")
            print(f"Testing: {name}")
            print(f"Mode: {mode}, Tier: {tier}")
            print(f"RFP Length: {len(rfp_text)} characters")
            print(f"{'='*80}")
            
            response = await self.client.post(
                f"{API_BASE_URL}/api/ai/analyze",
                json={
                    "request_text": rfp_text,
                    "mode": mode,
                    "tier": tier,
                    "strictness": "balanced"
                }
            )
            
            if response.status_code != 200:
                print(f"❌ Failed to start analysis: {response.status_code}")
                print(f"Response: {response.text}")
                return {"error": f"Failed to start: {response.status_code}"}
            
            job_data = response.json()
            job_id = job_data.get("job_id")
            print(f"✅ Analysis started - Job ID: {job_id}")
            
            # Poll for results
            max_polls = 60  # Poll for up to 5 minutes
            poll_interval = 5  # Check every 5 seconds
            
            for poll in range(max_polls):
                await asyncio.sleep(poll_interval)
                
                status_response = await self.client.get(
                    f"{API_BASE_URL}/api/ai/status/{job_id}"
                )
                
                if status_response.status_code != 200:
                    print(f"❌ Failed to get status: {status_response.status_code}")
                    continue
                
                status_data = status_response.json()
                status = status_data.get("status")
                progress = status_data.get("progress", 0)
                stage = status_data.get("current_stage", "")
                elapsed = status_data.get("elapsed_seconds", 0)
                
                print(f"  [{poll+1}/{max_polls}] Status: {status} | Progress: {progress}% | Stage: {stage} | Elapsed: {elapsed:.1f}s")
                
                if status == "completed":
                    end_time = time.time()
                    result = status_data.get("result", {})
                    
                    # Extract key metrics
                    plan = result.get("plan", {})
                    suggestions = plan.get("suggestions_by_department", {})
                    diagnostics = result.get("diagnostics", {})
                    
                    # Count deliverables
                    total_deliverables = 0
                    departments_with_deliverables = []
                    confidence_scores = []
                    deliverable_codes = set()
                    
                    for dept, items in suggestions.items():
                        dept_deliverables = 0
                        for item in items:
                            if item.get("level") == "deliverable":
                                dept_deliverables += 1
                                total_deliverables += 1
                                
                                # Collect confidence scores
                                confidence = item.get("confidence", 0)
                                if confidence > 0:
                                    confidence_scores.append(confidence)
                                
                                # Collect deliverable codes
                                code = item.get("code", "")
                                if code:
                                    deliverable_codes.add(code)
                        
                        if dept_deliverables > 0:
                            departments_with_deliverables.append(f"{dept}({dept_deliverables})")
                    
                    # Calculate statistics
                    avg_confidence = statistics.mean(confidence_scores) if confidence_scores else 0
                    min_confidence = min(confidence_scores) if confidence_scores else 0
                    max_confidence = max(confidence_scores) if confidence_scores else 0
                    
                    # Check for GPT-5 usage vs fallback
                    using_gpt5 = diagnostics.get("llm_scores_available", False)
                    rescue_triggered = diagnostics.get("rescue_triggered", False)
                    
                    print(f"\n{'='*60}")
                    print(f"✅ Analysis Complete for {name}")
                    print(f"{'='*60}")
                    print(f"Total Time: {end_time - start_time:.2f} seconds")
                    print(f"Deliverables Found: {total_deliverables}")
                    print(f"Departments: {', '.join(departments_with_deliverables)}")
                    print(f"Unique Deliverable Codes: {len(deliverable_codes)}")
                    print(f"Confidence Scores: Avg={avg_confidence:.2f}, Min={min_confidence:.2f}, Max={max_confidence:.2f}")
                    print(f"Using GPT-5: {'Yes' if using_gpt5 else 'No (Fallback)'}")
                    print(f"Rescue Function: {'Triggered' if rescue_triggered else 'Not Triggered'}")
                    print(f"Components Selected: {diagnostics.get('components_in_plan', 0)}")
                    print(f"Tasks Selected: {diagnostics.get('tasks_ai_selected', 0)}")
                    
                    # Store detailed results
                    return {
                        "success": True,
                        "name": name,
                        "mode": mode,
                        "tier": tier,
                        "time_seconds": end_time - start_time,
                        "total_deliverables": total_deliverables,
                        "departments": departments_with_deliverables,
                        "unique_codes": len(deliverable_codes),
                        "deliverable_codes": list(deliverable_codes),
                        "confidence_avg": avg_confidence,
                        "confidence_min": min_confidence,
                        "confidence_max": max_confidence,
                        "confidence_scores": confidence_scores[:10],  # Sample of scores
                        "using_gpt5": using_gpt5,
                        "rescue_triggered": rescue_triggered,
                        "diagnostics": diagnostics,
                        "raw_result": result
                    }
                
                elif status == "failed":
                    error = status_data.get("error", "Unknown error")
                    print(f"\n❌ Analysis Failed: {error}")
                    return {
                        "success": False,
                        "name": name,
                        "error": error,
                        "time_seconds": time.time() - start_time
                    }
            
            # Timeout
            print(f"\n⏱️ Analysis Timed Out after {max_polls * poll_interval} seconds")
            return {
                "success": False,
                "name": name,
                "error": "Timeout",
                "time_seconds": time.time() - start_time
            }
            
        except Exception as e:
            print(f"\n💥 Exception during analysis: {str(e)}")
            return {
                "success": False,
                "name": name,
                "error": str(e),
                "time_seconds": time.time() - start_time
            }
    
    async def run_all_tests(self):
        """Run comprehensive test suite"""
        print("\n" + "="*80)
        print("GPT-5 RFP ANALYSIS COMPREHENSIVE TEST SUITE")
        print("="*80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Load test RFPs
        test_rfps = []
        rfp_files = [
            ("Fashion Industry", "test_rfps/fashion_rfp.txt"),
            ("Beauty Industry", "test_rfps/beauty_rfp.txt"),
            ("Tech/SaaS Industry", "test_rfps/tech_rfp.txt"),
            ("Real Estate Industry", "test_rfps/real_estate_rfp.txt")
        ]
        
        for name, filepath in rfp_files:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    content = f.read()
                    test_rfps.append((name, content))
                    print(f"✅ Loaded: {name} ({len(content)} chars)")
            else:
                print(f"❌ Missing: {filepath}")
        
        # Test scenarios
        test_scenarios = []
        
        # Test 1: Deep mode with GPT-5 thinking tier (should produce 100+ deliverables)
        for name, rfp_text in test_rfps:
            test_scenarios.append({
                "name": f"{name} - Deep/Thinking",
                "rfp_text": rfp_text,
                "mode": "deep",
                "tier": "thinking",
                "expected_deliverables": 100
            })
        
        # Test 2: Fast mode (should use TF-IDF only, no GPT-5)
        test_scenarios.append({
            "name": "Fashion - Fast Mode",
            "rfp_text": test_rfps[0][1] if test_rfps else "",
            "mode": "fast",
            "tier": "mini",
            "expected_deliverables": 50
        })
        
        # Test 3: Pro tier for highest quality
        test_scenarios.append({
            "name": "Tech - Pro Tier",
            "rfp_text": test_rfps[2][1] if len(test_rfps) > 2 else "",
            "mode": "deep",
            "tier": "pro",
            "expected_deliverables": 100
        })
        
        # Test 4: Short RFP (should still work)
        short_rfp = """
        We need a comprehensive digital marketing campaign for our new product launch.
        Services needed: Social media marketing, content creation, paid advertising,
        influencer partnerships, email marketing, and analytics reporting.
        Budget: $500K, Timeline: 6 months.
        """
        test_scenarios.append({
            "name": "Short RFP Test",
            "rfp_text": short_rfp,
            "mode": "deep",
            "tier": "thinking",
            "expected_deliverables": 20
        })
        
        # Run all test scenarios
        all_results = []
        for scenario in test_scenarios:
            if not scenario["rfp_text"]:
                print(f"\n⚠️ Skipping {scenario['name']} - No RFP text")
                continue
            
            result = await self.analyze_rfp(
                rfp_text=scenario["rfp_text"],
                name=scenario["name"],
                mode=scenario["mode"],
                tier=scenario["tier"]
            )
            
            # Evaluate result
            if result.get("success"):
                actual_deliverables = result.get("total_deliverables", 0)
                expected = scenario["expected_deliverables"]
                
                # Check pass/fail criteria
                passed = True
                issues = []
                
                # Check deliverable count
                if actual_deliverables < expected * 0.5:
                    passed = False
                    issues.append(f"Too few deliverables: {actual_deliverables} < {expected * 0.5}")
                
                # Check confidence scores
                avg_confidence = result.get("confidence_avg", 0)
                if avg_confidence < 0.6 or avg_confidence > 0.95:
                    issues.append(f"Unrealistic confidence avg: {avg_confidence:.2f}")
                
                # Check for GPT-5 usage (except in fast mode)
                if scenario["mode"] == "deep" and not result.get("using_gpt5"):
                    passed = False
                    issues.append("Not using GPT-5 (fell back to embeddings)")
                
                # Check unique codes
                if result.get("unique_codes", 0) < 10:
                    issues.append(f"Too few unique codes: {result.get('unique_codes', 0)}")
                
                result["passed"] = passed
                result["issues"] = issues
                result["expected_deliverables"] = expected
                
                if passed:
                    print(f"✅ TEST PASSED")
                    self.results["tests_passed"] += 1
                else:
                    print(f"❌ TEST FAILED: {', '.join(issues)}")
                    self.results["tests_failed"] += 1
            else:
                result["passed"] = False
                result["issues"] = [result.get("error", "Unknown error")]
                self.results["tests_failed"] += 1
                print(f"❌ TEST FAILED: {result.get('error')}")
            
            self.results["tests_run"] += 1
            all_results.append(result)
            self.results["test_details"] = all_results
            
            # Small delay between tests
            await asyncio.sleep(2)
        
        # Generate final report
        await self.generate_report()
    
    async def generate_report(self):
        """Generate comprehensive test report"""
        report = []
        report.append("\n" + "="*80)
        report.append("GPT-5 RFP ANALYSIS TEST REPORT")
        report.append("="*80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"\nSUMMARY:")
        report.append(f"  Total Tests: {self.results['tests_run']}")
        report.append(f"  Passed: {self.results['tests_passed']}")
        report.append(f"  Failed: {self.results['tests_failed']}")
        report.append(f"  Success Rate: {(self.results['tests_passed']/max(1, self.results['tests_run'])*100):.1f}%")
        
        report.append(f"\n{'='*80}")
        report.append("DETAILED RESULTS:")
        report.append("="*80)
        
        for i, test in enumerate(self.results["test_details"], 1):
            report.append(f"\n{i}. {test.get('name', 'Unknown Test')}")
            report.append("-" * 60)
            
            if test.get("success"):
                report.append(f"  Status: {'PASSED' if test.get('passed') else 'FAILED'}")
                report.append(f"  Time: {test.get('time_seconds', 0):.2f} seconds")
                report.append(f"  Mode: {test.get('mode')} | Tier: {test.get('tier')}")
                report.append(f"  Deliverables: {test.get('total_deliverables')} (expected: {test.get('expected_deliverables', 'N/A')})")
                report.append(f"  Departments: {len(test.get('departments', []))}")
                report.append(f"  Unique Codes: {test.get('unique_codes')}")
                report.append(f"  Confidence: Avg={test.get('confidence_avg', 0):.2f}, Min={test.get('confidence_min', 0):.2f}, Max={test.get('confidence_max', 0):.2f}")
                report.append(f"  Using GPT-5: {'Yes' if test.get('using_gpt5') else 'No'}")
                report.append(f"  Rescue Triggered: {'Yes' if test.get('rescue_triggered') else 'No'}")
                
                if test.get("issues"):
                    report.append(f"  Issues: {', '.join(test['issues'])}")
                
                # Sample of confidence scores
                if test.get("confidence_scores"):
                    scores_sample = test["confidence_scores"][:5]
                    report.append(f"  Sample Scores: {[f'{s:.2f}' for s in scores_sample]}")
                
                # Sample of deliverable codes
                if test.get("deliverable_codes"):
                    codes_sample = list(test["deliverable_codes"])[:10]
                    report.append(f"  Sample Codes: {codes_sample}")
            else:
                report.append(f"  Status: FAILED")
                report.append(f"  Error: {test.get('error', 'Unknown')}")
                report.append(f"  Time: {test.get('time_seconds', 0):.2f} seconds")
        
        # Analysis insights
        report.append(f"\n{'='*80}")
        report.append("INSIGHTS & RECOMMENDATIONS:")
        report.append("="*80)
        
        # Check for systemic issues
        all_using_gpt5 = all(t.get("using_gpt5", False) for t in self.results["test_details"] if t.get("success") and t.get("mode") == "deep")
        avg_deliverables = statistics.mean([t.get("total_deliverables", 0) for t in self.results["test_details"] if t.get("success")])
        avg_time = statistics.mean([t.get("time_seconds", 0) for t in self.results["test_details"] if t.get("success")])
        
        if not all_using_gpt5:
            report.append("⚠️ WARNING: Some deep mode tests fell back to embeddings instead of using GPT-5")
            report.append("  Recommendation: Check GPT-5 API availability and configuration")
        
        if avg_deliverables < 50:
            report.append("⚠️ WARNING: Average deliverables count is low")
            report.append(f"  Average: {avg_deliverables:.0f} deliverables")
            report.append("  Recommendation: Increase AI_MIN_DELIVERABLES or adjust prompt")
        
        if avg_time > 60:
            report.append("⚠️ WARNING: Average processing time is high")
            report.append(f"  Average: {avg_time:.1f} seconds")
            report.append("  Recommendation: Consider optimizing batch sizes or using faster tier")
        
        # Performance metrics
        report.append(f"\nPERFORMANCE METRICS:")
        report.append(f"  Average Deliverables: {avg_deliverables:.0f}")
        report.append(f"  Average Time: {avg_time:.1f} seconds")
        report.append(f"  Deliverables/Second: {avg_deliverables/max(1, avg_time):.1f}")
        
        # Write report to file
        report_text = "\n".join(report)
        print(report_text)
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"gpt5_test_report_{timestamp}.txt"
        
        with open(report_file, 'w') as f:
            f.write(report_text)
        
        print(f"\n📄 Report saved to: {report_file}")
        
        # Save detailed JSON results
        json_file = f"gpt5_test_results_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"📊 Detailed results saved to: {json_file}")
    
    async def close(self):
        """Clean up resources"""
        await self.client.aclose()

async def main():
    """Main test runner"""
    tester = GPT5AnalysisTester()
    
    try:
        # Check if API is available
        health_response = await tester.client.get(f"{API_BASE_URL}/api/ai/health")
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"✅ API Health Check Passed")
            print(f"  Database: {health_data.get('database_source', 'Unknown')}")
            print(f"  Deliverables: {health_data.get('deliverables', 0)}")
        else:
            print(f"❌ API Health Check Failed: {health_response.status_code}")
        
        # Run comprehensive tests
        await tester.run_all_tests()
        
    except Exception as e:
        print(f"\n💥 Critical Error: {str(e)}")
    finally:
        await tester.close()

if __name__ == "__main__":
    asyncio.run(main())