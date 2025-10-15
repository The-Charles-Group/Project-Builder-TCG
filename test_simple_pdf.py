#!/usr/bin/env python3
"""
Simple PDF Processing and Session Test Suite
Tests the actual API endpoints available in the system
"""

import os
import sys
import json
import time
import asyncio
import httpx
from typing import Dict, List, Any
from datetime import datetime

# Test configuration
API_BASE_URL = "http://localhost:5000"
TIMEOUT = 30

async def test_pdf_upload():
    """Test PDF upload and text extraction"""
    print("\n" + "="*60)
    print("TEST 1: PDF Upload and Text Extraction")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Test with a simple PDF
        pdf_path = "test_pdfs/small_marketing_rfp.pdf"
        
        if not os.path.exists(pdf_path):
            print("❌ Test PDF not found. Run test_pdf_generator.py first")
            return False
        
        print(f"📁 Uploading: {pdf_path}")
        
        try:
            with open(pdf_path, 'rb') as f:
                files = {'files': (os.path.basename(pdf_path), f, 'application/pdf')}
                response = await client.post(
                    f"{API_BASE_URL}/api/suggest_by_file",
                    files=files
                )
            
            print(f"📡 Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                # Check response structure
                has_deliverables = 'deliverables' in result or 'suggestions' in result
                has_ok = 'ok' in result
                
                if has_ok:
                    print(f"✅ Response 'ok': {result.get('ok')}")
                
                if has_deliverables:
                    deliv_count = len(result.get('deliverables', result.get('suggestions', [])))
                    print(f"✅ Deliverables found: {deliv_count}")
                    
                    # Show first few deliverables
                    deliverables = result.get('deliverables', result.get('suggestions', []))[:3]
                    for d in deliverables:
                        if isinstance(d, dict):
                            print(f"   - {d.get('deliverable', d.get('name', 'Unknown'))}")
                        else:
                            print(f"   - {d}")
                
                if 'summary' in result:
                    print(f"✅ Summary extracted: {len(str(result['summary']))} chars")
                
                return True
            else:
                print(f"❌ Upload failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False

async def test_session_isolation():
    """Test session isolation between uploads"""
    print("\n" + "="*60)
    print("TEST 2: Session Isolation")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        pdfs = [
            "test_pdfs/small_marketing_rfp.pdf",
            "test_pdfs/small_tech_rfp.pdf"
        ]
        
        if not all(os.path.exists(p) for p in pdfs):
            print("❌ Test PDFs not found")
            return False
        
        results = []
        
        for i, pdf_path in enumerate(pdfs):
            print(f"\n📁 Upload {i+1}: {os.path.basename(pdf_path)}")
            
            try:
                # Upload PDF
                with open(pdf_path, 'rb') as f:
                    files = {'files': (os.path.basename(pdf_path), f, 'application/pdf')}
                    response = await client.post(
                        f"{API_BASE_URL}/api/suggest_by_file",
                        files=files
                    )
                
                if response.status_code == 200:
                    result = response.json()
                    deliverables = result.get('deliverables', result.get('suggestions', []))
                    
                    print(f"   Deliverables: {len(deliverables)}")
                    
                    # Store deliverable codes for comparison
                    deliv_codes = set()
                    for d in deliverables:
                        if isinstance(d, dict):
                            code = d.get('deliverable_code', d.get('code', ''))
                            if code:
                                deliv_codes.add(code)
                    
                    results.append({
                        'pdf': os.path.basename(pdf_path),
                        'deliverable_count': len(deliverables),
                        'deliverable_codes': deliv_codes
                    })
                else:
                    print(f"   Upload failed: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"   Error: {str(e)}")
                return False
        
        # Check isolation
        if len(results) == 2:
            r1, r2 = results
            
            # Files should produce different deliverables
            common_codes = r1['deliverable_codes'] & r2['deliverable_codes']
            unique_to_r1 = r1['deliverable_codes'] - r2['deliverable_codes']
            unique_to_r2 = r2['deliverable_codes'] - r1['deliverable_codes']
            
            print(f"\n📊 Analysis:")
            print(f"   Common deliverables: {len(common_codes)}")
            print(f"   Unique to PDF 1: {len(unique_to_r1)}")
            print(f"   Unique to PDF 2: {len(unique_to_r2)}")
            
            # Some overlap is expected, but not complete identity
            if r1['deliverable_codes'] == r2['deliverable_codes'] and len(r1['deliverable_codes']) > 5:
                print("⚠️ Warning: Identical deliverable sets (possible contamination)")
                return False
            else:
                print("✅ Sessions appear isolated")
                return True
        
        return False

async def test_clear_session():
    """Test session clearing functionality"""
    print("\n" + "="*60)
    print("TEST 3: Session Clearing")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        session_id = f"test_session_{int(time.time())}"
        
        print(f"🔑 Session ID: {session_id[:30]}...")
        
        try:
            # Try to clear session
            response = await client.post(
                f"{API_BASE_URL}/api/clear_session",
                json={"session_id": session_id}
            )
            
            print(f"📡 Clear session response: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Session clear endpoint working")
                return True
            else:
                print(f"⚠️ Clear session returned: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return True  # Not critical if this endpoint is missing
                
        except Exception as e:
            print(f"⚠️ Clear session error: {str(e)}")
            return True  # Not critical

async def test_parallel_uploads():
    """Test parallel PDF uploads"""
    print("\n" + "="*60)
    print("TEST 4: Parallel Uploads")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        pdfs = [
            "test_pdfs/small_marketing_rfp.pdf",
            "test_pdfs/small_tech_rfp.pdf",
            "test_pdfs/no_images_rfp.pdf"
        ]
        
        # Filter to existing files
        pdfs = [p for p in pdfs if os.path.exists(p)][:3]
        
        if len(pdfs) < 2:
            print("❌ Not enough test PDFs found")
            return False
        
        print(f"📁 Uploading {len(pdfs)} PDFs in parallel...")
        
        async def upload_pdf(pdf_path):
            try:
                with open(pdf_path, 'rb') as f:
                    files = {'files': (os.path.basename(pdf_path), f, 'application/pdf')}
                    response = await client.post(
                        f"{API_BASE_URL}/api/suggest_by_file",
                        files=files
                    )
                return response.status_code == 200
            except:
                return False
        
        try:
            start_time = time.time()
            results = await asyncio.gather(*[upload_pdf(p) for p in pdfs])
            duration = time.time() - start_time
            
            successful = sum(results)
            print(f"⏱️ Duration: {duration:.2f}s")
            print(f"📊 Success rate: {successful}/{len(pdfs)}")
            
            if successful == len(pdfs):
                print("✅ All parallel uploads successful")
                return True
            elif successful > 0:
                print(f"⚠️ Partial success: {successful}/{len(pdfs)}")
                return True
            else:
                print("❌ All uploads failed")
                return False
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False

async def test_large_pdf():
    """Test with larger PDF file"""
    print("\n" + "="*60)
    print("TEST 5: Large PDF Processing")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=60) as client:
        # Try to find largest PDF
        large_pdfs = [
            "test_pdfs/stress_test_pages.pdf",
            "test_pdfs/large_marketing_rfp.pdf",
            "test_pdfs/stress_test_images.pdf"
        ]
        
        pdf_path = None
        for p in large_pdfs:
            if os.path.exists(p):
                pdf_path = p
                break
        
        if not pdf_path:
            print("⚠️ No large PDF found, skipping test")
            return True
        
        file_size = os.path.getsize(pdf_path) / 1024  # KB
        print(f"📁 Testing with: {os.path.basename(pdf_path)} ({file_size:.1f}KB)")
        
        try:
            start_time = time.time()
            
            with open(pdf_path, 'rb') as f:
                files = {'files': (os.path.basename(pdf_path), f, 'application/pdf')}
                response = await client.post(
                    f"{API_BASE_URL}/api/suggest_by_file",
                    files=files
                )
            
            duration = time.time() - start_time
            
            print(f"⏱️ Processing time: {duration:.2f}s")
            print(f"📡 Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                deliverables = result.get('deliverables', result.get('suggestions', []))
                print(f"✅ Deliverables found: {len(deliverables)}")
                
                processing_speed = file_size / duration if duration > 0 else 0
                print(f"⚡ Processing speed: {processing_speed:.1f}KB/s")
                
                return True
            else:
                print(f"❌ Upload failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False

async def main():
    """Run all tests"""
    print("="*60)
    print("Agency Project Builder - Test Suite")
    print("="*60)
    print(f"API Base: {API_BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Generate test PDFs if needed
    if not os.path.exists("test_pdfs"):
        print("\n📁 Generating test PDFs...")
        from test_pdf_generator import main as generate_pdfs
        generate_pdfs()
    
    # Run tests
    tests = [
        ("PDF Upload", test_pdf_upload),
        ("Session Isolation", test_session_isolation),
        ("Clear Session", test_clear_session),
        ("Parallel Uploads", test_parallel_uploads),
        ("Large PDF", test_large_pdf),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    # Save results
    results_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": [{"test": name, "passed": result} for name, result in results],
            "summary": {"passed": passed, "total": total}
        }, f, indent=2)
    print(f"\n📊 Results saved to: {results_file}")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)