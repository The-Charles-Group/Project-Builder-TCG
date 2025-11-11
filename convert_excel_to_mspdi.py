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


def create_governance_milestone_task(
    task_uid: int,
    ns: str,
    name: str,
    milestone_date: datetime,
    governance_type: str,
    wbs_level: str = "1",
    hours: float = 0,
    predecessor_uid: Optional[int] = None
) -> Tuple[ET.Element, Dict[str, Any]]:
    """
    Create a governance milestone task in MSPDI format
    
    Args:
        task_uid: Unique ID for the task
        ns: XML namespace
        name: Task name
        milestone_date: Date for the milestone
        governance_type: Type of governance milestone (steering_review, executive_briefing, etc.)
        wbs_level: WBS level for the task
        hours: Hours for the task (0 for pure milestone)
        predecessor_uid: UID of predecessor task if any
        
    Returns:
        Tuple of (XML Element, task metadata dict)
    """
    task = ET.Element("{%s}Task" % ns)
    
    # Basic task properties
    ET.SubElement(task, "{%s}UID" % ns).text = str(task_uid)
    ET.SubElement(task, "{%s}ID" % ns).text = str(task_uid)
    ET.SubElement(task, "{%s}Name" % ns).text = name
    ET.SubElement(task, "{%s}Type" % ns).text = "2"  # Fixed duration
    ET.SubElement(task, "{%s}IsNull" % ns).text = "0"
    ET.SubElement(task, "{%s}WBS" % ns).text = wbs_level
    ET.SubElement(task, "{%s}OutlineNumber" % ns).text = wbs_level
    # FIX: Enforce Workfront 3-level hierarchy - map WBS depth to max 3 levels
    # 0 dots (e.g., "1") → OutlineLevel 1, 1 dot (e.g., "1.1") → OutlineLevel 2, 2+ dots → OutlineLevel 3
    dot_count = wbs_level.count('.')
    outline_level = min(dot_count + 1, 3)  # Cap at level 3 for Workfront compatibility
    ET.SubElement(task, "{%s}OutlineLevel" % ns).text = str(outline_level)
    
    # Mark as milestone if no hours
    if hours == 0:
        ET.SubElement(task, "{%s}Milestone" % ns).text = "1"
        ET.SubElement(task, "{%s}Duration" % ns).text = "PT0H0M0S"
    else:
        ET.SubElement(task, "{%s}Milestone" % ns).text = "0"
        duration_days = max(1, int(hours / 8))
        ET.SubElement(task, "{%s}Duration" % ns).text = f"PT{duration_days * 8}H0M0S"
    
    # Set dates
    ET.SubElement(task, "{%s}Start" % ns).text = milestone_date.isoformat()
    if hours > 0:
        end_date = milestone_date + timedelta(days=max(1, int(hours / 8)))
        ET.SubElement(task, "{%s}Finish" % ns).text = end_date.isoformat()
    else:
        ET.SubElement(task, "{%s}Finish" % ns).text = milestone_date.isoformat()
    
    # Priority based on governance type
    priority_map = {
        "steering_review": "600",
        "executive_briefing": "700",
        "risk_review": "650",
        "quality_gate": "550",
        "change_control": "500",
        "compliance": "600",
        "uat": "550",
        "performance_test": "500"
    }
    ET.SubElement(task, "{%s}Priority" % ns).text = priority_map.get(governance_type, "500")
    
    # Work and duration format
    ET.SubElement(task, "{%s}DurationFormat" % ns).text = "39"  # Hours
    ET.SubElement(task, "{%s}Work" % ns).text = f"PT{hours}H0M0S"
    ET.SubElement(task, "{%s}EffortDriven" % ns).text = "0"
    ET.SubElement(task, "{%s}Summary" % ns).text = "0"
    ET.SubElement(task, "{%s}Critical" % ns).text = "0"
    
    # Add custom field for governance type
    ext_attrs = ET.SubElement(task, "{%s}ExtendedAttribute" % ns)
    ET.SubElement(ext_attrs, "{%s}FieldID" % ns).text = "188743731"  # Text1
    ET.SubElement(ext_attrs, "{%s}Value" % ns).text = f"GOVERNANCE_{governance_type.upper()}"
    
    # Add notes to identify as governance milestone
    ET.SubElement(task, "{%s}Notes" % ns).text = f"Governance Milestone: {governance_type}"
    
    # Metadata for tracking
    metadata = {
        "uid": task_uid,
        "name": name,
        "type": governance_type,
        "date": milestone_date.isoformat(),
        "is_governance": True,
        "hours": hours
    }
    
    return task, metadata


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
    add_deliverable_milestones: bool = False,
    add_phase_gates: bool = False,
    add_client_approval_milestone: bool = False,
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
        add_deliverable_milestones: Add START/END anchor milestones for deliverables
        add_phase_gates: Add phase gate milestones at 25%, 50%, 75%
        add_client_approval_milestone: Add CLIENT APPROVAL - FINAL milestone at end
        add_dependencies: Add task dependencies
        add_custom_fields: Add ExtendedAttribute elements for Workfront
        
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
        tree.write(output_xml, encoding="utf-8", xml_declaration=True)
        return {"task_count": 0, "warning": "Empty input data"}
    
    # Determine project start date
    if fixed_start_iso:
        project_start = datetime.fromisoformat(fixed_start_iso.replace("Z", "+00:00"))
        # Remove timezone info to ensure all datetimes are timezone-naive for consistent comparisons
        project_start = project_start.replace(tzinfo=None)
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
    ET.SubElement(root, "{%s}CalendarUID" % ns).text = "1"
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
    ET.SubElement(root, "{%s}MicrosoftProjectServerURL" % ns).text = "1"
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
        
        # Custom Field 7: Service Category (Text) - WORKFRONT REQUIREMENT
        ext_attr7 = ET.SubElement(extended_attrs, "{%s}ExtendedAttribute" % ns)
        ET.SubElement(ext_attr7, "{%s}FieldID" % ns).text = "188743734"  # Task Text4
        ET.SubElement(ext_attr7, "{%s}FieldName" % ns).text = "Text4"
        ET.SubElement(ext_attr7, "{%s}Alias" % ns).text = "Service Category"
        ET.SubElement(ext_attr7, "{%s}Guid" % ns).text = "000039B7-8BBE-4CEB-82C4-FA8C0B400039"
    
    # Add Calendar definition
    calendars = ET.SubElement(root, "{%s}Calendars" % ns)
    calendar = ET.SubElement(calendars, "{%s}Calendar" % ns)
    ET.SubElement(calendar, "{%s}UID" % ns).text = "1"
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
    
    # Create Resources container with enhanced resource definitions
    resources = ET.SubElement(root, "{%s}Resources" % ns)
    
    # Add resources from the DataFrame with enhanced properties
    resource_map = {}
    resource_uid_map = {}  # FIX: New mapping for (role, seniority) -> resource_uid
    department_resources = {}
    resource_id = 1
    
    # Extract unique departments and roles
    departments = set()
    if "Department" in df.columns:
        departments.update(df["Department"].dropna().unique())
    
    # Add department-level resources first
    for dept in departments:
        res = ET.SubElement(resources, "{%s}Resource" % ns)
        ET.SubElement(res, "{%s}UID" % ns).text = str(resource_id)
        ET.SubElement(res, "{%s}ID" % ns).text = str(resource_id)
        ET.SubElement(res, "{%s}Name" % ns).text = f"{dept} Team"
        ET.SubElement(res, "{%s}Initials" % ns).text = "".join([w[0] for w in str(dept).split()[:2]])
        ET.SubElement(res, "{%s}Group" % ns).text = str(dept)
        ET.SubElement(res, "{%s}Type" % ns).text = "1"  # Work resource
        ET.SubElement(res, "{%s}MaterialLabel" % ns).text = "hrs"
        ET.SubElement(res, "{%s}MaxUnits" % ns).text = "1000"  # 10 resources at 100% each
        ET.SubElement(res, "{%s}PeakUnits" % ns).text = "1000"
        ET.SubElement(res, "{%s}OverAllocated" % ns).text = "0"
        ET.SubElement(res, "{%s}AvailableFrom" % ns).text = project_start.isoformat()
        ET.SubElement(res, "{%s}AvailableTo" % ns).text = (project_start + timedelta(days=365)).isoformat()
        ET.SubElement(res, "{%s}Start" % ns).text = project_start.isoformat()
        ET.SubElement(res, "{%s}Finish" % ns).text = (project_start + timedelta(days=365)).isoformat()
        ET.SubElement(res, "{%s}CanLevel" % ns).text = "1"
        ET.SubElement(res, "{%s}AccrueAt" % ns).text = "3"  # Prorated
        ET.SubElement(res, "{%s}WorkGroup" % ns).text = "0"  # Default
        ET.SubElement(res, "{%s}StandardRate" % ns).text = f"{blended_rate or 150:.2f}"
        ET.SubElement(res, "{%s}StandardRateFormat" % ns).text = "2"  # Per hour
        ET.SubElement(res, "{%s}OvertimeRate" % ns).text = f"{(blended_rate or 150) * 1.5:.2f}"
        ET.SubElement(res, "{%s}OvertimeRateFormat" % ns).text = "2"
        ET.SubElement(res, "{%s}CostPerUse" % ns).text = "0"
        ET.SubElement(res, "{%s}CalendarUID" % ns).text = "1"
        
        department_resources[str(dept)] = resource_id
        resource_id += 1
    
    # FIX: Add individual role resources with (role, seniority) mapping
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
        
        # Create resources from registry (sorted for consistency)
        for normalized_key in sorted(resource_registry.keys()):
            res_data = resource_registry[normalized_key]
            res = ET.SubElement(resources, "{%s}Resource" % ns)
            ET.SubElement(res, "{%s}UID" % ns).text = str(resource_id)
            ET.SubElement(res, "{%s}ID" % ns).text = str(resource_id)
            ET.SubElement(res, "{%s}Name" % ns).text = res_data["display_name"]
            ET.SubElement(res, "{%s}Initials" % ns).text = "".join([w[0] for w in str(res_data["role"]).split()[:3]])
            ET.SubElement(res, "{%s}Type" % ns).text = "1"  # Work resource
            ET.SubElement(res, "{%s}MaterialLabel" % ns).text = "hrs"
            ET.SubElement(res, "{%s}MaxUnits" % ns).text = "100"  # 100% allocation
            ET.SubElement(res, "{%s}PeakUnits" % ns).text = "100"
            ET.SubElement(res, "{%s}OverAllocated" % ns).text = "0"
            ET.SubElement(res, "{%s}AvailableFrom" % ns).text = project_start.isoformat()
            ET.SubElement(res, "{%s}AvailableTo" % ns).text = (project_start + timedelta(days=365)).isoformat()
            ET.SubElement(res, "{%s}Start" % ns).text = project_start.isoformat()
            ET.SubElement(res, "{%s}Finish" % ns).text = (project_start + timedelta(days=365)).isoformat()
            ET.SubElement(res, "{%s}CanLevel" % ns).text = "1"
            ET.SubElement(res, "{%s}AccrueAt" % ns).text = "3"  # Prorated
            ET.SubElement(res, "{%s}WorkGroup" % ns).text = "0"
            
            # Add rate if available
            if blended_rate:
                ET.SubElement(res, "{%s}StandardRate" % ns).text = f"{blended_rate:.2f}"
            elif res_data["rate"] is not None:
                ET.SubElement(res, "{%s}StandardRate" % ns).text = f"{res_data['rate']:.2f}"
            else:
                ET.SubElement(res, "{%s}StandardRate" % ns).text = "150.00"
            
            ET.SubElement(res, "{%s}StandardRateFormat" % ns).text = "2"
            ET.SubElement(res, "{%s}OvertimeRate" % ns).text = f"{(blended_rate or 150) * 1.5:.2f}"
            ET.SubElement(res, "{%s}OvertimeRateFormat" % ns).text = "2"
            ET.SubElement(res, "{%s}CostPerUse" % ns).text = "0"
            ET.SubElement(res, "{%s}CalendarUID" % ns).text = "1"
            
            # Store in resource_uid_map using NORMALIZED key
            resource_uid_map[normalized_key] = resource_id
            resource_map[res_data["role"]] = resource_id  # Keep for backward compatibility
            
            logging.info(f"[RESOURCE CREATION] Created resource UID={resource_id} for Role='{res_data['role']}', Seniority='{res_data['seniority']}', Name='{res_data['display_name']}' (normalized_key='{normalized_key}')")
            
            resource_id += 1
    
    # VALIDATION GUARD: Ensure no duplicate Resource UIDs
    logging.info("[RESOURCE VALIDATION] Running post-creation validation...")
    
    # Collect all Resource UIDs from XML
    resource_uids_in_xml = []
    for res_elem in resources.findall("{%s}Resource" % ns):
        uid_elem = res_elem.find("{%s}UID" % ns)
        if uid_elem is not None:
            resource_uids_in_xml.append(int(uid_elem.text))
    
    # Check for duplicates
    assert len(resource_uids_in_xml) == len(set(resource_uids_in_xml)), \
        f"CRITICAL: Duplicate ResourceUIDs found in XML! UIDs: {resource_uids_in_xml}"
    
    logging.info(f"[RESOURCE VALIDATION] ✓ All {len(resource_uids_in_xml)} Resource UIDs are unique")
    
    # Build valid resource UID set for assignment validation later
    valid_resource_uids = set(resource_uids_in_xml)
    
    # FIX: Log resource mapping summary for debugging
    logging.info(f"[RESOURCE VALIDATION] Created {len(resource_uid_map)} role-seniority resources")
    logging.info(f"[RESOURCE VALIDATION] resource_uid_map keys (first 10): {list(resource_uid_map.keys())[:10]}")
    
    # Create Tasks container
    tasks = ET.SubElement(root, "{%s}Tasks" % ns)
    
    # Add project summary task (Task 0)
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
    
    # Calculate total project timeline for phase gates
    total_rows = len(df)
    phase_gate_positions = []
    if add_phase_gates:
        phase_gate_positions = [
            int(total_rows * 0.25),  # 25% milestone
            int(total_rows * 0.50),  # 50% milestone
            int(total_rows * 0.75),  # 75% milestone
        ]
    
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
            
            ET.SubElement(deliv_task, "{%s}UID" % ns).text = str(deliv_uid)
            ET.SubElement(deliv_task, "{%s}ID" % ns).text = str(deliv_uid)
            ET.SubElement(deliv_task, "{%s}Name" % ns).text = str(deliverable_name)
            ET.SubElement(deliv_task, "{%s}Type" % ns).text = "1"  # Fixed Duration
            ET.SubElement(deliv_task, "{%s}IsNull" % ns).text = "0"
            ET.SubElement(deliv_task, "{%s}WBS" % ns).text = deliv_wbs
            ET.SubElement(deliv_task, "{%s}OutlineNumber" % ns).text = deliv_wbs
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
            
            # Add constraint type based on Gantt-sourced dates
            has_gantt_start = False
            has_gantt_end = False
            
            # Check if Start_Date was successfully parsed from Gantt
            if not group.empty and "Start_Date" in group.columns:
                first_row_start = group.iloc[0].get("Start_Date")
                if pd.notna(first_row_start):
                    has_gantt_start = True
            
            # Check if End_Date was successfully parsed from Gantt
            if not group.empty and "End_Date" in group.columns:
                first_row_end = group.iloc[0].get("End_Date")
                if pd.notna(first_row_end):
                    has_gantt_end = True
            
            # Apply constraint type
            # NOTE: Manual tag removed for summary tasks - they auto-calculate from children
            if has_gantt_start and has_gantt_end:
                # Both dates from Gantt: Must Start On (locks start date, duration determines finish)
                ET.SubElement(deliv_task, "{%s}ConstraintType" % ns).text = "2"
                ET.SubElement(deliv_task, "{%s}ConstraintDate" % ns).text = deliverable_start_date.isoformat()
                logging.info(f"[CONSTRAINT] Deliverable '{deliverable_name}': Must Start On (Type 2)")
            elif has_gantt_start:
                # Only start date from Gantt: Must Start On
                ET.SubElement(deliv_task, "{%s}ConstraintType" % ns).text = "2"
                ET.SubElement(deliv_task, "{%s}ConstraintDate" % ns).text = deliverable_start_date.isoformat()
                logging.info(f"[CONSTRAINT] Deliverable '{deliverable_name}': Must Start On (Type 2)")
            
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
            
            # Add custom fields for deliverable
            if add_custom_fields:
                # Deliverable Code
                if deliv_code:
                    ext_attrs_dc = ET.SubElement(deliv_task, "{%s}ExtendedAttribute" % ns)
                    ET.SubElement(ext_attrs_dc, "{%s}FieldID" % ns).text = "188743732"  # Text2
                    ET.SubElement(ext_attrs_dc, "{%s}Value" % ns).text = deliv_code
                
                # FIX D: Text1 (Department) and Text4 (Service Category) must both be set
                # Text1 mirrors Service Category for default grid visibility in Workfront
                category_value = service_dept if service_dept else "Unassigned"
                
                # Text1 = Department (mirrors Service Category)
                ext_attrs_dept = ET.SubElement(deliv_task, "{%s}ExtendedAttribute" % ns)
                ET.SubElement(ext_attrs_dept, "{%s}FieldID" % ns).text = "188743731"  # Text1
                ET.SubElement(ext_attrs_dept, "{%s}Value" % ns).text = category_value
                
                # Text4 = Service Category (WORKFRONT REQUIREMENT)
                ext_attrs_sc = ET.SubElement(deliv_task, "{%s}ExtendedAttribute" % ns)
                ET.SubElement(ext_attrs_sc, "{%s}FieldID" % ns).text = "188743734"  # Text4
                ET.SubElement(ext_attrs_sc, "{%s}Value" % ns).text = category_value
            
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
                    # FIX: Filter out tasks with blank Component values to avoid "Uncategorized" wrapper
                    # This ensures clean Deliverable → Component → Task hierarchy
                    group_copy = group.copy()
                    
                    # Convert categorical to object if needed
                    if pd.api.types.is_categorical_dtype(group_copy["Component"]):
                        logging.info(f"[3-LEVEL HIERARCHY] Converting Component from categorical to object type")
                        group_copy["Component"] = group_copy["Component"].astype(object)
                    
                    # FIX: FILTER OUT tasks with blank Component values (don't include them in XML)
                    # Check for NaN, None, and empty strings
                    blank_mask = group_copy["Component"].isna() | (group_copy["Component"] == "") | group_copy["Component"].isnull()
                    blank_count = blank_mask.sum()
                    if blank_count > 0:
                        logging.info(f"[3-LEVEL HIERARCHY] Found {blank_count} tasks with blank Component, EXCLUDING them from export")
                        # Filter OUT blank rows instead of filling them with "Uncategorized"
                        group_copy = group_copy[~blank_mask]
                    
                    # Now groupby will work correctly with only non-blank components
                    component_grouped = group_copy.groupby("Component", sort=False, dropna=True)
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
                component_num += 1
                
                # Create component summary task (Level 2)
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
                ET.SubElement(comp_task, "{%s}Name" % ns).text = str(component_name) if component_name else "Uncategorized"
                ET.SubElement(comp_task, "{%s}Type" % ns).text = "1"  # Fixed Duration
                ET.SubElement(comp_task, "{%s}IsNull" % ns).text = "0"
                ET.SubElement(comp_task, "{%s}WBS" % ns).text = comp_wbs
                ET.SubElement(comp_task, "{%s}OutlineNumber" % ns).text = comp_wbs
                ET.SubElement(comp_task, "{%s}OutlineLevel" % ns).text = comp_outline_level
                ET.SubElement(comp_task, "{%s}Priority" % ns).text = "500"
                ET.SubElement(comp_task, "{%s}Start" % ns).text = current_date.isoformat()
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
                
                # Add custom fields for component
                if add_custom_fields:
                    # Component Name
                    ext_attr_comp = ET.SubElement(comp_task, "{%s}ExtendedAttribute" % ns)
                    ET.SubElement(ext_attr_comp, "{%s}FieldID" % ns).text = "188743733"  # Text3
                    ET.SubElement(ext_attr_comp, "{%s}Value" % ns).text = str(component_name)
                    
                    # Deliverable Code
                    if deliv_code:
                        ext_attr_dc = ET.SubElement(comp_task, "{%s}ExtendedAttribute" % ns)
                        ET.SubElement(ext_attr_dc, "{%s}FieldID" % ns).text = "188743732"  # Text2
                        ET.SubElement(ext_attr_dc, "{%s}Value" % ns).text = deliv_code
                    
                    # FIX D: Text1 (Department) and Text4 (Service Category) must both be set
                    # Text1 mirrors Service Category for default grid visibility in Workfront
                    comp_category_value = comp_service_dept if comp_service_dept else "Unassigned"
                    
                    # Text1 = Department (mirrors Service Category)
                    ext_attr_dept_comp = ET.SubElement(comp_task, "{%s}ExtendedAttribute" % ns)
                    ET.SubElement(ext_attr_dept_comp, "{%s}FieldID" % ns).text = "188743731"  # Text1
                    ET.SubElement(ext_attr_dept_comp, "{%s}Value" % ns).text = comp_category_value
                    
                    # Text4 = Service Category (WORKFRONT REQUIREMENT)
                    ext_attr_sc_comp = ET.SubElement(comp_task, "{%s}ExtendedAttribute" % ns)
                    ET.SubElement(ext_attr_sc_comp, "{%s}FieldID" % ns).text = "188743734"  # Text4
                    ET.SubElement(ext_attr_sc_comp, "{%s}Value" % ns).text = comp_category_value
                
                # Track component start/finish dates
                component_start = current_date
                component_finish = current_date
                task_num_in_component = 0
                
                # FIX: Initialize task counter for this component
                comp_key = (str(deliverable_name), str(component_name))
                if comp_key not in task_counter_per_comp:
                    task_counter_per_comp[comp_key] = 1
                
                # Loop through tasks within this component (Level 3)
                for idx, row in component_group.iterrows():
                    try:
                        # FIX: SKIP creating Task elements for role rows (rows where Role is populated)
                        # These will be converted to Assignments later
                        role_value = row.get("Role", "")
                        if pd.notna(role_value) and str(role_value).strip():
                            logging.info(f"[ROLE ROW] Skipping task creation for role row at index {idx}: Role={role_value}")
                            continue  # Skip to next row without creating a Task
                        
                        task_num_in_component += 1
                        task = ET.SubElement(tasks, "{%s}Task" % ns)
                        uid = task_uid
                        task_uid += 1
                        all_task_uids.append(uid)
                        
                        # Get task details - FIX: Use proper L3 task name, NOT Component as fallback
                        task_name = (row.get("Task_Name") or 
                                    row.get("L3_Task") or 
                                    row.get("Task_Label") or 
                                    f"{component_name} - Task {task_num_in_component}")
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
                        ET.SubElement(task, "{%s}WBS" % ns).text = task_wbs
                        ET.SubElement(task, "{%s}OutlineNumber" % ns).text = task_wbs
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
                        
                        # Add cost if available and accumulate into component and deliverable totals
                        price_usd = row.get("Price_USD") if hasattr(row, 'get') else row["Price_USD"] if "Price_USD" in row.index else None
                        if price_usd is not None and pd.notna(price_usd):
                            try:
                                price_value = float(price_usd)
                                if price_value > 0:  # Only add positive costs
                                    ET.SubElement(task, "{%s}Cost" % ns).text = str(price_value)
                                    ET.SubElement(task, "{%s}FixedCost" % ns).text = str(price_value)
                                    ET.SubElement(task, "{%s}FixedCostAccrual" % ns).text = "2"  # Prorated
                                    
                                    # Accumulate cost into component and deliverable totals
                                    component_costs[comp_uid] += price_value
                                    deliverable_costs[deliv_uid] += price_value
                                    
                                    # Add Revenue extended attribute (same as cost for flat billing)
                                    if add_custom_fields:
                                        ext_attr_revenue = ET.SubElement(task, "{%s}ExtendedAttribute" % ns)
                                        ET.SubElement(ext_attr_revenue, "{%s}FieldID" % ns).text = "188743715"  # Number3
                                        ET.SubElement(ext_attr_revenue, "{%s}Value" % ns).text = str(price_value)
                                else:
                                    logging.warning(f"Skipping zero or negative price for task '{task_name}': {price_value}")
                            except (ValueError, TypeError) as e:
                                logging.warning(f"Could not parse Price_USD for task '{task_name}': {e}")
                        
                        # Add extended attributes (custom fields) for each task
                        if add_custom_fields:
                            # Risk Score (random for demo)
                            ext_attr_risk = ET.SubElement(task, "{%s}ExtendedAttribute" % ns)
                            ET.SubElement(ext_attr_risk, "{%s}FieldID" % ns).text = "188743713"  # Number1
                            ET.SubElement(ext_attr_risk, "{%s}Value" % ns).text = str(random.randint(1, 10))
                            
                            # Confidence Level (random 70-100)
                            ext_attr_conf = ET.SubElement(task, "{%s}ExtendedAttribute" % ns)
                            ET.SubElement(ext_attr_conf, "{%s}FieldID" % ns).text = "188743714"  # Number2
                            ET.SubElement(ext_attr_conf, "{%s}Value" % ns).text = str(random.randint(70, 100))
                            
                            # FIX D: Text1 (Department) = Service Category for default grid visibility
                            # Service Category is the primary field; Department mirrors it
                            task_category_value = task_service_dept if task_service_dept else "Unassigned"
                            ext_attr_dept = ET.SubElement(task, "{%s}ExtendedAttribute" % ns)
                            ET.SubElement(ext_attr_dept, "{%s}FieldID" % ns).text = "188743731"  # Text1
                            ET.SubElement(ext_attr_dept, "{%s}Value" % ns).text = task_category_value
                            
                            # Deliverable Code
                            if deliv_code:
                                ext_attr_dc = ET.SubElement(task, "{%s}ExtendedAttribute" % ns)
                                ET.SubElement(ext_attr_dc, "{%s}FieldID" % ns).text = "188743732"  # Text2
                                ET.SubElement(ext_attr_dc, "{%s}Value" % ns).text = deliv_code
                            
                            # Component Name
                            ext_attr_comp = ET.SubElement(task, "{%s}ExtendedAttribute" % ns)
                            ET.SubElement(ext_attr_comp, "{%s}FieldID" % ns).text = "188743733"  # Text3
                            ET.SubElement(ext_attr_comp, "{%s}Value" % ns).text = str(component_name)
                            
                            # Service Category (Text4 - WORKFRONT REQUIREMENT)
                            ext_attr_sc_task = ET.SubElement(task, "{%s}ExtendedAttribute" % ns)
                            ET.SubElement(ext_attr_sc_task, "{%s}FieldID" % ns).text = "188743734"  # Text4
                            ET.SubElement(ext_attr_sc_task, "{%s}Value" % ns).text = task_category_value
                        
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
                
                # Update component summary with calculated duration
                # FIX: Calculate Duration from actual time span (Finish - Start), not business hours
                # This prevents Duration=PT0M when component_start == component_finish
                component_duration_minutes = int((component_finish - component_start).total_seconds() / 60)
                ET.SubElement(comp_task, "{%s}Duration" % ns).text = f"PT{component_duration_minutes}M"
                ET.SubElement(comp_task, "{%s}Finish" % ns).text = component_finish.isoformat()
                
                # Add aggregated cost/revenue to component summary task
                comp_total_cost = component_costs.get(comp_uid, 0.0)
                if comp_total_cost > 0:
                    ET.SubElement(comp_task, "{%s}Cost" % ns).text = str(comp_total_cost)
                    ET.SubElement(comp_task, "{%s}FixedCost" % ns).text = str(comp_total_cost)
                    ET.SubElement(comp_task, "{%s}FixedCostAccrual" % ns).text = "2"  # Prorated
                    
                    # Add Revenue extended attribute (same as cost for flat billing)
                    if add_custom_fields:
                        ext_attr_comp_revenue = ET.SubElement(comp_task, "{%s}ExtendedAttribute" % ns)
                        ET.SubElement(ext_attr_comp_revenue, "{%s}FieldID" % ns).text = "188743715"  # Number3
                        ET.SubElement(ext_attr_comp_revenue, "{%s}Value" % ns).text = str(comp_total_cost)
                    
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
            
            # Update deliverable summary with calculated duration
            # FIX: Calculate Duration from actual time span (Finish - Start), not business hours
            # This prevents Duration=PT0M when dates match or business hours = 0
            deliverable_duration_minutes = int((deliverable_finish - deliverable_start).total_seconds() / 60)
            ET.SubElement(deliv_task, "{%s}Duration" % ns).text = f"PT{deliverable_duration_minutes}M"
            ET.SubElement(deliv_task, "{%s}Finish" % ns).text = deliverable_finish.isoformat()
            deliverable_ends[deliverable_name] = deliverable_finish
            
            # Add aggregated cost/revenue to deliverable summary task
            deliv_total_cost = deliverable_costs.get(deliv_uid, 0.0)
            if deliv_total_cost > 0:
                ET.SubElement(deliv_task, "{%s}Cost" % ns).text = str(deliv_total_cost)
                ET.SubElement(deliv_task, "{%s}FixedCost" % ns).text = str(deliv_total_cost)
                ET.SubElement(deliv_task, "{%s}FixedCostAccrual" % ns).text = "2"  # Prorated
                
                # Add Revenue extended attribute (same as cost for flat billing)
                if add_custom_fields:
                    ext_attr_deliv_revenue = ET.SubElement(deliv_task, "{%s}ExtendedAttribute" % ns)
                    ET.SubElement(ext_attr_deliv_revenue, "{%s}FieldID" % ns).text = "188743715"  # Number3
                    ET.SubElement(ext_attr_deliv_revenue, "{%s}Value" % ns).text = str(deliv_total_cost)
                
                logging.info(f"[COST AGGREGATION] Deliverable '{deliverable_name}' total cost: ${deliv_total_cost:.2f}")
            
            # FIX: Store DUAL WBS to UID mappings for deliverables
            # 1. Original WBS_ID → UID (for dependency lookup from DataFrame)
            # 2. Sequential WBS → UID (for XML structure)
            if original_deliv_wbs_id:
                original_wbs_to_uid[original_deliv_wbs_id] = deliv_uid
            sequential_wbs_to_uid[deliv_wbs] = deliv_uid
            
            # Add deliverable completion milestone
            if add_deliverable_milestones:
                milestone = ET.SubElement(tasks, "{%s}Task" % ns)
                milestone_uid = task_uid
                task_uid += 1
                all_task_uids.append(milestone_uid)
                
                # Use component_num to set proper WBS numbering after all components
                milestone_wbs_num = component_num + 1
                
                ET.SubElement(milestone, "{%s}UID" % ns).text = str(milestone_uid)
                ET.SubElement(milestone, "{%s}ID" % ns).text = str(milestone_uid)
                ET.SubElement(milestone, "{%s}Name" % ns).text = f"{deliverable_name} - COMPLETE"
                ET.SubElement(milestone, "{%s}Type" % ns).text = "1"
                ET.SubElement(milestone, "{%s}Milestone" % ns).text = "1"
                ET.SubElement(milestone, "{%s}WBS" % ns).text = f"{deliverable_num}.{milestone_wbs_num}"
                ET.SubElement(milestone, "{%s}OutlineNumber" % ns).text = f"{deliverable_num}.{milestone_wbs_num}"
                ET.SubElement(milestone, "{%s}OutlineLevel" % ns).text = "2"
                ET.SubElement(milestone, "{%s}Priority" % ns).text = "500"
                ET.SubElement(milestone, "{%s}Start" % ns).text = deliverable_finish.isoformat()
                ET.SubElement(milestone, "{%s}Finish" % ns).text = deliverable_finish.isoformat()
                ET.SubElement(milestone, "{%s}Duration" % ns).text = "PT0M"
                ET.SubElement(milestone, "{%s}DurationFormat" % ns).text = "7"
                ET.SubElement(milestone, "{%s}Work" % ns).text = "PT0M"
                ET.SubElement(milestone, "{%s}Summary" % ns).text = "0"
                ET.SubElement(milestone, "{%s}Critical" % ns).text = "1"
                ET.SubElement(milestone, "{%s}IsMarked" % ns).text = "1"
                ET.SubElement(milestone, "{%s}ConstraintType" % ns).text = str(ConstraintType.MUST_FINISH_ON.value)
                ET.SubElement(milestone, "{%s}ConstraintDate" % ns).text = deliverable_finish.isoformat()
                
                # Add custom field for milestone type
                if add_custom_fields:
                    ext_attr_mt = ET.SubElement(milestone, "{%s}ExtendedAttribute" % ns)
                    ET.SubElement(ext_attr_mt, "{%s}FieldID" % ns).text = "188743731"  # Text1
                    ET.SubElement(ext_attr_mt, "{%s}Value" % ns).text = "Deliverable Milestone"
            
            # FIX: Increment deliverable counter for next deliverable
            deliverable_counter += 1
    
    # Add phase gate milestones
    if add_phase_gates and all_task_uids:
        phase_names = ["Phase 1 Complete (25%)", "Phase 2 Complete (50%)", "Phase 3 Complete (75%)"]
        for i, position in enumerate(phase_gate_positions):
            if position < len(all_task_uids):
                # Get the task at this position
                ref_task_uid = all_task_uids[position]
                if ref_task_uid in task_map:
                    ref_task_data = task_map[ref_task_uid]
                    ref_task = ref_task_data["task"]
                    
                    # Find the finish date from the reference task
                    finish_elem = ref_task.find("{%s}Finish" % ns)
                    if finish_elem is not None:
                        phase_date = finish_elem.text
                    else:
                        phase_date = (project_start + timedelta(days=30 * (i+1))).isoformat()
                    
                    # Create phase gate milestone
                    phase_milestone = ET.SubElement(tasks, "{%s}Task" % ns)
                    phase_uid = task_uid
                    task_uid += 1
                    
                    ET.SubElement(phase_milestone, "{%s}UID" % ns).text = str(phase_uid)
                    ET.SubElement(phase_milestone, "{%s}ID" % ns).text = str(phase_uid)
                    ET.SubElement(phase_milestone, "{%s}Name" % ns).text = phase_names[i]
                    ET.SubElement(phase_milestone, "{%s}Type" % ns).text = "1"
                    ET.SubElement(phase_milestone, "{%s}Milestone" % ns).text = "1"
                    ET.SubElement(phase_milestone, "{%s}WBS" % ns).text = str(deliverable_counter)
                    ET.SubElement(phase_milestone, "{%s}OutlineNumber" % ns).text = str(deliverable_counter)
                    ET.SubElement(phase_milestone, "{%s}OutlineLevel" % ns).text = "1"
                    deliverable_counter += 1  # Increment for next milestone
                    ET.SubElement(phase_milestone, "{%s}Priority" % ns).text = "1000"  # High priority
                    ET.SubElement(phase_milestone, "{%s}Start" % ns).text = phase_date
                    ET.SubElement(phase_milestone, "{%s}Finish" % ns).text = phase_date
                    ET.SubElement(phase_milestone, "{%s}Duration" % ns).text = "PT0M"
                    ET.SubElement(phase_milestone, "{%s}DurationFormat" % ns).text = "7"
                    ET.SubElement(phase_milestone, "{%s}Work" % ns).text = "PT0M"
                    ET.SubElement(phase_milestone, "{%s}Summary" % ns).text = "0"
                    ET.SubElement(phase_milestone, "{%s}Critical" % ns).text = "1"
                    ET.SubElement(phase_milestone, "{%s}IsMarked" % ns).text = "1"
                    ET.SubElement(phase_milestone, "{%s}Notes" % ns).text = f"Phase gate at {(i+1)*25}% project completion"
                    
                    # Add custom field for milestone type
                    if add_custom_fields:
                        ext_attr_pg = ET.SubElement(phase_milestone, "{%s}ExtendedAttribute" % ns)
                        ET.SubElement(ext_attr_pg, "{%s}FieldID" % ns).text = "188743731"  # Text1
                        ET.SubElement(ext_attr_pg, "{%s}Value" % ns).text = "Phase Gate"
    
    # Add client approval milestone at the end
    if add_client_approval_milestone:
        approval_milestone = ET.SubElement(tasks, "{%s}Task" % ns)
        approval_uid = task_uid
        task_uid += 1
        
        ET.SubElement(approval_milestone, "{%s}UID" % ns).text = str(approval_uid)
        ET.SubElement(approval_milestone, "{%s}ID" % ns).text = str(approval_uid)
        ET.SubElement(approval_milestone, "{%s}Name" % ns).text = "CLIENT APPROVAL - FINAL"
        ET.SubElement(approval_milestone, "{%s}Type" % ns).text = "1"
        ET.SubElement(approval_milestone, "{%s}Milestone" % ns).text = "1"
        ET.SubElement(approval_milestone, "{%s}WBS" % ns).text = str(deliverable_counter)
        ET.SubElement(approval_milestone, "{%s}OutlineNumber" % ns).text = str(deliverable_counter)
        ET.SubElement(approval_milestone, "{%s}OutlineLevel" % ns).text = "1"
        deliverable_counter += 1  # Increment for consistency
        ET.SubElement(approval_milestone, "{%s}Priority" % ns).text = "1000"
        ET.SubElement(approval_milestone, "{%s}Start" % ns).text = current_date.isoformat()
        ET.SubElement(approval_milestone, "{%s}Finish" % ns).text = current_date.isoformat()
        ET.SubElement(approval_milestone, "{%s}Duration" % ns).text = "PT0M"
        ET.SubElement(approval_milestone, "{%s}DurationFormat" % ns).text = "7"
        ET.SubElement(approval_milestone, "{%s}Work" % ns).text = "PT0M"
        ET.SubElement(approval_milestone, "{%s}Summary" % ns).text = "0"
        ET.SubElement(approval_milestone, "{%s}Critical" % ns).text = "1"
        ET.SubElement(approval_milestone, "{%s}IsMarked" % ns).text = "1"
        ET.SubElement(approval_milestone, "{%s}Notes" % ns).text = "Final client approval and sign-off"
        
        # Add custom field for milestone type
        if add_custom_fields:
            ext_attr_ca = ET.SubElement(approval_milestone, "{%s}ExtendedAttribute" % ns)
            ET.SubElement(ext_attr_ca, "{%s}FieldID" % ns).text = "188743731"  # Text1
            ET.SubElement(ext_attr_ca, "{%s}Value" % ns).text = "Client Approval"
    
    # Add PredecessorLink elements for dependencies
    # FIX FOR ISSUE 1: Process dependencies for ALL task types (deliverables, components, AND leaf tasks)
    if add_dependencies:
        logging.info("[DEPENDENCIES] Processing Dependencies column for ALL task types (deliverables, components, leaf tasks)")
        
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
                        
                        logging.info(f"[DEPENDENCIES] ✓ Found predecessor UID={predecessor_uid} for WBS '{dep_wbs}'")
                        
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
                        logging.info(f"[DEPENDENCIES] ✓ Creating PredecessorLink: Task '{task_name_for_log}' (UID={task_uid}) → Predecessor UID={predecessor_uid} (Type=0, FS)")
                        
                        # FIX: Create PredecessorLink as child of task_elem using SubElement
                        # This ensures the link is properly attached to the task in the XML tree
                        pred_link = ET.SubElement(task_elem, "{%s}PredecessorLink" % ns)
                        ET.SubElement(pred_link, "{%s}PredecessorUID" % ns).text = str(predecessor_uid)
                        ET.SubElement(pred_link, "{%s}Type" % ns).text = "0"  # Type=0 is FS (Finish-to-Start)
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
    
    # FIX A: Build assignment data list BEFORE creating XML elements
    # This allows us to aggregate work by task and update Task.Work elements
    logging.info("[FIX A] Building assignment data structure before creating XML")
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
                # FIX B: Try child_hours_by_parent if task not found directly
                if parent_wbs in child_hours_by_parent:
                    logging.info(f"[FIX B] Using child hours aggregator for parent WBS '{parent_wbs}'")
                else:
                    logging.warning(f"[ROLE ASSIGNMENTS] Skipping role row at index {idx}: Parent WBS '{parent_wbs}' not found for Role={role}")
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
    
    for assign_data in assignment_data_list:
        res_uid = assign_data.get("ResourceUID")
        if res_uid not in valid_resource_uids:
            invalid_assignments.append({
                "task_uid": assign_data.get("TaskUID"),
                "resource_uid": res_uid,
                "assignment_uid": assign_data.get("AssignmentUID")
            })
    
    assert len(invalid_assignments) == 0, \
        f"CRITICAL: {len(invalid_assignments)} assignments reference invalid ResourceUIDs: {invalid_assignments}"
    
    logging.info(f"[ASSIGNMENT VALIDATION] ✓ All {len(assignment_data_list)} assignments reference valid Resource UIDs")
    
    # FIX A & E: Update Task.Work and Task.Cost elements from aggregated assignments
    logging.info("[FIX A & E] Updating Task.Work and Task.Cost from aggregated assignments")
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
                        work_elem.text = f"PT{planned_minutes}M"
                    else:
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
                    logging.info(f"[FIX A & E] Updated task '{task_name}' (UID={task_uid}): Work={planned_minutes}M, Cost=${task_cost:.2f}")
                break
    
    # Create Assignments container with enhanced resource assignments
    logging.info("[FIX A] Creating Assignment XML elements from assignment data")
    assignments = ET.SubElement(root, "{%s}Assignments" % ns)
    
    # Create assignment XML elements from assignment_data_list
    for assignment_data in assignment_data_list:
        assign = ET.SubElement(assignments, "{%s}Assignment" % ns)
        ET.SubElement(assign, "{%s}UID" % ns).text = str(assignment_data["AssignmentUID"])
        ET.SubElement(assign, "{%s}TaskUID" % ns).text = str(assignment_data["TaskUID"])
        ET.SubElement(assign, "{%s}ResourceUID" % ns).text = str(assignment_data["ResourceUID"])
        ET.SubElement(assign, "{%s}Units" % ns).text = "100"  # 100% allocation
        
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
    
    # Write the XML file
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(output_xml, encoding="utf-8", xml_declaration=True)
    
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
        "assignment_count": assignment_uid - 1,
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
        "has_phase_gates": add_phase_gates,
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
    
    ET.SubElement(root, "{%s}CalendarUID" % ns).text = "1"
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
    # Test the enhanced converter
    test_xlsx = "test.xlsx"
    test_xml = "test_enhanced.xml"
    
    if os.path.exists(test_xlsx):
        stats = convert_excel_to_mspdi(
            input_xlsx=test_xlsx,
            output_xml=test_xml,
            project_name="Enhanced Test Project",
            add_deliverable_milestones=True,
            add_phase_gates=True,
            add_dependencies=True,
            add_custom_fields=True
        )
        print(f"Enhanced conversion complete: {stats}")
    else:
        print(f"Test file {test_xlsx} not found")