#!/usr/bin/env python3
"""
Generate a fresh St. Regis XML export using the current code and verify it matches the golden reference.
"""

import sys
import os
import xml.etree.ElementTree as ET
from convert_excel_to_mspdi import convert_excel_to_mspdi

# Input Excel file
ST_REGIS_EXCEL = "St.Regis_Nashville_Branding_Agency_RFP_10.22.2024_Workfront_Export_FINAL_SHIP_2025-11-05_06-21PM_EST.xlsx"

# Output XML file
OUTPUT_XML = "St_Regis_TEST_EXPORT_FRESH.xml"

# Golden reference (Nov 7 9:10 AM - 774 tasks)
GOLDEN_REFERENCE = "attached_assets/St.Regis_Nashville_Branding_Agency_RFP_10.22.2024_Workfront_Export_Scenario_A_2025-11-07_09-10AM_EST_1762949605846.xml"

def count_tasks_milestones_and_uncategorized(xml_path):
    """Count tasks, milestones, and uncategorized tasks in XML"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        ns = {"ns": "http://schemas.microsoft.com/project"}
        
        tasks = root.findall(".//ns:Task", ns)
        milestone_count = 0
        uncategorized_count = 0
        tasks_with_hours = 0
        tasks_with_predecessors = 0
        
        milestone_names = []
        
        for task in tasks:
            # Count milestones
            milestone_elem = task.find("ns:Milestone", ns)
            if milestone_elem is not None and milestone_elem.text == "1":
                milestone_count += 1
                name_elem = task.find("ns:Name", ns)
                if name_elem is not None:
                    milestone_names.append(name_elem.text)
            
            # Count uncategorized
            name_elem = task.find("ns:Name", ns)
            if name_elem is not None and "Uncategorized" in name_elem.text:
                uncategorized_count += 1
            
            # Count tasks with hours
            work_elem = task.find("ns:Work", ns)
            if work_elem is not None and work_elem.text and work_elem.text != "PT0H0M0S":
                tasks_with_hours += 1
            
            # Count tasks with predecessors
            pred_link = task.find("ns:PredecessorLink", ns)
            if pred_link is not None:
                tasks_with_predecessors += 1
        
        return {
            "total_tasks": len(tasks),
            "milestones": milestone_count,
            "milestone_names": milestone_names,
            "uncategorized": uncategorized_count,
            "tasks_with_hours": tasks_with_hours,
            "tasks_with_predecessors": tasks_with_predecessors
        }
    except Exception as e:
        print(f"Error parsing {xml_path}: {e}")
        return None

def main():
    print("=" * 80)
    print("FRESH ST. REGIS EXPORT GENERATION TEST")
    print("=" * 80)
    
    # Check if Excel file exists
    if not os.path.exists(ST_REGIS_EXCEL):
        print(f"\n❌ ERROR: Excel file not found: {ST_REGIS_EXCEL}")
        return 1
    
    print(f"\n[1] Generating fresh export from Excel...")
    print(f"   Input:  {ST_REGIS_EXCEL}")
    print(f"   Output: {OUTPUT_XML}")
    
    # Generate the XML export using convert_excel_to_mspdi
    try:
        stats = convert_excel_to_mspdi(
            input_xlsx=ST_REGIS_EXCEL,
            output_xml=OUTPUT_XML,
            sheet_name="Scenario A - Final",
            start_date_mode="next_monday",
            fixed_start_iso=None,
            hours_per_day=6.5,
            merge_identical_children=False,
            project_name="St. Regis Nashville Branding Agency RFP",
            pricing_mode="Flat_Blended",
            rate_band="Standard_US",
            blended_rate=195.0,
            add_dependencies=True,
            add_custom_fields=True
        )
        
        print(f"\n   ✓ Export generated successfully!")
        print(f"   ✓ Conversion stats: {stats}")
        
    except Exception as e:
        print(f"\n   ❌ ERROR during export generation: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Analyze the fresh export
    print(f"\n[2] Analyzing FRESH EXPORT...")
    fresh_stats = count_tasks_milestones_and_uncategorized(OUTPUT_XML)
    
    if fresh_stats:
        print(f"   ✓ Total tasks: {fresh_stats['total_tasks']}")
        print(f"   ✓ Milestones: {fresh_stats['milestones']}")
        if fresh_stats['milestone_names']:
            print(f"   ✓ Milestone names: {fresh_stats['milestone_names'][:10]}...")
        print(f"   ✓ Uncategorized tasks: {fresh_stats['uncategorized']}")
        print(f"   ✓ Tasks with hours: {fresh_stats['tasks_with_hours']}")
        print(f"   ✓ Tasks with predecessors: {fresh_stats['tasks_with_predecessors']}")
    else:
        print(f"   ❌ Failed to analyze fresh export")
        return 1
    
    # Analyze the golden reference
    print(f"\n[3] Analyzing GOLDEN REFERENCE...")
    golden_stats = count_tasks_milestones_and_uncategorized(GOLDEN_REFERENCE)
    
    if golden_stats:
        print(f"   ✓ Total tasks: {golden_stats['total_tasks']}")
        print(f"   ✓ Milestones: {golden_stats['milestones']}")
        if golden_stats['milestone_names']:
            print(f"   ✓ Milestone names: {golden_stats['milestone_names'][:10]}...")
        print(f"   ✓ Uncategorized tasks: {golden_stats['uncategorized']}")
        print(f"   ✓ Tasks with hours: {golden_stats['tasks_with_hours']}")
        print(f"   ✓ Tasks with predecessors: {golden_stats['tasks_with_predecessors']}")
    else:
        print(f"   ⚠️  Golden reference not available for comparison")
    
    # Verification
    print("\n" + "=" * 80)
    print("VERIFICATION RESULTS")
    print("=" * 80)
    
    all_passed = True
    
    # Check task count
    if fresh_stats['total_tasks'] == 774:
        print(f"\n✅ PASS: Task count matches golden reference (774)")
    else:
        print(f"\n❌ FAIL: Expected 774 tasks, got {fresh_stats['total_tasks']}")
        if golden_stats:
            print(f"   Golden reference has {golden_stats['total_tasks']} tasks")
        all_passed = False
    
    # Check milestone count
    if fresh_stats['milestones'] == 0:
        print(f"✅ PASS: No milestones in fresh export")
    else:
        print(f"❌ FAIL: Found {fresh_stats['milestones']} milestones (expected 0)")
        print(f"   Milestone names: {fresh_stats['milestone_names']}")
        all_passed = False
    
    # Check hours
    if fresh_stats['tasks_with_hours'] > 0:
        print(f"✅ PASS: Tasks have work hours ({fresh_stats['tasks_with_hours']} tasks)")
    else:
        print(f"❌ FAIL: No tasks have work hours")
        all_passed = False
    
    # Check predecessors
    if fresh_stats['tasks_with_predecessors'] > 0:
        print(f"✅ PASS: Tasks have dependencies ({fresh_stats['tasks_with_predecessors']} tasks)")
    else:
        print(f"⚠️  WARNING: No tasks have dependencies")
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL TESTS PASSED - Export is valid!")
    else:
        print("❌ SOME TESTS FAILED - Review issues above")
    print("=" * 80)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
