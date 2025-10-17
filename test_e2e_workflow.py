#!/usr/bin/env python3
"""
COMPREHENSIVE END-TO-END TEST
St. Regis Nashville RFP Workflow Test
Tests all 4 steps of the workflow with detailed reporting
"""

import requests
import json
import time
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:5000"
PDF_PATH = "attached_assets/St.Regis_Nashville_ Branding Agency RFP_10.22.2024_1760738776363.pdf"

class WorkflowTest:
    def __init__(self):
        self.results = {
            "step1": {"status": "pending", "details": {}},
            "step2": {"status": "pending", "details": {}},
            "step3": {"status": "pending", "details": {}},
            "step4": {"status": "pending", "details": {}},
        }
        self.start_time = time.time()
        self.scenario_data = None
        
    def log(self, message):
        """Log with timestamp"""
        elapsed = time.time() - self.start_time
        print(f"[{elapsed:.1f}s] {message}")
    
    def test_step1_upload_and_analysis(self):
        """Step 1: Upload RFP PDF and verify AI analysis"""
        self.log("=" * 80)
        self.log("STEP 1: Upload & Analysis")
        self.log("=" * 80)
        
        try:
            # Check if PDF exists
            if not Path(PDF_PATH).exists():
                raise FileNotFoundError(f"PDF not found: {PDF_PATH}")
            
            # Upload PDF
            self.log(f"Uploading PDF: {PDF_PATH}")
            with open(PDF_PATH, 'rb') as f:
                files = {'file': (Path(PDF_PATH).name, f, 'application/pdf')}
                data = {'analyze': 'true', 'mode': 'deep'}
                
                response = requests.post(
                    f"{BASE_URL}/api/upload_rfp",
                    files=files,
                    data=data,
                    timeout=180
                )
            
            self.log(f"Upload response status: {response.status_code}")
            
            if response.status_code != 200:
                raise Exception(f"Upload failed: {response.status_code} - {response.text[:200]}")
            
            result = response.json()
            self.log(f"Upload successful: {result.get('filename')}")
            
            # Check for job_id (async analysis)
            if 'job_id' in result:
                job_id = result['job_id']
                self.log(f"Analysis job created: {job_id}")
                
                # Poll for analysis completion
                max_wait = 300  # 5 minutes
                poll_start = time.time()
                
                while time.time() - poll_start < max_wait:
                    job_response = requests.get(f"{BASE_URL}/api/ai/jobs/{job_id}")
                    self.log(f"Job status check: {job_response.status_code}")
                    
                    if job_response.status_code == 404:
                        self.results["step1"]["status"] = "FAIL"
                        self.results["step1"]["details"] = {
                            "error": "404 on job polling - SSE_JOB_STORE issue",
                            "job_id": job_id,
                            "http_status": 404
                        }
                        self.log("❌ FAIL: 404 error on job polling!")
                        return False
                    
                    if job_response.status_code == 200:
                        job_data = job_response.json()
                        status = job_data.get('status')
                        self.log(f"Job status: {status}")
                        
                        if status in ['completed', 'success']:
                            deliverables = job_data.get('result', {}).get('deliverables', [])
                            self.log(f"✅ Analysis complete! Found {len(deliverables)} deliverables")
                            
                            self.results["step1"]["status"] = "PASS"
                            self.results["step1"]["details"] = {
                                "http_status": 200,
                                "job_id": job_id,
                                "deliverables_count": len(deliverables),
                                "deliverables": deliverables[:3]  # Sample
                            }
                            return True
                        
                        elif status == 'failed':
                            raise Exception(f"Analysis job failed: {job_data.get('error')}")
                    
                    time.sleep(2)
                
                raise Exception("Analysis timeout after 5 minutes")
            
            # Check for immediate deliverables (sync response)
            elif 'deliverables' in result:
                deliverables = result['deliverables']
                self.log(f"✅ Analysis complete! Found {len(deliverables)} deliverables")
                
                self.results["step1"]["status"] = "PASS"
                self.results["step1"]["details"] = {
                    "http_status": 200,
                    "deliverables_count": len(deliverables),
                    "deliverables": deliverables[:3]
                }
                return True
            
            else:
                raise Exception("No job_id or deliverables in response")
                
        except Exception as e:
            self.log(f"❌ FAIL: {str(e)}")
            self.results["step1"]["status"] = "FAIL"
            self.results["step1"]["details"] = {"error": str(e)}
            return False
    
    def test_step2_build_scenario(self):
        """Step 2: Build pricing scenario with 5-8 deliverables"""
        self.log("\n" + "=" * 80)
        self.log("STEP 2: Build Pricing Scenario")
        self.log("=" * 80)
        
        try:
            # Get available deliverables
            self.log("Fetching available deliverables...")
            response = requests.get(f"{BASE_URL}/api/options")
            
            if response.status_code != 200:
                raise Exception(f"Failed to get options: {response.status_code}")
            
            options = response.json()
            deliverables = options.get('deliverables', [])
            self.log(f"Found {len(deliverables)} deliverables")
            
            # Select 6 deliverables across different departments
            selected = []
            departments_used = set()
            
            for deliv in deliverables:
                # Extract deliverable code (the key field for the API)
                deliv_code = deliv.get('Deliverable_Code', deliv.get('code', ''))
                deliv_name = deliv.get('Deliverable', deliv.get('name', deliv_code))
                dept = deliv.get('Department', deliv.get('department', 'Unknown'))
                
                if dept not in departments_used and len(selected) < 6 and deliv_code:
                    selected.append(deliv_code)
                    departments_used.add(dept)
                    self.log(f"  - Selected: {deliv_name} ({deliv_code}, {dept})")
            
            if len(selected) < 5:
                # If not enough from different departments, just take first 6
                selected = []
                for d in deliverables[:6]:
                    deliv_code = d.get('Deliverable_Code', d.get('code', ''))
                    if deliv_code:
                        selected.append(deliv_code)
            
            self.log(f"Building scenario with {len(selected)} deliverable codes")
            
            # Build scenario payload with correct structure
            payload = {
                "session_id": "test_e2e_session",
                "selection": {
                    "deliverable_codes": selected,
                    "components_map": {},  # Empty for basic test
                    "l3_map": {}           # Empty for basic test
                },
                "project_name": "St. Regis Nashville E2E Test",
                "pricing_mode": "Flat_Blended",
                "blended_rate": 195.0,
                "rate_band": "Standard_US"
            }
            
            response = requests.post(
                f"{BASE_URL}/api/pricing/build_scenario",
                json=payload,
                timeout=60
            )
            
            self.log(f"Build scenario response: {response.status_code}")
            
            if response.status_code == 500:
                self.results["step2"]["status"] = "FAIL"
                self.results["step2"]["details"] = {
                    "error": "500 error - BuildScenarioPayload issue",
                    "http_status": 500,
                    "response": response.text[:500]
                }
                self.log("❌ FAIL: 500 error on build_scenario!")
                return False
            
            if response.status_code != 200:
                raise Exception(f"Build scenario failed: {response.status_code} - {response.text[:200]}")
            
            self.scenario_data = response.json()
            
            # Verify response structure
            if 'scenario' not in self.scenario_data:
                raise Exception("No 'scenario' key in response")
            
            scenario = self.scenario_data['scenario']
            
            self.log(f"✅ Scenario built successfully!")
            self.log(f"   Project: {scenario.get('project_name', 'N/A')}")
            self.log(f"   Items: {len(scenario.get('items', []))}")
            
            self.results["step2"]["status"] = "PASS"
            self.results["step2"]["details"] = {
                "http_status": 200,
                "deliverables_selected": len(selected),
                "items_count": len(scenario.get('items', [])),
                "project_name": scenario.get('project_name')
            }
            return True
            
        except Exception as e:
            self.log(f"❌ FAIL: {str(e)}")
            self.results["step2"]["status"] = "FAIL"
            self.results["step2"]["details"] = {"error": str(e)}
            return False
    
    def test_step3_verify_structure(self):
        """Step 3: Verify pricing data structure"""
        self.log("\n" + "=" * 80)
        self.log("STEP 3: Verify Pricing Data Structure")
        self.log("=" * 80)
        
        try:
            if not self.scenario_data:
                raise Exception("No scenario data from Step 2")
            
            scenario = self.scenario_data['scenario']
            items = scenario.get('items', [])
            
            self.log(f"Verifying {len(items)} items...")
            
            # Check hierarchy
            has_deliverables = False
            has_components = False
            has_tasks = False
            
            deliverable_count = 0
            component_count = 0
            task_count = 0
            
            for item in items:
                item_type = item.get('type', '').lower()
                
                if 'deliverable' in item_type or item.get('level') == 1:
                    has_deliverables = True
                    deliverable_count += 1
                elif 'component' in item_type or item.get('level') == 2:
                    has_components = True
                    component_count += 1
                elif 'task' in item_type or item.get('level') == 3:
                    has_tasks = True
                    task_count += 1
            
            self.log(f"  Deliverables: {deliverable_count}")
            self.log(f"  Components: {component_count}")
            self.log(f"  Tasks: {task_count}")
            
            # Check totals
            total_hours = scenario.get('total_hours', 0)
            total_cost = scenario.get('total_cost', 0)
            
            self.log(f"  Total Hours: {total_hours}")
            self.log(f"  Total Cost: ${total_cost:,.2f}")
            
            # Verify structure
            checks = []
            checks.append(("Has deliverables", has_deliverables))
            checks.append(("Has components", has_components))
            checks.append(("Has tasks", has_tasks))
            checks.append(("Has total hours", total_hours > 0))
            checks.append(("Has total cost", total_cost > 0))
            checks.append(("Items array not empty", len(items) > 0))
            
            all_passed = all(check[1] for check in checks)
            
            for check_name, passed in checks:
                status = "✅" if passed else "❌"
                self.log(f"  {status} {check_name}")
            
            if all_passed:
                self.log("✅ All structure checks passed!")
                self.results["step3"]["status"] = "PASS"
                self.results["step3"]["details"] = {
                    "deliverable_count": deliverable_count,
                    "component_count": component_count,
                    "task_count": task_count,
                    "total_hours": total_hours,
                    "total_cost": total_cost
                }
                return True
            else:
                raise Exception("Some structure checks failed")
                
        except Exception as e:
            self.log(f"❌ FAIL: {str(e)}")
            self.results["step3"]["status"] = "FAIL"
            self.results["step3"]["details"] = {"error": str(e)}
            return False
    
    def test_step4_generate_timeline(self):
        """Step 4: Generate timeline and verify job polling works"""
        self.log("\n" + "=" * 80)
        self.log("STEP 4: Generate Timeline")
        self.log("=" * 80)
        
        try:
            if not self.scenario_data:
                raise Exception("No scenario data from Step 2")
            
            # Generate timeline
            self.log("Calling /api/ai/generate_timeline...")
            
            response = requests.post(
                f"{BASE_URL}/api/ai/generate_timeline",
                json=self.scenario_data,
                timeout=30
            )
            
            self.log(f"Generate timeline response: {response.status_code}")
            
            if response.status_code != 200:
                raise Exception(f"Generate timeline failed: {response.status_code} - {response.text[:200]}")
            
            result = response.json()
            job_id = result.get('job_id')
            
            if not job_id:
                raise Exception("No job_id in response")
            
            self.log(f"Timeline job created: {job_id}")
            
            # Poll for completion
            max_wait = 600  # 10 minutes for timeline generation
            poll_start = time.time()
            poll_count = 0
            found_404 = False
            
            while time.time() - poll_start < max_wait:
                poll_count += 1
                job_response = requests.get(f"{BASE_URL}/api/ai/jobs/{job_id}")
                
                self.log(f"Poll #{poll_count}: Status {job_response.status_code}")
                
                # Check for 404 error
                if job_response.status_code == 404:
                    found_404 = True
                    self.log(f"❌ FAIL: 404 error on job polling! (SSE_JOB_STORE issue)")
                    self.results["step4"]["status"] = "FAIL"
                    self.results["step4"]["details"] = {
                        "error": "404 on job polling - SSE_JOB_STORE not working",
                        "job_id": job_id,
                        "http_status": 404,
                        "poll_attempts": poll_count
                    }
                    return False
                
                if job_response.status_code == 200:
                    job_data = job_response.json()
                    status = job_data.get('status')
                    progress = job_data.get('progress', 0)
                    
                    self.log(f"  Status: {status}, Progress: {progress}%")
                    
                    if status in ['completed', 'success']:
                        timeline_data = job_data.get('result', {})
                        
                        self.log(f"✅ Timeline generated successfully!")
                        self.log(f"   Timeline items: {len(timeline_data.get('items', []))}")
                        
                        self.results["step4"]["status"] = "PASS"
                        self.results["step4"]["details"] = {
                            "http_status": 200,
                            "job_id": job_id,
                            "poll_attempts": poll_count,
                            "no_404_errors": True,
                            "timeline_items": len(timeline_data.get('items', [])),
                            "generation_time": time.time() - poll_start
                        }
                        return True
                    
                    elif status == 'failed':
                        raise Exception(f"Timeline job failed: {job_data.get('error')}")
                
                time.sleep(3)
            
            raise Exception("Timeline generation timeout after 10 minutes")
            
        except Exception as e:
            self.log(f"❌ FAIL: {str(e)}")
            self.results["step4"]["status"] = "FAIL"
            self.results["step4"]["details"] = {"error": str(e)}
            return False
    
    def print_final_report(self):
        """Print comprehensive final report"""
        elapsed = time.time() - self.start_time
        
        print("\n" + "=" * 80)
        print("FINAL COMPREHENSIVE TEST REPORT")
        print("=" * 80)
        print(f"Total Execution Time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print()
        
        # Step-by-step results
        for step_num in range(1, 5):
            step_key = f"step{step_num}"
            result = self.results[step_key]
            status = result['status']
            
            status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⏸️"
            
            print(f"{status_icon} STEP {step_num}: {status}")
            
            if result['details']:
                for key, value in result['details'].items():
                    if key != 'error':
                        print(f"   {key}: {value}")
                if 'error' in result['details']:
                    print(f"   ERROR: {result['details']['error']}")
            print()
        
        # Overall assessment
        print("=" * 80)
        print("SUCCESS CRITERIA EVALUATION:")
        print("=" * 80)
        
        all_200_ok = all(
            self.results[f"step{i}"]["details"].get("http_status") == 200
            for i in range(1, 5)
            if self.results[f"step{i}"]["status"] == "PASS"
        )
        
        no_500_errors = not any(
            self.results[f"step{i}"]["details"].get("http_status") == 500
            for i in range(1, 5)
        )
        
        no_404_errors = not any(
            self.results[f"step{i}"]["details"].get("http_status") == 404
            for i in range(1, 5)
        )
        
        no_timeouts = not any(
            'timeout' in str(self.results[f"step{i}"]["details"].get("error", "")).lower()
            for i in range(1, 5)
        )
        
        all_steps_passed = all(
            self.results[f"step{i}"]["status"] == "PASS"
            for i in range(1, 5)
        )
        
        print(f"{'✅' if all_200_ok else '❌'} All endpoints return 200 OK")
        print(f"{'✅' if no_500_errors else '❌'} NO 500 errors (BuildScenarioPayload fix working)")
        print(f"{'✅' if no_404_errors else '❌'} NO 404 errors on job polling (SSE_JOB_STORE fix working)")
        print(f"{'✅' if no_timeouts else '❌'} NO timeouts or hanging")
        print(f"{'✅' if all_steps_passed else '❌'} Complete data flows through all 4 steps")
        print()
        
        # Production readiness
        print("=" * 80)
        print("PRODUCTION READINESS ASSESSMENT:")
        print("=" * 80)
        
        if all_steps_passed and no_500_errors and no_404_errors and no_timeouts:
            print("✅ PRODUCTION READY")
            print("   All workflow steps completed successfully")
            print("   No critical errors detected")
            print("   System is ready for user testing")
        else:
            print("❌ NOT PRODUCTION READY")
            print("   Issues found that need to be addressed:")
            
            if not all_steps_passed:
                failed_steps = [i for i in range(1, 5) if self.results[f"step{i}"]["status"] != "PASS"]
                print(f"   - Failed steps: {', '.join(f'Step {i}' for i in failed_steps)}")
            
            if not no_500_errors:
                print("   - 500 errors detected (BuildScenarioPayload issue)")
            
            if not no_404_errors:
                print("   - 404 errors on job polling (SSE_JOB_STORE issue)")
            
            if not no_timeouts:
                print("   - Timeout issues detected")
        
        print("=" * 80)
        
        return all_steps_passed and no_500_errors and no_404_errors and no_timeouts

def main():
    print("=" * 80)
    print("ST. REGIS NASHVILLE RFP - COMPREHENSIVE END-TO-END WORKFLOW TEST")
    print("=" * 80)
    print()
    
    test = WorkflowTest()
    
    # Run all steps
    step1_ok = test.test_step1_upload_and_analysis()
    step2_ok = test.test_step2_build_scenario() if step1_ok else False
    step3_ok = test.test_step3_verify_structure() if step2_ok else False
    step4_ok = test.test_step4_generate_timeline() if step3_ok else False
    
    # Print final report
    production_ready = test.print_final_report()
    
    # Return exit code
    return 0 if production_ready else 1

if __name__ == "__main__":
    exit(main())
