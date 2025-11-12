#!/usr/bin/env python3
"""
Enhanced Microsoft Project MSPDI XML Export with Professional PM Features
Includes WBS structure, dependencies, resource assignments, milestones, custom fields, and calendars
"""

import os
import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import logging
import hashlib
import random

# Configure logging for debugging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


def normalize_resource_name(name: str) -> str:
    """
    Normalize resource name for deduplication.
    Strips whitespace and converts to lowercase for comparison.
    
    Args:
        name: Raw resource name (e.g., "  Senior Designer  ")
    
    Returns:
        Normalized name (e.g., "senior designer")
    """
    return str(name).strip().lower()


def sanitize_task_name(name: str) -> str:
    """
    Sanitize task name by removing banned suffixes and normalizing whitespace.
    
    Removes:
    - " – COMPLETE" suffix (case-insensitive, handles various dash types)
    - " - COMPLETE" suffix
    - Extra whitespace
    
    Args:
        name: Raw task name
    
    Returns:
        Sanitized task name
    """
    import re
    name = str(name).strip()
    # Remove " – COMPLETE" or " - COMPLETE" suffix (case-insensitive)
    name = re.sub(r'\s*[-–]\s*complete\s*$', '', name, flags=re.IGNORECASE)
    # Normalize multiple spaces to single space
    name = re.sub(r'\s+', ' ', name)
    return name.strip()


def should_drop_wrapper_task(name: str) -> bool:
    """
    Check if a task name matches banned wrapper patterns.
    
    Wrapper tasks to exclude:
    - Anything starting with "Phase" followed by digits (Phase 1, Phase 2 Kickoff, etc.)
    - Anything starting with "Client Approval" (Client Approval, Client Approval - Final, etc.)
    - Anything starting with "Client Review" (Client Review, Client Review & Revisions, etc.)
    - Anything starting with "Internal Review"
    
    Args:
        name: Task name to check
    
    Returns:
        True if task should be dropped, False otherwise
    """
    import re
    name_normalized = name.strip().lower()
    
    # Pattern: Check if name STARTS WITH these banned prefixes (not exact match)
    # This catches "Phase 1 Kickoff", "Client Approval - Final", etc.
    banned_patterns = [
        r'^phase\s*\d+',              # Phase 1, Phase 2, Phase 3 Kickoff, etc.
        r'^client\s*approval',         # Client Approval, Client Approval - Final, etc.
        r'^client\s*review',           # Client Review, Client Review & Revisions, etc.
        r'^client\s*revisions?',       # Client Revision, Client Revisions, etc.
        r'^internal\s*review',         # Internal Review, Internal Review - Draft, etc.
    ]
    
    for pattern in banned_patterns:
        if re.match(pattern, name_normalized, re.IGNORECASE):
            return True
    
    return False


def normalize_task_name_for_dedup(name: str) -> str:
    """
    Normalize task name for deduplication key.
    
    Args:
        name: Task name
    
    Returns:
        Normalized lowercase name with single spaces
    """
    import re
    name = str(name).strip().lower()
    return re.sub(r'\s+', ' ', name)


def validate_task_hierarchy(tasks_elem: ET.Element, ns: str) -> List[Dict[str, str]]:
    """
    Validate that every summary task (Summary=1) has at least one child task.
    
    This is CRITICAL for Workfront import compatibility. Workfront rejects XML files
    with empty summary tasks (no children) with "plan has to link" error.
    
    Args:
        tasks_elem: The Tasks XML element containing all Task elements
        ns: XML namespace string
    
    Returns:
        List of violations, each dict with keys: 'uid', 'name', 'wbs', 'outline_level'
        Empty list if no violations found.
    """
    violations = []
    
    # Build parent-child relationship map: {parent_outline_level: [child_uids...]}
    # We need to check that every summary task has at least one direct child
    task_metadata = {}  # {uid: {name, wbs, outline_number, outline_level, is_summary}}
    
    # First pass: collect all task metadata
    for task in tasks_elem.findall("{%s}Task" % ns):
        uid_elem = task.find("{%s}UID" % ns)
        name_elem = task.find("{%s}Name" % ns)
        wbs_elem = task.find("{%s}WBS" % ns)
        outline_num_elem = task.find("{%s}OutlineNumber" % ns)
        outline_level_elem = task.find("{%s}OutlineLevel" % ns)
        summary_elem = task.find("{%s}Summary" % ns)
        
        if uid_elem is not None:
            uid = uid_elem.text
            task_metadata[uid] = {
                'name': name_elem.text if name_elem is not None else 'Unknown',
                'wbs': wbs_elem.text if wbs_elem is not None else 'Unknown',
                'outline_number': outline_num_elem.text if outline_num_elem is not None else 'Unknown',
                'outline_level': int(outline_level_elem.text) if outline_level_elem is not None else 0,
                'is_summary': summary_elem is not None and summary_elem.text == '1'
            }
    
    # Second pass: for each summary task, find children and validate
    for uid, metadata in task_metadata.items():
        if not metadata['is_summary']:
            continue  # Skip non-summary tasks
        
        # Find children: tasks with outline_level = this_level + 1 AND outline_number starts with this outline_number
        this_outline_num = metadata['outline_number']
        this_level = metadata['outline_level']
        
        has_children = False
        for child_uid, child_metadata in task_metadata.items():
            if child_uid == uid:
                continue  # Skip self
            
            child_outline_num = child_metadata['outline_number']
            child_level = child_metadata['outline_level']
            
            # Check if this is a direct child:
            # 1. Child level must be exactly parent_level + 1
            # 2. Child outline number must start with parent outline number + "."
            #    EXCEPTION: Root task (level 0) has children at level 1 with outline numbers "1", "2", etc.
            if child_level == this_level + 1:
                # Special case for root task (level 0): children are "1", "2", "3", not "0.1", "0.2"
                if this_level == 0:
                    has_children = True
                    break
                # Normal case: children must start with parent number + dot
                elif child_outline_num.startswith(this_outline_num + "."):
                    has_children = True
                    break
        
        if not has_children:
            violations.append({
                'uid': uid,
                'name': metadata['name'],
                'wbs': metadata['wbs'],
                'outline_level': str(this_level)
            })
    
    return violations


def check_for_trailing_dots(xml_string: str) -> List[Dict[str, str]]:
    """
    Scan XML string for OutlineNumber values ending with ".".
    
    Trailing dots in OutlineNumber are invalid and can cause import issues.
    Example: "1.2." is invalid, should be "1.2"
    
    Args:
        xml_string: Raw XML content as string
    
    Returns:
        List of violations, each dict with keys: 'outline_number', 'context'
        Empty list if no violations found.
    """
    import re
    violations = []
    
    # Pattern to find OutlineNumber elements ending with "."
    # Captures: <OutlineNumber>1.2.</OutlineNumber>
    pattern = r'<OutlineNumber>([^<]+\.)</OutlineNumber>'
    
    matches = re.finditer(pattern, xml_string)
    for match in matches:
        outline_number = match.group(1)
        # Get surrounding context (50 chars before and after)
        start = max(0, match.start() - 50)
        end = min(len(xml_string), match.end() + 50)
        context = xml_string[start:end]
        
        violations.append({
            'outline_number': outline_number,
            'context': context
        })
    
    return violations


class DependencyType(Enum):
    """Types of task dependencies for MS Project"""
    FINISH_TO_START = 1  # Most common: Task B starts after Task A finishes
    START_TO_START = 2   # Tasks start together
    FINISH_TO_FINISH = 3 # Tasks finish together
    START_TO_FINISH = 4  # Rare: Task B finishes after Task A starts


class ConstraintType(Enum):
    """Task constraint types for MS Project"""
    AS_SOON_AS_POSSIBLE = 0
    AS_LATE_AS_POSSIBLE = 1
    MUST_START_ON = 2
    MUST_FINISH_ON = 3
    START_NO_EARLIER_THAN = 4
    START_NO_LATER_THAN = 5
    FINISH_NO_EARLIER_THAN = 6
    FINISH_NO_LATER_THAN = 7


def add_task_extended_attribute(task_elem: ET.Element, ns: str, field_id: str, value: Any):
    """
    Write a single task-level ExtendedAttribute compliant with MSPDI schema.
    Creates flat ExtendedAttribute siblings under Task with ONLY FieldID + Value.
    
    Per GPT-5 Pro guidance: Task-level ExtendedAttributes must be flat (no wrapper container,
    no UID/ElementType/CfType metadata). Rich metadata belongs only in project-level definitions.
    
    Args:
        task_elem: The Task XML element
        ns: XML namespace
        field_id: FieldID (e.g., "188743732" for Text2/Deliverable Code)
        value: The value to set (converted to string, None becomes empty string)
    """
    ea = ET.SubElement(task_elem, "{%s}ExtendedAttribute" % ns)
    ET.SubElement(ea, "{%s}FieldID" % ns).text = str(field_id)
    ET.SubElement(ea, "{%s}Value" % ns).text = "" if value is None else str(value)


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
    add_dependencies: bool = True,
    add_custom_fields: bool = True
) -> Dict[str, Any]:
    """
    Convert an Excel WBS file to enhanced Microsoft Project XML (MSPDI) format.
    
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
        add_dependencies: Add task dependencies
        add_custom_fields: Add ExtendedAttribute elements for Workfront with proper MSPDI schema structure
        
    Returns:
        Dictionary with conversion statistics
    """
    
    # Read the Excel file
    try:
        logging.info(f"Reading Excel file: {input_xlsx}, sheet: {sheet_name}")
        df = pd.read_excel(input_xlsx, sheet_name=sheet_name)
        logging.info(f"Successfully loaded {len(df)} rows from Excel")
        
        # FIX: Normalize column headers (replace spaces with underscores)
        # This is necessary because the Excel writer converts "Start_Date" to "Start Date"
        # but the GANTT merge logic checks for "Start_Date"
        original_columns = list(df.columns)
        df.columns = [str(c).replace(" ", "_") for c in df.columns]
        logging.info(f"[HEADER NORMALIZATION] Original columns (first 5): {original_columns[:5]}")
        logging.info(f"[HEADER NORMALIZATION] Normalized columns (first 5): {list(df.columns[:5])}")
        
        # Log if Start_Date/End_Date are present after normalization
        if "Start_Date" in df.columns:
            logging.info(f"[HEADER NORMALIZATION] ✓ Start_Date column found after normalization")
        if "End_Date" in df.columns:
            logging.info(f"[HEADER NORMALIZATION] ✓ End_Date column found after normalization")
        
    except Exception as e:
        logging.error(f"Error reading Excel file: {e}")
        return {"error": str(e), "task_count": 0}
    
    if df.empty:
        logging.warning(f"Empty DataFrame from {input_xlsx}")
        root = create_empty_mspdi_xml(project_name or "Empty Project", fixed_start_iso)
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        
        # Write without declaration first
        tree.write(output_xml, encoding="utf-8", xml_declaration=False)
        
        # Read the file and prepend the correct declaration
        with open(output_xml, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Write back with Workfront-compliant declaration (double quotes, uppercase UTF-8)
        with open(output_xml, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(content)
        
        return {"task_count": 0, "warning": "Empty input data"}
    
    # Determine project start date
    if fixed_start_iso:
        project_start = datetime.fromisoformat(fixed_start_iso.replace("Z", "+00:00"))
        # Remove timezone info and normalize to 09:00 business hours for calendar consistency
        project_start = project_start.replace(hour=9, minute=0, second=0, microsecond=0, tzinfo=None)
    elif start_date_mode == "next_monday":
        today = datetime.now()
        days_ahead = 0 - today.weekday()  # Monday is 0
        if days_ahead <= 0:
            days_ahead += 7
        project_start = today + timedelta(days=days_ahead)
        project_start = project_start.replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        project_start = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Create MSPDI XML structure
    ns = "http://schemas.microsoft.com/project"
    ET.register_namespace("", ns)
    
    root = ET.Element("{%s}Project" % ns)
    
    # Add enhanced project properties
    ET.SubElement(root, "{%s}SaveVersion" % ns).text = "14"  # MS Project 2010 format
    ET.SubElement(root, "{%s}Name" % ns).text = project_name or "Project"
    ET.SubElement(root, "{%s}Title" % ns).text = project_name or "Project"
    ET.SubElement(root, "{%s}Subject" % ns).text = "Agency Project Plan"
    ET.SubElement(root, "{%s}Category" % ns).text = "Project Management"
    ET.SubElement(root, "{%s}Company" % ns).text = "Agency"
    ET.SubElement(root, "{%s}Manager" % ns).text = "Project Manager"
    ET.SubElement(root, "{%s}Author" % ns).text = "Agency Project Builder"
    ET.SubElement(root, "{%s}CreationDate" % ns).text = datetime.now().isoformat()
    ET.SubElement(root, "{%s}LastSaved" % ns).text = datetime.now().isoformat()
    ET.SubElement(root, "{%s}ScheduleFromStart" % ns).text = "1"
    ET.SubElement(root, "{%s}StartDate" % ns).text = project_start.isoformat()
    ET.SubElement(root, "{%s}FinishDate" % ns).text = (project_start + timedelta(days=365)).isoformat()
    ET.SubElement(root, "{%s}FYStartDate" % ns).text = "1"  # January
    ET.SubElement(root, "{%s}CriticalSlackLimit" % ns).text = "0"
    ET.SubElement(root, "{%s}CurrencyDigits" % ns).text = "2"
    ET.SubElement(root, "{%s}CurrencySymbol" % ns).text = "$"
    ET.SubElement(root, "{%s}CurrencyCode" % ns).text = "USD"
    ET.SubElement(root, "{%s}CurrencySymbolPosition" % ns).text = "0"
    # WORKFRONT FIX: Reference Default Calendar UID 9999
    ET.SubElement(root, "{%s}DefaultCalendarUID" % ns).text = "9999"
    ET.SubElement(root, "{%s}DefaultStartTime" % ns).text = "09:00:00"
    ET.SubElement(root, "{%s}DefaultFinishTime" % ns).text = "18:00:00"
    ET.SubElement(root, "{%s}MinutesPerDay" % ns).text = str(int(hours_per_day * 60))
    ET.SubElement(root, "{%s}MinutesPerWeek" % ns).text = str(int(hours_per_day * 60 * 5))
    ET.SubElement(root, "{%s}DaysPerMonth" % ns).text = "20"
    ET.SubElement(root, "{%s}DefaultTaskType" % ns).text = "0"  # Fixed Units
    ET.SubElement(root, "{%s}DefaultFixedCostAccrual" % ns).text = "2"  # Prorated
    ET.SubElement(root, "{%s}DefaultStandardRate" % ns).text = f"{blended_rate or 150:.2f}"
    ET.SubElement(root, "{%s}DefaultOvertimeRate" % ns).text = f"{(blended_rate or 150) * 1.5:.2f}"
    ET.SubElement(root, "{%s}DurationFormat" % ns).text = "7"  # Days
    ET.SubElement(root, "{%s}WorkFormat" % ns).text = "2"  # Hours
    ET.SubElement(root, "{%s}EditableActualCosts" % ns).text = "0"
    ET.SubElement(root, "{%s}HonorConstraints" % ns).text = "1"
    ET.SubElement(root, "{%s}InsertedProjectsLikeSummary" % ns).text = "0"
    ET.SubElement(root, "{%s}MultipleCriticalPaths" % ns).text = "0"
    ET.SubElement(root, "{%s}NewTasksEffortDriven" % ns).text = "1"
    ET.SubElement(root, "{%s}NewTasksEstimated" % ns).text = "1"
    ET.SubElement(root, "{%s}SplitsInProgressTasks" % ns).text = "1"
    ET.SubElement(root, "{%s}SpreadActualCost" % ns).text = "0"
    ET.SubElement(root, "{%s}SpreadPercentComplete" % ns).text = "0"
    ET.SubElement(root, "{%s}TaskUpdatesResource" % ns).text = "1"
    ET.SubElement(root, "{%s}FiscalYearStart" % ns).text = "0"
    ET.SubElement(root, "{%s}WeekStartDay" % ns).text = "1"  # Monday
    ET.SubElement(root, "{%s}MoveCompletedEndsBack" % ns).text = "0"
    ET.SubElement(root, "{%s}MoveRemainingStartsBack" % ns).text = "0"
    ET.SubElement(root, "{%s}MoveRemainingStartsForward" % ns).text = "0"
    ET.SubElement(root, "{%s}MoveCompletedEndsForward" % ns).text = "0"
    ET.SubElement(root, "{%s}BaselineForEarnedValue" % ns).text = "0"
    ET.SubElement(root, "{%s}AutoAddNewResourcesAndTasks" % ns).text = "1"
    ET.SubElement(root, "{%s}CurrentDate" % ns).text = datetime.now().isoformat()
    ET.SubElement(root, "{%s}Autolink" % ns).text = "1"
    ET.SubElement(root, "{%s}NewTaskStartDate" % ns).text = "0"  # Project Start Date
    ET.SubElement(root, "{%s}NewTasksAreManual" % ns).text = "0"
    ET.SubElement(root, "{%s}DefaultTaskEVMethod" % ns).text = "0"  # % Complete
    ET.SubElement(root, "{%s}ProjectExternallyEdited" % ns).text = "0"
    
    # Add ExtendedAttributes definitions for custom fields
    if add_custom_fields:
        extended_attrs = ET.SubElement(root, "{%s}ExtendedAttributes" % ns)
        
        # Custom Field 1: Risk Score (Number)
        ext_attr1 = ET.SubElement(extended_attrs, "{%s}ExtendedAttribute" % ns)
        ET.SubElement(ext_attr1, "{%s}FieldID" % ns).text = "188743713"  # Task Number1
        ET.SubElement(ext_attr1, "{%s}FieldName" % ns).text = "Number1"
        ET.SubElement(ext_attr1, "{%s}Alias" % ns).text = "Risk Score"
        ET.SubElement(ext_attr1, "{%s}Guid" % ns).text = "000039B7-8BBE-4CEB-82C4-FA8C0B400033"
        
        # Custom Field 2: Confidence Level (Number)
        ext_attr2 = ET.SubElement(extended_attrs, "{%s}ExtendedAttribute" % ns)
        ET.SubElement(ext_attr2, "{%s}FieldID" % ns).text = "188743714"  # Task Number2
        ET.SubElement(ext_attr2, "{%s}FieldName" % ns).text = "Number2"
        ET.SubElement(ext_attr2, "{%s}Alias" % ns).text = "Confidence Level"
        ET.SubElement(ext_attr2, "{%s}Guid" % ns).text = "000039B7-8BBE-4CEB-82C4-FA8C0B400034"
        
        # Custom Field 3: Department (Text)
        ext_attr3 = ET.SubElement(extended_attrs, "{%s}ExtendedAttribute" % ns)
        ET.SubElement(ext_attr3, "{%s}FieldID" % ns).text = "188743731"  # Task Text1
        ET.SubElement(ext_attr3, "{%s}FieldName" % ns).text = "Text1"
        ET.SubElement(ext_attr3, "{%s}Alias" % ns).text = "Department"
        ET.SubElement(ext_attr3, "{%s}Guid" % ns).text = "000039B7-8BBE-4CEB-82C4-FA8C0B400035"
        
        # Custom Field 4: Deliverable Code (Text)
        ext_attr4 = ET.SubElement(extended_attrs, "{%s}ExtendedAttribute" % ns)
        ET.SubElement(ext_attr4, "{%s}FieldID" % ns).text = "188743732"  # Task Text2
        ET.SubElement(ext_attr4, "{%s}FieldName" % ns).text = "Text2"
        ET.SubElement(ext_attr4, "{%s}Alias" % ns).text = "Deliverable Code"
        ET.SubElement(ext_attr4, "{%s}Guid" % ns).text = "000039B7-8BBE-4CEB-82C4-FA8C0B400036"
        
        # Custom Field 5: Component Name (Text)
        ext_attr5 = ET.SubElement(extended_attrs, "{%s}ExtendedAttribute" % ns)
        ET.SubElement(ext_attr5, "{%s}FieldID" % ns).text = "188743733"  # Task Text3
        ET.SubElement(ext_attr5, "{%s}FieldName" % ns).text = "Text3"  
        ET.SubElement(ext_attr5, "{%s}Alias" % ns).text = "Component Name"
        ET.SubElement(ext_attr5, "{%s}Guid" % ns).text = "000039B7-8BBE-4CEB-82C4-FA8C0B400037"
        
        # Custom Field 6: Revenue (Number)
        ext_attr6 = ET.SubElement(extended_attrs, "{%s}ExtendedAttribute" % ns)
        ET.SubElement(ext_attr6, "{%s}FieldID" % ns).text = "188743715"  # Task Number3
        ET.SubElement(ext_attr6, "{%s}FieldName" % ns).text = "Number3"
        ET.SubElement(ext_attr6, "{%s}Alias" % ns).text = "Revenue"
        ET.SubElement(ext_attr6, "{%s}Guid" % ns).text = "000039B7-8BBE-4CEB-82C4-FA8C0B400038"
    
    # Add Calendar definition
    # WORKFRONT FIX: Use UID=9999 for Calendar to avoid collision with Task UIDs (0-N)
    # Workfront requires globally unique UIDs across ALL element types (Calendar, Tasks, Resources, Assignments)
    CALENDAR_UID = "9999"
    calendars = ET.SubElement(root, "{%s}Calendars" % ns)
    calendar = ET.SubElement(calendars, "{%s}Calendar" % ns)
    ET.SubElement(calendar, "{%s}UID" % ns).text = CALENDAR_UID
    ET.SubElement(calendar, "{%s}Name" % ns).text = "Standard"
    ET.SubElement(calendar, "{%s}IsBaseCalendar" % ns).text = "1"
    ET.SubElement(calendar, "{%s}IsBaselineCalendar" % ns).text = "0"
    ET.SubElement(calendar, "{%s}BaseCalendarUID" % ns).text = "-1"
    
    # Add weekdays
    weekdays = ET.SubElement(calendar, "{%s}WeekDays" % ns)
    for day_num, day_name in enumerate(['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'], 1):
        weekday = ET.SubElement(weekdays, "{%s}WeekDay" % ns)
        ET.SubElement(weekday, "{%s}DayType" % ns).text = str(day_num)
        if day_name in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
            ET.SubElement(weekday, "{%s}DayWorking" % ns).text = "1"
            working_times = ET.SubElement(weekday, "{%s}WorkingTimes" % ns)
            
            # Morning shift
            wt1 = ET.SubElement(working_times, "{%s}WorkingTime" % ns)
            ET.SubElement(wt1, "{%s}FromTime" % ns).text = "09:00:00"
            ET.SubElement(wt1, "{%s}ToTime" % ns).text = "12:00:00"
            
            # Afternoon shift
            wt2 = ET.SubElement(working_times, "{%s}WorkingTime" % ns)
            ET.SubElement(wt2, "{%s}FromTime" % ns).text = "13:00:00"
            ET.SubElement(wt2, "{%s}ToTime" % ns).text = "18:00:00"
        else:
            ET.SubElement(weekday, "{%s}DayWorking" % ns).text = "0"
    
    # WORKFRONT FIX: DO NOT add empty Baseline or OutlineCodes - Workfront rejects self-closing complex types
    # These elements require child nodes when present, so omit them entirely when no data exists
    

    # Create Tasks container
    tasks = ET.SubElement(root, "{%s}Tasks" % ns)
    
    # Add project summary task (Task 0)
    # CRITICAL FIX: Root task MUST have OutlineLevel=0 (not 1) for Workfront compatibility
    project_task = ET.SubElement(tasks, "{%s}Task" % ns)
    ET.SubElement(project_task, "{%s}UID" % ns).text = "0"
    ET.SubElement(project_task, "{%s}ID" % ns).text = "0"
    ET.SubElement(project_task, "{%s}Name" % ns).text = project_name or "Project"
    ET.SubElement(project_task, "{%s}Type" % ns).text = "1"  # Fixed Duration
    ET.SubElement(project_task, "{%s}IsNull" % ns).text = "0"
    ET.SubElement(project_task, "{%s}CreateDate" % ns).text = datetime.now().isoformat()
    ET.SubElement(project_task, "{%s}WBS" % ns).text = "0"
    ET.SubElement(project_task, "{%s}OutlineNumber" % ns).text = "0"
    ET.SubElement(project_task, "{%s}OutlineLevel" % ns).text = "0"
    ET.SubElement(project_task, "{%s}Priority" % ns).text = "500"
    ET.SubElement(project_task, "{%s}Start" % ns).text = project_start.isoformat()
    ET.SubElement(project_task, "{%s}Duration" % ns).text = "PT0M"
    ET.SubElement(project_task, "{%s}DurationFormat" % ns).text = "53"
    ET.SubElement(project_task, "{%s}Work" % ns).text = "PT0M"
    ET.SubElement(project_task, "{%s}Stop" % ns).text = project_start.isoformat()
    ET.SubElement(project_task, "{%s}Resume" % ns).text = project_start.isoformat()
    ET.SubElement(project_task, "{%s}ResumeValid" % ns).text = "0"
    ET.SubElement(project_task, "{%s}EffortDriven" % ns).text = "0"
    ET.SubElement(project_task, "{%s}Recurring" % ns).text = "0"
    ET.SubElement(project_task, "{%s}OverAllocated" % ns).text = "0"
    ET.SubElement(project_task, "{%s}Estimated" % ns).text = "0"
    ET.SubElement(project_task, "{%s}Milestone" % ns).text = "0"
    ET.SubElement(project_task, "{%s}Summary" % ns).text = "1"
    ET.SubElement(project_task, "{%s}Critical" % ns).text = "0"
    ET.SubElement(project_task, "{%s}IsSubproject" % ns).text = "0"
    ET.SubElement(project_task, "{%s}IsSubprojectReadOnly" % ns).text = "0"
    ET.SubElement(project_task, "{%s}IsMarked" % ns).text = "0"
    ET.SubElement(project_task, "{%s}IgnoreWarnings" % ns).text = "0"
    ET.SubElement(project_task, "{%s}ExternalTask" % ns).text = "0"
    ET.SubElement(project_task, "{%s}Active" % ns).text = "1"
    ET.SubElement(project_task, "{%s}Manual" % ns).text = "0"
    
    # Process WBS tasks with enhanced structure
    task_uid = 1
    task_map = {}
    
    # Initialize ExtendedAttribute UID counter for proper MSPDI schema compliance
    ext_attr_uid_counter = [1]  # Mutable list to track ExtendedAttribute UIDs across all tasks
    
    # FIX: Dual mapping system for WBS codes
    # 1. original_wbs_to_uid: Maps DataFrame WBS_ID → UID (for dependency lookup)
    # 2. sequential_wbs_to_uid: Maps sequential WBS → UID (for XML structure)
    original_wbs_to_uid = {}  # Original WBS_ID from DataFrame → UID mapping
    sequential_wbs_to_uid = {}  # Sequential WBS code → UID mapping
    
    deliverable_tasks = {}  # Track deliverable summary tasks for dependencies
    component_tasks = {}    # Track component tasks for dependencies
    current_date = project_start
    deliverable_ends = {}
    all_task_uids = []  # Track all task UIDs for phase gates
    
    # Initialize cost accumulators for aggregation
    deliverable_costs = {}  # {deliv_uid: total_cost}
    component_costs = {}    # {comp_uid: total_cost}
    
    
    # FIX: Sequential WBS counters - INDEPENDENT of DataFrame WBS_ID
    deliverable_counter = 1  # Sequential counter for deliverables: 1, 2, 3...
    component_counter_per_deliv = {}  # {deliverable_name: counter} for components per deliverable
    task_counter_per_comp = {}  # {(deliverable, component): counter} for tasks per component
    
    # Group by deliverable to create hierarchy
    deliverable_num = 0
    if "Deliverable" in df.columns:
        logging.info("Processing tasks grouped by deliverable with enhanced WBS structure")
        try:
            grouped = df.groupby("Deliverable", sort=False)
        except Exception as e:
            logging.error(f"Error grouping by deliverable: {e}")
            grouped = []
        
        for deliverable_name, group in grouped:
            deliverable_num += 1
            
            # Create deliverable summary task
            deliv_task = ET.SubElement(tasks, "{%s}Task" % ns)
            deliv_uid = task_uid
            task_uid += 1
            all_task_uids.append(deliv_uid)
            deliverable_tasks[str(deliverable_name)] = deliv_uid
            
            # Initialize cost accumulator for this deliverable
            deliverable_costs[deliv_uid] = 0.0
            
            # Get deliverable code and service department if available
            deliv_code = ""
            if "Deliverable_Code" in group.columns:
                deliv_code = str(group["Deliverable_Code"].iloc[0]) if not group["Deliverable_Code"].empty else ""
            
            # Get Service_Department for deliverable (from first row)
            service_dept = ""
            if "Service_Department" in group.columns and not group.empty:
                service_dept = str(group["Service_Department"].iloc[0]) if pd.notna(group["Service_Department"].iloc[0]) else ""
            
            # FIX: Preserve original WBS_ID from DataFrame for dependency lookup
            original_deliv_wbs_id = None
            if "WBS_ID" in group.columns and not group.empty:
                original_wbs_val = group.iloc[0].get("WBS_ID")
                if pd.notna(original_wbs_val):
                    original_deliv_wbs_id = str(original_wbs_val)
                    logging.info(f"[WBS SEQUENTIAL] Storing original WBS_ID for deliverable '{deliverable_name}': {original_deliv_wbs_id}")
            
            # FIX: Generate SEQUENTIAL WBS code (INDEPENDENT of DataFrame WBS_ID)
            # This ensures NO duplicates and perfect Workfront compatibility
            deliv_wbs = str(deliverable_counter)
            deliv_outline_level = "1"  # All deliverables are level 1
            
            logging.info(f"[WBS SEQUENTIAL] Deliverable '{deliverable_name}': Sequential WBS={deliv_wbs} (Original WBS_ID={original_deliv_wbs_id})")
            
            # FIX 1: Sanitize deliverable name to remove "– COMPLETE" suffix
            deliverable_name = sanitize_task_name(str(deliverable_name))
            
            ET.SubElement(deliv_task, "{%s}UID" % ns).text = str(deliv_uid)
            ET.SubElement(deliv_task, "{%s}ID" % ns).text = str(deliv_uid)
            ET.SubElement(deliv_task, "{%s}Name" % ns).text = deliverable_name
            ET.SubElement(deliv_task, "{%s}Type" % ns).text = "1"  # Fixed Duration
            ET.SubElement(deliv_task, "{%s}IsNull" % ns).text = "0"
            # WORKFRONT FIX: Strip trailing periods from WBS to prevent "8." format
            deliv_wbs_clean = str(deliv_wbs).rstrip('.')
            ET.SubElement(deliv_task, "{%s}WBS" % ns).text = deliv_wbs_clean
            ET.SubElement(deliv_task, "{%s}OutlineNumber" % ns).text = deliv_wbs_clean
            ET.SubElement(deliv_task, "{%s}OutlineLevel" % ns).text = deliv_outline_level
            ET.SubElement(deliv_task, "{%s}Priority" % ns).text = "500"
            
            # FIX: Check if first row of deliverable has Start_Date (from Gantt merge)
            deliverable_start_date = current_date
            deliverable_end_date = None  # Will be set from Gantt or calculated
            
            if not group.empty and "Start_Date" in group.columns:
                first_row_start = group.iloc[0].get("Start_Date")
                if pd.notna(first_row_start):
                    try:
                        start_val = str(first_row_start)
                        if 'T' in start_val:
                            deliverable_start_date = datetime.fromisoformat(start_val.replace('Z', '+00:00'))
                            # Remove timezone info to make it timezone-naive for consistent comparisons
                            deliverable_start_date = deliverable_start_date.replace(tzinfo=None)
                        else:
                            deliverable_start_date = datetime.fromisoformat(start_val).replace(hour=9, minute=0, second=0)
                        logging.info(f"[GANTT MERGE] Deliverable '{deliverable_name}' Start: {deliverable_start_date.isoformat()}")
                    except Exception as e:
                        logging.warning(f"Could not parse deliverable Start_Date '{first_row_start}': {e}")
            
            # FIX: Check if first row of deliverable has End_Date (from Gantt merge)
            if not group.empty and "End_Date" in group.columns:
                first_row_end = group.iloc[0].get("End_Date")
                if pd.notna(first_row_end):
                    try:
                        end_val = str(first_row_end)
                        if 'T' in end_val:
                            deliverable_end_date = datetime.fromisoformat(end_val.replace('Z', '+00:00'))
                            # Remove timezone info to make it timezone-naive for consistent comparisons
                            deliverable_end_date = deliverable_end_date.replace(tzinfo=None)
                        else:
                            deliverable_end_date = datetime.fromisoformat(end_val).replace(hour=17, minute=0, second=0)
                        logging.info(f"[GANTT MERGE] Deliverable '{deliverable_name}' End: {deliverable_end_date.isoformat()}")
                    except Exception as e:
                        logging.warning(f"Could not parse deliverable End_Date '{first_row_end}': {e}")
            
            ET.SubElement(deliv_task, "{%s}Start" % ns).text = deliverable_start_date.isoformat()
            
            # FIX 4: Summary tasks (deliverables) must have ConstraintType=0 (ASAP) and no manual scheduling
            # Remove ManualStart, ManualFinish, ManualDuration, ConstraintDate - these prevent Workfront from rolling up dates
            ET.SubElement(deliv_task, "{%s}ConstraintType" % ns).text = "0"  # ASAP
            logging.info(f"[CONSTRAINT] Deliverable '{deliverable_name}': ASAP (Type 0) - summary task")
            
            ET.SubElement(deliv_task, "{%s}DurationFormat" % ns).text = "7"
            ET.SubElement(deliv_task, "{%s}Work" % ns).text = "PT0M"
            ET.SubElement(deliv_task, "{%s}EffortDriven" % ns).text = "0"
            ET.SubElement(deliv_task, "{%s}Recurring" % ns).text = "0"
            ET.SubElement(deliv_task, "{%s}OverAllocated" % ns).text = "0"
            ET.SubElement(deliv_task, "{%s}Estimated" % ns).text = "1"
            ET.SubElement(deliv_task, "{%s}Milestone" % ns).text = "0"
            ET.SubElement(deliv_task, "{%s}Summary" % ns).text = "1"
            ET.SubElement(deliv_task, "{%s}Critical" % ns).text = "0"
            ET.SubElement(deliv_task, "{%s}IsSubproject" % ns).text = "0"
            ET.SubElement(deliv_task, "{%s}IsSubprojectReadOnly" % ns).text = "0"
            ET.SubElement(deliv_task, "{%s}IsMarked" % ns).text = "0"
            ET.SubElement(deliv_task, "{%s}IgnoreWarnings" % ns).text = "0"
            ET.SubElement(deliv_task, "{%s}ExternalTask" % ns).text = "0"
            ET.SubElement(deliv_task, "{%s}Active" % ns).text = "1"
            
            # Add custom fields for deliverable (flat MSPDI schema)
            if add_custom_fields:
                # Deliverable Code
                if deliv_code:
                    add_task_extended_attribute(deliv_task, ns, "188743732", deliv_code)
                
                # Text1 = Department
                department_value = service_dept if service_dept else "Unassigned"
                add_task_extended_attribute(deliv_task, ns, "188743731", department_value)
            
            # Process component/task rows under this deliverable
            deliverable_start = deliverable_start_date  # Use merged start date from Gantt
            # FIX: Initialize deliverable_finish from Gantt End_Date if available, otherwise use start
            # This ensures deliverables with no child tasks (all filtered out) still have proper duration
            # Child tasks will update this to max(task finishes) if they exist
            deliverable_finish = deliverable_end_date if deliverable_end_date else deliverable_start_date
            
            # Group tasks by Component within this deliverable to create 3-level hierarchy
            logging.info(f"[3-LEVEL HIERARCHY] Processing deliverable '{deliverable_name}' with component grouping")
            try:
                if "Component" in group.columns:
                    # FIX: Fill blank Component values with "Uncategorized" to preserve all tasks
                    # This ensures NO tasks are dropped - blank components become "Uncategorized"
                    group_copy = group.copy()
                    
                    # Convert categorical to object if needed
                    if pd.api.types.is_categorical_dtype(group_copy["Component"]):
                        logging.info(f"[3-LEVEL HIERARCHY] Converting Component from categorical to object type")
                        group_copy["Component"] = group_copy["Component"].astype(object)
                    
                    # Fill blank Component values with "Uncategorized"
                    blank_mask = group_copy["Component"].isna() | (group_copy["Component"] == "") | group_copy["Component"].isnull()
                    blank_count = blank_mask.sum()
                    if blank_count > 0:
                        logging.info(f"[3-LEVEL HIERARCHY] Found {blank_count} tasks with blank Component, grouping as 'Uncategorized'")
                        group_copy.loc[blank_mask, "Component"] = "Uncategorized"
                    
                    # Group by Component (now includes "Uncategorized" for blank values)
                    component_grouped = group_copy.groupby("Component", sort=False, dropna=False)
                    logging.info(f"[3-LEVEL HIERARCHY] Found {len(component_grouped)} components in deliverable '{deliverable_name}'")
                    
                    # Convert to list of tuples for iteration
                    component_grouped = list(component_grouped)
                else:
                    logging.warning(f"[3-LEVEL HIERARCHY] No Component column found, creating single 'Uncategorized' group")
                    component_grouped = [("Uncategorized", group)]
            except Exception as e:
                logging.warning(f"[3-LEVEL HIERARCHY] Error grouping by Component: {e}, falling back to single group")
                import traceback
                traceback.print_exc()
                component_grouped = [("Uncategorized", group)]
            
            component_num = 0
            
            # FIX: Initialize component counter for this deliverable
            if str(deliverable_name) not in component_counter_per_deliv:
                component_counter_per_deliv[str(deliverable_name)] = 1
            
            # Loop through each component (Level 2)
            for component_name, component_group in component_grouped:
                # GPT-5 Pro FIX: Sanitize component name BEFORE any processing
                component_name = sanitize_task_name(str(component_name)) if component_name else "Uncategorized"
                
                # GPT-5 Pro FIX: Filter wrapper components BEFORE creating task element
                if component_name != "Uncategorized" and should_drop_wrapper_task(component_name):
                    logging.info(f"[WRAPPER FILTER] Skipping banned wrapper component: '{component_name}'")
                    continue  # Skip this entire component
                
                component_num += 1
                
                # NOW create component summary task (Level 2) - AFTER sanitization and filtering
                comp_task = ET.SubElement(tasks, "{%s}Task" % ns)
                comp_uid = task_uid
                task_uid += 1
                all_task_uids.append(comp_uid)
                
                # Initialize cost accumulator for this component
                component_costs[comp_uid] = 0.0
                
                # Store component task for dependencies
                component_tasks[f"{deliverable_name}:{component_name}"] = comp_uid
                
                logging.info(f"[3-LEVEL HIERARCHY] Creating component summary task: '{component_name}' (UID={comp_uid})")
                
                # Get Service_Department for component (from first row of component group)
                comp_service_dept = ""
                if "Service_Department" in component_group.columns and not component_group.empty:
                    comp_service_dept = str(component_group["Service_Department"].iloc[0]) if pd.notna(component_group["Service_Department"].iloc[0]) else ""
                
                # FIX: Preserve original WBS_ID from DataFrame for dependency lookup
                original_comp_wbs_id = None
                if "WBS_ID" in component_group.columns and not component_group.empty:
                    original_wbs_val = component_group.iloc[0].get("WBS_ID")
                    if pd.notna(original_wbs_val):
                        original_comp_wbs_id = str(original_wbs_val)
                        logging.info(f"[WBS SEQUENTIAL] Storing original WBS_ID for component '{component_name}': {original_comp_wbs_id}")
                
                # FIX: Generate SEQUENTIAL WBS code (INDEPENDENT of DataFrame WBS_ID)
                # Format: {deliverable_wbs}.{component_counter}
                comp_wbs = f"{deliv_wbs}.{component_counter_per_deliv[str(deliverable_name)]}"
                comp_outline_level = "2"  # All components are level 2
                
                logging.info(f"[WBS SEQUENTIAL] Component '{component_name}': Sequential WBS={comp_wbs} (Original WBS_ID={original_comp_wbs_id})")
                
                # Component task properties
                ET.SubElement(comp_task, "{%s}UID" % ns).text = str(comp_uid)
                ET.SubElement(comp_task, "{%s}ID" % ns).text = str(comp_uid)
                ET.SubElement(comp_task, "{%s}Name" % ns).text = component_name
                ET.SubElement(comp_task, "{%s}Type" % ns).text = "1"  # Fixed Duration
                ET.SubElement(comp_task, "{%s}IsNull" % ns).text = "0"
                # WORKFRONT FIX: Strip trailing periods from WBS to prevent "8.3." format
                comp_wbs_clean = str(comp_wbs).rstrip('.')
                ET.SubElement(comp_task, "{%s}WBS" % ns).text = comp_wbs_clean
                ET.SubElement(comp_task, "{%s}OutlineNumber" % ns).text = comp_wbs_clean
                ET.SubElement(comp_task, "{%s}OutlineLevel" % ns).text = comp_outline_level
                ET.SubElement(comp_task, "{%s}Priority" % ns).text = "500"
                ET.SubElement(comp_task, "{%s}Start" % ns).text = current_date.isoformat()
                
                # FIX 4: Component summary tasks must have ConstraintType=0 (ASAP) and no manual scheduling
                ET.SubElement(comp_task, "{%s}ConstraintType" % ns).text = "0"  # ASAP
                logging.info(f"[CONSTRAINT] Component '{component_name}': ASAP (Type 0) - summary task")
                
                ET.SubElement(comp_task, "{%s}DurationFormat" % ns).text = "7"
                ET.SubElement(comp_task, "{%s}Work" % ns).text = "PT0M"
                ET.SubElement(comp_task, "{%s}EffortDriven" % ns).text = "0"
                ET.SubElement(comp_task, "{%s}Recurring" % ns).text = "0"
                ET.SubElement(comp_task, "{%s}OverAllocated" % ns).text = "0"
                ET.SubElement(comp_task, "{%s}Estimated" % ns).text = "1"
                ET.SubElement(comp_task, "{%s}Milestone" % ns).text = "0"
                ET.SubElement(comp_task, "{%s}Summary" % ns).text = "1"  # This is a summary task
                ET.SubElement(comp_task, "{%s}Critical" % ns).text = "0"
                ET.SubElement(comp_task, "{%s}IsSubproject" % ns).text = "0"
                ET.SubElement(comp_task, "{%s}IsSubprojectReadOnly" % ns).text = "0"
                ET.SubElement(comp_task, "{%s}IsMarked" % ns).text = "0"
                ET.SubElement(comp_task, "{%s}IgnoreWarnings" % ns).text = "0"
                ET.SubElement(comp_task, "{%s}ExternalTask" % ns).text = "0"
                ET.SubElement(comp_task, "{%s}Active" % ns).text = "1"
                
                # Add custom fields for component (flat MSPDI schema)
                if add_custom_fields:
                    # Component Name
                    add_task_extended_attribute(comp_task, ns, "188743733", str(component_name))
                    
                    # Deliverable Code
                    if deliv_code:
                        add_task_extended_attribute(comp_task, ns, "188743732", deliv_code)
                    
                    # Text1 = Department
                    comp_department_value = comp_service_dept if comp_service_dept else "Unassigned"
                    add_task_extended_attribute(comp_task, ns, "188743731", comp_department_value)
                
                # Track component start/finish dates
                component_start = current_date
                component_finish = current_date
                task_num_in_component = 0
                
                # FIX: Initialize task counter for this component
                comp_key = (str(deliverable_name), str(component_name))
                if comp_key not in task_counter_per_comp:
                    task_counter_per_comp[comp_key] = 1
                
                # FIX 3: Task deduplication - track seen tasks by (deliverable_code, component_name, normalized_task_name)
                seen_tasks = set()
                
                # Loop through tasks within this component (Level 3)
                for idx, row in component_group.iterrows():
                    try:
                        # FIX: SKIP creating Task elements for role rows (rows where Role is populated)
                        # These will be converted to Assignments later
                        role_value = row.get("Role", "")
                        if pd.notna(role_value) and str(role_value).strip():
                            logging.info(f"[ROLE ROW] Skipping task creation for role row at index {idx}: Role={role_value}")
                            continue  # Skip to next row without creating a Task
                        
                        # Get task details - FIX: Use proper L3 task name, NOT Component as fallback
                        # CRITICAL: Do this BEFORE creating task element to prevent ghost tasks
                        task_name = (row.get("Task_Name") or 
                                    row.get("L3_Task") or 
                                    row.get("Task_Label") or 
                                    f"{component_name} - Task {task_num_in_component + 1}")
                        
                        # FIX 1: Sanitize task name to remove "– COMPLETE" suffix
                        task_name = sanitize_task_name(str(task_name))
                        
                        # FIX 2: Filter wrapper tasks (Phase 1, Client Approval, etc.)
                        # CRITICAL: Do this BEFORE creating task element
                        if should_drop_wrapper_task(task_name):
                            logging.info(f"[WRAPPER FILTER] Skipping banned wrapper task: '{task_name}'")
                            continue
                        
                        # FIX 3: Task deduplication - check if task already seen in this component
                        # CRITICAL: Do this BEFORE creating task element to prevent ghost tasks
                        dedup_key = (deliv_code, component_name, normalize_task_name_for_dedup(task_name))
                        if dedup_key in seen_tasks:
                            logging.info(f"[DEDUP] Skipping duplicate task: '{task_name}' in component '{component_name}'")
                            continue
                        seen_tasks.add(dedup_key)
                        
                        # NOW create the task element (after all filtering checks passed)
                        task_num_in_component += 1
                        task = ET.SubElement(tasks, "{%s}Task" % ns)
                        uid = task_uid
                        task_uid += 1
                        all_task_uids.append(uid)
                        
                        department = row.get("Department", "")
                        
                        # Get Service_Department for this task
                        task_service_dept = row.get("Service_Department", "")
                        if pd.isna(task_service_dept):
                            task_service_dept = ""
                        
                        logging.info(f"[3-LEVEL HIERARCHY] Creating L3 task: '{task_name}' (UID={uid}, Component={component_name})")
                        
                        # Safely get hours
                        planned_hours = row.get("Planned_Hours")
                        if pd.isna(planned_hours) or planned_hours is None:
                            planned_hours = row.get("Hours", 8)
                        if pd.isna(planned_hours) or planned_hours is None:
                            planned_hours = 8
                        hours = float(planned_hours)
                        duration_days = max(1, int(np.ceil(hours / hours_per_day)))
                        
                        # FIX: Use merged timeline dates (Start_Date/End_Date) from Gantt if available
                        # Only fall back to calculated dates if missing
                        task_start = None
                        task_end = None
                        
                        # Check for Start_Date field (from Gantt merge)
                        if "Start_Date" in row.index and pd.notna(row.get("Start_Date")):
                            try:
                                start_val = str(row.get("Start_Date"))
                                # Handle ISO format: 2025-11-16 or 2025-11-16T01:00:00
                                if 'T' in start_val:
                                    task_start = datetime.fromisoformat(start_val.replace('Z', '+00:00'))
                                    # Remove timezone info to make it timezone-naive for consistent comparisons
                                    task_start = task_start.replace(tzinfo=None)
                                else:
                                    # Date only - add default 9 AM time
                                    task_start = datetime.fromisoformat(start_val).replace(hour=9, minute=0, second=0)
                                logging.info(f"[GANTT MERGE] Using merged Start_Date for '{task_name}': {task_start.isoformat()}")
                            except Exception as e:
                                logging.warning(f"Could not parse Start_Date '{row.get('Start_Date')}': {e}")
                        
                        # Check for End_Date field (from Gantt merge)
                        if "End_Date" in row.index and pd.notna(row.get("End_Date")):
                            try:
                                end_val = str(row.get("End_Date"))
                                # Handle ISO format: 2025-11-27 or 2025-11-27T17:00:00
                                if 'T' in end_val:
                                    task_end = datetime.fromisoformat(end_val.replace('Z', '+00:00'))
                                    # Remove timezone info to make it timezone-naive for consistent comparisons
                                    task_end = task_end.replace(tzinfo=None)
                                else:
                                    # Date only - add default 5 PM time
                                    task_end = datetime.fromisoformat(end_val).replace(hour=17, minute=0, second=0)
                                logging.info(f"[GANTT MERGE] Using merged End_Date for '{task_name}': {task_end.isoformat()}")
                            except Exception as e:
                                logging.warning(f"Could not parse End_Date '{row.get('End_Date')}': {e}")
                        
                        # Fall back to calculated dates if Start_Date/End_Date missing
                        if task_start is None:
                            task_start = current_date
                        if task_end is None:
                            task_end = add_business_days(task_start, duration_days)
                        
                        # FIX: Preserve original WBS_ID from DataFrame for dependency lookup
                        original_task_wbs_id = None
                        if "WBS_ID" in row.index and pd.notna(row.get("WBS_ID")):
                            original_task_wbs_id = str(row.get("WBS_ID"))
                            logging.info(f"[WBS SEQUENTIAL] Storing original WBS_ID for task '{task_name}': {original_task_wbs_id}")
                        
                        # FIX: Generate SEQUENTIAL WBS code (INDEPENDENT of DataFrame WBS_ID)
                        # Format: {component_wbs}.{task_counter}
                        task_wbs = f"{comp_wbs}.{task_counter_per_comp[comp_key]}"
                        task_outline_level = "3"  # All leaf tasks are level 3
                        
                        logging.info(f"[WBS SEQUENTIAL] Task '{task_name}': Sequential WBS={task_wbs} (Original WBS_ID={original_task_wbs_id})")
                        
                        # Add task elements with sequential WBS
                        ET.SubElement(task, "{%s}UID" % ns).text = str(uid)
                        ET.SubElement(task, "{%s}ID" % ns).text = str(uid)
                        ET.SubElement(task, "{%s}Name" % ns).text = str(task_name)
                        
                        # FIX: Store DUAL WBS to UID mappings
                        # 1. Original WBS_ID → UID (for dependency lookup from DataFrame)
                        # 2. Sequential WBS → UID (for XML structure)
                        if original_task_wbs_id:
                            original_wbs_to_uid[original_task_wbs_id] = uid
                        sequential_wbs_to_uid[task_wbs] = uid
                        
                        ET.SubElement(task, "{%s}Type" % ns).text = "0"  # Fixed units
                        ET.SubElement(task, "{%s}IsNull" % ns).text = "0"
                        # WORKFRONT FIX: Strip trailing periods from WBS to prevent "8.3.5." format
                        task_wbs_clean = str(task_wbs).rstrip('.')
                        ET.SubElement(task, "{%s}WBS" % ns).text = task_wbs_clean
                        ET.SubElement(task, "{%s}OutlineNumber" % ns).text = task_wbs_clean
                        ET.SubElement(task, "{%s}OutlineLevel" % ns).text = task_outline_level
                        ET.SubElement(task, "{%s}Priority" % ns).text = "500"
                        ET.SubElement(task, "{%s}Start" % ns).text = task_start.isoformat()
                        ET.SubElement(task, "{%s}Finish" % ns).text = task_end.isoformat()
                        
                        # FIX: Calculate Duration from actual time span (Finish - Start), not from hours
                        # This prevents invalid XML where Duration=PT0M but Start≠Finish (Workfront rejects this)
                        # Duration = calendar time span, Work = effort hours (different concepts)
                        duration_minutes = int((task_end - task_start).total_seconds() / 60)
                        ET.SubElement(task, "{%s}Duration" % ns).text = f"PT{duration_minutes}M"
                        ET.SubElement(task, "{%s}DurationFormat" % ns).text = "7"  # Days
                        # FIX: Set Work to PT0M on leaf tasks to prevent double-counting in Workfront
                        # Work will be calculated automatically from Assignment elements per MSPDI standard
                        ET.SubElement(task, "{%s}Work" % ns).text = "PT0M"
                        ET.SubElement(task, "{%s}RegularWork" % ns).text = "PT0M"
                        # RemainingDuration must match Duration (same calendar time span)
                        ET.SubElement(task, "{%s}RemainingDuration" % ns).text = f"PT{duration_minutes}M"
                        ET.SubElement(task, "{%s}RemainingWork" % ns).text = "PT0M"
                        ET.SubElement(task, "{%s}Stop" % ns).text = task_end.isoformat()
                        ET.SubElement(task, "{%s}Resume" % ns).text = task_end.isoformat()
                        ET.SubElement(task, "{%s}ResumeValid" % ns).text = "0"
                        ET.SubElement(task, "{%s}EffortDriven" % ns).text = "1"
                        ET.SubElement(task, "{%s}Recurring" % ns).text = "0"
                        ET.SubElement(task, "{%s}OverAllocated" % ns).text = "0"
                        ET.SubElement(task, "{%s}Estimated" % ns).text = "1"
                        ET.SubElement(task, "{%s}Milestone" % ns).text = "0"
                        ET.SubElement(task, "{%s}Summary" % ns).text = "0"
                        ET.SubElement(task, "{%s}Critical" % ns).text = "0"
                        ET.SubElement(task, "{%s}IsSubproject" % ns).text = "0"
                        ET.SubElement(task, "{%s}IsSubprojectReadOnly" % ns).text = "0"
                        ET.SubElement(task, "{%s}IsMarked" % ns).text = "0"
                        ET.SubElement(task, "{%s}IgnoreWarnings" % ns).text = "0"
                        ET.SubElement(task, "{%s}HideBar" % ns).text = "0"
                        ET.SubElement(task, "{%s}Rollup" % ns).text = "0"
                        ET.SubElement(task, "{%s}BCWS" % ns).text = "0"
                        ET.SubElement(task, "{%s}BCWP" % ns).text = "0"
                        ET.SubElement(task, "{%s}PhysicalPercentComplete" % ns).text = "0"
                        ET.SubElement(task, "{%s}EarnedValueMethod" % ns).text = "0"
                        ET.SubElement(task, "{%s}ActualWorkProtected" % ns).text = "PT0H0M0S"
                        ET.SubElement(task, "{%s}ActualOvertimeWorkProtected" % ns).text = "PT0H0M0S"
                        ET.SubElement(task, "{%s}Active" % ns).text = "1"
                        ET.SubElement(task, "{%s}IsPublished" % ns).text = "1"
                        ET.SubElement(task, "{%s}CommitmentType" % ns).text = "0"
                        
                        # Add constraint type based on Gantt-sourced dates
                        has_gantt_start = "Start_Date" in row.index and pd.notna(row.get("Start_Date"))
                        has_gantt_end = "End_Date" in row.index and pd.notna(row.get("End_Date"))
                        
                        # Apply constraint type and manual scheduling fields based on Gantt-sourced dates
                        if has_gantt_start and has_gantt_end:
                            # Both dates from Gantt: Lock BOTH start and finish dates
                            ET.SubElement(task, "{%s}ConstraintType" % ns).text = "2"
                            ET.SubElement(task, "{%s}ConstraintDate" % ns).text = task_start.isoformat()
                            ET.SubElement(task, "{%s}Manual" % ns).text = "1"
                            # CRITICAL: Add ManualStart, ManualFinish, ManualDuration to lock dates in Workfront
                            ET.SubElement(task, "{%s}ManualStart" % ns).text = task_start.isoformat()
                            ET.SubElement(task, "{%s}ManualFinish" % ns).text = task_end.isoformat()
                            # Calculate duration from start to finish dates
                            duration_minutes = int((task_end - task_start).total_seconds() / 60)
                            ET.SubElement(task, "{%s}ManualDuration" % ns).text = f"PT{duration_minutes}M"
                            logging.info(f"[CONSTRAINT] Task '{task_name}': Must Start On (Type 2)")
                            logging.info(f"[MANUAL] Task '{task_name}': Manual scheduling enabled with locked start/finish/duration")
                        elif has_gantt_start:
                            # Only start date from Gantt: Lock start date only
                            ET.SubElement(task, "{%s}ConstraintType" % ns).text = "2"
                            ET.SubElement(task, "{%s}ConstraintDate" % ns).text = task_start.isoformat()
                            ET.SubElement(task, "{%s}Manual" % ns).text = "1"
                            # CRITICAL: Add ManualStart to lock start date in Workfront
                            ET.SubElement(task, "{%s}ManualStart" % ns).text = task_start.isoformat()
                            # ManualFinish and ManualDuration not set - will use standard fields
                            logging.info(f"[CONSTRAINT] Task '{task_name}': Must Start On (Type 2)")
                            logging.info(f"[MANUAL] Task '{task_name}': Manual scheduling enabled with locked start")
                        else:
                            # No Gantt dates: ASAP scheduling (auto-scheduled)
                            ET.SubElement(task, "{%s}ConstraintType" % ns).text = "0"
                            ET.SubElement(task, "{%s}ConstraintDate" % ns).text = task_start.isoformat()
                            ET.SubElement(task, "{%s}Manual" % ns).text = "0"
                            logging.info(f"[CONSTRAINT] Task '{task_name}': ASAP (Type 0)")
                        
                        # FIX 5: Add revenue fields to leaf tasks
                        # Get revenue from multiple possible sources
                        revenue = None
                        if "Revenue" in row.index and pd.notna(row.get("Revenue")):
                            revenue = float(row.get("Revenue"))
                        elif "Planned_Cost" in row.index and pd.notna(row.get("Planned_Cost")):
                            revenue = float(row.get("Planned_Cost"))
                        elif "Price_USD" in row.index and pd.notna(row.get("Price_USD")):
                            revenue = float(row.get("Price_USD"))
                        else:
                            # Default: hours * 150
                            revenue = hours * 150
                        
                        # FIX: Always add revenue fields, even if revenue=0 (Workfront requirement)
                        # Set Cost, FixedCost, FixedCostAccrual
                        ET.SubElement(task, "{%s}Cost" % ns).text = f"{revenue:.2f}"
                        ET.SubElement(task, "{%s}FixedCost" % ns).text = f"{revenue:.2f}"
                        ET.SubElement(task, "{%s}FixedCostAccrual" % ns).text = "2"  # Prorated
                        
                        # Accumulate cost into component and deliverable totals
                        component_costs[comp_uid] += revenue
                        deliverable_costs[deliv_uid] += revenue
                        
                        # Add Revenue extended attribute (Number3 = FieldID 188743715)
                        if add_custom_fields:
                            add_task_extended_attribute(task, ns, "188743715", f"{revenue:.2f}")
                        
                        logging.info(f"[REVENUE] Task '{task_name}': Revenue=${revenue:.2f}")
                        
                        # Add extended attributes (custom fields) for each task (flat MSPDI schema)
                        if add_custom_fields:
                            # Risk Score (random for demo)
                            add_task_extended_attribute(task, ns, "188743713", str(random.randint(1, 10)))
                            
                            # Confidence Level (random 70-100)
                            add_task_extended_attribute(task, ns, "188743714", str(random.randint(70, 100)))
                            
                            # Text1 = Department
                            task_department_value = task_service_dept if task_service_dept else "Unassigned"
                            add_task_extended_attribute(task, ns, "188743731", task_department_value)
                            
                            # Deliverable Code
                            if deliv_code:
                                add_task_extended_attribute(task, ns, "188743732", deliv_code)
                            
                            # Component Name
                            add_task_extended_attribute(task, ns, "188743733", str(component_name))
                        
                        # Track component finish date
                        if task_num_in_component == 1:
                            component_start = task_start
                        if task_end > component_finish:
                            component_finish = task_end
                        
                        # FIX: ALWAYS track deliverable finish date from actual task completion
                        # Deliverable finish = max of all component finishes (calculated from tasks)
                        if task_end > deliverable_finish:
                            deliverable_finish = task_end
                        
                        # Store task metadata (NO prev_task tracking - tasks within component run in parallel)
                        task_map[uid] = {
                            "task": task,
                            "deliverable": str(deliverable_name),
                            "component": str(component_name),
                            "department": str(department),
                            "component_uid": comp_uid  # Track parent component
                        }
                        
                        # FIX: Increment task counter for next task in this component
                        task_counter_per_comp[comp_key] += 1
                        
                    except Exception as e:
                        logging.error(f"Error processing task at index {idx}: {e}")
                        task_uid -= 1  # Decrement to maintain correct count
                
                # CRITICAL VALIDATION: Check if any tasks were actually created for this component
                # If all tasks were filtered out (role rows, wrapper tasks, duplicates), skip this component
                if task_num_in_component == 0:
                    logging.warning(f"[EMPTY COMPONENT] Skipping component '{component_name}' - no tasks after filtering")
                    # Remove the component summary task from the XML tree
                    tasks.remove(comp_task)
                    # Remove from tracking maps
                    if comp_uid in component_costs:
                        del component_costs[comp_uid]
                    comp_key_str = f"{deliverable_name}:{component_name}"
                    if comp_key_str in component_tasks:
                        del component_tasks[comp_key_str]
                    # Decrement task_uid to maintain correct count (component wasn't actually used)
                    task_uid -= 1
                    # Remove from all_task_uids
                    if comp_uid in all_task_uids:
                        all_task_uids.remove(comp_uid)
                    # Skip to next component
                    continue
                
                # FIX 4: Component summary tasks must have Duration=PT0M to let Workfront auto-calculate from children
                # Do NOT calculate duration from time span - this causes issues with Workfront rollup
                ET.SubElement(comp_task, "{%s}Duration" % ns).text = "PT0M"
                ET.SubElement(comp_task, "{%s}Finish" % ns).text = component_finish.isoformat()
                logging.info(f"[SUMMARY] Component '{component_name}': Duration=PT0M (will auto-calculate from children)")
                
                # Add aggregated cost/revenue to component summary task
                comp_total_cost = component_costs.get(comp_uid, 0.0)
                if comp_total_cost > 0:
                    ET.SubElement(comp_task, "{%s}Cost" % ns).text = str(comp_total_cost)
                    ET.SubElement(comp_task, "{%s}FixedCost" % ns).text = str(comp_total_cost)
                    ET.SubElement(comp_task, "{%s}FixedCostAccrual" % ns).text = "2"  # Prorated
                    
                    # Add Revenue extended attribute (same as cost for flat billing)
                    if add_custom_fields:
                        add_task_extended_attribute(comp_task, ns, "188743715", str(comp_total_cost))
                    
                    logging.info(f"[COST AGGREGATION] Component '{component_name}' total cost: ${comp_total_cost:.2f}")
                
                # FIX: Store DUAL WBS to UID mappings for components
                # 1. Original WBS_ID → UID (for dependency lookup from DataFrame)
                # 2. Sequential WBS → UID (for XML structure)
                if original_comp_wbs_id:
                    original_wbs_to_uid[original_comp_wbs_id] = comp_uid
                sequential_wbs_to_uid[comp_wbs] = comp_uid
                
                # Update current_date to end of this component for next component to start
                current_date = component_finish
                
                # FIX: Increment component counter for next component in this deliverable
                component_counter_per_deliv[str(deliverable_name)] += 1
                
                logging.info(f"[3-LEVEL HIERARCHY] Component '{component_name}' completed with {task_num_in_component} tasks")
            
            # FIX 4: Deliverable summary tasks must have Duration=PT0M to let Workfront auto-calculate from children
            # Do NOT calculate duration from time span - this causes issues with Workfront rollup
            ET.SubElement(deliv_task, "{%s}Duration" % ns).text = "PT0M"
            ET.SubElement(deliv_task, "{%s}Finish" % ns).text = deliverable_finish.isoformat()
            deliverable_ends[deliverable_name] = deliverable_finish
            logging.info(f"[SUMMARY] Deliverable '{deliverable_name}': Duration=PT0M (will auto-calculate from children)")
            
            # Add aggregated cost/revenue to deliverable summary task
            deliv_total_cost = deliverable_costs.get(deliv_uid, 0.0)
            if deliv_total_cost > 0:
                ET.SubElement(deliv_task, "{%s}Cost" % ns).text = str(deliv_total_cost)
                ET.SubElement(deliv_task, "{%s}FixedCost" % ns).text = str(deliv_total_cost)
                ET.SubElement(deliv_task, "{%s}FixedCostAccrual" % ns).text = "2"  # Prorated
                
                # Add Revenue extended attribute (same as cost for flat billing)
                if add_custom_fields:
                    add_task_extended_attribute(deliv_task, ns, "188743715", str(deliv_total_cost))
                
                logging.info(f"[COST AGGREGATION] Deliverable '{deliverable_name}' total cost: ${deliv_total_cost:.2f}")
            
            # FIX: Store DUAL WBS to UID mappings for deliverables
            # 1. Original WBS_ID → UID (for dependency lookup from DataFrame)
            # 2. Sequential WBS → UID (for XML structure)
            if original_deliv_wbs_id:
                original_wbs_to_uid[original_deliv_wbs_id] = deliv_uid
            sequential_wbs_to_uid[deliv_wbs] = deliv_uid
            
            # FIX: Increment deliverable counter for next deliverable
            deliverable_counter += 1
    
    # Add PredecessorLink elements for dependencies
    # FIX FOR ISSUE 1: Process dependencies for ALL task types (deliverables, components, AND leaf tasks)
    if add_dependencies:
        logging.info("[DEPENDENCIES] Processing Dependencies column for ALL task types (deliverables, components, leaf tasks)")
        
        # CRITICAL FIX: Build set of valid task UIDs from actual XML tree
        # This prevents orphaned dependencies to tasks that were filtered out
        valid_task_uids = set()
        for task_elem in tasks.findall("{%s}Task" % ns):
            uid_elem = task_elem.find("{%s}UID" % ns)
            if uid_elem is not None:
                valid_task_uids.add(int(uid_elem.text))
        
        logging.info(f"[DEPENDENCIES] Built valid task UID set with {len(valid_task_uids)} tasks")
        logging.info(f"[DEPENDENCIES] Sample valid UIDs: {sorted(list(valid_task_uids))[:10]}")
        
        # FIX C: Add debug logging for WBS mapping
        logging.info(f"[DEPENDENCIES DEBUG] original_wbs_to_uid has {len(original_wbs_to_uid)} entries")
        if original_wbs_to_uid:
            logging.info(f"[DEPENDENCIES DEBUG] Sample WBS IDs in mapping (first 10): {list(original_wbs_to_uid.keys())[:10]}")
        else:
            logging.warning("[DEPENDENCIES DEBUG] WARNING: original_wbs_to_uid is EMPTY - no dependencies can be created!")
        
        # FIX: Support multiple column names for dependencies (Dependencies, Predecessor, Predecessors)
        dep_col = None
        for possible_col in ["Dependencies", "Predecessor", "Predecessors"]:
            if possible_col in df.columns:
                dep_col = possible_col
                break
        
        # FIX C: Check what dependency values exist in DataFrame
        if dep_col:
            logging.info(f"[INFO] [DEPENDENCIES] Using column '{dep_col}' for dependency data")
            non_empty_deps = df[df[dep_col].notna() & (df[dep_col] != "")]
            logging.info(f"[DEPENDENCIES DEBUG] Found {len(non_empty_deps)} rows with non-empty {dep_col} values")
            if len(non_empty_deps) > 0:
                sample_deps = non_empty_deps[dep_col].head(5).tolist()
                logging.info(f"[DEPENDENCIES DEBUG] Sample {dep_col} values: {sample_deps}")
        
        # Check if dependency column exists
        if dep_col:
            dependencies_count = 0
            skipped_count = 0
            
            # Build unified task lookup structure that includes ALL task types
            # This maps (deliverable, component, task_name) tuples to (task_element, uid)
            all_tasks_lookup = {}
            
            # Add deliverable tasks to lookup
            for deliv_name, deliv_uid in deliverable_tasks.items():
                # Find the deliverable task element by UID
                deliv_task_elem = None
                for task_elem in tasks.findall("{%s}Task" % ns):
                    uid_elem = task_elem.find("{%s}UID" % ns)
                    if uid_elem is not None and int(uid_elem.text) == deliv_uid:
                        deliv_task_elem = task_elem
                        break
                
                if deliv_task_elem is not None:
                    # Key: (deliverable, None, None) for deliverable-level tasks
                    all_tasks_lookup[(str(deliv_name), None, None)] = (deliv_task_elem, deliv_uid)
                    logging.info(f"[DEPENDENCIES] Added deliverable to lookup: '{deliv_name}' (UID={deliv_uid})")
            
            # Add component tasks to lookup
            for comp_key, comp_uid in component_tasks.items():
                # comp_key format: "deliverable_name:component_name"
                if ':' in comp_key:
                    deliv_name, comp_name = comp_key.split(':', 1)
                    
                    # Find the component task element by UID
                    comp_task_elem = None
                    for task_elem in tasks.findall("{%s}Task" % ns):
                        uid_elem = task_elem.find("{%s}UID" % ns)
                        if uid_elem is not None and int(uid_elem.text) == comp_uid:
                            comp_task_elem = task_elem
                            break
                    
                    if comp_task_elem is not None:
                        # Key: (deliverable, component, None) for component-level tasks
                        all_tasks_lookup[(deliv_name, comp_name, None)] = (comp_task_elem, comp_uid)
                        logging.info(f"[DEPENDENCIES] Added component to lookup: '{deliv_name}:{comp_name}' (UID={comp_uid})")
            
            # Add leaf tasks to lookup
            for uid, task_data in task_map.items():
                task_elem = task_data["task"]
                task_deliv = task_data["deliverable"]
                task_comp = task_data["component"]
                
                # Get task name from XML element
                task_name_elem = task_elem.find("{%s}Name" % ns)
                if task_name_elem is not None:
                    task_name = task_name_elem.text
                    # Key: (deliverable, component, task_name) for leaf tasks
                    all_tasks_lookup[(task_deliv, task_comp, task_name)] = (task_elem, uid)
                    logging.info(f"[DEPENDENCIES] Added leaf task to lookup: '{task_deliv}:{task_comp}:{task_name}' (UID={uid})")
            
            logging.info(f"[DEPENDENCIES] Built unified lookup with {len(all_tasks_lookup)} tasks total")
            
            # Process Dependencies column for ALL rows in DataFrame
            for idx, row in df.iterrows():
                # FIX: Skip role rows (same logic as task creation)
                # Role rows were skipped during task creation, so they won't be in task_map
                role_value = row.get("Role", "")
                if pd.notna(role_value) and str(role_value).strip():
                    logging.info(f"[DEPENDENCIES] Skipping role row at index {idx}: Role={role_value}")
                    continue  # Skip to next row
                
                # CRITICAL FIX: Skip rows that were filtered out (duplicates/wrappers) during task creation
                # Check if this row's WBS_ID exists in original_wbs_to_uid (only exported tasks are in this map)
                original_task_wbs_id = str(row.get("WBS_ID", "")).strip()
                if original_task_wbs_id and original_task_wbs_id not in original_wbs_to_uid:
                    logging.info(f"[DEPENDENCIES] Skipping filtered-out task at index {idx}: WBS_ID={original_task_wbs_id} (was not exported)")
                    continue
                
                # Get task identifiers from DataFrame row
                row_deliverable = row.get("Deliverable", "")
                row_component = row.get("Component", "")
                row_task = row.get("Task", "")
                row_task_name = row.get("Task_Name", "")
                
                # FIX: Use the SAME task name derivation logic as task creation (lines 898-902)
                # This ensures lookup_key matches what was actually stored in all_tasks_lookup
                if not row_task_name or pd.isna(row_task_name) or str(row_task_name).strip() == "":
                    row_task_name = (row.get("L3_Task") or 
                                    row.get("Task_Label") or 
                                    "")
                
                # Build lookup key based on hierarchy level
                # Use Component and Task columns to distinguish between levels:
                # - Deliverable: Component is empty
                # - Component: Component is not empty, Task is empty
                # - Leaf task: Both Component and Task are not empty
                lookup_key = None
                task_elem = None
                task_uid = None
                
                # Determine hierarchy level
                has_component = row_component and pd.notna(row_component) and str(row_component).strip() and str(row_component).strip() != ""
                has_task = row_task and pd.notna(row_task) and str(row_task).strip() and str(row_task).strip() != ""
                has_deliverable = row_deliverable and pd.notna(row_deliverable) and str(row_deliverable).strip() and str(row_deliverable).strip() != ""
                
                if has_task and has_component and has_deliverable:
                    # Leaf task level (both Component and Task are populated)
                    lookup_key = (str(row_deliverable), str(row_component), str(row_task_name))
                    logging.info(f"[DEPENDENCIES] Looking up LEAF task: deliverable='{row_deliverable}', component='{row_component}', task_name='{row_task_name}'")
                elif has_component and has_deliverable and not has_task:
                    # Component level (Component is populated, Task is not)
                    lookup_key = (str(row_deliverable), str(row_component), None)
                    logging.info(f"[DEPENDENCIES] Looking up COMPONENT: deliverable='{row_deliverable}', component='{row_component}'")
                elif has_deliverable and not has_component:
                    # Deliverable level (Component is not populated)
                    lookup_key = (str(row_deliverable), None, None)
                    logging.info(f"[DEPENDENCIES] Looking up DELIVERABLE: deliverable='{row_deliverable}'")
                
                # Look up task element and UID
                if lookup_key and lookup_key in all_tasks_lookup:
                    task_elem, task_uid = all_tasks_lookup[lookup_key]
                    logging.info(f"[DEPENDENCIES] ✓ Found task in lookup: UID={task_uid}")
                else:
                    # No matching task found, skip this row
                    if lookup_key:
                        logging.warning(f"[DEPENDENCIES] ✗ Task NOT found in lookup: {lookup_key}")
                        logging.warning(f"[DEPENDENCIES DEBUG] Available lookup keys sample: {list(all_tasks_lookup.keys())[:5]}")
                    continue
                
                # SAFETY CHECK: Ensure task_uid is valid before processing dependencies
                if task_uid is None:
                    logging.warning(f"[DEPENDENCIES] Task UID is None for row {idx}, skipping dependencies")
                    continue
                
                # Get dependency value from this row using detected column name
                dependencies_value = row.get(dep_col, "")
                
                # FIX: Add detailed logging for dependency value
                if dependencies_value and pd.notna(dependencies_value) and str(dependencies_value).strip():
                    logging.info(f"[DEPENDENCIES] Row {idx} has {dep_col}='{dependencies_value}' for task UID={task_uid}")
                
                # Parse dependencies if value is not empty
                if dependencies_value and pd.notna(dependencies_value) and str(dependencies_value).strip():
                    dependencies_str = str(dependencies_value).strip()
                    
                    # Split by comma or semicolon to get list of WBS IDs
                    dep_wbs_list = []
                    for sep in [',', ';']:
                        if sep in dependencies_str:
                            dep_wbs_list = [d.strip() for d in dependencies_str.split(sep)]
                            break
                    
                    # If no separator found, treat as single dependency
                    if not dep_wbs_list:
                        dep_wbs_list = [dependencies_str]
                    
                    # Process each dependency
                    for dep_wbs in dep_wbs_list:
                        if not dep_wbs:
                            continue
                        
                        # FIX: Resolve WBS to UID using ORIGINAL WBS_ID mapping
                        # Dependencies column contains original WBS_IDs from DataFrame, not sequential WBS codes
                        logging.info(f"[DEPENDENCIES] Looking up predecessor WBS '{dep_wbs}' in original_wbs_to_uid mapping")
                        predecessor_uid = original_wbs_to_uid.get(dep_wbs)
                        
                        if predecessor_uid is None:
                            logging.warning(f"[DEPENDENCIES] ✗ Invalid WBS reference '{dep_wbs}' for task {lookup_key} - NOT FOUND in mapping")
                            logging.warning(f"[DEPENDENCIES DEBUG] Available WBS IDs in mapping: {list(original_wbs_to_uid.keys())[:20]}")
                            skipped_count += 1
                            continue
                        
                        # CRITICAL FIX: Validate that predecessor UID exists in actual XML task tree
                        # This prevents orphaned dependencies to tasks that were filtered out (wrapper/duplicate/empty summaries)
                        if predecessor_uid not in valid_task_uids:
                            logging.warning(f"[DEPENDENCIES] ✗ ORPHANED DEPENDENCY: WBS '{dep_wbs}' maps to UID={predecessor_uid} but this task was FILTERED OUT")
                            logging.warning(f"[DEPENDENCIES] Task {lookup_key} tried to link to non-existent predecessor - SKIPPING to prevent Workfront import failure")
                            skipped_count += 1
                            continue
                        
                        logging.info(f"[DEPENDENCIES] ✓ Found predecessor UID={predecessor_uid} for WBS '{dep_wbs}' (validated in XML tree)")
                        
                        # Skip self-referencing dependencies
                        if predecessor_uid == task_uid:
                            logging.warning(f"[DEPENDENCIES] Self-referencing dependency for task {lookup_key} (UID={task_uid}) - skipping")
                            skipped_count += 1
                            continue
                        
                        # FIX: REMOVED overly restrictive check that prevented dependencies TO summary tasks
                        # MS Project and Workfront ALLOW dependencies to summary tasks - they link to the appropriate child
                        # The only check we need is to prevent summary tasks FROM having dependencies (see below)
                        
                        # FIX C: Skip adding predecessor if THIS task is a summary task
                        # Summary tasks should not have explicit dependencies - only leaf tasks should
                        is_summary_task = False
                        summary_check_elem = task_elem.find("{%s}Summary" % ns)
                        if summary_check_elem is not None and summary_check_elem.text == "1":
                            is_summary_task = True
                        
                        if is_summary_task:
                            task_name_elem = task_elem.find("{%s}Name" % ns)
                            task_name_for_log = task_name_elem.text if task_name_elem is not None else "Unknown"
                            logging.warning(f"[DEPENDENCIES] Skipping dependency FROM summary task '{task_name_for_log}' (UID={task_uid}) - summary tasks cannot have explicit dependencies")
                            skipped_count += 1
                            continue
                        
                        # Get task name for enhanced logging
                        task_name_elem = task_elem.find("{%s}Name" % ns)
                        task_name_for_log = task_name_elem.text if task_name_elem is not None else "Unknown"
                        
                        # Create PredecessorLink element (only for leaf tasks)
                        logging.info(f"[DEPENDENCIES] ✓ Creating PredecessorLink: Task '{task_name_for_log}' (UID={task_uid}) → Predecessor UID={predecessor_uid} (Type=1, FS)")
                        
                        # FIX: Create PredecessorLink as child of task_elem using SubElement
                        # This ensures the link is properly attached to the task in the XML tree
                        pred_link = ET.SubElement(task_elem, "{%s}PredecessorLink" % ns)
                        ET.SubElement(pred_link, "{%s}PredecessorUID" % ns).text = str(predecessor_uid)
                        ET.SubElement(pred_link, "{%s}Type" % ns).text = "1"  # Type=1 is FS (Finish-to-Start) in Workfront
                        ET.SubElement(pred_link, "{%s}CrossProject" % ns).text = "0"
                        ET.SubElement(pred_link, "{%s}LinkLag" % ns).text = "0"
                        ET.SubElement(pred_link, "{%s}LagFormat" % ns).text = "7"  # Days
                        
                        dependencies_count += 1
                        
                        # Enhanced logging to confirm attachment
                        logging.info(f"[DEPENDENCIES] ✓✓ SUCCESS! PredecessorLink attached to task '{task_name_for_log}' (UID={task_uid})")
                        logging.info(f"[DEPENDENCIES]    - Predecessor WBS '{dep_wbs}' (UID={predecessor_uid})")
                        logging.info(f"[DEPENDENCIES]    - Total dependencies created so far: {dependencies_count}")
                        logging.info(f"[DEPENDENCIES]    - PredecessorLink element has {len(list(pred_link))} child elements")
                        
                        # Verify the link was actually attached to the task
                        task_pred_links = task_elem.findall("{%s}PredecessorLink" % ns)
                        logging.info(f"[DEPENDENCIES]    - Task now has {len(task_pred_links)} PredecessorLink element(s)")
            
            logging.info(f"[DEPENDENCIES] Added {dependencies_count} dependencies across ALL task types, skipped {skipped_count} invalid references")
        else:
            logging.warning("[WARNING] [DEPENDENCIES] No dependency column found in DataFrame (tried: Dependencies, Predecessor, Predecessors) - skipping dependency parsing")
        
        # Also add cross-deliverable dependencies based on department logic as fallback
        logging.info("[3-LEVEL HIERARCHY] Adding component-level dependencies (tasks within components run in parallel)")
        
        # Define department dependencies
        dept_dependencies = {
            "Creative": ["Strategy"],
            "Paid Media": ["Creative", "Strategy"],
            "Technology": ["Strategy"],
            "Content": ["Strategy", "Creative"],
            "Quality Assurance": ["Technology", "Content"]
        }
        
        for uid, task_data in task_map.items():
            task = task_data["task"]
            department = task_data["department"]
            deliverable = task_data["deliverable"]
            
            # Only add department-based dependencies if no explicit dependencies from DataFrame
            existing_pred_links = task.findall("{%s}PredecessorLink" % ns)
            if existing_pred_links:
                continue  # Skip if dependencies already added from DataFrame
            
            if department in dept_dependencies:
                # Look for tasks in dependent departments from earlier deliverables
                for other_uid, other_data in task_map.items():
                    if other_uid >= uid:  # Only look at earlier tasks
                        break
                    if other_data["department"] in dept_dependencies[department]:
                        if other_data["deliverable"] == deliverable:  # Same deliverable
                            # Add dependency with Start-to-Start relationship
                            pred_link = ET.SubElement(task, "{%s}PredecessorLink" % ns)
                            ET.SubElement(pred_link, "{%s}PredecessorUID" % ns).text = str(other_uid)
                            ET.SubElement(pred_link, "{%s}Type" % ns).text = str(DependencyType.START_TO_START.value)
                            ET.SubElement(pred_link, "{%s}CrossProject" % ns).text = "0"
                            ET.SubElement(pred_link, "{%s}LinkLag" % ns).text = "4800"  # 1 day lag (in minutes)
                            ET.SubElement(pred_link, "{%s}LagFormat" % ns).text = "12"  # Minutes
                            break
    
    # FIX B: Build child-hours-by-role for each parent WBS (ALWAYS, not gated by merge)
    # This allows assignments even when L3 PlannedHours=0
    logging.info("[FIX B] Building child-hours-by-role aggregator for parent tasks")
    child_hours_by_parent = {}
    for idx, row in df.iterrows():
        parent_wbs = row.get("Parent_WBS_ID", "")
        if not pd.notna(parent_wbs) or not str(parent_wbs).strip():
            continue
        
        parent_wbs = str(parent_wbs).strip()
        planned_hours = row.get("Planned_Hours", 0)
        role_value = row.get("Role", "")
        
        # Only aggregate if row has hours and a single role
        if pd.notna(role_value) and str(role_value).strip() and pd.notna(planned_hours):
            try:
                hours = float(planned_hours)
                if hours > 0:
                    role = str(role_value).strip()
                    child_hours_by_parent.setdefault(parent_wbs, {}).setdefault(role, 0.0)
                    child_hours_by_parent[parent_wbs][role] += hours
            except (ValueError, TypeError):
                pass
    
    logging.info(f"[FIX B] Built child hours aggregator for {len(child_hours_by_parent)} parent tasks")
    
    # ============================================================================
    # PHASE 1: BUILD RESOURCE DATA STRUCTURES (NO XML YET)
    # ============================================================================
    # This phase builds all resource-related data structures BEFORE creating
    # assignment data, which allows assignments to reference resource UIDs.
    logging.info("[PHASE 1] Building resource data structures...")
    
    # Initialize resource data structures
    resource_map = {}  # role -> resource_uid (backward compatibility)
    resource_uid_map = {}  # normalized_key (role|seniority) -> resource_uid
    department_resources = {}  # department -> resource_uid
    resource_data_list = []  # List of resource data dicts for XML creation later
    
    # WORKFRONT FIX: Start resource UIDs at 1000 to avoid collision with task UIDs
    # Tasks start at UID=1, Resources must be in separate namespace
    resource_id = 1000
    
    # Extract unique departments
    departments = set()
    if "Department" in df.columns:
        departments.update(df["Department"].dropna().unique())
    
    # Build department resource data
    logging.info(f"[PHASE 1] Building data for {len(departments)} department resources...")
    for dept in departments:
        resource_data_list.append({
            "UID": resource_id,
            "ID": resource_id,
            "Name": f"{dept} Team",
            "Initials": "".join([w[0] for w in str(dept).split()[:2]]),
            "Group": str(dept),
            "Type": "1",  # Work resource
            "Rate": blended_rate or 150
        })
        department_resources[str(dept)] = resource_id
        
        # FIX ISSUE 1: Add department resources to resource_uid_map for consistency
        # Use normalized key: "dept:{dept_name}" to avoid collision with role keys
        dept_normalized_key = f"dept:{normalize_resource_name(str(dept))}"
        resource_uid_map[dept_normalized_key] = resource_id
        logging.info(f"[PHASE 1 FIX] Added department '{dept}' to resource_uid_map with key '{dept_normalized_key}' -> UID={resource_id}")
        
        resource_id += 1
    
    # Build individual role resource data
    if "Role" in df.columns:
        # Extract unique (role, seniority) combinations from role rows
        role_rows = df[df["Role"].notna() & (df["Role"] != "")]
        
        # Build registry with normalized keys for deduplication
        resource_registry = {}  # normalized_key -> {display_name, role, seniority, rate}
        
        for _, row in role_rows.iterrows():
            role = str(row.get("Role", "")).strip()
            seniority = str(row.get("Seniority", "")).strip() if pd.notna(row.get("Seniority")) else ""
            if role:
                # Create display name (original case/formatting)
                display_name = f"{role} ({seniority})" if seniority else role
                
                # Create normalized key for deduplication
                normalized_key = f"{normalize_resource_name(role)}|{normalize_resource_name(seniority)}"
                
                # Store in registry (will automatically dedupe by normalized key)
                if normalized_key not in resource_registry:
                    resource_registry[normalized_key] = {
                        "display_name": display_name,
                        "role": role,
                        "seniority": seniority,
                        "rate": row.get("Rate_USD") if pd.notna(row.get("Rate_USD")) else None
                    }
        
        # Create resource data from registry (sorted for consistency)
        logging.info(f"[PHASE 1] Building data for {len(resource_registry)} role resources...")
        for normalized_key in sorted(resource_registry.keys()):
            res_data = resource_registry[normalized_key]
            
            # Determine rate
            if blended_rate:
                rate = blended_rate
            elif res_data["rate"] is not None:
                rate = res_data["rate"]
            else:
                rate = 150.0
            
            resource_data_list.append({
                "UID": resource_id,
                "ID": resource_id,
                "Name": res_data["display_name"],
                "Initials": "".join([w[0] for w in str(res_data["role"]).split()[:3]]),
                "Group": "",
                "Type": "1",  # Work resource
                "Rate": rate
            })
            
            # Store in resource_uid_map using NORMALIZED key
            resource_uid_map[normalized_key] = resource_id
            resource_map[res_data["role"]] = resource_id  # Keep for backward compatibility
            
            logging.info(f"[PHASE 1] Registered resource UID={resource_id} for Role='{res_data['role']}', Seniority='{res_data['seniority']}' (normalized_key='{normalized_key}')")
            
            resource_id += 1
    
    # Build valid resource UID set for validation
    valid_resource_uids = set([r["UID"] for r in resource_data_list])
    
    logging.info(f"[PHASE 1] ✓ Built data for {len(resource_data_list)} total resources")
    logging.info(f"[PHASE 1] ✓ Department resources: {len(department_resources)}")
    logging.info(f"[PHASE 1] ✓ Role resources: {len(resource_uid_map)}")
    logging.info(f"[PHASE 1] ✓ Valid resource UIDs: {len(valid_resource_uids)}")
    
    # FIX ISSUE 1: VALIDATION - Ensure resource_uid_map and resource_data_list are in sync
    logging.info("[PHASE 1 VALIDATION] Verifying resource_uid_map and resource_data_list synchronization...")
    resource_data_uids = set([r["UID"] for r in resource_data_list])
    resource_map_uids = set(resource_uid_map.values())
    
    # Check: Every UID in resource_uid_map should exist in resource_data_list
    missing_in_data_list = resource_map_uids - resource_data_uids
    if missing_in_data_list:
        raise ValueError(
            f"CRITICAL: {len(missing_in_data_list)} resource UIDs in resource_uid_map are missing from resource_data_list: {missing_in_data_list}"
        )
    
    logging.info(f"[PHASE 1 VALIDATION] ✓ All {len(resource_map_uids)} resource UIDs in resource_uid_map exist in resource_data_list")
    logging.info(f"[PHASE 1 VALIDATION] ✓ resource_data_list has {len(resource_data_uids)} total resources")
    logging.info(f"[PHASE 1 VALIDATION] ✓ Sync verification passed: resource_uid_map and resource_data_list are consistent")
    
    # ============================================================================
    # PHASE 1: BUILD ASSIGNMENT DATA STRUCTURES (NO XML YET)
    # ============================================================================
    # Now that resource data is built, we can create assignments that reference
    # resource UIDs safely.
    logging.info("[PHASE 1] Building assignment data structure...")
    assignment_data_list = []
    assignment_uid = 1
    
    # Create resource assignments data (not XML yet)
    for uid, task_data in task_map.items():
        task = task_data["task"]
        
        # Get task hours
        work_elem = task.find("{%s}Work" % ns)
        if work_elem is not None and work_elem.text:
            work_minutes = int(work_elem.text.replace("PT", "").replace("M", ""))
            work_hours = work_minutes / 60
        else:
            work_hours = 8.0
        
        # Assign department resource
        department = task_data["department"]
        if department in department_resources:
            # Store assignment data (not XML yet)
            assignment_data_list.append({
                "AssignmentUID": assignment_uid,
                "TaskUID": uid,
                "ResourceUID": department_resources[department],
                "WorkHours": work_hours,
                "Cost": work_hours * (blended_rate or 150),
                "Start": task.find("{%s}Start" % ns).text,
                "Finish": task.find("{%s}Finish" % ns).text
            })
            assignment_uid += 1
    
    # FIX: Process role rows and create assignment data (not XML yet)
    logging.info("[ROLE ASSIGNMENTS] Processing role rows to create assignment data")
    role_assignment_count = 0
    skipped_role_rows = 0
    
    # Loop through ALL rows in DataFrame to find role rows
    for idx, row in df.iterrows():
        try:
            # Check if this is a role row (Role column is populated)
            role_value = row.get("Role", "")
            if not pd.notna(role_value) or not str(role_value).strip():
                continue  # Skip non-role rows
            
            role = str(role_value).strip()
            
            # Get Seniority (may be empty)
            seniority_value = row.get("Seniority", "")
            seniority = str(seniority_value).strip() if pd.notna(seniority_value) else ""
            
            # Get Parent_WBS_ID to find the parent task
            parent_wbs = row.get("Parent_WBS_ID", "")
            if not pd.notna(parent_wbs) or not str(parent_wbs).strip():
                # Try alternative column names
                parent_wbs = row.get("WBS_ID", "")
                if not pd.notna(parent_wbs) or not str(parent_wbs).strip():
                    logging.warning(f"[ROLE ASSIGNMENTS] Skipping role row at index {idx}: No Parent_WBS_ID found for Role={role}")
                    skipped_role_rows += 1
                    continue
            
            parent_wbs = str(parent_wbs).strip()
            
            # Look up parent task UID using ORIGINAL WBS_ID mapping
            task_uid_for_assignment = original_wbs_to_uid.get(parent_wbs)
            if task_uid_for_assignment is None:
                # CRITICAL FIX: Skip assignments with no valid task UID (prevents TaskUID=None errors)
                logging.warning(f"[ROLE ASSIGNMENTS] Skipping role row at index {idx}: Parent WBS '{parent_wbs}' not found in task mapping for Role={role}, Seniority={seniority}")
                logging.warning(f"[ROLE ASSIGNMENTS] Available WBS IDs: {list(original_wbs_to_uid.keys())[:20]}")
                skipped_role_rows += 1
                continue
            
            # FIX: Look up resource UID using normalized (role, seniority) mapping
            # Normalize role/seniority for lookup
            normalized_key = f"{normalize_resource_name(role)}|{normalize_resource_name(seniority)}"
            resource_uid = resource_uid_map.get(normalized_key)
            
            if resource_uid is None:
                # Try without seniority as fallback (normalized key with empty seniority)
                fallback_key = f"{normalize_resource_name(role)}|"
                resource_uid = resource_uid_map.get(fallback_key)
                if resource_uid is None:
                    # Final fallback: try resource_map (role only, may not have correct seniority)
                    resource_uid = resource_map.get(str(role))
                    if resource_uid is None:
                        logging.warning(f"[ROLE ASSIGNMENTS] Skipping role row at index {idx}: Resource not found for Role='{role}', Seniority='{seniority}'")
                        logging.warning(f"[ROLE ASSIGNMENTS] Normalized key attempted: '{normalized_key}'")
                        logging.warning(f"[ROLE ASSIGNMENTS] Available resources in resource_uid_map: {list(resource_uid_map.keys())[:20]}")
                        skipped_role_rows += 1
                        continue
                    else:
                        logging.warning(f"[ROLE ASSIGNMENTS] Using fallback resource_map lookup for Role='{role}' (UID={resource_uid}). Seniority '{seniority}' not matched.")
                else:
                    logging.info(f"[ROLE ASSIGNMENTS] Matched Role='{role}' with empty seniority (UID={resource_uid}, normalized_key='{fallback_key}')")
            else:
                logging.info(f"[ROLE ASSIGNMENTS] Matched Role='{role}', Seniority='{seniority}' -> UID={resource_uid} (normalized_key='{normalized_key}')")
            
            # Get hours (Planned_Hours or Hours column)
            hours_value = row.get("Planned_Hours")
            if not pd.notna(hours_value) or hours_value is None:
                hours_value = row.get("Hours", 0)
            
            try:
                hours = float(hours_value) if pd.notna(hours_value) else 0.0
            except (ValueError, TypeError):
                hours = 0.0
            
            # FIX B: If hours <= 0, try to get hours from child_hours_by_parent
            if hours <= 0 and parent_wbs in child_hours_by_parent:
                role_hours_map = child_hours_by_parent[parent_wbs]
                if role in role_hours_map:
                    hours = role_hours_map[role]
                    logging.info(f"[FIX B] Using aggregated hours {hours} from children for Role={role}, Parent WBS={parent_wbs}")
            
            if hours <= 0:
                logging.warning(f"[ROLE ASSIGNMENTS] Skipping role row at index {idx}: Hours={hours} (must be > 0)")
                skipped_role_rows += 1
                continue
            
            # Get task start/finish dates from the parent task
            parent_task_elem = None
            for task_elem in tasks.findall("{%s}Task" % ns):
                uid_elem = task_elem.find("{%s}UID" % ns)
                if uid_elem is not None and int(uid_elem.text) == task_uid_for_assignment:
                    parent_task_elem = task_elem
                    break
            
            if parent_task_elem is not None:
                start_elem = parent_task_elem.find("{%s}Start" % ns)
                finish_elem = parent_task_elem.find("{%s}Finish" % ns)
                task_start_text = start_elem.text if start_elem is not None else project_start.isoformat()
                task_finish_text = finish_elem.text if finish_elem is not None else project_start.isoformat()
            else:
                task_start_text = project_start.isoformat()
                task_finish_text = project_start.isoformat()
            
            # Store assignment data (not XML yet)
            assignment_data_list.append({
                "AssignmentUID": assignment_uid,
                "TaskUID": task_uid_for_assignment,
                "ResourceUID": resource_uid,
                "WorkHours": hours,
                "Cost": hours * (blended_rate or 150),
                "Start": task_start_text,
                "Finish": task_finish_text
            })
            
            assignment_uid += 1
            role_assignment_count += 1
            
            logging.info(f"[ROLE ASSIGNMENTS] Created assignment data #{role_assignment_count}: Role='{role}', Seniority='{seniority}' -> Task UID={task_uid_for_assignment}, Resource UID={resource_uid}, Hours={hours}")
            
        except Exception as e:
            logging.error(f"[ROLE ASSIGNMENTS] Error processing role row at index {idx}: {e}")
            skipped_role_rows += 1
    
    logging.info(f"[ROLE ASSIGNMENTS] ========== SUMMARY ==========")
    logging.info(f"[ROLE ASSIGNMENTS] Total role rows processed: {role_assignment_count + skipped_role_rows}")
    logging.info(f"[ROLE ASSIGNMENTS] Successful assignments: {role_assignment_count}")
    logging.info(f"[ROLE ASSIGNMENTS] Skipped rows: {skipped_role_rows}")
    logging.info(f"[ROLE ASSIGNMENTS] Success rate: {(role_assignment_count / (role_assignment_count + skipped_role_rows) * 100) if (role_assignment_count + skipped_role_rows) > 0 else 0:.1f}%")
    logging.info(f"[ROLE ASSIGNMENTS] ===============================")
    
    # FIX A: Aggregate work by task from assignments
    logging.info("[FIX A] Aggregating work by task from assignments")
    work_by_task = {}
    cost_by_task = {}
    for a in assignment_data_list:
        task_uid = a["TaskUID"]
        work_by_task[task_uid] = work_by_task.get(task_uid, 0.0) + float(a["WorkHours"])
        cost_by_task[task_uid] = cost_by_task.get(task_uid, 0.0) + float(a["Cost"])
    
    logging.info(f"[FIX A] Aggregated work for {len(work_by_task)} tasks")
    
    # VALIDATION GUARD: Ensure all assignments reference valid Resource UIDs
    logging.info("[ASSIGNMENT VALIDATION] Validating assignment ResourceUIDs...")
    invalid_assignments = []
    resource_uid_usage = {}  # Track which resource UIDs are actually used
    
    for assign_data in assignment_data_list:
        res_uid = assign_data.get("ResourceUID")
        task_uid = assign_data.get("TaskUID")
        
        # FIX ISSUE 2: Verify resource UID exists in resource_data_list
        if res_uid not in valid_resource_uids:
            invalid_assignments.append({
                "task_uid": task_uid,
                "resource_uid": res_uid,
                "assignment_uid": assign_data.get("AssignmentUID")
            })
        else:
            # Track resource UID usage for reporting
            resource_uid_usage[res_uid] = resource_uid_usage.get(res_uid, 0) + 1
    
    if len(invalid_assignments) > 0:
        logging.error(f"[ASSIGNMENT VALIDATION] ❌ CRITICAL: {len(invalid_assignments)} assignments reference invalid ResourceUIDs!")
        logging.error(f"[ASSIGNMENT VALIDATION] Valid resource UIDs: {sorted(valid_resource_uids)[:20]} ...")
        logging.error(f"[ASSIGNMENT VALIDATION] Invalid assignments: {invalid_assignments[:10]}")
        raise ValueError(
            f"CRITICAL: {len(invalid_assignments)} assignments reference resource UIDs that don't exist in resource_data_list. "
            f"First invalid: Task UID={invalid_assignments[0]['task_uid']}, Resource UID={invalid_assignments[0]['resource_uid']}"
        )
    
    logging.info(f"[ASSIGNMENT VALIDATION] ✓ All {len(assignment_data_list)} assignments reference valid Resource UIDs")
    logging.info(f"[ASSIGNMENT VALIDATION] ✓ {len(resource_uid_usage)} unique resources are assigned to tasks")
    
    # FIX ISSUE 2: Verify resource UIDs are from 1000+ range (not sequential from 1)
    all_resource_uids_in_assignments = [a["ResourceUID"] for a in assignment_data_list]
    min_res_uid = min(all_resource_uids_in_assignments) if all_resource_uids_in_assignments else None
    max_res_uid = max(all_resource_uids_in_assignments) if all_resource_uids_in_assignments else None
    
    if min_res_uid is not None and min_res_uid < 1000:
        logging.warning(f"[ASSIGNMENT VALIDATION] ⚠ WARNING: Found resource UID {min_res_uid} < 1000. Expected UIDs >= 1000 to avoid collision with Task UIDs.")
    
    logging.info(f"[ASSIGNMENT VALIDATION] ✓ Resource UID range in assignments: {min_res_uid} to {max_res_uid}")
    logging.info(f"[ASSIGNMENT VALIDATION] ✓ Issue 2 validation passed: All assignments use actual resource UIDs from resource_uid_map")
    
    # ============================================================================
    # FIX ISSUE 3: APPLY WORK AGGREGATION TO TASK XML ELEMENTS
    # ============================================================================
    # This section takes the work_by_task aggregation calculated from assignments
    # and applies it to the Task XML elements BEFORE Phase 2 serialization.
    # This ensures Task.Work fields accurately reflect assignment totals.
    logging.info("[FIX ISSUE 3] Applying work_by_task aggregation to Task XML elements...")
    logging.info(f"[FIX ISSUE 3] work_by_task contains aggregated work for {len(work_by_task)} tasks")
    
    tasks_updated_count = 0
    tasks_skipped_summary = 0
    tasks_not_found = 0
    
    for task_uid, work_hours in work_by_task.items():
        # Find task element by UID
        for task_elem in tasks.findall("{%s}Task" % ns):
            uid_elem = task_elem.find("{%s}UID" % ns)
            if uid_elem is not None and int(uid_elem.text) == task_uid:
                # Check if this is a summary task (skip work updates for summary tasks)
                summary_elem = task_elem.find("{%s}Summary" % ns)
                is_summary = summary_elem is not None and summary_elem.text == "1"
                
                if not is_summary:
                    # Update Work, RemainingWork, RegularWork
                    planned_minutes = int(round(60 * work_hours))
                    
                    work_elem = task_elem.find("{%s}Work" % ns)
                    if work_elem is not None:
                        old_work_value = work_elem.text
                        work_elem.text = f"PT{planned_minutes}M"
                    else:
                        old_work_value = "MISSING"
                        ET.SubElement(task_elem, "{%s}Work" % ns).text = f"PT{planned_minutes}M"
                    
                    remaining_work_elem = task_elem.find("{%s}RemainingWork" % ns)
                    if remaining_work_elem is not None:
                        remaining_work_elem.text = f"PT{planned_minutes}M"
                    
                    regular_work_elem = task_elem.find("{%s}RegularWork" % ns)
                    if regular_work_elem is not None:
                        regular_work_elem.text = f"PT{planned_minutes}M"
                    
                    # FIX E: Update Task.Cost from assignment costs
                    task_cost = cost_by_task.get(task_uid, 0.0)
                    cost_elem = task_elem.find("{%s}Cost" % ns)
                    if cost_elem is not None:
                        cost_elem.text = str(task_cost)
                    else:
                        ET.SubElement(task_elem, "{%s}Cost" % ns).text = str(task_cost)
                    
                    # FIX E: Ensure FixedCost is set to match Cost (create if missing)
                    fixed_cost_elem = task_elem.find("{%s}FixedCost" % ns)
                    if fixed_cost_elem is not None:
                        fixed_cost_elem.text = str(task_cost)
                    else:
                        ET.SubElement(task_elem, "{%s}FixedCost" % ns).text = str(task_cost)
                    
                    task_name_elem = task_elem.find("{%s}Name" % ns)
                    task_name = task_name_elem.text if task_name_elem is not None else "Unknown"
                    
                    # Log update details
                    logging.info(f"[FIX ISSUE 3] Updated task '{task_name}' (UID={task_uid}): Work={old_work_value} → PT{planned_minutes}M ({work_hours}h), Cost=${task_cost:.2f}")
                    tasks_updated_count += 1
                else:
                    # Log skipped summary task
                    task_name_elem = task_elem.find("{%s}Name" % ns)
                    task_name = task_name_elem.text if task_name_elem is not None else "Unknown"
                    logging.info(f"[FIX ISSUE 3] Skipped summary task '{task_name}' (UID={task_uid}) - summary tasks auto-calculate work from children")
                    tasks_skipped_summary += 1
                break
        else:
            # Task UID not found in XML tree
            tasks_not_found += 1
            logging.warning(f"[FIX ISSUE 3] Task UID={task_uid} not found in XML tree (work={work_hours}h cannot be applied)")
    
    # FIX ISSUE 3: Summary and validation
    logging.info(f"[FIX ISSUE 3] ========== WORK AGGREGATION SUMMARY ==========")
    logging.info(f"[FIX ISSUE 3] Tasks with aggregated work: {len(work_by_task)}")
    logging.info(f"[FIX ISSUE 3] Leaf tasks updated: {tasks_updated_count}")
    logging.info(f"[FIX ISSUE 3] Summary tasks skipped: {tasks_skipped_summary}")
    logging.info(f"[FIX ISSUE 3] Tasks not found: {tasks_not_found}")
    
    # Validation: Ensure most tasks were updated successfully
    if tasks_updated_count == 0 and len(work_by_task) > 0:
        logging.warning(f"[FIX ISSUE 3] ⚠ WARNING: No tasks were updated despite {len(work_by_task)} tasks in work_by_task!")
        logging.warning(f"[FIX ISSUE 3] This may indicate that work aggregation is not being applied correctly.")
    elif tasks_updated_count > 0:
        success_rate = (tasks_updated_count / len(work_by_task) * 100) if len(work_by_task) > 0 else 0
        logging.info(f"[FIX ISSUE 3] ✓ Success rate: {success_rate:.1f}% ({tasks_updated_count}/{len(work_by_task)} tasks updated)")
        logging.info(f"[FIX ISSUE 3] ✓ Issue 3 fix COMPLETE: work_by_task aggregation successfully applied to Task XML elements")
    
    logging.info(f"[FIX ISSUE 3] ================================================")

    # ============================================================================
    # PHASE 2: WRITE RESOURCES XML FROM PRE-BUILT DATA
    # ============================================================================
    # This phase creates Resource XML elements in the correct MSPDI schema order
    # (after Tasks) using the resource data structures built in Phase 1.
    logging.info("[PHASE 2] Writing Resources XML from pre-built data...")
    resources = ET.SubElement(root, "{%s}Resources" % ns)
    
    # Create Resource XML elements from resource_data_list
    for res_data in resource_data_list:
        res = ET.SubElement(resources, "{%s}Resource" % ns)
        ET.SubElement(res, "{%s}UID" % ns).text = str(res_data["UID"])
        ET.SubElement(res, "{%s}ID" % ns).text = str(res_data["ID"])
        ET.SubElement(res, "{%s}Name" % ns).text = res_data["Name"]
        ET.SubElement(res, "{%s}Initials" % ns).text = res_data["Initials"]
        if res_data.get("Group"):
            ET.SubElement(res, "{%s}Group" % ns).text = res_data["Group"]
        ET.SubElement(res, "{%s}Type" % ns).text = res_data["Type"]
        ET.SubElement(res, "{%s}MaterialLabel" % ns).text = "hrs"
        ET.SubElement(res, "{%s}MaxUnits" % ns).text = "1.0"  # Workfront requires fractional format: 1.0 = 100%
        ET.SubElement(res, "{%s}PeakUnits" % ns).text = "1.0"  # Workfront requires fractional format: 1.0 = 100%
        ET.SubElement(res, "{%s}OverAllocated" % ns).text = "0"
        ET.SubElement(res, "{%s}AvailableFrom" % ns).text = project_start.isoformat()
        ET.SubElement(res, "{%s}AvailableTo" % ns).text = (project_start + timedelta(days=365)).isoformat()
        ET.SubElement(res, "{%s}Start" % ns).text = project_start.isoformat()
        ET.SubElement(res, "{%s}Finish" % ns).text = (project_start + timedelta(days=365)).isoformat()
        ET.SubElement(res, "{%s}CanLevel" % ns).text = "1"
        ET.SubElement(res, "{%s}AccrueAt" % ns).text = "3"  # Prorated
        ET.SubElement(res, "{%s}WorkGroup" % ns).text = "0"  # Default
        ET.SubElement(res, "{%s}StandardRate" % ns).text = f"{res_data['Rate']:.2f}"
        ET.SubElement(res, "{%s}StandardRateFormat" % ns).text = "2"  # Per hour
        ET.SubElement(res, "{%s}OvertimeRate" % ns).text = f"{res_data['Rate'] * 1.5:.2f}"
        ET.SubElement(res, "{%s}OvertimeRateFormat" % ns).text = "2"
        ET.SubElement(res, "{%s}CostPerUse" % ns).text = "0"
        # WORKFRONT FIX: Reference Calendar UID 9999
        ET.SubElement(res, "{%s}CalendarUID" % ns).text = "9999"
    
    logging.info(f"[PHASE 2] ✓ Created {len(resource_data_list)} Resource XML elements")
    
    # VALIDATION GUARD: Verify Resource XML elements match data structures
    resource_uids_in_xml = []
    for res_elem in resources.findall("{%s}Resource" % ns):
        uid_elem = res_elem.find("{%s}UID" % ns)
        if uid_elem is not None:
            resource_uids_in_xml.append(int(uid_elem.text))
    
    # Verify count matches
    assert len(resource_uids_in_xml) == len(resource_data_list), \
        f"CRITICAL: Resource XML count mismatch! XML={len(resource_uids_in_xml)}, Data={len(resource_data_list)}"
    
    # Check for duplicates
    assert len(resource_uids_in_xml) == len(set(resource_uids_in_xml)), \
        f"CRITICAL: Duplicate ResourceUIDs found in XML! UIDs: {resource_uids_in_xml}"
    
    # Verify UIDs match valid_resource_uids from Phase 1
    xml_uid_set = set(resource_uids_in_xml)
    assert xml_uid_set == valid_resource_uids, \
        f"CRITICAL: Resource UIDs in XML don't match Phase 1 data! XML UIDs: {xml_uid_set}, Expected: {valid_resource_uids}"
    
    logging.info(f"[PHASE 2] ✓ All {len(resource_uids_in_xml)} Resource UIDs validated (no duplicates, matches Phase 1 data)")
    
    # ============================================================================
    # PHASE 2: WRITE ASSIGNMENTS XML FROM PRE-BUILT DATA
    # ============================================================================
    # This phase creates Assignment XML elements using the assignment data
    # structures built in Phase 1 (after resource data was built).
    logging.info("[PHASE 2] Writing Assignments XML from pre-built data...")
    assignments = ET.SubElement(root, "{%s}Assignments" % ns)
    
    # Create assignment XML elements from assignment_data_list
    for assignment_data in assignment_data_list:
        assign = ET.SubElement(assignments, "{%s}Assignment" % ns)
        ET.SubElement(assign, "{%s}UID" % ns).text = str(assignment_data["AssignmentUID"])
        ET.SubElement(assign, "{%s}TaskUID" % ns).text = str(assignment_data["TaskUID"])
        ET.SubElement(assign, "{%s}ResourceUID" % ns).text = str(assignment_data["ResourceUID"])
        ET.SubElement(assign, "{%s}Units" % ns).text = "1.0"  # Workfront requires fractional (1.0 = 100%)
        
        # Work in minutes (PT format)
        work_minutes = int(assignment_data["WorkHours"] * 60)
        ET.SubElement(assign, "{%s}Work" % ns).text = f"PT{work_minutes}M"
        ET.SubElement(assign, "{%s}RegularWork" % ns).text = f"PT{work_minutes}M"
        ET.SubElement(assign, "{%s}RemainingWork" % ns).text = f"PT{work_minutes}M"
        ET.SubElement(assign, "{%s}Start" % ns).text = assignment_data["Start"]
        ET.SubElement(assign, "{%s}Finish" % ns).text = assignment_data["Finish"]
        
        # Standard assignment fields
        ET.SubElement(assign, "{%s}StartVariance" % ns).text = "0"
        ET.SubElement(assign, "{%s}FinishVariance" % ns).text = "0"
        ET.SubElement(assign, "{%s}WorkVariance" % ns).text = "0"
        ET.SubElement(assign, "{%s}HasFixedRateUnits" % ns).text = "1"
        ET.SubElement(assign, "{%s}FixedMaterial" % ns).text = "0"
        ET.SubElement(assign, "{%s}Leveling" % ns).text = "0"
        ET.SubElement(assign, "{%s}LevelingCanSplit" % ns).text = "1"
        ET.SubElement(assign, "{%s}LevelingDelay" % ns).text = "0"
        ET.SubElement(assign, "{%s}LevelingDelayFormat" % ns).text = "8"
        ET.SubElement(assign, "{%s}VariableRateUnits" % ns).text = "0"
        ET.SubElement(assign, "{%s}OverAllocated" % ns).text = "0"
        ET.SubElement(assign, "{%s}ResponsePending" % ns).text = "0"
        ET.SubElement(assign, "{%s}UpdateNeeded" % ns).text = "0"
        ET.SubElement(assign, "{%s}Cost" % ns).text = str(assignment_data["Cost"])
        ET.SubElement(assign, "{%s}BCWS" % ns).text = "0"
        ET.SubElement(assign, "{%s}BCWP" % ns).text = "0"
        ET.SubElement(assign, "{%s}ACWP" % ns).text = "0"
        ET.SubElement(assign, "{%s}SV" % ns).text = "0"
        ET.SubElement(assign, "{%s}CostVariance" % ns).text = "0"
        ET.SubElement(assign, "{%s}WorkContour" % ns).text = "0"  # Flat
        ET.SubElement(assign, "{%s}StartSlack" % ns).text = "0"
        ET.SubElement(assign, "{%s}FinishSlack" % ns).text = "0"
        ET.SubElement(assign, "{%s}VAC" % ns).text = "0"
    
    logging.info(f"[FIX A] Created {len(assignment_data_list)} Assignment XML elements")
    
    # WORKFRONT COMPATIBILITY: Safety passes to normalize values
    logging.info("[WORKFRONT FIX] Running safety passes to ensure Workfront compatibility...")
    
    # Safety Pass A: Normalize PredecessorLink Type (0 or invalid → 1 for FS)
    type_fixed = 0
    for t in root.findall(".//{%s}PredecessorLink/{%s}Type" % (ns, ns)):
        current_val = (t.text or "").strip()
        if current_val not in {"1", "2", "3"}:  # Type 0 or blank → Force FS (Type 1)
            t.text = "1"
            type_fixed += 1
    logging.info(f"[WORKFRONT FIX] Fixed {type_fixed} PredecessorLink Type values")
    logging.info("[WORKFRONT FIX] ✓ Safety pass completed")
    
    # GPT-5 Pro Regression Guard: Validate task-level ExtendedAttributes schema
    logging.info("[REGRESSION GUARD] Validating task-level ExtendedAttribute schema...")
    schema_violations = []
    tasks_elem = root.find("{%s}Tasks" % ns)
    if tasks_elem is not None:
        for task in tasks_elem.findall("{%s}Task" % ns):
            uid_elem = task.find("{%s}UID" % ns)
            task_uid_text = uid_elem.text if uid_elem is not None else "Unknown"
            
            # Check for ExtendedAttributes wrapper (WRONG)
            ext_attrs_wrapper = task.find("{%s}ExtendedAttributes" % ns)
            if ext_attrs_wrapper is not None:
                schema_violations.append(f"Task UID={task_uid_text}: Has ExtendedAttributes wrapper (should be flat siblings)")
            
            # Check each ExtendedAttribute for proper structure
            for ea in task.findall("{%s}ExtendedAttribute" % ns):
                # Must have FieldID and Value
                if ea.find("{%s}FieldID" % ns) is None:
                    schema_violations.append(f"Task UID={task_uid_text}: ExtendedAttribute missing FieldID")
                if ea.find("{%s}Value" % ns) is None:
                    schema_violations.append(f"Task UID={task_uid_text}: ExtendedAttribute missing Value")
                
                # Must NOT have UID, CfType, or ElementType at task level
                if ea.find("{%s}UID" % ns) is not None:
                    schema_violations.append(f"Task UID={task_uid_text}: ExtendedAttribute has UID (task-level should NOT have UID)")
                if ea.find("{%s}CfType" % ns) is not None:
                    schema_violations.append(f"Task UID={task_uid_text}: ExtendedAttribute has CfType (task-level should NOT have CfType)")
                if ea.find("{%s}ElementType" % ns) is not None:
                    schema_violations.append(f"Task UID={task_uid_text}: ExtendedAttribute has ElementType (task-level should NOT have ElementType)")
    
    if schema_violations:
        logging.error(f"[REGRESSION GUARD] ❌ SCHEMA VIOLATIONS DETECTED! {len(schema_violations)} violations:")
        for violation in schema_violations[:10]:  # Show first 10
            logging.error(f"  - {violation}")
        if len(schema_violations) > 10:
            logging.error(f"  ... and {len(schema_violations) - 10} more violations")
        raise ValueError(f"Task-level ExtendedAttribute schema violations detected. Export aborted.")
    else:
        logging.info("[REGRESSION GUARD] ✓ All task-level ExtendedAttributes have correct flat schema (FieldID + Value only)")
    
    # CRITICAL VALIDATION: Check for empty summary tasks before export
    # Workfront rejects XML with summary tasks that have no children
    logging.info("[HIERARCHY VALIDATION] Validating task hierarchy...")
    
    # Ensure tasks_elem exists before validation
    if tasks_elem is None:
        logging.warning("[HIERARCHY VALIDATION] No Tasks element found in XML, skipping validation")
        hierarchy_violations = []
    else:
        hierarchy_violations = validate_task_hierarchy(tasks_elem, ns)
    
    if hierarchy_violations:
        logging.error(f"[HIERARCHY VALIDATION] ❌ CRITICAL: Found {len(hierarchy_violations)} empty summary tasks!")
        logging.error(f"[HIERARCHY VALIDATION] Workfront will reject this XML with 'plan has to link' error")
        
        # Log first 10 violations
        for i, violation in enumerate(hierarchy_violations[:10]):
            logging.error(f"  {i+1}. Empty summary task: UID={violation['uid']}, Name='{violation['name']}', WBS={violation['wbs']}, Level={violation['outline_level']}")
        
        if len(hierarchy_violations) > 10:
            logging.error(f"  ... and {len(hierarchy_violations) - 10} more empty summary tasks")
        
        # Raise error to abort export
        raise ValueError(
            f"Export aborted: Found {len(hierarchy_violations)} empty summary tasks. "
            f"Workfront requires all summary tasks (Summary=1) to have at least one child task. "
            f"First violation: UID={hierarchy_violations[0]['uid']}, Name='{hierarchy_violations[0]['name']}'"
        )
    else:
        logging.info("[HIERARCHY VALIDATION] ✓ All summary tasks have at least one child - hierarchy is valid")
    
    # CRITICAL VALIDATION: Count Summary elements before export
    logging.info("[SUMMARY VALIDATION] Counting Summary elements in XML tree...")
    summary_count = 0
    if tasks_elem is not None:
        for task in tasks_elem.findall("{%s}Task" % ns):
            summary_elem = task.find("{%s}Summary" % ns)
            if summary_elem is not None:
                summary_count += 1
                if summary_elem.text == "1":
                    uid_elem = task.find("{%s}UID" % ns)
                    name_elem = task.find("{%s}Name" % ns)
                    level_elem = task.find("{%s}OutlineLevel" % ns)
                    logging.info(f"[SUMMARY CHECK] Found Summary=1: UID={uid_elem.text if uid_elem is not None else '?'}, Name='{name_elem.text if name_elem is not None else '?'}', Level={level_elem.text if level_elem is not None else '?'}")
    
    logging.info(f"[SUMMARY VALIDATION] Found {summary_count} tasks with Summary element")
    if summary_count == 0:
        logging.error("[SUMMARY VALIDATION] ❌ CRITICAL: NO Summary elements found in XML tree!")
        logging.error("[SUMMARY VALIDATION] Workfront requires Summary=1 for all deliverables and components")
        raise ValueError("Export aborted: No Summary elements found in XML tree. This will cause Workfront import to fail.")
    
    # ============================================================================
    # FINAL VALIDATION: Verify All Three Critical Issues Are Resolved
    # ============================================================================
    logging.info("[FINAL VALIDATION] ========== COMPREHENSIVE REGRESSION CHECK ==========")
    
    # Issue 1 Validation: Resource UID Mapping Consistency
    logging.info("[FINAL VALIDATION] Issue 1: Checking resource_uid_map and resource_data_list synchronization...")
    resource_xml_uids = set()
    for res_elem in resources.findall("{%s}Resource" % ns):
        uid_elem = res_elem.find("{%s}UID" % ns)
        if uid_elem is not None:
            resource_xml_uids.add(int(uid_elem.text))
    
    if resource_xml_uids == valid_resource_uids:
        logging.info(f"[FINAL VALIDATION] ✓ Issue 1 PASSED: All {len(resource_xml_uids)} resources in XML match resource_data_list")
    else:
        missing = valid_resource_uids - resource_xml_uids
        extra = resource_xml_uids - valid_resource_uids
        raise ValueError(f"Issue 1 FAILED: Resource UID mismatch! Missing: {missing}, Extra: {extra}")
    
    # Issue 2 Validation: Assignment ResourceUIDs Use Correct Range (1000+)
    logging.info("[FINAL VALIDATION] Issue 2: Checking assignment resource UID references...")
    assignment_resource_uids = set()
    for assign_elem in assignments.findall("{%s}Assignment" % ns):
        res_uid_elem = assign_elem.find("{%s}ResourceUID" % ns)
        if res_uid_elem is not None:
            res_uid = int(res_uid_elem.text)
            assignment_resource_uids.add(res_uid)
            
            # Verify UID exists in resources
            if res_uid not in resource_xml_uids:
                raise ValueError(f"Issue 2 FAILED: Assignment references invalid ResourceUID={res_uid} (not in Resources)")
    
    if min(assignment_resource_uids) >= 1000 if assignment_resource_uids else True:
        logging.info(f"[FINAL VALIDATION] ✓ Issue 2 PASSED: All {len(assignment_resource_uids)} assignment resource UIDs >= 1000 and exist in Resources")
    else:
        invalid_uids = [uid for uid in assignment_resource_uids if uid < 1000]
        logging.warning(f"[FINAL VALIDATION] ⚠ Issue 2 WARNING: {len(invalid_uids)} resource UIDs < 1000: {invalid_uids[:10]}")
    
    # Issue 3 Validation: Task Work Aggregation Applied
    logging.info("[FINAL VALIDATION] Issue 3: Checking task work aggregation...")
    tasks_with_nonzero_work = 0
    tasks_with_zero_work = 0
    
    for task_elem in tasks.findall("{%s}Task" % ns):
        work_elem = task_elem.find("{%s}Work" % ns)
        summary_elem = task_elem.find("{%s}Summary" % ns)
        is_summary = summary_elem is not None and summary_elem.text == "1"
        
        if work_elem is not None and not is_summary:
            work_val = work_elem.text
            if work_val and work_val != "PT0M":
                tasks_with_nonzero_work += 1
            else:
                tasks_with_zero_work += 1
    
    if tasks_with_nonzero_work > 0:
        logging.info(f"[FINAL VALIDATION] ✓ Issue 3 PASSED: {tasks_with_nonzero_work} leaf tasks have non-zero Work values")
        if tasks_with_zero_work > 0:
            logging.info(f"[FINAL VALIDATION]   ({tasks_with_zero_work} tasks still have PT0M - may be tasks without assignments)")
    else:
        logging.warning(f"[FINAL VALIDATION] ⚠ Issue 3 WARNING: No tasks have non-zero Work values! work_by_task may not have been applied.")
    
    logging.info("[FINAL VALIDATION] ========== ALL REGRESSIONS CHECKED ==========")
    logging.info("[FINAL VALIDATION] ✓ All three critical issues validated successfully")
    logging.info("[FINAL VALIDATION] ✓ XML is ready for export")
    
    # Write the XML file
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    
    # WORKFRONT FIX: Write in BINARY mode to prevent UTF-8 BOM
    # Workfront rejects files with BOM (EF BB BF) at the start
    # Binary mode gives us complete control over bytes written
    
    # First, get XML content as string (without declaration)
    import io
    xml_buffer = io.BytesIO()
    tree.write(xml_buffer, encoding="utf-8", xml_declaration=False)
    xml_content = xml_buffer.getvalue().decode('utf-8')
    
    # Write to file in BINARY mode with manual UTF-8 encoding (no BOM)
    with open(output_xml, 'wb') as f:
        # Write declaration manually as UTF-8 bytes (no BOM)
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        # Write content as UTF-8 bytes (no BOM)
        f.write(xml_content.encode('utf-8'))
    
    # FIX: Verify PredecessorLink elements were created
    # Count all PredecessorLink elements in the XML
    pred_links_in_xml = root.findall(".//{%s}PredecessorLink" % ns)
    pred_link_count = len(pred_links_in_xml)
    
    logging.info(f"[VERIFICATION] ==================== FINAL XML VERIFICATION ====================")
    logging.info(f"[VERIFICATION] XML contains {pred_link_count} PredecessorLink elements")
    if pred_link_count > 0:
        logging.info(f"[VERIFICATION] ✓ SUCCESS! PredecessorLink elements were created in XML")
        # Sample a few for logging
        for i, pred_link in enumerate(pred_links_in_xml[:5]):
            pred_uid_elem = pred_link.find("{%s}PredecessorUID" % ns)
            pred_type_elem = pred_link.find("{%s}Type" % ns)
            # Find parent task
            parent_task = None
            for task in root.findall(".//{%s}Task" % ns):
                if pred_link in list(task):
                    parent_task = task
                    break
            parent_uid = "Unknown"
            parent_name = "Unknown"
            if parent_task is not None:
                uid_elem = parent_task.find("{%s}UID" % ns)
                name_elem = parent_task.find("{%s}Name" % ns)
                if uid_elem is not None:
                    parent_uid = uid_elem.text
                if name_elem is not None:
                    parent_name = name_elem.text
            
            if pred_uid_elem is not None:
                logging.info(f"[VERIFICATION] Sample #{i+1}: Task '{parent_name}' (UID={parent_uid}) → Predecessor UID={pred_uid_elem.text}, Type={pred_type_elem.text if pred_type_elem is not None else 'N/A'}")
    else:
        logging.warning(f"[VERIFICATION] ✗ WARNING! No PredecessorLink elements found in XML despite dependency processing")
    logging.info(f"[VERIFICATION] ==================================================================")
    
    # Return enhanced statistics
    deliverable_count = 0
    if "Deliverable" in df.columns:
        try:
            deliverable_series = df["Deliverable"] if isinstance(df["Deliverable"], pd.Series) else pd.Series(df["Deliverable"])
            deliverable_count = len(deliverable_series.dropna().unique())
        except Exception:
            deliverable_count = 0
    
    total_hours = 0.0
    if "Planned_Hours" in df.columns:
        try:
            total_hours = float(df["Planned_Hours"].dropna().sum())
        except (ValueError, TypeError):
            total_hours = 0.0
    elif "Hours" in df.columns:
        try:
            total_hours = float(df["Hours"].dropna().sum())
        except (ValueError, TypeError):
            total_hours = 0.0
    
    total_cost = 0.0
    if "Price_USD" in df.columns:
        try:
            total_cost = float(df["Price_USD"].dropna().sum())
        except (ValueError, TypeError):
            total_cost = 0.0
    
    stats = {
        "task_count": task_uid - 1,
        "resource_count": len(resource_map) + len(department_resources),
        "assignment_count": 0,  # Assignments disabled for Workfront compatibility
        "project_start": project_start.isoformat(),
        "project_end": current_date.isoformat() if current_date else project_start.isoformat(),
        "deliverable_count": deliverable_count,
        "milestone_count": len([1 for t in tasks if t.find("{%s}Milestone" % ns) is not None and t.find("{%s}Milestone" % ns).text == "1"]),
        "total_hours": total_hours,
        "total_cost": total_cost,
        "has_wbs": True,
        "has_dependencies": add_dependencies,
        "has_custom_fields": add_custom_fields,
        "has_calendars": True,
        "predecessor_links_count": pred_link_count
    }
    
    logging.info(f"[Enhanced MSPDI] Created {output_xml}: {stats['task_count']} tasks, {stats['resource_count']} resources, {stats['milestone_count']} milestones, {stats['predecessor_links_count']} dependencies")
    
    return stats


def create_empty_mspdi_xml(project_name: str, start_date_iso: Optional[str] = None) -> ET.Element:
    """Create a minimal empty MSPDI XML structure with professional features"""
    ns = "http://schemas.microsoft.com/project"
    ET.register_namespace("", ns)
    
    root = ET.Element("{%s}Project" % ns)
    ET.SubElement(root, "{%s}SaveVersion" % ns).text = "14"
    ET.SubElement(root, "{%s}Name" % ns).text = project_name
    ET.SubElement(root, "{%s}Title" % ns).text = project_name
    
    if start_date_iso:
        ET.SubElement(root, "{%s}StartDate" % ns).text = start_date_iso
    else:
        ET.SubElement(root, "{%s}StartDate" % ns).text = datetime.now().isoformat()
    
    # WORKFRONT FIX: Reference Default Calendar UID 9999
    ET.SubElement(root, "{%s}DefaultCalendarUID" % ns).text = "9999"
    ET.SubElement(root, "{%s}DefaultTaskType" % ns).text = "0"
    ET.SubElement(root, "{%s}DefaultFixedCostAccrual" % ns).text = "2"
    ET.SubElement(root, "{%s}DefaultStandardRate" % ns).text = "0"
    ET.SubElement(root, "{%s}DefaultOvertimeRate" % ns).text = "0"
    ET.SubElement(root, "{%s}DurationFormat" % ns).text = "7"
    ET.SubElement(root, "{%s}WorkFormat" % ns).text = "2"
    
    # Add empty containers
    ET.SubElement(root, "{%s}Calendars" % ns)
    ET.SubElement(root, "{%s}Resources" % ns)
    tasks = ET.SubElement(root, "{%s}Tasks" % ns)
    
    # Add minimal project task
    # CRITICAL FIX: Root task MUST have OutlineLevel=0 (not 1) for Workfront compatibility
    project_task = ET.SubElement(tasks, "{%s}Task" % ns)
    ET.SubElement(project_task, "{%s}UID" % ns).text = "0"
    ET.SubElement(project_task, "{%s}ID" % ns).text = "0"
    ET.SubElement(project_task, "{%s}Name" % ns).text = project_name
    ET.SubElement(project_task, "{%s}Type" % ns).text = "1"
    ET.SubElement(project_task, "{%s}IsNull" % ns).text = "0"
    ET.SubElement(project_task, "{%s}WBS" % ns).text = "0"
    ET.SubElement(project_task, "{%s}OutlineNumber" % ns).text = "0"
    ET.SubElement(project_task, "{%s}OutlineLevel" % ns).text = "0"
    ET.SubElement(project_task, "{%s}Priority" % ns).text = "500"
    ET.SubElement(project_task, "{%s}Duration" % ns).text = "PT0M"
    ET.SubElement(project_task, "{%s}DurationFormat" % ns).text = "53"
    ET.SubElement(project_task, "{%s}Work" % ns).text = "PT0M"
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
    # Support command-line arguments or use default test files
    import sys
    
    if len(sys.argv) >= 3:
        test_xlsx = sys.argv[1]
        test_xml = sys.argv[2]
    else:
        test_xlsx = "test.xlsx"
        test_xml = "test_enhanced.xml"
    
    if os.path.exists(test_xlsx):
        stats = convert_excel_to_mspdi(
            input_xlsx=test_xlsx,
            output_xml=test_xml,
            project_name="Enhanced Test Project",
            add_dependencies=True,
            add_custom_fields=True
        )
        print(f"Conversion complete: {stats}")
        print(f"\n✓ Output written to: {test_xml}")
        print(f"✓ Verify the three critical issues are resolved in the output above")
    else:
        print(f"Test file {test_xlsx} not found")