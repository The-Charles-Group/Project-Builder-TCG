#!/usr/bin/env python3
"""
Comprehensive Test Suite for GPT-5 RFP Analysis Functionality
Tests all scenarios for document processing, deliverable extraction, and error handling
"""

import os
import sys
import json
import time
import psutil
import asyncio
import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime
import traceback

# Test configuration
API_BASE_URL = "http://localhost:5000"
TIMEOUT = 300  # 5 minutes timeout for large documents

# Expected minimum deliverables for GPT-5 (not fallback)
MIN_DELIVERABLES_GPT5 = 100
MIN_DELIVERABLES_FALLBACK = 15

# Test results storage
test_results = {
    "timestamp": datetime.now().isoformat(),
    "tests": [],
    "summary": {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "warnings": 0
    },
    "performance_metrics": {
        "total_runtime": 0,
        "memory_usage": {}
    }
}

class TestCase:
    """Single test case for RFP analysis"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.start_time = None
        self.end_time = None
        self.status = "pending"
        self.result = {}
        self.error = None
        self.warnings = []
        
    def start(self):
        """Start the test case"""
        self.start_time = time.time()
        print(f"\n🔄 Running: {self.name}")
        print(f"   {self.description}")
        
    def complete(self, status: str, result: Dict = None, error: str = None):
        """Complete the test case"""
        self.end_time = time.time()
        self.status = status
        self.result = result or {}
        self.error = error
        duration = self.end_time - self.start_time
        
        # Status emoji
        emoji = "✅" if status == "passed" else "❌" if status == "failed" else "⚠️"
        
        print(f"{emoji} {self.name}: {status} ({duration:.2f}s)")
        if error:
            print(f"   Error: {error}")
        
        # Add to results
        test_results["tests"].append({
            "name": self.name,
            "description": self.description,
            "status": status,
            "duration": duration,
            "result": self.result,
            "error": error,
            "warnings": self.warnings
        })
        
        # Update summary
        test_results["summary"]["total"] += 1
        if status == "passed":
            test_results["summary"]["passed"] += 1
        elif status == "failed":
            test_results["summary"]["failed"] += 1
        if self.warnings:
            test_results["summary"]["warnings"] += len(self.warnings)

async def upload_and_analyze(file_path: str, mode: str = "deep") -> Dict:
    """Upload a document and analyze it using the API"""
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Test file not found: {file_path}")
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Upload the file
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'application/octet-stream')}
            data = {'mode': mode}
            
            # Start timing
            start_time = time.time()
            
            # Call the analyze endpoint
            response = await client.post(
                f"{API_BASE_URL}/api/ai/analyze",
                files=files,
                data=data
            )
            
            # Calculate duration
            duration = time.time() - start_time
            
            if response.status_code != 200:
                raise Exception(f"API returned {response.status_code}: {response.text}")
            
            result = response.json()
            result['response_time'] = duration
            
            # Check if this is a job response (async processing)
            if 'job_id' in result:
                job_id = result['job_id']
                print(f"   Job started: {job_id}")
                
                # Poll for job completion
                max_polls = 60  # Poll for up to 5 minutes
                poll_count = 0
                
                while poll_count < max_polls:
                    await asyncio.sleep(5)  # Wait 5 seconds between polls
                    poll_count += 1
                    
                    status_response = await client.get(f"{API_BASE_URL}/api/ai/jobs/{job_id}")
                    if status_response.status_code == 200:
                        job_status = status_response.json()
                        
                        print(f"   Job status: {job_status.get('status', 'unknown')} - {job_status.get('current_stage', '')}")
                        
                        if job_status.get('status') == 'completed':
                            result = job_status.get('result', {})
                            result['response_time'] = time.time() - start_time
                            result['job_id'] = job_id
                            break
                        elif job_status.get('status') == 'failed':
                            raise Exception(f"Job failed: {job_status.get('error', 'Unknown error')}")
                else:
                    raise Exception(f"Job timeout after {poll_count * 5} seconds")
            
            return result

async def test_document_format(file_path: str, test_case: TestCase, expected_min_deliverables: int = MIN_DELIVERABLES_GPT5):
    """Test analysis of a specific document format"""
    
    test_case.start()
    
    try:
        # Get memory before
        process = psutil.Process()
        mem_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Analyze the document
        result = await upload_and_analyze(file_path)
        
        # Get memory after
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_used = mem_after - mem_before
        
        # Extract key metrics
        deliverables = result.get('suggestions', [])
        deliverable_count = len(deliverables)
        response_time = result.get('response_time', 0)
        method_used = result.get('method', 'unknown')
        
        # Check if GPT-5 was used
        is_gpt5 = 'gpt5' in method_used.lower() or 'gpt-5' in method_used.lower()
        
        # Verify deliverable count
        if deliverable_count < expected_min_deliverables:
            test_case.warnings.append(f"Only {deliverable_count} deliverables returned (expected {expected_min_deliverables}+)")
            
        # Check for evidence and confidence scores
        has_confidence = all('confidence' in d for d in deliverables[:10]) if deliverables else False
        has_evidence = all('evidence' in d or 'reasoning' in d for d in deliverables[:10]) if deliverables else False
        
        # Check for department grouping
        departments = set()
        for d in deliverables:
            if 'department' in d:
                departments.add(d['department'])
            elif 'category' in d:
                departments.add(d['category'])
        
        test_result = {
            "file": os.path.basename(file_path),
            "deliverable_count": deliverable_count,
            "response_time": response_time,
            "memory_used_mb": mem_used,
            "method": method_used,
            "is_gpt5": is_gpt5,
            "has_confidence_scores": has_confidence,
            "has_evidence": has_evidence,
            "department_count": len(departments),
            "departments": list(departments)
        }
        
        # Determine pass/fail
        if deliverable_count >= expected_min_deliverables and is_gpt5:
            test_case.complete("passed", test_result)
        elif deliverable_count >= MIN_DELIVERABLES_FALLBACK:
            test_case.warnings.append("Using fallback method, not GPT-5")
            test_case.complete("warning", test_result)
        else:
            test_case.complete("failed", test_result, f"Insufficient deliverables: {deliverable_count}")
            
    except Exception as e:
        test_case.complete("failed", error=str(e))
        print(f"   Exception: {traceback.format_exc()}")

async def test_error_handling(file_path: str, test_case: TestCase, should_fail: bool = True):
    """Test error handling for invalid files"""
    
    test_case.start()
    
    try:
        result = await upload_and_analyze(file_path)
        
        # If we expected failure but got success
        if should_fail:
            test_case.complete("failed", result, "Expected error but request succeeded")
        else:
            test_case.complete("passed", result)
            
    except Exception as e:
        # If we expected failure and got it
        if should_fail:
            test_case.complete("passed", {"error_message": str(e)})
        else:
            test_case.complete("failed", error=str(e))

async def test_performance_comparison():
    """Test and compare performance between small and large documents"""
    
    print("\n📊 Performance Comparison Test")
    print("="*50)
    
    results = {}
    
    # Test small document
    test_case = TestCase(
        "Performance - Small Document",
        "Test response time and resource usage for 1-page document"
    )
    test_case.start()
    
    try:
        start_mem = psutil.virtual_memory().percent
        result_small = await upload_and_analyze("test_docs/luxury_fashion_rfp_small.pdf")
        end_mem = psutil.virtual_memory().percent
        
        results["small"] = {
            "response_time": result_small.get('response_time', 0),
            "deliverable_count": len(result_small.get('suggestions', [])),
            "memory_delta": end_mem - start_mem
        }
        test_case.complete("passed", results["small"])
    except Exception as e:
        test_case.complete("failed", error=str(e))
    
    # Test large document
    test_case = TestCase(
        "Performance - Large Document",
        "Test response time and resource usage for 10+ page document"
    )
    test_case.start()
    
    try:
        start_mem = psutil.virtual_memory().percent
        result_large = await upload_and_analyze("test_docs/luxury_fashion_rfp_large.pdf")
        end_mem = psutil.virtual_memory().percent
        
        results["large"] = {
            "response_time": result_large.get('response_time', 0),
            "deliverable_count": len(result_large.get('suggestions', [])),
            "memory_delta": end_mem - start_mem
        }
        test_case.complete("passed", results["large"])
    except Exception as e:
        test_case.complete("failed", error=str(e))
    
    # Calculate performance ratio
    if "small" in results and "large" in results:
        time_ratio = results["large"]["response_time"] / results["small"]["response_time"]
        print(f"\n   Performance Ratio (Large/Small): {time_ratio:.2f}x slower")
        
    return results

async def run_all_tests():
    """Run all test scenarios"""
    
    print("="*60)
    print("🧪 GPT-5 RFP Analysis - Comprehensive Test Suite")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Endpoint: {API_BASE_URL}")
    print(f"Expected minimum deliverables: {MIN_DELIVERABLES_GPT5}")
    
    # Track overall start time
    suite_start = time.time()
    
    # Get initial system metrics
    initial_memory = psutil.virtual_memory().percent
    initial_cpu = psutil.cpu_percent(interval=1)
    
    print("\n" + "="*60)
    print("📁 Testing Document Format Support")
    print("="*60)
    
    # Test different document formats with small files
    formats_to_test = [
        ("test_docs/luxury_fashion_rfp_small.txt", "TXT Format - Small"),
        ("test_docs/luxury_fashion_rfp_small.docx", "DOCX Format - Small"),
        ("test_docs/luxury_fashion_rfp_small.pdf", "PDF Format - Small"),
    ]
    
    for file_path, description in formats_to_test:
        test_case = TestCase(f"Format Test - {description}", f"Test {description} document processing")
        await test_document_format(file_path, test_case)
    
    print("\n" + "="*60)
    print("📏 Testing Document Size Handling")
    print("="*60)
    
    # Test large documents
    large_formats = [
        ("test_docs/luxury_fashion_rfp_large.txt", "TXT Format - Large"),
        ("test_docs/luxury_fashion_rfp_large.docx", "DOCX Format - Large"),
        ("test_docs/luxury_fashion_rfp_large.pdf", "PDF Format - Large"),
    ]
    
    for file_path, description in large_formats:
        test_case = TestCase(f"Size Test - {description}", f"Test {description} (10+ pages) document processing")
        await test_document_format(file_path, test_case)
    
    print("\n" + "="*60)
    print("❌ Testing Error Handling")
    print("="*60)
    
    # Test error scenarios
    error_scenarios = [
        ("test_docs/empty.txt", "Empty TXT File", True),
        ("test_docs/empty.pdf", "Empty PDF File", True),
        ("test_docs/empty.docx", "Empty DOCX File", True),
        ("test_docs/corrupted.pdf", "Corrupted PDF File", True),
        ("test_docs/corrupted.docx", "Corrupted DOCX File", True),
        ("test_docs/nonexistent.pdf", "Non-existent File", True),
    ]
    
    for file_path, description, should_fail in error_scenarios:
        test_case = TestCase(f"Error Test - {description}", f"Test error handling for {description}")
        await test_error_handling(file_path, test_case, should_fail)
    
    print("\n" + "="*60)
    print("⚡ Testing Performance")
    print("="*60)
    
    # Run performance comparison
    perf_results = await test_performance_comparison()
    
    # Calculate final metrics
    suite_end = time.time()
    total_runtime = suite_end - suite_start
    final_memory = psutil.virtual_memory().percent
    final_cpu = psutil.cpu_percent(interval=1)
    
    # Update performance metrics
    test_results["performance_metrics"] = {
        "total_runtime": total_runtime,
        "memory_usage": {
            "initial": initial_memory,
            "final": final_memory,
            "delta": final_memory - initial_memory
        },
        "cpu_usage": {
            "initial": initial_cpu,
            "final": final_cpu
        }
    }
    
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    
    # Print summary
    summary = test_results["summary"]
    print(f"Total Tests: {summary['total']}")
    print(f"✅ Passed: {summary['passed']}")
    print(f"❌ Failed: {summary['failed']}")
    print(f"⚠️  Warnings: {summary['warnings']}")
    print(f"⏱️  Total Runtime: {total_runtime:.2f}s")
    print(f"💾 Memory Delta: {final_memory - initial_memory:.2f}%")
    
    # Calculate success rate
    if summary['total'] > 0:
        success_rate = (summary['passed'] / summary['total']) * 100
        print(f"📈 Success Rate: {success_rate:.1f}%")
    
    return test_results

def generate_report(results: Dict):
    """Generate a comprehensive test report"""
    
    report_path = "test_report_gpt5_rfp_analysis.md"
    
    with open(report_path, 'w') as f:
        f.write("# GPT-5 RFP Analysis - Test Report\n\n")
        f.write(f"**Generated:** {results['timestamp']}\n\n")
        
        # Executive Summary
        f.write("## Executive Summary\n\n")
        summary = results['summary']
        f.write(f"- **Total Tests:** {summary['total']}\n")
        f.write(f"- **Passed:** {summary['passed']}\n")
        f.write(f"- **Failed:** {summary['failed']}\n")
        f.write(f"- **Warnings:** {summary['warnings']}\n")
        
        success_rate = (summary['passed'] / summary['total']) * 100 if summary['total'] > 0 else 0
        f.write(f"- **Success Rate:** {success_rate:.1f}%\n\n")
        
        # Performance Metrics
        f.write("## Performance Metrics\n\n")
        perf = results['performance_metrics']
        f.write(f"- **Total Runtime:** {perf['total_runtime']:.2f} seconds\n")
        f.write(f"- **Memory Usage Delta:** {perf['memory_usage']['delta']:.2f}%\n")
        f.write(f"- **Initial CPU:** {perf['cpu_usage']['initial']:.1f}%\n")
        f.write(f"- **Final CPU:** {perf['cpu_usage']['final']:.1f}%\n\n")
        
        # Detailed Test Results
        f.write("## Detailed Test Results\n\n")
        
        for test in results['tests']:
            status_emoji = "✅" if test['status'] == "passed" else "❌" if test['status'] == "failed" else "⚠️"
            f.write(f"### {status_emoji} {test['name']}\n\n")
            f.write(f"**Description:** {test['description']}\n")
            f.write(f"**Status:** {test['status']}\n")
            f.write(f"**Duration:** {test['duration']:.2f}s\n\n")
            
            if test['result']:
                f.write("**Results:**\n")
                for key, value in test['result'].items():
                    if isinstance(value, list):
                        f.write(f"- **{key}:** {len(value)} items\n")
                    elif isinstance(value, float):
                        f.write(f"- **{key}:** {value:.2f}\n")
                    else:
                        f.write(f"- **{key}:** {value}\n")
                f.write("\n")
            
            if test.get('error'):
                f.write(f"**Error:** {test['error']}\n\n")
            
            if test.get('warnings'):
                f.write("**Warnings:**\n")
                for warning in test['warnings']:
                    f.write(f"- {warning}\n")
                f.write("\n")
        
        # Key Findings
        f.write("## Key Findings\n\n")
        
        # Analyze deliverable counts
        deliverable_tests = [t for t in results['tests'] if 'deliverable_count' in t.get('result', {})]
        if deliverable_tests:
            counts = [t['result']['deliverable_count'] for t in deliverable_tests]
            avg_count = sum(counts) / len(counts)
            max_count = max(counts)
            min_count = min(counts)
            
            f.write(f"### Deliverable Analysis\n")
            f.write(f"- **Average Deliverables:** {avg_count:.0f}\n")
            f.write(f"- **Maximum Deliverables:** {max_count}\n")
            f.write(f"- **Minimum Deliverables:** {min_count}\n")
            f.write(f"- **Target (GPT-5):** {MIN_DELIVERABLES_GPT5}+\n\n")
            
            # Check if GPT-5 is being used
            gpt5_tests = [t for t in deliverable_tests if t['result'].get('is_gpt5', False)]
            if gpt5_tests:
                f.write(f"### GPT-5 Usage\n")
                f.write(f"- **Tests using GPT-5:** {len(gpt5_tests)}/{len(deliverable_tests)}\n")
                f.write(f"- **GPT-5 Adoption Rate:** {(len(gpt5_tests)/len(deliverable_tests)*100):.1f}%\n\n")
        
        # Response time analysis
        response_times = [t['result'].get('response_time', 0) for t in results['tests'] if 'response_time' in t.get('result', {})]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            f.write(f"### Response Time Analysis\n")
            f.write(f"- **Average Response Time:** {avg_time:.2f}s\n")
            f.write(f"- **Maximum Response Time:** {max_time:.2f}s\n")
            f.write(f"- **Minimum Response Time:** {min_time:.2f}s\n\n")
        
        # Recommendations
        f.write("## Recommendations\n\n")
        
        if summary['failed'] > 0:
            f.write("### Critical Issues to Address\n\n")
            failed_tests = [t for t in results['tests'] if t['status'] == 'failed']
            for test in failed_tests:
                f.write(f"- **{test['name']}:** {test.get('error', 'Unknown error')}\n")
            f.write("\n")
        
        if summary['warnings'] > 0:
            f.write("### Warnings to Review\n\n")
            warning_tests = [t for t in results['tests'] if t.get('warnings')]
            for test in warning_tests:
                f.write(f"- **{test['name']}:**\n")
                for warning in test['warnings']:
                    f.write(f"  - {warning}\n")
            f.write("\n")
        
        f.write("## Conclusion\n\n")
        if success_rate >= 90:
            f.write("✅ The GPT-5 RFP analysis system is performing excellently with high success rate.\n")
        elif success_rate >= 70:
            f.write("⚠️ The system is functional but has some issues that should be addressed.\n")
        else:
            f.write("❌ The system has critical issues that need immediate attention.\n")
    
    print(f"\n📄 Test report generated: {report_path}")
    return report_path

async def main():
    """Main test execution"""
    try:
        # Run all tests
        results = await run_all_tests()
        
        # Generate report
        report_path = generate_report(results)
        
        # Save raw results as JSON
        with open("test_results_gpt5_rfp_analysis.json", 'w') as f:
            json.dump(results, f, indent=2)
        
        print("\n✅ Testing completed successfully!")
        print(f"📊 Results saved to: test_results_gpt5_rfp_analysis.json")
        print(f"📄 Report saved to: {report_path}")
        
        # Return exit code based on failures
        if results['summary']['failed'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())