"""
Unified Scheduling Calendar Module

Single source of truth for:
- start/finish datetime calculations
- working_minutes_between(start, finish) using Mon-Fri, 9-5, 480 min/day
- Duration derivation from calendar math

This module ensures the app timeline and XML export use the SAME scheduling logic.
"""

import datetime
from datetime import date, time, timedelta
from typing import Tuple, Optional, List
import math


# Standard business hours: Mon-Fri, 9:00 AM - 5:00 PM (8 hours = 480 minutes/day)
BUSINESS_DAY_START = time(9, 0)
BUSINESS_DAY_END = time(17, 0)
MINUTES_PER_DAY = 480  # 8 hours
HOURS_PER_DAY = 8.0

# Business hour blocks (9-12 AM, 1-5 PM allows for lunch break if needed)
# Using single block for simplicity: 9:00 - 17:00
BUSINESS_BLOCKS = [(time(9, 0), time(17, 0))]


def is_business_day(d: date) -> bool:
    """Check if a date is a business day (Mon-Fri)."""
    return d.weekday() < 5  # 0=Monday, 4=Friday


def get_next_business_day(d: date, direction: int = 1) -> date:
    """Get the next (or previous) business day from a given date."""
    d = d + timedelta(days=direction)
    while not is_business_day(d):
        d = d + timedelta(days=direction)
    return d


def business_minutes_in_day(day: date, start_t: Optional[time] = None, end_t: Optional[time] = None) -> int:
    """
    Calculate working minutes on a single day between start_t and end_t.
    
    Args:
        day: The date to calculate for
        start_t: Start time (defaults to BUSINESS_DAY_START)
        end_t: End time (defaults to BUSINESS_DAY_END)
    
    Returns:
        Number of working minutes
    """
    if not is_business_day(day):
        return 0
    
    start_t = start_t or BUSINESS_DAY_START
    end_t = end_t or BUSINESS_DAY_END
    
    # Clamp to business hours
    start_t = max(start_t, BUSINESS_DAY_START)
    end_t = min(end_t, BUSINESS_DAY_END)
    
    if end_t <= start_t:
        return 0
    
    total = 0
    for block_start, block_end in BUSINESS_BLOCKS:
        s = max(start_t, block_start)
        e = min(end_t, block_end)
        if e > s:
            start_dt = datetime.datetime.combine(day, s)
            end_dt = datetime.datetime.combine(day, e)
            total += int((end_dt - start_dt).total_seconds() // 60)
    
    return total


def working_minutes_between(start_dt: datetime.datetime, end_dt: datetime.datetime) -> int:
    """
    Calculate working minutes between two datetimes using Mon-Fri, 9-5 calendar.
    
    This is THE source of truth for duration calculation.
    
    Args:
        start_dt: Start datetime
        end_dt: End datetime
    
    Returns:
        Total working minutes between start and end
    """
    if end_dt <= start_dt:
        return 0
    
    start_date = start_dt.date()
    end_date = end_dt.date()
    total_minutes = 0
    
    if start_date == end_date:
        # Same day - calculate partial day
        return business_minutes_in_day(start_date, start_dt.time(), end_dt.time())
    
    # First day (partial - from start_time to end of business day)
    total_minutes += business_minutes_in_day(start_date, start_dt.time(), BUSINESS_DAY_END)
    
    # Middle full days
    current = start_date + timedelta(days=1)
    while current < end_date:
        if is_business_day(current):
            total_minutes += MINUTES_PER_DAY
        current += timedelta(days=1)
    
    # Last day (partial - from start of business day to end_time)
    total_minutes += business_minutes_in_day(end_date, BUSINESS_DAY_START, end_dt.time())
    
    return total_minutes


def working_days_between(start_dt: datetime.datetime, end_dt: datetime.datetime) -> float:
    """
    Calculate working days between two datetimes.
    
    Returns:
        Number of working days (may be fractional)
    """
    minutes = working_minutes_between(start_dt, end_dt)
    return minutes / MINUTES_PER_DAY


def add_working_minutes(start_dt: datetime.datetime, minutes: int) -> datetime.datetime:
    """
    Add working minutes to a datetime, respecting business hours.
    
    Args:
        start_dt: Starting datetime
        minutes: Number of working minutes to add
    
    Returns:
        End datetime after adding working minutes
    """
    if minutes <= 0:
        return start_dt
    
    current_dt = start_dt
    remaining = minutes
    
    # If starting outside business hours, move to next business day start
    if not is_business_day(current_dt.date()) or current_dt.time() >= BUSINESS_DAY_END:
        current_dt = datetime.datetime.combine(
            get_next_business_day(current_dt.date()), 
            BUSINESS_DAY_START
        )
    elif current_dt.time() < BUSINESS_DAY_START:
        current_dt = datetime.datetime.combine(current_dt.date(), BUSINESS_DAY_START)
    
    while remaining > 0:
        if not is_business_day(current_dt.date()):
            current_dt = datetime.datetime.combine(
                get_next_business_day(current_dt.date()),
                BUSINESS_DAY_START
            )
            continue
        
        # Calculate remaining minutes in current day
        remaining_in_day = business_minutes_in_day(
            current_dt.date(), 
            current_dt.time(), 
            BUSINESS_DAY_END
        )
        
        if remaining <= remaining_in_day:
            # Finish within this day
            current_dt = current_dt + timedelta(minutes=remaining)
            remaining = 0
        else:
            # Use up this day and move to next
            remaining -= remaining_in_day
            current_dt = datetime.datetime.combine(
                get_next_business_day(current_dt.date()),
                BUSINESS_DAY_START
            )
    
    return current_dt


def add_working_days(start_dt: datetime.datetime, days: float) -> datetime.datetime:
    """
    Add working days to a datetime.
    
    Args:
        start_dt: Starting datetime
        days: Number of working days to add (can be fractional)
    
    Returns:
        End datetime after adding working days
    """
    minutes = int(days * MINUTES_PER_DAY)
    return add_working_minutes(start_dt, minutes)


def hours_to_working_days(hours: float) -> float:
    """
    Convert hours to working days.
    
    Args:
        hours: Number of hours
    
    Returns:
        Number of working days
    """
    return hours / HOURS_PER_DAY


def calculate_task_schedule(
    project_start: datetime.datetime,
    duration_minutes: int,
    predecessor_finish: Optional[datetime.datetime] = None,
    lag_minutes: int = 0
) -> Tuple[datetime.datetime, datetime.datetime]:
    """
    Calculate start and finish times for a task.
    
    Args:
        project_start: Project start datetime
        duration_minutes: Task duration in working minutes
        predecessor_finish: Finish time of predecessor task (if any)
        lag_minutes: Lag after predecessor (for FS dependencies)
    
    Returns:
        Tuple of (start_datetime, finish_datetime)
    """
    if predecessor_finish:
        # FS dependency: start after predecessor finishes + lag
        start = add_working_minutes(predecessor_finish, lag_minutes)
    else:
        start = project_start
    
    # Ensure start is at beginning of a business day if it's at day end
    if start.time() >= BUSINESS_DAY_END or not is_business_day(start.date()):
        start = datetime.datetime.combine(
            get_next_business_day(start.date()),
            BUSINESS_DAY_START
        )
    
    finish = add_working_minutes(start, duration_minutes)
    
    return start, finish


def format_mspdi_duration(minutes: int) -> str:
    """
    Format duration as MSPDI duration string (PT{M}M format).
    
    Args:
        minutes: Duration in minutes
    
    Returns:
        MSPDI duration string like "PT480M" for 8 hours
    """
    return f"PT{minutes}M"


def format_mspdi_work(hours: float) -> str:
    """
    Format work hours as MSPDI work string (PT{H}H0M0S format).
    
    Args:
        hours: Work hours
    
    Returns:
        MSPDI work string like "PT8H0M0S"
    """
    h = int(hours)
    m = int((hours - h) * 60)
    return f"PT{h}H{m}M0S"


def schedule_sequential_tasks(
    project_start: datetime.datetime,
    tasks: List[dict]
) -> List[dict]:
    """
    Schedule a list of tasks sequentially (FS dependencies with 0 lag).
    
    Each task dict should have:
        - 'id': Task identifier
        - 'duration_minutes' OR 'hours': Task duration
    
    Returns tasks with added:
        - 'start': Start datetime
        - 'finish': Finish datetime
        - 'duration_minutes': Duration in working minutes
    
    Args:
        project_start: Project start datetime
        tasks: List of task dictionaries
    
    Returns:
        List of scheduled task dictionaries
    """
    scheduled = []
    predecessor_finish = None
    
    for task in tasks:
        # Get duration
        if 'duration_minutes' in task:
            duration = task['duration_minutes']
        elif 'hours' in task:
            duration = int(task['hours'] * 60)
        else:
            duration = MINUTES_PER_DAY  # Default to 1 day
        
        start, finish = calculate_task_schedule(
            project_start,
            duration,
            predecessor_finish,
            lag_minutes=0  # FS with 0 lag
        )
        
        scheduled_task = task.copy()
        scheduled_task['start'] = start
        scheduled_task['finish'] = finish
        scheduled_task['duration_minutes'] = duration
        scheduled.append(scheduled_task)
        
        predecessor_finish = finish
    
    return scheduled


def get_mspdi_dates(
    start_dt: datetime.datetime, 
    finish_dt: datetime.datetime
) -> dict:
    """
    Get all date/duration values needed for MSPDI export from start/finish.
    
    This is the primary interface for XML export - it derives everything
    from the start and finish datetimes using consistent calendar math.
    
    Args:
        start_dt: Task start datetime
        finish_dt: Task finish datetime
    
    Returns:
        Dictionary with:
            - start_iso: Start datetime as ISO string
            - finish_iso: Finish datetime as ISO string
            - duration_minutes: Working minutes (for <Duration>)
            - duration_pt: Duration as PT string (e.g., "PT480M")
    """
    duration_minutes = working_minutes_between(start_dt, finish_dt)
    
    return {
        'start_iso': start_dt.isoformat(),
        'finish_iso': finish_dt.isoformat(),
        'duration_minutes': duration_minutes,
        'duration_pt': format_mspdi_duration(duration_minutes),
    }
