#!/usr/bin/env python3
"""
End-to-End Flow Test for Agency Project Builder
Tests the complete user journey from AI job to XML export
"""

import json
import time
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
import sys

# Configuration
BASE_URL = "http://localhost:5000"
TEST_JOB_ID = "23ad2edc-0b57-48c8-9146-88e4f5851ccb"
TEST_SESSION_ID = "test-flow-session-001"

class APBFlowTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session_id = TEST_SESSION_ID
        self.job_id = TEST_JOB_ID
        self.results = {
            "start_time": datetime.now().isoformat(),
            "steps": [],
            "metrics": {},
            "issues": [],
            "status": "in_progress"
        }
        self.scenario_data = None
        self.selected_deliverables = []
        self.timeline_data = None
        
    def log(self, message: str, level: str = "INFO"):
        """Log messages with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [{level}] {message}")
        
    def measure_time(self, func, *args, **kwargs):
        """Measure execution time of a function"""
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        return result, elapsed
        
    def record_step(self, step_name: str, success: bool, details: Dict[str, Any], elapsed_time: float):
        """Record test step results"""
        self.results["steps"].append({
            "name": step_name,
            "success": success,
            "details": details,
            "elapsed_time_seconds": round(elapsed_time, 3),
            "timestamp": datetime.now().isoformat()
        })
        
    def test_job_status(self) -> bool:
        """Test 1: Check AI analysis job status"""
        self.log(f"Testing job status for job_id: {self.job_id}")
        
        try:
            response, elapsed = self.measure_time(
                requests.get,
                f"{self.base_url}/api/ai/jobs/{self.job_id}"
            )
            
            if response.status_code == 200:
                job_data = response.json()
                success = job_data.get("status") == "completed"
                
                details = {
                    "job_status": job_data.get("status"),
                    "deliverables_found": len(job_data.get("data", {}).get("deliverables", [])) if job_data.get("data") else 0,
                    "response_code": response.status_code,
                    "job_data_keys": list(job_data.keys()) if job_data else []
                }
                
                if success and job_data.get("data"):
                    self.selected_deliverables = job_data["data"].get("deliverables", [])[:10]  # Select first 10
                    self.log(f"✅ Job completed successfully with {details['deliverables_found']} deliverables")
                else:
                    self.log(f"⚠️ Job status: {job_data.get('status')}", "WARNING")
                    
                self.record_step("Check AI Job Status", success, details, elapsed)
                return success
            else:
                self.log(f"❌ Failed to get job status: HTTP {response.status_code}", "ERROR")
                self.record_step("Check AI Job Status", False, 
                               {"error": f"HTTP {response.status_code}", "response": response.text[:500]}, 
                               elapsed)
                return False
                
        except Exception as e:
            self.log(f"❌ Exception checking job status: {str(e)}", "ERROR")
            self.record_step("Check AI Job Status", False, {"error": str(e)}, 0)
            return False
            
    def test_create_scenario(self) -> bool:
        """Test 2: Create a scenario from selected deliverables"""
        self.log("Creating scenario from selected deliverables")
        
        if not self.selected_deliverables:
            self.log("⚠️ No deliverables available, using mock data", "WARNING")
            self.selected_deliverables = [
                "strategy_development",
                "brand_identity",
                "website_development",
                "content_creation",
                "paid_media_management"
            ]
        
        try:
            # Build scenario using selected deliverables
            payload = {
                "deliverables": self.selected_deliverables,
                "session_id": self.session_id,
                "options": {
                    "rate_band": "Standard",
                    "complexity": "Medium",
                    "urgency": "Standard"
                }
            }
            
            response, elapsed = self.measure_time(
                requests.post,
                f"{self.base_url}/api/scenarios",
                json=payload
            )
            
            if response.status_code == 200:
                scenario_data = response.json()
                self.scenario_data = scenario_data
                
                # Extract scenario A data
                scenario_a = scenario_data.get("scenario_a", {})
                total_hours = scenario_a.get("total_hours", 0)
                total_price = scenario_a.get("total_price", 0)
                
                details = {
                    "deliverables_count": len(self.selected_deliverables),
                    "scenario_a_hours": total_hours,
                    "scenario_a_price": total_price,
                    "has_scenario_b": "scenario_b" in scenario_data,
                    "response_code": response.status_code
                }
                
                success = total_hours > 0 and total_price > 0
                
                if success:
                    self.log(f"✅ Scenario created: {total_hours} hours, ${total_price:,.2f}")
                else:
                    self.log(f"⚠️ Scenario created but missing data", "WARNING")
                    
                self.record_step("Create Scenario", success, details, elapsed)
                return success
            else:
                self.log(f"❌ Failed to create scenario: HTTP {response.status_code}", "ERROR")
                self.record_step("Create Scenario", False, 
                               {"error": f"HTTP {response.status_code}", "response": response.text[:500]}, 
                               elapsed)
                return False
                
        except Exception as e:
            self.log(f"❌ Exception creating scenario: {str(e)}", "ERROR")
            self.record_step("Create Scenario", False, {"error": str(e)}, 0)
            return False
            
    def test_pricing_calculations(self) -> bool:
        """Test 3: Verify pricing calculations"""
        self.log("Testing pricing calculations")
        
        if not self.scenario_data:
            self.log("⚠️ No scenario data available", "WARNING")
            return False
            
        try:
            # Test pricing optimization
            payload = {
                "scenario": self.scenario_data.get("scenario_a", {}),
                "target_price": 200000,  # $200k target
                "session_id": self.session_id
            }
            
            response, elapsed = self.measure_time(
                requests.post,
                f"{self.base_url}/api/pricing/optimize",
                json=payload
            )
            
            success = response.status_code == 200
            details = {
                "response_code": response.status_code,
                "original_price": self.scenario_data.get("scenario_a", {}).get("total_price", 0)
            }
            
            if success:
                optimized = response.json()
                details["optimized_price"] = optimized.get("optimized_price", 0)
                details["adjustment_percentage"] = optimized.get("adjustment_percentage", 0)
                details["pricing_valid"] = optimized.get("optimized_price", 0) > 0
                
                self.log(f"✅ Pricing optimization successful: ${details['optimized_price']:,.2f}")
            else:
                self.log(f"⚠️ Pricing optimization failed", "WARNING")
                
            self.record_step("Pricing Calculations", success, details, elapsed)
            
            # Test retainer suggestions
            if self.scenario_data:
                retainer_response, retainer_elapsed = self.measure_time(
                    requests.post,
                    f"{self.base_url}/api/pricing/retainer_suggestions",
                    json={"deliverables": self.selected_deliverables, "session_id": self.session_id}
                )
                
                if retainer_response.status_code == 200:
                    retainer_data = retainer_response.json()
                    details["retainer_suggestions"] = len(retainer_data.get("suggestions", []))
                    self.log(f"✅ Retainer suggestions: {details['retainer_suggestions']} items")
                    
            return success
            
        except Exception as e:
            self.log(f"❌ Exception testing pricing: {str(e)}", "ERROR")
            self.record_step("Pricing Calculations", False, {"error": str(e)}, 0)
            return False
            
    def test_timeline_generation(self) -> bool:
        """Test 4: Generate and verify timeline"""
        self.log("Testing timeline generation")
        
        if not self.scenario_data:
            self.log("⚠️ No scenario data available", "WARNING")
            return False
            
        try:
            # Generate timeline for scenario A
            payload = {
                "scenario": self.scenario_data.get("scenario_a", {}),
                "start_date": "2025-01-01",
                "session_id": self.session_id
            }
            
            response, elapsed = self.measure_time(
                requests.post,
                f"{self.base_url}/api/ai/generate_timeline",
                json=payload
            )
            
            if response.status_code == 200:
                timeline_data = response.json()
                self.timeline_data = timeline_data
                
                tasks = timeline_data.get("tasks", [])
                milestones = timeline_data.get("milestones", [])
                
                details = {
                    "tasks_count": len(tasks),
                    "milestones_count": len(milestones),
                    "start_date": timeline_data.get("start_date"),
                    "end_date": timeline_data.get("end_date"),
                    "total_duration_days": timeline_data.get("total_duration_days", 0),
                    "response_code": response.status_code
                }
                
                success = len(tasks) > 0
                
                if success:
                    self.log(f"✅ Timeline generated: {details['tasks_count']} tasks, {details['milestones_count']} milestones")
                    self.log(f"   Duration: {details['total_duration_days']} days ({details['start_date']} to {details['end_date']})")
                else:
                    self.log(f"⚠️ Timeline generation incomplete", "WARNING")
                    
                self.record_step("Timeline Generation", success, details, elapsed)
                return success
            else:
                self.log(f"❌ Failed to generate timeline: HTTP {response.status_code}", "ERROR")
                self.record_step("Timeline Generation", False, 
                               {"error": f"HTTP {response.status_code}", "response": response.text[:500]}, 
                               elapsed)
                return False
                
        except Exception as e:
            self.log(f"❌ Exception generating timeline: {str(e)}", "ERROR")
            self.record_step("Timeline Generation", False, {"error": str(e)}, 0)
            return False
            
    def test_xml_export(self) -> bool:
        """Test 5: Export to XML format"""
        self.log("Testing XML export functionality")
        
        if not self.scenario_data:
            self.log("⚠️ No scenario data available", "WARNING")
            return False
            
        try:
            # Test XML export
            payload = {
                "scenario": self.scenario_data.get("scenario_a", {}),
                "timeline": self.timeline_data if self.timeline_data else {},
                "project_name": "Test Project Export",
                "session_id": self.session_id,
                "format": "xml"
            }
            
            response, elapsed = self.measure_time(
                requests.post,
                f"{self.base_url}/api/export/xml",
                json=payload
            )
            
            if response.status_code == 200:
                # Check if we got XML content
                content_type = response.headers.get("content-type", "")
                is_xml = "xml" in content_type.lower() or response.text.startswith("<?xml")
                
                details = {
                    "response_code": response.status_code,
                    "content_type": content_type,
                    "content_length": len(response.content),
                    "is_valid_xml": is_xml,
                    "first_100_chars": response.text[:100] if response.text else ""
                }
                
                success = is_xml and len(response.content) > 100
                
                if success:
                    self.log(f"✅ XML export successful: {details['content_length']} bytes")
                    # Save XML for inspection
                    with open(f"test_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml", "wb") as f:
                        f.write(response.content)
                    self.log("   XML file saved for inspection")
                else:
                    self.log(f"⚠️ XML export returned but may be invalid", "WARNING")
                    
                self.record_step("XML Export", success, details, elapsed)
                
                # Also test Excel export
                self.test_excel_export()
                
                return success
            else:
                self.log(f"❌ Failed to export XML: HTTP {response.status_code}", "ERROR")
                self.record_step("XML Export", False, 
                               {"error": f"HTTP {response.status_code}", "response": response.text[:500]}, 
                               elapsed)
                return False
                
        except Exception as e:
            self.log(f"❌ Exception exporting XML: {str(e)}", "ERROR")
            self.record_step("XML Export", False, {"error": str(e)}, 0)
            return False
            
    def test_excel_export(self) -> bool:
        """Test Excel export functionality"""
        self.log("Testing Excel export functionality")
        
        try:
            payload = {
                "scenario": self.scenario_data.get("scenario_a", {}),
                "timeline": self.timeline_data if self.timeline_data else {},
                "project_name": "Test Project Export",
                "session_id": self.session_id
            }
            
            response, elapsed = self.measure_time(
                requests.post,
                f"{self.base_url}/api/export_workbook",
                json=payload
            )
            
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                is_excel = "excel" in content_type.lower() or "spreadsheet" in content_type.lower()
                
                details = {
                    "response_code": response.status_code,
                    "content_type": content_type,
                    "content_length": len(response.content),
                    "is_valid_excel": is_excel
                }
                
                success = is_excel and len(response.content) > 1000
                
                if success:
                    self.log(f"✅ Excel export successful: {details['content_length']} bytes")
                    # Save Excel for inspection
                    with open(f"test_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", "wb") as f:
                        f.write(response.content)
                    self.log("   Excel file saved for inspection")
                else:
                    self.log(f"⚠️ Excel export returned but may be invalid", "WARNING")
                    
                self.record_step("Excel Export", success, details, elapsed)
                return success
            else:
                self.log(f"⚠️ Excel export failed: HTTP {response.status_code}", "WARNING")
                return False
                
        except Exception as e:
            self.log(f"⚠️ Exception exporting Excel: {str(e)}", "WARNING")
            return False
            
    def generate_report(self):
        """Generate comprehensive test report"""
        self.log("\n" + "="*80)
        self.log("COMPREHENSIVE TEST REPORT")
        self.log("="*80)
        
        # Calculate metrics
        total_steps = len(self.results["steps"])
        successful_steps = sum(1 for step in self.results["steps"] if step["success"])
        failed_steps = total_steps - successful_steps
        total_time = sum(step["elapsed_time_seconds"] for step in self.results["steps"])
        
        self.results["metrics"] = {
            "total_steps": total_steps,
            "successful_steps": successful_steps,
            "failed_steps": failed_steps,
            "success_rate": (successful_steps / total_steps * 100) if total_steps > 0 else 0,
            "total_execution_time": round(total_time, 3),
            "average_step_time": round(total_time / total_steps, 3) if total_steps > 0 else 0
        }
        
        # Determine overall status
        self.results["status"] = "success" if failed_steps == 0 else "partial_failure"
        self.results["end_time"] = datetime.now().isoformat()
        
        # Print summary
        print("\n📊 TEST EXECUTION SUMMARY")
        print("-" * 40)
        print(f"Job ID: {self.job_id}")
        print(f"Session ID: {self.session_id}")
        print(f"Total Steps: {total_steps}")
        print(f"✅ Successful: {successful_steps}")
        print(f"❌ Failed: {failed_steps}")
        print(f"Success Rate: {self.results['metrics']['success_rate']:.1f}%")
        print(f"Total Time: {total_time:.2f} seconds")
        print(f"Average Time per Step: {self.results['metrics']['average_step_time']:.2f} seconds")
        
        print("\n📝 STEP-BY-STEP RESULTS")
        print("-" * 40)
        for i, step in enumerate(self.results["steps"], 1):
            status_icon = "✅" if step["success"] else "❌"
            print(f"{i}. {status_icon} {step['name']}")
            print(f"   Time: {step['elapsed_time_seconds']}s")
            if not step["success"] and "error" in step["details"]:
                print(f"   Error: {step['details']['error']}")
            else:
                for key, value in step["details"].items():
                    if key not in ["response_code", "error", "response"]:
                        print(f"   {key}: {value}")
        
        print("\n🔍 PERFORMANCE METRICS")
        print("-" * 40)
        # Find slowest operations
        sorted_steps = sorted(self.results["steps"], key=lambda x: x["elapsed_time_seconds"], reverse=True)
        print("Slowest Operations:")
        for step in sorted_steps[:3]:
            print(f"  - {step['name']}: {step['elapsed_time_seconds']}s")
        
        print("\n📋 ISSUES FOUND")
        print("-" * 40)
        if self.results.get("issues"):
            for issue in self.results["issues"]:
                print(f"  - {issue}")
        else:
            print("  No critical issues found")
        
        # Save full report to file
        report_filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Full report saved to: {report_filename}")
        
        # Final verdict
        print("\n" + "="*80)
        if self.results["status"] == "success":
            print("🎉 ALL TESTS PASSED SUCCESSFULLY!")
            print("✅ The application is fully functional from start to finish")
        else:
            print("⚠️ TESTS COMPLETED WITH SOME FAILURES")
            print("Please review the failed steps above")
        print("="*80)
        
        return self.results
        
    def run_all_tests(self):
        """Run complete end-to-end test flow"""
        self.log("Starting End-to-End Flow Test", "INFO")
        self.log(f"Job ID: {self.job_id}")
        self.log(f"Session ID: {self.session_id}")
        self.log("-" * 50)
        
        # Run test sequence
        tests = [
            ("Job Status Check", self.test_job_status),
            ("Scenario Creation", self.test_create_scenario),
            ("Pricing Calculations", self.test_pricing_calculations),
            ("Timeline Generation", self.test_timeline_generation),
            ("XML Export", self.test_xml_export)
        ]
        
        all_passed = True
        for test_name, test_func in tests:
            self.log(f"\n🔄 Running: {test_name}")
            try:
                passed = test_func()
                if not passed:
                    all_passed = False
                    self.log(f"⚠️ {test_name} did not pass completely", "WARNING")
            except Exception as e:
                self.log(f"❌ {test_name} failed with exception: {str(e)}", "ERROR")
                all_passed = False
        
        # Generate and return report
        report = self.generate_report()
        return all_passed, report


def main():
    """Main test execution"""
    print("\n" + "="*80)
    print("AGENCY PROJECT BUILDER - END-TO-END FLOW TEST")
    print("="*80)
    print(f"Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {BASE_URL}")
    print("-"*80)
    
    # Check if server is running
    try:
        health = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if health.status_code != 200:
            print("❌ Server is not responding properly")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to server at {BASE_URL}: {e}")
        print("Please ensure the FastAPI server is running on port 5000")
        sys.exit(1)
    
    # Run tests
    tester = APBFlowTester()
    all_passed, report = tester.run_all_tests()
    
    # Return appropriate exit code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()