#!/usr/bin/env python3
"""
Test script for the enhanced XML export with professional PM features
"""

import os
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from convert_excel_to_mspdi import convert_excel_to_mspdi

def create_test_data():
    """Create sample project data for testing"""
    data = {
        'Deliverable': [
            'Strategic Planning', 'Strategic Planning', 'Strategic Planning',
            'Creative Development', 'Creative Development', 'Creative Development',
            'Technical Implementation', 'Technical Implementation', 'Technical Implementation',
            'Quality Assurance', 'Quality Assurance', 'Quality Assurance'
        ],
        'Deliverable_Code': [
            'SP001', 'SP001', 'SP001',
            'CD002', 'CD002', 'CD002',
            'TI003', 'TI003', 'TI003',
            'QA004', 'QA004', 'QA004'
        ],
        'Component': [
            'Market Research', 'Competitive Analysis', 'Strategy Document',
            'Concept Design', 'Visual Assets', 'Brand Guidelines',
            'Backend Development', 'Frontend Development', 'API Integration',
            'Unit Testing', 'Integration Testing', 'UAT'
        ],
        'Task_Name': [
            'Conduct market research', 'Analyze competitors', 'Write strategy document',
            'Create initial concepts', 'Develop visual assets', 'Define brand guidelines',
            'Build backend services', 'Develop frontend UI', 'Integrate APIs',
            'Execute unit tests', 'Run integration tests', 'User acceptance testing'
        ],
        'Department': [
            'Strategy', 'Strategy', 'Strategy',
            'Creative', 'Creative', 'Creative',
            'Technology', 'Technology', 'Technology',
            'Quality Assurance', 'Quality Assurance', 'Quality Assurance'
        ],
        'Role': [
            'Senior Strategist', 'Business Analyst', 'Strategy Director',
            'Art Director', 'Graphic Designer', 'Brand Manager',
            'Backend Developer', 'Frontend Developer', 'Integration Specialist',
            'QA Lead', 'Test Engineer', 'UAT Coordinator'
        ],
        'Planned_Hours': [
            40, 32, 24,
            48, 80, 16,
            120, 100, 60,
            40, 48, 32
        ],
        'Rate_USD': [
            200, 150, 250,
            180, 120, 160,
            175, 165, 170,
            140, 120, 130
        ],
        'Price_USD': [
            8000, 4800, 6000,
            8640, 9600, 2560,
            21000, 16500, 10200,
            5600, 5760, 4160
        ]
    }
    
    df = pd.DataFrame(data)
    return df

def verify_xml_features(xml_file):
    """Verify that all enhanced features are present in the XML"""
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # Namespace for MS Project
    ns = {'ms': 'http://schemas.microsoft.com/project'}
    
    print("\n" + "="*60)
    print("VERIFYING ENHANCED XML FEATURES")
    print("="*60)
    
    results = {}
    
    # 1. Check for WBS Structure
    print("\n1. WBS STRUCTURE:")
    tasks = root.findall('.//ms:Task', ns)
    has_wbs = False
    has_outline = False
    for task in tasks[:5]:  # Check first 5 tasks
        wbs = task.find('ms:WBS', ns)
        outline_num = task.find('ms:OutlineNumber', ns)
        outline_lvl = task.find('ms:OutlineLevel', ns)
        if wbs is not None:
            has_wbs = True
        if outline_num is not None and outline_lvl is not None:
            has_outline = True
            name = task.find('ms:Name', ns).text if task.find('ms:Name', ns) is not None else "Unknown"
            print(f"   Task: {name[:30]:<30} WBS: {wbs.text if wbs else 'N/A':<10} Level: {outline_lvl.text if outline_lvl else 'N/A'}")
    results['wbs_structure'] = has_wbs and has_outline
    print(f"   ✓ WBS Structure Present: {results['wbs_structure']}")
    
    # 2. Check for Dependencies & Predecessors
    print("\n2. DEPENDENCIES & PREDECESSORS:")
    predecessor_links = root.findall('.//ms:PredecessorLink', ns)
    has_dependencies = len(predecessor_links) > 0
    if has_dependencies:
        print(f"   Found {len(predecessor_links)} predecessor links")
        for link in predecessor_links[:3]:  # Show first 3
            pred_uid = link.find('ms:PredecessorUID', ns)
            dep_type = link.find('ms:Type', ns)
            lag = link.find('ms:LinkLag', ns)
            print(f"   - Predecessor UID: {pred_uid.text if pred_uid is not None else 'N/A'}, Type: {dep_type.text if dep_type is not None else 'N/A'}, Lag: {lag.text if lag is not None else '0'}")
    results['dependencies'] = has_dependencies
    print(f"   ✓ Dependencies Present: {results['dependencies']}")
    
    # 3. Check for Resource Assignments
    print("\n3. RESOURCE ASSIGNMENTS:")
    resources = root.findall('.//ms:Resource', ns)
    assignments = root.findall('.//ms:Assignment', ns)
    print(f"   Found {len(resources)} resources")
    print(f"   Found {len(assignments)} assignments")
    
    has_detailed_assignments = False
    for assign in assignments[:3]:  # Check first 3 assignments
        units = assign.find('ms:Units', ns)
        work = assign.find('ms:Work', ns)
        regular_work = assign.find('ms:RegularWork', ns)
        if units is not None and work is not None:
            has_detailed_assignments = True
            print(f"   - Assignment: Units: {units.text if units else 'N/A'}, Work: {work.text if work else 'N/A'}, RegularWork: {regular_work.text if regular_work else 'N/A'}")
    results['resource_assignments'] = has_detailed_assignments
    print(f"   ✓ Detailed Assignments: {results['resource_assignments']}")
    
    # 4. Check for Milestones
    print("\n4. MILESTONES & PHASES:")
    milestones = []
    phase_gates = []
    for task in tasks:
        milestone_elem = task.find('ms:Milestone', ns)
        if milestone_elem is not None and milestone_elem.text == '1':
            name = task.find('ms:Name', ns).text if task.find('ms:Name', ns) is not None else "Unknown"
            milestones.append(name)
            if 'Phase' in name or '25%' in name or '50%' in name or '75%' in name:
                phase_gates.append(name)
    
    print(f"   Found {len(milestones)} milestones:")
    for ms in milestones[:5]:
        print(f"   - {ms}")
    results['milestones'] = len(milestones) > 0
    results['phase_gates'] = len(phase_gates) > 0
    print(f"   ✓ Milestones Present: {results['milestones']}")
    print(f"   ✓ Phase Gates Present: {results['phase_gates']}")
    
    # 5. Check for Custom Fields (ExtendedAttributes)
    print("\n5. CUSTOM FIELDS (ExtendedAttributes):")
    ext_attrs_def = root.findall('.//ms:ExtendedAttribute', ns)
    print(f"   Found {len(ext_attrs_def)} extended attribute definitions")
    
    # Check for custom fields in tasks
    tasks_with_custom_fields = 0
    for task in tasks:
        task_ext_attrs = task.findall('ms:ExtendedAttribute', ns)
        if len(task_ext_attrs) > 0:
            tasks_with_custom_fields += 1
    
    print(f"   Tasks with custom fields: {tasks_with_custom_fields}")
    results['custom_fields'] = len(ext_attrs_def) > 0 and tasks_with_custom_fields > 0
    print(f"   ✓ Custom Fields Present: {results['custom_fields']}")
    
    # 6. Check for Calendar
    print("\n6. CALENDARS & CONSTRAINTS:")
    calendars = root.findall('.//ms:Calendar', ns)
    print(f"   Found {len(calendars)} calendar(s)")
    
    if calendars:
        cal = calendars[0]
        weekdays = cal.findall('.//ms:WeekDay', ns)
        print(f"   Calendar has {len(weekdays)} weekday definitions")
    
    # Check for constraints
    constraints_found = 0
    for task in tasks:
        constraint_type = task.find('ms:ConstraintType', ns)
        if constraint_type is not None and constraint_type.text != '0':  # Not "As Soon As Possible"
            constraints_found += 1
    
    print(f"   Tasks with constraints: {constraints_found}")
    results['calendars'] = len(calendars) > 0
    print(f"   ✓ Calendars Present: {results['calendars']}")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY:")
    print("="*60)
    all_features_present = all(results.values())
    
    for feature, present in results.items():
        status = "✅" if present else "❌"
        print(f"{status} {feature.replace('_', ' ').title()}: {'PASS' if present else 'FAIL'}")
    
    print("\n" + "="*60)
    if all_features_present:
        print("✅ ALL ENHANCED FEATURES VERIFIED SUCCESSFULLY!")
    else:
        print("⚠️ Some features are missing. Please review the implementation.")
    print("="*60)
    
    return all_features_present

def main():
    """Main test function"""
    print("Starting Enhanced XML Export Test...")
    
    # Create test data
    print("\n1. Creating test data...")
    df = create_test_data()
    
    # Save to Excel
    test_excel = "test_enhanced_project.xlsx"
    print(f"2. Saving test data to {test_excel}...")
    df.to_excel(test_excel, sheet_name="Scenario A", index=False)
    
    # Convert to XML with all enhancements
    test_xml = "test_enhanced_output.xml"
    print(f"\n3. Converting to enhanced XML format...")
    
    stats = convert_excel_to_mspdi(
        input_xlsx=test_excel,
        output_xml=test_xml,
        sheet_name="Scenario A",
        project_name="Enhanced Test Project",
        add_deliverable_milestones=True,
        add_phase_gates=True,
        add_dependencies=True,
        add_custom_fields=True,
        hours_per_day=8.0
    )
    
    print("\n4. Conversion Statistics:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Verify the XML contains all features
    if os.path.exists(test_xml):
        print(f"\n5. Verifying XML features in {test_xml}...")
        success = verify_xml_features(test_xml)
        
        if success:
            print(f"\n✅ SUCCESS: Enhanced XML file '{test_xml}' is ready for import to MS Project/Workfront!")
            print("The file contains all professional PM features including:")
            print("  • Hierarchical WBS structure with proper numbering")
            print("  • Task dependencies and predecessor links")
            print("  • Resource assignments with work allocation")
            print("  • Milestones and phase gates")
            print("  • Custom fields for Workfront integration")
            print("  • Calendar and constraint definitions")
        else:
            print(f"\n⚠️ WARNING: Some features may be missing in '{test_xml}'")
    else:
        print(f"\n❌ ERROR: Output file '{test_xml}' was not created")
    
    # Clean up test files (optional)
    # os.remove(test_excel)
    # os.remove(test_xml)

if __name__ == "__main__":
    main()