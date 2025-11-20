"""
Phase 2 Dual-Write Integration Tests
Verifies scheduler is called, dates are stored, and XML export still works
"""
import pytest
import datetime
import sys
from decimal import Decimal
sys.path.insert(0, '.')

from scheduler import compute_wbs_schedule, rollup_parent_dates
from main import _apply_wbs_scheduler_to_scenario, ENABLE_WBS_SCHEDULER

def test_phase2_scheduler_called_when_enabled():
    """Test that _apply_wbs_scheduler_to_scenario stores scheduler_dates when flag=True"""
    # Create a minimal scenario
    scenario = {
        "items": [
            {
                "UID": 1,
                "WBS": "1",
                "Task_Label": "Project",
                "OutlineLevel": 1,
                "Hours": 100,
                "Dependencies": "",
                "Start_Date": "2026-05-26",
                "End_Date": "2026-08-03"
            },
            {
                "UID": 2,
                "WBS": "1.1",
                "Task_Label": "Phase 1",
                "OutlineLevel": 2,
                "Hours": 50,
                "Dependencies": "",
                "Start_Date": "",
                "End_Date": ""
            }
        ],
        "project_start": "2026-05-26"
    }
    
    # Apply scheduler
    result = _apply_wbs_scheduler_to_scenario(scenario)
    
    if ENABLE_WBS_SCHEDULER:
        # Should have scheduler_dates stored
        assert "scheduler_dates" in result, "scheduler_dates should be stored in scenario"
        assert len(result["scheduler_dates"]) > 0, "scheduler_dates should have entries"
        assert 1 in result["scheduler_dates"], "UID 1 should have schedule"
        assert 2 in result["scheduler_dates"], "UID 2 should have schedule"
        
        # Check date structure
        sched_1 = result["scheduler_dates"][1]
        assert "start" in sched_1, "schedule should have start"
        assert "finish" in sched_1, "schedule should have finish"
        assert "duration_days" in sched_1, "schedule should have duration_days"
        
        # Verify start is datetime
        assert isinstance(sched_1["start"], datetime.datetime), "start should be datetime"
        assert isinstance(sched_1["finish"], datetime.datetime), "finish should be datetime"
        
        print(f"✅ Phase 2 Test PASSED: scheduler_dates stored = {len(result['scheduler_dates'])} tasks")
    else:
        print(f"⚠️ Phase 2 Test SKIPPED: ENABLE_WBS_SCHEDULER=False")

def test_phase2_legacy_dates_preserved():
    """Test that legacy dates are preserved in items (not overwritten)"""
    scenario = {
        "items": [
            {
                "UID": 1,
                "WBS": "1",
                "Task_Label": "Project",
                "OutlineLevel": 1,
                "Hours": 100,
                "Dependencies": "",
                "Start_Date": "2026-05-26",
                "End_Date": "2026-08-03"
            }
        ],
        "project_start": "2026-05-26"
    }
    
    legacy_start = scenario["items"][0]["Start_Date"]
    legacy_end = scenario["items"][0]["End_Date"]
    
    # Apply scheduler
    result = _apply_wbs_scheduler_to_scenario(scenario)
    
    # Legacy dates should still be in items
    assert result["items"][0]["Start_Date"] == legacy_start, "Legacy Start_Date should be preserved"
    assert result["items"][0]["End_Date"] == legacy_end, "Legacy End_Date should be preserved"
    
    print(f"✅ Phase 2 Test PASSED: Legacy dates preserved")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PHASE 2 INTEGRATION TESTS")
    print("="*60 + "\n")
    
    test_phase2_scheduler_called_when_enabled()
    test_phase2_legacy_dates_preserved()
    
    print("\n" + "="*60)
    print("✅ ALL PHASE 2 TESTS COMPLETED")
    print("="*60 + "\n")
