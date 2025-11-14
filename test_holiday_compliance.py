#!/usr/bin/env python3
"""
Holiday Compliance Test Suite
Validates that ALL timeline tasks respect business days and TCG company holidays.
Tests multiple scenario archetypes to ensure comprehensive coverage.
"""

import sys
import json
from datetime import datetime, date
from typing import List, Dict, Set
from business_calendar import BusinessCalendar


class HolidayComplianceValidator:
    """Validates timeline compliance with business days and holidays"""
    
    def __init__(self):
        self.violations = []
        self.stats = {
            'total_tasks': 0,
            'weekend_violations': 0,
            'holiday_violations': 0,
            'total_violations': 0
        }
    
    def validate_timeline(self, timeline_data: Dict, scenario_name: str) -> bool:
        """
        Validate all tasks in a timeline respect business days.
        
        Args:
            timeline_data: Timeline JSON data with schedule items
            scenario_name: Descriptive name for reporting
            
        Returns:
            True if validation passes, False otherwise
        """
        print(f"\n{'='*60}")
        print(f"Validating Scenario: {scenario_name}")
        print(f"{'='*60}")
        
        all_dates = set()
        
        # Extract dates from timeline items
        if 'items' in timeline_data:
            for item in timeline_data['items']:
                schedule = item.get('schedule', [])
                for task in schedule:
                    start_date = task.get('start_date')
                    end_date = task.get('end_date')
                    
                    if start_date:
                        all_dates.add(start_date)
                        self._check_date(start_date, task.get('task_name', 'Unknown'), 'start')
                    
                    if end_date:
                        all_dates.add(end_date)
                        self._check_date(end_date, task.get('task_name', 'Unknown'), 'end')
                    
                    self.stats['total_tasks'] += 1
        
        # Report findings
        print(f"\n📊 Validation Results:")
        print(f"   Total tasks analyzed: {self.stats['total_tasks']}")
        print(f"   Unique dates checked: {len(all_dates)}")
        print(f"   Weekend violations: {self.stats['weekend_violations']}")
        print(f"   Holiday violations: {self.stats['holiday_violations']}")
        print(f"   Total violations: {self.stats['total_violations']}")
        
        if self.violations:
            print(f"\n❌ VIOLATIONS FOUND:")
            for v in self.violations[:10]:  # Show first 10
                print(f"   • {v}")
            if len(self.violations) > 10:
                print(f"   ... and {len(self.violations) - 10} more")
            return False
        else:
            print(f"\n✅ PASS - All tasks scheduled on valid business days!")
            return True
    
    def _check_date(self, date_str: str, task_name: str, date_type: str):
        """Check if a single date violates business day rules"""
        try:
            dt = datetime.fromisoformat(date_str).date()
        except:
            # Try parsing as date only
            dt = date.fromisoformat(date_str)
        
        # Check if business day
        if not BusinessCalendar.is_business_day(dt):
            weekday = dt.weekday()
            
            # Determine violation type
            if weekday >= 5:  # Saturday=5, Sunday=6
                violation_type = "WEEKEND"
                self.stats['weekend_violations'] += 1
            else:
                violation_type = "HOLIDAY"
                self.stats['holiday_violations'] += 1
            
            self.stats['total_violations'] += 1
            
            violation_msg = (
                f"{violation_type}: {task_name} ({date_type}) on "
                f"{dt.strftime('%Y-%m-%d (%A)')}"
            )
            self.violations.append(violation_msg)
    
    def print_summary(self):
        """Print final summary across all scenarios"""
        print(f"\n{'='*60}")
        print(f"FINAL SUMMARY")
        print(f"{'='*60}")
        print(f"Total scenarios tested: Multiple")
        print(f"Total tasks analyzed: {self.stats['total_tasks']}")
        print(f"Total violations: {self.stats['total_violations']}")
        
        if self.stats['total_violations'] == 0:
            print(f"\n✅✅✅ ALL TESTS PASSED ✅✅✅")
            print(f"Zero tasks scheduled on weekends or holidays!")
            return True
        else:
            print(f"\n❌❌❌ TESTS FAILED ❌❌❌")
            print(f"Found {self.stats['total_violations']} violations")
            return False


def test_edge_cases():
    """
    Test specific edge cases manually.
    These test the BusinessCalendar directly without requiring full timeline generation.
    """
    print(f"\n{'='*60}")
    print(f"Testing Edge Cases (Direct BusinessCalendar)")
    print(f"{'='*60}")
    
    passed = True
    
    # Test 1: Thanksgiving week 2025 (Nov 27-28, 2025)
    print("\n📅 Test: Day before Thanksgiving 2025")
    thanksgiving_eve = date(2025, 11, 26)  # Wednesday before Thanksgiving
    next_bd = BusinessCalendar.add_business_days(thanksgiving_eve, 1)
    expected = date(2025, 12, 1)  # Monday after Thanksgiving (Thu+Fri are holidays)
    if next_bd != expected:
        print(f"   ❌ FAIL: Expected {expected}, got {next_bd}")
        passed = False
    else:
        print(f"   ✅ PASS: Correctly skipped Thanksgiving")
    
    # Test 2: Winter Closure 2025-2026 (Dec 22, 2025 - Jan 2, 2026)
    print("\n📅 Test: Winter Closure 2025-2026")
    last_day_before = date(2025, 12, 19)  # Friday before closure
    next_bd = BusinessCalendar.add_business_days(last_day_before, 1)
    expected = date(2026, 1, 5)  # Monday after closure (Jan 2 is Manager Regroup)
    if next_bd != expected:
        print(f"   ❌ FAIL: Expected {expected}, got {next_bd}")
        passed = False
    else:
        print(f"   ✅ PASS: Correctly skipped entire Winter Closure")
    
    # Test 3: Mental Health Break 2025 (Aug 28-29, 2025 + Labor Day Sept 1)
    print("\n📅 Test: Mental Health Break 2025")
    before_break = date(2025, 8, 27)  # Wednesday before break
    next_bd = BusinessCalendar.add_business_days(before_break, 1)
    expected = date(2025, 9, 2)  # Tuesday after Labor Day
    if next_bd != expected:
        print(f"   ❌ FAIL: Expected {expected}, got {next_bd}")
        passed = False
    else:
        print(f"   ✅ PASS: Correctly skipped Mental Health Break + Memorial Day")
    
    # Test 4: Regular weekend
    print("\n📅 Test: Regular weekend")
    friday = date(2025, 1, 10)
    next_bd = BusinessCalendar.add_business_days(friday, 1)
    expected = date(2025, 1, 13)  # Monday
    if next_bd != expected:
        print(f"   ❌ FAIL: Expected {expected}, got {next_bd}")
        passed = False
    else:
        print(f"   ✅ PASS: Correctly skipped weekend")
    
    # Test 5: Negative offset (backwards)
    print("\n📅 Test: Backwards scheduling (FS with lag)")
    start = date(2025, 1, 15)  # Wednesday
    prev_bd = BusinessCalendar.add_business_days(start, -3)
    expected = date(2025, 1, 10)  # Friday (3 bdays back)
    if prev_bd != expected:
        print(f"   ❌ FAIL: Expected {expected}, got {prev_bd}")
        passed = False
    else:
        print(f"   ✅ PASS: Backwards scheduling works correctly")
    
    print(f"\n{'='*60}")
    if passed:
        print(f"✅ All edge case tests PASSED")
    else:
        print(f"❌ Some edge case tests FAILED")
    print(f"{'='*60}")
    
    return passed


if __name__ == "__main__":
    print("="*60)
    print("HOLIDAY COMPLIANCE TEST SUITE")
    print("="*60)
    print("This test validates that ALL timeline tasks respect:")
    print("  • Monday-Friday work weeks (no weekends)")
    print("  • All 34 TCG company holidays")
    print("="*60)
    
    # Run edge case tests first
    edge_case_result = test_edge_cases()
    
    print("\n" + "="*60)
    print("INSTRUCTIONS FOR TIMELINE VALIDATION:")
    print("="*60)
    print("1. Generate a timeline scenario via the web UI")
    print("2. Export the scenario JSON data")
    print("3. Run: python test_holiday_compliance.py <scenario.json>")
    print("4. The script will validate all task dates")
    print("="*60)
    
    # If JSON file provided, validate it
    if len(sys.argv) > 1:
        import json
        validator = HolidayComplianceValidator()
        
        with open(sys.argv[1], 'r') as f:
            timeline_data = json.load(f)
        
        result = validator.validate_timeline(timeline_data, sys.argv[1])
        validator.print_summary()
        
        sys.exit(0 if (result and edge_case_result) else 1)
    else:
        # Just run edge cases
        sys.exit(0 if edge_case_result else 1)
