#!/usr/bin/env python3
"""Test script for the /api/ai/generate_timeline endpoint"""

import json
import httpx
import asyncio
from datetime import datetime, timedelta

def create_test_payload():
    """Create a test payload that matches what the frontend sends"""
    
    # Sample deliverables from frontend structure
    deliverables = [
        {
            "deliverable_code": "DEL-0001",
            "name": "Strategic Planning",
            "department": "Strategy",
            "hours": 80,
            "components": ["Market Research", "Competitive Analysis"],
            "is_retainer": False,
            "retainer_months": 0
        },
        {
            "deliverable_code": "DEL-0002", 
            "name": "Creative Concepts",
            "department": "Creative",
            "hours": 120,
            "components": ["Visual Design", "Brand Identity"],
            "is_retainer": False,
            "retainer_months": 0
        },
        {
            "deliverable_code": "DEL-0003",
            "name": "Content Strategy",
            "department": "Content",
            "hours": 60,
            "components": ["Editorial Calendar", "Content Guidelines"],
            "is_retainer": False,
            "retainer_months": 0
        }
    ]
    
    # Calculate project start date (next Monday)
    today = datetime.now()
    days_ahead = 0 - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    next_monday = today + timedelta(days=days_ahead)
    
    payload = {
        "deliverables": deliverables,
        "rfp_text": "We need a comprehensive marketing campaign for our luxury brand launch",
        "project_start": next_monday.strftime("%Y-%m-%d"),
        "optimization_mode": "balanced",
        "use_intelligent_scheduler": True
    }
    
    return payload

async def test_timeline_endpoint():
    """Test the /api/ai/generate_timeline endpoint"""
    
    print("=" * 60)
    print("Testing /api/ai/generate_timeline Endpoint")
    print("=" * 60)
    
    # Create test payload
    payload = create_test_payload()
    
    print("\n📤 Request Payload:")
    print(json.dumps(payload, indent=2))
    
    # Test the endpoint
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            print("\n🔄 Sending request to /api/ai/generate_timeline...")
            
            response = await client.post(
                "http://localhost:5000/api/ai/generate_timeline",
                json=payload
            )
            
            print(f"\n📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("\n✅ Success! Response structure:")
                
                # Check if it returns a job or direct result
                if "job_id" in result:
                    print(f"  - Job ID: {result.get('job_id')}")
                    print(f"  - Status: {result.get('status')}")
                    print(f"  - Message: {result.get('message')}")
                    
                    # Wait a bit and check job status
                    if result.get('job_id'):
                        await asyncio.sleep(2)
                        print(f"\n🔍 Checking job status...")
                        status_response = await client.get(
                            f"http://localhost:5000/api/stream/{result['job_id']}"
                        )
                        print(f"  - Stream endpoint status: {status_response.status_code}")
                        
                else:
                    # Direct result
                    print("\nResult keys:", list(result.keys()))
                    
                    if "tasks" in result:
                        print(f"  - Tasks: {len(result['tasks'])} items")
                        if result['tasks']:
                            print(f"    Sample task: {result['tasks'][0]}")
                    
                    if "milestones" in result:
                        print(f"  - Milestones: {len(result['milestones'])} items")
                    
                    if "metadata" in result:
                        print(f"  - Metadata keys: {list(result['metadata'].keys())}")
                    
                    if "reasoning" in result:
                        print(f"  - AI Reasoning available: Yes")
                    
                    if "cpm_metrics" in result:
                        print(f"  - CPM Analysis: {result['cpm_metrics']}")
                
            else:
                print(f"\n❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
                
                # Parse error details if available
                try:
                    error = response.json()
                    print(f"\nError details: {json.dumps(error, indent=2)}")
                except:
                    print(f"Raw response: {response.text[:500]}")
            
        except httpx.ConnectError:
            print("\n❌ Connection Error: Cannot connect to http://localhost:5000")
            print("   Make sure the FastAPI server is running")
        except httpx.TimeoutException:
            print("\n❌ Timeout Error: Request took too long")
        except Exception as e:
            print(f"\n❌ Unexpected Error: {e}")
            import traceback
            traceback.print_exc()

def test_alternative_formats():
    """Test different payload formats that might be expected"""
    
    print("\n" + "=" * 60)
    print("Testing Alternative Payload Formats")
    print("=" * 60)
    
    # Alternative format 1: Using 'scenario' instead of 'deliverables'
    alt1 = {
        "scenario": {
            "deliverables": [
                {"code": "DEL-0001", "name": "Strategic Planning"},
                {"code": "DEL-0002", "name": "Creative Concepts"}
            ]
        },
        "project_start": "2025-01-20",
        "optimization_mode": "balanced"
    }
    
    print("\nAlternative 1 - 'scenario' wrapper:")
    print(json.dumps(alt1, indent=2))
    
    # Alternative format 2: Using 'scenario_data'
    alt2 = {
        "scenario_data": {
            "items": [
                {"deliverable_code": "DEL-0001", "total_hours": 80},
                {"deliverable_code": "DEL-0002", "total_hours": 120}
            ]
        },
        "project_start": "2025-01-20"
    }
    
    print("\nAlternative 2 - 'scenario_data' format:")
    print(json.dumps(alt2, indent=2))
    
    # Alternative format 3: Direct deliverable codes
    alt3 = {
        "deliverable_codes": ["DEL-0001", "DEL-0002", "DEL-0003"],
        "project_start": "2025-01-20",
        "optimization_mode": "balanced"
    }
    
    print("\nAlternative 3 - Direct codes:")
    print(json.dumps(alt3, indent=2))

if __name__ == "__main__":
    print("🚀 Timeline API Test Suite")
    print("=" * 60)
    
    # Run the async test
    asyncio.run(test_timeline_endpoint())
    
    # Show alternative formats for reference
    test_alternative_formats()
    
    print("\n✅ Test complete!")