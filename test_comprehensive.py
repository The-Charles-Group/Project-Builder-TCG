#!/usr/bin/env python3
"""
MASTER TEST SUITE - Agency Project Builder
Comprehensive test runner coordinating all feature tests
"""

import os
import sys
import json
import time
import asyncio
import subprocess
import psutil
from datetime import datetime
from typing import Dict, List, Any, Tuple
import traceback

# Test modules to run
TEST_MODULES = [
    {
        "name": "GPT-5 RFP Analysis",
        "file": "test_gpt5_analysis.py",
        "description": "Tests document processing, AI intelligence, and error handling"
    },
    {
        "name": "Industry Templates",
        "file": "test_industry_templates.py", 
        "description": "Tests all 6 industry templates and their deliverables"
    },
    {
        "name": "Scenario Workflow",
        "file": "test_scenario_workflow.py",
        "description": "Tests scenario building, AI features, and pricing"
    },
    {
        "name": "Timeline & CPM",
        "file": "test_timeline_cpm.py",
        "description": "Tests timeline generation, critical path, and resource leveling"
    },
    {
        "name": "XML Workfront Export",
        "file": "test_xml_workfront.py",
        "description": "Tests XML export and Workfront compatibility"
    }
]

class TestReport:
    """Comprehensive test report generator"""
    
    def __init__(self):
        self.start_time = time.time()
        self.results = {}
        self.summary = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "errors": [],
            "performance": {},
            "memory": {},
            "recommendations": []
        }
        
    def add_test_result(self, name: str, result: Dict):
        """Add test result to report"""
        self.results[name] = result
        self.summary["total_tests"] += result.get("tests_run", 0)
        self.summary["passed"] += result.get("passed", 0)
        self.summary["failed"] += result.get("failed", 0)
        self.summary["warnings"] += result.get("warnings", 0)
        
        if result.get("errors"):
            self.summary["errors"].extend(result["errors"])
            
    def generate_html_report(self) -> str:
        """Generate HTML report"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Agency Project Builder - Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
        .summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }
        .stat-card { background: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-card h3 { margin: 0; font-size: 14px; color: #666; }
        .stat-card .value { font-size: 36px; font-weight: bold; margin: 10px 0; }
        .passed { color: #27ae60; }
        .failed { color: #e74c3c; }
        .warning { color: #f39c12; }
        .test-module { background: white; margin: 20px 0; padding: 20px; border-radius: 5px; }
        .test-module h2 { border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        .error { background: #ffe5e5; padding: 10px; border-left: 4px solid #e74c3c; margin: 10px 0; }
        .recommendation { background: #fff3cd; padding: 10px; border-left: 4px solid #f39c12; margin: 10px 0; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; }
        .progress-bar { background: #e0e0e0; height: 20px; border-radius: 10px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #27ae60, #3498db); }
    </style>
</head>
<body>
    <div class="header">
        <h1>Agency Project Builder - Comprehensive Test Report</h1>
        <p>Generated: {{timestamp}}</p>
        <p>Total Runtime: {{runtime}}</p>
    </div>
    
    <div class="summary">
        <div class="stat-card">
            <h3>Total Tests</h3>
            <div class="value">{{total_tests}}</div>
        </div>
        <div class="stat-card">
            <h3>Passed</h3>
            <div class="value passed">{{passed}}</div>
        </div>
        <div class="stat-card">
            <h3>Failed</h3>
            <div class="value failed">{{failed}}</div>
        </div>
        <div class="stat-card">
            <h3>Success Rate</h3>
            <div class="value">{{success_rate}}%</div>
        </div>
    </div>
    
    <div class="progress-bar">
        <div class="progress-fill" style="width: {{success_rate}}%"></div>
    </div>
    
    {{test_modules}}
    
    {{errors_section}}
    
    {{recommendations_section}}
    
</body>
</html>
"""
        
        # Generate test modules section
        modules_html = ""
        for name, result in self.results.items():
            modules_html += f"""
    <div class="test-module">
        <h2>{name}</h2>
        <p>{result.get('description', '')}</p>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Tests Run</td><td>{result.get('tests_run', 0)}</td></tr>
            <tr><td>Passed</td><td class="passed">{result.get('passed', 0)}</td></tr>
            <tr><td>Failed</td><td class="failed">{result.get('failed', 0)}</td></tr>
            <tr><td>Duration</td><td>{result.get('duration', 0):.2f}s</td></tr>
            <tr><td>Memory Used</td><td>{result.get('memory_mb', 0):.1f}MB</td></tr>
        </table>
    </div>
"""
        
        # Generate errors section
        errors_html = ""
        if self.summary["errors"]:
            errors_html = "<h2>Errors Found</h2>"
            for error in self.summary["errors"]:
                errors_html += f'<div class="error">{error}</div>'
                
        # Generate recommendations
        recommendations_html = ""
        if self.summary["recommendations"]:
            recommendations_html = "<h2>Recommendations</h2>"
            for rec in self.summary["recommendations"]:
                recommendations_html += f'<div class="recommendation">{rec}</div>'
                
        # Fill template
        runtime = time.time() - self.start_time
        success_rate = (self.summary["passed"] / self.summary["total_tests"] * 100) if self.summary["total_tests"] > 0 else 0
        
        html = html.replace("{{timestamp}}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        html = html.replace("{{runtime}}", f"{runtime:.2f}s")
        html = html.replace("{{total_tests}}", str(self.summary["total_tests"]))
        html = html.replace("{{passed}}", str(self.summary["passed"]))
        html = html.replace("{{failed}}", str(self.summary["failed"]))
        html = html.replace("{{success_rate}}", f"{success_rate:.1f}")
        html = html.replace("{{test_modules}}", modules_html)
        html = html.replace("{{errors_section}}", errors_html)
        html = html.replace("{{recommendations_section}}", recommendations_html)
        
        return html

class ComprehensiveTestRunner:
    """Master test runner coordinating all tests"""
    
    def __init__(self):
        self.report = TestReport()
        
    def check_server_running(self) -> bool:
        """Check if FastAPI server is running"""
        try:
            import httpx
            with httpx.Client() as client:
                response = client.get("http://localhost:5000/api/load", timeout=5)
                return response.status_code == 200
        except:
            return False
            
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
        
    def run_test_module(self, module: Dict) -> Dict:
        """Run a single test module"""
        print(f"\n{'='*80}")
        print(f"Running: {module['name']}")
        print(f"Description: {module['description']}")
        print('='*80)
        
        result = {
            "name": module["name"],
            "file": module["file"],
            "description": module["description"],
            "tests_run": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "errors": [],
            "duration": 0,
            "memory_mb": 0
        }
        
        if not os.path.exists(module["file"]):
            print(f"❌ Test file {module['file']} not found")
            result["errors"] = [f"Test file {module['file']} not found"]
            return result
            
        try:
            start_time = time.time()
            start_memory = self.get_memory_usage()
            
            # Run the test module
            process = subprocess.run(
                [sys.executable, module["file"]],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            end_time = time.time()
            end_memory = self.get_memory_usage()
            
            result["duration"] = end_time - start_time
            result["memory_mb"] = end_memory - start_memory
            
            # Parse output for results
            output = process.stdout
            
            # Look for test results in output
            if "passed" in output.lower():
                # Try to extract numbers
                lines = output.split('\n')
                for line in lines:
                    if 'total tests' in line.lower():
                        try:
                            result["tests_run"] = int(''.join(filter(str.isdigit, line.split(':')[-1])))
                        except:
                            pass
                    if 'passed' in line.lower() and '✅' in line:
                        try:
                            result["passed"] = int(''.join(filter(str.isdigit, line.split(':')[-1])))
                        except:
                            pass
                    if 'failed' in line.lower() and '❌' in line:
                        try:
                            result["failed"] = int(''.join(filter(str.isdigit, line.split(':')[-1])))
                        except:
                            pass
                            
            # If we didn't get specific counts, use exit code
            if result["tests_run"] == 0:
                if process.returncode == 0:
                    result["tests_run"] = 1
                    result["passed"] = 1
                else:
                    result["tests_run"] = 1
                    result["failed"] = 1
                    
            # Capture any errors
            if process.stderr:
                result["errors"].append(process.stderr[:500])  # First 500 chars of error
                
            print(f"\n✅ Module completed in {result['duration']:.2f}s")
            print(f"   Tests: {result['tests_run']} | Passed: {result['passed']} | Failed: {result['failed']}")
            print(f"   Memory used: {result['memory_mb']:.1f}MB")
            
        except subprocess.TimeoutExpired:
            result["errors"] = ["Test module timed out after 10 minutes"]
            print(f"❌ Test module timed out")
            
        except Exception as e:
            result["errors"] = [str(e)]
            print(f"❌ Error running test module: {e}")
            
        return result
        
    async def run_all_tests(self):
        """Run all test modules"""
        print("\n" + "="*80)
        print("AGENCY PROJECT BUILDER - COMPREHENSIVE TEST SUITE")
        print("="*80)
        print(f"Starting at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check server
        if not self.check_server_running():
            print("\n❌ FastAPI server is not running!")
            print("Please start the server with: python -m uvicorn main:app --host 0.0.0.0 --port 5000 --reload")
            return
            
        print("✅ Server is running")
        
        # Run each test module
        for module in TEST_MODULES:
            result = self.run_test_module(module)
            self.report.add_test_result(module["name"], result)
            
        # Analyze results and generate recommendations
        self.analyze_and_recommend()
        
        # Print summary
        self.print_summary()
        
        # Generate HTML report
        html_report = self.report.generate_html_report()
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(report_file, 'w') as f:
            f.write(html_report)
        print(f"\n📊 HTML report generated: {report_file}")
        
        # Save JSON report
        json_report = {
            "timestamp": datetime.now().isoformat(),
            "summary": self.report.summary,
            "results": self.report.results
        }
        json_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_file, 'w') as f:
            json.dump(json_report, f, indent=2)
        print(f"📊 JSON report generated: {json_file}")
        
    def analyze_and_recommend(self):
        """Analyze results and generate recommendations"""
        recommendations = []
        
        # Check overall success rate
        if self.report.summary["total_tests"] > 0:
            success_rate = (self.report.summary["passed"] / self.report.summary["total_tests"]) * 100
            
            if success_rate < 50:
                recommendations.append(
                    "⚠️ CRITICAL: Success rate below 50%. Major issues detected that need immediate attention."
                )
            elif success_rate < 80:
                recommendations.append(
                    "⚠️ WARNING: Success rate below 80%. Several issues need to be addressed before production."
                )
            elif success_rate < 95:
                recommendations.append(
                    "ℹ️ INFO: Success rate above 80% but below 95%. Minor issues to address for optimal performance."
                )
            else:
                recommendations.append(
                    "✅ EXCELLENT: Success rate above 95%. System is production-ready."
                )
                
        # Check for specific issues
        for name, result in self.report.results.items():
            if result.get("errors"):
                recommendations.append(f"Fix errors in {name}: {result['errors'][0][:100]}")
                
            if result.get("duration", 0) > 300:  # 5 minutes
                recommendations.append(f"Optimize {name} - taking {result['duration']:.0f}s (>5 min)")
                
            if result.get("memory_mb", 0) > 500:
                recommendations.append(f"High memory usage in {name}: {result['memory_mb']:.0f}MB")
                
        # Check specific features
        if "GPT-5" in str(self.report.results):
            if any("gpt-5" in str(r.get("errors", [])).lower() for r in self.report.results.values()):
                recommendations.append("Ensure GPT-5 API key is configured and model access is enabled")
                
        if self.report.summary["failed"] > 0:
            recommendations.append(f"Fix {self.report.summary['failed']} failing tests before deployment")
            
        self.report.summary["recommendations"] = recommendations
        
    def print_summary(self):
        """Print test summary to console"""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        total = self.report.summary["total_tests"]
        passed = self.report.summary["passed"]
        failed = self.report.summary["failed"]
        
        print(f"Total Tests Run: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Warnings: {self.report.summary['warnings']} ⚠️")
        
        if total > 0:
            success_rate = (passed / total) * 100
            print(f"Success Rate: {success_rate:.1f}%")
            
            # Visual progress bar
            bar_length = 50
            filled = int(bar_length * passed / total)
            bar = '█' * filled + '░' * (bar_length - filled)
            print(f"Progress: [{bar}] {success_rate:.1f}%")
            
        # Performance metrics
        print("\n📊 PERFORMANCE METRICS:")
        total_duration = sum(r.get("duration", 0) for r in self.report.results.values())
        total_memory = sum(r.get("memory_mb", 0) for r in self.report.results.values())
        print(f"Total Runtime: {total_duration:.2f}s")
        print(f"Total Memory Used: {total_memory:.1f}MB")
        
        # Module breakdown
        print("\n📋 MODULE BREAKDOWN:")
        for name, result in self.report.results.items():
            status = "✅" if result.get("failed", 0) == 0 else "❌"
            print(f"{status} {name}: {result.get('passed', 0)}/{result.get('tests_run', 0)} passed ({result.get('duration', 0):.1f}s)")
            
        # Errors
        if self.report.summary["errors"]:
            print("\n❌ ERRORS FOUND:")
            for i, error in enumerate(self.report.summary["errors"][:5], 1):
                print(f"  {i}. {error[:100]}...")
                
        # Recommendations
        if self.report.summary["recommendations"]:
            print("\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(self.report.summary["recommendations"], 1):
                print(f"  {i}. {rec}")
                
        # Final verdict
        print("\n" + "="*80)
        if failed == 0 and total > 0:
            print("🎉 ALL TESTS PASSED - SYSTEM IS PRODUCTION READY! 🎉")
        elif failed < total * 0.2:
            print("✅ MOSTLY PASSING - Minor fixes needed before production")
        elif failed < total * 0.5:
            print("⚠️ NEEDS WORK - Significant issues to address")
        else:
            print("❌ CRITICAL ISSUES - Major problems detected, not ready for production")
        print("="*80)

async def main():
    """Main entry point"""
    runner = ComprehensiveTestRunner()
    await runner.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())