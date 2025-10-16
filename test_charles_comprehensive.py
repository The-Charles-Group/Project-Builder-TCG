#!/usr/bin/env python3
"""
Comprehensive test suite for CHARLES Agent v3.0
Tests all features including state preservation, error recovery, batch processing
"""

import requests
import json
import time
import os
from pathlib import Path

BASE_URL = "http://localhost:5000"

class CharlesAgentTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        self.job_ids = []
        
    def test_basic_health(self):
        """Test 1: Basic agent health check"""
        print("\n🔬 Test 1: Basic Health Check")
        try:
            resp = self.session.get(f"{BASE_URL}/api/agent/status")
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Agent is healthy: v{data.get('version', 'unknown')}")
                print(f"   Features: {', '.join(data.get('features', []))}")
                return True
            else:
                print(f"❌ Agent unhealthy: {resp.status_code}")
                return False
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def test_file_upload(self, filepath):
        """Test 2: File upload and extraction"""
        print(f"\n🔬 Test 2: File Upload - {filepath}")
        try:
            with open(filepath, 'rb') as f:
                files = {'file': (os.path.basename(filepath), f, 'text/plain')}
                resp = self.session.post(f"{BASE_URL}/api/upload_rfp", files=files)
                
            if resp.status_code == 200:
                data = resp.json()
                job_id = data.get('job_id')
                if job_id:
                    self.job_ids.append(job_id)
                    print(f"✅ File uploaded successfully")
                    print(f"   Job ID: {job_id}")
                    print(f"   Text extracted: {data.get('text_length', 0)} chars")
                    print(f"   Analysis started: {data.get('analysis_started', False)}")
                    return job_id
                else:
                    print("❌ No job ID returned")
                    return None
            else:
                print(f"❌ Upload failed: {resp.status_code}")
                return None
        except Exception as e:
            print(f"❌ Upload error: {e}")
            return None
    
    def test_job_tracking(self, job_id, max_polls=30):
        """Test 3: Job status tracking"""
        print(f"\n🔬 Test 3: Job Tracking - {job_id}")
        
        for i in range(max_polls):
            try:
                resp = self.session.get(f"{BASE_URL}/api/agencydb/status/{job_id}")
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get('status')
                    progress = data.get('progress', 0)
                    stage = data.get('stage', '')
                    
                    print(f"   Poll {i+1}: {status} - {progress}% - {stage}")
                    
                    if status == 'completed':
                        deliverables = data.get('data', {}).get('deliverables', [])
                        print(f"✅ Job completed with {len(deliverables)} deliverables")
                        return True
                    elif status == 'failed':
                        print(f"❌ Job failed: {data.get('error')}")
                        return False
                    
                    time.sleep(2)
                elif resp.status_code == 404:
                    print(f"❌ Job not found: {job_id}")
                    return False
                else:
                    print(f"⚠️ Status check returned: {resp.status_code}")
                    
            except Exception as e:
                print(f"❌ Tracking error: {e}")
                return False
                
        print("⏱️ Job timed out after 60 seconds")
        return False
    
    def test_agent_command(self, message, tier="auto"):
        """Test 4: Agent command execution"""
        print(f"\n🔬 Test: Agent Command - '{message}'")
        try:
            resp = self.session.post(
                f"{BASE_URL}/api/agent/chat",
                json={"message": message, "tier": tier}
            )
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get('success'):
                    command_type = data.get('command', {}).get('type', 'unknown')
                    parsing_method = data.get('command', {}).get('parsing_method', 'unknown')
                    exec_time = data.get('execution_time', 0)
                    
                    print(f"✅ Command executed: {command_type}")
                    print(f"   Method: {parsing_method}, Time: {exec_time*1000:.2f}ms")
                    
                    if data.get('actions'):
                        print(f"   Actions: {len(data['actions'])} queued")
                    
                    return True
                else:
                    print(f"❌ Command failed: {data.get('error')}")
                    return False
            else:
                print(f"❌ API error: {resp.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Command error: {e}")
            return False
    
    def test_state_preservation(self):
        """Test 5: State save and restore"""
        print("\n🔬 Test 5: State Preservation")
        
        # Save current state
        save_resp = self.test_agent_command("save current state", "mini")
        if not save_resp:
            print("❌ Failed to save state")
            return False
            
        # Simulate some changes
        self.test_agent_command("navigate to step 2", "mini")
        self.test_agent_command("select all strategy deliverables", "mini")
        
        # Restore state
        restore_resp = self.test_agent_command("restore previous state", "mini")
        if restore_resp:
            print("✅ State preservation working")
            return True
        else:
            print("❌ State restoration failed")
            return False
    
    def test_batch_processing(self):
        """Test 6: Batch file processing"""
        print("\n🔬 Test 6: Batch File Processing")
        
        test_files = [
            "test_samples/test1_simple.txt",
            "test_samples/test2_complex.txt"
        ]
        
        job_ids = []
        for filepath in test_files:
            if os.path.exists(filepath):
                job_id = self.test_file_upload(filepath)
                if job_id:
                    job_ids.append(job_id)
                    
        if len(job_ids) == len(test_files):
            print(f"✅ Batch upload successful: {len(job_ids)} files")
            
            # Track all jobs
            success_count = 0
            for job_id in job_ids:
                if self.test_job_tracking(job_id):
                    success_count += 1
                    
            if success_count == len(job_ids):
                print(f"✅ All {len(job_ids)} jobs completed successfully")
                return True
            else:
                print(f"⚠️ Only {success_count}/{len(job_ids)} jobs completed")
                return False
        else:
            print(f"❌ Batch upload incomplete: {len(job_ids)}/{len(test_files)}")
            return False
    
    def test_complex_workflow(self):
        """Test 7: Complete workflow from upload to deliverables"""
        print("\n🔬 Test 7: Complete Workflow")
        
        workflow_steps = [
            ("Upload RFP", "upload the test RFP for analysis"),
            ("Start analysis", "analyze this RFP in deep mode"),
            ("Check progress", "what's the analysis progress?"),
            ("Select deliverables", "select the top 10 deliverables"),
            ("Calculate cost", "calculate the total cost"),
            ("Generate timeline", "generate a project timeline"),
            ("Export data", "prepare for export to Excel")
        ]
        
        success_count = 0
        for step_name, command in workflow_steps:
            print(f"\n   Step: {step_name}")
            if self.test_agent_command(command, "thinking"):
                success_count += 1
            time.sleep(1)  # Pause between steps
            
        if success_count == len(workflow_steps):
            print(f"✅ Complete workflow executed: {success_count}/{len(workflow_steps)} steps")
            return True
        else:
            print(f"⚠️ Workflow partially completed: {success_count}/{len(workflow_steps)} steps")
            return False
    
    def test_error_recovery(self):
        """Test 8: Error recovery and self-healing"""
        print("\n🔬 Test 8: Error Recovery")
        
        # Trigger intentional error
        print("   Triggering intentional error...")
        self.test_agent_command("analyze nonexistent file xyz123.pdf", "mini")
        
        # Check if agent recovers
        time.sleep(2)
        recovery = self.test_agent_command("status check", "mini")
        
        if recovery:
            print("✅ Agent recovered from error successfully")
            return True
        else:
            print("❌ Agent failed to recover")
            return False
    
    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("\n" + "="*80)
        print("🚀 CHARLES AGENT v3.0 COMPREHENSIVE TEST SUITE")
        print("="*80)
        
        tests = [
            ("Health Check", self.test_basic_health),
            ("State Preservation", self.test_state_preservation),
            ("Batch Processing", self.test_batch_processing),
            ("Error Recovery", self.test_error_recovery),
            ("Complex Workflow", self.test_complex_workflow)
        ]
        
        results = {}
        for test_name, test_func in tests:
            print(f"\n{'='*40}")
            try:
                result = test_func()
                results[test_name] = result
            except Exception as e:
                print(f"❌ Test crashed: {e}")
                results[test_name] = False
                
        # Summary
        print("\n" + "="*80)
        print("📊 TEST RESULTS SUMMARY")
        print("="*80)
        
        passed = sum(1 for r in results.values() if r)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} - {test_name}")
            
        print(f"\nOverall: {passed}/{total} tests passed ({passed*100//total}%)")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED! CHARLES Agent is fully operational!")
        elif passed >= total * 0.8:
            print("\n⚠️ Most tests passed but some issues remain.")
        else:
            print("\n❌ Critical issues detected. Agent needs fixes.")
            
        return results

if __name__ == "__main__":
    tester = CharlesAgentTester()
    results = tester.run_all_tests()
    
    # Return exit code based on results
    import sys
    if all(results.values()):
        sys.exit(0)
    else:
        sys.exit(1)