"""
Business Timeline Adapter - Timeline-Specific Business-Day Helpers

This module provides a clean interface between timeline generation logic and the
BusinessCalendar utility. All date math in timeline generation should use these
helpers to ensure consistent Monday-Friday scheduling with no weekends.

Design Pattern: Adapter Layer
- Keeps timeline code readable (simple function calls)
- Centralizes business-day conversions
- Delegates to BusinessCalendar for actual calculations
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from business_calendar import BusinessCalendar


class BusinessTimelineAdapter:
    """
    Timeline-specific business-day operations.
    
    All methods ensure dates use Monday-Friday scheduling, matching Workfront's
    business calendar exactly.
    """
    
    @staticmethod
    def coerce_start_date(project_start: datetime) -> datetime:
        """
        Ensure project start date falls on a business day.
        If weekend/holiday, roll forward to next Monday.
        
        Args:
            project_start: Requested project start date
            
        Returns:
            Project start date on a business day
        """
        return BusinessCalendar.next_business_day(project_start)
    
    @staticmethod
    def add_duration(start: datetime, duration_days: int) -> datetime:
        """
        Add duration in business days to a start date.
        
        Args:
            start: Start date (datetime object)
            duration_days: Number of business days to add
            
        Returns:
            End date (last day of work, inclusive)
        """
        # Ensure start is on a business day
        start_business = BusinessCalendar.next_business_day(start)
        
        if duration_days <= 0:
            return start_business
        
        # Get end date (inclusive)
        return BusinessCalendar.get_business_day_end(start_business, duration_days)
    
    @staticmethod
    def next_start_after_dependency(predecessor_end: datetime, lag_days: int = 0) -> datetime:
        """
        Calculate successor task start date based on predecessor end date.
        For Finish-to-Start (FS) dependencies.
        
        Args:
            predecessor_end: End date of predecessor task
            lag_days: Optional lag in business days (0 = start next business day)
            
        Returns:
            Start date for successor task
        """
        # Successor starts on next business day after predecessor ends
        next_day = predecessor_end + timedelta(days=1)
        start_business = BusinessCalendar.next_business_day(next_day)
        
        # Add lag if specified
        if lag_days > 0:
            start_business = BusinessCalendar.add_business_days(start_business, lag_days)
        
        return start_business
    
    @staticmethod
    def calc_duration(start: datetime, end: datetime) -> int:
        """
        Calculate duration in business days between start and end dates (inclusive).
        
        Args:
            start: Start date
            end: End date
            
        Returns:
            Number of business days (inclusive of both start and end)
        """
        if end < start:
            return 0
        
        # Add 1 because end date is inclusive
        # Example: Monday to Monday = 1 day (same day)
        # Example: Monday to Tuesday = 2 days
        return BusinessCalendar.business_days_between(start, end) + 1
    
    @staticmethod
    def align_month_window(year: int, month: int) -> Tuple[datetime, datetime]:
        """
        Get first and last business day of a calendar month for retainer deliverables.
        
        Args:
            year: Year
            month: Month (1-12)
            
        Returns:
            Tuple of (first_business_day, last_business_day) of the month
        """
        from calendar import monthrange
        
        # First day of month
        first_cal = datetime(year, month, 1)
        first_business = BusinessCalendar.next_business_day(first_cal)
        
        # Last day of month
        last_day_num = monthrange(year, month)[1]
        last_cal = datetime(year, month, last_day_num)
        
        # Walk backwards to find last business day
        while not BusinessCalendar.is_business_day(last_cal):
            last_cal = last_cal - timedelta(days=1)
        
        return (first_business, last_cal)
    
    @staticmethod
    def add_buffer_days(task_end: datetime, buffer_days: int) -> datetime:
        """
        Add buffer days (for project/feeding buffers) in business days.
        
        Args:
            task_end: End date of task
            buffer_days: Number of business days for buffer
            
        Returns:
            End date of buffer (last day of buffer)
        """
        # Buffer starts day after task ends
        buffer_start = BusinessTimelineAdapter.next_start_after_dependency(task_end)
        
        if buffer_days <= 0:
            return buffer_start
        
        # Buffer end is start + duration
        return BusinessCalendar.get_business_day_end(buffer_start, buffer_days)
    
    @staticmethod
    def milestone_at_percentage(project_start: datetime, project_end: datetime, percentage: float) -> datetime:
        """
        Calculate milestone date at a given percentage of project duration.
        
        Args:
            project_start: Project start date
            project_end: Project end date
            percentage: Percentage (0.0 to 1.0)
            
        Returns:
            Milestone date on a business day
        """
        # Calculate total business days in project (inclusive count)
        total_days = BusinessTimelineAdapter.calc_duration(project_start, project_end)
        
        # Calculate offset for milestone (subtract 1 since calc_duration is inclusive)
        offset_days = int((total_days - 1) * percentage)
        
        # Calculate milestone date
        milestone = BusinessCalendar.add_business_days(project_start, offset_days)
        
        return milestone
    
    @staticmethod
    def format_iso(dt: datetime) -> str:
        """
        Format datetime as ISO date string (YYYY-MM-DD) for TimelineTask.
        
        Args:
            dt: Datetime object
            
        Returns:
            ISO format date string
        """
        return dt.strftime('%Y-%m-%d')
    
    @staticmethod
    def parse_iso(date_str: str) -> datetime:
        """
        Parse ISO date string (YYYY-MM-DD) to datetime.
        
        Args:
            date_str: ISO format date string
            
        Returns:
            Datetime object
        """
        return datetime.fromisoformat(date_str)


# Convenience functions for common timeline operations
def ensure_business_day(dt: datetime) -> datetime:
    """Ensure date is on a business day (roll forward if weekend/holiday)."""
    return BusinessCalendar.next_business_day(dt)


def add_business_days_timeline(start: datetime, days: int) -> datetime:
    """Add business days to start date (timeline-specific)."""
    return BusinessTimelineAdapter.add_duration(start, days)


def business_duration(start: datetime, end: datetime) -> int:
    """Calculate business day duration (inclusive of start and end)."""
    return BusinessTimelineAdapter.calc_duration(start, end)


def next_task_start(prev_end: datetime) -> datetime:
    """Get next task start date (day after previous task ends)."""
    return BusinessTimelineAdapter.next_start_after_dependency(prev_end)
