#!/usr/bin/env python3
"""
Sanity Test: Minimal MSPDI XML with Predecessors

This script generates a minimal Microsoft Project XML file with:
- 2 tasks: Task A (6 working days) and Task B (2 working days)
- Finish-to-Start (FS) predecessor relationship (Task B starts after Task A)
- Business calendar with Mon-Fri working days, Sat-Sun off
- Expected outcome: Task B should start Dec 9 09:00 (next working day after Task A Dec 8 18:00)

Usage:
    python scripts/test_predecessor_sanity.py
    
Output:
    scripts/sanity_test_output.xml
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime


def create_minimal_mspdi_with_predecessors():
    """Create minimal MSPDI XML with 2 tasks and predecessor relationship"""
    
    # Define namespace
    ns = "http://schemas.microsoft.com/project"
    ET.register_namespace('', ns)
    
    # Create root Project element
    root = ET.Element(f"{{{ns}}}Project")
    
    # Basic project info
    ET.SubElement(root, f"{{{ns}}}Name").text = "Predecessor Sanity Test"
    ET.SubElement(root, f"{{{ns}}}Title").text = "2-Task Predecessor Test"
    ET.SubElement(root, f"{{{ns}}}ScheduleFromStart").text = "1"
    ET.SubElement(root, f"{{{ns}}}StartDate").text = "2025-12-01T09:00:00"
    ET.SubElement(root, f"{{{ns}}}FinishDate").text = "2025-12-10T18:00:00"
    ET.SubElement(root, f"{{{ns}}}CurrentDate").text = datetime.now().isoformat()
    
    # Add default calendar (Mon-Fri working, Sat-Sun off)
    calendars_elem = ET.SubElement(root, f"{{{ns}}}Calendars")
    cal = ET.SubElement(calendars_elem, f"{{{ns}}}Calendar")
    ET.SubElement(cal, f"{{{ns}}}UID").text = "1"
    ET.SubElement(cal, f"{{{ns}}}Name").text = "Standard"
    ET.SubElement(cal, f"{{{ns}}}IsBaseCalendar").text = "1"
    
    # Define weekdays (Mon-Fri working, Sat-Sun off)
    weekdays_elem = ET.SubElement(cal, f"{{{ns}}}WeekDays")
    
    # Sunday (DayType=1) - OFF
    sun = ET.SubElement(weekdays_elem, f"{{{ns}}}WeekDay")
    ET.SubElement(sun, f"{{{ns}}}DayType").text = "1"
    ET.SubElement(sun, f"{{{ns}}}DayWorking").text = "0"
    
    # Monday-Friday (DayType=2-6) - WORKING 9-12, 13-18
    for day_type in range(2, 7):
        day = ET.SubElement(weekdays_elem, f"{{{ns}}}WeekDay")
        ET.SubElement(day, f"{{{ns}}}DayType").text = str(day_type)
        ET.SubElement(day, f"{{{ns}}}DayWorking").text = "1"
        
        # Working times
        times_elem = ET.SubElement(day, f"{{{ns}}}WorkingTimes")
        
        # Morning: 09:00-12:00
        morning = ET.SubElement(times_elem, f"{{{ns}}}WorkingTime")
        ET.SubElement(morning, f"{{{ns}}}FromTime").text = "09:00:00"
        ET.SubElement(morning, f"{{{ns}}}ToTime").text = "12:00:00"
        
        # Afternoon: 13:00-18:00
        afternoon = ET.SubElement(times_elem, f"{{{ns}}}WorkingTime")
        ET.SubElement(afternoon, f"{{{ns}}}FromTime").text = "13:00:00"
        ET.SubElement(afternoon, f"{{{ns}}}ToTime").text = "18:00:00"
    
    # Saturday (DayType=7) - OFF
    sat = ET.SubElement(weekdays_elem, f"{{{ns}}}WeekDay")
    ET.SubElement(sat, f"{{{ns}}}DayType").text = "7"
    ET.SubElement(sat, f"{{{ns}}}DayWorking").text = "0"
    
    # Add tasks
    tasks_elem = ET.SubElement(root, f"{{{ns}}}Tasks")
    
    # Task A: Dec 1-8, 2025 (6 working days, 2880 minutes)
    task_a = ET.SubElement(tasks_elem, f"{{{ns}}}Task")
    ET.SubElement(task_a, f"{{{ns}}}UID").text = "1"
    ET.SubElement(task_a, f"{{{ns}}}ID").text = "1"
    ET.SubElement(task_a, f"{{{ns}}}Name").text = "Task A - 6 Working Days"
    ET.SubElement(task_a, f"{{{ns}}}Type").text = "1"  # Fixed Duration
    ET.SubElement(task_a, f"{{{ns}}}IsNull").text = "0"
    ET.SubElement(task_a, f"{{{ns}}}CreateDate").text = datetime.now().isoformat()
    ET.SubElement(task_a, f"{{{ns}}}WBS").text = "1"
    ET.SubElement(task_a, f"{{{ns}}}OutlineNumber").text = "1"
    ET.SubElement(task_a, f"{{{ns}}}OutlineLevel").text = "1"
    ET.SubElement(task_a, f"{{{ns}}}Priority").text = "500"
    ET.SubElement(task_a, f"{{{ns}}}Start").text = "2025-12-01T09:00:00"
    ET.SubElement(task_a, f"{{{ns}}}Finish").text = "2025-12-08T18:00:00"
    ET.SubElement(task_a, f"{{{ns}}}Duration").text = "PT2880M"  # 6 days × 480 min
    ET.SubElement(task_a, f"{{{ns}}}DurationFormat").text = "7"  # Minutes
    ET.SubElement(task_a, f"{{{ns}}}Work").text = "PT2880M"
    ET.SubElement(task_a, f"{{{ns}}}ConstraintType").text = "0"  # ASAP
    ET.SubElement(task_a, f"{{{ns}}}Manual").text = "0"  # Auto-scheduled
    
    # Task B: Dec 9-10, 2025 (2 working days, 960 minutes) with FS predecessor
    task_b = ET.SubElement(tasks_elem, f"{{{ns}}}Task")
    ET.SubElement(task_b, f"{{{ns}}}UID").text = "2"
    ET.SubElement(task_b, f"{{{ns}}}ID").text = "2"
    ET.SubElement(task_b, f"{{{ns}}}Name").text = "Task B - 2 Working Days (FS Predecessor)"
    ET.SubElement(task_b, f"{{{ns}}}Type").text = "1"  # Fixed Duration
    ET.SubElement(task_b, f"{{{ns}}}IsNull").text = "0"
    ET.SubElement(task_b, f"{{{ns}}}CreateDate").text = datetime.now().isoformat()
    ET.SubElement(task_b, f"{{{ns}}}WBS").text = "2"
    ET.SubElement(task_b, f"{{{ns}}}OutlineNumber").text = "2"
    ET.SubElement(task_b, f"{{{ns}}}OutlineLevel").text = "1"
    ET.SubElement(task_b, f"{{{ns}}}Priority").text = "500"
    ET.SubElement(task_b, f"{{{ns}}}Start").text = "2025-12-09T09:00:00"
    ET.SubElement(task_b, f"{{{ns}}}Finish").text = "2025-12-10T18:00:00"
    ET.SubElement(task_b, f"{{{ns}}}Duration").text = "PT960M"  # 2 days × 480 min
    ET.SubElement(task_b, f"{{{ns}}}DurationFormat").text = "7"  # Minutes
    ET.SubElement(task_b, f"{{{ns}}}Work").text = "PT960M"
    ET.SubElement(task_b, f"{{{ns}}}ConstraintType").text = "0"  # ASAP
    ET.SubElement(task_b, f"{{{ns}}}Manual").text = "0"  # Auto-scheduled
    
    # Add FS predecessor (Task B depends on Task A)
    predecessors_elem = ET.SubElement(task_b, f"{{{ns}}}PredecessorLink")
    ET.SubElement(predecessors_elem, f"{{{ns}}}PredecessorUID").text = "1"  # Task A UID
    ET.SubElement(predecessors_elem, f"{{{ns}}}Type").text = "1"  # FS (Finish-to-Start)
    ET.SubElement(predecessors_elem, f"{{{ns}}}CrossProject").text = "0"
    ET.SubElement(predecessors_elem, f"{{{ns}}}LinkLag").text = "0"
    ET.SubElement(predecessors_elem, f"{{{ns}}}LagFormat").text = "7"  # Minutes
    
    # Convert to pretty XML
    xml_str = minidom.parseString(ET.tostring(root, encoding='unicode')).toprettyxml(indent="  ")
    
    # Remove empty lines
    xml_lines = [line for line in xml_str.split('\n') if line.strip()]
    xml_str = '\n'.join(xml_lines)
    
    return xml_str


def main():
    """Generate and save minimal MSPDI XML"""
    print("=" * 60)
    print("Predecessor Sanity Test - Minimal MSPDI XML Generator")
    print("=" * 60)
    print()
    print("Test Configuration:")
    print("  Task A: Dec 1-8, 2025 (6 working days)")
    print("    Start: Monday Dec 1, 09:00")
    print("    Finish: Monday Dec 8, 18:00")
    print("    Duration: PT2880M (6 days × 480 min)")
    print()
    print("  Task B: Dec 9-10, 2025 (2 working days)")
    print("    Start: Tuesday Dec 9, 09:00")
    print("    Finish: Wednesday Dec 10, 18:00")
    print("    Duration: PT960M (2 days × 480 min)")
    print("    Predecessor: Task A (FS - Finish-to-Start)")
    print()
    print("  Calendar: Mon-Fri 09:00-12:00, 13:00-18:00 (Sat-Sun OFF)")
    print()
    print("Expected Result in Workfront:")
    print("  ✓ Task A finishes: Monday Dec 8, 18:00")
    print("  ✓ Task B starts: Tuesday Dec 9, 09:00 (next working day)")
    print("  ✓ NO GAPS between tasks (weekend excluded properly)")
    print()
    
    # Generate XML
    xml_content = create_minimal_mspdi_with_predecessors()
    
    # Save to file
    output_path = "scripts/sanity_test_output.xml"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)
    
    print(f"✅ XML generated successfully: {output_path}")
    print()
    print("Verification Steps:")
    print("  1. Check Saturday configuration:")
    print(f"     grep 'DayType>7' {output_path} -A 1")
    print("     Expected: <DayWorking>0</DayWorking>")
    print()
    print("  2. Check predecessor link:")
    print(f"     grep 'PredecessorLink' {output_path} -A 4")
    print("     Expected: PredecessorUID=1, Type=1 (FS)")
    print()
    print("  3. Import into Workfront and verify:")
    print("     - Task B starts Dec 9 09:00 (immediately after Task A)")
    print("     - No gaps or extra days inserted")
    print("=" * 60)


if __name__ == "__main__":
    main()
