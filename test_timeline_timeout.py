#!/usr/bin/env python3
"""
Test script to verify timeline generation works with the new timeout settings.
This will test with various numbers of deliverables to ensure no timeouts occur.
"""
import asyncio
import aiohttp
import json
import time

async def test_timeline_with_deliverables(num_deliverables=5):
    """Test timeline generation with specified number of deliverables"""
    base_url = "http://localhost:5000"
    
    print(f"\n{'='*60}")
    print(f"Testing timeline generation with {num_deliverables} deliverables")
    print("="*60)
    
    # Create test deliverables
    deliverables = []
    for i in range(num_deliverables):
        deliverables.append({
            "deliverable_code": f"DEL-{i+1:03d}",
            "deliverable": f"Test Deliverable {i+1}",
            "department": ["Strategy", "Creative", "Technology", "Paid Media"][i % 4],
            "hours": 40 + (i * 10),
            "price": 6000 + (i * 1500),
            "components": [
                {
                    "name": f"Component {j+1} for Deliverable {i+1}",
                    "hours": 10
                }
                for j in range(3)  # 3 components per deliverable
            ]
        })
    
    request_data = {
        "deliverables": deliverables,
        "rfp_text": "Test RFP for timeline generation with multiple deliverables to verify timeout handling.",
        "project_start": "2025-12-01",
        "optimization_mode": "balanced",
        "use_intelligent_scheduler": True
    }
    
    start_time = time.time()
    
    try:
        async with aiohttp.ClientSession() as session:
            # Step 1: Start timeline generation
            print(f"  → Starting timeline generation...")
            async with session.post(
                f"{base_url}/api/ai/generate_timeline",
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=300)  # 5 minute timeout for the request itself
            ) as resp:
                if resp.status != 200:
                    print(f"  ❌ Failed to start: {resp.status}")
                    error_text = await resp.text()
                    print(f"     Error: {error_text[:200]}")
                    return False
                
                result = await resp.json()
                job_id = result.get('job_id')
                print(f"  ✅ Job started: {job_id}")
            
            if not job_id:
                print("  ❌ No job_id returned")
                return False
            
            # Step 2: Monitor SSE stream
            print(f"  → Monitoring progress via SSE...")
            last_progress = 0
            event_count = 0
            
            async with session.get(
                f"{base_url}/api/stream/{job_id}",
                timeout=aiohttp.ClientTimeout(total=300)
            ) as resp:
                if resp.status != 200:
                    print(f"  ❌ Failed to connect to stream: {resp.status}")
                    return False
                
                async for line in resp.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        event_count += 1
                        try:
                            event_data = json.loads(line[6:])
                            status = event_data.get('status', '')
                            progress = event_data.get('progress', 0)
                            message = event_data.get('message', '')
                            
                            if progress > last_progress or event_count % 10 == 0:
                                elapsed = time.time() - start_time
                                print(f"     [{elapsed:.1f}s] {status}: {message} ({progress:.1f}%)")
                                last_progress = progress
                            
                            if status in ['completed', 'failed']:
                                elapsed = time.time() - start_time
                                if status == 'completed':
                                    print(f"  ✅ Timeline generated successfully in {elapsed:.1f} seconds!")
                                    print(f"     Total events received: {event_count}")
                                    return True
                                else:
                                    print(f"  ❌ Generation failed after {elapsed:.1f} seconds")
                                    print(f"     Error: {message}")
                                    return False
                        except json.JSONDecodeError:
                            continue
            
            elapsed = time.time() - start_time
            print(f"  ⚠️ Stream ended without completion after {elapsed:.1f} seconds")
            return False
            
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print(f"  ❌ Client timeout after {elapsed:.1f} seconds")
        return False
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  ❌ Error after {elapsed:.1f} seconds: {e}")
        return False

async def main():
    """Run tests with different numbers of deliverables"""
    print("\n" + "="*60)
    print("TIMELINE GENERATION TIMEOUT TEST")
    print("Testing with new 180s base + 5s/deliverable timeout")
    print("="*60)
    
    # Test with increasing numbers of deliverables
    test_cases = [
        (3, "Small project"),
        (8, "Medium project"),
        (15, "Large project"),
        (20, "Very large project")
    ]
    
    results = []
    
    for num_deliverables, description in test_cases:
        print(f"\n### Test Case: {description}")
        success = await test_timeline_with_deliverables(num_deliverables)
        results.append((description, num_deliverables, success))
        
        if not success:
            print(f"\n⚠️ Stopping tests due to failure")
            break
        
        # Small delay between tests
        await asyncio.sleep(2)
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for description, num, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {description} ({num} deliverables): {status}")
    
    all_passed = all(r[2] for r in results)
    if all_passed:
        print("\n🎉 All tests passed! Timeline generation handles complex projects without timeout.")
    else:
        print("\n⚠️ Some tests failed. Timeline generation may still have issues.")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)