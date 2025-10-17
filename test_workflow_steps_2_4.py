#!/usr/bin/env python3
"""
End-to-End Workflow Test: Steps 2-4
Tests build_scenario, pricing verification, and timeline generation
"""

import os
import requests
import json
import time
import uuid
from datetime import datetime, date
from typing import Dict, Any, List, Optional

# Configuration
BASE_URL = "http://localhost:5000"
SESSION_ID = str(uuid.uuid4())
PROJECT_NAME = "St. Regis Nashville - Branding Agency"
PROJECT_START = date.today().isoformat()

class WorkflowTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session_id = SESSION_ID
        self.results = {
            "step2": {},
            "step3": {},
            "step4": {},
            "timing": {},
            "success_criteria": {}
        }
        self.start_time = None
        
    def log(self, message: str, level: str = "INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [{level}] {message}")
        
    def upload_rfp_and_get_deliverables(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Upload St. Regis RFP and get suggested deliverables"""
        self.log(f"Uploading RFP from: {pdf_path}")
        try:
            with open(pdf_path, 'rb') as f:
                files = {'files': ('st_regis.pdf', f, 'application/pdf')}
                response = requests.post(
                    f"{self.base_url}/api/suggest_by_file",
                    files=files,
                    timeout=60
                )
                response.raise_for_status()
                data = response.json()
                
                # Extract deliverables from suggestions
                suggestions = data.get('suggestions', [])
                self.log(f"RFP uploaded successfully - got {len(suggestions)} suggestions")
                
                # If no suggestions, use fallback
                if not suggestions:
                    self.log("No suggestions from RFP, using fallback deliverables", "WARN")
                    return self.get_fallback_deliverables()
                
                # Format as deliverable objects
                deliverables = []
                for sugg in suggestions:
                    deliverables.append({
                        'deliverable_code': sugg.get('deliverable_code', sugg.get('code', '')),
                        'deliverable': sugg.get('deliverable', ''),
                        'category': sugg.get('category', ''),
                        'score': sugg.get('score', 0)
                    })
                
                return deliverables
        except Exception as e:
            self.log(f"Failed to upload RFP: {e}", "ERROR")
            # Fallback to hardcoded deliverables for St. Regis branding project
            self.log("Using fallback deliverable codes for branding project")
            return self.get_fallback_deliverables()
    
    def get_fallback_deliverables(self) -> List[Dict[str, Any]]:
        """Fallback deliverables for branding agency projects - using real database codes"""
        # Real deliverable codes from the database for St. Regis branding project
        fallback_codes = [
            {"deliverable_code": "DEL-0001", "deliverable": "Content Plan", "category": "deck_strategy"},
            {"deliverable_code": "DEL-0008", "deliverable": "Brand Identity Development", "category": "development"},
            {"deliverable_code": "DEL-0009", "deliverable": "Brand Style & Usage Guidelines", "category": "guidelines"},
            {"deliverable_code": "DEL-0011", "deliverable": "Campaign Strategy", "category": "deck_strategy"},
            {"deliverable_code": "DEL-0014", "deliverable": "Marketing Collateral (Asset Prod)", "category": "assets"},
            {"deliverable_code": "DEL-0016", "deliverable": "Paid Media Assets", "category": "assets"},
            {"deliverable_code": "DEL-0018", "deliverable": "Video Assets", "category": "general"},
            {"deliverable_code": "DEL-0019", "deliverable": "Web Assets", "category": "assets"},
        ]
        return fallback_codes
    
    def select_diverse_deliverables(self, deliverables: List[Dict], count: int = 6) -> List[str]:
        """Select diverse deliverables from different departments"""
        self.log(f"Selecting {count} diverse deliverables...")
        
        # Group by department
        by_dept = {}
        for deliv in deliverables:
            dept = deliv.get('category', 'Unknown')
            if dept not in by_dept:
                by_dept[dept] = []
            by_dept[dept].append(deliv)
        
        # Select one from each department until we have enough
        selected = []
        dept_list = list(by_dept.keys())
        idx = 0
        
        while len(selected) < count and dept_list:
            dept = dept_list[idx % len(dept_list)]
            if by_dept[dept]:
                deliv = by_dept[dept].pop(0)
                selected.append(deliv['deliverable_code'])
                self.log(f"  Selected: {deliv['deliverable_code']} ({dept})")
            else:
                dept_list.remove(dept)
            idx += 1
        
        return selected
    
    def step2_build_scenario(self, deliverable_codes: List[str]) -> Dict[str, Any]:
        """Step 2: Build pricing scenario"""
        self.log("=" * 60)
        self.log("STEP 2: BUILD PRICING SCENARIO")
        self.log("=" * 60)
        
        step_start = time.time()
        
        # Build payload
        payload = {
            "session_id": self.session_id,
            "selection": {
                "deliverable_codes": deliverable_codes,
                "components_map": {},  # Will use defaults
                "l3_map": {}  # Will use defaults
            },
            "project_name": PROJECT_NAME,
            "project_start": PROJECT_START,
            "pricing_mode": "Flat_Blended",
            "blended_rate": 195.0,
            "rate_band": "Standard_US"
        }
        
        self.log(f"Payload: {json.dumps(payload, indent=2)}")
        self.log(f"Calling POST /api/pricing/build_scenario...")
        
        try:
            response = requests.post(
                f"{self.base_url}/api/pricing/build_scenario",
                json=payload,
                timeout=30
            )
            
            elapsed = time.time() - step_start
            self.results['timing']['step2'] = elapsed
            
            # Log response
            self.log(f"Response Status: {response.status_code}")
            self.log(f"Response Time: {elapsed:.2f}s")
            
            # Check success criteria #1: NO 500 errors
            if response.status_code == 500:
                self.results['success_criteria']['no_500_on_build_scenario'] = False
                self.log("❌ FAIL: Got 500 error on build_scenario", "ERROR")
                self.log(f"Response: {response.text}", "ERROR")
                return {"error": response.text, "status": 500}
            else:
                self.results['success_criteria']['no_500_on_build_scenario'] = True
                self.log("✅ PASS: No 500 error on build_scenario")
            
            # Parse response
            response.raise_for_status()
            data = response.json()
            
            # Store results
            self.results['step2'] = {
                "status_code": response.status_code,
                "scenario": data.get('scenario'),
                "items_count": len(data.get('scenario', {}).get('items', [])),
                "success": True
            }
            
            self.log(f"✅ Scenario created with {self.results['step2']['items_count']} items")
            return data
            
        except requests.exceptions.HTTPError as e:
            self.log(f"❌ HTTP Error: {e}", "ERROR")
            self.results['step2'] = {"error": str(e), "status_code": response.status_code, "success": False}
            return {"error": str(e)}
        except Exception as e:
            self.log(f"❌ Exception: {e}", "ERROR")
            self.results['step2'] = {"error": str(e), "success": False}
            return {"error": str(e)}
    
    def step3_verify_pricing_data(self, scenario: Dict[str, Any]) -> bool:
        """Step 3: Verify pricing table data structure"""
        self.log("=" * 60)
        self.log("STEP 3: VERIFY PRICING TABLE DATA")
        self.log("=" * 60)
        
        step_start = time.time()
        
        try:
            items = scenario.get('items', [])
            self.log(f"Verifying {len(items)} scenario items...")
            
            # Verification checks
            checks = {
                "has_items": len(items) > 0,
                "has_hierarchy": False,
                "has_hours": False,
                "has_rates": False,
                "has_totals": False,
                "deliverable_count": 0,
                "component_count": 0,
                "task_count": 0
            }
            
            # Analyze items - use actual key names from API
            for item in items:
                # Check hierarchy (using actual API keys)
                if 'Deliverable_Code' in item or 'Deliverable' in item:
                    checks['deliverable_count'] += 1
                if 'Component' in item and item.get('Component'):
                    checks['component_count'] += 1
                if 'Task_Label' in item and item.get('Task_Label'):
                    checks['task_count'] += 1
                
                # Check hours and rates (using actual API keys)
                if 'Planned_Hours' in item:
                    checks['has_hours'] = True
                if 'Rate_USD' in item and item.get('Rate_USD', 0) > 0:
                    checks['has_rates'] = True
            
            # Check if we have proper hierarchy
            checks['has_hierarchy'] = (
                checks['deliverable_count'] > 0 and
                (checks['component_count'] > 0 or checks['task_count'] > 0)
            )
            
            # Check totals in scenario metadata
            scenario_meta = scenario
            if 'hours_sum' in scenario_meta or 'total_hours' in scenario_meta:
                checks['has_totals'] = True
            if 'price_sum' in scenario_meta or 'total_price' in scenario_meta:
                checks['has_totals'] = True
            
            # Log verification results
            self.log(f"Deliverables: {checks['deliverable_count']}")
            self.log(f"Components: {checks['component_count']}")
            self.log(f"Tasks: {checks['task_count']}")
            self.log(f"Has hierarchy: {checks['has_hierarchy']}")
            self.log(f"Has hours: {checks['has_hours']}")
            self.log(f"Has rates: {checks['has_rates']}")
            self.log(f"Has totals: {checks['has_totals']}")
            
            # Overall verification
            all_checks_passed = all([
                checks['has_items'],
                checks['has_hierarchy'],
                checks['has_hours'],
                checks['has_rates']
            ])
            
            elapsed = time.time() - step_start
            self.results['timing']['step3'] = elapsed
            
            self.results['step3'] = {
                "checks": checks,
                "all_passed": all_checks_passed,
                "elapsed": elapsed
            }
            
            if all_checks_passed:
                self.log("✅ PASS: All pricing data verifications passed")
            else:
                self.log("⚠️ PARTIAL: Some verifications failed", "WARN")
            
            return all_checks_passed
            
        except Exception as e:
            self.log(f"❌ Verification failed: {e}", "ERROR")
            self.results['step3'] = {"error": str(e), "success": False}
            return False
    
    def step4_generate_timeline(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Step 4: Generate timeline and monitor job progress"""
        self.log("=" * 60)
        self.log("STEP 4: GENERATE TIMELINE")
        self.log("=" * 60)
        
        step_start = time.time()
        
        # Build timeline payload - extract deliverable codes from scenario items
        deliverable_codes = []
        seen_codes = set()
        for item in scenario.get('items', []):
            code = item.get('Deliverable_Code')
            if code and code not in seen_codes:
                deliverable_codes.append({
                    "deliverable_code": code,
                    "deliverable_name": item.get('Deliverable', code)
                })
                seen_codes.add(code)
        
        payload = {
            "deliverables": deliverable_codes,
            "project_start": PROJECT_START,
            "project_name": PROJECT_NAME,
            "rfp_text": "",  # Optional context
            "use_ai": True,
            "mode": "intelligent"
        }
        
        self.log("Calling POST /api/ai/generate_timeline...")
        
        try:
            # Start timeline generation
            response = requests.post(
                f"{self.base_url}/api/ai/generate_timeline",
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            job_id = data.get('job_id')
            self.log(f"Timeline job started: {job_id}")
            
            if not job_id:
                self.log("❌ No job_id returned", "ERROR")
                self.results['step4'] = {"error": "No job_id", "success": False}
                return {"error": "No job_id"}
            
            # Monitor job progress
            self.log("Monitoring job progress...")
            max_wait = 60  # 60 seconds max
            poll_interval = 1  # 1 second
            elapsed_wait = 0
            last_progress = -1
            got_404 = False
            
            while elapsed_wait < max_wait:
                time.sleep(poll_interval)
                elapsed_wait += poll_interval
                
                # Poll job status
                try:
                    job_response = requests.get(
                        f"{self.base_url}/api/ai/jobs/{job_id}",
                        timeout=5
                    )
                    
                    # Check success criteria #2: NO 404 errors for NEW jobs
                    if job_response.status_code == 404:
                        got_404 = True
                        self.log(f"❌ Got 404 for job {job_id} (elapsed: {elapsed_wait}s)", "ERROR")
                        self.results['success_criteria']['no_404_on_job_status'] = False
                        break
                    
                    job_response.raise_for_status()
                    job_data = job_response.json()
                    
                    status = job_data.get('status')
                    progress = job_data.get('progress', 0)
                    
                    # Log progress updates
                    if progress != last_progress:
                        self.log(f"Progress: {progress}% - Status: {status}")
                        last_progress = progress
                    
                    # Check for completion
                    if status == 'completed':
                        elapsed = time.time() - step_start
                        self.results['timing']['step4'] = elapsed
                        
                        self.log(f"✅ Timeline completed in {elapsed:.2f}s")
                        self.results['success_criteria']['no_404_on_job_status'] = True
                        self.results['success_criteria']['no_timeout_or_hanging'] = elapsed < 30
                        
                        # Get final result
                        result = job_data.get('result', {})
                        tasks = result.get('tasks', [])
                        
                        self.results['step4'] = {
                            "status_code": 200,
                            "job_id": job_id,
                            "elapsed": elapsed,
                            "tasks_count": len(tasks),
                            "success": True,
                            "got_404": False
                        }
                        
                        self.log(f"Timeline generated with {len(tasks)} tasks")
                        return result
                    
                    # Check for failure
                    if status == 'failed':
                        error = job_data.get('error', 'Unknown error')
                        self.log(f"❌ Timeline generation failed: {error}", "ERROR")
                        self.results['step4'] = {"error": error, "success": False}
                        return {"error": error}
                    
                    # Check for hanging at 100%
                    if progress >= 100 and status != 'completed':
                        self.log(f"⚠️ Job hanging at {progress}% with status: {status}", "WARN")
                        if elapsed_wait > 10:  # Give it 10 seconds at 100%
                            self.log("❌ Job hanging - timeout", "ERROR")
                            self.results['success_criteria']['no_timeout_or_hanging'] = False
                            self.results['step4'] = {"error": "Hanging at 100%", "success": False}
                            return {"error": "Hanging at 100%"}
                
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 404:
                        got_404 = True
                        self.log(f"❌ Got 404 for job {job_id}", "ERROR")
                        break
                    else:
                        self.log(f"HTTP Error polling job: {e}", "ERROR")
                except Exception as e:
                    self.log(f"Error polling job: {e}", "WARN")
            
            # If we got here, we timed out or got 404
            elapsed = time.time() - step_start
            self.results['timing']['step4'] = elapsed
            
            if got_404:
                self.results['success_criteria']['no_404_on_job_status'] = False
                self.results['step4'] = {
                    "error": "404 on job status",
                    "job_id": job_id,
                    "got_404": True,
                    "success": False
                }
                self.log("❌ FAIL: Got 404 on job status (Fix #2 failed)", "ERROR")
            else:
                self.results['success_criteria']['no_timeout_or_hanging'] = False
                self.results['step4'] = {
                    "error": f"Timeout after {elapsed:.2f}s",
                    "success": False
                }
                self.log(f"❌ Timeline generation timed out after {elapsed:.2f}s", "ERROR")
            
            return {"error": "Timeout or 404"}
            
        except Exception as e:
            self.log(f"❌ Timeline generation failed: {e}", "ERROR")
            self.results['step4'] = {"error": str(e), "success": False}
            return {"error": str(e)}
    
    def run_full_test(self, pdf_path: str = None):
        """Execute full Steps 2-4 workflow test"""
        self.start_time = time.time()
        
        self.log("=" * 60)
        self.log(f"STARTING END-TO-END WORKFLOW TEST")
        self.log(f"Session ID: {self.session_id}")
        self.log(f"Project: {PROJECT_NAME}")
        self.log("=" * 60)
        
        # Get deliverables from RFP or fallback
        if pdf_path and os.path.exists(pdf_path):
            deliverables = self.upload_rfp_and_get_deliverables(pdf_path)
        else:
            self.log("No PDF provided, using fallback deliverables", "WARN")
            deliverables = self.get_fallback_deliverables()
        
        if not deliverables:
            self.log("❌ No deliverables available - cannot continue", "ERROR")
            return self.results
        
        # Select diverse deliverables
        selected_codes = self.select_diverse_deliverables(deliverables, count=6)
        self.log(f"Selected deliverables: {selected_codes}")
        
        # Step 2: Build scenario
        scenario_response = self.step2_build_scenario(selected_codes)
        if 'error' in scenario_response:
            self.log("❌ Step 2 failed - aborting test", "ERROR")
            return self.generate_report()
        
        scenario = scenario_response.get('scenario', {})
        
        # Step 3: Verify pricing data
        self.step3_verify_pricing_data(scenario)
        
        # Step 4: Generate timeline
        self.step4_generate_timeline(scenario)
        
        # Generate final report
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_elapsed = time.time() - self.start_time if self.start_time else 0
        
        self.log("=" * 60)
        self.log("TEST REPORT")
        self.log("=" * 60)
        
        # Success criteria summary
        criteria = self.results.get('success_criteria', {})
        self.log("\n✅ SUCCESS CRITERIA:")
        self.log(f"  1. No 500 on build_scenario: {criteria.get('no_500_on_build_scenario', 'N/A')}")
        self.log(f"  2. No 404 on job status: {criteria.get('no_404_on_job_status', 'N/A')}")
        self.log(f"  3. No timeout/hanging: {criteria.get('no_timeout_or_hanging', 'N/A')}")
        
        # Step results
        self.log("\n📊 STEP RESULTS:")
        for step_name in ['step2', 'step3', 'step4']:
            step_data = self.results.get(step_name, {})
            success = step_data.get('success', False) if isinstance(step_data, dict) else False
            elapsed = self.results['timing'].get(step_name, 0)
            self.log(f"  {step_name.upper()}: {'✅ PASS' if success else '❌ FAIL'} ({elapsed:.2f}s)")
            if 'error' in step_data:
                self.log(f"    Error: {step_data['error']}")
        
        # Timing summary
        self.log(f"\n⏱️ TOTAL TIME: {total_elapsed:.2f}s")
        
        # Overall verdict
        all_passed = all([
            criteria.get('no_500_on_build_scenario', False),
            criteria.get('no_404_on_job_status', False),
            self.results.get('step2', {}).get('success', False),
            self.results.get('step4', {}).get('success', False)
        ])
        
        if all_passed:
            self.log("\n🎉 OVERALL: ✅ ALL TESTS PASSED")
        else:
            self.log("\n⚠️ OVERALL: ❌ SOME TESTS FAILED")
        
        self.log("=" * 60)
        
        # Add report to results
        self.results['report'] = {
            "total_elapsed": total_elapsed,
            "all_passed": all_passed,
            "timestamp": datetime.now().isoformat()
        }
        
        return self.results

if __name__ == "__main__":
    import os
    
    # Path to St. Regis RFP
    pdf_path = "attached_assets/St.Regis_Nashville_ Branding Agency RFP_10.22.2024_1760738776363.pdf"
    
    tester = WorkflowTester()
    results = tester.run_full_test(pdf_path=pdf_path if os.path.exists(pdf_path) else None)
    
    # Save results to file
    with open('test_results_steps_2_4.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n\n📄 Results saved to: test_results_steps_2_4.json")
