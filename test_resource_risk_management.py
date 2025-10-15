#!/usr/bin/env python3
"""
Comprehensive test script for Resource Risk Management functionality
Tests department assignments, conflict detection, resource leveling, and utilization calculations
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any
import httpx
from ai_timeline_manager import (
    TimelineTask, TimelineOptimizer, ResourceLeveler, 
    CPMCalculator, DEPARTMENT_COLORS
)

# ANSI color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
BOLD = '\033[1m'
RESET = '\033[0m'

def print_header(msg: str):
    print(f"\n{BOLD}{BLUE}{'=' * 60}{RESET}")
    print(f"{BOLD}{BLUE}{msg:^60}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 60}{RESET}\n")

def print_success(msg: str):
    print(f"{GREEN}✓ {msg}{RESET}")

def print_error(msg: str):
    print(f"{RED}✗ {msg}{RESET}")

def print_info(msg: str):
    print(f"{CYAN}ℹ {msg}{RESET}")

def print_warning(msg: str):
    print(f"{YELLOW}⚠ {msg}{RESET}")

class ResourceRiskTester:
    """Test suite for resource risk management features"""
    
    def __init__(self):
        self.results = {"passed": 0, "failed": 0, "warnings": 0}
        self.test_tasks = []
        
    def create_test_timeline_with_overlaps(self) -> List[TimelineTask]:
        """Create test timeline with intentional resource conflicts"""
        print_header("Creating Test Timeline with Resource Conflicts")
        
        # Define start date
        start_date = datetime(2025, 1, 15)  # Wednesday
        tasks = []
        
        # Strategy department tasks (overlapping)
        strategy_tasks = [
            ("Research Phase", 0, 5, 40),  # Days 0-5
            ("Strategy Development", 3, 8, 60),  # Days 3-8 (OVERLAPS with Research)
            ("Documentation", 7, 10, 30),  # Days 7-10 (OVERLAPS with Strategy Dev)
        ]
        
        for i, (name, start_offset, end_offset, hours) in enumerate(strategy_tasks):
            task = TimelineTask(
                id=f"strat_{i+1}",
                name=f"Strategy: {name}",
                deliverable_code=f"STRAT_{i+1}",
                deliverable_name=name,
                department="Strategy",
                start_date=(start_date + timedelta(days=start_offset)).strftime('%Y-%m-%d'),
                end_date=(start_date + timedelta(days=end_offset)).strftime('%Y-%m-%d'),
                hours=hours,
                color=DEPARTMENT_COLORS.get("Strategy", "#667eea")
            )
            tasks.append(task)
            print_info(f"Created: {name} (Strategy) - Days {start_offset}-{end_offset}")
        
        # Creative department tasks (with gaps)
        creative_tasks = [
            ("Initial Concepts", 2, 6, 50),  # Days 2-6
            ("Design Development", 10, 15, 80),  # Days 10-15 (4-day gap after Initial)
            ("Final Production", 20, 25, 60),  # Days 20-25 (5-day gap after Design)
        ]
        
        for i, (name, start_offset, end_offset, hours) in enumerate(creative_tasks):
            task = TimelineTask(
                id=f"creative_{i+1}",
                name=f"Creative: {name}",
                deliverable_code=f"CREATIVE_{i+1}",
                deliverable_name=name,
                department="Creative",
                start_date=(start_date + timedelta(days=start_offset)).strftime('%Y-%m-%d'),
                end_date=(start_date + timedelta(days=end_offset)).strftime('%Y-%m-%d'),
                hours=hours,
                color=DEPARTMENT_COLORS.get("Creative", "#f56565")
            )
            tasks.append(task)
            print_info(f"Created: {name} (Creative) - Days {start_offset}-{end_offset} {'(with gap)' if i > 0 else ''}")
        
        # Technology department tasks (severe overlap)
        tech_tasks = [
            ("System Architecture", 1, 7, 70),  # Days 1-7
            ("Backend Development", 3, 12, 120),  # Days 3-12 (HEAVY OVERLAP)
            ("Frontend Development", 5, 14, 100),  # Days 5-14 (TRIPLE OVERLAP)
            ("Testing & Deployment", 13, 18, 60),  # Days 13-18
        ]
        
        for i, (name, start_offset, end_offset, hours) in enumerate(tech_tasks):
            task = TimelineTask(
                id=f"tech_{i+1}",
                name=f"Technology: {name}",
                deliverable_code=f"TECH_{i+1}",
                deliverable_name=name,
                department="Technology",
                start_date=(start_date + timedelta(days=start_offset)).strftime('%Y-%m-%d'),
                end_date=(start_date + timedelta(days=end_offset)).strftime('%Y-%m-%d'),
                hours=hours,
                color=DEPARTMENT_COLORS.get("Technology", "#4299e1")
            )
            tasks.append(task)
            print_info(f"Created: {name} (Technology) - Days {start_offset}-{end_offset}")
        
        # Paid Media tasks (well-spaced)
        media_tasks = [
            ("Campaign Planning", 5, 8, 40),  # Days 5-8
            ("Media Setup", 9, 12, 35),  # Days 9-12
            ("Campaign Launch", 13, 16, 45),  # Days 13-16
            ("Optimization", 17, 20, 30),  # Days 17-20
        ]
        
        for i, (name, start_offset, end_offset, hours) in enumerate(media_tasks):
            task = TimelineTask(
                id=f"media_{i+1}",
                name=f"Paid Media: {name}",
                deliverable_code=f"MEDIA_{i+1}",
                deliverable_name=name,
                department="Paid Media",
                start_date=(start_date + timedelta(days=start_offset)).strftime('%Y-%m-%d'),
                end_date=(start_date + timedelta(days=end_offset)).strftime('%Y-%m-%d'),
                hours=hours,
                color=DEPARTMENT_COLORS.get("Paid Media", "#48bb78")
            )
            tasks.append(task)
            print_info(f"Created: {name} (Paid Media) - Days {start_offset}-{end_offset}")
        
        # Content department (with retainer tasks)
        content_tasks = [
            ("Content Strategy", 1, 4, 30),  # Days 1-4
            ("Blog Content (Monthly)", 5, 25, 15, True),  # Ongoing retainer
            ("Social Media Content", 8, 20, 25, True),  # Ongoing retainer
        ]
        
        for i, (name, start_offset, end_offset, hours, *is_retainer) in enumerate(content_tasks):
            task = TimelineTask(
                id=f"content_{i+1}",
                name=f"Content: {name}",
                deliverable_code=f"CONTENT_{i+1}",
                deliverable_name=name,
                department="Content",
                start_date=(start_date + timedelta(days=start_offset)).strftime('%Y-%m-%d'),
                end_date=(start_date + timedelta(days=end_offset)).strftime('%Y-%m-%d'),
                hours=hours,
                color=DEPARTMENT_COLORS.get("Content", "#ed8936"),
                is_retainer=bool(is_retainer)
            )
            if is_retainer:
                task.monthly_hours = hours
            tasks.append(task)
            print_info(f"Created: {name} (Content) - Days {start_offset}-{end_offset} {'[RETAINER]' if is_retainer else ''}")
        
        print_success(f"Created {len(tasks)} tasks across 5 departments with conflicts")
        self.test_tasks = tasks
        return tasks
    
    def test_department_names(self, tasks: List[TimelineTask]) -> bool:
        """Test that all departments are correctly named (not 'General')"""
        print_header("Testing Department Names")
        
        valid_departments = set(DEPARTMENT_COLORS.keys())
        all_valid = True
        
        for task in tasks:
            if task.department == 'General' or task.department == '':
                print_error(f"Task '{task.name}' has invalid department: '{task.department}'")
                all_valid = False
            elif task.department not in valid_departments:
                print_warning(f"Task '{task.name}' has unknown department: '{task.department}'")
                self.results["warnings"] += 1
            else:
                print_success(f"Task '{task.name}' has valid department: {task.department}")
        
        if all_valid:
            print_success("All tasks have valid department names (no 'General')")
            self.results["passed"] += 1
        else:
            print_error("Some tasks have invalid department names")
            self.results["failed"] += 1
        
        return all_valid
    
    def test_conflict_detection(self, tasks: List[TimelineTask]) -> Dict[str, List[Any]]:
        """Test resource conflict detection"""
        print_header("Testing Conflict Detection")
        
        # Group tasks by department
        dept_tasks = {}
        for task in tasks:
            if task.department not in dept_tasks:
                dept_tasks[task.department] = []
            dept_tasks[task.department].append(task)
        
        conflicts = {}
        
        # Check for overlaps within each department
        for dept, dept_task_list in dept_tasks.items():
            dept_conflicts = []
            
            # Sort by start date
            sorted_tasks = sorted(dept_task_list, 
                                 key=lambda t: datetime.fromisoformat(t.start_date))
            
            for i in range(len(sorted_tasks) - 1):
                task1 = sorted_tasks[i]
                task2 = sorted_tasks[i + 1]
                
                # Check for overlap
                if task1.end_date > task2.start_date:
                    conflict = {
                        'task1': task1.name,
                        'task2': task2.name,
                        'overlap_start': task2.start_date,
                        'overlap_end': min(task1.end_date, task2.end_date)
                    }
                    dept_conflicts.append(conflict)
                    print_warning(f"Conflict in {dept}: '{task1.name}' overlaps with '{task2.name}'")
            
            if dept_conflicts:
                conflicts[dept] = dept_conflicts
        
        # Expected conflicts
        expected_conflicts = {
            "Strategy": 2,  # Research-Strategy, Strategy-Documentation
            "Technology": 3,  # Multiple overlaps
        }
        
        for dept, expected_count in expected_conflicts.items():
            if dept in conflicts:
                actual_count = len(conflicts[dept])
                if actual_count >= expected_count:
                    print_success(f"{dept}: Detected {actual_count} conflicts (expected at least {expected_count})")
                    self.results["passed"] += 1
                else:
                    print_error(f"{dept}: Only detected {actual_count} conflicts (expected {expected_count})")
                    self.results["failed"] += 1
            else:
                print_error(f"{dept}: No conflicts detected (expected {expected_count})")
                self.results["failed"] += 1
        
        return conflicts
    
    def test_resource_leveling(self, tasks: List[TimelineTask]) -> Dict[str, Any]:
        """Test resource leveling algorithm"""
        print_header("Testing Resource Leveling")
        
        # Run CPM analysis first
        cpm_calc = CPMCalculator(tasks)
        critical_path_ids, cpm_metrics = cpm_calc.calculate_cpm()
        
        print_info(f"Critical path contains {len(critical_path_ids)} tasks")
        
        # Create a copy of tasks for before/after comparison
        original_tasks = [
            {
                'id': t.id,
                'name': t.name,
                'start': t.start_date,
                'end': t.end_date,
                'leveled_start': t.leveled_start,
                'leveled_end': t.leveled_end
            }
            for t in tasks
        ]
        
        # Apply resource leveling
        leveler = ResourceLeveler(tasks)
        leveler.level_resources(critical_path_ids)
        
        # Check for changes
        changes = 0
        for i, task in enumerate(tasks):
            orig = original_tasks[i]
            if task.leveled_start != orig['leveled_start'] or task.leveled_end != orig['leveled_end']:
                changes += 1
                print_info(f"Task '{task.name}' was leveled:")
                print_info(f"  Original: {orig['start']} to {orig['end']}")
                print_info(f"  Leveled: {task.leveled_start} to {task.leveled_end}")
        
        if changes > 0:
            print_success(f"Resource leveling adjusted {changes} tasks")
            self.results["passed"] += 1
        else:
            print_warning("No tasks were adjusted by resource leveling")
            self.results["warnings"] += 1
        
        return {
            'tasks_adjusted': changes,
            'critical_path_size': len(critical_path_ids)
        }
    
    def test_resource_utilization(self, tasks: List[TimelineTask]) -> Dict[str, float]:
        """Test resource utilization calculation"""
        print_header("Testing Resource Utilization")
        
        # First run CPM to set early_start and early_finish values
        cpm_calc = CPMCalculator(tasks)
        critical_path_ids, cpm_metrics = cpm_calc.calculate_cpm()
        
        leveler = ResourceLeveler(tasks)
        utilization = leveler.calculate_resource_utilization()
        
        print_info("Resource Utilization by Department:")
        for dept, util_pct in utilization.items():
            util_display = f"{util_pct * 100:.1f}%"
            
            # Create a visual bar
            bar_length = int(util_pct * 20)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            
            if util_pct > 0.8:
                print_warning(f"  {dept:30} [{bar}] {util_display} (HIGH)")
            elif util_pct < 0.3:
                print_info(f"  {dept:30} [{bar}] {util_display} (LOW)")
            else:
                print_success(f"  {dept:30} [{bar}] {util_display}")
        
        # Validate calculations
        for dept, util in utilization.items():
            if 0 <= util <= 1.0:
                print_success(f"{dept} utilization is valid: {util:.2%}")
            else:
                print_error(f"{dept} utilization out of range: {util:.2%}")
                self.results["failed"] += 1
                return utilization
        
        self.results["passed"] += 1
        return utilization
    
    def test_api_endpoints(self):
        """Test API endpoints for resource risk features"""
        print_header("Testing API Endpoints")
        
        base_url = "http://localhost:5000"
        
        # Test timeline generation endpoint
        print_info("Testing /api/timeline/generate endpoint...")
        
        test_data = {
            "deliverables": [
                {
                    "deliverable_code": "TEST_001",
                    "deliverable_name": "Test Strategy",
                    "department": "Strategy",
                    "total_hours": 40,
                    "components": []
                },
                {
                    "deliverable_code": "TEST_002",
                    "deliverable_name": "Test Creative",
                    "department": "Creative",
                    "total_hours": 60,
                    "components": []
                }
            ],
            "rfp_text": "Test project for resource risk management",
            "optimization_mode": "balanced",
            "include_governance": False
        }
        
        try:
            # Use synchronous httpx for testing
            with httpx.Client() as client:
                response = client.post(
                    f"{base_url}/api/ai/generate_timeline",
                    json=test_data,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if "tasks" in result and "reasoning" in result:
                        print_success(f"Timeline API returned {len(result['tasks'])} tasks")
                        
                        # Check for CPM metrics
                        if "cpm" in result and "resource_utilization" in result["cpm"]:
                            print_success("CPM metrics include resource utilization")
                            self.results["passed"] += 1
                        else:
                            print_warning("CPM metrics missing resource utilization")
                            self.results["warnings"] += 1
                    else:
                        print_error("Timeline API response missing required fields")
                        self.results["failed"] += 1
                else:
                    print_error(f"Timeline API returned status {response.status_code}")
                    self.results["failed"] += 1
                    
        except Exception as e:
            print_error(f"Failed to test API: {e}")
            self.results["failed"] += 1
    
    def run_all_tests(self):
        """Run complete test suite"""
        print_header("RESOURCE RISK MANAGEMENT TEST SUITE")
        print_info(f"Starting at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. Create test timeline
        tasks = self.create_test_timeline_with_overlaps()
        
        # 2. Test department names
        self.test_department_names(tasks)
        
        # 3. Test conflict detection
        conflicts = self.test_conflict_detection(tasks)
        print_info(f"Total conflicts detected: {sum(len(c) for c in conflicts.values())}")
        
        # 4. Test resource utilization
        utilization = self.test_resource_utilization(tasks)
        
        # 5. Test resource leveling
        leveling_results = self.test_resource_leveling(tasks)
        
        # 6. Test API endpoints
        self.test_api_endpoints()
        
        # Final report
        print_header("TEST RESULTS SUMMARY")
        total = self.results["passed"] + self.results["failed"]
        
        if self.results["failed"] == 0:
            print(f"{GREEN}{BOLD}✅ ALL TESTS PASSED!{RESET}")
        else:
            print(f"{RED}{BOLD}❌ SOME TESTS FAILED{RESET}")
        
        print(f"\nPassed: {GREEN}{self.results['passed']}/{total}{RESET}")
        print(f"Failed: {RED}{self.results['failed']}/{total}{RESET}")
        print(f"Warnings: {YELLOW}{self.results['warnings']}{RESET}")
        
        # Success rate
        if total > 0:
            success_rate = (self.results["passed"] / total) * 100
            if success_rate == 100:
                print(f"\n{GREEN}Success Rate: {success_rate:.1f}%{RESET}")
            elif success_rate >= 80:
                print(f"\n{YELLOW}Success Rate: {success_rate:.1f}%{RESET}")
            else:
                print(f"\n{RED}Success Rate: {success_rate:.1f}%{RESET}")
        
        return self.results["failed"] == 0

def main():
    """Main test runner"""
    tester = ResourceRiskTester()
    
    # Run all tests
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()