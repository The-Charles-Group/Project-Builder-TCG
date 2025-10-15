#!/usr/bin/env python3
"""
Performance Test Suite
Tests system performance with large files, concurrent operations, and memory usage
"""

import os
import sys
import json
import time
import asyncio
import httpx
import psutil
import gc
from typing import Dict, List, Any, Optional
from datetime import datetime
import tracemalloc

# Test configuration
API_BASE_URL = "http://localhost:5000"
TIMEOUT = 600  # 10 minutes for stress tests

class PerformanceTester:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "performance_metrics": {
                "peak_memory_mb": 0,
                "peak_cpu_percent": 0,
                "total_runtime": 0,
                "requests_per_second": 0
            },
            "resource_usage": []
        }
        self.client = None
        self.monitoring = False
        self.process = psutil.Process()
        
    async def setup(self):
        """Initialize async HTTP client and monitoring"""
        self.client = httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True)
        tracemalloc.start()
        
    async def teardown(self):
        """Clean up resources"""
        if self.client:
            await self.client.aclose()
        tracemalloc.stop()
        gc.collect()
    
    async def monitor_resources(self, interval: float = 0.5):
        """Monitor system resources during tests"""
        self.monitoring = True
        resource_samples = []
        
        while self.monitoring:
            try:
                # Get current resource usage
                memory_mb = self.process.memory_info().rss / 1024 / 1024
                cpu_percent = self.process.cpu_percent()
                
                sample = {
                    "timestamp": time.time(),
                    "memory_mb": memory_mb,
                    "cpu_percent": cpu_percent,
                    "num_threads": self.process.num_threads()
                }
                
                resource_samples.append(sample)
                
                # Update peaks
                if memory_mb > self.results["performance_metrics"]["peak_memory_mb"]:
                    self.results["performance_metrics"]["peak_memory_mb"] = memory_mb
                if cpu_percent > self.results["performance_metrics"]["peak_cpu_percent"]:
                    self.results["performance_metrics"]["peak_cpu_percent"] = cpu_percent
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                print(f"   Resource monitoring error: {e}")
                break
        
        # Save samples for analysis
        self.results["resource_usage"] = resource_samples[-100:]  # Keep last 100 samples
    
    async def test_large_pdf_processing(self):
        """Test processing of large PDF files"""
        test_name = "Large PDF Processing (100+ pages)"
        print(f"\n🔄 Testing: {test_name}")
        
        # Generate or use large test PDF
        test_pdfs_dir = "test_pdfs"
        large_pdf = os.path.join(test_pdfs_dir, "stress_test_pages.pdf")
        
        if not os.path.exists(large_pdf):
            print("   Generating large test PDF...")
            from test_pdf_generator import create_test_pdf
            large_pdf = create_test_pdf(large_pdf, num_images=20, num_pages=100, category="construction")
        
        file_size_mb = os.path.getsize(large_pdf) / 1024 / 1024
        print(f"   PDF size: {file_size_mb:.1f}MB")
        
        # Start resource monitoring
        monitor_task = asyncio.create_task(self.monitor_resources())
        
        try:
            start_time = time.time()
            start_memory = self.process.memory_info().rss / 1024 / 1024
            
            # Take memory snapshot before
            snapshot1 = tracemalloc.take_snapshot()
            
            # Upload large PDF
            with open(large_pdf, 'rb') as f:
                files = {'file': (os.path.basename(large_pdf), f, 'application/pdf')}
                data = {'analyze_images': 'true'}
                
                response = await self.client.post(
                    f"{API_BASE_URL}/api/upload",
                    files=files,
                    data=data
                )
            
            if response.status_code != 200:
                raise Exception(f"Upload failed: {response.status_code}")
            
            result = response.json()
            job_id = result.get('job_id')
            
            # Wait for job completion if processing images
            if job_id:
                print(f"   Monitoring job {job_id}...")
                job_start = time.time()
                
                while time.time() - job_start < 300:  # 5 minute timeout
                    status_response = await self.client.get(f"{API_BASE_URL}/api/upload/status/{job_id}")
                    if status_response.status_code == 200:
                        status = status_response.json()
                        if status.get('status') in ['completed', 'failed', 'cancelled']:
                            break
                    await asyncio.sleep(2)
            
            # Take memory snapshot after
            snapshot2 = tracemalloc.take_snapshot()
            
            # Stop monitoring
            self.monitoring = False
            await monitor_task
            
            # Calculate metrics
            duration = time.time() - start_time
            end_memory = self.process.memory_info().rss / 1024 / 1024
            memory_delta = end_memory - start_memory
            
            # Get top memory allocations
            top_stats = snapshot2.compare_to(snapshot1, 'lineno')[:10]
            
            test_result = {
                "name": test_name,
                "status": "passed" if duration < 300 else "warning",  # Warn if >5 minutes
                "duration_seconds": duration,
                "file_size_mb": file_size_mb,
                "memory_used_mb": memory_delta,
                "peak_memory_mb": self.results["performance_metrics"]["peak_memory_mb"],
                "processing_speed_mb_per_sec": file_size_mb / duration if duration > 0 else 0
            }
            
            status_emoji = "✅" if duration < 300 else "⚠️"
            print(f"{status_emoji} {test_name}")
            print(f"   Duration: {duration:.1f}s")
            print(f"   Speed: {file_size_mb / duration:.2f}MB/s")
            print(f"   Memory used: {memory_delta:.1f}MB")
            print(f"   Peak memory: {self.results['performance_metrics']['peak_memory_mb']:.1f}MB")
            
            self.results["tests"].append(test_result)
            
        except Exception as e:
            self.monitoring = False
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e)
            })
        
        finally:
            self.monitoring = False
            gc.collect()
    
    async def test_concurrent_uploads(self):
        """Test system performance with concurrent uploads"""
        test_name = "Concurrent Upload Performance"
        print(f"\n🔄 Testing: {test_name}")
        
        test_pdfs_dir = "test_pdfs"
        test_pdfs = [
            os.path.join(test_pdfs_dir, f)
            for f in os.listdir(test_pdfs_dir)
            if f.endswith('.pdf')
        ][:10]  # Use up to 10 PDFs
        
        if len(test_pdfs) < 5:
            print("   Generating test PDFs...")
            from test_pdf_generator import main as generate_pdfs
            generate_pdfs()
            test_pdfs = [
                os.path.join(test_pdfs_dir, f)
                for f in os.listdir(test_pdfs_dir)
                if f.endswith('.pdf')
            ][:10]
        
        concurrent_counts = [1, 3, 5, 10]
        results_by_concurrency = []
        
        # Start resource monitoring
        monitor_task = asyncio.create_task(self.monitor_resources())
        
        try:
            for concurrent in concurrent_counts:
                if concurrent > len(test_pdfs):
                    continue
                
                print(f"\n   Testing {concurrent} concurrent uploads...")
                
                start_time = time.time()
                start_memory = self.process.memory_info().rss / 1024 / 1024
                
                # Create upload tasks
                tasks = []
                for i in range(concurrent):
                    pdf_path = test_pdfs[i % len(test_pdfs)]
                    task = self.upload_pdf_async(pdf_path)
                    tasks.append(task)
                
                # Execute concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                duration = time.time() - start_time
                end_memory = self.process.memory_info().rss / 1024 / 1024
                
                # Count successes
                successful = sum(1 for r in results if not isinstance(r, Exception))
                failed = concurrent - successful
                
                # Calculate throughput
                requests_per_second = successful / duration if duration > 0 else 0
                
                result = {
                    "concurrent_uploads": concurrent,
                    "successful": successful,
                    "failed": failed,
                    "duration_seconds": duration,
                    "requests_per_second": requests_per_second,
                    "memory_used_mb": end_memory - start_memory,
                    "avg_time_per_request": duration / concurrent if concurrent > 0 else 0
                }
                
                results_by_concurrency.append(result)
                
                print(f"   ✓ {concurrent} concurrent: {successful}/{concurrent} successful")
                print(f"     Duration: {duration:.1f}s, RPS: {requests_per_second:.2f}")
                
                # Brief pause between tests
                await asyncio.sleep(2)
                gc.collect()
            
            # Stop monitoring
            self.monitoring = False
            await monitor_task
            
            # Find optimal concurrency
            best_rps = max(r["requests_per_second"] for r in results_by_concurrency)
            optimal = next(r["concurrent_uploads"] for r in results_by_concurrency 
                         if r["requests_per_second"] == best_rps)
            
            test_result = {
                "name": test_name,
                "status": "passed",
                "results_by_concurrency": results_by_concurrency,
                "optimal_concurrency": optimal,
                "best_rps": best_rps,
                "peak_memory_mb": self.results["performance_metrics"]["peak_memory_mb"]
            }
            
            print(f"\n✅ {test_name}")
            print(f"   Optimal concurrency: {optimal}")
            print(f"   Best RPS: {best_rps:.2f}")
            
            self.results["tests"].append(test_result)
            self.results["performance_metrics"]["requests_per_second"] = best_rps
            
        except Exception as e:
            self.monitoring = False
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e)
            })
        
        finally:
            self.monitoring = False
    
    async def upload_pdf_async(self, pdf_path: str):
        """Helper for concurrent upload test"""
        with open(pdf_path, 'rb') as f:
            files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
            data = {'analyze_images': 'false'}
            
            response = await self.client.post(
                f"{API_BASE_URL}/api/upload",
                files=files,
                data=data
            )
            
            if response.status_code != 200:
                raise Exception(f"Upload failed: {response.status_code}")
            
            return response.json()
    
    async def test_memory_leaks(self):
        """Test for memory leaks with repeated operations"""
        test_name = "Memory Leak Detection"
        print(f"\n🔄 Testing: {test_name}")
        
        test_pdfs_dir = "test_pdfs"
        test_pdf = os.path.join(test_pdfs_dir, "small_marketing_rfp.pdf")
        
        if not os.path.exists(test_pdf):
            from test_pdf_generator import create_test_pdf
            test_pdf = create_test_pdf(test_pdf, num_images=3, num_pages=5)
        
        num_iterations = 20
        memory_samples = []
        
        try:
            print(f"   Running {num_iterations} iterations...")
            
            # Force garbage collection before starting
            gc.collect()
            initial_memory = self.process.memory_info().rss / 1024 / 1024
            
            for i in range(num_iterations):
                # Upload and process
                with open(test_pdf, 'rb') as f:
                    files = {'file': (os.path.basename(test_pdf), f, 'application/pdf')}
                    data = {'analyze_images': 'false'}
                    
                    response = await self.client.post(
                        f"{API_BASE_URL}/api/upload",
                        files=files,
                        data=data
                    )
                
                if response.status_code != 200:
                    print(f"   Iteration {i+1} failed: {response.status_code}")
                    continue
                
                # Force garbage collection
                gc.collect()
                
                # Measure memory
                current_memory = self.process.memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)
                
                if (i + 1) % 5 == 0:
                    print(f"   Iteration {i+1}/{num_iterations}: Memory: {current_memory:.1f}MB")
                
                # Small delay between iterations
                await asyncio.sleep(0.5)
            
            # Analyze memory trend
            final_memory = memory_samples[-1]
            memory_growth = final_memory - initial_memory
            avg_growth_per_iteration = memory_growth / num_iterations
            
            # Calculate linear regression to detect trend
            import numpy as np
            x = np.arange(len(memory_samples))
            y = np.array(memory_samples)
            slope, intercept = np.polyfit(x, y, 1)
            
            # Leak detected if consistent growth (slope > 0.5 MB per iteration)
            has_leak = slope > 0.5
            
            test_result = {
                "name": test_name,
                "status": "failed" if has_leak else "passed",
                "iterations": num_iterations,
                "initial_memory_mb": initial_memory,
                "final_memory_mb": final_memory,
                "total_growth_mb": memory_growth,
                "avg_growth_per_iteration_mb": avg_growth_per_iteration,
                "memory_slope_mb_per_iteration": float(slope),
                "potential_leak": has_leak
            }
            
            if has_leak:
                print(f"❌ {test_name}: Potential memory leak detected!")
                print(f"   Memory growth: {memory_growth:.1f}MB over {num_iterations} iterations")
                print(f"   Average growth: {avg_growth_per_iteration:.2f}MB per iteration")
            else:
                print(f"✅ {test_name}: No memory leak detected")
                print(f"   Memory stable: {initial_memory:.1f}MB → {final_memory:.1f}MB")
            
            self.results["tests"].append(test_result)
            
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e)
            })
    
    async def test_stress_many_images(self):
        """Stress test with PDF containing many images"""
        test_name = "Stress Test: Many Images (50+)"
        print(f"\n🔄 Testing: {test_name}")
        
        test_pdfs_dir = "test_pdfs"
        stress_pdf = os.path.join(test_pdfs_dir, "stress_test_images.pdf")
        
        if not os.path.exists(stress_pdf):
            print("   Generating stress test PDF with 50 images...")
            from test_pdf_generator import create_test_pdf
            stress_pdf = create_test_pdf(stress_pdf, num_images=50, num_pages=30, category="technology")
        
        file_size_mb = os.path.getsize(stress_pdf) / 1024 / 1024
        print(f"   PDF size: {file_size_mb:.1f}MB with 50 images")
        
        # Start resource monitoring
        monitor_task = asyncio.create_task(self.monitor_resources())
        
        try:
            start_time = time.time()
            start_memory = self.process.memory_info().rss / 1024 / 1024
            
            # Upload PDF with image analysis
            with open(stress_pdf, 'rb') as f:
                files = {'file': (os.path.basename(stress_pdf), f, 'application/pdf')}
                data = {'analyze_images': 'true'}
                
                response = await self.client.post(
                    f"{API_BASE_URL}/api/upload",
                    files=files,
                    data=data
                )
            
            if response.status_code != 200:
                raise Exception(f"Upload failed: {response.status_code}")
            
            result = response.json()
            job_id = result.get('job_id')
            
            # Monitor job progress
            if job_id:
                print(f"   Processing images (Job: {job_id})...")
                job_start = time.time()
                last_progress = 0
                
                while time.time() - job_start < 600:  # 10 minute timeout
                    status_response = await self.client.get(f"{API_BASE_URL}/api/upload/status/{job_id}")
                    
                    if status_response.status_code == 200:
                        status = status_response.json()
                        progress = status.get('percentage', 0)
                        
                        if progress > last_progress + 10:  # Update every 10%
                            print(f"   Progress: {progress:.0f}% - "
                                  f"Processed: {status.get('processed_images', 0)}/{status.get('total_images', 0)}")
                            last_progress = progress
                        
                        if status.get('status') in ['completed', 'failed', 'cancelled']:
                            print(f"   Job {status.get('status')}")
                            break
                    
                    await asyncio.sleep(2)
            
            # Stop monitoring
            self.monitoring = False
            await monitor_task
            
            duration = time.time() - start_time
            end_memory = self.process.memory_info().rss / 1024 / 1024
            memory_used = end_memory - start_memory
            
            test_result = {
                "name": test_name,
                "status": "passed" if duration < 600 else "warning",
                "duration_seconds": duration,
                "file_size_mb": file_size_mb,
                "images_count": 50,
                "memory_used_mb": memory_used,
                "peak_memory_mb": self.results["performance_metrics"]["peak_memory_mb"],
                "peak_cpu_percent": self.results["performance_metrics"]["peak_cpu_percent"],
                "avg_time_per_image": duration / 50
            }
            
            status_emoji = "✅" if duration < 600 else "⚠️"
            print(f"{status_emoji} {test_name}")
            print(f"   Duration: {duration:.1f}s ({duration/50:.1f}s per image)")
            print(f"   Memory used: {memory_used:.1f}MB")
            print(f"   Peak CPU: {self.results['performance_metrics']['peak_cpu_percent']:.1f}%")
            
            self.results["tests"].append(test_result)
            
        except Exception as e:
            self.monitoring = False
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e)
            })
        
        finally:
            self.monitoring = False
            gc.collect()
    
    async def test_api_response_times(self):
        """Test API endpoint response times"""
        test_name = "API Response Time Analysis"
        print(f"\n🔄 Testing: {test_name}")
        
        endpoints = [
            ("/api/options", "GET", None),
            ("/api/load", "GET", None),
            ("/api/clear_session", "POST", {"session_id": "test_session"}),
        ]
        
        response_times = {}
        
        try:
            for endpoint, method, data in endpoints:
                times = []
                
                print(f"   Testing {method} {endpoint}...")
                
                # Run multiple requests to get average
                for _ in range(10):
                    start = time.time()
                    
                    if method == "GET":
                        response = await self.client.get(f"{API_BASE_URL}{endpoint}")
                    else:
                        response = await self.client.post(
                            f"{API_BASE_URL}{endpoint}",
                            json=data if data else {}
                        )
                    
                    duration = time.time() - start
                    times.append(duration * 1000)  # Convert to ms
                    
                    await asyncio.sleep(0.1)  # Small delay between requests
                
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                
                response_times[endpoint] = {
                    "method": method,
                    "avg_ms": avg_time,
                    "min_ms": min_time,
                    "max_ms": max_time
                }
                
                print(f"     Avg: {avg_time:.1f}ms, Min: {min_time:.1f}ms, Max: {max_time:.1f}ms")
            
            # Check if any endpoints are slow
            slow_endpoints = [
                ep for ep, times in response_times.items()
                if times["avg_ms"] > 1000  # Warn if >1 second
            ]
            
            test_result = {
                "name": test_name,
                "status": "warning" if slow_endpoints else "passed",
                "response_times": response_times,
                "slow_endpoints": slow_endpoints
            }
            
            if slow_endpoints:
                print(f"⚠️ {test_name}: Some endpoints are slow")
                for ep in slow_endpoints:
                    print(f"   {ep}: {response_times[ep]['avg_ms']:.1f}ms average")
            else:
                print(f"✅ {test_name}: All endpoints responsive")
            
            self.results["tests"].append(test_result)
            
        except Exception as e:
            print(f"❌ {test_name}: Failed - {str(e)}")
            self.results["tests"].append({
                "name": test_name,
                "status": "failed",
                "error": str(e)
            })
    
    async def run_all_tests(self):
        """Run all performance tests"""
        print("="*70)
        print("Performance Test Suite")
        print("="*70)
        
        await self.setup()
        
        suite_start = time.time()
        
        # Run tests
        await self.test_api_response_times()
        await self.test_large_pdf_processing()
        await self.test_concurrent_uploads()
        await self.test_memory_leaks()
        await self.test_stress_many_images()
        
        suite_duration = time.time() - suite_start
        self.results["performance_metrics"]["total_runtime"] = suite_duration
        
        # Calculate summary
        total_tests = len(self.results["tests"])
        passed = sum(1 for t in self.results["tests"] if t["status"] == "passed")
        failed = sum(1 for t in self.results["tests"] if t["status"] == "failed")
        warnings = sum(1 for t in self.results["tests"] if t["status"] == "warning")
        
        # Print summary
        print("\n" + "="*70)
        print("PERFORMANCE TEST SUMMARY")
        print("="*70)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Warnings: {warnings}")
        print(f"Total Duration: {suite_duration:.1f}s")
        print("\nPERFORMANCE METRICS:")
        print(f"  Peak Memory: {self.results['performance_metrics']['peak_memory_mb']:.1f}MB")
        print(f"  Peak CPU: {self.results['performance_metrics']['peak_cpu_percent']:.1f}%")
        print(f"  Best RPS: {self.results['performance_metrics']['requests_per_second']:.2f}")
        
        if failed > 0:
            print("\n⚠️ FAILED TESTS:")
            for test in self.results["tests"]:
                if test["status"] == "failed":
                    print(f"  - {test['name']}: {test.get('error', 'Unknown error')}")
        
        print("="*70)
        
        # Save results
        results_file = f"performance_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n📊 Results saved to: {results_file}")
        
        await self.teardown()
        
        return self.results

async def main():
    tester = PerformanceTester()
    results = await tester.run_all_tests()
    
    # Return exit code based on results
    if any(t["status"] == "failed" for t in results["tests"]):
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())