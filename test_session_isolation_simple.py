#!/usr/bin/env python3
"""
Simple Session Isolation Test 
Tests core session isolation functionality to verify no data contamination
"""

import os
import json
import time
import httpx
import asyncio
import uuid
from datetime import datetime

API_BASE_URL = "http://localhost:5000"

class SimpleSessionIsolationTest:
    def __init__(self):
        self.results = []
        self.client = None
        
    async def setup(self):
        """Initialize HTTP client"""
        self.client = httpx.AsyncClient(timeout=60.0)
        
    async def teardown(self):
        """Clean up"""
        if self.client:
            await self.client.aclose()
    
    def generate_session_id(self) -> str:
        """Generate unique session ID"""
        return f"session_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
    
    async def test_embedding_cache_isolation(self):
        """Test that embedding cache is properly isolated by session"""
        print("\n🔒 Testing Embedding Cache Session Isolation")
        print("-" * 50)
        
        try:
            # Create two distinct sessions
            session1 = self.generate_session_id()
            session2 = self.generate_session_id()
            
            print(f"Session 1: {session1[:40]}...")
            print(f"Session 2: {session2[:40]}...")
            
            # Unique RFP texts for each session
            rfp_text1 = """
            We need to build a SoundCloud music streaming platform integration.
            Requirements include:
            - Audio processing and streaming capabilities
            - Music recommendation algorithms
            - Social features for SoundCloud artists
            - Real-time audio streaming infrastructure
            """
            
            rfp_text2 = """
            We need to develop a healthcare management system.
            Requirements include:
            - Patient portal for medical records
            - HIPAA compliant data storage
            - Telemedicine video consultation features
            - Electronic health records (EHR) system
            """
            
            print("\n📝 Submitting RFP 1 (SoundCloud)...")
            # Submit RFP 1 to session 1
            response1 = await self.client.post(
                f"{API_BASE_URL}/api/suggest/deliverables",
                json={
                    "rfp_text": rfp_text1,
                    "session_id": session1,
                    "mode": "fast"
                }
            )
            
            suggestions1 = []
            if response1.status_code == 200:
                data1 = response1.json()
                suggestions1 = data1.get('deliverables', [])
                print(f"   Got {len(suggestions1)} suggestions for SoundCloud RFP")
            else:
                print(f"   Warning: Status {response1.status_code}")
            
            print("\n📝 Submitting RFP 2 (Healthcare)...")
            # Submit RFP 2 to session 2
            response2 = await self.client.post(
                f"{API_BASE_URL}/api/suggest/deliverables",
                json={
                    "rfp_text": rfp_text2,
                    "session_id": session2,
                    "mode": "fast"
                }
            )
            
            suggestions2 = []
            if response2.status_code == 200:
                data2 = response2.json()
                suggestions2 = data2.get('deliverables', [])
                print(f"   Got {len(suggestions2)} suggestions for Healthcare RFP")
            else:
                print(f"   Warning: Status {response2.status_code}")
            
            # Check for cross-contamination
            print("\n🔍 Checking for cross-contamination...")
            
            # Convert suggestions to text for analysis
            suggestions1_text = ' '.join([str(s) for s in suggestions1]).lower()
            suggestions2_text = ' '.join([str(s) for s in suggestions2]).lower()
            
            # Check for domain-specific keywords
            soundcloud_keywords = ['soundcloud', 'music', 'streaming', 'audio', 'artists']
            healthcare_keywords = ['healthcare', 'medical', 'patient', 'hipaa', 'health']
            
            contamination_found = False
            contamination_details = []
            
            # Check if SoundCloud keywords appear in Healthcare suggestions
            for keyword in soundcloud_keywords:
                if keyword in suggestions2_text:
                    contamination_found = True
                    contamination_details.append(f"SoundCloud keyword '{keyword}' found in Healthcare session")
            
            # Check if Healthcare keywords appear in SoundCloud suggestions
            for keyword in healthcare_keywords:
                if keyword in suggestions1_text:
                    contamination_found = True
                    contamination_details.append(f"Healthcare keyword '{keyword}' found in SoundCloud session")
            
            print("\n🧹 Testing session cleanup...")
            # Clear session 1
            clear_response = await self.client.post(
                f"{API_BASE_URL}/api/clear_session",
                json={"session_id": session1}
            )
            
            session1_cleared = clear_response.status_code == 200
            print(f"   Session 1 cleared: {session1_cleared}")
            
            # Try to get suggestions again for session 1 (should recompute)
            print("\n📝 Re-submitting to cleared session 1...")
            response1_after = await self.client.post(
                f"{API_BASE_URL}/api/suggest/deliverables",
                json={
                    "rfp_text": rfp_text1,
                    "session_id": session1,
                    "mode": "fast"
                }
            )
            
            session1_works = response1_after.status_code == 200
            
            # Session 2 should still work
            print("\n📝 Verifying session 2 still works...")
            response2_after = await self.client.post(
                f"{API_BASE_URL}/api/suggest/deliverables",
                json={
                    "rfp_text": rfp_text2,
                    "session_id": session2,
                    "mode": "fast"
                }
            )
            
            session2_works = response2_after.status_code == 200
            
            # Results
            print("\n" + "="*50)
            print("📊 RESULTS")
            print("="*50)
            
            if not contamination_found:
                print("✅ NO CROSS-CONTAMINATION DETECTED")
                print("   Each session maintained independent context")
            else:
                print("❌ CONTAMINATION DETECTED!")
                for detail in contamination_details:
                    print(f"   - {detail}")
            
            print(f"\n✓ Session 1 cleared successfully: {session1_cleared}")
            print(f"✓ Session 1 works after clear: {session1_works}")
            print(f"✓ Session 2 unaffected: {session2_works}")
            
            # Overall verdict
            isolation_verified = (
                not contamination_found and
                session1_cleared and
                session1_works and
                session2_works
            )
            
            return {
                "test": "embedding_cache_isolation",
                "isolation_verified": isolation_verified,
                "contamination_found": contamination_found,
                "contamination_details": contamination_details,
                "session1_cleared": session1_cleared,
                "session1_works_after": session1_works,
                "session2_unaffected": session2_works
            }
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            return {
                "test": "embedding_cache_isolation",
                "error": str(e),
                "isolation_verified": False
            }
    
    async def test_rfp_text_cache_isolation(self):
        """Test RFP text cache isolation between sessions"""
        print("\n📄 Testing RFP Text Cache Isolation")
        print("-" * 50)
        
        try:
            session_id = self.generate_session_id()
            
            # Cache some RFP text
            print("   Caching test RFP text...")
            await self.client.post(
                f"{API_BASE_URL}/api/rfp/cache",
                data={"text": "Test RFP content for session isolation"}
            )
            
            # Get cached text
            cache_response = await self.client.get(f"{API_BASE_URL}/api/rfp/cache")
            has_cache_before = False
            if cache_response.status_code == 200:
                cached_text = cache_response.json().get('text', '')
                has_cache_before = bool(cached_text)
                print(f"   Cache before clear: {'Yes' if has_cache_before else 'No'}")
            
            # Clear session
            print(f"   Clearing session {session_id[:40]}...")
            clear_response = await self.client.post(
                f"{API_BASE_URL}/api/clear_session",
                json={"session_id": session_id}
            )
            
            clear_success = clear_response.status_code == 200
            
            # Check cache after clear
            cache_after = await self.client.get(f"{API_BASE_URL}/api/rfp/cache")
            has_cache_after = False
            if cache_after.status_code == 200:
                cached_text_after = cache_after.json().get('text', '')
                has_cache_after = bool(cached_text_after)
                print(f"   Cache after clear: {'Yes' if has_cache_after else 'No'}")
            
            # Results
            cache_cleared = has_cache_before and not has_cache_after
            
            print("\n📊 Results:")
            if cache_cleared:
                print("✅ RFP text cache properly cleared")
            else:
                print("❌ RFP text cache NOT cleared properly")
            
            return {
                "test": "rfp_text_cache_isolation",
                "cache_cleared": cache_cleared,
                "had_cache_before": has_cache_before,
                "has_cache_after": has_cache_after,
                "clear_success": clear_success
            }
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            return {
                "test": "rfp_text_cache_isolation",
                "error": str(e),
                "cache_cleared": False
            }
    
    async def test_unique_session_ids(self):
        """Test that session IDs are unique"""
        print("\n🔑 Testing Unique Session ID Generation")
        print("-" * 50)
        
        session_ids = []
        for i in range(10):
            session_id = self.generate_session_id()
            session_ids.append(session_id)
            await asyncio.sleep(0.001)
        
        unique_count = len(set(session_ids))
        all_unique = unique_count == len(session_ids)
        
        print(f"   Generated {len(session_ids)} session IDs")
        print(f"   Unique IDs: {unique_count}")
        
        if all_unique:
            print("✅ All session IDs are unique")
        else:
            print(f"❌ Found {len(session_ids) - unique_count} duplicate IDs")
        
        return {
            "test": "unique_session_ids",
            "all_unique": all_unique,
            "total_generated": len(session_ids),
            "unique_count": unique_count
        }
    
    async def run_all_tests(self):
        """Run all session isolation tests"""
        print("\n" + "="*60)
        print(" 🔐 SESSION ISOLATION TEST SUITE")
        print("="*60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        test_results = []
        
        # Run tests
        test_results.append(await self.test_unique_session_ids())
        test_results.append(await self.test_embedding_cache_isolation())
        test_results.append(await self.test_rfp_text_cache_isolation())
        
        # Summary
        print("\n" + "="*60)
        print(" 📊 TEST SUMMARY")
        print("="*60)
        
        all_passed = True
        for result in test_results:
            test_name = result.get('test', 'Unknown')
            if 'error' in result:
                print(f"❌ {test_name}: FAILED - {result['error']}")
                all_passed = False
            elif test_name == 'embedding_cache_isolation':
                if result.get('isolation_verified'):
                    print(f"✅ {test_name}: PASSED - No contamination detected")
                else:
                    print(f"❌ {test_name}: FAILED - Contamination detected")
                    all_passed = False
            elif test_name == 'rfp_text_cache_isolation':
                if result.get('cache_cleared'):
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
                    all_passed = False
            elif test_name == 'unique_session_ids':
                if result.get('all_unique'):
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
                    all_passed = False
        
        # Final Verdict
        print("\n" + "="*60)
        print(" 🔐 SESSION ISOLATION VERDICT")
        print("="*60)
        
        if all_passed:
            print("✅ ✅ ✅ SESSION ISOLATION VERIFIED ✅ ✅ ✅")
            print("   ✓ No cross-contamination between sessions")
            print("   ✓ Each session maintains independent context")
            print("   ✓ Session cleanup working correctly")
            print("   ✓ Unique session IDs generated properly")
        else:
            print("❌ SESSION ISOLATION ISSUES DETECTED")
            print("   Please review the test results above")
        
        # Save results
        results_file = f"test_results_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "all_passed": all_passed,
                "tests": test_results
            }, f, indent=2, default=str)
        
        print(f"\n📊 Results saved to: {results_file}")
        print("="*60)
        
        return all_passed

async def main():
    """Run the session isolation tests"""
    tester = SimpleSessionIsolationTest()
    
    try:
        await tester.setup()
        
        # Check server health
        health_response = await tester.client.get(f"{API_BASE_URL}/api/health")
        if health_response.status_code != 200:
            print("❌ Server health check failed")
            return 1
        
        print("✅ Server is healthy")
        
        # Run tests
        all_passed = await tester.run_all_tests()
        
        return 0 if all_passed else 1
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return 2
    finally:
        await tester.teardown()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)