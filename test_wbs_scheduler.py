"""
WBS Scheduler Unit Tests - Phase 1 Task 3
Tests compute_wbs_schedule() and rollup_parent_dates() with golden scenarios
"""
import datetime
from decimal import Decimal

# Import scheduler functions from scheduler.py (extracted module)
from scheduler import (
    add_business_days,
    compute_wbs_schedule,
    rollup_parent_dates,
    business_day_diff,
    is_business_day,
)

def test_add_business_days_half_day_morning():
    """Test 0.5 days from Mon 8AM → Mon 12PM"""
    start = datetime.datetime(2026, 1, 5, 8, 0)  # Monday 8 AM
    result = add_business_days(start, 0.5)
    expected = datetime.datetime(2026, 1, 5, 12, 0)  # Monday 12 PM
    
    assert result == expected, f"Expected {expected}, got {result}"

def test_add_business_days_midday_start():
    """Test 0.5 days from Mon 10AM → Mon 3PM (2h before lunch + 2h after)"""
    start = datetime.datetime(2026, 1, 5, 10, 0)  # Monday 10 AM
    result = add_business_days(start, 0.5)
    expected = datetime.datetime(2026, 1, 5, 15, 0)  # Monday 3 PM
    
    assert result == expected, f"Expected {expected}, got {result}"

def test_add_business_days_full_day():
    """Test 1.0 day from Mon 8AM → Mon 5PM"""
    start = datetime.datetime(2026, 1, 5, 8, 0)  # Monday 8 AM
    result = add_business_days(start, 1.0)
    expected = datetime.datetime(2026, 1, 5, 17, 0)  # Monday 5 PM
    
    assert result == expected, f"Expected {expected}, got {result}"

def test_add_business_days_two_days():
    """Test 2.0 days from Mon 8AM → Tue 5PM"""
    start = datetime.datetime(2026, 1, 5, 8, 0)  # Monday 8 AM
    result = add_business_days(start, 2.0)
    expected = datetime.datetime(2026, 1, 6, 17, 0)  # Tuesday 5 PM
    
    assert result == expected, f"Expected {expected}, got {result}"

def test_add_business_days_zero_duration():
    """Test 0 days from Mon 10AM → Mon 10AM (unchanged)"""
    start = datetime.datetime(2026, 1, 5, 10, 0)  # Monday 10 AM
    result = add_business_days(start, 0.0)
    expected = datetime.datetime(2026, 1, 5, 10, 0)  # Monday 10 AM (unchanged)
    
    assert result == expected, f"Expected {expected}, got {result}"

def test_cpd_golden_scenario_add_business_days():
    """
    Test CPD block with add_business_days: 395 hours = 49.375 business days
    Start: Mon 5/26/26 8AM → Expected: Mon 8/3/26 11AM (exact)
    """
    # Project start: May 26, 2026 (Monday) 8 AM
    project_start = datetime.datetime(2026, 5, 26, 8, 0)
    
    # CPD task: 395 hours ÷ 8 hours/day = 49.375 days
    duration_days = 395.0 / 8.0  # 49.375
    
    # Calculate actual finish
    result = add_business_days(project_start, duration_days)
    
    # Expected finish: Mon 8/3/26 11:00 AM (49 business days + 3 hours)
    expected = datetime.datetime(2026, 8, 3, 11, 0)
    
    # Verify exact datetime match
    assert result == expected, f"Expected {expected}, got {result}"

def test_cpd_with_compute_wbs_schedule():
    """
    Test CPD block using full compute_wbs_schedule() function.
    Validates that scheduler produces correct dates for 395h task.
    Expected: Start 5/26/26 8AM, Finish 8/3/26 11AM, Duration 49.375 days
    """
    # Define CPD task rows
    cpd_rows = [
        {
            "UID": 100,
            "WBS": "1.2.3",
            "Name": "Creative Strategy / Campaign Plan Deck",
            "Hours": 395,
            "OutlineLevel": 4,
        }
    ]
    
    # No dependencies (standalone task)
    cpd_edges = []
    
    # Project start: May 26, 2026 (Monday)
    project_start = datetime.date(2026, 5, 26)
    
    # Run scheduler
    result = compute_wbs_schedule(cpd_rows, cpd_edges, project_start)
    
    # Verify result structure
    assert 100 in result, "CPD task UID should be in results"
    assert "start" in result[100], "Result should have start date"
    assert "finish" in result[100], "Result should have finish date"
    assert "duration_days" in result[100], "Result should have duration"
    
    # Verify duration calculation (exact)
    assert result[100]["duration_days"] == 49.375, f"Expected 49.375 days, got {result[100]['duration_days']}"
    
    # Verify start datetime (exact)
    expected_start = datetime.datetime(2026, 5, 26, 8, 0)
    assert result[100]["start"] == expected_start, f"Expected start {expected_start}, got {result[100]['start']}"
    
    # Verify finish datetime (exact)
    expected_finish = datetime.datetime(2026, 8, 3, 11, 0)
    assert result[100]["finish"] == expected_finish, f"Expected finish {expected_finish}, got {result[100]['finish']}"

def test_parallel_branches_with_compute_wbs_schedule():
    """
    Test parallel branches using compute_wbs_schedule().
    
    Structure:
    Task A (10h = 1.25 days) → Task B (20h = 2.5 days)
                             → Task C (15h = 1.875 days)
    
    Expected: Both B and C start at the same time (A's finish time)
    """
    # Define task rows
    parallel_rows = [
        {"UID": 1, "WBS": "1.1", "Name": "Task A", "Hours": 10, "OutlineLevel": 5},
        {"UID": 2, "WBS": "1.2", "Name": "Task B", "Hours": 20, "OutlineLevel": 5},
        {"UID": 3, "WBS": "1.3", "Name": "Task C", "Hours": 15, "OutlineLevel": 5},
    ]
    
    # Dependencies: Both B and C depend on A
    parallel_edges = [
        ("1.1", "1.2"),  # A → B
        ("1.1", "1.3"),  # A → C
    ]
    
    project_start = datetime.date(2026, 1, 6)  # Monday
    
    # Run scheduler
    result = compute_wbs_schedule(parallel_rows, parallel_edges, project_start)
    
    # Verify all tasks scheduled
    assert all(uid in result for uid in [1, 2, 3]), "All tasks should be scheduled"
    
    # Verify parallel tasks (B and C) share the same start time (A's finish)
    assert result[2]["start"] == result[3]["start"], f"Parallel tasks should start at same time: B={result[2]['start']}, C={result[3]['start']}"
    
    # Verify parallel tasks start after A finishes
    assert result[2]["start"] == result[1]["finish"], "Task B should start when A finishes"
    assert result[3]["start"] == result[1]["finish"], "Task C should start when A finishes"

def test_milestone_with_compute_wbs_schedule():
    """
    Test zero-duration milestones using compute_wbs_schedule().
    
    Structure:
    Task A (10h = 1.25 days) → Review Milestone (0h) → Task B (15h = 1.875 days)
    
    Expected: Milestone has zero duration, B starts immediately after milestone
    """
    # Define task rows
    milestone_rows = [
        {"UID": 1, "WBS": "1.1", "Name": "Task A", "Hours": 10, "OutlineLevel": 5},
        {"UID": 2, "WBS": "1.2", "Name": "Review Milestone", "Hours": 0, "OutlineLevel": 5},
        {"UID": 3, "WBS": "1.3", "Name": "Task B", "Hours": 15, "OutlineLevel": 5},
    ]
    
    # Dependencies: A → Milestone → B
    milestone_edges = [
        ("1.1", "1.2"),  # A → Milestone
        ("1.2", "1.3"),  # Milestone → B
    ]
    
    project_start = datetime.date(2026, 1, 6)  # Monday
    
    # Run scheduler
    result = compute_wbs_schedule(milestone_rows, milestone_edges, project_start)
    
    # Verify milestone has zero duration
    assert result[2]["duration_days"] == 0.0, "Milestone should have zero duration"
    
    # Verify milestone start == finish (zero duration)
    assert result[2]["start"] == result[2]["finish"], "Milestone start should equal finish"
    
    # Verify Task B starts immediately after milestone (which is same as A's finish)
    assert result[3]["start"] == result[2]["finish"], "Task B should start at milestone finish"
    assert result[3]["start"] == result[1]["finish"], "Task B should start immediately after Task A"

def test_rollup_parent_dates():
    """
    Test rollup_parent_dates() with parent-child hierarchy.
    
    Structure:
    Parent (L4) contains:
      - Child A (L5, 10h)
      - Child B (L5, 20h)
    
    Expected: Parent dates rolled up from children
    """
    # Define parent-child rows
    rows = [
        {"UID": 1, "WBS": "1", "Name": "Parent", "Hours": 0, "OutlineLevel": 4},
        {"UID": 2, "WBS": "1.1", "Name": "Child A", "Hours": 10, "OutlineLevel": 5},
        {"UID": 3, "WBS": "1.2", "Name": "Child B", "Hours": 20, "OutlineLevel": 5},
    ]
    
    # No dependencies between children (parallel)
    edges = []
    
    project_start = datetime.date(2026, 1, 6)  # Monday
    
    # First, compute schedule for children
    uid_to_sched = compute_wbs_schedule(rows, edges, project_start)
    
    # Then roll up parent dates
    result = rollup_parent_dates(rows, uid_to_sched)
    
    # Verify parent dates are rolled up from children
    assert result[1]["start"] == min(result[2]["start"], result[3]["start"]), "Parent start should be min of children"
    assert result[1]["finish"] == max(result[2]["finish"], result[3]["finish"]), "Parent finish should be max of children"
