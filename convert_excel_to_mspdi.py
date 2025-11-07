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


# GPT-5 PRO FIX 1 & 5: Comprehensive Dependency Rules Table for "Seasoned PM Brain"
# Maps component/task type relationships to (dependency_type, lag_days)
# MSPDI Type codes: 0=FF, 1=FS, 2=SF, 3=SS
# Negative lag = lead time, Positive lag = delay
DEPENDENCY_RULES = {
    # === Discovery & Research Phase ===
    ("Discovery", "Research"): (3, 2),       # SS + 2d: Research can start 2 days after Discovery begins
    ("Discovery", "Strategy"): (3, 2),       # SS + 2d: Strategy overlaps with Discovery
    ("Discovery", "Analysis"): (3, 1),       # SS + 1d: Analysis can start shortly after Discovery
    ("Research", "Strategy"): (1, 0),        # FS + 0d: Strategy waits for Research to finish
    ("Research", "Analysis"): (3, 1),        # SS + 1d: Analysis can overlap with Research
    ("Analysis", "Strategy"): (1, 0),        # FS + 0d: Strategy waits for Analysis
    
    # === Strategy Phase ===
    ("Strategy", "Creative"): (1, 0),        # FS + 0d: Creative waits for Strategy
    ("Strategy", "Design"): (1, 0),          # FS + 0d: Design waits for Strategy
    ("Strategy", "Copywriting"): (1, 0),     # FS + 0d: Copy waits for Strategy
    ("Strategy", "Planning"): (1, 0),        # FS + 0d: Planning waits for Strategy
    ("Strategy", "Development"): (1, 2),     # FS + 2d: Dev starts 2 days after Strategy finishes
    ("Strategy", "Media"): (1, 1),           # FS + 1d: Media planning starts after Strategy
    
    # === Creative & Design Phase ===
    ("Copywriting", "Design"): (1, 0),       # FS + 0d: Design waits for final copy
    ("Copy", "Design"): (1, 0),              # FS + 0d: Design waits for copy
    ("Creative", "Design"): (3, 1),          # SS + 1d: Design can start shortly after Creative begins
    ("Design", "Development"): (1, 0),       # FS + 0d: Dev waits for Design
    ("Design", "Production"): (1, 0),        # FS + 0d: Production waits for Design
    ("Creative", "Production"): (1, 0),      # FS + 0d: Production waits for Creative
    ("Design", "QA"): (1, 0),                # FS + 0d: QA waits for Design
    ("Design", "Review"): (1, 0),            # FS + 0d: Review waits for Design
    
    # === Development Phase ===
    ("Development", "Testing"): (3, 3),      # SS + 3d: Testing can start when Dev is ~30% in
    ("Development", "QA"): (3, 3),           # SS + 3d: QA can start when Dev is ~30% in
    ("Dev", "Quality Assurance"): (3, 3),    # SS + 3d: QA overlaps with Development
    ("Dev", "Testing"): (3, 3),              # SS + 3d: Testing overlaps with Development
    ("Development", "Review"): (3, 5),       # SS + 5d: Review can start when Dev is ~50% in
    ("Development", "Launch"): (1, 2),       # FS + 2d: Launch waits 2 days after Dev finishes
    
    # === QA & Testing Phase ===
    ("QA", "Launch"): (1, 1),                # FS + 1d: Launch waits 1 day after QA finishes
    ("Testing", "Launch"): (1, 1),           # FS + 1d: Launch waits 1 day after Testing
    ("Quality Assurance", "Launch"): (1, 1), # FS + 1d: Launch waits after QA
    ("QA", "Production"): (1, 0),            # FS + 0d: Production waits for QA
    ("Testing", "Production"): (1, 0),       # FS + 0d: Production waits for Testing
    ("QA", "Deployment"): (1, 0),            # FS + 0d: Deployment waits for QA
    ("Testing", "Deployment"): (1, 0),       # FS + 0d: Deployment waits for Testing
    
    # === Review & Approval Phase ===
    ("Review", "Approval"): (1, 0),          # FS + 0d: Approval waits for Review
    ("Review", "Launch"): (1, 1),            # FS + 1d: Launch waits after Review
    ("Approval", "Launch"): (1, 0),          # FS + 0d: Launch waits for Approval
    ("Approval", "Production"): (1, 0),      # FS + 0d: Production waits for Approval
    ("Review", "Production"): (1, 1),        # FS + 1d: Production waits after Review
    
    # === Media & Content Phase ===
    ("Media", "QA"): (1, 0),                 # FS + 0d: QA waits for Media
    ("Content", "Review"): (1, 0),           # FS + 0d: Review waits for Content
    ("Content", "QA"): (1, 0),               # FS + 0d: QA waits for Content
    ("Media", "Launch"): (1, 1),             # FS + 1d: Launch waits after Media
    ("Content", "Production"): (1, 0),       # FS + 0d: Production waits for Content
    
    # === Production & Launch Phase ===
    ("Production", "Launch"): (1, 0),        # FS + 0d: Launch waits for Production
    ("Production", "Deployment"): (1, 0),    # FS + 0d: Deployment waits for Production
    ("Deployment", "Launch"): (1, 0),        # FS + 0d: Launch waits for Deployment
    
    # === Planning & Execution ===
    ("Planning", "Execution"): (1, 0),       # FS + 0d: Execution waits for Planning
    ("Planning", "Development"): (1, 1),     # FS + 1d: Development starts after Planning
    ("Planning", "Design"): (1, 0),          # FS + 0d: Design waits for Planning
    
    # === Common Cross-Phase Dependencies ===
    ("Strategy", "QA"): (1, 5),              # FS + 5d: QA starts well after Strategy
    ("Strategy", "Launch"): (1, 10),         # FS + 10d: Launch is far downstream from Strategy
    ("Discovery", "Launch"): (1, 15),        # FS + 15d: Launch is end of project from Discovery
    ("Research", "Launch"): (1, 12),         # FS + 12d: Launch is far downstream from Research
}


def link_for(pred_task_name: str, succ_task_name: str, pred_component: Optional[str] = None, succ_component: Optional[str] = None) -> Tuple[int, int]:
    """
    GPT-5 PRO FIX 1: Determine dependency type and lag based on task relationships.
    
    Uses "seasoned PM" rules to determine realistic overlaps and dependencies.
    
    Args:
        pred_task_name: Name of predecessor task
        succ_task_name: Name of successor task
        pred_component: Component name of predecessor (optional)
        succ_component: Component name of successor (optional)
        
    Returns:
        Tuple of (type_code, lag_days) where:
        - type_code: 0=FF, 1=FS, 2=SF, 3=SS
        - lag_days: Number of days lag (positive for delay, negative for lead)
    """
    # Try component-level match first
    if pred_component and succ_component:
        rule_key = (pred_component, succ_component)
        if rule_key in DEPENDENCY_RULES:
            return DEPENDENCY_RULES[rule_key]
    
    # Try task-name-level match (e.g., "Research" in task name)
    for (pred_pattern, succ_pattern), (dep_type, lag) in DEPENDENCY_RULES.items():
        if pred_pattern.lower() in pred_task_name.lower() and succ_pattern.lower() in succ_task_name.lower():
            return (dep_type, lag)
    
    # Default to Finish-to-Start with no lag
    return (1, 0)  # FS + 0 days


def parse_dependency_spec(dep_str):
    """
    Parse dependency specification like 'SS+2d', 'FS+0', 'FF-1d', 'SF+8h'
    
    Returns:
        tuple: (mspdi_type_code, lag_days)
        
    Examples:
        'SS+2d' -> ('2', 2)  # Start-to-Start with 2-day lag
        'FS+0' -> ('1', 0)   # Finish-to-Start with no lag
        'FF-1d' -> ('3', -1) # Finish-to-Finish with 1-day lead
        'SF+8h' -> ('4', 1)  # Start-to-Finish with 1-day lag (8h rounds to 1d)
    """
    # CRITICAL ERROR #1 FIX: CORRECT MSPDI type codes per standard
    # FS=1, SS=2, FF=3, SF=4 (NOT the old incorrect values!)
    TYPE_MAP = {"FS": "1", "SS": "2", "FF": "3", "SF": "4"}
    LAG_UNITS = {"H": 60, "D": 480, "M": 1}  # hours, days, minutes (uppercase for matching)
    
    # Default to FS+0 if parsing fails
    dep_str = str(dep_str).strip().upper()
    if not dep_str:
        return ("1", 0)
    
    # Extract type (FS, SS, FF, SF)
    dep_type = "FS"  # default
    for t in TYPE_MAP.keys():
        if dep_str.startswith(t):
            dep_type = t
            dep_str = dep_str[len(t):]
            break
    
    # Extract lag (e.g., '+2d', '-1d', '+8h')
    lag_minutes = 0
    if dep_str:
        # Parse sign
        sign = 1
        if dep_str[0] == '+':
            dep_str = dep_str[1:]
        elif dep_str[0] == '-':
            sign = -1
            dep_str = dep_str[1:]
        
        # Parse value and unit
        if dep_str:
            # Extract numeric part
            num_str = ""
            unit = "D"  # default to days
            for char in dep_str:
                if char.isdigit() or char == '.':
                    num_str += char
                elif char in LAG_UNITS:
                    unit = char
                    break
            
            if num_str:
                lag_value = float(num_str)
                lag_minutes = int(sign * lag_value * LAG_UNITS[unit])
    
    # CRITICAL ERROR #2 FIX: Convert to days (not minutes) for LagFormat=7
    # LinkLag should be in DAYS when LagFormat=7, not minutes!
    lag_days = lag_minutes // 480  # Convert to whole days (480 min/day)
    return (TYPE_MAP[dep_type], lag_days)


# Test cases for parse_dependency_spec function
# These demonstrate the expected behavior:
# parse_dependency_spec("SS+2d") should return ("3", 960)  # Start-to-Start with 2-day lag
# parse_dependency_spec("FS+0") should return ("1", 0)     # Finish-to-Start with no lag
# parse_dependency_spec("FF-1d") should return ("0", -480) # Finish-to-Finish with 1-day lead
# parse_dependency_spec("SF+8h") should return ("2", 480)  # Start-to-Finish with 8-hour lag


# CRITICAL ERROR #3 FIX: Move calendar helper functions BEFORE they are used (line 979)
# Business calendar configuration
# Two working blocks per day: 9am-12pm (morning) and 1pm-6pm (afternoon)
BUS_BLOCKS = [(datetime.min.time().replace(hour=9, minute=0), datetime.min.time().replace(hour=12, minute=0)),
              (datetime.min.time().replace(hour=13, minute=0), datetime.min.time().replace(hour=18, minute=0))]


def is_business_day(date) -> bool:
    """Check if a date is a business day (Monday-Friday)"""
    if isinstance(date, datetime):
        date = date.date()
    return date.weekday() < 5  # Monday=0, Friday=4


def add_business_minutes(dt, minutes):
    """
    Add working minutes to a datetime, skipping non-business time.
    Uses BUS_BLOCKS: [(time(9,0), time(12,0)), (time(13,0), time(18,0))]
    
    Args:
        dt: Starting datetime
        minutes: Number of working minutes to add
        
    Returns:
        Ending datetime after adding working minutes
    """
    from datetime import datetime as _dt, timedelta as _td, time
    
    def _in_block(t):
        """Check if time is within any business block"""
        return any(a <= t < b for a, b in BUS_BLOCKS)
    
    rem = int(minutes)
    cur = dt
    
    while rem > 0:
        # Advance to next working minute if needed
        if not is_business_day(cur.date()) or not _in_block(cur.time()):
            # Jump to next valid block start
            moved = False
            for a, b in BUS_BLOCKS:
                if cur.time() < a and is_business_day(cur.date()):
                    cur = _dt.combine(cur.date(), a)
                    moved = True
                    break
            if not moved:
                # Move to next business day
                d = cur.date() + timedelta(days=1)
                while not is_business_day(d):
                    d += timedelta(days=1)
                cur = _dt.combine(d, BUS_BLOCKS[0][0])
            continue
        
        # Within a working block: consume up to end of block or rem
        for a, b in BUS_BLOCKS:
            if a <= cur.time() < b:
                can = int((_dt.combine(cur.date(), b) - cur).total_seconds() // 60)
                step = min(rem, can)
                cur += _td(minutes=step)
                rem -= step
                break
    
    return cur


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
        # CRITICAL: Normalize time to business hours (09:00) regardless of input time
        project_start = project_start.replace(hour=9, minute=0, second=0, microsecond=0)
        logging.info(f"[TIME NORMALIZATION] Normalized project_start to 09:00:00: {project_start.isoformat()}")
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
    department_resources = {}
    resource_id = 1
    
    # FIX ISSUE 1: Track max_resource_uid globally to prevent duplicate UIDs
    max_resource_uid = 0
    
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
        ET.SubElement(res, "{%s}MaxUnits" % ns).text = "1"  # 1.0 = 100% capacity (MSPDI ratio format)
        ET.SubElement(res, "{%s}PeakUnits" % ns).text = "1"  # 1.0 = 100% peak capacity
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
        max_resource_uid = resource_id  # FIX ISSUE 1: Track highest UID
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
            ET.SubElement(res, "{%s}MaxUnits" % ns).text = "1"  # 1.0 = 100% capacity (MSPDI ratio format)
            ET.SubElement(res, "{%s}PeakUnits" % ns).text = "1"  # 1.0 = 100% peak capacity
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
            elif "Rate_USD" in df.columns:
                role_rate = df[df["Role"] == role]["Rate_USD"].dropna().iloc[0] if not df[df["Role"] == role]["Rate_USD"].dropna().empty else 150
                ET.SubElement(res, "{%s}StandardRate" % ns).text = f"{role_rate:.2f}"
            else:
                ET.SubElement(res, "{%s}StandardRate" % ns).text = "150.00"
            
            ET.SubElement(res, "{%s}StandardRateFormat" % ns).text = "2"
            ET.SubElement(res, "{%s}OvertimeRate" % ns).text = f"{(blended_rate or 150) * 1.5:.2f}"
            ET.SubElement(res, "{%s}OvertimeRateFormat" % ns).text = "2"
            ET.SubElement(res, "{%s}CostPerUse" % ns).text = "0"
            ET.SubElement(res, "{%s}CalendarUID" % ns).text = "1"
            
            resource_map[str(role)] = resource_id
            max_resource_uid = resource_id  # FIX ISSUE 1: Track highest UID
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
    # Add Finish element immediately (will be updated after deliverables are processed)
    # This ensures proper XML element ordering per MS Project schema
    project_task_finish = ET.SubElement(project_task, "{%s}Finish" % ns)
    project_task_finish.text = project_start.isoformat()  # Initial value, will be updated
    logging.info(f"[PROJECT] Initialized project Finish date to: {project_start.isoformat()}")
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
    project_finish_date = project_start  # Track the maximum deliverable finish date for project summary task
    
    # Initialize cost and duration accumulators for aggregation
    deliverable_costs = {}  # {deliv_uid: total_cost}
    component_costs = {}    # {comp_uid: total_cost}
    deliverable_task_hours = {}  # {deliv_uid: sum_of_child_hours}
    component_task_hours = {}    # {comp_uid: sum_of_child_hours}
    
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
            deliverable_tasks[str(deliverable_name)] = deliv_uid
            
            # Initialize cost accumulator for this deliverable
            deliverable_costs[deliv_uid] = 0.0
            deliverable_task_hours[deliv_uid] = 0.0
            
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
                            deliverable_start_date = datetime.fromisoformat(start_val)
                        # CRITICAL: Always normalize time to 09:00 regardless of input
                        deliverable_start_date = deliverable_start_date.replace(hour=9, minute=0, second=0, microsecond=0)
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
                            deliverable_end_date = datetime.fromisoformat(end_val)
                        # CRITICAL: Always normalize time to 09:00 regardless of input
                        deliverable_end_date = deliverable_end_date.replace(hour=9, minute=0, second=0, microsecond=0)
                        logging.info(f"[GANTT MERGE] Deliverable '{deliverable_name}' End: {deliverable_end_date.isoformat()}")
                    except Exception as e:
                        logging.warning(f"Could not parse deliverable End_Date '{first_row_end}': {e}")
            
            ET.SubElement(deliv_task, "{%s}Start" % ns).text = deliverable_start_date.isoformat()
            
            # FIX ISSUE 3: DO NOT add constraints to summary tasks (violates MSPDI rules)
            # Summary tasks auto-calculate dates from children - constraints cause Workfront import errors
            # Note: Deliverable tasks are summary tasks (Summary=1 is set on line 677)
            # Constraints will be applied only to leaf tasks (non-summary tasks) below
            
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
                
                # Service Category (replaces Category tag for Workfront)
                category_value = service_dept if service_dept else "Unassigned"
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
                
                # Initialize cost accumulator for this component
                component_costs[comp_uid] = 0.0
                component_task_hours[comp_uid] = 0.0
                
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
                    
                    # Service Category (replaces Category tag for Workfront)
                    comp_category_value = comp_service_dept if comp_service_dept else "Unassigned"
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
                        task_num_in_component += 1
                        task = ET.SubElement(tasks, "{%s}Task" % ns)
                        uid = task_uid
                        task_uid += 1
                        
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
                        
                        # Safely get hours (for Work calculation, NOT for Duration)
                        planned_hours = row.get("Planned_Hours")
                        if pd.isna(planned_hours) or planned_hours is None:
                            planned_hours = row.get("Hours", 8)
                        if pd.isna(planned_hours) or planned_hours is None:
                            planned_hours = 8
                        hours = float(planned_hours)
                        
                        # GPT-5 PRO FIX 1 & 2: DO NOT inflate duration from hours
                        # Duration should be calculated from business-time span between Start/Finish dates ONLY
                        # Use a standard 1-day duration as fallback when no End_Date is provided
                        # This allows Units to show over-allocation (e.g., 16 hours in 1 day = 200% units)
                        duration_days = 1  # Standard 1-day window, NOT based on hours
                        
                        # Accumulate task hours into component and deliverable totals
                        component_task_hours[comp_uid] += hours
                        deliverable_task_hours[deliv_uid] += hours
                        
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
                                    task_start = datetime.fromisoformat(start_val)
                                # CRITICAL: Always normalize time to 09:00 regardless of input
                                task_start = task_start.replace(hour=9, minute=0, second=0, microsecond=0)
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
                                    task_end = datetime.fromisoformat(end_val)
                                # CRITICAL: Always normalize time to 09:00 regardless of input
                                task_end = task_end.replace(hour=9, minute=0, second=0, microsecond=0)
                                logging.info(f"[GANTT MERGE] Using merged End_Date for '{task_name}': {task_end.isoformat()}")
                            except Exception as e:
                                logging.warning(f"Could not parse End_Date '{row.get('End_Date')}': {e}")
                        
                        # Fall back to calculated dates if Start_Date/End_Date missing
                        if task_start is None:
                            task_start = current_date
                            
                            # USER INSTRUCTION: Align Start to working blocks
                            # "If a Start equals the end of a work block (e.g., 18:00), advance to the next block's start"
                            # Ensure task starts at valid business time (09:00), not after hours
                            from datetime import time as dt_time
                            if task_start.time() >= dt_time(18, 0) or task_start.time() < dt_time(9, 0):
                                # Start is outside working hours, move to next business day at 09:00
                                next_day = task_start.date() + timedelta(days=1)
                                while not is_business_day(next_day):
                                    next_day += timedelta(days=1)
                                task_start = datetime.combine(next_day, dt_time(9, 0))
                                logging.info(f"[START ALIGNMENT] Moved task start from after-hours to next business day: {task_start.isoformat()}")
                            elif task_start.time() < dt_time(13, 0) and task_start.time() >= dt_time(12, 0):
                                # Start is during lunch break (12:00-13:00), move to 13:00
                                task_start = task_start.replace(hour=13, minute=0, second=0, microsecond=0)
                                logging.info(f"[START ALIGNMENT] Moved task start from lunch to 13:00: {task_start.isoformat()}")
                            
                        if task_end is None:
                            # Calculate end by adding working minutes (480 per business day)
                            # This keeps tasks within same day instead of rolling to next morning
                            duration_minutes_to_add = duration_days * 480  # 480 minutes = 8-hour business day
                            task_end = add_business_minutes(task_start, duration_minutes_to_add)
                        
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
                        
                        # GPT-5 PRO FIX 3: Set non-summary leaf tasks to Type="1" (Fixed Duration)
                        ET.SubElement(task, "{%s}Type" % ns).text = "1"  # Fixed Duration
                        ET.SubElement(task, "{%s}IsNull" % ns).text = "0"
                        ET.SubElement(task, "{%s}WBS" % ns).text = task_wbs
                        ET.SubElement(task, "{%s}OutlineNumber" % ns).text = task_wbs
                        ET.SubElement(task, "{%s}OutlineLevel" % ns).text = task_outline_level
                        ET.SubElement(task, "{%s}Priority" % ns).text = "500"
                        ET.SubElement(task, "{%s}Start" % ns).text = task_start.isoformat()
                        ET.SubElement(task, "{%s}Finish" % ns).text = task_end.isoformat()
                        
                        # FIX ISSUE 2: Calculate Duration in WORKING minutes (480 per day), not calendar minutes
                        # MSPDI requires MinutesPerDay=480 for 8-hour workdays (not 1440 calendar minutes)
                        # Calculate business days between start and end, then multiply by 480
                        business_days = 0
                        current_check_date = task_start.date()
                        end_check_date = task_end.date()
                        while current_check_date <= end_check_date:
                            # Count only weekdays (Monday=0 to Friday=4)
                            if current_check_date.weekday() < 5:
                                business_days += 1
                            current_check_date += timedelta(days=1)
                        
                        # FIX 3: Duration calculation - preserve sub-day tasks instead of rounding up
                        # Calculate duration in working minutes = business_days × 480 (MinutesPerDay)
                        duration_minutes = business_days * 480
                        
                        # Only round to full days (480 min) if duration is already >= 1 day
                        # This preserves sub-day tasks (2h, 4h) instead of inflating them to 8h
                        if duration_minutes >= 480:
                            duration_minutes = ((duration_minutes + 479) // 480) * 480
                        elif duration_minutes < 60:
                            # Ensure minimum of 1 hour (60 minutes) for very short tasks
                            duration_minutes = 60
                        # else: leave sub-day tasks (60-479 minutes) as-is
                        
                        ET.SubElement(task, "{%s}Duration" % ns).text = f"PT{duration_minutes}M"
                        logging.info(f"[DURATION FIX] Task '{task_name}': {business_days} business days = PT{duration_minutes}M (working minutes)")
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
                        # GPT-5 PRO FIX 3: Set IsEffortDriven="0" for Fixed Duration tasks
                        ET.SubElement(task, "{%s}EffortDriven" % ns).text = "0"
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
                            
                            # Service Category (replaces Category tag for Workfront)
                            task_category_value = task_service_dept if task_service_dept else "Unassigned"
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
                
                # Update component summary with PT0M duration (Workfront standard for summary tasks)
                # Summary tasks are organizational containers - actual work is tracked in leaf tasks
                # CRITICAL: For PT0M duration, Start must equal Finish to satisfy Workfront validation
                ET.SubElement(comp_task, "{%s}Duration" % ns).text = "PT0M"
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
            
            # Update deliverable summary with PT0M duration (Workfront standard for summary tasks)
            # Summary tasks are organizational containers - actual work is tracked in leaf tasks
            # CRITICAL: For PT0M duration, Start must equal Finish to satisfy Workfront validation
            ET.SubElement(deliv_task, "{%s}Duration" % ns).text = "PT0M"
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
            
            # FIX: Advance current_date to deliverable finish for proper deliverable sequencing
            # This ensures each deliverable starts after the previous one finishes
            current_date = deliverable_finish
            
            # Update project finish date to track the latest deliverable finish
            # Since deliverables are sequential, this will naturally track the last one
            project_finish_date = deliverable_finish
            
            # FIX: Increment deliverable counter for next deliverable
            deliverable_counter += 1
            
            # Log each deliverable finish update
            logging.info(f"[PROJECT] Updated project finish date after '{deliverable_name}': {project_finish_date.isoformat()}")
    
    # Update project summary task (UID=0) Finish date
    # Find the existing Finish element and update its value (don't create a new one)
    # This is required by Workfront for valid XML import
    finish_elem = project_task.find("{%s}Finish" % ns)
    if finish_elem is not None:
        finish_elem.text = project_finish_date.isoformat()
        logging.info(f"[PROJECT] ✅ Updated project Finish date to: {project_finish_date.isoformat()}")
    else:
        logging.error(f"[PROJECT] ❌ ERROR: Finish element not found in project task!")
        # Fallback: create it if missing (shouldn't happen)
        ET.SubElement(project_task, "{%s}Finish" % ns).text = project_finish_date.isoformat()
        logging.info(f"[PROJECT] Created missing Finish element with date: {project_finish_date.isoformat()}")
    
    # Add PredecessorLink elements for dependencies
    # FIX FOR ISSUE 1: Process dependencies for ALL task types (deliverables, components, AND leaf tasks)
    if add_dependencies:
        logging.info("[DEPENDENCIES] Processing Dependencies column for ALL task types (deliverables, components, leaf tasks)")
        
        # Check if Dependencies column exists
        if "Dependencies" in df.columns:
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
                # Get task identifiers from DataFrame row
                row_deliverable = row.get("Deliverable", "")
                row_component = row.get("Component", "")
                row_task = row.get("Task", "")
                row_task_name = row.get("Task_Name", "")
                
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
                elif has_component and has_deliverable and not has_task:
                    # Component level (Component is populated, Task is not)
                    lookup_key = (str(row_deliverable), str(row_component), None)
                elif has_deliverable and not has_component:
                    # Deliverable level (Component is not populated)
                    lookup_key = (str(row_deliverable), None, None)
                
                # Look up task element and UID
                if lookup_key and lookup_key in all_tasks_lookup:
                    task_elem, task_uid = all_tasks_lookup[lookup_key]
                else:
                    # No matching task found, skip this row
                    continue
                
                # Get Dependencies value from this row
                dependencies_value = row.get("Dependencies", "")
                
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
                        predecessor_uid = original_wbs_to_uid.get(dep_wbs)
                        
                        if predecessor_uid is None:
                            logging.warning(f"[DEPENDENCIES] Invalid WBS reference '{dep_wbs}' for task {lookup_key} - skipping")
                            skipped_count += 1
                            continue
                        
                        # Skip self-referencing dependencies
                        if predecessor_uid == task_uid:
                            logging.warning(f"[DEPENDENCIES] Self-referencing dependency for task {lookup_key} (UID={task_uid}) - skipping")
                            skipped_count += 1
                            continue
                        
                        # WORKFRONT FIX: Check if predecessor is a summary task
                        # Dependencies can only link to LEAF tasks, not summary tasks (deliverables/components)
                        predecessor_task_elem = None
                        for potential_pred_task in tasks.findall("{%s}Task" % ns):
                            pred_uid_elem = potential_pred_task.find("{%s}UID" % ns)
                            if pred_uid_elem is not None and int(pred_uid_elem.text) == predecessor_uid:
                                predecessor_task_elem = potential_pred_task
                                break
                        
                        if predecessor_task_elem is not None:
                            # Check if this is a summary task
                            summary_elem = predecessor_task_elem.find("{%s}Summary" % ns)
                            is_summary = summary_elem is not None and summary_elem.text == "1"
                            
                            if is_summary:
                                # Get predecessor name for better logging
                                pred_name_elem = predecessor_task_elem.find("{%s}Name" % ns)
                                pred_name = pred_name_elem.text if pred_name_elem is not None else "Unknown"
                                
                                logging.warning(f"[DEPENDENCIES] Skipping dependency to summary task: Task {lookup_key} (UID={task_uid}) -> Summary '{pred_name}' (UID={predecessor_uid}, WBS={dep_wbs})")
                                skipped_count += 1
                                continue
                        
                        # GPT-5 PRO FIX 1 & 2: Get task names and components for link_for() function
                        # Get successor task name and component
                        succ_task_name = row_task_name if row_task_name else str(row_deliverable)
                        succ_component = str(row_component) if has_component else None
                        
                        # Get predecessor task name and component by looking up in task_map or DataFrame
                        pred_task_name = "Unknown"
                        pred_component = None
                        
                        if predecessor_task_elem is not None:
                            pred_name_elem = predecessor_task_elem.find("{%s}Name" % ns)
                            if pred_name_elem is not None:
                                pred_task_name = pred_name_elem.text
                        
                        # Try to find predecessor component from task_map
                        if predecessor_uid in task_map:
                            pred_component = task_map[predecessor_uid].get("component")
                        
                        # Determine dependency type and lag using "seasoned PM" rules
                        link_type, lag_days = link_for(pred_task_name, succ_task_name, pred_component, succ_component)
                        # CRITICAL ERROR #2 FIX: Use lag_days directly, don't multiply by 480
                        # When LagFormat=7 (Days), LinkLag should be in DAYS, not minutes!
                        
                        # Create PredecessorLink element with proper type and lag
                        pred_link = ET.SubElement(task_elem, "{%s}PredecessorLink" % ns)
                        ET.SubElement(pred_link, "{%s}PredecessorUID" % ns).text = str(predecessor_uid)
                        ET.SubElement(pred_link, "{%s}Type" % ns).text = str(link_type)  # 1=FS, 2=SS, 3=FF, 4=SF
                        ET.SubElement(pred_link, "{%s}CrossProject" % ns).text = "0"
                        ET.SubElement(pred_link, "{%s}LinkLag" % ns).text = str(lag_days)  # Lag in DAYS (not minutes!)
                        ET.SubElement(pred_link, "{%s}LagFormat" % ns).text = "7"  # Days format
                        
                        dependencies_count += 1
                        
                        # Log dependency type for debugging
                        type_names = {0: "FF", 1: "FS", 2: "SF", 3: "SS"}
                        type_name = type_names.get(link_type, f"Type{link_type}")
                        logging.info(f"[DEPENDENCIES] Added {type_name}+{lag_days}d dependency: '{succ_task_name}' (UID={task_uid}) depends on '{pred_task_name}' (UID={predecessor_uid})")
            
            logging.info(f"[DEPENDENCIES] Added {dependencies_count} dependencies across ALL task types, skipped {skipped_count} invalid references")
        else:
            logging.warning("[DEPENDENCIES] Dependencies column not found in DataFrame - skipping dependency parsing")
        
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
                            # Parse dependency spec (e.g., 'SS+1d', 'FS+0', 'FF-1d')
                            # For now, use default SS+1d since we don't have spec from DataFrame yet
                            dep_spec = "SS+1d"  # TODO: Get from DataFrame Dependencies column
                            dep_type_code, lag_days = parse_dependency_spec(dep_spec)
                            
                            pred_link = ET.SubElement(task, "{%s}PredecessorLink" % ns)
                            ET.SubElement(pred_link, "{%s}PredecessorUID" % ns).text = str(other_uid)
                            ET.SubElement(pred_link, "{%s}Type" % ns).text = dep_type_code
                            ET.SubElement(pred_link, "{%s}CrossProject" % ns).text = "0"
                            ET.SubElement(pred_link, "{%s}LinkLag" % ns).text = str(lag_days)  # FIXED: Use lag_days directly
                            ET.SubElement(pred_link, "{%s}LagFormat" % ns).text = "7"  # Days format
                            break
    
    # Create Assignments container with enhanced resource assignments
    assignments = ET.SubElement(root, "{%s}Assignments" % ns)
    assignment_uid = 1
    
    # Create resource assignments
    for uid, task_data in task_map.items():
        task = task_data["task"]
        
        # GPT-5 PRO FIX 2: Get task hours with backfill from duration
        work_elem = task.find("{%s}Work" % ns)
        if work_elem is not None and work_elem.text:
            work_minutes = int(work_elem.text.replace("PT", "").replace("M", ""))
            work_hours = work_minutes / 60
        else:
            work_hours = 0.0
        
        # GPT-5 PRO FIX 2: Backfill zero hours from duration (assume 1 FTE across duration)
        if work_hours <= 0.0001:
            duration_elem = task.find("{%s}Duration" % ns)
            if duration_elem is not None and duration_elem.text:
                duration_minutes = int(duration_elem.text.replace("PT", "").replace("M", ""))
                work_hours = duration_minutes / 60  # Assume 1.0 FTE across the duration
                logging.info(f"[ASSIGNMENT BACKFILL] Task UID={uid}: Backfilled {work_hours:.2f} hours from duration")
        
        # If still zero, use default
        if work_hours <= 0.0001:
            work_hours = 8.0
        
        # Assign department resource
        department = task_data["department"]
        
        # GPT-5 PRO FIX 2: Ensure all tasks have at least one assignment (default to "Unassigned")
        if not department or department not in department_resources:
            department = "Unassigned"
            # Create "Unassigned" resource if it doesn't exist
            if department not in department_resources:
                resources = root.find("{%s}Resources" % ns)
                if resources is not None:
                    # FIX ISSUE 1: Use max_resource_uid + 1 to prevent duplicate UIDs
                    unassigned_uid = max_resource_uid + 1
                    unassigned_res = ET.SubElement(resources, "{%s}Resource" % ns)
                    ET.SubElement(unassigned_res, "{%s}UID" % ns).text = str(unassigned_uid)
                    ET.SubElement(unassigned_res, "{%s}ID" % ns).text = str(unassigned_uid)
                    ET.SubElement(unassigned_res, "{%s}Name" % ns).text = "Unassigned"
                    ET.SubElement(unassigned_res, "{%s}Type" % ns).text = "1"
                    ET.SubElement(unassigned_res, "{%s}MaxUnits" % ns).text = "1"  # 1.0 = 100% capacity (MSPDI ratio format)
                    ET.SubElement(unassigned_res, "{%s}StandardRate" % ns).text = f"{blended_rate or 195:.2f}"
                    ET.SubElement(unassigned_res, "{%s}CalendarUID" % ns).text = "1"
                    department_resources["Unassigned"] = unassigned_uid
                    max_resource_uid = unassigned_uid  # FIX ISSUE 1: Update max_resource_uid
                    logging.info(f"[ASSIGNMENT BACKFILL] Created 'Unassigned' resource (UID={unassigned_uid})")
        
        if department in department_resources:
            assign = ET.SubElement(assignments, "{%s}Assignment" % ns)
            ET.SubElement(assign, "{%s}UID" % ns).text = str(assignment_uid)
            ET.SubElement(assign, "{%s}TaskUID" % ns).text = str(uid)
            ET.SubElement(assign, "{%s}ResourceUID" % ns).text = str(department_resources[department])
            
            # EXPERT SPECIFICATION: Calculate Units as work/duration ratio with proper clamping
            # units = 0 if dur_min == 0 else min(1.0, round(work_min / dur_min, 4))
            # MSPDI expects 1.0 = 100%, values >1.0 indicate over-allocation
            duration_elem = task.find("{%s}Duration" % ns)
            if duration_elem is not None and duration_elem.text:
                dur_minutes = int(duration_elem.text.replace("PT", "").replace("M", ""))
                work_minutes = work_hours * 60
                units = 0 if dur_minutes == 0 else min(1.0, round(work_minutes / dur_minutes, 4))
            else:
                units = 1.0  # Default to 100%
            
            ET.SubElement(assign, "{%s}Units" % ns).text = f"{units:.4f}"
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
    
    # WORKFRONT FIX: Roll up assignment work hours back to tasks
    # Workfront requires task Work = sum of assignment Work, or it rejects the file
    logging.info("[WORKFRONT FIX] Rolling up assignment work hours to tasks...")
    
    # Step 1: Sum assignment work by TaskUID
    task_work_rollup = {}  # {task_uid: total_work_minutes}
    for assignment_elem in assignments.findall("{%s}Assignment" % ns):
        task_uid_elem = assignment_elem.find("{%s}TaskUID" % ns)
        work_elem = assignment_elem.find("{%s}Work" % ns)
        
        if task_uid_elem is not None and work_elem is not None:
            task_uid = int(task_uid_elem.text)
            work_text = work_elem.text or "PT0M"
            work_minutes = int(work_text.replace("PT", "").replace("M", ""))
            
            if task_uid not in task_work_rollup:
                task_work_rollup[task_uid] = 0
            task_work_rollup[task_uid] += work_minutes
    
    # Step 2: Update task Work/RegularWork/RemainingWork elements
    tasks_updated = 0
    for uid, task_data in task_map.items():
        task = task_data["task"]
        total_work_minutes = task_work_rollup.get(uid, 0)
        
        # Update Work element
        work_elem = task.find("{%s}Work" % ns)
        if work_elem is not None:
            old_work = work_elem.text
            work_elem.text = f"PT{total_work_minutes}M"
            if total_work_minutes > 0:
                tasks_updated += 1
                logging.info(f"[WORKFRONT FIX] Task UID={uid}: Updated Work from {old_work} to PT{total_work_minutes}M")
        
        # Update RegularWork element
        regular_work_elem = task.find("{%s}RegularWork" % ns)
        if regular_work_elem is not None:
            regular_work_elem.text = f"PT{total_work_minutes}M"
        
        # Update RemainingWork element
        remaining_work_elem = task.find("{%s}RemainingWork" % ns)
        if remaining_work_elem is not None:
            remaining_work_elem.text = f"PT{total_work_minutes}M"
    
    logging.info(f"[WORKFRONT FIX] Successfully updated {tasks_updated} tasks with rolled-up work hours")
    
    # Validation: Check for zero-work tasks
    zero_work_count = 0
    for uid, task_data in task_map.items():
        task = task_data["task"]
        work_elem = task.find("{%s}Work" % ns)
        if work_elem is not None and work_elem.text == "PT0M":
            # Check if it's a summary task (summary tasks can have zero direct work)
            summary_elem = task.find("{%s}Summary" % ns)
            is_summary = summary_elem is not None and summary_elem.text == "1"
            if not is_summary:
                zero_work_count += 1
                task_name = task.find("{%s}Name" % ns).text if task.find("{%s}Name" % ns) is not None else "Unknown"
                logging.warning(f"[WORKFRONT VALIDATION] Task UID={uid} '{task_name}' has zero work (not a summary task)")
    
    if zero_work_count > 0:
        logging.warning(f"[WORKFRONT VALIDATION] Found {zero_work_count} non-summary tasks with zero work - may cause import issues")
    else:
        logging.info("[WORKFRONT VALIDATION] ✅ All non-summary tasks have work hours assigned")
    
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
        "has_calendars": True
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


if __name__ == "__main__":
    # Test the enhanced converter
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
        print(f"Enhanced conversion complete: {stats}")
    else:
        print(f"Test file {test_xlsx} not found")