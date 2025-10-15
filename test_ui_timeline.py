#!/usr/bin/env python3
"""Generate a test timeline through the API and verify resource risk management"""

import requests
import json

# Read the test RFP
with open('/tmp/test_resource_conflicts.txt', 'r') as f:
    rfp_text = f.read()

# Create test deliverables with overlapping schedules
test_data = {
    "rfp_text": rfp_text,
    "deliverables": [
        # Strategy tasks
        {"deliverable_code": "STRAT_001", "deliverable_name": "Market Research", "department": "Strategy", "total_hours": 40},
        {"deliverable_code": "STRAT_002", "deliverable_name": "Strategic Planning", "department": "Strategy", "total_hours": 60},
        {"deliverable_code": "STRAT_003", "deliverable_name": "Competitive Analysis", "department": "Strategy", "total_hours": 35},
        
        # Creative tasks (overlapping)
        {"deliverable_code": "CREATIVE_001", "deliverable_name": "Brand Concepts", "department": "Creative", "total_hours": 50},
        {"deliverable_code": "CREATIVE_002", "deliverable_name": "Visual Identity", "department": "Creative", "total_hours": 80},
        {"deliverable_code": "CREATIVE_003", "deliverable_name": "Campaign Assets", "department": "Creative", "total_hours": 100},
        
        # Technology tasks (heavy overlap)
        {"deliverable_code": "TECH_001", "deliverable_name": "Website Development", "department": "Technology", "total_hours": 120},
        {"deliverable_code": "TECH_002", "deliverable_name": "API Integration", "department": "Technology", "total_hours": 80},
        {"deliverable_code": "TECH_003", "deliverable_name": "Database Setup", "department": "Technology", "total_hours": 60},
        {"deliverable_code": "TECH_004", "deliverable_name": "Mobile App", "department": "Technology", "total_hours": 150},
        
        # Paid Media tasks
        {"deliverable_code": "MEDIA_001", "deliverable_name": "Media Planning", "department": "Paid Media", "total_hours": 40},
        {"deliverable_code": "MEDIA_002", "deliverable_name": "Campaign Setup", "department": "Paid Media", "total_hours": 35},
        {"deliverable_code": "MEDIA_003", "deliverable_name": "Performance Optimization", "department": "Paid Media", "total_hours": 45},
        
        # Content tasks
        {"deliverable_code": "CONTENT_001", "deliverable_name": "Content Strategy", "department": "Content", "total_hours": 30},
        {"deliverable_code": "CONTENT_002", "deliverable_name": "Blog Content", "department": "Content", "total_hours": 60},
        {"deliverable_code": "CONTENT_003", "deliverable_name": "Social Media Calendar", "department": "Content", "total_hours": 40}
    ],
    "optimization_mode": "aggressive",  # Aggressive to create more overlaps
    "include_governance": False
}

# Call the API
response = requests.post(
    "http://localhost:5000/api/ai/generate_timeline",
    json=test_data,
    headers={"Content-Type": "application/json"}
)

if response.status_code == 200:
    result = response.json()
    print(f"✓ Timeline generated with {len(result.get('tasks', []))} tasks")
    
    # Check for resource utilization
    if 'cpm' in result and 'resource_utilization' in result['cpm']:
        util = result['cpm']['resource_utilization']
        print("\n📊 Resource Utilization by Department:")
        for dept, pct in util.items():
            print(f"  {dept}: {pct*100:.1f}%")
    
    # Check task departments
    tasks = result.get('tasks', [])
    dept_counts = {}
    for task in tasks:
        dept = task.get('department', 'Unknown')
        dept_counts[dept] = dept_counts.get(dept, 0) + 1
    
    print("\n📋 Tasks by Department:")
    for dept, count in dept_counts.items():
        if dept == 'General' or dept == 'Unknown':
            print(f"  ❌ {dept}: {count} tasks (SHOULD NOT EXIST)")
        else:
            print(f"  ✓ {dept}: {count} tasks")
    
    # Save for UI testing
    with open('/tmp/timeline_result.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    print("\n✅ Timeline data saved to /tmp/timeline_result.json")
    print("📌 You can now check the UI for Resource Risk Management table")
else:
    print(f"❌ API error: {response.status_code}")
    print(response.text[:500])
