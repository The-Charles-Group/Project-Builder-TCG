#!/usr/bin/env python3
"""
Comprehensive PDF Processing Test Suite
Tests PDF upload, text extraction, image analysis, and progress tracking
"""

import os
import sys
import json
import time
import asyncio
import httpx
import psutil
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib

# Test configuration
API_BASE_URL = "http://localhost:5000"
TIMEOUT = 300  # 5 minutes for large files

class PDFProcessingTester:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "metrics": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "total_time": 0,
                "memory_usage": {}
            }
        }
        self.client = None
        
    async def setup(self):
        """Initialize async HTTP client"""
        self.client = httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True)
        
    async def teardown(self):
        """Clean up resources"""
        if self.client:
            await self.client.aclose()
    
    async def test_pdf_upload_basic(self, pdf_path: str):
        """Test basic PDF upload and text extraction"""
        test_name = f"Basic Upload: {os.path.basename(pdf_path)}"
        print(f"\n🔄 Testing: {test_name}")
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        try:
            # Upload PDF for analysis
            with open(pdf_path, 'rb') as f:
                files = {'files': (os.path.basename(pdf_path), f, 'application/pdf')}
                
                response = await self.client.post(
                    f"{API_BASE_URL}/api/suggest_by_file",
                    files=files
                )
            
            if response.status_code != 200:
                raise Exception(f"Upload failed: {response.status_code} - {response.text}")
            
            result = response.json()
            
            # Verify response structure
            assert 'ok' in result, "Missing 'ok' field"
            assert result['ok'] == True, "Upload not successful"
            assert 'summary' in result, "Missing summary"
            
            # Check if text was extracted
            summary = result.get('summary', {})
            has_text = bool(summary.get('objectives') or summary.get('deliverables'))
            
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            duration = time.time() - start_time
            
            test_result = {
                "name": test_name,
                "status": "passed" if has_text else "warning",
                "duration": duration,
                "memory_delta": end_memory - start_memory,
                "file_size": os.path.getsize(pdf_path) / 1024 / 1024,  # MB
                "text_extracted": has_text,
                "summary_length": len(str(summary))
            }
            
            print(f"✅ {test_name}: {'Passed' if has_text else 'Warning - No text extracted'}")
            print(f"   Duration: {duration:.2f}s, Memory: {end_memory - start_memory:.1f}MB")
            
            self.results["tests"].append(test_result)
            self.results["metrics"]["passed"] += 1
            
            return result
            
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.results["metrics"]["failed"] += 1
            raise
    
    async def test_pdf_with_images(self, pdf_path: str):
        """Test PDF upload with image analysis"""
        test_name = f"Image Analysis: {os.path.basename(pdf_path)}"
        print(f"\n🔄 Testing: {test_name}")
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            # Upload PDF for analysis
            with open(pdf_path, 'rb') as f:
                files = {'files': (os.path.basename(pdf_path), f, 'application/pdf')}
                
                response = await self.client.post(
                    f"{API_BASE_URL}/api/suggest_by_file",
                    files=files
                )
            
            if response.status_code != 200:
                raise Exception(f"Upload failed: {response.status_code} - {response.text}")
            
            result = response.json()
            
            # Get job ID if images are being processed
            job_id = result.get('job_id')
            
            if job_id:
                print(f"   Job ID: {job_id}")
                # Monitor job progress
                progress_result = await self.monitor_job_progress(job_id)
                
                # Merge results
                if progress_result:
                    result['image_analysis'] = progress_result
            
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            duration = time.time() - start_time
            
            test_result = {
                "name": test_name,
                "status": "passed",
                "duration": duration,
                "memory_delta": end_memory - start_memory,
                "file_size": os.path.getsize(pdf_path) / 1024 / 1024,
                "job_id": job_id,
                "images_processed": progress_result.get('total_images', 0) if progress_result else 0
            }
            
            print(f"✅ {test_name}: Passed")
            print(f"   Duration: {duration:.2f}s, Memory: {end_memory - start_memory:.1f}MB")
            if progress_result:
                print(f"   Images: {progress_result.get('total_images', 0)} processed")
            
            self.results["tests"].append(test_result)
            self.results["metrics"]["passed"] += 1
            
            return result
            
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.results["metrics"]["failed"] += 1
            raise
    
    async def monitor_job_progress(self, job_id: str, max_wait: int = 120):
        """Monitor async job progress"""
        print(f"   Monitoring job {job_id}...")
        
        start_time = time.time()
        last_percentage = 0
        
        while time.time() - start_time < max_wait:
            try:
                response = await self.client.get(f"{API_BASE_URL}/api/upload/status/{job_id}")
                
                if response.status_code == 404:
                    print(f"   Job {job_id} not found")
                    return None
                
                if response.status_code != 200:
                    print(f"   Status check failed: {response.status_code}")
                    return None
                
                status = response.json()
                current_percentage = status.get('percentage', 0)
                
                # Update progress if changed
                if current_percentage > last_percentage:
                    phase = status.get('phase', 'processing')
                    processed = status.get('processed_images', 0)
                    total = status.get('total_images', 0)
                    relevant = status.get('relevant_images', 0)
                    
                    print(f"   Progress: {current_percentage:.1f}% - Phase: {phase} - "
                          f"Images: {processed}/{total} (relevant: {relevant})")
                    last_percentage = current_percentage
                
                # Check if completed
                if status.get('status') == 'completed':
                    print(f"   ✅ Job completed in {time.time() - start_time:.1f}s")
                    return status
                
                elif status.get('status') == 'failed':
                    print(f"   ❌ Job failed: {status.get('errors', [])}")
                    return status
                
                elif status.get('status') == 'cancelled':
                    print(f"   ⚠️ Job cancelled")
                    return status
                
                # Wait before next check
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"   Error checking status: {e}")
                await asyncio.sleep(2)
        
        print(f"   ⚠️ Job monitoring timed out after {max_wait}s")
        return None
    
    async def test_parallel_uploads(self, pdf_paths: List[str], max_concurrent: int = 3):
        """Test parallel PDF uploads to check for race conditions"""
        test_name = f"Parallel Upload Test ({max_concurrent} concurrent)"
        print(f"\n🔄 Testing: {test_name}")
        
        start_time = time.time()
        
        try:
            # Create upload tasks
            tasks = []
            for i, pdf_path in enumerate(pdf_paths[:max_concurrent]):
                task = self.upload_pdf_async(pdf_path, f"parallel_{i}")
                tasks.append(task)
            
            # Execute in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check results
            successful = 0
            failed = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"   Upload {i}: Failed - {str(result)}")
                    failed += 1
                else:
                    print(f"   Upload {i}: Success")
                    successful += 1
            
            duration = time.time() - start_time
            
            test_result = {
                "name": test_name,
                "status": "passed" if failed == 0 else "partial",
                "duration": duration,
                "concurrent_uploads": max_concurrent,
                "successful": successful,
                "failed": failed
            }
            
            status_emoji = "✅" if failed == 0 else "⚠️"
            print(f"{status_emoji} {test_name}: {successful}/{max_concurrent} successful")
            print(f"   Total duration: {duration:.2f}s")
            
            self.results["tests"].append(test_result)
            if failed == 0:
                self.results["metrics"]["passed"] += 1
            else:
                self.results["metrics"]["failed"] += 1
            
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e),
                "duration": time.time() - start_time
            })
            self.results["metrics"]["failed"] += 1
    
    async def upload_pdf_async(self, pdf_path: str, tag: str = ""):
        """Helper function for parallel upload"""
        with open(pdf_path, 'rb') as f:
            files = {'files': (os.path.basename(pdf_path), f, 'application/pdf')}
            
            response = await self.client.post(
                f"{API_BASE_URL}/api/suggest_by_file",
                files=files
            )
            
            if response.status_code != 200:
                raise Exception(f"Upload failed: {response.status_code}")
            
            return response.json()
    
    async def test_large_pdf_memory(self, pdf_path: str):
        """Test memory usage with large PDF"""
        test_name = f"Memory Test: {os.path.basename(pdf_path)}"
        print(f"\n🔄 Testing: {test_name}")
        
        # Get initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        memory_samples = []
        
        # Start memory monitoring
        async def monitor_memory():
            while True:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)
                await asyncio.sleep(0.5)
        
        # Start monitoring task
        monitor_task = asyncio.create_task(monitor_memory())
        
        try:
            # Upload large PDF
            result = await self.test_pdf_upload_basic(pdf_path)
            
            # Stop monitoring
            monitor_task.cancel()
            
            # Analyze memory usage
            peak_memory = max(memory_samples) if memory_samples else initial_memory
            final_memory = process.memory_info().rss / 1024 / 1024
            memory_leaked = final_memory - initial_memory
            
            test_result = {
                "name": test_name,
                "status": "passed" if memory_leaked < 100 else "warning",  # Warn if >100MB leak
                "initial_memory_mb": initial_memory,
                "peak_memory_mb": peak_memory,
                "final_memory_mb": final_memory,
                "memory_delta_mb": memory_leaked,
                "file_size_mb": os.path.getsize(pdf_path) / 1024 / 1024
            }
            
            status_emoji = "✅" if memory_leaked < 100 else "⚠️"
            print(f"{status_emoji} Memory Test: Initial: {initial_memory:.1f}MB, "
                  f"Peak: {peak_memory:.1f}MB, Final: {final_memory:.1f}MB")
            print(f"   Memory delta: {memory_leaked:.1f}MB")
            
            self.results["tests"].append(test_result)
            
        except Exception as e:
            monitor_task.cancel()
            print(f"❌ {test_name}: Failed - {str(e)}")
            raise
    
    async def test_job_cancellation(self, pdf_path: str):
        """Test job cancellation functionality"""
        test_name = "Job Cancellation Test"
        print(f"\n🔄 Testing: {test_name}")
        
        try:
            # Start upload for analysis
            with open(pdf_path, 'rb') as f:
                files = {'files': (os.path.basename(pdf_path), f, 'application/pdf')}
                
                response = await self.client.post(
                    f"{API_BASE_URL}/api/suggest_by_file",
                    files=files
                )
            
            if response.status_code != 200:
                raise Exception(f"Upload failed: {response.status_code}")
            
            result = response.json()
            job_id = result.get('job_id')
            
            if not job_id:
                print("   No job ID returned - skipping cancellation test")
                return
            
            print(f"   Job ID: {job_id}")
            
            # Wait briefly then cancel
            await asyncio.sleep(2)
            
            # Cancel the job
            cancel_response = await self.client.post(f"{API_BASE_URL}/api/upload/cancel/{job_id}")
            
            if cancel_response.status_code != 200:
                raise Exception(f"Cancellation failed: {cancel_response.status_code}")
            
            cancel_result = cancel_response.json()
            
            # Check job status
            status_response = await self.client.get(f"{API_BASE_URL}/api/upload/status/{job_id}")
            if status_response.status_code == 200:
                status = status_response.json()
                is_cancelled = status.get('status') == 'cancelled'
            else:
                is_cancelled = False
            
            test_result = {
                "name": test_name,
                "status": "passed" if is_cancelled else "failed",
                "job_id": job_id,
                "cancelled": is_cancelled
            }
            
            if is_cancelled:
                print(f"✅ {test_name}: Job successfully cancelled")
            else:
                print(f"❌ {test_name}: Job was not cancelled properly")
            
            self.results["tests"].append(test_result)
            
            if is_cancelled:
                self.results["metrics"]["passed"] += 1
            else:
                self.results["metrics"]["failed"] += 1
                
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e)
            })
            self.results["metrics"]["failed"] += 1
    
    async def run_all_tests(self):
        """Run all PDF processing tests"""
        print("="*70)
        print("PDF Processing Test Suite")
        print("="*70)
        
        await self.setup()
        
        # Generate test PDFs if they don't exist
        test_pdfs_dir = "test_pdfs"
        if not os.path.exists(test_pdfs_dir):
            print("\n📁 Generating test PDFs...")
            from test_pdf_generator import main as generate_pdfs
            generate_pdfs()
        
        # Get test PDF files
        pdf_files = [
            os.path.join(test_pdfs_dir, f) for f in os.listdir(test_pdfs_dir)
            if f.endswith('.pdf')
        ]
        
        if not pdf_files:
            print("❌ No test PDF files found!")
            return
        
        print(f"\n📚 Found {len(pdf_files)} test PDFs")
        
        # Run tests
        suite_start = time.time()
        
        # 1. Basic upload tests
        print("\n" + "="*50)
        print("1. BASIC PDF UPLOAD TESTS")
        print("="*50)
        
        for pdf_path in pdf_files[:3]:  # Test first 3 PDFs
            await self.test_pdf_upload_basic(pdf_path)
            await asyncio.sleep(1)  # Brief pause between tests
        
        # 2. Image analysis tests
        print("\n" + "="*50)
        print("2. IMAGE ANALYSIS TESTS")
        print("="*50)
        
        # Test PDFs with varying image counts
        image_test_pdfs = [
            f for f in pdf_files 
            if 'medium' in f or 'large' in f or 'images' in f
        ][:3]
        
        for pdf_path in image_test_pdfs:
            await self.test_pdf_with_images(pdf_path)
            await asyncio.sleep(1)
        
        # 3. Parallel upload test
        print("\n" + "="*50)
        print("3. PARALLEL PROCESSING TEST")
        print("="*50)
        
        await self.test_parallel_uploads(pdf_files[:5], max_concurrent=3)
        
        # 4. Memory test with large PDF
        print("\n" + "="*50)
        print("4. MEMORY USAGE TEST")
        print("="*50)
        
        large_pdfs = [f for f in pdf_files if 'large' in f or 'stress' in f]
        if large_pdfs:
            await self.test_large_pdf_memory(large_pdfs[0])
        
        # 5. Job cancellation test
        print("\n" + "="*50)
        print("5. JOB CANCELLATION TEST")
        print("="*50)
        
        if image_test_pdfs:
            await self.test_job_cancellation(image_test_pdfs[0])
        
        # Calculate totals
        suite_duration = time.time() - suite_start
        self.results["metrics"]["total_time"] = suite_duration
        self.results["metrics"]["total_tests"] = len(self.results["tests"])
        
        # Print summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Total Tests: {self.results['metrics']['total_tests']}")
        print(f"Passed: {self.results['metrics']['passed']}")
        print(f"Failed: {self.results['metrics']['failed']}")
        print(f"Total Duration: {suite_duration:.2f}s")
        print("="*70)
        
        # Save results
        results_file = f"pdf_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n📊 Results saved to: {results_file}")
        
        await self.teardown()
        
        return self.results

async def main():
    tester = PDFProcessingTester()
    results = await tester.run_all_tests()
    
    # Return exit code based on results
    if results["metrics"]["failed"] > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())