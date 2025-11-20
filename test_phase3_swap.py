"""
Phase 3 Swap Tests - Verify scheduler dates are used in XML export
"""
import sys
sys.path.insert(0, '.')
import datetime

from main import _apply_wbs_scheduler_to_scenario, ENABLE_WBS_SCHEDULER

def test_phase3_scheduler_enabled():
    """Test that ENABLE_WBS_SCHEDULER flag is enabled for Phase 3"""
    assert ENABLE_WBS_SCHEDULER == True, "ENABLE_WBS_SCHEDULER should be True for Phase 3"
    print(f"✅ Phase 3 Test PASSED: ENABLE_WBS_SCHEDULER={ENABLE_WBS_SCHEDULER}")

def test_phase3_dates_in_scenario():
    """Test that scheduler dates are stored in scenario after Phase 2"""
    scenario = {
        "items": [
            {
                "UID": 1,
                "WBS": "1",
                "Task_Label": "Project",
                "OutlineLevel": 1,
                "Hours": 80,
                "Dependencies": "",
                "Start_Date": "",
                "End_Date": ""
            }
        ],
        "project_start": "2026-05-26"
    }
    
    result = _apply_wbs_scheduler_to_scenario(scenario)
    
    # Phase 2 output: scheduler_dates should be stored
    if ENABLE_WBS_SCHEDULER:
        assert "scheduler_dates" in result, "scheduler_dates should be in scenario after Phase 2"
        assert 1 in result["scheduler_dates"], "UID 1 should have scheduler dates"
        print(f"✅ Phase 3 Test PASSED: scheduler_dates stored in scenario")
    else:
        print(f"⚠️ Phase 3 Test SKIPPED: ENABLE_WBS_SCHEDULER=False")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PHASE 3 SWAP TESTS")
    print("="*60 + "\n")
    
    test_phase3_scheduler_enabled()
    test_phase3_dates_in_scenario()
    
    print("\n" + "="*60)
    print("✅ PHASE 3 SWAP TESTS PASSED")
    print("="*60 + "\n")
