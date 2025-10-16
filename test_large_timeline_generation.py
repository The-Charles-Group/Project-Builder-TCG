#!/usr/bin/env python3
"""
Test script to verify timeline generation works with large numbers of deliverables.
Tests the SSE-based solution with heartbeat mechanism and polling fallback.
"""

import asyncio
import aiohttp
import json
import time
import sys
from typing import List, Dict, Any

# Configuration
BASE_URL = "http://localhost:5000"
TEST_CONFIGS = [
    {"name": "Small Project", "count": 10, "timeout": 120},
    {"name": "Medium Project", "count": 20, "timeout": 180},
    {"name": "Large Project", "count": 50, "timeout": 300},
    {"name": "Enterprise Project", "count": 100, "timeout": 600},
    {"name": "Massive Project", "count": 150, "timeout": 900},
]

# Department rotation for realistic test data
DEPARTMENTS = ["Strategy", "Creative", "Technology", "Paid Media", "Content"]

def generate_test_deliverables(count: int) -> List[Dict[str, Any]]:
    """Generate test deliverables with realistic data."""
    deliverables = []
    
    for i in range(count):
        # Vary the complexity based on position
        if i < count * 0.2:  # 20% are simple
            components_count = 2
            base_hours = 20
        elif i < count * 0.7:  # 50% are medium
            components_count = 3
            base_hours = 40
        else:  # 30% are complex
            components_count = 5
            base_hours = 80
        
        deliverable = {
            "deliverable_code": f"DEL-{i+1:04d}",
            "deliverable": f"Deliverable {i+1}: {'Complex' if components_count > 3 else 'Standard'} Task",
            "department": DEPARTMENTS[i % len(DEPARTMENTS)],
            "hours": base_hours + (i * 5),
            "price": (base_hours * 150) + (i * 500),
            "components": [
                {
                    "name": f"Component {j+1} for Deliverable {i+1}",
                    "hours": base_hours / components_count
                }
                for j in range(components_count)
            ]
        }
        
        # Add some retainer deliverables for variety
        if i % 15 == 0 and i > 0:
            deliverable["is_retainer"] = True
            deliverable["retainer_months"] = 6
        
        deliverables.append(deliverable)
    
    return deliverables

async def test_sse_connection(session: aiohttp.ClientSession, job_id: str, max_duration: int) -> Dict[str, Any]:
    """Test SSE streaming with heartbeat monitoring."""
    print(f"  📡 Connecting to SSE stream for job {job_id}...")
    
    start_time = time.time()
    last_heartbeat = time.time()
    heartbeat_count = 0
    progress_updates = []
    connection_switched = False
    result = None
    
    try:
        # Connect to SSE stream
        async with session.get(f"{BASE_URL}/api/stream/{job_id}") as response:
            if response.status != 200:
                print(f"  ❌ Failed to connect to SSE stream: {response.status}")
                return await test_polling_fallback(session, job_id, max_duration)
            
            print("  ✅ SSE connection established")
            
            # Read SSE events
            async for line in response.content:
                line_text = line.decode('utf-8').strip()
                
                if line_text.startswith('data: '):
                    try:
                        data = json.loads(line_text[6:])
                        current_time = time.time()
                        
                        # Track heartbeats
                        if data.get('type') == 'heartbeat':
                            heartbeat_count += 1
                            last_heartbeat = current_time
                            if heartbeat_count % 10 == 0:  # Log every 10th heartbeat
                                print(f"  💓 Heartbeat #{heartbeat_count} received (last: {current_time - last_heartbeat:.1f}s ago)")
                        
                        # Track progress
                        if 'progress' in data:
                            progress_updates.append({
                                'time': current_time - start_time,
                                'progress': data['progress'],
                                'message': data.get('message', ''),
                                'stage': data.get('current_stage', ''),
                                'items': f"{data.get('processed_items', 0)}/{data.get('total_items', 0)}"
                            })
                            
                            # Log significant progress
                            if len(progress_updates) == 1 or data['progress'] % 20 == 0 or data['progress'] >= 95:
                                elapsed = current_time - start_time
                                print(f"  📊 Progress: {data['progress']:.1f}% - {data.get('message', 'Processing...')} [{elapsed:.1f}s]")
                                if data.get('processed_items'):
                                    print(f"     Items: {data['processed_items']}/{data['total_items']}")
                        
                        # Check for completion
                        if data.get('status') == 'completed':
                            result = data.get('result', {})
                            print(f"  ✅ Timeline generation completed!")
                            break
                        
                        elif data.get('status') == 'failed':
                            print(f"  ❌ Generation failed: {data.get('error', 'Unknown error')}")
                            break
                        
                        # Check for timeout on our end
                        if current_time - start_time > max_duration:
                            print(f"  ⏱️ Test timeout reached ({max_duration}s)")
                            break
                        
                        # Check heartbeat health
                        if current_time - last_heartbeat > 30:
                            print(f"  ⚠️ No heartbeat for 30s, connection may be stale")
                            connection_switched = True
                            return await test_polling_fallback(session, job_id, max_duration - (current_time - start_time))
                            
                    except json.JSONDecodeError:
                        pass  # Ignore malformed data
            
    except asyncio.TimeoutError:
        print("  ⏱️ SSE connection timed out, switching to polling...")
        connection_switched = True
        return await test_polling_fallback(session, job_id, max_duration)
    except Exception as e:
        print(f"  ❌ SSE error: {e}")
        connection_switched = True
        return await test_polling_fallback(session, job_id, max_duration)
    
    duration = time.time() - start_time
    
    return {
        'success': result is not None,
        'duration': duration,
        'heartbeat_count': heartbeat_count,
        'progress_updates': len(progress_updates),
        'connection_switched': connection_switched,
        'result': result
    }

async def test_polling_fallback(session: aiohttp.ClientSession, job_id: str, max_duration: int) -> Dict[str, Any]:
    """Test polling fallback mechanism."""
    print(f"  🔄 Switching to polling mode for job {job_id}...")
    
    start_time = time.time()
    poll_count = 0
    last_progress = 0
    result = None
    
    while time.time() - start_time < max_duration:
        poll_count += 1
        
        try:
            # Poll job status endpoint
            async with session.get(f"{BASE_URL}/api/ai/jobs/{job_id}") as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Log progress changes
                    if data.get('progress', 0) != last_progress:
                        last_progress = data.get('progress', 0)
                        elapsed = time.time() - start_time
                        print(f"  📊 [Polling] Progress: {last_progress:.1f}% - {data.get('message', '')} [{elapsed:.1f}s]")
                    
                    # Check completion
                    if data.get('status') == 'completed':
                        result = data.get('result', {})
                        print(f"  ✅ [Polling] Timeline generation completed!")
                        break
                    
                    elif data.get('status') == 'failed':
                        print(f"  ❌ [Polling] Generation failed: {data.get('error', 'Unknown error')}")
                        break
                        
                elif response.status == 404:
                    print(f"  ❓ Job {job_id} not found, may have completed")
                    break
                    
        except Exception as e:
            print(f"  ⚠️ Polling error: {e}")
        
        # Wait before next poll
        await asyncio.sleep(2)
    
    duration = time.time() - start_time
    
    return {
        'success': result is not None,
        'duration': duration,
        'poll_count': poll_count,
        'connection_switched': True,
        'result': result
    }

async def test_timeline_generation(config: Dict[str, Any]) -> Dict[str, Any]:
    """Test timeline generation with specified configuration."""
    name = config['name']
    count = config['count']
    timeout = config['timeout']
    
    print(f"\n{'='*70}")
    print(f"Testing: {name} ({count} deliverables)")
    print('='*70)
    
    # Generate test deliverables
    print(f"  📝 Generating {count} test deliverables...")
    deliverables = generate_test_deliverables(count)
    
    # Prepare request
    request_data = {
        "deliverables": deliverables,
        "rfp_text": f"Test RFP for {name}. This project requires comprehensive timeline planning across multiple departments and workstreams.",
        "project_start": "2025-01-01",
        "optimization_mode": "balanced",
        "use_intelligent_scheduler": True
    }
    
    async with aiohttp.ClientSession() as session:
        # Start timeline generation
        print(f"  🚀 Starting timeline generation...")
        start_time = time.time()
        
        try:
            async with session.post(
                f"{BASE_URL}/api/ai/generate_timeline",
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    print(f"  ❌ Failed to start generation: {response.status}")
                    text = await response.text()
                    print(f"     Error: {text[:200]}")
                    return {
                        'name': name,
                        'count': count,
                        'success': False,
                        'error': f"HTTP {response.status}"
                    }
                
                data = await response.json()
                job_id = data.get('job_id')
                
                if not job_id:
                    print("  ❌ No job_id returned")
                    return {
                        'name': name,
                        'count': count,
                        'success': False,
                        'error': "No job_id"
                    }
                
                print(f"  ✅ Job created: {job_id}")
                
        except Exception as e:
            print(f"  ❌ Failed to start: {e}")
            return {
                'name': name,
                'count': count,
                'success': False,
                'error': str(e)
            }
        
        # Monitor progress via SSE
        test_result = await test_sse_connection(session, job_id, timeout)
        
        # Calculate statistics
        total_duration = time.time() - start_time
        
        # Validate result
        if test_result['success'] and test_result.get('result'):
            tasks = test_result['result'].get('tasks', [])
            print(f"\n  📈 Results:")
            print(f"     Total duration: {total_duration:.1f}s")
            print(f"     Tasks generated: {len(tasks)}")
            print(f"     Heartbeats received: {test_result.get('heartbeat_count', 0)}")
            print(f"     Progress updates: {test_result.get('progress_updates', 0)}")
            print(f"     Connection switched: {test_result.get('connection_switched', False)}")
            print(f"     Average time per deliverable: {total_duration/count:.2f}s")
            
            # Performance rating
            time_per_deliverable = total_duration / count
            if time_per_deliverable < 1:
                rating = "⚡ Excellent"
            elif time_per_deliverable < 2:
                rating = "✅ Good"
            elif time_per_deliverable < 5:
                rating = "⚠️ Acceptable"
            else:
                rating = "❌ Slow"
            
            print(f"     Performance: {rating}")
            
            return {
                'name': name,
                'count': count,
                'success': True,
                'duration': total_duration,
                'tasks': len(tasks),
                'heartbeats': test_result.get('heartbeat_count', 0),
                'connection_switched': test_result.get('connection_switched', False),
                'time_per_deliverable': time_per_deliverable,
                'rating': rating
            }
        else:
            print(f"\n  ❌ Test failed")
            return {
                'name': name,
                'count': count,
                'success': False,
                'duration': total_duration,
                'error': 'No result generated'
            }

async def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("TIMELINE GENERATION STRESS TEST")
    print("Testing SSE with heartbeat and polling fallback")
    print("="*70)
    
    # Check if custom test size is requested
    if len(sys.argv) > 1:
        try:
            custom_count = int(sys.argv[1])
            TEST_CONFIGS.insert(0, {
                "name": f"Custom Test",
                "count": custom_count,
                "timeout": max(180, custom_count * 6)
            })
            print(f"\n📌 Added custom test with {custom_count} deliverables")
        except ValueError:
            print(f"\n⚠️ Invalid argument: {sys.argv[1]}")
    
    results = []
    
    # Run tests
    for config in TEST_CONFIGS:
        result = await test_timeline_generation(config)
        results.append(result)
        
        # Wait between tests to avoid overload
        if config != TEST_CONFIGS[-1]:
            print(f"\n⏸️ Waiting 5 seconds before next test...")
            await asyncio.sleep(5)
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"\n✅ Successful: {len(successful)}/{len(results)}")
    for r in successful:
        print(f"   - {r['name']}: {r['count']} deliverables in {r['duration']:.1f}s ({r.get('rating', 'N/A')})")
        if r.get('connection_switched'):
            print(f"     ↳ Connection switched to polling")
    
    if failed:
        print(f"\n❌ Failed: {len(failed)}/{len(results)}")
        for r in failed:
            print(f"   - {r['name']}: {r.get('error', 'Unknown error')}")
    
    # Performance statistics
    if successful:
        print("\n📊 Performance Statistics:")
        avg_time_per_deliv = sum(r['time_per_deliverable'] for r in successful) / len(successful)
        max_count = max(r['count'] for r in successful)
        print(f"   Average time per deliverable: {avg_time_per_deliv:.2f}s")
        print(f"   Largest successful test: {max_count} deliverables")
        
        # Check heartbeat effectiveness
        heartbeat_tests = [r for r in successful if r.get('heartbeats', 0) > 0]
        if heartbeat_tests:
            avg_heartbeats = sum(r['heartbeats'] for r in heartbeat_tests) / len(heartbeat_tests)
            print(f"   Average heartbeats per test: {avg_heartbeats:.0f}")
    
    # Final verdict
    print("\n" + "="*70)
    if len(successful) == len(results):
        print("🎉 ALL TESTS PASSED! Timeline generation is production-ready.")
    elif len(successful) > 0:
        print("⚠️ PARTIAL SUCCESS. Some tests failed, review the issues.")
    else:
        print("❌ ALL TESTS FAILED. Critical issues need to be fixed.")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())