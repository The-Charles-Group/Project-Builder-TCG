#!/usr/bin/env python3
"""
Convert Excel WBS data to Microsoft Project MSPDI XML format
"""

import os
import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any


def convert_excel_to_mspdi(
    input_xlsx: str,
    output_xml: str,
    sheet_name: str = "Scenario A",
    start_date_mode: str = "next_monday",
    fixed_start_iso: Optional[str] = None,
    hours_per_day: float = 8.0,
    merge_identical_children: bool = False,
    project_name: Optional[str] = None,
    pricing_mode: str = "Flat_Blended",
    rate_band: str = "Standard_US",
    blended_rate: Optional[float] = None,
    add_deliverable_milestones: bool = False
) -> Dict[str, Any]:
    """
    Convert an Excel WBS file to Microsoft Project XML (MSPDI) format.
    
    Args:
        input_xlsx: Path to input Excel file
        output_xml: Path to output XML file
        sheet_name: Sheet name to read from Excel
        start_date_mode: "next_monday" or "fixed"
        fixed_start_iso: ISO date string for fixed start date
        hours_per_day: Working hours per day (default 8)
        merge_identical_children: Whether to merge tasks with identical names
        project_name: Name of the project
        pricing_mode: Pricing mode for the project
        rate_band: Rate band for pricing
        blended_rate: Blended rate if using flat pricing
        add_deliverable_milestones: Add milestone tasks for deliverables
        
    Returns:
        Dictionary with conversion statistics
    """
    
    # Read the Excel file
    try:
        df = pd.read_excel(input_xlsx, sheet_name=sheet_name)
    except Exception as e:
        print(f"[MSPDI] Error reading Excel file: {e}")
        return {"error": str(e), "task_count": 0}
    
    if df.empty:
        print(f"[MSPDI] Warning: Empty DataFrame from {input_xlsx}")
        # Create minimal XML with just project header
        root = create_empty_mspdi_xml(project_name or "Empty Project", fixed_start_iso)
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(output_xml, encoding="utf-8", xml_declaration=True)
        return {"task_count": 0, "warning": "Empty input data"}
    
    # Determine project start date
    if fixed_start_iso:
        project_start = datetime.fromisoformat(fixed_start_iso.replace("Z", "+00:00"))
    elif start_date_mode == "next_monday":
        today = datetime.now()
        days_ahead = 0 - today.weekday()  # Monday is 0
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        project_start = today + timedelta(days=days_ahead)
        project_start = project_start.replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        project_start = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Create MSPDI XML structure
    ns = "http://schemas.microsoft.com/project"
    ET.register_namespace("", ns)
    
    root = ET.Element("{%s}Project" % ns)
    
    # Add project properties
    ET.SubElement(root, "{%s}Name" % ns).text = project_name or "Project"
    ET.SubElement(root, "{%s}Title" % ns).text = project_name or "Project"
    ET.SubElement(root, "{%s}StartDate" % ns).text = project_start.isoformat()
    ET.SubElement(root, "{%s}FinishDate" % ns).text = (project_start + timedelta(days=365)).isoformat()
    ET.SubElement(root, "{%s}ScheduleFromStart" % ns).text = "1"
    ET.SubElement(root, "{%s}CurrentDate" % ns).text = datetime.now().isoformat()
    
    # Add currency settings
    ET.SubElement(root, "{%s}CurrencySymbol" % ns).text = "$"
    ET.SubElement(root, "{%s}CurrencyCode" % ns).text = "USD"
    ET.SubElement(root, "{%s}CurrencySymbolPosition" % ns).text = "0"
    
    # Create Resources container
    resources = ET.SubElement(root, "{%s}Resources" % ns)
    
    # Add resources from the DataFrame
    resource_map = {}
    resource_id = 1
    
    # Extract unique roles/resources
    if "Role" in df.columns:
        unique_roles = df["Role"].dropna().unique()
        for role in unique_roles:
            res = ET.SubElement(resources, "{%s}Resource" % ns)
            ET.SubElement(res, "{%s}UID" % ns).text = str(resource_id)
            ET.SubElement(res, "{%s}Name" % ns).text = str(role)
            ET.SubElement(res, "{%s}Type" % ns).text = "1"  # Work resource
            
            # Add rate if available
            if blended_rate:
                ET.SubElement(res, "{%s}StandardRate" % ns).text = f"${blended_rate:.2f}/h"
            elif "Rate_USD" in df.columns:
                role_rate = df[df["Role"] == role]["Rate_USD"].dropna().iloc[0] if not df[df["Role"] == role]["Rate_USD"].dropna().empty else 150
                ET.SubElement(res, "{%s}StandardRate" % ns).text = f"${role_rate:.2f}/h"
            
            resource_map[str(role)] = resource_id
            resource_id += 1
    
    # Create Tasks container
    tasks = ET.SubElement(root, "{%s}Tasks" % ns)
    
    # Add project summary task (Task 0)
    project_task = ET.SubElement(tasks, "{%s}Task" % ns)
    ET.SubElement(project_task, "{%s}UID" % ns).text = "0"
    ET.SubElement(project_task, "{%s}ID" % ns).text = "0"
    ET.SubElement(project_task, "{%s}Name" % ns).text = project_name or "Project"
    ET.SubElement(project_task, "{%s}Type" % ns).text = "1"
    ET.SubElement(project_task, "{%s}IsNull" % ns).text = "0"
    ET.SubElement(project_task, "{%s}CreateDate" % ns).text = datetime.now().isoformat()
    ET.SubElement(project_task, "{%s}WBS" % ns).text = "0"
    ET.SubElement(project_task, "{%s}OutlineLevel" % ns).text = "0"
    ET.SubElement(project_task, "{%s}Priority" % ns).text = "500"
    ET.SubElement(project_task, "{%s}Start" % ns).text = project_start.isoformat()
    ET.SubElement(project_task, "{%s}Duration" % ns).text = "PT0M"
    ET.SubElement(project_task, "{%s}DurationFormat" % ns).text = "53"
    ET.SubElement(project_task, "{%s}Work" % ns).text = "PT0M"
    ET.SubElement(project_task, "{%s}Summary" % ns).text = "1"
    
    # Process WBS tasks
    task_uid = 1
    task_map = {}
    current_date = project_start
    deliverable_ends = {}  # Track end dates for deliverables
    
    # Group by deliverable to create hierarchy
    if "Deliverable" in df.columns:
        grouped = df.groupby("Deliverable", sort=False)
        
        for deliverable_name, group in grouped:
            # Create deliverable summary task
            deliv_task = ET.SubElement(tasks, "{%s}Task" % ns)
            deliv_uid = task_uid
            task_uid += 1
            
            ET.SubElement(deliv_task, "{%s}UID" % ns).text = str(deliv_uid)
            ET.SubElement(deliv_task, "{%s}ID" % ns).text = str(deliv_uid)
            ET.SubElement(deliv_task, "{%s}Name" % ns).text = str(deliverable_name)
            ET.SubElement(deliv_task, "{%s}Type" % ns).text = "1"
            ET.SubElement(deliv_task, "{%s}IsNull" % ns).text = "0"
            ET.SubElement(deliv_task, "{%s}WBS" % ns).text = str(deliv_uid)
            ET.SubElement(deliv_task, "{%s}OutlineLevel" % ns).text = "1"
            ET.SubElement(deliv_task, "{%s}Priority" % ns).text = "500"
            ET.SubElement(deliv_task, "{%s}Start" % ns).text = current_date.isoformat()
            ET.SubElement(deliv_task, "{%s}Summary" % ns).text = "1"
            
            # Process component/task rows under this deliverable
            deliverable_start = current_date
            deliverable_finish = current_date
            
            for idx, row in group.iterrows():
                task = ET.SubElement(tasks, "{%s}Task" % ns)
                uid = task_uid
                task_uid += 1
                
                # Get task details
                task_name = row.get("Task_Name", row.get("Component", f"Task {uid}"))
                hours = float(row.get("Planned_Hours", row.get("Hours", 8)))
                duration_days = max(1, int(np.ceil(hours / hours_per_day)))
                
                # Calculate dates
                task_start = current_date
                task_end = add_business_days(task_start, duration_days)
                
                # Add task elements
                ET.SubElement(task, "{%s}UID" % ns).text = str(uid)
                ET.SubElement(task, "{%s}ID" % ns).text = str(uid)
                ET.SubElement(task, "{%s}Name" % ns).text = str(task_name)
                ET.SubElement(task, "{%s}Type" % ns).text = "0"  # Fixed units
                ET.SubElement(task, "{%s}IsNull" % ns).text = "0"
                ET.SubElement(task, "{%s}WBS" % ns).text = f"{deliv_uid}.{uid - deliv_uid}"
                ET.SubElement(task, "{%s}OutlineLevel" % ns).text = "2"
                ET.SubElement(task, "{%s}Priority" % ns).text = "500"
                ET.SubElement(task, "{%s}Start" % ns).text = task_start.isoformat()
                ET.SubElement(task, "{%s}Finish" % ns).text = task_end.isoformat()
                ET.SubElement(task, "{%s}Duration" % ns).text = f"PT{int(hours * 60)}M"
                ET.SubElement(task, "{%s}DurationFormat" % ns).text = "7"  # Days
                ET.SubElement(task, "{%s}Work" % ns).text = f"PT{int(hours * 60)}M"
                ET.SubElement(task, "{%s}Summary" % ns).text = "0"
                ET.SubElement(task, "{%s}FixedCostAccrual" % ns).text = "2"
                
                # Add cost if available
                if "Price_USD" in row and pd.notna(row["Price_USD"]):
                    ET.SubElement(task, "{%s}Cost" % ns).text = str(float(row["Price_USD"]))
                    ET.SubElement(task, "{%s}FixedCost" % ns).text = str(float(row["Price_USD"]))
                
                # Track deliverable finish date
                if task_end > deliverable_finish:
                    deliverable_finish = task_end
                
                # Update current date for next task
                current_date = task_end
                
                task_map[uid] = task
            
            # Update deliverable summary with calculated duration
            duration_hours = calculate_business_hours(deliverable_start, deliverable_finish)
            ET.SubElement(deliv_task, "{%s}Duration" % ns).text = f"PT{int(duration_hours * 60)}M"
            ET.SubElement(deliv_task, "{%s}Finish" % ns).text = deliverable_finish.isoformat()
            deliverable_ends[deliverable_name] = deliverable_finish
            
            # Add milestone if requested
            if add_deliverable_milestones:
                milestone = ET.SubElement(tasks, "{%s}Task" % ns)
                milestone_uid = task_uid
                task_uid += 1
                
                ET.SubElement(milestone, "{%s}UID" % ns).text = str(milestone_uid)
                ET.SubElement(milestone, "{%s}ID" % ns).text = str(milestone_uid)
                ET.SubElement(milestone, "{%s}Name" % ns).text = f"{deliverable_name} Complete"
                ET.SubElement(milestone, "{%s}Type" % ns).text = "1"
                ET.SubElement(milestone, "{%s}Milestone" % ns).text = "1"
                ET.SubElement(milestone, "{%s}WBS" % ns).text = str(milestone_uid)
                ET.SubElement(milestone, "{%s}OutlineLevel" % ns).text = "1"
                ET.SubElement(milestone, "{%s}Start" % ns).text = deliverable_finish.isoformat()
                ET.SubElement(milestone, "{%s}Finish" % ns).text = deliverable_finish.isoformat()
                ET.SubElement(milestone, "{%s}Duration" % ns).text = "PT0M"
                ET.SubElement(milestone, "{%s}Summary" % ns).text = "0"
    
    else:
        # No deliverable column, create flat task list
        for idx, row in df.iterrows():
            task = ET.SubElement(tasks, "{%s}Task" % ns)
            uid = task_uid
            task_uid += 1
            
            task_name = row.get("Task_Name", f"Task {uid}")
            hours = float(row.get("Planned_Hours", row.get("Hours", 8)))
            duration_days = max(1, int(np.ceil(hours / hours_per_day)))
            
            task_start = current_date
            task_end = add_business_days(task_start, duration_days)
            
            ET.SubElement(task, "{%s}UID" % ns).text = str(uid)
            ET.SubElement(task, "{%s}ID" % ns).text = str(uid)
            ET.SubElement(task, "{%s}Name" % ns).text = str(task_name)
            ET.SubElement(task, "{%s}Type" % ns).text = "0"
            ET.SubElement(task, "{%s}IsNull" % ns).text = "0"
            ET.SubElement(task, "{%s}WBS" % ns).text = str(uid)
            ET.SubElement(task, "{%s}OutlineLevel" % ns).text = "1"
            ET.SubElement(task, "{%s}Priority" % ns).text = "500"
            ET.SubElement(task, "{%s}Start" % ns).text = task_start.isoformat()
            ET.SubElement(task, "{%s}Finish" % ns).text = task_end.isoformat()
            ET.SubElement(task, "{%s}Duration" % ns).text = f"PT{int(hours * 60)}M"
            ET.SubElement(task, "{%s}DurationFormat" % ns).text = "7"
            ET.SubElement(task, "{%s}Work" % ns).text = f"PT{int(hours * 60)}M"
            ET.SubElement(task, "{%s}Summary" % ns).text = "0"
            
            current_date = task_end
            task_map[uid] = task
    
    # Create Assignments container
    assignments = ET.SubElement(root, "{%s}Assignments" % ns)
    assignment_uid = 1
    
    # Create resource assignments
    if "Role" in df.columns:
        for idx, row in df.iterrows():
            if pd.notna(row.get("Role")):
                role = str(row["Role"])
                if role in resource_map:
                    # Find the corresponding task
                    task_idx = idx + 1  # Adjust for 0-based project task
                    if "Deliverable" in df.columns:
                        task_idx += len(df["Deliverable"].unique())  # Account for deliverable summary tasks
                    
                    # Create assignment
                    assign = ET.SubElement(assignments, "{%s}Assignment" % ns)
                    ET.SubElement(assign, "{%s}UID" % ns).text = str(assignment_uid)
                    ET.SubElement(assign, "{%s}TaskUID" % ns).text = str(task_idx)
                    ET.SubElement(assign, "{%s}ResourceUID" % ns).text = str(resource_map[role])
                    ET.SubElement(assign, "{%s}Units" % ns).text = "1"
                    
                    hours = float(row.get("Planned_Hours", row.get("Hours", 8)))
                    ET.SubElement(assign, "{%s}Work" % ns).text = f"PT{int(hours * 60)}M"
                    
                    assignment_uid += 1
    
    # Write the XML file
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(output_xml, encoding="utf-8", xml_declaration=True)
    
    # Return statistics
    stats = {
        "task_count": task_uid - 1,
        "resource_count": len(resource_map),
        "assignment_count": assignment_uid - 1,
        "project_start": project_start.isoformat(),
        "project_end": current_date.isoformat() if current_date else project_start.isoformat(),
        "deliverable_count": len(df["Deliverable"].unique()) if "Deliverable" in df.columns else 0,
        "total_hours": float(df["Planned_Hours"].sum() if "Planned_Hours" in df.columns else df.get("Hours", pd.Series([0])).sum()),
        "total_cost": float(df["Price_USD"].sum()) if "Price_USD" in df.columns else 0
    }
    
    print(f"[MSPDI] Created {output_xml}: {stats['task_count']} tasks, {stats['resource_count']} resources")
    
    return stats


def create_empty_mspdi_xml(project_name: str, start_date_iso: Optional[str] = None) -> ET.Element:
    """Create a minimal empty MSPDI XML structure"""
    ns = "http://schemas.microsoft.com/project"
    ET.register_namespace("", ns)
    
    root = ET.Element("{%s}Project" % ns)
    ET.SubElement(root, "{%s}Name" % ns).text = project_name
    ET.SubElement(root, "{%s}Title" % ns).text = project_name
    
    if start_date_iso:
        ET.SubElement(root, "{%s}StartDate" % ns).text = start_date_iso
    else:
        ET.SubElement(root, "{%s}StartDate" % ns).text = datetime.now().isoformat()
    
    # Add empty containers
    ET.SubElement(root, "{%s}Resources" % ns)
    tasks = ET.SubElement(root, "{%s}Tasks" % ns)
    
    # Add minimal project task
    project_task = ET.SubElement(tasks, "{%s}Task" % ns)
    ET.SubElement(project_task, "{%s}UID" % ns).text = "0"
    ET.SubElement(project_task, "{%s}ID" % ns).text = "0"
    ET.SubElement(project_task, "{%s}Name" % ns).text = project_name
    ET.SubElement(project_task, "{%s}Summary" % ns).text = "1"
    
    ET.SubElement(root, "{%s}Assignments" % ns)
    
    return root


def add_business_days(start_date: datetime, days: int) -> datetime:
    """Add business days to a date, skipping weekends"""
    current = start_date
    days_added = 0
    
    while days_added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Monday = 0, Friday = 4
            days_added += 1
    
    return current


def calculate_business_hours(start_date: datetime, end_date: datetime) -> float:
    """Calculate business hours between two dates"""
    if end_date <= start_date:
        return 0.0
    
    current = start_date
    total_hours = 0.0
    
    while current < end_date:
        if current.weekday() < 5:  # Business day
            total_hours += 8.0  # 8 hours per business day
        current += timedelta(days=1)
    
    return total_hours


if __name__ == "__main__":
    # Test the converter
    test_xlsx = "test.xlsx"
    test_xml = "test.xml"
    
    if os.path.exists(test_xlsx):
        stats = convert_excel_to_mspdi(
            input_xlsx=test_xlsx,
            output_xml=test_xml,
            project_name="Test Project"
        )
        print(f"Conversion complete: {stats}")
    else:
        print(f"Test file {test_xlsx} not found")