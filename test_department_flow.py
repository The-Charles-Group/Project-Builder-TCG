#!/usr/bin/env python3
"""
Test script to verify department information flows correctly through the timeline generation
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_department_flow():
    """Test that departments are properly mapped and flow through to timeline tasks"""
    
    print("Testing Department Information Flow...")
    print("=" * 50)
    
    # Step 1: Get available deliverables with departments
    print("\n1. Checking deliverable department mapping...")
    
    # Test timeline generation with sample deliverables
    test_deliverables = [
        {"deliverable_code": "BRAND_STRATEGY", "name": "Brand Strategy"},
        {"deliverable_code": "WEB_DESIGN", "name": "Web Design"},
        {"deliverable_code": "PAID_SEARCH", "name": "Paid Search Campaign"},
        {"deliverable_code": "CONTENT_DEVELOPMENT", "name": "Content Development"},
    ]
    
    timeline_request = {
        "deliverables": test_deliverables,
        "rfp_text": "Test RFP for department verification",
        "project_start": "2025-01-01",
        "optimization_mode": "balanced",
        "use_intelligent_scheduler": False
    }
    
    print("\n2. Generating timeline with deliverables...")
    response = requests.post(
        f"{BASE_URL}/api/ai/generate_timeline",
        json=timeline_request,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return False
    
    result = response.json()
    
    # Debug: Print the response
    print(f"   Response status: {response.status_code}")
    print(f"   Response keys: {result.keys() if result else 'None'}")
    print(f"   Success: {result.get('success', False)}")
    print(f"   Message: {result.get('message', 'No message')}")
    print(f"   Number of tasks: {len(result.get('tasks', []))}")
    
    # Check if tasks have department information
    print("\n3. Checking task departments...")
    departments_found = set()
    tasks_without_dept = []
    
    for task in result.get('tasks', []):
        dept = task.get('department', None)
        if dept and dept != 'General':
            departments_found.add(dept)
            print(f"   ✓ Task '{task.get('name', 'Unknown')}' -> Department: {dept}")
        else:
            tasks_without_dept.append(task.get('name', 'Unknown'))
            print(f"   ✗ Task '{task.get('name', 'Unknown')}' -> NO DEPARTMENT or 'General'")
    
    print("\n4. Summary:")
    print(f"   - Total tasks: {len(result.get('tasks', []))}")
    print(f"   - Unique departments found: {departments_found}")
    print(f"   - Tasks without proper department: {len(tasks_without_dept)}")
    
    if departments_found and 'General' not in departments_found:
        print("\n✅ SUCCESS: Department information is flowing correctly!")
        print(f"   Found departments: {', '.join(sorted(departments_found))}")
    else:
        print("\n❌ ISSUE: Some tasks are missing department information")
        if tasks_without_dept:
            print(f"   Tasks without department: {', '.join(tasks_without_dept[:5])}...")
    
    return len(departments_found) > 0

if __name__ == "__main__":
    try:
        success = test_department_flow()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\nError during test: {e}")
        exit(1)