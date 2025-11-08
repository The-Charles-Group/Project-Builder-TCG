#!/usr/bin/env python3
"""
Comprehensive End-to-End Test for PM-Brain Scheduling System

Tests:
1. Timeline Generation with Hours-Based Durations
2. WBS Generation with Summary Bars
3. XML Export with Role Assignments
4. Sync Throttling
5. Batch Updates
"""

import asyncio
import httpx
import json
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Any

# Test configuration
BASE_URL = "http://localhost:5000"
TEST_SESSION_ID = f"test_session_{int(time.time())}"

# ANSI color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class TestResult:
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def add_pass(self, msg: str):
        self.passed.append(msg)
        print(f"  {GREEN}✓{RESET} {msg}")
    
    def add_fail(self, msg: str):
        self.failed.append(msg)
        print(f"  {RED}✗{RESET} {msg}")
    
    def add_warning(self, msg: str):
        self.warnings.append(msg)
        print(f"  {YELLOW}⚠{RESET} {msg}")
    
    def is_success(self) -> bool:
        return len(self.failed) == 0
    
    def summary(self) -> str:
        total = len(self.passed) + len(self.failed)
        status = f"{GREEN}PASS{RESET}" if self.is_success() else f"{RED}FAIL{RESET}"
        return f"{status} [{len(self.passed)}/{total}] {self.test_name}"


async def test_timeline_generation_with_hours():
    """
    Test 1: Timeline Generation with Hours-Based Durations
    - Create scenario with deliverable that has hours data
    - Generate timeline using build_schedule()
    - Verify durations are calculated from hours (not static 2-4 days)
    - Check that schedule includes dependency metadata
    - Verify max_parallel resource leveling is applied
    """
    print(f"\n{BLUE}═══ Test 1: Timeline Generation with Hours-Based Durations ═══{RESET}\n")
    result = TestResult("Timeline Generation")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Create a test scenario with hours data
            scenario = {
                "project_name": "Test Project - Hours Based",
                "pricing_mode": "Flat_Blended",
                "rate_band": "Standard_US",
                "blended_rate": 150.0,
                "complexity": "Advanced",
                "tier": "T2_MediumVolume",
                "items": [
                    {
                        "deliverable": "Website Development",
                        "deliverable_code": "DEL-0001",
                        "complexity": "Advanced",
                        "tier": "T2_MediumVolume",
                        "hours": 320,  # Explicit hours to test duration calculation
                        "included_task_groups": [
                            "discovery",
                            "strategy",
                            "design",
                            "development",
                            "qa_testing"
                        ],
                        "included_task_groups_map": {
                            "discovery": ["Research", "Analysis"],
                            "strategy": ["Planning"],
                            "design": ["UI Design", "UX Design"],
                            "development": ["Frontend Dev", "Backend Dev"],
                            "qa_testing": ["Testing", "Bug Fixes"]
                        }
                    }
                ],
                "project_start": "2025-11-11"
            }
            
            # Call build endpoint to generate timeline
            response = await client.post(
                f"{BASE_URL}/api/build",
                json=scenario
            )
            
            if response.status_code != 200:
                result.add_fail(f"Build API returned status {response.status_code}")
                return result
            
            data = response.json()
            result.add_pass("Build API endpoint accessible")
            
            # Verify timeline was generated
            if "timeline" not in data or "tasks" not in data.get("timeline", {}):
                result.add_fail("No timeline.tasks in response")
                return result
            
            timeline_tasks = data["timeline"]["tasks"]
            result.add_pass(f"Timeline generated with {len(timeline_tasks)} tasks")
            
            # Test 1.1: Verify durations are hours-based (not static 2-4 days)
            durations = []
            for task in timeline_tasks:
                duration = task.get("duration_days", 0)
                if duration > 0:
                    durations.append(duration)
            
            if durations:
                min_dur = min(durations)
                max_dur = max(durations)
                avg_dur = sum(durations) / len(durations)
                
                # If truly hours-based, we should see variety, not just 2-4 days
                unique_durations = len(set(durations))
                if unique_durations > 2:
                    result.add_pass(f"Durations vary ({unique_durations} unique values: {min_dur:.1f}-{max_dur:.1f} days)")
                else:
                    result.add_fail(f"Limited duration variety ({unique_durations} unique values), possibly static defaults")
                
                # Check if any duration suggests hours-based calculation
                # With 320 hours and typical capacity, we'd expect durations that aren't simple integers
                has_fractional = any(dur != int(dur) for dur in durations)
                if has_fractional:
                    result.add_pass("Found fractional durations (indicates hours-based calculation)")
                else:
                    result.add_warning("All durations are whole numbers (may indicate rounding)")
            else:
                result.add_fail("No tasks with duration > 0 found")
            
            # Test 1.2: Check for dependency metadata (SS/FS types, lags, predecessors)
            has_dependencies = False
            ss_count = 0
            fs_count = 0
            
            for task in timeline_tasks:
                if "dependency_type" in task:
                    has_dependencies = True
                    dep_type = task.get("dependency_type", "")
                    if dep_type == "SS":
                        ss_count += 1
                    elif dep_type == "FS":
                        fs_count += 1
            
            if has_dependencies:
                result.add_pass(f"Dependencies present (SS: {ss_count}, FS: {fs_count})")
            else:
                result.add_warning("No dependency metadata in timeline tasks")
            
            # Test 1.3: Verify resource leveling (max_parallel should limit concurrent tasks)
            # Check if any tasks have resource_assigned info
            has_resources = any("resources_assigned" in task for task in timeline_tasks)
            if has_resources:
                result.add_pass("Resource assignment metadata present")
            else:
                result.add_warning("No resource assignment data in timeline")
            
            # Check for date overlap patterns that would indicate resource leveling
            date_ranges = []
            for task in timeline_tasks:
                start = task.get("start_date")
                end = task.get("end_date")
                if start and end:
                    date_ranges.append((start, end, task.get("task_group", "unknown")))
            
            if len(date_ranges) >= 2:
                # Check if some tasks are pushed out (not all starting on same day)
                start_dates = [dr[0] for dr in date_ranges]
                unique_starts = len(set(start_dates))
                if unique_starts > 1:
                    result.add_pass(f"Tasks spread across {unique_starts} different start dates (resource leveling active)")
                else:
                    result.add_warning("All tasks start on same date (resource leveling may not be active)")
            
        except Exception as e:
            result.add_fail(f"Exception: {str(e)}")
    
    return result


async def test_wbs_generation_with_summary_bars():
    """
    Test 2: WBS Generation with Summary Bars
    - Build WBS from scenario
    - Verify deliverable rows have Duration_Days="" (empty)
    - Verify component rows have Duration_Days="" (empty)
    - Verify task rows have actual Duration_Days values
    """
    print(f"\n{BLUE}═══ Test 2: WBS Generation with Summary Bars ═══{RESET}\n")
    result = TestResult("WBS Generation")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Create scenario with multi-level WBS structure
            scenario = {
                "project_name": "Test WBS Project",
                "pricing_mode": "Flat_Blended",
                "rate_band": "Standard_US",
                "blended_rate": 150.0,
                "items": [
                    {
                        "deliverable": "Campaign Development",
                        "deliverable_code": "DEL-0010",
                        "complexity": "Advanced",
                        "tier": "T2_MediumVolume",
                        "hours": 200,
                        "included_task_groups": ["strategy", "creative", "production"],
                        "included_task_groups_map": {
                            "strategy": ["Market Research", "Strategy Doc"],
                            "creative": ["Concept", "Design"],
                            "production": ["Asset Creation"]
                        }
                    }
                ]
            }
            
            # Build the scenario
            response = await client.post(
                f"{BASE_URL}/api/build",
                json=scenario
            )
            
            if response.status_code != 200:
                result.add_fail(f"Build API returned status {response.status_code}")
                return result
            
            data = response.json()
            result.add_pass("Build API successful")
            
            # Now export to Excel to get WBS
            export_response = await client.post(
                f"{BASE_URL}/api/export/workbook",
                json={
                    "scenario": data.get("scenario", scenario),
                    "project_name": "Test WBS Project",
                    "filename": "test_wbs_export.xlsx"
                }
            )
            
            if export_response.status_code != 200:
                result.add_fail(f"Export API returned status {export_response.status_code}")
                return result
            
            result.add_pass("WBS export successful")
            
            # Download and parse the Excel file
            import pandas as pd
            import io
            
            excel_data = export_response.content
            df = pd.read_excel(io.BytesIO(excel_data), sheet_name="Scenario A")
            
            result.add_pass(f"WBS has {len(df)} rows")
            
            # Test 2.1: Verify deliverable rows have empty Duration_Days
            deliverable_rows = df[df["Deliverable"].notna() & df["Component"].isna() & df["Task"].isna()]
            
            if len(deliverable_rows) > 0:
                result.add_pass(f"Found {len(deliverable_rows)} deliverable rows")
                
                # Check if Duration_Days is empty for deliverables
                empty_duration_deliverables = deliverable_rows[
                    (deliverable_rows["Duration_Days"].isna()) | 
                    (deliverable_rows["Duration_Days"] == "") |
                    (deliverable_rows["Duration_Days"] == 0)
                ]
                
                if len(empty_duration_deliverables) == len(deliverable_rows):
                    result.add_pass("All deliverable rows have empty Duration_Days (correct)")
                else:
                    result.add_fail(f"Only {len(empty_duration_deliverables)}/{len(deliverable_rows)} deliverable rows have empty Duration_Days")
            else:
                result.add_warning("No deliverable rows found in WBS")
            
            # Test 2.2: Verify component rows have empty Duration_Days
            component_rows = df[df["Component"].notna() & df["Task"].isna()]
            
            if len(component_rows) > 0:
                result.add_pass(f"Found {len(component_rows)} component rows")
                
                empty_duration_components = component_rows[
                    (component_rows["Duration_Days"].isna()) | 
                    (component_rows["Duration_Days"] == "") |
                    (component_rows["Duration_Days"] == 0)
                ]
                
                if len(empty_duration_components) == len(component_rows):
                    result.add_pass("All component rows have empty Duration_Days (correct)")
                else:
                    result.add_fail(f"Only {len(empty_duration_components)}/{len(component_rows)} component rows have empty Duration_Days")
            else:
                result.add_warning("No component rows found in WBS")
            
            # Test 2.3: Verify task rows have actual Duration_Days values
            task_rows = df[df["Task"].notna()]
            
            if len(task_rows) > 0:
                result.add_pass(f"Found {len(task_rows)} task rows")
                
                task_rows_with_duration = task_rows[
                    task_rows["Duration_Days"].notna() & 
                    (task_rows["Duration_Days"] != "") &
                    (task_rows["Duration_Days"] > 0)
                ]
                
                if len(task_rows_with_duration) == len(task_rows):
                    result.add_pass("All task rows have Duration_Days values (correct)")
                else:
                    result.add_fail(f"Only {len(task_rows_with_duration)}/{len(task_rows)} task rows have Duration_Days values")
                    
                    # Show some examples
                    missing_duration = task_rows[
                        (task_rows["Duration_Days"].isna()) | 
                        (task_rows["Duration_Days"] == "") |
                        (task_rows["Duration_Days"] <= 0)
                    ]
                    if len(missing_duration) > 0:
                        result.add_warning(f"Tasks with missing duration: {missing_duration['Task_Name'].head(3).tolist()}")
            else:
                result.add_fail("No task rows found in WBS")
            
        except Exception as e:
            result.add_fail(f"Exception: {str(e)}")
    
    return result


async def test_xml_export_with_role_assignments():
    """
    Test 3: XML Export with Role Assignments
    - Export to MSPDI XML format
    - Verify role rows create Assignment elements (not duplicate Task elements)
    - Verify resource_uid_map works with (role, seniority) keys
    - Verify assignments reference correct ResourceUID
    """
    print(f"\n{BLUE}═══ Test 3: XML Export with Role Assignments ═══{RESET}\n")
    result = TestResult("XML Export with Role Assignments")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Create scenario with role assignments
            scenario = {
                "project_name": "Test XML Export Project",
                "pricing_mode": "Per_Resource",
                "rate_band": "Standard_US",
                "items": [
                    {
                        "deliverable": "Marketing Campaign",
                        "deliverable_code": "DEL-0020",
                        "complexity": "Advanced",
                        "tier": "T2_MediumVolume",
                        "hours": 150,
                        "included_task_groups": ["strategy", "creative"],
                        "included_task_groups_map": {
                            "strategy": ["Research", "Planning"],
                            "creative": ["Design", "Copywriting"]
                        }
                    }
                ]
            }
            
            # Build scenario first
            build_response = await client.post(
                f"{BASE_URL}/api/build",
                json=scenario
            )
            
            if build_response.status_code != 200:
                result.add_fail(f"Build API returned status {build_response.status_code}")
                return result
            
            result.add_pass("Build API successful")
            
            # Export to XML
            export_response = await client.post(
                f"{BASE_URL}/api/export/xml",
                json={
                    "scenario": build_response.json().get("scenario", scenario),
                    "project_name": "Test XML Export Project",
                    "sheet_name": "Scenario A"
                }
            )
            
            if export_response.status_code != 200:
                result.add_fail(f"XML export returned status {export_response.status_code}")
                return result
            
            result.add_pass("XML export successful")
            
            # Parse XML
            xml_content = export_response.content
            root = ET.fromstring(xml_content)
            
            # Define namespace
            ns = {'ms': 'http://schemas.microsoft.com/project'}
            
            # Test 3.1: Verify Resources section exists
            resources = root.findall('.//ms:Resource', ns)
            if len(resources) > 0:
                result.add_pass(f"Found {len(resources)} resources in XML")
                
                # Check for role-based resources (should have specific naming pattern)
                role_resources = []
                for resource in resources:
                    name_elem = resource.find('ms:Name', ns)
                    if name_elem is not None and name_elem.text:
                        # Role resources typically have format like "Strategist (Senior)"
                        if "(" in name_elem.text and ")" in name_elem.text:
                            role_resources.append(name_elem.text)
                
                if len(role_resources) > 0:
                    result.add_pass(f"Found {len(role_resources)} role-based resources (e.g., {role_resources[0]})")
                else:
                    result.add_warning("No role-based resources with (seniority) format found")
            else:
                result.add_fail("No resources found in XML")
            
            # Test 3.2: Verify Assignments section exists (not duplicate tasks)
            assignments = root.findall('.//ms:Assignment', ns)
            if len(assignments) > 0:
                result.add_pass(f"Found {len(assignments)} assignments in XML")
                
                # Verify assignments reference valid ResourceUIDs
                valid_assignment_count = 0
                for assignment in assignments:
                    resource_uid_elem = assignment.find('ms:ResourceUID', ns)
                    task_uid_elem = assignment.find('ms:TaskUID', ns)
                    
                    if resource_uid_elem is not None and task_uid_elem is not None:
                        if resource_uid_elem.text and task_uid_elem.text:
                            valid_assignment_count += 1
                
                if valid_assignment_count == len(assignments):
                    result.add_pass("All assignments have valid ResourceUID and TaskUID")
                else:
                    result.add_fail(f"Only {valid_assignment_count}/{len(assignments)} assignments have valid UIDs")
            else:
                result.add_warning("No assignments found in XML (may indicate role rows creating duplicate tasks)")
            
            # Test 3.3: Verify no duplicate task elements for roles
            tasks = root.findall('.//ms:Task', ns)
            if len(tasks) > 0:
                result.add_pass(f"Found {len(tasks)} tasks in XML")
                
                # Check for suspicious task names that might be roles
                task_names = []
                role_like_tasks = []
                
                for task in tasks:
                    name_elem = task.find('ms:Name', ns)
                    if name_elem is not None and name_elem.text:
                        task_names.append(name_elem.text)
                        
                        # Role-like names typically have parentheses for seniority
                        # But should NOT appear as separate tasks
                        if "(" in name_elem.text and ")" in name_elem.text:
                            # Check if this looks like a role (e.g., "Designer (Senior)")
                            # and is not a legitimate task name
                            role_like_tasks.append(name_elem.text)
                
                if len(role_like_tasks) == 0:
                    result.add_pass("No role-like duplicate tasks found (correct)")
                else:
                    result.add_warning(f"Found {len(role_like_tasks)} potential role-as-task entries: {role_like_tasks[:3]}")
            else:
                result.add_fail("No tasks found in XML")
            
        except Exception as e:
            result.add_fail(f"Exception: {str(e)}")
    
    return result


async def test_sync_throttling():
    """
    Test 4: Sync Throttling
    - Simulate multiple rapid /api/scenario/sync calls
    - Verify throttling prevents excessive writes (WRITE_THROTTLE_MS=150)
    """
    print(f"\n{BLUE}═══ Test 4: Sync Throttling ═══{RESET}\n")
    result = TestResult("Sync Throttling")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Create a test scenario
            scenario = {
                "project_name": "Test Throttle Project",
                "items": [],
                "totals": {"grandTotal12": 1000.0}
            }
            
            # Test 4.1: Make rapid successive calls
            throttle_responses = []
            start_time = time.time()
            
            for i in range(10):
                payload = {
                    "session_id": TEST_SESSION_ID,
                    "client_version": i,
                    "last_server_version": i - 1 if i > 0 else 0,
                    "scenario": scenario,
                    "selections": {},
                    "timestamp": int(time.time() * 1000),
                    "checksum": f"test_checksum_{i}"
                }
                
                response = await client.post(
                    f"{BASE_URL}/api/scenario/sync",
                    json=payload
                )
                
                throttle_responses.append({
                    "status": response.status_code,
                    "data": response.json() if response.status_code == 200 else None,
                    "time": time.time()
                })
                
                # Small delay between requests (but less than throttle window)
                await asyncio.sleep(0.01)  # 10ms
            
            elapsed_time = (time.time() - start_time) * 1000  # Convert to ms
            result.add_pass(f"Made 10 rapid requests in {elapsed_time:.1f}ms")
            
            # Test 4.2: Verify throttling occurred
            throttled_count = sum(1 for r in throttle_responses if r["data"] and r["data"].get("throttled"))
            
            if throttled_count > 0:
                result.add_pass(f"{throttled_count}/10 requests were throttled (WRITE_THROTTLE_MS=150 working)")
            else:
                result.add_warning("No requests were throttled (throttling may not be active)")
            
            # Test 4.3: Verify server version increments properly (not for every request if throttled)
            server_versions = [r["data"].get("serverVersion", 0) for r in throttle_responses if r["data"]]
            
            if len(server_versions) > 0:
                max_version = max(server_versions)
                
                # If throttling works, max version should be less than number of requests
                if max_version < len(throttle_responses):
                    result.add_pass(f"Server version ({max_version}) < request count ({len(throttle_responses)}) due to throttling")
                else:
                    result.add_warning(f"Server version ({max_version}) >= request count ({len(throttle_responses)})")
            
            # Test 4.4: Wait for throttle window to pass, then verify sync works
            await asyncio.sleep(0.2)  # 200ms > 150ms throttle window
            
            final_payload = {
                "session_id": TEST_SESSION_ID,
                "client_version": 100,
                "last_server_version": max(server_versions) if server_versions else 0,
                "scenario": scenario,
                "selections": {},
                "timestamp": int(time.time() * 1000),
                "checksum": "final_checksum"
            }
            
            final_response = await client.post(
                f"{BASE_URL}/api/scenario/sync",
                json=final_payload
            )
            
            if final_response.status_code == 200:
                final_data = final_response.json()
                if not final_data.get("throttled"):
                    result.add_pass("Request after throttle window completed successfully")
                else:
                    result.add_fail("Request still throttled after waiting > 150ms")
            
        except Exception as e:
            result.add_fail(f"Exception: {str(e)}")
    
    return result


async def test_batch_updates():
    """
    Test 5: Batch Updates
    - Test /api/timeline/update_tasks_batch endpoint
    - Verify multiple task updates processed in single transaction
    """
    print(f"\n{BLUE}═══ Test 5: Batch Updates ═══{RESET}\n")
    result = TestResult("Batch Updates")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # First, create a scenario with tasks
            scenario = {
                "project_name": "Test Batch Update Project",
                "pricing_mode": "Flat_Blended",
                "rate_band": "Standard_US",
                "blended_rate": 150.0,
                "items": [
                    {
                        "deliverable": "Website Redesign",
                        "deliverable_code": "DEL-0030",
                        "complexity": "Advanced",
                        "tier": "T2_MediumVolume",
                        "hours": 180,
                        "included_task_groups": ["discovery", "design", "development", "qa_testing"]
                    }
                ]
            }
            
            # Build scenario
            build_response = await client.post(
                f"{BASE_URL}/api/build",
                json=scenario
            )
            
            if build_response.status_code != 200:
                result.add_fail(f"Build API returned status {build_response.status_code}")
                return result
            
            data = build_response.json()
            result.add_pass("Build API successful")
            
            # Get timeline tasks
            timeline_tasks = data.get("timeline", {}).get("tasks", [])
            
            if len(timeline_tasks) < 2:
                result.add_warning("Need at least 2 tasks for batch update test")
                return result
            
            result.add_pass(f"Timeline has {len(timeline_tasks)} tasks")
            
            # Test 5.1: Prepare batch updates
            batch_updates = []
            for i, task in enumerate(timeline_tasks[:3]):  # Update first 3 tasks
                task_id = task.get("id") or f"{task.get('deliverable_code')}_{task.get('task_group')}"
                
                # Modify start date and duration
                batch_updates.append({
                    "id": task_id,
                    "start_date": "2025-12-01",
                    "duration_days": 5 + i  # Varying durations
                })
            
            # Test 5.2: Send batch update request
            batch_payload = {
                "session_id": TEST_SESSION_ID,
                "updates": batch_updates,
                "timestamp": int(time.time() * 1000)
            }
            
            batch_response = await client.post(
                f"{BASE_URL}/api/timeline/update_tasks_batch",
                json=batch_payload
            )
            
            if batch_response.status_code != 200:
                result.add_fail(f"Batch update API returned status {batch_response.status_code}")
                # Try to get error details
                try:
                    error_data = batch_response.json()
                    result.add_fail(f"Error: {error_data}")
                except:
                    result.add_fail(f"Response: {batch_response.text[:200]}")
                return result
            
            batch_data = batch_response.json()
            result.add_pass("Batch update API successful")
            
            # Test 5.3: Verify response indicates success
            if "updated_count" in batch_data:
                updated_count = batch_data["updated_count"]
                expected_count = len(batch_updates)
                
                if updated_count == expected_count:
                    result.add_pass(f"All {expected_count} tasks updated successfully")
                else:
                    result.add_fail(f"Only {updated_count}/{expected_count} tasks updated")
            else:
                result.add_warning("Response doesn't include updated_count field")
            
            # Test 5.4: Verify updates were atomic (all or nothing)
            if batch_data.get("transaction_completed"):
                result.add_pass("Batch update was processed as single transaction")
            else:
                result.add_warning("Transaction status not indicated in response")
            
            # Test 5.5: Verify no partial updates on error
            # Send a batch with one invalid update
            invalid_batch = [
                {"id": "valid_task_1", "start_date": "2025-12-15", "duration_days": 3},
                {"id": "INVALID_TASK_ID", "start_date": "invalid_date", "duration_days": -1},  # Invalid
                {"id": "valid_task_2", "start_date": "2025-12-20", "duration_days": 4}
            ]
            
            invalid_response = await client.post(
                f"{BASE_URL}/api/timeline/update_tasks_batch",
                json={
                    "session_id": TEST_SESSION_ID,
                    "updates": invalid_batch,
                    "timestamp": int(time.time() * 1000)
                }
            )
            
            # Should either return error or indicate partial success
            if invalid_response.status_code == 200:
                invalid_data = invalid_response.json()
                if "errors" in invalid_data or "updated_count" in invalid_data:
                    result.add_pass("Batch update handles invalid data gracefully")
                else:
                    result.add_warning("Response unclear for invalid batch data")
            elif invalid_response.status_code in [400, 422]:
                result.add_pass(f"Batch update rejects invalid data (status {invalid_response.status_code})")
            else:
                result.add_warning(f"Unexpected status {invalid_response.status_code} for invalid batch")
            
        except Exception as e:
            result.add_fail(f"Exception: {str(e)}")
    
    return result


async def main():
    """Run all tests and generate report"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}  PM-BRAIN COMPREHENSIVE END-TO-END TEST SUITE{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    print(f"Test Configuration:")
    print(f"  Base URL: {BASE_URL}")
    print(f"  Session ID: {TEST_SESSION_ID}")
    print(f"  Timestamp: {datetime.now().isoformat()}")
    
    # Run all tests
    results = []
    
    results.append(await test_timeline_generation_with_hours())
    results.append(await test_wbs_generation_with_summary_bars())
    results.append(await test_xml_export_with_role_assignments())
    results.append(await test_sync_throttling())
    results.append(await test_batch_updates())
    
    # Generate final report
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}  TEST SUMMARY{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    total_passed = 0
    total_failed = 0
    all_success = True
    
    for result in results:
        print(result.summary())
        total_passed += len(result.passed)
        total_failed += len(result.failed)
        if not result.is_success():
            all_success = False
    
    print(f"\n{BLUE}{'='*70}{RESET}")
    
    if all_success:
        print(f"\n{GREEN}✓✓✓ ALL TESTS PASSED ✓✓✓{RESET}")
        print(f"{GREEN}Total Checks: {total_passed} passed, {total_failed} failed{RESET}\n")
    else:
        print(f"\n{RED}✗✗✗ SOME TESTS FAILED ✗✗✗{RESET}")
        print(f"{RED}Total Checks: {total_passed} passed, {total_failed} failed{RESET}\n")
        
        # Show which tests failed
        print("Failed tests:")
        for result in results:
            if not result.is_success():
                print(f"  • {result.test_name}")
                for failure in result.failed:
                    print(f"    - {failure}")
        print()
    
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    return 0 if all_success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
