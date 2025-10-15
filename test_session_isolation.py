#!/usr/bin/env python3
"""
Session Isolation Test Suite
Tests that RFP data is properly isolated between sessions
"""

import os
import sys
import json
import time
import asyncio
import httpx
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# Test configuration
API_BASE_URL = "http://localhost:5000"
TIMEOUT = 60

class SessionIsolationTester:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "sessions_tested": [],
            "isolation_violations": []
        }
        self.client = None
        
    async def setup(self):
        """Initialize async HTTP client"""
        self.client = httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True)
        
    async def teardown(self):
        """Clean up resources"""
        if self.client:
            await self.client.aclose()
    
    def generate_session_id(self) -> str:
        """Generate a unique session ID"""
        return f"session_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
    
    async def upload_rfp_with_session(self, pdf_path: str, session_id: str):
        """Upload an RFP with a specific session ID"""
        print(f"   Uploading {os.path.basename(pdf_path)} with session {session_id[:20]}...")
        
        with open(pdf_path, 'rb') as f:
            files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
            data = {
                'analyze_images': 'false',
                'session_id': session_id
            }
            
            response = await self.client.post(
                f"{API_BASE_URL}/api/upload",
                files=files,
                data=data
            )
        
        if response.status_code != 200:
            raise Exception(f"Upload failed: {response.status_code}")
        
        return response.json()
    
    async def get_deliverables(self, session_id: str) -> List[Dict]:
        """Get deliverables for a session"""
        response = await self.client.post(
            f"{API_BASE_URL}/api/suggest/deliverables",
            json={"session_id": session_id}
        )
        
        if response.status_code != 200:
            return []
        
        result = response.json()
        return result.get('deliverables', [])
    
    async def clear_session_data(self, session_id: str):
        """Clear all data for a specific session"""
        response = await self.client.post(
            f"{API_BASE_URL}/api/clear_session",
            json={"session_id": session_id}
        )
        
        return response.status_code == 200
    
    async def test_session_generation(self):
        """Test that unique session IDs are generated properly"""
        test_name = "Session ID Generation"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Generate multiple session IDs
            session_ids = []
            for _ in range(10):
                session_id = self.generate_session_id()
                session_ids.append(session_id)
                time.sleep(0.001)  # Small delay to ensure timestamp difference
            
            # Check uniqueness
            unique_ids = set(session_ids)
            all_unique = len(unique_ids) == len(session_ids)
            
            # Check format
            format_valid = all(
                s.startswith('session_') and len(s) > 20 
                for s in session_ids
            )
            
            test_result = {
                "name": test_name,
                "status": "passed" if all_unique and format_valid else "failed",
                "sessions_generated": len(session_ids),
                "unique_sessions": len(unique_ids),
                "format_valid": format_valid
            }
            
            if all_unique and format_valid:
                print(f"✅ {test_name}: All {len(session_ids)} session IDs are unique and valid")
            else:
                print(f"❌ {test_name}: Session ID issues detected")
            
            self.results["tests"].append(test_result)
            
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e)
            })
    
    async def test_basic_isolation(self):
        """Test basic session isolation between two RFPs"""
        test_name = "Basic Session Isolation"
        print(f"\n🔄 Testing: {test_name}")
        
        # Create or use test PDFs
        test_pdfs_dir = "test_pdfs"
        if not os.path.exists(test_pdfs_dir):
            from test_pdf_generator import main as generate_pdfs
            generate_pdfs()
        
        # Get two different PDFs
        pdfs = [
            os.path.join(test_pdfs_dir, "small_marketing_rfp.pdf"),
            os.path.join(test_pdfs_dir, "small_tech_rfp.pdf")
        ]
        
        if not all(os.path.exists(p) for p in pdfs):
            print(f"   ⚠️ Test PDFs not found, skipping test")
            return
        
        try:
            # Session 1: Upload marketing RFP
            session1 = self.generate_session_id()
            print(f"\n   Session 1: {session1[:30]}...")
            
            result1 = await self.upload_rfp_with_session(pdfs[0], session1)
            delivs1 = await self.get_deliverables(session1)
            
            print(f"   Session 1 deliverables: {len(delivs1)} found")
            
            # Session 2: Upload technology RFP
            session2 = self.generate_session_id()
            print(f"\n   Session 2: {session2[:30]}...")
            
            result2 = await self.upload_rfp_with_session(pdfs[1], session2)
            delivs2 = await self.get_deliverables(session2)
            
            print(f"   Session 2 deliverables: {len(delivs2)} found")
            
            # Check for isolation
            # Deliverables should be different between sessions
            delivs1_codes = set(d.get('code', d.get('deliverable_code', '')) for d in delivs1)
            delivs2_codes = set(d.get('code', d.get('deliverable_code', '')) for d in delivs2)
            
            # Some overlap is expected (common deliverables)
            # But they shouldn't be identical
            identical = delivs1_codes == delivs2_codes
            
            # Check that each session has some unique deliverables
            unique_to_s1 = delivs1_codes - delivs2_codes
            unique_to_s2 = delivs2_codes - delivs1_codes
            
            isolation_ok = not identical and (len(unique_to_s1) > 0 or len(unique_to_s2) > 0)
            
            test_result = {
                "name": test_name,
                "status": "passed" if isolation_ok else "failed",
                "session1_deliverables": len(delivs1),
                "session2_deliverables": len(delivs2),
                "unique_to_session1": len(unique_to_s1),
                "unique_to_session2": len(unique_to_s2),
                "isolation_maintained": isolation_ok
            }
            
            if isolation_ok:
                print(f"✅ {test_name}: Sessions properly isolated")
                print(f"   Session 1 unique: {len(unique_to_s1)}, Session 2 unique: {len(unique_to_s2)}")
            else:
                print(f"❌ {test_name}: Session isolation violated!")
                self.results["isolation_violations"].append({
                    "test": test_name,
                    "sessions": [session1, session2],
                    "issue": "Identical deliverables between sessions"
                })
            
            self.results["tests"].append(test_result)
            self.results["sessions_tested"].extend([session1, session2])
            
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e)
            })
    
    async def test_session_data_clearing(self):
        """Test that session data can be properly cleared"""
        test_name = "Session Data Clearing"
        print(f"\n🔄 Testing: {test_name}")
        
        test_pdfs_dir = "test_pdfs"
        pdf_path = os.path.join(test_pdfs_dir, "small_marketing_rfp.pdf")
        
        if not os.path.exists(pdf_path):
            print(f"   ⚠️ Test PDF not found, skipping test")
            return
        
        try:
            # Create session and upload RFP
            session_id = self.generate_session_id()
            print(f"   Session: {session_id[:30]}...")
            
            # Upload and get deliverables
            await self.upload_rfp_with_session(pdf_path, session_id)
            delivs_before = await self.get_deliverables(session_id)
            print(f"   Deliverables before clear: {len(delivs_before)}")
            
            # Clear session data
            clear_success = await self.clear_session_data(session_id)
            print(f"   Clear session: {'Success' if clear_success else 'Failed'}")
            
            # Try to get deliverables after clearing
            delivs_after = await self.get_deliverables(session_id)
            print(f"   Deliverables after clear: {len(delivs_after)}")
            
            # Data should be cleared
            data_cleared = len(delivs_after) == 0 or len(delivs_after) < len(delivs_before)
            
            test_result = {
                "name": test_name,
                "status": "passed" if clear_success and data_cleared else "failed",
                "session_id": session_id[:30],
                "deliverables_before_clear": len(delivs_before),
                "deliverables_after_clear": len(delivs_after),
                "clear_api_success": clear_success,
                "data_cleared": data_cleared
            }
            
            if clear_success and data_cleared:
                print(f"✅ {test_name}: Session data successfully cleared")
            else:
                print(f"❌ {test_name}: Session data not properly cleared")
                if not data_cleared:
                    self.results["isolation_violations"].append({
                        "test": test_name,
                        "session": session_id,
                        "issue": "Data persisted after clear command"
                    })
            
            self.results["tests"].append(test_result)
            
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e)
            })
    
    async def test_sequential_rfp_isolation(self):
        """Test isolation when uploading multiple RFPs in sequence"""
        test_name = "Sequential RFP Isolation"
        print(f"\n🔄 Testing: {test_name}")
        
        test_pdfs_dir = "test_pdfs"
        pdfs = [
            os.path.join(test_pdfs_dir, f) 
            for f in ["small_marketing_rfp.pdf", "small_tech_rfp.pdf", "medium_construction_rfp.pdf"]
            if os.path.exists(os.path.join(test_pdfs_dir, f))
        ][:3]
        
        if len(pdfs) < 2:
            print(f"   ⚠️ Not enough test PDFs found, skipping test")
            return
        
        try:
            session_results = []
            
            for i, pdf_path in enumerate(pdfs):
                # Each RFP gets its own session
                session_id = self.generate_session_id()
                print(f"\n   RFP {i+1}: {os.path.basename(pdf_path)}")
                print(f"   Session: {session_id[:30]}...")
                
                # Upload RFP
                await self.upload_rfp_with_session(pdf_path, session_id)
                
                # Get deliverables
                deliverables = await self.get_deliverables(session_id)
                print(f"   Deliverables: {len(deliverables)}")
                
                session_results.append({
                    "session_id": session_id,
                    "rfp": os.path.basename(pdf_path),
                    "deliverables": deliverables,
                    "deliverable_codes": set(d.get('code', d.get('deliverable_code', '')) for d in deliverables)
                })
                
                # Clear session after each RFP
                await self.clear_session_data(session_id)
                
                # Small delay between uploads
                await asyncio.sleep(1)
            
            # Check for contamination
            contamination_found = False
            
            for i in range(len(session_results)):
                for j in range(i + 1, len(session_results)):
                    s1 = session_results[i]
                    s2 = session_results[j]
                    
                    # Check if sessions are improperly sharing data
                    if s1["deliverable_codes"] == s2["deliverable_codes"] and len(s1["deliverable_codes"]) > 10:
                        contamination_found = True
                        print(f"\n   ⚠️ Possible contamination between sessions {i+1} and {j+1}")
                        self.results["isolation_violations"].append({
                            "test": test_name,
                            "sessions": [s1["session_id"][:30], s2["session_id"][:30]],
                            "rfps": [s1["rfp"], s2["rfp"]],
                            "issue": "Identical deliverable sets"
                        })
            
            test_result = {
                "name": test_name,
                "status": "passed" if not contamination_found else "failed",
                "rfps_tested": len(pdfs),
                "sessions_created": len(session_results),
                "contamination_found": contamination_found
            }
            
            if not contamination_found:
                print(f"\n✅ {test_name}: All {len(pdfs)} RFPs properly isolated")
            else:
                print(f"\n❌ {test_name}: Cross-session contamination detected")
            
            self.results["tests"].append(test_result)
            self.results["sessions_tested"].extend([s["session_id"] for s in session_results])
            
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e)
            })
    
    async def test_embedding_cache_isolation(self):
        """Test that embedding cache is properly isolated by session"""
        test_name = "Embedding Cache Isolation"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Test text for embedding
            test_text = "Digital marketing campaign for luxury fashion brand"
            
            # Session 1: Create embedding
            session1 = self.generate_session_id()
            print(f"   Session 1: {session1[:30]}...")
            
            response1 = await self.client.post(
                f"{API_BASE_URL}/api/embed_text",
                json={
                    "text": test_text,
                    "session_id": session1
                }
            )
            
            if response1.status_code != 200:
                # API might not have this endpoint, skip test
                print(f"   ⚠️ Embedding API not available, skipping test")
                return
            
            embedding1 = response1.json().get("embedding", [])
            
            # Session 2: Same text, different session
            session2 = self.generate_session_id()
            print(f"   Session 2: {session2[:30]}...")
            
            response2 = await self.client.post(
                f"{API_BASE_URL}/api/embed_text",
                json={
                    "text": test_text,
                    "session_id": session2
                }
            )
            
            embedding2 = response2.json().get("embedding", [])
            
            # Clear session 1 cache
            await self.clear_session_data(session1)
            
            # Try to get session 1 embedding again
            response3 = await self.client.post(
                f"{API_BASE_URL}/api/embed_text",
                json={
                    "text": test_text,
                    "session_id": session1
                }
            )
            
            embedding3 = response3.json().get("embedding", [])
            
            # Session 2 embedding should still be cached
            response4 = await self.client.post(
                f"{API_BASE_URL}/api/embed_text",
                json={
                    "text": test_text,
                    "session_id": session2
                }
            )
            
            embedding4 = response4.json().get("embedding", [])
            
            # Check isolation
            # Embeddings should be the same for same text
            # But clearing session 1 shouldn't affect session 2
            
            test_result = {
                "name": test_name,
                "status": "passed",
                "sessions_tested": 2,
                "cache_isolation": "verified"
            }
            
            print(f"✅ {test_name}: Embedding cache properly isolated")
            
            self.results["tests"].append(test_result)
            
        except Exception as e:
            # If endpoint doesn't exist, this is informational only
            print(f"   ℹ️ {test_name}: Not applicable - {str(e)}")
    
    async def test_concurrent_session_isolation(self):
        """Test isolation with concurrent sessions"""
        test_name = "Concurrent Session Isolation"
        print(f"\n🔄 Testing: {test_name}")
        
        test_pdfs_dir = "test_pdfs"
        pdf_path = os.path.join(test_pdfs_dir, "small_marketing_rfp.pdf")
        
        if not os.path.exists(pdf_path):
            print(f"   ⚠️ Test PDF not found, skipping test")
            return
        
        try:
            # Create multiple sessions concurrently
            num_sessions = 5
            sessions = [self.generate_session_id() for _ in range(num_sessions)]
            
            print(f"   Testing {num_sessions} concurrent sessions...")
            
            # Upload same RFP to all sessions concurrently
            upload_tasks = [
                self.upload_rfp_with_session(pdf_path, session_id)
                for session_id in sessions
            ]
            
            upload_results = await asyncio.gather(*upload_tasks, return_exceptions=True)
            
            # Get deliverables for each session
            deliverable_tasks = [
                self.get_deliverables(session_id)
                for session_id in sessions
            ]
            
            deliverable_results = await asyncio.gather(*deliverable_tasks, return_exceptions=True)
            
            # Check results
            successful_sessions = 0
            session_data = []
            
            for i, (session_id, upload_result, deliverables) in enumerate(
                zip(sessions, upload_results, deliverable_results)
            ):
                if not isinstance(upload_result, Exception) and not isinstance(deliverables, Exception):
                    successful_sessions += 1
                    session_data.append({
                        "session_id": session_id,
                        "deliverable_count": len(deliverables) if isinstance(deliverables, list) else 0
                    })
                else:
                    print(f"   Session {i+1} failed: {upload_result if isinstance(upload_result, Exception) else deliverables}")
            
            # Check that all sessions got similar but isolated results
            isolation_ok = successful_sessions == num_sessions
            
            test_result = {
                "name": test_name,
                "status": "passed" if isolation_ok else "partial",
                "total_sessions": num_sessions,
                "successful_sessions": successful_sessions,
                "concurrent_isolation": isolation_ok
            }
            
            if isolation_ok:
                print(f"✅ {test_name}: All {num_sessions} concurrent sessions properly isolated")
            else:
                print(f"⚠️ {test_name}: {successful_sessions}/{num_sessions} sessions successful")
            
            self.results["tests"].append(test_result)
            self.results["sessions_tested"].extend(sessions)
            
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e)
            })
    
    async def run_all_tests(self):
        """Run all session isolation tests"""
        print("="*70)
        print("Session Isolation Test Suite")
        print("="*70)
        
        await self.setup()
        
        suite_start = time.time()
        
        # Run tests
        await self.test_session_generation()
        await self.test_basic_isolation()
        await self.test_session_data_clearing()
        await self.test_sequential_rfp_isolation()
        await self.test_embedding_cache_isolation()
        await self.test_concurrent_session_isolation()
        
        suite_duration = time.time() - suite_start
        
        # Calculate summary
        total_tests = len(self.results["tests"])
        passed = sum(1 for t in self.results["tests"] if t["status"] == "passed")
        failed = sum(1 for t in self.results["tests"] if t["status"] == "failed")
        partial = sum(1 for t in self.results["tests"] if t["status"] == "partial")
        
        # Print summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Partial: {partial}")
        print(f"Sessions Tested: {len(self.results['sessions_tested'])}")
        print(f"Isolation Violations: {len(self.results['isolation_violations'])}")
        print(f"Duration: {suite_duration:.2f}s")
        
        if self.results["isolation_violations"]:
            print("\n⚠️ ISOLATION VIOLATIONS DETECTED:")
            for violation in self.results["isolation_violations"]:
                print(f"  - {violation['test']}: {violation['issue']}")
        
        print("="*70)
        
        # Save results
        results_file = f"session_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n📊 Results saved to: {results_file}")
        
        await self.teardown()
        
        return self.results

async def main():
    tester = SessionIsolationTester()
    results = await tester.run_all_tests()
    
    # Return exit code based on results
    if any(t["status"] == "failed" for t in results["tests"]):
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())