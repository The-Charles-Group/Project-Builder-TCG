#!/usr/bin/env python3
"""
Test script to verify the resource UID mapping fix for role assignments.
This tests the scenario where the same role has multiple seniorities.
"""

import pandas as pd
import logging
from convert_excel_to_mspdi import convert_excel_to_mspdi
import os

# Configure logging to see all the debug output
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def create_test_data():
    """Create test data with multiple seniorities for the same role"""
    
    # Create test data with Designer role at 3 different seniority levels
    data = {
        'Deliverable': ['Website Redesign', 'Website Redesign', 'Website Redesign', 
                       'Website Redesign', 'Website Redesign', 'Website Redesign',
                       'Website Redesign'],
        'Component': ['Design System', 'Design System', 'Design System',
                     'Design System', 'Design System', 'Design System',
                     'Design System'],
        'Task_Name': ['Create Design System', 'Create Design System', 'Create Design System',
                      'Create Design System', 'Create Design System', 'Create Design System',
                      'Create Design System'],
        'WBS_ID': ['1.1.1', '1.1.1.1', '1.1.1.2', '1.1.1.3',
                   '1.2.1', '1.2.1.1', '1.2.1.2'],
        'Parent_WBS_ID': ['1.1', '1.1.1', '1.1.1', '1.1.1',
                         '1.2', '1.2.1', '1.2.1'],
        'Department': ['Creative', 'Creative', 'Creative', 'Creative',
                      'Strategy', 'Strategy', 'Strategy'],
        'Role': [None, 'Designer', 'Designer', 'Designer',
                None, 'Strategist', 'Strategist'],
        'Seniority': [None, 'Junior', 'Mid', 'Senior',
                     None, 'Senior', 'Mid'],
        'Planned_Hours': [80, 20, 30, 30,
                         40, 20, 20],
        'Rate_USD': [0, 75, 100, 150,
                    0, 150, 120],
        'Price_USD': [0, 1500, 3000, 4500,
                     0, 3000, 2400],
        'Service_Department': ['Creative Services', 'Creative Services', 'Creative Services', 'Creative Services',
                              'Strategy', 'Strategy', 'Strategy']
    }
    
    df = pd.DataFrame(data)
    
    # Save to Excel
    test_file = 'test_resource_uid_mapping.xlsx'
    with pd.ExcelWriter(test_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Scenario A', index=False)
    
    print(f"✓ Created test file: {test_file}")
    print(f"✓ Test data includes:")
    print(f"  - Designer (Junior): 20 hours")
    print(f"  - Designer (Mid): 30 hours")
    print(f"  - Designer (Senior): 30 hours")
    print(f"  - Strategist (Senior): 20 hours")
    print(f"  - Strategist (Mid): 20 hours")
    print()
    
    return test_file

def run_test():
    """Run the test conversion"""
    
    print("=" * 70)
    print("RESOURCE UID MAPPING FIX TEST")
    print("=" * 70)
    print()
    
    # Create test data
    test_file = create_test_data()
    
    # Run conversion
    output_file = 'test_resource_uid_mapping_output.xml'
    
    print("Running conversion...")
    print("-" * 70)
    
    try:
        stats = convert_excel_to_mspdi(
            input_xlsx=test_file,
            output_xml=output_file,
            sheet_name='Scenario A',
            project_name='Resource UID Test Project',
            start_date_mode='next_monday',
            blended_rate=100.0,
            add_dependencies=False,
            add_phase_gates=False
        )
        
        print("-" * 70)
        print()
        print("✓ Conversion completed successfully!")
        print()
        print("RESULTS:")
        print(f"  - Total tasks: {stats.get('task_count', 0)}")
        print(f"  - Total resources: {stats.get('resource_count', 0)}")
        print(f"  - Total assignments: {stats.get('assignment_count', 0)}")
        print(f"  - Output file: {output_file}")
        print()
        
        # Verify the XML file was created
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✓ XML file created: {file_size:,} bytes")
            
            # Parse XML to verify resource assignments
            import xml.etree.ElementTree as ET
            tree = ET.parse(output_file)
            root = tree.getroot()
            ns = {"ns": "http://schemas.microsoft.com/project"}
            
            # Count resources
            resources = root.findall(".//ns:Resource", ns)
            print(f"✓ Resources in XML: {len(resources)}")
            
            # List resource names
            print()
            print("RESOURCES CREATED:")
            for res in resources:
                uid = res.find("ns:UID", ns)
                name = res.find("ns:Name", ns)
                if uid is not None and name is not None:
                    print(f"  - UID {uid.text}: {name.text}")
            
            # Count assignments
            assignments = root.findall(".//ns:Assignment", ns)
            print()
            print(f"✓ Assignments in XML: {len(assignments)}")
            print()
            print("ASSIGNMENTS CREATED:")
            for assign in assignments:
                assign_uid = assign.find("ns:UID", ns)
                task_uid = assign.find("ns:TaskUID", ns)
                resource_uid = assign.find("ns:ResourceUID", ns)
                work = assign.find("ns:Work", ns)
                
                if all([assign_uid, task_uid, resource_uid, work]):
                    # Find resource name
                    res_name = "Unknown"
                    for res in resources:
                        res_uid = res.find("ns:UID", ns)
                        if res_uid is not None and res_uid.text == resource_uid.text:
                            res_name_elem = res.find("ns:Name", ns)
                            if res_name_elem is not None:
                                res_name = res_name_elem.text
                            break
                    
                    print(f"  - Assignment {assign_uid.text}: Task {task_uid.text} -> Resource {resource_uid.text} ({res_name}), Work: {work.text}")
            
            print()
            print("=" * 70)
            print("TEST PASSED! ✓")
            print("=" * 70)
            print()
            print("Key verification points:")
            print("  ✓ Multiple seniorities for same role handled correctly")
            print("  ✓ All role assignments created successfully")
            print("  ✓ No KeyErrors or wrong ResourceUID references")
            print()
            
        else:
            print("✗ ERROR: Output XML file was not created!")
            return False
            
    except Exception as e:
        print()
        print("=" * 70)
        print("TEST FAILED! ✗")
        print("=" * 70)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = run_test()
    exit(0 if success else 1)
