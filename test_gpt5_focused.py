#!/usr/bin/env python3
"""
Focused GPT-5 RFP Analysis Test
Tests key requirements for GPT-5 integration
"""

import os
import json
import time
import httpx
import asyncio
from typing import Dict, List, Any
from datetime import datetime

API_BASE_URL = "http://localhost:5000"

class FocusedGPT5Tester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=300)
        self.test_results = []
        
    async def test_rfp_analysis(self, rfp_text: str, test_name: str, expected_deliverables: int = 100) -> Dict[str, Any]:
        """Test a single RFP and collect detailed metrics"""
        print(f"\n{'='*60}")
        print(f"Testing: {test_name}")
        print(f"{'='*60}")
        print(f"RFP Length: {len(rfp_text)} characters")
        print(f"Expected Deliverables: {expected_deliverables}+")
        
        start_time = time.time()
        
        try:
            # Start analysis
            response = await self.client.post(
                f"{API_BASE_URL}/api/ai/analyze",
                json={
                    "request_text": rfp_text,
                    "mode": "deep",
                    "tier": "thinking",
                    "strictness": "balanced"
                }
            )
            
            if response.status_code != 200:
                return {"success": False, "error": f"Failed to start: {response.status_code}"}
            
            job_data = response.json()
            job_id = job_data["job_id"]
            print(f"✅ Job started: {job_id}")
            
            # Poll for results
            for attempt in range(60):  # Max 5 minutes
                await asyncio.sleep(5)
                
                status_response = await self.client.get(f"{API_BASE_URL}/api/ai/status/{job_id}")
                if status_response.status_code != 200:
                    continue
                
                status = status_response.json()
                current_status = status.get("status")
                progress = status.get("progress", 0)
                stage = status.get("current_stage", "")
                
                print(f"  Status: {current_status} | Progress: {progress}% | {stage}")
                
                if current_status == "completed":
                    elapsed = time.time() - start_time
                    result = status.get("result", {})
                    return self.analyze_results(result, test_name, elapsed, expected_deliverables)
                
                elif current_status == "failed":
                    return {"success": False, "error": status.get("error", "Unknown error")}
            
            return {"success": False, "error": "Timeout"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def analyze_results(self, result: Dict[str, Any], test_name: str, elapsed: float, expected: int) -> Dict[str, Any]:
        """Analyze and validate results from GPT-5"""
        plan = result.get("plan", {})
        diagnostics = result.get("diagnostics", {})
        suggestions = plan.get("suggestions_by_department", {})
        
        # Count deliverables and analyze quality
        deliverables = []
        components = []
        tasks = []
        departments_found = set()
        confidence_scores = []
        deliverable_codes = set()
        
        for dept, items in suggestions.items():
            departments_found.add(dept)
            for item in items:
                level = item.get("level")
                if level == "deliverable":
                    deliverables.append(item)
                    conf = item.get("confidence", 0)
                    if conf > 0:
                        confidence_scores.append(conf)
                    code = item.get("code", "")
                    if code:
                        deliverable_codes.add(code)
                elif level == "component":
                    components.append(item)
                elif level == "task":
                    tasks.append(item)
        
        # Calculate metrics
        total_deliverables = len(deliverables)
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        min_confidence = min(confidence_scores) if confidence_scores else 0
        max_confidence = max(confidence_scores) if confidence_scores else 0
        using_gpt5 = diagnostics.get("llm_scores_available", False)
        
        # Validation checks
        issues = []
        passed = True
        
        # Check 1: Deliverable count
        if total_deliverables < expected * 0.8:
            issues.append(f"Too few deliverables: {total_deliverables} < {expected * 0.8:.0f}")
            passed = False
        
        # Check 2: GPT-5 usage
        if not using_gpt5:
            issues.append("Not using GPT-5 (fell back to embeddings)")
            passed = False
        
        # Check 3: Confidence scores range
        if avg_confidence < 0.6 or avg_confidence > 0.95:
            issues.append(f"Unrealistic avg confidence: {avg_confidence:.2f}")
        
        if min_confidence < 0.5 or max_confidence > 0.98:
            issues.append(f"Confidence range issue: {min_confidence:.2f}-{max_confidence:.2f}")
        
        # Check 4: Department coverage
        expected_depts = {"Creative", "Strategy", "Paid Media", "Content", "Technology"}
        missing_depts = expected_depts - departments_found
        if missing_depts:
            issues.append(f"Missing departments: {missing_depts}")
        
        # Check 5: Evidence quality (sample check)
        evidence_count = 0
        for item in deliverables[:10]:  # Check first 10
            if item.get("why") and len(item.get("why", "")) > 20:
                evidence_count += 1
        
        if evidence_count < 8:
            issues.append(f"Insufficient evidence/justifications: {evidence_count}/10")
        
        # Print results
        print(f"\n📊 Results for {test_name}:")
        print(f"  ⏱️ Time: {elapsed:.1f} seconds")
        print(f"  📦 Deliverables: {total_deliverables} (expected {expected}+)")
        print(f"  🏢 Departments: {len(departments_found)} - {', '.join(sorted(departments_found))}")
        print(f"  📈 Confidence: Avg={avg_confidence:.2f}, Min={min_confidence:.2f}, Max={max_confidence:.2f}")
        print(f"  🔢 Unique Codes: {len(deliverable_codes)}")
        print(f"  🤖 Using GPT-5: {'Yes ✅' if using_gpt5 else 'No ❌'}")
        print(f"  ✅ Status: {'PASSED' if passed else 'FAILED'}")
        
        if issues:
            print(f"  ⚠️ Issues: {'; '.join(issues)}")
        
        # Sample some deliverables
        print(f"\n  Sample Deliverables:")
        for i, deliv in enumerate(deliverables[:5], 1):
            print(f"    {i}. [{deliv.get('code')}] {deliv.get('title', 'N/A')} - Conf: {deliv.get('confidence', 0):.2f}")
            why = deliv.get('why', '')[:100]
            if why:
                print(f"       Why: {why}...")
        
        return {
            "success": passed,
            "test_name": test_name,
            "elapsed": elapsed,
            "total_deliverables": total_deliverables,
            "total_components": len(components),
            "total_tasks": len(tasks),
            "departments": list(departments_found),
            "confidence_avg": avg_confidence,
            "confidence_min": min_confidence,
            "confidence_max": max_confidence,
            "unique_codes": len(deliverable_codes),
            "using_gpt5": using_gpt5,
            "issues": issues,
            "sample_deliverables": deliverables[:5]
        }
    
    async def run_tests(self):
        """Run focused test suite"""
        print("\n" + "="*80)
        print("GPT-5 RFP ANALYSIS - FOCUSED TEST SUITE")
        print("="*80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test 1: Complex Fashion RFP (should produce 100+ deliverables)
        if os.path.exists("test_rfps/fashion_rfp.txt"):
            with open("test_rfps/fashion_rfp.txt", "r") as f:
                fashion_rfp = f.read()
            
            result = await self.test_rfp_analysis(
                fashion_rfp,
                "Fashion Industry - Complex RFP",
                expected_deliverables=100
            )
            self.test_results.append(result)
        
        # Test 2: Tech RFP
        if os.path.exists("test_rfps/tech_rfp.txt"):
            with open("test_rfps/tech_rfp.txt", "r") as f:
                tech_rfp = f.read()
            
            result = await self.test_rfp_analysis(
                tech_rfp,
                "Tech/SaaS - Enterprise RFP",
                expected_deliverables=100
            )
            self.test_results.append(result)
        
        # Test 3: Simple RFP (should still produce good results)
        simple_rfp = """
        We need a comprehensive marketing campaign for our new product launch.
        Requirements:
        - Brand strategy and positioning
        - Creative campaign development
        - Digital marketing across all channels
        - Social media management
        - Influencer partnerships
        - Paid media strategy
        - Content creation
        - Analytics and reporting
        - PR and events
        Budget: $2M, Timeline: 6 months
        """
        
        result = await self.test_rfp_analysis(
            simple_rfp,
            "Simple Product Launch RFP",
            expected_deliverables=30
        )
        self.test_results.append(result)
        
        # Generate final report
        self.generate_report()
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "="*80)
        print("TEST SUMMARY REPORT")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.get("success"))
        total_time = sum(r.get("elapsed", 0) for r in self.test_results)
        total_deliverables = sum(r.get("total_deliverables", 0) for r in self.test_results)
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}/{total_tests} ({passed_tests/max(1,total_tests)*100:.0f}%)")
        print(f"Total Time: {total_time:.1f} seconds")
        print(f"Total Deliverables Generated: {total_deliverables}")
        
        # Key findings
        all_using_gpt5 = all(r.get("using_gpt5", False) for r in self.test_results)
        avg_deliverables = total_deliverables / max(1, total_tests)
        
        print(f"\n🎯 Key Findings:")
        print(f"  • GPT-5 Usage: {'All tests used GPT-5 ✅' if all_using_gpt5 else 'Some tests fell back to embeddings ⚠️'}")
        print(f"  • Avg Deliverables per Test: {avg_deliverables:.0f}")
        print(f"  • Avg Time per Test: {total_time/max(1, total_tests):.1f}s")
        
        # Issues summary
        all_issues = []
        for result in self.test_results:
            all_issues.extend(result.get("issues", []))
        
        if all_issues:
            print(f"\n⚠️ Issues Found:")
            issue_counts = {}
            for issue in all_issues:
                key = issue.split(":")[0]
                issue_counts[key] = issue_counts.get(key, 0) + 1
            for issue_type, count in issue_counts.items():
                print(f"  • {issue_type}: {count} occurrence(s)")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        if not all_using_gpt5:
            print("  • Check GPT-5 availability and API configuration")
        if avg_deliverables < 50:
            print("  • Increase batch sizes or adjust prompts for more comprehensive results")
        if total_time / max(1, total_tests) > 60:
            print("  • Consider optimizing batch processing for faster results")
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"gpt5_focused_report_{timestamp}.json"
        with open(report_file, "w") as f:
            json.dump({
                "summary": {
                    "total_tests": total_tests,
                    "passed": passed_tests,
                    "total_time": total_time,
                    "total_deliverables": total_deliverables,
                    "all_using_gpt5": all_using_gpt5
                },
                "test_results": self.test_results
            }, f, indent=2, default=str)
        
        print(f"\n📄 Report saved to: {report_file}")
        
        if passed_tests == total_tests:
            print(f"\n✅ ALL TESTS PASSED! GPT-5 integration is working correctly.")
        else:
            print(f"\n❌ Some tests failed. Review the issues and recommendations above.")
    
    async def close(self):
        """Clean up"""
        await self.client.aclose()

async def main():
    """Run focused tests"""
    tester = FocusedGPT5Tester()
    try:
        # Check API health
        response = await tester.client.get(f"{API_BASE_URL}/api/ai/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API is healthy")
            print(f"  Database: {data.get('deliverables')} deliverables available")
        
        # Run tests
        await tester.run_tests()
    except Exception as e:
        print(f"💥 Error: {e}")
    finally:
        await tester.close()

if __name__ == "__main__":
    asyncio.run(main())