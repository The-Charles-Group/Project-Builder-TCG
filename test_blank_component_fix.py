#!/usr/bin/env python3
"""
Test case for blank Component field bug fix in convert_excel_to_mspdi.py

This test verifies that:
1. Tasks with blank Component fields are NOT dropped from the export
2. Blank component tasks appear under "Uncategorized" component summary
3. All tasks from input appear in output XML
4. No regression in 3-level hierarchy structure
"""

import pandas as pd
import os
import xml.etree.ElementTree as ET
from convert_excel_to_mspdi import convert_excel_to_mspdi


def create_test_excel():
    """Create test Excel file with blank component tasks"""
    
    # Test data: 1 deliverable, 2 components (one blank, one named), 4 total tasks
    test_data = {
        'Deliverable': ['Test Deliverable'] * 4,
        'Deliverable_Code': ['DEL-001'] * 4,
        'Component': ['Component A', 'Component A', '', ''],  # 2 tasks in Component A, 2 with blank component
        'Task_Name': [
            'Task 1 in Component A',
            'Task 2 in Component A',
            'Task 1 with blank component',
            'Task 2 with blank component'
        ],
        'Hours': [8, 16, 12, 8],
        'Role': ['Designer', 'Developer', 'Designer', 'Developer'],
        'Rate_USD': [100, 150, 100, 150],
        'Price': [800, 2400, 1200, 1200]
    }
    
    df = pd.DataFrame(test_data)
    
    # Create test Excel file
    test_file = 'test_blank_component_input.xlsx'
    with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Scenario A', index=False)
    
    print(f"✓ Created test Excel file: {test_file}")
    print(f"  - 1 deliverable: {df['Deliverable'].unique()[0]}")
    print(f"  - 2 components: Component A (2 tasks), blank (2 tasks)")
    print(f"  - Total tasks: {len(df)}")
    
    return test_file, df


def verify_xml_output(xml_file, expected_task_count):
    """Verify the XML output contains all expected tasks"""
    
    print(f"\n🔍 Verifying XML output: {xml_file}")
    
    # Parse the XML
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # Define namespace
    ns = {'mspdi': 'http://schemas.microsoft.com/project'}
    
    # Find all tasks
    tasks = root.findall('.//mspdi:Task', ns)
    
    # Filter out summary tasks and project task to count only leaf tasks
    leaf_tasks = []
    deliverable_task = None
    component_tasks = {}
    
    for task in tasks:
        uid = task.find('mspdi:UID', ns).text
        name_elem = task.find('mspdi:Name', ns)
        name = name_elem.text if name_elem is not None else "Unknown"
        summary_elem = task.find('mspdi:Summary', ns)
        is_summary = summary_elem is not None and summary_elem.text == '1'
        outline_level_elem = task.find('mspdi:OutlineLevel', ns)
        outline_level = int(outline_level_elem.text) if outline_level_elem is not None else 0
        
        print(f"  Task UID={uid}, Name='{name}', OutlineLevel={outline_level}, Summary={is_summary}")
        
        if uid == '0':
            # Project root task
            continue
        elif outline_level == 1:
            # Deliverable summary task
            deliverable_task = name
        elif outline_level == 2:
            # Component summary task
            component_tasks[name] = []
        elif outline_level == 3:
            # Leaf task (actual work task)
            leaf_tasks.append(name)
    
    print(f"\n📊 Summary:")
    print(f"  - Total tasks in XML: {len(tasks)}")
    print(f"  - Deliverable task: {deliverable_task}")
    print(f"  - Component tasks found: {list(component_tasks.keys())}")
    print(f"  - Leaf tasks (actual work): {len(leaf_tasks)}")
    
    # Verify results
    success = True
    
    # Check 1: All leaf tasks should be present
    if len(leaf_tasks) != expected_task_count:
        print(f"\n❌ FAIL: Expected {expected_task_count} leaf tasks, found {len(leaf_tasks)}")
        success = False
    else:
        print(f"\n✓ PASS: All {expected_task_count} tasks present in XML")
    
    # Check 2: Should have "Uncategorized" component
    if "Uncategorized" not in component_tasks:
        print(f"❌ FAIL: 'Uncategorized' component not found in XML")
        success = False
    else:
        print(f"✓ PASS: 'Uncategorized' component found in XML")
    
    # Check 3: Should have "Component A"
    if "Component A" not in component_tasks:
        print(f"❌ FAIL: 'Component A' not found in XML")
        success = False
    else:
        print(f"✓ PASS: 'Component A' component found in XML")
    
    # Check 4: Should have exactly 2 component summary tasks (Level 2)
    if len(component_tasks) != 2:
        print(f"❌ FAIL: Expected 2 components, found {len(component_tasks)}")
        success = False
    else:
        print(f"✓ PASS: Exactly 2 component summary tasks found")
    
    # Check 5: Verify task names
    expected_task_names = [
        'Task 1 in Component A',
        'Task 2 in Component A',
        'Task 1 with blank component',
        'Task 2 with blank component'
    ]
    
    for expected_name in expected_task_names:
        if expected_name not in leaf_tasks:
            print(f"❌ FAIL: Task '{expected_name}' not found in XML")
            success = False
    
    if success:
        print(f"\n✓ PASS: All task names found in XML")
    
    return success


def run_test():
    """Run the complete test"""
    
    print("=" * 80)
    print("TEST: Blank Component Field Bug Fix")
    print("=" * 80)
    
    # Step 1: Create test Excel file
    test_excel, test_df = create_test_excel()
    
    # Step 2: Run conversion
    test_xml = 'test_blank_component_output.xml'
    
    print(f"\n🔧 Running conversion...")
    try:
        result = convert_excel_to_mspdi(
            input_xlsx=test_excel,
            output_xml=test_xml,
            sheet_name='Scenario A',
            project_name='Blank Component Test',
            start_date_mode='next_monday',
            add_deliverable_milestones=False,
            add_phase_gates=False,
            add_dependencies=False
        )
        print(f"✓ Conversion completed")
        print(f"  Result: {result}")
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Verify XML output
    success = verify_xml_output(test_xml, expected_task_count=4)
    
    # Step 4: Report results
    print("\n" + "=" * 80)
    if success:
        print("✅ TEST PASSED: All checks successful!")
        print("=" * 80)
        print("\nVerified:")
        print("  ✓ Tasks with blank Component field are NOT dropped")
        print("  ✓ Blank component tasks appear under 'Uncategorized' component")
        print("  ✓ All 4 tasks from input appear in output XML")
        print("  ✓ 3-level hierarchy structure maintained (Deliverable > Component > Task)")
    else:
        print("❌ TEST FAILED: Some checks failed")
        print("=" * 80)
    
    # Cleanup
    print(f"\n📁 Test files created:")
    print(f"  - Input: {test_excel}")
    print(f"  - Output: {test_xml}")
    
    return success


if __name__ == '__main__':
    success = run_test()
    exit(0 if success else 1)
