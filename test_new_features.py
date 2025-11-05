#!/usr/bin/env python3
"""
Test script for the three new Workfront export features:
1. Cost/Revenue aggregation
2. Service Category mapping
3. Dependency/Predecessor links
"""

import pandas as pd
import xml.etree.ElementTree as ET
from convert_excel_to_mspdi import convert_excel_to_mspdi
import os

def create_test_data():
    """Create a test DataFrame with all required fields"""
    data = {
        'Deliverable': ['Phase 1', 'Phase 1', 'Phase 1', 'Phase 1', 'Phase 2', 'Phase 2'],
        'Component': ['Planning', 'Planning', 'Execution', 'Execution', 'Review', 'Review'],
        'Task_Name': ['Task 1.1.1', 'Task 1.1.2', 'Task 1.2.1', 'Task 1.2.2', 'Task 2.1.1', 'Task 2.1.2'],
        'Planned_Hours': [8, 16, 24, 32, 8, 16],
        'Price_USD': [1000.0, 2000.0, 3000.0, 4000.0, 500.0, 1500.0],
        'Service_Department': ['Strategy', 'Creative', 'Technology', 'Content', 'Quality Assurance', 'Creative'],
        'Dependencies': ['', '', '1.1', '1.1.1', '1.2', '2.1.1'],
        'Department': ['Strategy', 'Creative', 'Technology', 'Content', 'Quality Assurance', 'Creative'],
        'Deliverable_Code': ['DEL1', 'DEL1', 'DEL1', 'DEL1', 'DEL2', 'DEL2']
    }
    
    df = pd.DataFrame(data)
    return df

def verify_xml_features(xml_file):
    """Verify that the XML has all three implemented features"""
    ns = "http://schemas.microsoft.com/project"
    
    # Parse XML
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # Define namespace for searches
    ns_dict = {'ns': ns}
    
    print("\n=== VERIFICATION RESULTS ===\n")
    
    # 1. Verify Revenue ExtendedAttribute definition exists
    print("1. REVENUE EXTENDED ATTRIBUTE DEFINITION:")
    ext_attrs = root.findall('.//ns:ExtendedAttribute', ns_dict)
    revenue_def_found = False
    for ext_attr in ext_attrs:
        alias = ext_attr.find('ns:Alias', ns_dict)
        if alias is not None and alias.text == 'Revenue':
            revenue_def_found = True
            field_id = ext_attr.find('ns:FieldID', ns_dict).text
            print(f"   ✓ Revenue ExtendedAttribute definition found (FieldID: {field_id})")
            break
    
    if not revenue_def_found:
        print("   ✗ Revenue ExtendedAttribute definition NOT found")
    
    # 2. Verify Cost/Revenue aggregation on summary tasks
    print("\n2. COST/REVENUE AGGREGATION:")
    tasks = root.findall('.//ns:Task', ns_dict)
    summary_tasks_with_cost = 0
    leaf_tasks_with_cost = 0
    
    for task in tasks:
        is_summary = task.find('ns:Summary', ns_dict)
        cost = task.find('ns:Cost', ns_dict)
        fixed_cost = task.find('ns:FixedCost', ns_dict)
        
        if is_summary is not None and is_summary.text == '1':
            if cost is not None and fixed_cost is not None:
                name = task.find('ns:Name', ns_dict).text
                print(f"   ✓ Summary task '{name}' has Cost=${cost.text}, FixedCost=${fixed_cost.text}")
                summary_tasks_with_cost += 1
        elif is_summary is not None and is_summary.text == '0':
            if cost is not None:
                leaf_tasks_with_cost += 1
    
    print(f"   Found {summary_tasks_with_cost} summary tasks with cost aggregation")
    print(f"   Found {leaf_tasks_with_cost} leaf tasks with costs")
    
    # 3. Verify Category elements
    print("\n3. SERVICE CATEGORY MAPPING:")
    tasks_with_category = 0
    category_values = set()
    
    for task in tasks:
        category = task.find('ns:Category', ns_dict)
        if category is not None:
            tasks_with_category += 1
            category_values.add(category.text)
    
    print(f"   ✓ Found {tasks_with_category} tasks with Category elements")
    print(f"   Category values: {sorted(category_values)}")
    
    # 4. Verify PredecessorLink elements
    print("\n4. DEPENDENCY/PREDECESSOR LINKS:")
    tasks_with_dependencies = 0
    total_dependencies = 0
    
    for task in tasks:
        pred_links = task.findall('ns:PredecessorLink', ns_dict)
        if pred_links:
            task_name = task.find('ns:Name', ns_dict).text
            tasks_with_dependencies += 1
            for pred_link in pred_links:
                pred_uid = pred_link.find('ns:PredecessorUID', ns_dict).text
                link_type = pred_link.find('ns:Type', ns_dict).text
                total_dependencies += 1
                print(f"   ✓ Task '{task_name}' depends on UID {pred_uid} (Type: {link_type})")
    
    print(f"   Found {tasks_with_dependencies} tasks with dependencies ({total_dependencies} total links)")
    
    # Summary
    print("\n=== SUMMARY ===")
    success = revenue_def_found and summary_tasks_with_cost > 0 and tasks_with_category > 0 and total_dependencies > 0
    if success:
        print("✓ All three features are working correctly!")
    else:
        print("✗ Some features may not be working as expected")
    
    return success

def main():
    print("Creating test data...")
    df = create_test_data()
    
    # Save to Excel for testing with correct sheet name
    test_xlsx = "test_new_features.xlsx"
    with pd.ExcelWriter(test_xlsx, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Scenario A', index=False)
    print(f"Saved test data to {test_xlsx} with sheet 'Scenario A'")
    
    # Convert to MSPDI XML
    test_xml = "test_new_features.xml"
    print(f"\nConverting to MSPDI XML...")
    
    stats = convert_excel_to_mspdi(
        input_xlsx=test_xlsx,
        output_xml=test_xml,
        project_name="New Features Test Project",
        add_deliverable_milestones=False,
        add_phase_gates=False,
        add_dependencies=True,
        add_custom_fields=True
    )
    
    print(f"\nConversion stats: {stats}")
    
    # Verify the XML has all features
    if os.path.exists(test_xml):
        success = verify_xml_features(test_xml)
        
        if success:
            print("\n✓ TEST PASSED: All features implemented correctly!")
            return 0
        else:
            print("\n✗ TEST FAILED: Some features missing or incorrect")
            return 1
    else:
        print(f"\n✗ ERROR: Output XML file not created")
        return 1

if __name__ == "__main__":
    exit(main())
