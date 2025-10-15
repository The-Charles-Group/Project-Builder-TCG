#!/usr/bin/env python3
"""
Test script to verify timeline generation with SSE progress streaming works end-to-end
"""

import asyncio
import aiohttp
import json
import time

async def test_timeline_generation():
    """Test the complete timeline generation flow with SSE streaming"""
    base_url = "http://localhost:5000"
    
    print("=" * 60)
    print("Timeline Generation SSE Test")
    print("=" * 60)
    
    # Prepare test data
    test_deliverables = [
        {
            "deliverable_code": "STR001",
            "deliverable": "Brand Strategy Development",
            "component": "Strategy",
            "hours": 80,
            "price": 12000
        },
        {
            "deliverable_code": "CRE001",
            "deliverable": "Creative Concept Development",
            "component": "Creative",
            "hours": 60,
            "price": 9000
        },
        {
            "deliverable_code": "PM001",
            "deliverable": "Campaign Management",
            "component": "Paid Media",
            "hours": 40,
            "price": 6000
        }
    ]
    
    request_data = {
        "deliverables": test_deliverables,
        "rfp_text": "We need a comprehensive digital marketing campaign for Q4 2025 product launch.",
        "project_start": "2025-11-01",
        "optimization_mode": "balanced",
        "use_intelligent_scheduler": True
    }
    
    async with aiohttp.ClientSession() as session:
        print("\n1. Triggering timeline generation...")
        print(f"   Deliverables: {len(test_deliverables)}")
        print(f"   Project start: {request_data['project_start']}")
        print(f"   Mode: {request_data['optimization_mode']}")
        
        # Start timeline generation
        async with session.post(f"{base_url}/api/ai/generate_timeline", json=request_data) as resp:
            if resp.status != 200:
                print(f"❌ Failed to start timeline generation: {resp.status}")
                text = await resp.text()
                print(f"   Response: {text}")
                return False
                
            result = await resp.json()
            print(f"✅ Timeline generation started!")
            print(f"   Job ID: {result.get('job_id')}")
            
            if not result.get('job_id'):
                print("❌ No job_id returned!")
                print(f"   Response: {result}")
                return False
                
            job_id = result['job_id']
            
        print(f"\n2. Connecting to SSE stream: /api/stream/{job_id}")
        
        # Connect to SSE stream for progress updates
        async with session.get(f"{base_url}/api/stream/{job_id}") as resp:
            if resp.status != 200:
                print(f"❌ Failed to connect to SSE stream: {resp.status}")
                return False
                
            print("✅ Connected to SSE stream!\n")
            print("3. Monitoring progress...")
            print("-" * 40)
            
            last_progress = 0
            start_time = time.time()
            
            # Read SSE events
            async for line in resp.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        
                        # Display progress
                        progress = data.get('progress', 0)
                        status = data.get('status', 'unknown')
                        message = data.get('message', '')
                        stage = data.get('current_stage', '')
                        
                        if progress != last_progress or status != 'processing':
                            elapsed = time.time() - start_time
                            print(f"[{elapsed:5.1f}s] {progress:5.1f}% | {status:12s} | {stage:20s} | {message}")
                            last_progress = progress
                        
                        # Check for completion
                        if status in ['completed', 'failed']:
                            print("-" * 40)
                            if status == 'completed':
                                print(f"✅ Timeline generation completed in {elapsed:.1f} seconds!")
                                if 'result' in data:
                                    result = data['result']
                                    if isinstance(result, dict):
                                        task_count = len(result.get('tasks', []))
                                        print(f"   Generated {task_count} tasks")
                                return True
                            else:
                                print(f"❌ Timeline generation failed: {data.get('error', 'Unknown error')}")
                                return False
                                
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse SSE data: {e}")
                        print(f"Line: {line}")
                        
            print("⚠️ SSE stream ended unexpectedly")
            return False

if __name__ == "__main__":
    print("Testing timeline generation with SSE progress streaming...")
    
    try:
        success = asyncio.run(test_timeline_generation())
        print("\n" + "=" * 60)
        if success:
            print("✅ TEST PASSED: Timeline generation with SSE works!")
        else:
            print("❌ TEST FAILED: Timeline generation or SSE streaming has issues")
        print("=" * 60)
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()