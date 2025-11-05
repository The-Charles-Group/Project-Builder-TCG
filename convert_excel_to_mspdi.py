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
    ET.SubElement(task, "{%s}OutlineLevel" % ns).text = str(wbs_level.count('.') + 1)
    
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
    add_deliverable_milestones: bool = True,
    add_phase_gates: bool = True,
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
        add_deliverable_milestones: Add milestone tasks for deliverables
        add_phase_gates: Add phase gate milestones at 25%, 50%, 75%
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
        ET.SubElement(ext_attr1, "{%s}FieldID" % ns).text = "188743731"  # Task Number1
        ET.SubElement(ext_attr1, "{%s}FieldName" % ns).text = "Number1"
        ET.SubElement(ext_attr1, "{%s}Alias" % ns).text = "Risk Score"
        ET.SubElement(ext_attr1, "{%s}Guid" % ns).text = "000039B7-8BBE-4CEB-82C4-FA8C0B400033"
        
        # Custom Field 2: Confidence Level (Number)
        ext_attr2 = ET.SubElement(extended_attrs, "{%s}ExtendedAttribute" % ns)
        ET.SubElement(ext_attr2, "{%s}FieldID" % ns).text = "188743732"  # Task Number2
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
        ET.SubElement(res, "{%s}StandardRate" % ns).text = f"${blended_rate or 150:.2f}/h"
        ET.SubElement(res, "{%s}StandardRateFormat" % ns).text = "2"  # Per hour
        ET.SubElement(res, "{%s}OvertimeRate" % ns).text = f"${(blended_rate or 150) * 1.5:.2f}/h"
        ET.SubElement(res, "{%s}OvertimeRateFormat" % ns).text = "2"
        ET.SubElement(res, "{%s}CostPerUse" % ns).text = "0"
        ET.SubElement(res, "{%s}CalendarUID" % ns).text = "1"
        
        department_resources[str(dept)] = resource_id
        resource_id += 1
    
    # Add individual role resources
    if "Role" in df.columns:
        role_series = df["Role"] if isinstance(df["Role"], pd.Series) else pd.Series(df["Role"])
        unique_roles = role_series.dropna().unique()
        for role in unique_roles:
            res = ET.SubElement(resources, "{%s}Resource" % ns)
            ET.SubElement(res, "{%s}UID" % ns).text = str(resource_id)
            ET.SubElement(res, "{%s}ID" % ns).text = str(resource_id)
            ET.SubElement(res, "{%s}Name" % ns).text = str(role)
            ET.SubElement(res, "{%s}Initials" % ns).text = "".join([w[0] for w in str(role).split()[:3]])
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
                ET.SubElement(res, "{%s}StandardRate" % ns).text = f"${blended_rate:.2f}/h"
            elif "Rate_USD" in df.columns:
                role_rate = df[df["Role"] == role]["Rate_USD"].dropna().iloc[0] if not df[df["Role"] == role]["Rate_USD"].dropna().empty else 150
                ET.SubElement(res, "{%s}StandardRate" % ns).text = f"${role_rate:.2f}/h"
            else:
                ET.SubElement(res, "{%s}StandardRate" % ns).text = "$150.00/h"
            
            ET.SubElement(res, "{%s}StandardRateFormat" % ns).text = "2"
            ET.SubElement(res, "{%s}OvertimeRate" % ns).text = f"${(blended_rate or 150) * 1.5:.2f}/h"
            ET.SubElement(res, "{%s}OvertimeRateFormat" % ns).text = "2"
            ET.SubElement(res, "{%s}CostPerUse" % ns).text = "0"
            ET.SubElement(res, "{%s}CalendarUID" % ns).text = "1"
            
            resource_map[str(role)] = resource_id
            resource_id += 1
    
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
    deliverable_tasks = {}  # Track deliverable summary tasks for dependencies
    component_tasks = {}    # Track component tasks for dependencies
    current_date = project_start
    deliverable_ends = {}
    all_task_uids = []  # Track all task UIDs for phase gates
    
    # Calculate total project timeline for phase gates
    total_rows = len(df)
    phase_gate_positions = []
    if add_phase_gates:
        phase_gate_positions = [
            int(total_rows * 0.25),  # 25% milestone
            int(total_rows * 0.50),  # 50% milestone
            int(total_rows * 0.75),  # 75% milestone
        ]
    
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
            
            # Get deliverable code if available
            deliv_code = ""
            if "Deliverable_Code" in group.columns:
                deliv_code = str(group["Deliverable_Code"].iloc[0]) if not group["Deliverable_Code"].empty else ""
            
            ET.SubElement(deliv_task, "{%s}UID" % ns).text = str(deliv_uid)
            ET.SubElement(deliv_task, "{%s}ID" % ns).text = str(deliv_uid)
            ET.SubElement(deliv_task, "{%s}Name" % ns).text = str(deliverable_name)
            ET.SubElement(deliv_task, "{%s}Type" % ns).text = "1"  # Fixed Duration
            ET.SubElement(deliv_task, "{%s}IsNull" % ns).text = "0"
            ET.SubElement(deliv_task, "{%s}WBS" % ns).text = str(deliverable_num)
            ET.SubElement(deliv_task, "{%s}OutlineNumber" % ns).text = str(deliverable_num)
            ET.SubElement(deliv_task, "{%s}OutlineLevel" % ns).text = "1"
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
            if add_custom_fields and deliv_code:
                ext_attrs = ET.SubElement(deliv_task, "{%s}ExtendedAttribute" % ns)
                ET.SubElement(ext_attrs, "{%s}FieldID" % ns).text = "188743732"
                ET.SubElement(ext_attrs, "{%s}Value" % ns).text = deliv_code
            
            # Process component/task rows under this deliverable
            deliverable_start = deliverable_start_date  # Use merged start date from Gantt
            # Use merged end date from Gantt if available, otherwise will be calculated from child tasks
            deliverable_finish = deliverable_end_date if deliverable_end_date else deliverable_start_date
            
            # Group tasks by Component within this deliverable to create 3-level hierarchy
            logging.info(f"[3-LEVEL HIERARCHY] Processing deliverable '{deliverable_name}' with component grouping")
            try:
                if "Component" in group.columns:
                    # FIX: Convert Component column to object type and fill NaN with "Uncategorized"
                    # This prevents issues with categorical types that don't allow null values
                    group_copy = group.copy()
                    
                    # Convert categorical to object if needed
                    if pd.api.types.is_categorical_dtype(group_copy["Component"]):
                        logging.info(f"[3-LEVEL HIERARCHY] Converting Component from categorical to object type")
                        group_copy["Component"] = group_copy["Component"].astype(object)
                    
                    # FIX: Fill blank/NaN component values with "Uncategorized" BEFORE groupby
                    # Check for NaN, None, and empty strings
                    blank_mask = group_copy["Component"].isna() | (group_copy["Component"] == "") | group_copy["Component"].isnull()
                    blank_count = blank_mask.sum()
                    if blank_count > 0:
                        logging.info(f"[3-LEVEL HIERARCHY] Found {blank_count} tasks with blank Component, setting to 'Uncategorized'")
                        group_copy.loc[blank_mask, "Component"] = "Uncategorized"
                    
                    # Now groupby will work correctly without dropna issues
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
            
            # Loop through each component (Level 2)
            for component_name, component_group in component_grouped:
                component_num += 1
                
                # Create component summary task (Level 2)
                comp_task = ET.SubElement(tasks, "{%s}Task" % ns)
                comp_uid = task_uid
                task_uid += 1
                all_task_uids.append(comp_uid)
                
                # Store component task for dependencies
                component_tasks[f"{deliverable_name}:{component_name}"] = comp_uid
                
                logging.info(f"[3-LEVEL HIERARCHY] Creating component summary task: '{component_name}' (UID={comp_uid})")
                
                # Component task properties
                ET.SubElement(comp_task, "{%s}UID" % ns).text = str(comp_uid)
                ET.SubElement(comp_task, "{%s}ID" % ns).text = str(comp_uid)
                ET.SubElement(comp_task, "{%s}Name" % ns).text = str(component_name) if component_name else "Uncategorized"
                ET.SubElement(comp_task, "{%s}Type" % ns).text = "1"  # Fixed Duration
                ET.SubElement(comp_task, "{%s}IsNull" % ns).text = "0"
                ET.SubElement(comp_task, "{%s}WBS" % ns).text = f"{deliverable_num}.{component_num}"
                ET.SubElement(comp_task, "{%s}OutlineNumber" % ns).text = f"{deliverable_num}.{component_num}"
                ET.SubElement(comp_task, "{%s}OutlineLevel" % ns).text = "2"  # Component level
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
                
                # Track component start/finish dates
                component_start = current_date
                component_finish = current_date
                task_num_in_component = 0
                
                # Loop through tasks within this component (Level 3)
                for idx, row in component_group.iterrows():
                    try:
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
                        
                        # Add task elements with 3-level WBS
                        ET.SubElement(task, "{%s}UID" % ns).text = str(uid)
                        ET.SubElement(task, "{%s}ID" % ns).text = str(uid)
                        ET.SubElement(task, "{%s}Name" % ns).text = str(task_name)
                        ET.SubElement(task, "{%s}Type" % ns).text = "0"  # Fixed units
                        ET.SubElement(task, "{%s}IsNull" % ns).text = "0"
                        ET.SubElement(task, "{%s}WBS" % ns).text = f"{deliverable_num}.{component_num}.{task_num_in_component}"
                        ET.SubElement(task, "{%s}OutlineNumber" % ns).text = f"{deliverable_num}.{component_num}.{task_num_in_component}"
                        ET.SubElement(task, "{%s}OutlineLevel" % ns).text = "3"  # Task level (Level 3)
                        ET.SubElement(task, "{%s}Priority" % ns).text = "500"
                        ET.SubElement(task, "{%s}Start" % ns).text = task_start.isoformat()
                        ET.SubElement(task, "{%s}Finish" % ns).text = task_end.isoformat()
                        ET.SubElement(task, "{%s}Duration" % ns).text = f"PT{int(hours * 60)}M"
                        ET.SubElement(task, "{%s}DurationFormat" % ns).text = "7"  # Days
                        ET.SubElement(task, "{%s}Work" % ns).text = f"PT{int(hours * 60)}M"
                        ET.SubElement(task, "{%s}RegularWork" % ns).text = f"PT{int(hours * 60)}M"
                        ET.SubElement(task, "{%s}RemainingDuration" % ns).text = f"PT{int(hours * 60)}M"
                        ET.SubElement(task, "{%s}RemainingWork" % ns).text = f"PT{int(hours * 60)}M"
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
                        
                        # Add cost if available
                        price_usd = row.get("Price_USD") if hasattr(row, 'get') else row["Price_USD"] if "Price_USD" in row.index else None
                        if price_usd is not None and pd.notna(price_usd):
                            try:
                                price_value = float(price_usd)
                                ET.SubElement(task, "{%s}Cost" % ns).text = str(price_value)
                                ET.SubElement(task, "{%s}FixedCost" % ns).text = str(price_value)
                                ET.SubElement(task, "{%s}FixedCostAccrual" % ns).text = "2"  # Prorated
                            except (ValueError, TypeError):
                                pass
                        
                        # Add extended attributes (custom fields) for each task
                        if add_custom_fields:
                            # Risk Score (random for demo)
                            ext_attr_risk = ET.SubElement(task, "{%s}ExtendedAttribute" % ns)
                            ET.SubElement(ext_attr_risk, "{%s}FieldID" % ns).text = "188743731"  # Number1
                            ET.SubElement(ext_attr_risk, "{%s}Value" % ns).text = str(random.randint(1, 10))
                            
                            # Confidence Level (random 70-100)
                            ext_attr_conf = ET.SubElement(task, "{%s}ExtendedAttribute" % ns)
                            ET.SubElement(ext_attr_conf, "{%s}FieldID" % ns).text = "188743732"  # Number2
                            ET.SubElement(ext_attr_conf, "{%s}Value" % ns).text = str(random.randint(70, 100))
                            
                            # Department
                            if department:
                                ext_attr_dept = ET.SubElement(task, "{%s}ExtendedAttribute" % ns)
                                ET.SubElement(ext_attr_dept, "{%s}FieldID" % ns).text = "188743731"  # Text1
                                ET.SubElement(ext_attr_dept, "{%s}Value" % ns).text = str(department)
                            
                            # Deliverable Code
                            if deliv_code:
                                ext_attr_dc = ET.SubElement(task, "{%s}ExtendedAttribute" % ns)
                                ET.SubElement(ext_attr_dc, "{%s}FieldID" % ns).text = "188743732"  # Text2
                                ET.SubElement(ext_attr_dc, "{%s}Value" % ns).text = deliv_code
                            
                            # Component Name
                            ext_attr_comp = ET.SubElement(task, "{%s}ExtendedAttribute" % ns)
                            ET.SubElement(ext_attr_comp, "{%s}FieldID" % ns).text = "188743733"  # Text3
                            ET.SubElement(ext_attr_comp, "{%s}Value" % ns).text = str(component_name)
                        
                        # Track component finish date
                        if task_num_in_component == 1:
                            component_start = task_start
                        if task_end > component_finish:
                            component_finish = task_end
                        
                        # Track deliverable finish date (only if not already set from Gantt)
                        # If user set End_Date in Gantt, respect that value
                        if deliverable_end_date is None:
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
                        
                    except Exception as e:
                        logging.error(f"Error processing task at index {idx}: {e}")
                        task_uid -= 1  # Decrement to maintain correct count
                
                # Update component summary with calculated duration
                duration_hours = calculate_business_hours(component_start, component_finish)
                ET.SubElement(comp_task, "{%s}Duration" % ns).text = f"PT{int(duration_hours * 60)}M"
                ET.SubElement(comp_task, "{%s}Finish" % ns).text = component_finish.isoformat()
                
                # Update current_date to end of this component for next component to start
                current_date = component_finish
                
                logging.info(f"[3-LEVEL HIERARCHY] Component '{component_name}' completed with {task_num_in_component} tasks")
            
            # Update deliverable summary with calculated duration
            duration_hours = calculate_business_hours(deliverable_start, deliverable_finish)
            ET.SubElement(deliv_task, "{%s}Duration" % ns).text = f"PT{int(duration_hours * 60)}M"
            ET.SubElement(deliv_task, "{%s}Finish" % ns).text = deliverable_finish.isoformat()
            deliverable_ends[deliverable_name] = deliverable_finish
            
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
                    ET.SubElement(phase_milestone, "{%s}WBS" % ns).text = f"999.{i+1}"
                    ET.SubElement(phase_milestone, "{%s}OutlineNumber" % ns).text = f"999.{i+1}"
                    ET.SubElement(phase_milestone, "{%s}OutlineLevel" % ns).text = "1"
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
    if add_deliverable_milestones:
        approval_milestone = ET.SubElement(tasks, "{%s}Task" % ns)
        approval_uid = task_uid
        task_uid += 1
        
        ET.SubElement(approval_milestone, "{%s}UID" % ns).text = str(approval_uid)
        ET.SubElement(approval_milestone, "{%s}ID" % ns).text = str(approval_uid)
        ET.SubElement(approval_milestone, "{%s}Name" % ns).text = "CLIENT APPROVAL - FINAL"
        ET.SubElement(approval_milestone, "{%s}Type" % ns).text = "1"
        ET.SubElement(approval_milestone, "{%s}Milestone" % ns).text = "1"
        ET.SubElement(approval_milestone, "{%s}WBS" % ns).text = "999.99"
        ET.SubElement(approval_milestone, "{%s}OutlineNumber" % ns).text = "999.99"
        ET.SubElement(approval_milestone, "{%s}OutlineLevel" % ns).text = "1"
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
    if add_dependencies:
        logging.info("[3-LEVEL HIERARCHY] Adding component-level dependencies (tasks within components run in parallel)")
        
        # NOTE: Sequential chaining of all tasks removed - causes unrealistic timeline
        # Tasks within a component should run in parallel
        # Only add cross-department dependencies if needed
        
        # Identify logical dependencies
        for uid, task_data in task_map.items():
            task = task_data["task"]
            
            # REMOVED: Sequential chaining (prev_task logic)
            # This was causing all tasks to chain sequentially, resulting in unrealistic timeline
            # Tasks within a component should run in parallel
            
            # Add cross-deliverable dependencies based on department logic
            department = task_data["department"]
            deliverable = task_data["deliverable"]
            
            # Define department dependencies
            dept_dependencies = {
                "Creative": ["Strategy"],
                "Paid Media": ["Creative", "Strategy"],
                "Technology": ["Strategy"],
                "Content": ["Strategy", "Creative"],
                "Quality Assurance": ["Technology", "Content"]
            }
            
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
    
    # Create Assignments container with enhanced resource assignments
    assignments = ET.SubElement(root, "{%s}Assignments" % ns)
    assignment_uid = 1
    
    # Create resource assignments
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
            assign = ET.SubElement(assignments, "{%s}Assignment" % ns)
            ET.SubElement(assign, "{%s}UID" % ns).text = str(assignment_uid)
            ET.SubElement(assign, "{%s}TaskUID" % ns).text = str(uid)
            ET.SubElement(assign, "{%s}ResourceUID" % ns).text = str(department_resources[department])
            ET.SubElement(assign, "{%s}Units" % ns).text = "100"  # 100% allocation
            ET.SubElement(assign, "{%s}Work" % ns).text = f"PT{int(work_hours * 60)}M"
            ET.SubElement(assign, "{%s}RegularWork" % ns).text = f"PT{int(work_hours * 60)}M"
            ET.SubElement(assign, "{%s}RemainingWork" % ns).text = f"PT{int(work_hours * 60)}M"
            ET.SubElement(assign, "{%s}Start" % ns).text = task.find("{%s}Start" % ns).text
            ET.SubElement(assign, "{%s}Finish" % ns).text = task.find("{%s}Finish" % ns).text
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
            ET.SubElement(assign, "{%s}Cost" % ns).text = str(work_hours * (blended_rate or 150))
            ET.SubElement(assign, "{%s}BCWS" % ns).text = "0"
            ET.SubElement(assign, "{%s}BCWP" % ns).text = "0"
            ET.SubElement(assign, "{%s}ACWP" % ns).text = "0"
            ET.SubElement(assign, "{%s}SV" % ns).text = "0"
            ET.SubElement(assign, "{%s}CostVariance" % ns).text = "0"
            ET.SubElement(assign, "{%s}WorkContour" % ns).text = "0"  # Flat
            ET.SubElement(assign, "{%s}StartSlack" % ns).text = "0"
            ET.SubElement(assign, "{%s}FinishSlack" % ns).text = "0"
            ET.SubElement(assign, "{%s}VAC" % ns).text = "0"
            
            assignment_uid += 1
    
    # Write the XML file
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(output_xml, encoding="utf-8", xml_declaration=True)
    
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
        "has_phase_gates": add_phase_gates
    }
    
    logging.info(f"[Enhanced MSPDI] Created {output_xml}: {stats['task_count']} tasks, {stats['resource_count']} resources, {stats['milestone_count']} milestones")
    
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