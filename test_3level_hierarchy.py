#!/usr/bin/env python3
"""
Test script to verify 3-level hierarchy implementation in convert_excel_to_mspdi.py
"""

import pandas as pd
import xml.etree.ElementTree as ET
from convert_excel_to_mspdi import convert_excel_to_mspdi
import os
import tempfile

def create_test_excel():
    """Create a test Excel file with 3-level structure"""
    data = {
        "Deliverable": ["Website Redesign", "Website Redesign", "Website Redesign", 
                       "Website Redesign", "Marketing Campaign", "Marketing Campaign"],
        "Deliverable_Code": ["DEL-001", "DEL-001", "DEL-001", "DEL-001", "DEL-002", "DEL-002"],
        "Component": ["UX Design", "UX Design", "Development", "Development", 
                     "Content Creation", "Ad Campaign"],
        "Task_Name": ["Create Wireframes", "Design Mockups", "Frontend Coding", 
                     "Backend API", "Write Blog Posts", "Launch Ads"],
        "Planned_Hours": [16, 24, 40, 32, 20, 15],
        "Department": ["Creative", "Creative", "Technology", "Technology", "Content", "Paid Media"],
        "Rate_USD": [150, 150, 175, 175, 125, 140],
        "Price_USD": [2400, 3600, 7000, 5600, 2500, 2100]
    }
    
    df = pd.DataFrame(data)
    
    # Create temp file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.xlsx', delete=False)
    temp_file.close()
    
    # Write to Excel
    with pd.ExcelWriter(temp_file.name, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Scenario A', index=False)
    
    return temp_file.name


def verify_xml_structure(xml_file):
    """Verify the XML has proper 3-level hierarchy"""
    
    print("\n" + "="*80)
    print("VERIFYING 3-LEVEL HIERARCHY IMPLEMENTATION")
    print("="*80)
    
    # Parse XML
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # Define namespace
    ns = {"ns": "http://schemas.microsoft.com/project"}
    
    # Find all tasks
    tasks = root.findall(".//ns:Task", ns)
    
    print(f"\n✓ Total tasks found: {len(tasks)}")
    
    # Analyze hierarchy
    level_counts = {0: 0, 1: 0, 2: 0, 3: 0}
    wbs_examples = {0: [], 1: [], 2: [], 3: []}
    
    for task in tasks:
        uid_elem = task.find("ns:UID", ns)
        name_elem = task.find("ns:Name", ns)
        outline_elem = task.find("ns:OutlineLevel", ns)
        wbs_elem = task.find("ns:WBS", ns)
        summary_elem = task.find("ns:Summary", ns)
        
        if outline_elem is not None:
            level = int(outline_elem.text)
            level_counts[level] = level_counts.get(level, 0) + 1
            
            # Collect examples
            if len(wbs_examples[level]) < 3:  # Keep first 3 examples
                wbs_examples[level].append({
                    "name": name_elem.text if name_elem is not None else "N/A",
                    "wbs": wbs_elem.text if wbs_elem is not None else "N/A",
                    "summary": summary_elem.text if summary_elem is not None else "0"
                })
    
    print("\n" + "-"*80)
    print("HIERARCHY BREAKDOWN:")
    print("-"*80)
    
    # Level 0 (Project)
    print(f"\nLevel 0 (Project): {level_counts[0]} task(s)")
    for ex in wbs_examples[0]:
        print(f"  • {ex['name'][:50]:50s} | WBS: {ex['wbs']:10s} | Summary: {ex['summary']}")
    
    # Level 1 (Deliverables)
    print(f"\nLevel 1 (Deliverables): {level_counts[1]} task(s)")
    for ex in wbs_examples[1]:
        print(f"  • {ex['name'][:50]:50s} | WBS: {ex['wbs']:10s} | Summary: {ex['summary']}")
    
    # Level 2 (Components)
    print(f"\nLevel 2 (Components): {level_counts[2]} task(s)")
    for ex in wbs_examples[2]:
        print(f"  • {ex['name'][:50]:50s} | WBS: {ex['wbs']:10s} | Summary: {ex['summary']}")
    
    # Level 3 (Tasks)
    print(f"\nLevel 3 (Tasks): {level_counts[3]} task(s)")
    for ex in wbs_examples[3]:
        print(f"  • {ex['name'][:50]:50s} | WBS: {ex['wbs']:10s} | Summary: {ex['summary']}")
    
    # Verification
    print("\n" + "="*80)
    print("VERIFICATION RESULTS:")
    print("="*80)
    
    checks = []
    
    # Check 1: Has Level 1 (Deliverables)
    if level_counts[1] >= 1:
        checks.append(("✓", "Deliverable tasks (Level 1) found"))
    else:
        checks.append(("✗", "NO Deliverable tasks (Level 1) found"))
    
    # Check 2: Has Level 2 (Components)
    if level_counts[2] >= 2:
        checks.append(("✓", "Component tasks (Level 2) found"))
    else:
        checks.append(("✗", "NO Component tasks (Level 2) found"))
    
    # Check 3: Has Level 3 (Tasks)
    if level_counts[3] >= 4:
        checks.append(("✓", "Individual tasks (Level 3) found"))
    else:
        checks.append(("✗", "NO Individual tasks (Level 3) found"))
    
    # Check 4: WBS format for Level 3
    level3_wbs_ok = all('.' in ex['wbs'] and ex['wbs'].count('.') >= 2 
                        for ex in wbs_examples[3] if ex['wbs'] != "N/A")
    if level3_wbs_ok and wbs_examples[3]:
        checks.append(("✓", "Level 3 WBS format correct (1.2.3)"))
    else:
        checks.append(("✗", "Level 3 WBS format incorrect"))
    
    # Check 5: Component summary flag
    comp_summary_ok = all(ex['summary'] == '1' for ex in wbs_examples[2])
    if comp_summary_ok and wbs_examples[2]:
        checks.append(("✓", "Component tasks marked as Summary"))
    else:
        checks.append(("✗", "Component tasks NOT marked as Summary"))
    
    # Check 6: Task summary flag
    task_summary_ok = all(ex['summary'] == '0' for ex in wbs_examples[3])
    if task_summary_ok and wbs_examples[3]:
        checks.append(("✓", "Individual tasks NOT marked as Summary"))
    else:
        checks.append(("✗", "Individual tasks incorrectly marked as Summary"))
    
    # Print results
    print()
    for symbol, msg in checks:
        print(f"{symbol} {msg}")
    
    # Overall result
    all_passed = all(symbol == "✓" for symbol, _ in checks)
    
    print("\n" + "="*80)
    if all_passed:
        print("✓✓✓ ALL CHECKS PASSED - 3-LEVEL HIERARCHY SUCCESSFULLY IMPLEMENTED ✓✓✓")
    else:
        print("✗✗✗ SOME CHECKS FAILED - REVIEW IMPLEMENTATION ✗✗✗")
    print("="*80 + "\n")
    
    return all_passed


def main():
    """Run the test"""
    
    print("\nCreating test Excel file...")
    excel_file = create_test_excel()
    print(f"✓ Created: {excel_file}")
    
    print("\nGenerating XML with 3-level hierarchy...")
    xml_file = excel_file.replace('.xlsx', '.xml')
    
    try:
        result = convert_excel_to_mspdi(
            input_xlsx=excel_file,
            output_xml=xml_file,
            sheet_name="Scenario A",
            project_name="Test 3-Level Hierarchy",
            add_deliverable_milestones=True,
            add_phase_gates=False,
            add_dependencies=False,  # Disable dependencies for clarity
            add_custom_fields=True
        )
        
        print(f"✓ Generated: {xml_file}")
        print(f"  Task count: {result.get('task_count', 'N/A')}")
        
        # Verify structure
        success = verify_xml_structure(xml_file)
        
        # Cleanup
        print("\nCleaning up test files...")
        if os.path.exists(excel_file):
            os.remove(excel_file)
            print(f"✓ Removed: {excel_file}")
        
        # Keep XML for inspection
        print(f"\n✓ XML file kept for inspection: {xml_file}")
        print("  You can import this into MS Project or Workfront to verify the hierarchy.")
        
        return success
        
    except Exception as e:
        print(f"\n✗ Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
