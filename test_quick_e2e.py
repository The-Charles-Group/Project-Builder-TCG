#!/usr/bin/env python3
"""
QUICK END-TO-END TEST
Focused test of Steps 2-4 to verify critical fixes
Skips long RFP analysis, uses database deliverables directly
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

class QuickE2ETest:
    def __init__(self):
        self.results = {}
        self.start_time = time.time()
        self.scenario_data = None
        
    def log(self, msg):
        elapsed = time.time() - self.start_time
        print(f"[{elapsed:.1f}s] {msg}")
    
    def test_step2_build_scenario(self):
        """Step 2: Build pricing scenario"""
        self.log("="*80)
        self.log("STEP 2: Build Pricing Scenario")
        self.log("="*80)
        
        try:
            # Get deliverables from /api/options
            self.log("Fetching deliverables from /api/options...")
            resp = requests.get(f"{BASE_URL}/api/options")
            
            if resp.status_code != 200:
                raise Exception(f"Failed to get options: {resp.status_code}")
            
            options = resp.json()
            deliverables = options.get('deliverables', [])
            self.log(f"Found {len(deliverables)} deliverables")
            
            # Select 6 deliverables across departments
            selected_codes = []
            depts = set()
            
            for d in deliverables:
                code = d.get('Deliverable_Code', '')
                dept = d.get('Department', 'Unknown')
                name = d.get('Deliverable', code)
                
                if code and dept not in depts and len(selected_codes) < 6:
                    selected_codes.append(code)
                    depts.add(dept)
                    self.log(f"  Selected: {name} ({code}, {dept})")
            
            if len(selected_codes) < 5:
                # Fallback: just take first 6
                selected_codes = [d.get('Deliverable_Code', '') for d in deliverables[:6] if d.get('Deliverable_Code')]
            
            # Build scenario payload
            payload = {
                "session_id": "quick_e2e_test",
                "selection": {
                    "deliverable_codes": selected_codes,
                    "components_map": {},
                    "l3_map": {}
                },
                "project_name": "St. Regis Nashville Quick E2E",
                "pricing_mode": "Flat_Blended",
                "blended_rate": 195.0,
                "rate_band": "Standard_US"
            }
            
            self.log(f"Building scenario with {len(selected_codes)} deliverables...")
            resp = requests.post(
                f"{BASE_URL}/api/pricing/build_scenario",
                json=payload,
                timeout=60
            )
            
            self.log(f"Response: {resp.status_code}")
            
            if resp.status_code == 500:
                self.results['step2'] = {
                    'status': 'FAIL',
                    'error': '500 Internal Server Error - BuildScenarioPayload issue',
                    'http_status': 500
                }
                self.log("❌ FAIL: 500 error!")
                return False
            
            if resp.status_code != 200:
                raise Exception(f"Build failed: {resp.status_code} - {resp.text[:200]}")
            
            result = resp.json()
            
            # Store scenario data
            self.scenario_data = result
            scenario = result.get('scenario', result)
            
            items = scenario.get('items', [])
            total_hours = scenario.get('total_hours', 0)
            total_cost = scenario.get('total_cost', 0)
            
            self.log(f"✅ SUCCESS!")
            self.log(f"   Items: {len(items)}")
            self.log(f"   Total Hours: {total_hours}")
            self.log(f"   Total Cost: ${total_cost:,.2f}")
            
            self.results['step2'] = {
                'status': 'PASS',
                'http_status': 200,
                'items_count': len(items),
                'total_hours': total_hours,
                'total_cost': total_cost
            }
            return True
            
        except Exception as e:
            self.log(f"❌ FAIL: {str(e)}")
            self.results['step2'] = {'status': 'FAIL', 'error': str(e)}
            return False
    
    def test_step3_verify_structure(self):
        """Step 3: Verify data structure"""
        self.log("\n" + "="*80)
        self.log("STEP 3: Verify Pricing Data Structure")
        self.log("="*80)
        
        try:
            if not self.scenario_data:
                raise Exception("No scenario data from Step 2")
            
            scenario = self.scenario_data.get('scenario', self.scenario_data)
            items = scenario.get('items', [])
            
            # Check hierarchy
            deliverable_count = sum(1 for item in items if 'deliverable' in item.get('type', '').lower() or item.get('level') == 1)
            component_count = sum(1 for item in items if 'component' in item.get('type', '').lower() or item.get('level') == 2)
            task_count = sum(1 for item in items if 'task' in item.get('type', '').lower() or item.get('level') == 3)
            
            self.log(f"Hierarchy:")
            self.log(f"  Deliverables: {deliverable_count}")
            self.log(f"  Components: {component_count}")
            self.log(f"  Tasks: {task_count}")
            
            # Check totals
            total_hours = scenario.get('total_hours', 0)
            total_cost = scenario.get('total_cost', 0)
            
            self.log(f"Totals:")
            self.log(f"  Hours: {total_hours}")
            self.log(f"  Cost: ${total_cost:,.2f}")
            
            # Verify structure
            checks = [
                ("Has items", len(items) > 0),
                ("Has deliverables", deliverable_count > 0),
                ("Has components", component_count > 0),
                ("Has tasks", task_count > 0),
                ("Has total hours", total_hours > 0),
                ("Has total cost", total_cost > 0)
            ]
            
            all_passed = all(check[1] for check in checks)
            
            for name, passed in checks:
                status = "✅" if passed else "❌"
                self.log(f"  {status} {name}")
            
            if all_passed:
                self.log("✅ All structure checks PASSED!")
                self.results['step3'] = {
                    'status': 'PASS',
                    'deliverable_count': deliverable_count,
                    'component_count': component_count,
                    'task_count': task_count,
                    'total_hours': total_hours,
                    'total_cost': total_cost
                }
                return True
            else:
                raise Exception("Some structure checks failed")
                
        except Exception as e:
            self.log(f"❌ FAIL: {str(e)}")
            self.results['step3'] = {'status': 'FAIL', 'error': str(e)}
            return False
    
    def test_step4_generate_timeline(self):
        """Step 4: Generate timeline and verify NO 404 errors"""
        self.log("\n" + "="*80)
        self.log("STEP 4: Generate Timeline")
        self.log("="*80)
        
        try:
            if not self.scenario_data:
                raise Exception("No scenario data from Step 2")
            
            # Generate timeline
            self.log("Calling /api/ai/generate_timeline...")
            resp = requests.post(
                f"{BASE_URL}/api/ai/generate_timeline",
                json=self.scenario_data,
                timeout=30
            )
            
            self.log(f"Response: {resp.status_code}")
            
            if resp.status_code != 200:
                raise Exception(f"Generate timeline failed: {resp.status_code} - {resp.text[:200]}")
            
            result = resp.json()
            job_id = result.get('job_id')
            
            if not job_id:
                raise Exception("No job_id in response")
            
            self.log(f"Timeline job created: {job_id}")
            
            # Poll for completion
            max_wait = 300  # 5 minutes
            poll_start = time.time()
            poll_count = 0
            found_404 = False
            
            while time.time() - poll_start < max_wait:
                poll_count += 1
                job_resp = requests.get(f"{BASE_URL}/api/ai/jobs/{job_id}")
                
                if poll_count % 5 == 0:  # Log every 5th poll
                    self.log(f"Poll #{poll_count}: Status {job_resp.status_code}")
                
                # Check for 404 - the critical test!
                if job_resp.status_code == 404:
                    found_404 = True
                    self.log(f"❌ FAIL: 404 error on job polling!")
                    self.results['step4'] = {
                        'status': 'FAIL',
                        'error': '404 on job polling - SSE_JOB_STORE not working',
                        'job_id': job_id,
                        'http_status': 404,
                        'poll_attempts': poll_count
                    }
                    return False
                
                if job_resp.status_code == 200:
                    job_data = job_resp.json()
                    status = job_data.get('status')
                    progress = job_data.get('progress', 0)
                    
                    if poll_count % 5 == 0:
                        self.log(f"  Status: {status}, Progress: {progress}%")
                    
                    if status in ['completed', 'success']:
                        timeline_data = job_data.get('result', {})
                        
                        self.log(f"✅ Timeline generated successfully!")
                        self.log(f"   Poll attempts: {poll_count}")
                        self.log(f"   Timeline items: {len(timeline_data.get('items', []))}")
                        self.log(f"   Generation time: {time.time() - poll_start:.1f}s")
                        
                        self.results['step4'] = {
                            'status': 'PASS',
                            'http_status': 200,
                            'job_id': job_id,
                            'poll_attempts': poll_count,
                            'no_404_errors': True,
                            'timeline_items': len(timeline_data.get('items', [])),
                            'generation_time': time.time() - poll_start
                        }
                        return True
                    
                    elif status == 'failed':
                        raise Exception(f"Timeline job failed: {job_data.get('error')}")
                
                time.sleep(2)
            
            raise Exception("Timeline timeout after 5 minutes")
            
        except Exception as e:
            self.log(f"❌ FAIL: {str(e)}")
            self.results['step4'] = {'status': 'FAIL', 'error': str(e)}
            return False
    
    def print_final_report(self):
        """Print final comprehensive report"""
        elapsed = time.time() - self.start_time
        
        print("\n" + "="*80)
        print("FINAL QUICK E2E TEST REPORT")
        print("="*80)
        print(f"Total Execution Time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print()
        
        # Results for each step
        for step_name in ['step2', 'step3', 'step4']:
            result = self.results.get(step_name, {})
            status = result.get('status', 'NOT RUN')
            
            step_num = step_name[-1]
            status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⏸️"
            
            print(f"{status_icon} STEP {step_num}: {status}")
            
            if result:
                for key, value in result.items():
                    if key not in ['status', 'error']:
                        print(f"   {key}: {value}")
                if 'error' in result:
                    print(f"   ERROR: {result['error']}")
            print()
        
        # Success criteria evaluation
        print("="*80)
        print("SUCCESS CRITERIA EVALUATION:")
        print("="*80)
        
        all_passed = all(self.results.get(f"step{i}", {}).get('status') == 'PASS' for i in [2, 3, 4])
        
        no_500 = not any(self.results.get(f"step{i}", {}).get('http_status') == 500 for i in [2, 3, 4])
        no_404 = not any(self.results.get(f"step{i}", {}).get('http_status') == 404 for i in [2, 3, 4])
        no_404_polling = self.results.get('step4', {}).get('no_404_errors', False)
        
        print(f"{'✅' if all_passed else '❌'} All endpoints return 200 OK")
        print(f"{'✅' if no_500 else '❌'} NO 500 errors (BuildScenarioPayload fix working)")
        print(f"{'✅' if no_404 and no_404_polling else '❌'} NO 404 errors on job polling (SSE_JOB_STORE fix working)")
        print(f"{'✅' if all_passed else '❌'} Complete data flows through all steps")
        print()
        
        # Production readiness
        print("="*80)
        print("PRODUCTION READINESS ASSESSMENT:")
        print("="*80)
        
        if all_passed and no_500 and no_404 and no_404_polling:
            print("✅ PRODUCTION READY")
            print("   All critical workflow steps completed successfully")
            print("   No critical errors detected (NO 404s, NO 500s)")
            print("   System is ready for user testing")
        else:
            print("❌ NOT PRODUCTION READY")
            print("   Issues found:")
            if not all_passed:
                failed = [i for i in [2, 3, 4] if self.results.get(f"step{i}", {}).get('status') != 'PASS']
                print(f"   - Failed steps: {', '.join(f'Step {i}' for i in failed)}")
            if not no_500:
                print("   - 500 errors detected")
            if not no_404 or not no_404_polling:
                print("   - 404 errors on job polling")
        
        print("="*80)
        
        return all_passed and no_500 and no_404 and no_404_polling

def main():
    print("="*80)
    print("QUICK END-TO-END TEST - CRITICAL WORKFLOW VERIFICATION")
    print("Testing Steps 2-4 with critical fixes")
    print("="*80)
    print()
    
    test = QuickE2ETest()
    
    step2_ok = test.test_step2_build_scenario()
    step3_ok = test.test_step3_verify_structure() if step2_ok else False
    step4_ok = test.test_step4_generate_timeline() if step3_ok else False
    
    production_ready = test.print_final_report()
    
    return 0 if production_ready else 1

if __name__ == "__main__":
    exit(main())
