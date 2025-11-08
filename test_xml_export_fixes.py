#!/usr/bin/env python3
"""
Comprehensive Test for 5 XML Export Fixes
Tests hours, assignments, predecessors, service categories, and revenue
"""

import os
import sys
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
from convert_excel_to_mspdi import convert_excel_to_mspdi

# ANSI color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}{text.center(80)}{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")

def print_pass(test_name):
    print(f"{GREEN}✓ PASS:{RESET} {test_name}")

def print_fail(test_name, details=""):
    print(f"{RED}✗ FAIL:{RESET} {test_name}")
    if details:
        print(f"  {YELLOW}Details:{RESET} {details}")

def create_test_data():
    """
    Create sample WBS data with all required test scenarios:
    - Deliverable with Service Category
    - Component under deliverable  
    - L3 task with PlannedHours=0 but role rows with hours
    - L3 task with PlannedHours > 0
    - Summary tasks and leaf tasks
    - Tasks with predecessor dependencies
    """
    
    data = []
    
    # Deliverable 1: Digital Marketing Campaign (with Service Category)
    # This deliverable has Service_Department = "Creative Services"
    
    # Deliverable row
    data.append({
        'WBS_ID': '1',
        'Parent_WBS_ID': '',  # No parent
        'Deliverable': 'Digital Marketing Campaign',
        'Deliverable_Code': 'DEL-001',
        'Service_Department': 'Creative Services',
        'Component': '',
        'Task_Name': '',
        'Planned_Hours': 0,
        'Role': '',
        'Seniority': '',
        'Rate_USD': 0,
        'Predecessor': ''
    })
    
    # Component 1.1: Strategy & Planning
    data.append({
        'WBS_ID': '1.1',
        'Parent_WBS_ID': '',  # No parent for component
        'Deliverable': 'Digital Marketing Campaign',
        'Deliverable_Code': 'DEL-001',
        'Service_Department': 'Creative Services',
        'Component': 'Strategy & Planning',
        'Task_Name': '',
        'Planned_Hours': 0,
        'Role': '',
        'Seniority': '',
        'Rate_USD': 0,
        'Predecessor': ''
    })
    
    # L3 Task with PlannedHours=0 but role assignments (FIX A & B TEST)
    data.append({
        'WBS_ID': '1.1.1',
        'Parent_WBS_ID': '',  # Parent task level
        'Deliverable': 'Digital Marketing Campaign',
        'Deliverable_Code': 'DEL-001',
        'Service_Department': 'Creative Services',
        'Component': 'Strategy & Planning',
        'Task_Name': 'Market Research',
        'Planned_Hours': 0,  # ZERO hours at L3 level
        'Role': '',
        'Seniority': '',
        'Rate_USD': 0,
        'Predecessor': ''
    })
    
    # Role rows under Market Research (should sum to create Task.Work)
    data.append({
        'WBS_ID': '1.1.1.1',
        'Parent_WBS_ID': '1.1.1',  # Parent is Market Research task
        'Deliverable': 'Digital Marketing Campaign',
        'Deliverable_Code': 'DEL-001',
        'Service_Department': 'Creative Services',
        'Component': 'Strategy & Planning',
        'Task_Name': 'Market Research',
        'Planned_Hours': 16,  # Role 1: 16 hours
        'Role': 'Strategist',
        'Seniority': 'Senior',
        'Rate_USD': 150,
        'Predecessor': ''
    })
    
    data.append({
        'WBS_ID': '1.1.1.2',
        'Parent_WBS_ID': '1.1.1',  # Parent is Market Research task
        'Deliverable': 'Digital Marketing Campaign',
        'Deliverable_Code': 'DEL-001',
        'Service_Department': 'Creative Services',
        'Component': 'Strategy & Planning',
        'Task_Name': 'Market Research',
        'Planned_Hours': 24,  # Role 2: 24 hours
        'Role': 'Analyst',
        'Seniority': 'Mid',
        'Rate_USD': 120,
        'Predecessor': ''
    })
    # Total for Market Research should be 40 hours (16+24)
    
    # L3 Task with PlannedHours > 0 (normal task)
    data.append({
        'WBS_ID': '1.1.2',
        'Parent_WBS_ID': '',  # Parent task level
        'Deliverable': 'Digital Marketing Campaign',
        'Deliverable_Code': 'DEL-001',
        'Service_Department': 'Creative Services',
        'Component': 'Strategy & Planning',
        'Task_Name': 'Develop Strategy',
        'Planned_Hours': 32,  # Has hours at L3
        'Role': '',
        'Seniority': '',
        'Rate_USD': 0,
        'Predecessor': '1.1.1'  # Depends on Market Research
    })
    
    # Role row under Develop Strategy
    data.append({
        'WBS_ID': '1.1.2.1',
        'Parent_WBS_ID': '1.1.2',  # Parent is Develop Strategy task
        'Deliverable': 'Digital Marketing Campaign',
        'Deliverable_Code': 'DEL-001',
        'Service_Department': 'Creative Services',
        'Component': 'Strategy & Planning',
        'Task_Name': 'Develop Strategy',
        'Planned_Hours': 32,
        'Role': 'Strategist',
        'Seniority': 'Senior',
        'Rate_USD': 150,
        'Predecessor': ''
    })
    
    # Component 1.2: Creative Development
    data.append({
        'WBS_ID': '1.2',
        'Parent_WBS_ID': '',  # No parent for component
        'Deliverable': 'Digital Marketing Campaign',
        'Deliverable_Code': 'DEL-001',
        'Service_Department': 'Creative Services',
        'Component': 'Creative Development',
        'Task_Name': '',
        'Planned_Hours': 0,
        'Role': '',
        'Seniority': '',
        'Rate_USD': 0,
        'Predecessor': ''
    })
    
    # L3 Task with multiple assignments (FIX E TEST)
    data.append({
        'WBS_ID': '1.2.1',
        'Parent_WBS_ID': '',  # Parent task level
        'Deliverable': 'Digital Marketing Campaign',
        'Deliverable_Code': 'DEL-001',
        'Service_Department': 'Creative Services',
        'Component': 'Creative Development',
        'Task_Name': 'Design Assets',
        'Planned_Hours': 0,
        'Role': '',
        'Seniority': '',
        'Rate_USD': 0,
        'Predecessor': '1.1.2'
    })
    
    # Multiple roles for cost calculation
    data.append({
        'WBS_ID': '1.2.1.1',
        'Parent_WBS_ID': '1.2.1',  # Parent is Design Assets task
        'Deliverable': 'Digital Marketing Campaign',
        'Deliverable_Code': 'DEL-001',
        'Service_Department': 'Creative Services',
        'Component': 'Creative Development',
        'Task_Name': 'Design Assets',
        'Planned_Hours': 40,
        'Role': 'Designer',
        'Seniority': 'Senior',
        'Rate_USD': 130,
        'Predecessor': ''
    })
    
    data.append({
        'WBS_ID': '1.2.1.2',
        'Parent_WBS_ID': '1.2.1',  # Parent is Design Assets task
        'Deliverable': 'Digital Marketing Campaign',
        'Deliverable_Code': 'DEL-001',
        'Service_Department': 'Creative Services',
        'Component': 'Creative Development',
        'Task_Name': 'Design Assets',
        'Planned_Hours': 20,
        'Role': 'Copywriter',
        'Seniority': 'Mid',
        'Rate_USD': 110,
        'Predecessor': ''
    })
    # Expected cost: (40 * 130) + (20 * 110) = 5200 + 2200 = 7400
    
    return pd.DataFrame(data)

def verify_fix_a_task_work_from_assignments(root, ns):
    """
    Fix A: Task.Work from assignments
    Find L3 task with PlannedHours=0 but assignments, verify Task.Work reflects sum
    """
    print_header("FIX A: Task.Work Calculated from Assignments")
    
    passed = True
    
    # Find "Market Research" task (has PlannedHours=0 but role assignments totaling 40h)
    tasks = root.findall(f".//{{{ns}}}Task")
    market_research_task = None
    
    for task in tasks:
        name_elem = task.find(f"{{{ns}}}Name")
        if name_elem is not None and name_elem.text == "Market Research":
            market_research_task = task
            break
    
    if market_research_task is None:
        print_fail("Find Market Research task", "Task not found in XML")
        return False
    
    print(f"  Found task: Market Research")
    
    # Check Task.Work element
    work_elem = market_research_task.find(f"{{{ns}}}Work")
    if work_elem is None:
        print_fail("Task.Work element exists", "Work element not found")
        return False
    
    work_value = work_elem.text
    print(f"  Task.Work value: {work_value}")
    
    # Expected: PT2400M (2400 minutes = 40 hours from 16+24)
    # MS Project uses PT format with minutes (PTnnnM) or hours (PTnnnH0M0S)
    expected_minutes = 2400  # 40 hours * 60 minutes
    
    # Parse work value
    if work_value.startswith("PT") and "M" in work_value:
        # Extract minutes (e.g., "PT2400M" -> 2400)
        work_minutes_str = work_value.replace("PT", "").replace("M", "").split("H")[0]
        try:
            work_minutes = int(work_minutes_str)
        except:
            work_minutes = 0
    else:
        work_minutes = 0
    
    if work_minutes != expected_minutes:
        print_fail(f"Task.Work = PT{expected_minutes}M (40 hours)", 
                   f"Got {work_value} ({work_minutes} minutes), expected PT{expected_minutes}M")
        passed = False
    else:
        print_pass(f"Task.Work = PT{expected_minutes}M (40 hours from assignments)")
    
    # Check RemainingWork
    remaining_work_elem = market_research_task.find(f"{{{ns}}}RemainingWork")
    if remaining_work_elem is not None:
        if remaining_work_elem.text != "PT40H0M0S":
            print_fail("RemainingWork matches Work", f"Got {remaining_work_elem.text}")
            passed = False
        else:
            print_pass("RemainingWork = PT40H0M0S")
    
    # Check RegularWork
    regular_work_elem = market_research_task.find(f"{{{ns}}}RegularWork")
    if regular_work_elem is not None:
        if regular_work_elem.text != "PT40H0M0S":
            print_fail("RegularWork matches Work", f"Got {regular_work_elem.text}")
            passed = False
        else:
            print_pass("RegularWork = PT40H0M0S")
    
    return passed

def verify_fix_b_assignments_when_l3_hours_zero(root, ns):
    """
    Fix B: Assignments when L3 hours=0
    Verify Assignment elements exist for Market Research task
    """
    print_header("FIX B: Assignments Exist for Zero-Hour L3 Tasks")
    
    passed = True
    
    # Find Market Research task UID
    tasks = root.findall(f".//{{{ns}}}Task")
    market_research_uid = None
    
    for task in tasks:
        name_elem = task.find(f"{{{ns}}}Name")
        if name_elem is not None and name_elem.text == "Market Research":
            uid_elem = task.find(f"{{{ns}}}UID")
            if uid_elem is not None:
                market_research_uid = uid_elem.text
                break
    
    if market_research_uid is None:
        print_fail("Find Market Research UID", "UID not found")
        return False
    
    print(f"  Market Research task UID: {market_research_uid}")
    
    # Find assignments for this task
    assignments = root.findall(f".//{{{ns}}}Assignment")
    task_assignments = []
    
    for assignment in assignments:
        task_uid_elem = assignment.find(f"{{{ns}}}TaskUID")
        if task_uid_elem is not None and task_uid_elem.text == market_research_uid:
            task_assignments.append(assignment)
    
    if len(task_assignments) == 0:
        print_fail("Assignments exist for Market Research", "No assignments found")
        return False
    
    print(f"  Found {len(task_assignments)} assignment(s)")
    
    # Verify assignment hours match role hours
    total_assignment_hours = 0
    for i, assignment in enumerate(task_assignments, 1):
        work_elem = assignment.find(f"{{{ns}}}Work")
        if work_elem is not None:
            work_value = work_elem.text
            print(f"  Assignment {i} Work: {work_value}")
            
            # Parse PT960M or PT16H0M0S format
            if work_value.startswith("PT"):
                try:
                    if "M" in work_value and "H" not in work_value:
                        # Format: PT960M (minutes only)
                        minutes = int(work_value.replace("PT", "").replace("M", ""))
                        hours = minutes / 60
                    elif "H" in work_value:
                        # Format: PT16H0M0S
                        hours_str = work_value.split("PT")[1].split("H")[0]
                        hours = float(hours_str)
                    else:
                        hours = 0
                    total_assignment_hours += hours
                except Exception as e:
                    print(f"    Warning: Could not parse work value '{work_value}': {e}")
    
    print(f"  Total assignment hours: {total_assignment_hours}")
    
    # Expected: 40 hours total (16 + 24)
    if abs(total_assignment_hours - 40.0) > 0.1:
        print_fail("Assignment hours = 40", f"Got {total_assignment_hours} hours")
        passed = False
    else:
        print_pass("Assignment hours = 40 (16 + 24 from roles)")
    
    return passed

def verify_fix_c_predecessor_safety(root, ns):
    """
    Fix C: Predecessor safety
    Verify summary tasks have NO PredecessorLink, leaf tasks HAVE them with Type=0
    """
    print_header("FIX C: Predecessor Safety (Only on Leaf Tasks, Type=0)")
    
    passed = True
    
    tasks = root.findall(f".//{{{ns}}}Task")
    
    summary_with_pred = []
    leaf_with_wrong_type = []
    
    for task in tasks:
        name_elem = task.find(f"{{{ns}}}Name")
        summary_elem = task.find(f"{{{ns}}}Summary")
        pred_links = task.findall(f"{{{ns}}}PredecessorLink")
        
        task_name = name_elem.text if name_elem is not None else "Unknown"
        is_summary = summary_elem is not None and summary_elem.text == "1"
        
        # Check summary tasks should NOT have predecessors
        if is_summary and len(pred_links) > 0:
            summary_with_pred.append(task_name)
        
        # Check leaf tasks with predecessors have Type=0
        if not is_summary and len(pred_links) > 0:
            for pred_link in pred_links:
                type_elem = pred_link.find(f"{{{ns}}}Type")
                if type_elem is not None and type_elem.text != "0":
                    leaf_with_wrong_type.append((task_name, type_elem.text))
    
    if len(summary_with_pred) > 0:
        print_fail("Summary tasks have NO predecessors", 
                   f"Found {len(summary_with_pred)} summary tasks with predecessors: {summary_with_pred[:3]}")
        passed = False
    else:
        print_pass("Summary tasks have NO PredecessorLink elements")
    
    if len(leaf_with_wrong_type) > 0:
        print_fail("Leaf task predecessors have Type=0", 
                   f"Found {len(leaf_with_wrong_type)} with wrong type: {leaf_with_wrong_type[:3]}")
        passed = False
    else:
        print_pass("All leaf task PredecessorLink elements have Type=0 (Finish-to-Start)")
    
    # Find "Develop Strategy" which should have a predecessor
    develop_strategy_task = None
    for task in tasks:
        name_elem = task.find(f"{{{ns}}}Name")
        if name_elem is not None and name_elem.text == "Develop Strategy":
            develop_strategy_task = task
            break
    
    if develop_strategy_task is not None:
        pred_links = develop_strategy_task.findall(f"{{{ns}}}PredecessorLink")
        if len(pred_links) > 0:
            print_pass("Develop Strategy has predecessor dependency")
        else:
            print_fail("Develop Strategy has predecessor", "No PredecessorLink found")
            passed = False
    
    return passed

def verify_fix_d_service_category_visibility(root, ns):
    """
    Fix D: Service Category visibility
    Verify deliverable has Service Category in both Text1 and Text4
    """
    print_header("FIX D: Service Category in Text1 and Text4")
    
    passed = True
    
    # Find "Digital Marketing Campaign" deliverable task
    tasks = root.findall(f".//{{{ns}}}Task")
    deliverable_task = None
    
    for task in tasks:
        name_elem = task.find(f"{{{ns}}}Name")
        if name_elem is not None and name_elem.text == "Digital Marketing Campaign":
            deliverable_task = task
            break
    
    if deliverable_task is None:
        print_fail("Find deliverable task", "Digital Marketing Campaign not found")
        return False
    
    print(f"  Found deliverable: Digital Marketing Campaign")
    
    # Check for Text1 ExtendedAttribute (Department)
    text1_value = None
    text4_value = None
    
    ext_attrs = deliverable_task.findall(f"{{{ns}}}ExtendedAttribute")
    for ext_attr in ext_attrs:
        field_id_elem = ext_attr.find(f"{{{ns}}}FieldID")
        value_elem = ext_attr.find(f"{{{ns}}}Value")
        
        if field_id_elem is not None and value_elem is not None:
            field_id = field_id_elem.text
            value = value_elem.text
            
            # Text1 = FieldID 188743731
            if field_id == "188743731":
                text1_value = value
                print(f"  Text1 (FieldID 188743731): {value}")
            
            # Text4 = FieldID 188743734
            if field_id == "188743734":
                text4_value = value
                print(f"  Text4 (FieldID 188743734): {value}")
    
    expected_service_cat = "Creative Services"
    
    if text1_value != expected_service_cat:
        print_fail("Text1 contains Service Category", 
                   f"Got '{text1_value}', expected '{expected_service_cat}'")
        passed = False
    else:
        print_pass(f"Text1 = '{expected_service_cat}'")
    
    if text4_value != expected_service_cat:
        print_fail("Text4 contains Service Category", 
                   f"Got '{text4_value}', expected '{expected_service_cat}'")
        passed = False
    else:
        print_pass(f"Text4 = '{expected_service_cat}'")
    
    if text1_value == text4_value and text1_value == expected_service_cat:
        print_pass("Text1 and Text4 match and contain correct Service Category")
    
    return passed

def verify_fix_e_task_cost_from_assignments(root, ns):
    """
    Fix E: Task.Cost from assignments
    Verify task cost equals sum of assignment costs
    """
    print_header("FIX E: Task.Cost Equals Sum of Assignment Costs")
    
    passed = True
    
    # Find "Design Assets" task with multiple assignments
    tasks = root.findall(f".//{{{ns}}}Task")
    design_assets_task = None
    design_assets_uid = None
    
    for task in tasks:
        name_elem = task.find(f"{{{ns}}}Name")
        if name_elem is not None and name_elem.text == "Design Assets":
            design_assets_task = task
            uid_elem = task.find(f"{{{ns}}}UID")
            if uid_elem is not None:
                design_assets_uid = uid_elem.text
            break
    
    if design_assets_task is None:
        print_fail("Find Design Assets task", "Task not found")
        return False
    
    print(f"  Found task: Design Assets (UID: {design_assets_uid})")
    
    # Get Task.Cost
    cost_elem = design_assets_task.find(f"{{{ns}}}Cost")
    task_cost = 0
    if cost_elem is not None:
        try:
            task_cost = float(cost_elem.text)
            print(f"  Task.Cost: ${task_cost}")
        except:
            pass
    
    # Get FixedCost
    fixed_cost_elem = design_assets_task.find(f"{{{ns}}}FixedCost")
    fixed_cost = 0
    if fixed_cost_elem is not None:
        try:
            fixed_cost = float(fixed_cost_elem.text)
            print(f"  Task.FixedCost: ${fixed_cost}")
        except:
            pass
    
    # Calculate sum of assignment costs
    assignments = root.findall(f".//{{{ns}}}Assignment")
    assignment_costs = []
    total_assignment_cost = 0
    
    for assignment in assignments:
        task_uid_elem = assignment.find(f"{{{ns}}}TaskUID")
        if task_uid_elem is not None and task_uid_elem.text == design_assets_uid:
            cost_elem = assignment.find(f"{{{ns}}}Cost")
            if cost_elem is not None:
                try:
                    cost = float(cost_elem.text)
                    assignment_costs.append(cost)
                    total_assignment_cost += cost
                except:
                    pass
    
    print(f"  Assignment costs: {assignment_costs}")
    print(f"  Sum of assignment costs: ${total_assignment_cost}")
    
    # Expected: (40 * 150) + (20 * 150) = 6000 + 3000 = 9000 (using blended_rate=150)
    expected_cost = 9000.0
    
    if abs(total_assignment_cost - expected_cost) > 0.01:
        print_fail("Sum of assignment costs = $7400", 
                   f"Got ${total_assignment_cost}, expected ${expected_cost}")
        passed = False
    else:
        print_pass(f"Sum of assignment costs = ${expected_cost}")
    
    if abs(task_cost - total_assignment_cost) > 0.01:
        print_fail("Task.Cost equals sum of assignments", 
                   f"Task.Cost=${task_cost}, Assignments=${total_assignment_cost}")
        passed = False
    else:
        print_pass(f"Task.Cost = ${task_cost} (matches assignments)")
    
    if abs(fixed_cost - task_cost) > 0.01:
        print_fail("FixedCost equals Task.Cost", 
                   f"FixedCost=${fixed_cost}, Task.Cost=${task_cost}")
        passed = False
    else:
        print_pass(f"FixedCost = ${fixed_cost} (matches Task.Cost)")
    
    return passed

def main():
    """Main test execution"""
    
    print_header("XML Export Fixes - Comprehensive Test Suite")
    print(f"{YELLOW}Testing 5 critical fixes for MSPDI XML export{RESET}\n")
    
    # Create test data
    print("📝 Creating test data...")
    df = create_test_data()
    print(f"   Created {len(df)} test rows")
    
    # Save to temporary Excel file
    temp_excel = "/tmp/test_xml_fixes.xlsx"
    temp_xml = "/tmp/test_xml_fixes.xml"
    
    print(f"💾 Saving test data to {temp_excel}...")
    df.to_excel(temp_excel, sheet_name="Scenario A", index=False)
    
    # Call convert_excel_to_mspdi
    print(f"🔄 Converting Excel to MSPDI XML...")
    try:
        result = convert_excel_to_mspdi(
            input_xlsx=temp_excel,
            output_xml=temp_xml,
            sheet_name="Scenario A",
            start_date_mode="fixed",
            fixed_start_iso="2025-01-13T09:00:00",
            merge_identical_children=False,
            project_name="XML Fixes Test Project",
            blended_rate=150.0,
            add_dependencies=True,
            add_custom_fields=True
        )
        print(f"   ✓ Conversion complete: {result.get('task_count', 0)} tasks created")
    except Exception as e:
        print(f"{RED}✗ Conversion failed: {e}{RESET}")
        return 1
    
    # Parse XML output
    print(f"📖 Parsing XML output...")
    try:
        tree = ET.parse(temp_xml)
        root = tree.getroot()
        ns = "http://schemas.microsoft.com/project"
        print(f"   ✓ XML parsed successfully")
    except Exception as e:
        print(f"{RED}✗ XML parsing failed: {e}{RESET}")
        return 1
    
    # Run all verification tests
    print("\n" + "="*80)
    print("RUNNING VERIFICATION TESTS")
    print("="*80 + "\n")
    
    results = {
        "Fix A: Task.Work from assignments": verify_fix_a_task_work_from_assignments(root, ns),
        "Fix B: Assignments when L3 hours=0": verify_fix_b_assignments_when_l3_hours_zero(root, ns),
        "Fix C: Predecessor safety": verify_fix_c_predecessor_safety(root, ns),
        "Fix D: Service Category visibility": verify_fix_d_service_category_visibility(root, ns),
        "Fix E: Task.Cost from assignments": verify_fix_e_task_cost_from_assignments(root, ns)
    }
    
    # Print summary
    print_header("TEST SUMMARY")
    
    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    for fix_name, passed in results.items():
        status = f"{GREEN}✅ PASS{RESET}" if passed else f"{RED}❌ FAIL{RESET}"
        print(f"{status} - {fix_name}")
    
    print(f"\n{BLUE}Results: {passed_count}/{total_count} tests passed{RESET}")
    
    if passed_count == total_count:
        print(f"\n{GREEN}{'='*80}{RESET}")
        print(f"{GREEN}{'ALL TESTS PASSED!'.center(80)}{RESET}")
        print(f"{GREEN}{'='*80}{RESET}\n")
        return 0
    else:
        print(f"\n{RED}{'='*80}{RESET}")
        print(f"{RED}{'SOME TESTS FAILED'.center(80)}{RESET}")
        print(f"{RED}{'='*80}{RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
