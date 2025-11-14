#!/usr/bin/env python3
"""
Test script to verify timeline merge logic for components and tasks
"""

# Test the _build_timeline_lookup function independently
def test_timeline_lookup():
    """Test the timeline lookup function"""
    from main import _build_timeline_lookup
    
    # Test Case 1: Empty timeline_tasks
    lookup = _build_timeline_lookup([])
    assert lookup == {}, "Empty timeline should return empty lookup"
    print("✅ Test 1 passed: Empty timeline returns empty dict")
    
    # Test Case 2: Timeline with deliverable, component, and task
    timeline_tasks = [
        {
            "deliverable_code": "DEL-001",
            "component_code": "COMP-A",
            "task_code": "TASK-1",
            "start_date": "2025-01-01",
            "end_date": "2025-01-15",
            "hours": 40,
            "is_summary": False
        },
        {
            "deliverable_code": "DEL-001",
            "component_code": "COMP-B",
            "task_code": None,
            "name": "Component B",
            "start_date": "2025-01-16",
            "end_date": "2025-01-31",
            "hours": 80,
            "is_summary": True
        }
    ]
    
    lookup = _build_timeline_lookup(timeline_tasks)
    
    # Verify keys exist
    assert ("DEL-001", "COMP-A", "TASK-1") in lookup, "Task key should exist"
    assert ("DEL-001", "COMP-B", None) in lookup, "Component key should exist"
    assert ("DEL-001", "Component B", None) in lookup, "Name fallback should exist"
    
    # Verify values
    task_entry = lookup[("DEL-001", "COMP-A", "TASK-1")]
    assert task_entry["start_date"] == "2025-01-01", "Start date should match"
    assert task_entry["end_date"] == "2025-01-15", "End date should match"
    assert task_entry["hours"] == 40, "Hours should match"
    
    comp_entry = lookup[("DEL-001", "COMP-B", None)]
    assert comp_entry["start_date"] == "2025-01-16", "Component start date should match"
    assert comp_entry["is_summary"] is True, "Is summary flag should be True"
    
    print("✅ Test 2 passed: Timeline lookup correctly indexes tasks")
    
    # Test Case 3: Handle None/empty values gracefully
    timeline_tasks_with_nones = [
        {
            "deliverable_code": None,
            "component_code": "",
            "task_code": None,
            "start_date": None,
            "end_date": "2025-02-01"
        }
    ]
    
    lookup = _build_timeline_lookup(timeline_tasks_with_nones)
    # Should not crash and should handle empty string normalization
    assert ("", None, None) in lookup or ("", "", None) in lookup, "Should handle None/empty gracefully"
    print("✅ Test 3 passed: Handles None/empty values gracefully")
    
    print("\n🎉 All timeline lookup tests passed!")
    return True

if __name__ == "__main__":
    try:
        test_timeline_lookup()
        print("\n✅ Timeline merge logic implementation verified successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
