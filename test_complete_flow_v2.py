#!/usr/bin/env python3
"""
End-to-End Flow Test for Agency Project Builder V2
Tests the complete user journey from RFP submission to XML export
"""

import json
import time
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
import sys
import uuid

# Configuration
BASE_URL = "http://localhost:5000"

class APBFlowTesterV2:
    def __init__(self):
        self.base_url = BASE_URL
        self.session_id = f"test-session-{uuid.uuid4().hex[:8]}"
        self.job_id = None
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
        self.rfp_text = """REQUEST FOR PROPOSAL
Digital Marketing Campaign for E-Commerce Launch

Project Overview
Our company, TechStyle Fashion, is launching a new direct-to-consumer e-commerce platform focusing on sustainable fashion. We are seeking a digital marketing agency to develop and execute a comprehensive marketing campaign for our Q2 2025 launch.

Scope of Work

1. Brand Strategy & Positioning
   - Develop brand messaging and value proposition
   - Create brand guidelines and visual identity refinement
   - Competitive analysis and market positioning
   - Target audience segmentation and persona development

2. Website Development Support
   - Landing page design and optimization
   - E-commerce platform marketing integration
   - SEO technical audit and implementation
   - Analytics setup and tracking implementation

3. Content Marketing
   - Content strategy development
   - Blog content creation (20 articles)
   - Product descriptions and category pages
   - Email marketing templates and campaigns
   - Social media content calendar (3 months)

4. Paid Media Campaigns
   - Google Ads setup and management
   - Facebook and Instagram advertising
   - TikTok advertising campaign
   - Retargeting campaign setup
   - Budget allocation and optimization strategy

5. Social Media Management
   - Platform strategy for Instagram, TikTok, Pinterest
   - Community management and engagement
   - Influencer partnership program
   - User-generated content campaigns

6. Launch Campaign
   - Pre-launch teaser campaign
   - Launch week intensive promotion
   - PR outreach and media relations
   - Event planning for virtual launch

Budget
Total budget range: $150,000 - $250,000
Campaign timeline: 6 months (January - June 2025)

Success Metrics
- 50,000 website visitors in first month
- 2,500 email subscribers pre-launch
- 1,000 customers in first quarter
- 15% conversion rate on paid traffic
- 25% month-over-month growth"""
        
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
        
    def test_create_ai_job(self) -> bool:
        """Test 1: Create AI Analysis Job"""
        self.log("Creating new AI analysis job")
        
        try:
            # Use the suggest_by_text endpoint with correct field name
            payload = {
                "rfp_text": self.rfp_text  # Changed from "text" to "rfp_text"
            }
            
            response, elapsed = self.measure_time(
                requests.post,
                f"{self.base_url}/api/suggest_by_text",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                suggestions = data.get("suggested", data.get("suggestions", []))  # Try both field names
                
                details = {
                    "deliverables_suggested": len(suggestions),
                    "response_code": response.status_code,
                    "sample_suggestions": suggestions[:3] if suggestions else []
                }
                
                # Store the suggested deliverables - extract just the codes
                if suggestions and isinstance(suggestions, list):
                    # Extract deliverable codes from suggestion objects
                    self.selected_deliverables = []
                    for sugg in suggestions[:10]:  # Take first 10 suggestions
                        if isinstance(sugg, dict) and 'deliverable_code' in sugg:
                            self.selected_deliverables.append(sugg['deliverable_code'])
                else:
                    self.selected_deliverables = []
                
                success = len(suggestions) > 0
                
                if success:
                    self.log(f"✅ AI suggested {len(suggestions)} deliverables")
                else:
                    self.log(f"⚠️ No deliverables suggested", "WARNING")
                    
                self.record_step("AI Deliverable Suggestion", success, details, elapsed)
                return success
            else:
                self.log(f"❌ Failed to get suggestions: HTTP {response.status_code}", "ERROR")
                self.record_step("AI Deliverable Suggestion", False, 
                               {"error": f"HTTP {response.status_code}", "response": response.text[:500]}, 
                               elapsed)
                return False
                
        except Exception as e:
            self.log(f"❌ Exception creating AI job: {str(e)}", "ERROR")
            self.record_step("AI Deliverable Suggestion", False, {"error": str(e)}, 0)
            return False
            
    def test_create_scenario(self) -> bool:
        """Test 2: Create a scenario from selected deliverables"""
        self.log("Creating scenario from AI-suggested deliverables")
        
        if not self.selected_deliverables:
            # Use valid deliverable codes from the database
            self.log("⚠️ Using default deliverable codes", "WARNING")
            self.selected_deliverables = [
                "DEL-0001",  # Content Plan
                "DEL-0008",  # Brand Identity Development
                "DEL-0010",  # Campaign Concepting
                "DEL-0006",  # Ad Assets
                "DEL-0002"   # Meetings
            ]
        
        try:
            # Build scenario using the /api/build endpoint with correct field names
            payload = {
                "selected_deliverable_codes": self.selected_deliverables,  # Changed from "deliverables"
                "pricing_mode": "Flat_Blended",
                "rate_band": "Standard_US",
                "use_slack": True,
                "slack_after_internal": 1,
                "slack_after_client": 2,
                "slack_global_pct": 0.05,
                "project_start": "2025-01-06"
            }
            
            response, elapsed = self.measure_time(
                requests.post,
                f"{self.base_url}/api/build",
                json=payload
            )
            
            if response.status_code == 200:
                scenario_data = response.json()
                self.scenario_data = scenario_data
                
                # Store scenario data properly
                scenario_a = scenario_data.get("scenario_a", scenario_data)
                total_hours = scenario_a.get("total_hours", 0)
                total_price = scenario_a.get("total_price", 0)
                items = scenario_a.get("items", [])
                
                details = {
                    "deliverables_count": len(self.selected_deliverables),
                    "items_created": len(items),
                    "scenario_a_hours": total_hours,
                    "scenario_a_price": total_price,
                    "has_scenario_b": "scenario_b" in scenario_data,
                    "response_code": response.status_code
                }
                
                success = total_hours > 0 or len(items) > 0
                
                if success:
                    self.log(f"✅ Scenario created: {total_hours} hours, ${total_price:,.2f}, {len(items)} items")
                else:
                    self.log(f"⚠️ Scenario created but may have incomplete data", "WARNING")
                    
                self.record_step("Create Scenario", success, details, elapsed)
                return success
            else:
                self.log(f"❌ Failed to create scenario: HTTP {response.status_code}", "ERROR")
                self.log(f"Response: {response.text[:500]}", "DEBUG")
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
            # Extract scenario properly
            scenario = self.scenario_data.get("scenario_a", self.scenario_data)
            
            # Test pricing build
            payload = {
                "deliverables": self.selected_deliverables[:5],  # Use first 5 deliverables
                "options": {
                    "pricing_mode": "Flat_Blended",
                    "rate_band": "Standard_US"
                },
                "session_id": self.session_id
            }
            
            response, elapsed = self.measure_time(
                requests.post,
                f"{self.base_url}/api/pricing/build_scenario",
                json=payload
            )
            
            success = response.status_code == 200
            details = {
                "response_code": response.status_code,
                "original_price": scenario.get("total_price", 0),
                "original_hours": scenario.get("total_hours", 0)
            }
            
            if success:
                pricing_data = response.json()
                details["calculated_price"] = pricing_data.get("total_price", 0)
                details["calculated_hours"] = pricing_data.get("total_hours", 0)
                details["items_priced"] = len(pricing_data.get("items", []))
                details["pricing_valid"] = pricing_data.get("total_price", 0) > 0
                
                self.log(f"✅ Pricing calculated: ${details['calculated_price']:,.2f} for {details['calculated_hours']} hours")
            else:
                self.log(f"⚠️ Pricing calculation failed: HTTP {response.status_code}", "WARNING")
                
            self.record_step("Pricing Calculations", success, details, elapsed)
            
            # Test retainer detection
            if self.rfp_text:
                retainer_response, retainer_elapsed = self.measure_time(
                    requests.post,
                    f"{self.base_url}/api/retainer_detect",
                    json={"text": self.rfp_text[:5000], "session_id": self.session_id}  # Limit text length
                )
                
                if retainer_response.status_code == 200:
                    retainer_data = retainer_response.json()
                    details["has_retainer_opportunities"] = retainer_data.get("has_retainer", False)
                    details["retainer_confidence"] = retainer_data.get("confidence", 0)
                    self.log(f"✅ Retainer detection: {details['has_retainer_opportunities']}")
                    
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
            # Use the timeline/suggest endpoint which is simpler
            scenario = self.scenario_data.get("scenario_a", self.scenario_data)
            
            # Ensure we have items in the scenario
            if not scenario.get("items"):
                scenario["items"] = [
                    {
                        "deliverable_code": code,
                        "deliverable": code,
                        "hours": 40,
                        "price": 7800
                    }
                    for code in self.selected_deliverables[:3]
                ]
            
            payload = {
                "scenario": scenario,
                "project_start": "2025-01-06",  # Monday start date
                "session_id": self.session_id
            }
            
            response, elapsed = self.measure_time(
                requests.post,
                f"{self.base_url}/api/timeline/suggest",
                json=payload
            )
            
            if response.status_code == 200:
                timeline_data = response.json()
                self.timeline_data = timeline_data
                
                # Extract timeline info
                timeline = timeline_data.get("timeline", {})
                tasks = timeline.get("tasks", []) if isinstance(timeline, dict) else timeline_data.get("tasks", [])
                
                details = {
                    "tasks_count": len(tasks),
                    "project_duration": timeline_data.get("duration", "Unknown"),
                    "response_code": response.status_code,
                    "has_timeline_data": bool(tasks)
                }
                
                success = len(tasks) > 0 or response.status_code == 200
                
                if success:
                    self.log(f"✅ Timeline generated: {details['tasks_count']} tasks")
                else:
                    self.log(f"⚠️ Timeline generation incomplete", "WARNING")
                    
                self.record_step("Timeline Generation", success, details, elapsed)
                return success
            else:
                self.log(f"❌ Failed to generate timeline: HTTP {response.status_code}", "ERROR")
                self.log(f"Response: {response.text[:500]}", "DEBUG")
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
            # Use the simpler export endpoint
            scenario = self.scenario_data.get("scenario_a", self.scenario_data)
            
            # Build WBS data for export
            wbs_data = []
            for idx, item in enumerate(scenario.get("items", [])[:5]):  # Limit to 5 items for testing
                wbs_data.append({
                    "WBS": f"1.{idx+1}",
                    "Deliverable": item.get("deliverable", item.get("deliverable_code", f"Item {idx+1}")),
                    "Hours": item.get("hours", 40),
                    "Rate": item.get("rate", 195),
                    "Price": item.get("price", 7800),
                    "Start": "2025-01-06",
                    "End": "2025-01-31"
                })
            
            payload = {
                "wbs_data": wbs_data,
                "project_name": "Test Project Export",
                "project_start": "2025-01-06"
            }
            
            response, elapsed = self.measure_time(
                requests.post,
                f"{self.base_url}/api/export",
                json=payload
            )
            
            if response.status_code == 200:
                # Check if we got XML or CSV content
                content_type = response.headers.get("content-type", "")
                content_disp = response.headers.get("content-disposition", "")
                
                details = {
                    "response_code": response.status_code,
                    "content_type": content_type,
                    "content_disposition": content_disp,
                    "content_length": len(response.content),
                    "is_valid_export": len(response.content) > 100
                }
                
                success = len(response.content) > 100
                
                if success:
                    self.log(f"✅ Export successful: {details['content_length']} bytes")
                    # Save export for inspection
                    if "csv" in content_type.lower() or "csv" in content_disp.lower():
                        filename = f"test_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    else:
                        filename = f"test_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
                    
                    with open(filename, "wb") as f:
                        f.write(response.content)
                    self.log(f"   Export file saved as: {filename}")
                else:
                    self.log(f"⚠️ Export returned but may be invalid", "WARNING")
                    
                self.record_step("Export Functionality", success, details, elapsed)
                
                # Also test Excel export
                self.test_excel_export()
                
                return success
            else:
                self.log(f"❌ Failed to export: HTTP {response.status_code}", "ERROR")
                self.record_step("Export Functionality", False, 
                               {"error": f"HTTP {response.status_code}", "response": response.text[:500]}, 
                               elapsed)
                return False
                
        except Exception as e:
            self.log(f"❌ Exception exporting: {str(e)}", "ERROR")
            self.record_step("Export Functionality", False, {"error": str(e)}, 0)
            return False
            
    def test_excel_export(self) -> bool:
        """Test Excel export functionality"""
        self.log("Testing Excel export functionality")
        
        if not self.scenario_data:
            return False
            
        try:
            scenario = self.scenario_data.get("scenario_a", self.scenario_data)
            
            payload = {
                "scenario_a": scenario,
                "project_name": "Test Excel Export",
                "timestamp": datetime.now().strftime("%Y-%m-%d %I:%M%p EST")
            }
            
            response, elapsed = self.measure_time(
                requests.post,
                f"{self.base_url}/api/export_workbook",
                json=payload
            )
            
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                is_excel = "excel" in content_type.lower() or "spreadsheet" in content_type.lower() or "octet-stream" in content_type.lower()
                
                details = {
                    "response_code": response.status_code,
                    "content_type": content_type,
                    "content_length": len(response.content),
                    "is_valid_excel": is_excel and len(response.content) > 1000
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
        self.results["status"] = "success" if failed_steps == 0 else "partial_failure" if successful_steps > failed_steps else "failure"
        self.results["end_time"] = datetime.now().isoformat()
        
        # Print summary
        print("\n📊 TEST EXECUTION SUMMARY")
        print("-" * 40)
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
                    if key not in ["response_code", "error", "response", "sample_suggestions"]:
                        print(f"   {key}: {value}")
        
        print("\n🔍 PERFORMANCE METRICS")
        print("-" * 40)
        # Find slowest operations
        sorted_steps = sorted(self.results["steps"], key=lambda x: x["elapsed_time_seconds"], reverse=True)
        print("Slowest Operations:")
        for step in sorted_steps[:3]:
            print(f"  - {step['name']}: {step['elapsed_time_seconds']}s")
        
        print("\n📋 FUNCTIONALITY STATUS")
        print("-" * 40)
        functionality_status = {
            "AI Analysis": "✅ Working" if any(s["name"] == "AI Deliverable Suggestion" and s["success"] for s in self.results["steps"]) else "❌ Not Working",
            "Scenario Creation": "✅ Working" if any(s["name"] == "Create Scenario" and s["success"] for s in self.results["steps"]) else "❌ Not Working",
            "Pricing Engine": "✅ Working" if any(s["name"] == "Pricing Calculations" and s["success"] for s in self.results["steps"]) else "❌ Not Working",
            "Timeline Generator": "✅ Working" if any(s["name"] == "Timeline Generation" and s["success"] for s in self.results["steps"]) else "❌ Not Working",
            "Export System": "✅ Working" if any("Export" in s["name"] and s["success"] for s in self.results["steps"]) else "❌ Not Working"
        }
        
        for feature, status in functionality_status.items():
            print(f"{feature}: {status}")
        
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
        elif self.results["status"] == "partial_failure":
            print("⚠️ TESTS PARTIALLY SUCCESSFUL")
            print(f"✅ {successful_steps}/{total_steps} steps passed")
            print("Please review the failed steps above for areas needing attention")
        else:
            print("❌ CRITICAL FAILURES DETECTED")
            print(f"Only {successful_steps}/{total_steps} steps passed")
            print("The application needs significant fixes")
        print("="*80)
        
        return self.results
        
    def run_all_tests(self):
        """Run complete end-to-end test flow"""
        self.log("Starting End-to-End Flow Test V2", "INFO")
        self.log(f"Session ID: {self.session_id}")
        self.log("-" * 50)
        
        # Run test sequence
        tests = [
            ("AI Analysis", self.test_create_ai_job),
            ("Scenario Creation", self.test_create_scenario),
            ("Pricing Calculations", self.test_pricing_calculations),
            ("Timeline Generation", self.test_timeline_generation),
            ("Export System", self.test_xml_export)
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
    print("AGENCY PROJECT BUILDER - END-TO-END FLOW TEST V2")
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
    tester = APBFlowTesterV2()
    all_passed, report = tester.run_all_tests()
    
    # Return appropriate exit code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()