"""
Business Calendar Utility - Monday-Friday Scheduling Only

This module provides business-day calculation helpers that ensure all timeline
dates use Monday-Friday scheduling with no weekends. Designed to match Workfront's
business calendar exactly for accurate timeline export/import.

Key Features:
- Hard-coded Monday-Friday schedule (no toggles, no weekend scheduling)
- US/MX holiday calendar support
- Auto-roll weekend dates to next Monday
- Business-day duration calculations
- Working hours: 9:00-12:00, 13:00-18:00 (8 hours/day)
"""

import datetime
from datetime import date, time, timedelta
from typing import Union
import numpy as np

# TCG 2025-2026 Holiday Calendar
# These dates are excluded from business day calculations
US_MX_HOLIDAYS = [
    # 2025 TCG Holidays
    date(2025, 1, 1),   # New Year's Day
    date(2025, 1, 20),  # Martin Luther King, Jr. Day
    date(2025, 2, 17),  # Presidents Day
    date(2025, 5, 26),  # Memorial Day
    date(2025, 6, 19),  # Juneteenth National Independence Day
    date(2025, 7, 4),   # Independence Day
    date(2025, 8, 28),  # Mental Health Break - Thu
    date(2025, 8, 29),  # Mental Health Break - Fri
    date(2025, 9, 1),   # Labor Day (also end of Mental Health Break)
    date(2025, 10, 13), # Indigenous People Day
    date(2025, 11, 27), # Thanksgiving Day
    date(2025, 11, 28), # Day After Thanksgiving
    date(2025, 12, 22), # Holiday Break starts
    date(2025, 12, 23), # Holiday Break
    date(2025, 12, 24), # Holiday Break
    date(2025, 12, 25), # Christmas Day
    date(2025, 12, 26), # Holiday Break
    date(2025, 12, 27), # Holiday Break (ADDED - was missing)
    date(2025, 12, 28), # Holiday Break (ADDED - was missing)
    date(2025, 12, 29), # Holiday Break
    date(2025, 12, 30), # Holiday Break
    date(2025, 12, 31), # Holiday Break
    date(2026, 1, 1),   # New Year's Day (Holiday Break)
    date(2026, 1, 2),   # Manager Regroup / Return prep day
    # 2026 TCG Holidays (repeating pattern)
    date(2026, 1, 19),  # Martin Luther King, Jr. Day (estimated)
    date(2026, 2, 16),  # Presidents Day (estimated)
    date(2026, 5, 25),  # Memorial Day (estimated)
    date(2026, 6, 19),  # Juneteenth National Independence Day
    date(2026, 7, 3),   # Independence Day observed (estimated)
    date(2026, 9, 7),   # Labor Day (estimated)
    date(2026, 10, 12), # Indigenous People Day (estimated)
    date(2026, 11, 26), # Thanksgiving (estimated)
    date(2026, 11, 27), # Day After Thanksgiving (estimated)
    date(2026, 12, 25), # Christmas
]

# Business hours blocks: 9-12 (3h) and 13-18 (5h) = 8 hours/day
# MUST match XML calendar exactly: 09:00-12:00, 13:00-18:00 (Workfront standard)
BUSINESS_HOURS_PER_DAY = 8
WORK_BLOCKS = [
    (time(9, 0), time(12, 0)),   # Morning: 3 hours
    (time(13, 0), time(18, 0)),  # Afternoon: 5 hours
]


class BusinessCalendar:
    """
    Business calendar with hard-coded Monday-Friday scheduling.
    
    All methods ensure dates fall on business days (Mon-Fri) and skip
    weekends and holidays automatically.
    """
    
    @staticmethod
    def is_business_day(d: Union[date, datetime.datetime]) -> bool:
        """
        Check if a date is a business day (Mon-Fri, not a holiday).
        
        Args:
            d: Date to check (date or datetime object)
            
        Returns:
            True if business day, False if weekend or holiday
        """
        if isinstance(d, datetime.datetime):
            d = d.date()
        
        # Check if weekend (Saturday=5, Sunday=6 in weekday())
        if d.weekday() >= 5:
            return False
        
        # Check if holiday
        if d in US_MX_HOLIDAYS:
            return False
        
        return True
    
    @staticmethod
    def next_business_day(d: Union[date, datetime.datetime]) -> Union[date, datetime.datetime]:
        """
        Roll date forward to the next business day if it falls on weekend/holiday.
        
        Args:
            d: Date to check (date or datetime object)
            
        Returns:
            Same type as input, rolled to next business day if needed
        """
        is_datetime = isinstance(d, datetime.datetime)
        current = d.date() if is_datetime else d
        
        # Roll forward until we find a business day
        while not BusinessCalendar.is_business_day(current):
            current = current + timedelta(days=1)
        
        # Preserve time component if datetime
        if is_datetime:
            return datetime.datetime.combine(current, d.time())
        return current
    
    @staticmethod
    def add_business_days(start_date: Union[date, datetime.datetime], num_days: int) -> Union[date, datetime.datetime]:
        """
        Add num_days business days to start_date, skipping weekends and holidays.
        
        Args:
            start_date: Starting date (date or datetime object)
            num_days: Number of business days to add (can be 0)
            
        Returns:
            Same type as input, advanced by num_days business days
        """
        if num_days == 0:
            # If 0 days, just ensure we're on a business day
            return BusinessCalendar.next_business_day(start_date)
        
        is_datetime = isinstance(start_date, datetime.datetime)
        current = start_date.date() if is_datetime else start_date
        
        # Ensure we start on a business day
        current = BusinessCalendar.next_business_day(current)
        if isinstance(current, datetime.datetime):
            current = current.date()
        
        # Add business days using numpy.busday_offset for efficiency
        # Convert our holidays to numpy datetime64 format
        np_holidays = np.array(US_MX_HOLIDAYS, dtype='datetime64[D]')
        
        # Use numpy to add business days
        result = np.busday_offset(
            np.datetime64(current),
            num_days,
            roll='forward',
            holidays=np_holidays,
            weekmask='Mon Tue Wed Thu Fri'
        )
        
        # Convert back to Python date
        result_date = result.astype('datetime64[D]').astype(date)
        
        # Preserve time component if datetime
        if is_datetime:
            return datetime.datetime.combine(result_date, start_date.time())
        return result_date
    
    @staticmethod
    def business_days_between(start: Union[date, datetime.datetime], end: Union[date, datetime.datetime]) -> int:
        """
        Calculate number of business days between two dates (inclusive of start, exclusive of end).
        
        Args:
            start: Start date
            end: End date
            
        Returns:
            Number of business days
        """
        start_date = start.date() if isinstance(start, datetime.datetime) else start
        end_date = end.date() if isinstance(end, datetime.datetime) else end
        
        if end_date <= start_date:
            return 0
        
        # Use numpy for efficient business day counting
        np_holidays = np.array(US_MX_HOLIDAYS, dtype='datetime64[D]')
        
        count = np.busday_count(
            np.datetime64(start_date),
            np.datetime64(end_date),
            holidays=np_holidays,
            weekmask='Mon Tue Wed Thu Fri'
        )
        
        return int(count)
    
    @staticmethod
    def add_business_hours(start_datetime: datetime.datetime, hours: float) -> datetime.datetime:
        """
        Add business hours to a datetime, respecting 9-12, 13-18 work blocks.
        
        Args:
            start_datetime: Starting datetime
            hours: Number of business hours to add
            
        Returns:
            Datetime advanced by specified business hours
        """
        if hours <= 0:
            return start_datetime
        
        current = BusinessCalendar.next_business_day(start_datetime)
        remaining_hours = hours
        
        # Start at beginning of workday if before 9am
        if current.time() < time(9, 0):
            current = datetime.datetime.combine(current.date(), time(9, 0))
        # Start at 1pm if during lunch (12:00-13:00)
        elif time(12, 0) <= current.time() < time(13, 0):
            current = datetime.datetime.combine(current.date(), time(13, 0))
        # Roll to next day if after work hours
        elif current.time() >= time(18, 0):
            current = BusinessCalendar.add_business_days(current, 1)
            current = datetime.datetime.combine(current.date(), time(9, 0))
        
        # Add hours block by block
        while remaining_hours > 0:
            # Determine current block
            if time(9, 0) <= current.time() < time(12, 0):
                block_end = time(12, 0)
            elif time(13, 0) <= current.time() < time(18, 0):
                block_end = time(18, 0)
            else:
                # Between blocks or after hours, jump to next block
                if current.time() < time(13, 0):
                    current = datetime.datetime.combine(current.date(), time(13, 0))
                else:
                    current = BusinessCalendar.add_business_days(current, 1)
                    current = datetime.datetime.combine(current.date(), time(9, 0))
                continue
            
            # Calculate hours available in current block
            block_end_dt = datetime.datetime.combine(current.date(), block_end)
            hours_in_block = (block_end_dt - current).total_seconds() / 3600
            
            if remaining_hours <= hours_in_block:
                # Fits within current block
                current = current + timedelta(hours=remaining_hours)
                remaining_hours = 0
            else:
                # Use up current block, move to next
                remaining_hours -= hours_in_block
                current = block_end_dt
                
                # Move to next block or next day
                if current.time() == time(12, 0):
                    current = datetime.datetime.combine(current.date(), time(13, 0))
                else:
                    current = BusinessCalendar.add_business_days(current, 1)
                    current = datetime.datetime.combine(current.date(), time(9, 0))
        
        return current
    
    @staticmethod
    def get_business_day_end(start_date: Union[date, datetime.datetime], duration_days: int) -> Union[date, datetime.datetime]:
        """
        Calculate end date from start date + duration in business days.
        End date is inclusive (last day of work).
        
        Args:
            start_date: Project start date
            duration_days: Number of business days
            
        Returns:
            End date (inclusive)
        """
        if duration_days <= 0:
            return BusinessCalendar.next_business_day(start_date)
        
        # Duration is inclusive, so subtract 1 from the add operation
        # Example: 1-day task starts Monday, ends Monday (same day)
        # Example: 2-day task starts Monday, ends Tuesday (Monday + 1 business day)
        return BusinessCalendar.add_business_days(start_date, duration_days - 1)


# Convenience functions for backward compatibility
def is_business_day(d: Union[date, datetime.datetime]) -> bool:
    """Check if date is a business day (Mon-Fri, not holiday)."""
    return BusinessCalendar.is_business_day(d)


def next_business_day(d: Union[date, datetime.datetime]) -> Union[date, datetime.datetime]:
    """Roll date to next business day if on weekend/holiday."""
    return BusinessCalendar.next_business_day(d)


def add_business_days(start_date: Union[date, datetime.datetime], num_days: int) -> Union[date, datetime.datetime]:
    """Add business days, skipping weekends and holidays."""
    return BusinessCalendar.add_business_days(start_date, num_days)


def business_days_between(start: Union[date, datetime.datetime], end: Union[date, datetime.datetime]) -> int:
    """Count business days between two dates."""
    return BusinessCalendar.business_days_between(start, end)
