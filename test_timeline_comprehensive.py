#!/usr/bin/env python3
"""Comprehensive test for the timeline generation API with CPM analysis"""

import json
import httpx
import asyncio
import time
from datetime import datetime, timedelta

async def wait_for_job_completion(client, job_id, max_wait=60):
    """Wait for a job to complete and get the result"""
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            # Check job status via SSE endpoint
            response = await client.get(f"http://localhost:5000/api/stream/{job_id}")
            
            if response.status_code == 200:
                # Parse SSE data
                data = response.text
                lines = data.split('\n')
                
                for line in lines:
                    if line.startswith('data: '):
                        try:
                            event_data = json.loads(line[6:])
                            
                            if event_data.get('status') == 'completed':
                                return event_data.get('result', {})
                            elif event_data.get('status') == 'failed':
                                print(f"Job failed: {event_data.get('error', 'Unknown error')}")
                                return None
                            else:
                                print(f"  Progress: {event_data.get('progress', 0):.1f}% - {event_data.get('current_stage', 'processing')}")
                        except json.JSONDecodeError:
                            continue
            
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"Error checking job status: {e}")
            await asyncio.sleep(1)
    
    print(f"Timeout: Job did not complete within {max_wait} seconds")
    return None

async def test_timeline_with_cpm():
    """Test timeline generation with CPM analysis"""
    
    print("\n" + "=" * 60)
    print("🚀 Testing Timeline Generation with CPM Analysis")
    print("=" * 60)
    
    # More comprehensive deliverables list
    deliverables = [
        {
            "deliverable_code": "DEL-0001",
            "name": "Strategic Planning",
            "department": "Strategy",
            "total_hours": 80,
            "components": ["Market Research", "Competitive Analysis", "Target Audience"],
            "is_retainer": False
        },
        {
            "deliverable_code": "DEL-0002",
            "name": "Brand Development",
            "department": "Creative",
            "total_hours": 120,
            "components": ["Brand Identity", "Visual Design", "Brand Guidelines"],
            "is_retainer": False
        },
        {
            "deliverable_code": "DEL-0003",
            "name": "Content Strategy",
            "department": "Content",
            "total_hours": 60,
            "components": ["Content Calendar", "Editorial Guidelines", "Content Production"],
            "is_retainer": False
        },
        {
            "deliverable_code": "DEL-0004",
            "name": "Digital Platform",
            "department": "Technology",
            "total_hours": 200,
            "components": ["Website Development", "Mobile App", "API Integration"],
            "is_retainer": False
        },
        {
            "deliverable_code": "DEL-0005",
            "name": "Marketing Campaign",
            "department": "Paid Media",
            "total_hours": 150,
            "components": ["Media Planning", "Ad Creation", "Campaign Management"],
            "is_retainer": False
        }
    ]
    
    # Calculate project start (next Monday)
    today = datetime.now()
    days_ahead = 0 - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    next_monday = today + timedelta(days=days_ahead)
    
    payload = {
        "deliverables": deliverables,
        "rfp_text": "We need a comprehensive digital transformation project for our luxury fashion brand. The project should include brand repositioning, new digital platforms, and an integrated marketing campaign targeting high-net-worth millennials.",
        "project_start": next_monday.strftime("%Y-%m-%d"),
        "optimization_mode": "balanced",
        "use_intelligent_scheduler": True
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            print("\n📤 Sending timeline generation request...")
            print(f"   Deliverables: {len(deliverables)}")
            print(f"   Total Hours: {sum(d['total_hours'] for d in deliverables)}")
            print(f"   Project Start: {payload['project_start']}")
            print(f"   Optimization Mode: {payload['optimization_mode']}")
            
            # Send request
            response = await client.post(
                "http://localhost:5000/api/ai/generate_timeline",
                json=payload
            )
            
            if response.status_code != 200:
                print(f"\n❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
                return
            
            job_data = response.json()
            job_id = job_data.get('job_id')
            
            if not job_id:
                print("❌ No job ID returned")
                return
            
            print(f"\n✅ Job created: {job_id}")
            print("\n⏳ Waiting for timeline generation to complete...")
            
            # Wait for job completion
            result = await wait_for_job_completion(client, job_id, max_wait=120)
            
            if not result:
                print("\n❌ Failed to get timeline result")
                return
            
            print("\n✅ Timeline generated successfully!")
            print("\n" + "=" * 60)
            print("📊 Timeline Analysis Results")
            print("=" * 60)
            
            # Analyze the results
            if "tasks" in result:
                tasks = result["tasks"]
                print(f"\n📋 Tasks Generated: {len(tasks)}")
                
                # Show task breakdown by department
                dept_counts = {}
                for task in tasks:
                    dept = task.get("department", "Unknown")
                    dept_counts[dept] = dept_counts.get(dept, 0) + 1
                
                print("\n   Department Breakdown:")
                for dept, count in sorted(dept_counts.items()):
                    print(f"     • {dept}: {count} tasks")
                
                # Show critical path tasks
                critical_tasks = [t for t in tasks if t.get("critical_path") or t.get("is_critical")]
                print(f"\n🔴 Critical Path Tasks: {len(critical_tasks)}")
                
                if critical_tasks[:3]:  # Show first 3 critical tasks
                    print("   Sample critical tasks:")
                    for task in critical_tasks[:3]:
                        print(f"     • {task.get('name', 'Unnamed')}")
                        if task.get('total_float') is not None:
                            print(f"       Float: {task.get('total_float', 0):.1f} days")
            
            # Show milestones
            if "milestones" in result:
                milestones = result["milestones"]
                print(f"\n🎯 Milestones: {len(milestones)}")
                
                # Group milestones by type
                milestone_types = {}
                for m in milestones:
                    m_type = m.get("governance_type", "standard")
                    milestone_types[m_type] = milestone_types.get(m_type, 0) + 1
                
                if milestone_types:
                    print("   Milestone Types:")
                    for m_type, count in sorted(milestone_types.items()):
                        print(f"     • {m_type}: {count}")
            
            # Show CPM metrics
            if "cpm_metrics" in result:
                cpm = result["cpm_metrics"]
                print("\n📈 CPM Analysis Results:")
                print(f"   • Critical Path Length: {cpm.get('critical_path_length', 0):.1f} days")
                print(f"   • Total Project Duration: {cpm.get('project_duration', 0):.1f} days")
                print(f"   • Critical Tasks Count: {cpm.get('critical_tasks_count', 0)}")
                print(f"   • Average Float: {cpm.get('average_float', 0):.1f} days")
                
                # Show buffers (CCPM)
                if cpm.get('project_buffer_days'):
                    print(f"\n🛡️ Project Buffers:")
                    print(f"   • Project Buffer: {cpm.get('project_buffer_days', 0):.1f} days")
                    print(f"   • Feeding Buffers: {cpm.get('feeding_buffers_count', 0)}")
                    print(f"   • Total Buffer Days: {cpm.get('total_buffer_days', 0):.1f} days")
                
                # Show resource utilization
                if cpm.get('resource_utilization'):
                    util = cpm.get('resource_utilization', {})
                    print(f"\n👥 Resource Utilization:")
                    print(f"   • Average: {util.get('average', 0):.0%}")
                    print(f"   • Peak: {util.get('peak', 0):.0%}")
                    
                # Show confidence level
                if cpm.get('confidence_level'):
                    print(f"\n🎯 Schedule Confidence: {cpm.get('confidence_level', 0):.0%}")
            
            # Show project metadata
            if "metadata" in result:
                meta = result["metadata"]
                print(f"\n📝 Project Metadata:")
                print(f"   • Start Date: {meta.get('project_start', 'N/A')}")
                print(f"   • End Date: {meta.get('project_end', 'N/A')}")
                print(f"   • Total Duration: {meta.get('total_duration_days', 0)} days")
                print(f"   • Total Hours: {meta.get('total_hours', 0)}")
                
                if meta.get('workstreams'):
                    print(f"   • Workstreams: {', '.join(meta['workstreams'])}")
                
                if meta.get('phases'):
                    print(f"   • Phases: {', '.join(meta['phases'])}")
            
            # Show AI reasoning if available
            if "reasoning" in result:
                reasoning = result["reasoning"]
                print(f"\n🧠 AI Strategic Insights:")
                
                if reasoning.get('ai_strategic_rationale'):
                    print(f"   • Strategy: {reasoning['ai_strategic_rationale'][:200]}...")
                
                if reasoning.get('confidence_level'):
                    print(f"   • AI Confidence: {reasoning['confidence_level']}%")
                
                if reasoning.get('risk_mitigation'):
                    risks = reasoning['risk_mitigation']
                    if isinstance(risks, list) and risks:
                        print(f"   • Risk Mitigation: {len(risks)} strategies identified")
            
            print("\n" + "=" * 60)
            print("✅ Timeline API Test Complete!")
            print("=" * 60)
            
            # Save result for inspection
            with open("timeline_test_result.json", "w") as f:
                json.dump(result, f, indent=2)
            print("\n💾 Full result saved to timeline_test_result.json")
            
            return result
            
        except httpx.ConnectError:
            print("\n❌ Connection Error: Cannot connect to http://localhost:5000")
            print("   Make sure the FastAPI server is running")
        except Exception as e:
            print(f"\n❌ Unexpected Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Comprehensive Timeline API Test")
    print("=" * 60)
    
    # Run the test
    result = asyncio.run(test_timeline_with_cpm())
    
    if result:
        print("\n✅ All tests passed successfully!")
    else:
        print("\n❌ Some tests failed - check output above")