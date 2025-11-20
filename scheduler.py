"""
WBS Scheduler Module - Business Calendar and Timeline Calculation
Extracted from main.py for testability and modularity
"""
import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Tuple, Set

# Business Calendar Configuration
BUS_BLOCKS = [
    (datetime.time(8, 0), datetime.time(12, 0)),   # Morning: 8 AM - 12 PM (4 hours)
    (datetime.time(13, 0), datetime.time(17, 0)),  # Afternoon: 1 PM - 5 PM (4 hours)
]  # Total: 8 hours/day = 480 minutes/day

# US/MX Holiday Calendar (simplified - can be expanded)
HOLIDAYS = set([
    # 2026 holidays
    datetime.date(2026, 1, 1),   # New Year's Day
    datetime.date(2026, 7, 4),   # Independence Day
    datetime.date(2026, 12, 25),  # Christmas
    # Add more holidays as needed
])


def is_business_day(d: datetime.date) -> bool:
    """
    Check if a date is a business day (Monday-Friday, not a holiday).
    
    Args:
        d: Date to check
    
    Returns:
        True if business day, False otherwise
    """
    return d.weekday() < 5 and d not in HOLIDAYS


def business_minutes_in_range(d: datetime.date, start_time: datetime.time, end_time: datetime.time) -> int:
    """
    Count business minutes between start_time and end_time on a given date.
    Accounts for lunch break (12:00-13:00).
    
    Args:
        d: Date to calculate for
        start_time: Start time (inclusive)
        end_time: End time (exclusive)
    
    Returns:
        Number of business minutes in the range
    """
    if not is_business_day(d):
        return 0
    
    total_minutes = 0
    for block_start, block_end in BUS_BLOCKS:
        # Calculate overlap between [start_time, end_time) and [block_start, block_end)
        effective_start = max(start_time, block_start)
        effective_end = min(end_time, block_end)
        
        if effective_start < effective_end:
            minutes = int((datetime.datetime.combine(d, effective_end) - 
                          datetime.datetime.combine(d, effective_start)).total_seconds() // 60)
            total_minutes += minutes
    
    return total_minutes


def add_business_days(start_dt: datetime.datetime, days: float) -> datetime.datetime:
    """
    Add business days to a start datetime using business calendar with lunch break.
    BUS_BLOCKS: [(8:00-12:00), (13:00-17:00)] = 480 minutes/day.
    
    Algorithm: Consume requested minutes within current day's blocks while
    respecting the caller's actual start timestamp. Handles midday starts from
    predecessor finish times.
    
    Args:
        start_dt: Starting datetime (honors intraday time)
        days: Number of business days to add (can be fractional)
    
    Returns:
        Resulting datetime after adding business days
    
    Examples:
        - 0.5 days from Mon 8AM → Mon 12PM (240 minutes)
        - 0.5 days from Mon 10AM → Mon 3PM (2h before lunch + 2h after)
        - 1.0 day from Mon 8AM → Mon 5PM (480 minutes, ends at block boundary)
        - 2.0 days from Mon 8AM → Tue 5PM (960 minutes)
        - 0 days from Mon 10AM → Mon 10AM (unchanged)
    """
    # Zero-duration: return unchanged
    if days == 0:
        return start_dt
    
    # Convert days to minutes using Decimal for round-half-up precision
    minutes_to_add = int(Decimal(str(days * 480)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    
    # Start from the provided datetime (honor intraday time)
    current_dt = start_dt
    minutes_remaining = minutes_to_add
    
    while minutes_remaining > 0:
        # Skip to next business day if weekend/holiday
        if not is_business_day(current_dt.date()):
            current_dt = datetime.datetime.combine(
                current_dt.date() + datetime.timedelta(days=1),
                datetime.time(8, 0)
            )
            continue
        
        # Find which block we're in and consume minutes
        current_time = current_dt.time()
        consumed_this_iteration = False
        
        for block_start, block_end in BUS_BLOCKS:
            # Skip blocks before current time
            if current_time >= block_end:
                continue
            
            # Calculate minutes available in this block
            effective_start = max(current_time, block_start)
            minutes_in_block = int((datetime.datetime.combine(current_dt.date(), block_end) - 
                                   datetime.datetime.combine(current_dt.date(), effective_start)).total_seconds() // 60)
            
            if minutes_in_block <= 0:
                continue
            
            # Consume as many minutes as possible from this block
            minutes_to_consume = min(minutes_remaining, minutes_in_block)
            current_dt = datetime.datetime.combine(current_dt.date(), effective_start) + datetime.timedelta(minutes=minutes_to_consume)
            minutes_remaining -= minutes_to_consume
            consumed_this_iteration = True
            
            if minutes_remaining == 0:
                return current_dt
            
            # If more minutes remain, continue to next block
            if minutes_to_consume < minutes_in_block:
                # We're still within this block
                return current_dt
        
        # If no minutes consumed (end of day), advance to next business day
        if not consumed_this_iteration:
            current_dt = datetime.datetime.combine(
                current_dt.date() + datetime.timedelta(days=1),
                datetime.time(8, 0)
            )
    
    return current_dt


def business_day_diff(start_date: datetime.date, end_date: datetime.date) -> float:
    """
    Calculate business days between two dates using business minutes.
    Returns fractional days (480 minutes = 1.0 day).
    
    Args:
        start_date: Starting date
        end_date: Ending date
    
    Returns:
        Fractional business days between dates
    
    Examples:
        - Mon 8AM to Mon 12PM: 240 minutes → 0.5 days
        - Mon 8AM to Mon 5PM: 480 minutes → 1.0 day
        - Mon 8AM to Tue 5PM: 960 minutes → 2.0 days
    """
    if end_date < start_date:
        return 0.0
    
    # Convert dates to datetimes (8 AM to 5 PM spans)
    start_dt = datetime.datetime.combine(start_date, datetime.time(8, 0))
    end_dt = datetime.datetime.combine(end_date, datetime.time(17, 0))
    
    if end_dt <= start_dt:
        return 0.0
    
    # Calculate business minutes between dates without double-counting
    total_minutes = 0
    current = start_date
    
    while current <= end_date:
        if is_business_day(current):
            # Count full business day (480 minutes)
            total_minutes += 480
        
        current += datetime.timedelta(days=1)
    
    # Convert minutes to days using Decimal for precision
    days = float(Decimal(str(total_minutes)) / Decimal('480'))
    
    return days


def compute_wbs_schedule(rows: List[Dict], normalized_edges: List[Tuple[str, str]], project_start_date) -> Dict[int, Dict]:
    """
    WBS-based scheduler using Workfront semantics (8h/day, FS dependencies, business days).
    
    Algorithm:
    1. Convert Hours → DurationDays (8h = 1 day, Workfront standard)
    2. Topological sort tasks by WBS dependencies (FS-only, Kahn's algorithm)
    3. Calculate earliest start/finish times in business days from project start
    4. Convert day offsets to actual dates using business calendar
    
    Args:
        rows: List of task dictionaries containing:
            - 'UID': Unique task identifier
            - 'WBS': Work breakdown structure code
            - 'Hours': Planned hours (or 'PlannedHours')
        normalized_edges: List of (pred_wbs, succ_wbs) dependency tuples
        project_start_date: datetime.date or datetime.datetime
    
    Returns:
        uid_to_sched: Dict mapping UID to schedule info:
            {"start": datetime, "finish": datetime, "duration_days": float}
    """
    # Convert project_start to datetime if date (default to 8 AM)
    if isinstance(project_start_date, datetime.date) and not isinstance(project_start_date, datetime.datetime):
        project_start_date = datetime.datetime.combine(project_start_date, datetime.time(8, 0))
    
    # Build UID graph from WBS edges
    wbs_to_uid = {r["WBS"]: r["UID"] for r in rows}
    preds = {r["UID"]: [] for r in rows}
    
    for pred_wbs, succ_wbs in normalized_edges:
        pred_uid = wbs_to_uid.get(pred_wbs)
        succ_uid = wbs_to_uid.get(succ_wbs)
        if pred_uid and succ_uid:
            preds[succ_uid].append(pred_uid)
    
    # Convert Hours → DurationDays per task (Workfront: 8h = 1 day)
    duration_days = {}
    for r in rows:
        hours = float(r.get("Hours", 0) or r.get("PlannedHours", 0) or 0)
        
        # Handle milestones (hours = 0) as zero-duration
        if hours <= 0:
            duration_days[r["UID"]] = 0.0
        else:
            duration_days[r["UID"]] = hours / 8.0
    
    # Topological sort using Kahn's algorithm
    in_degree = {uid: len(preds[uid]) for uid in preds}
    queue = [uid for uid in in_degree if in_degree[uid] == 0]
    topo_order = []
    
    while queue:
        uid = queue.pop(0)
        topo_order.append(uid)
        
        # Reduce in-degree for successors
        for other_uid in in_degree:
            if uid in preds[other_uid]:
                in_degree[other_uid] -= 1
                if in_degree[other_uid] == 0:
                    queue.append(other_uid)
    
    # Check for cycles
    if len(topo_order) != len(rows):
        print(f"[WBS-SCHEDULER] ⚠️ Warning: Detected dependency cycle, {len(rows) - len(topo_order)} tasks unreachable")
        # Add unreachable tasks to end of order
        for r in rows:
            if r["UID"] not in topo_order:
                topo_order.append(r["UID"])
    
    # Calculate earliest start/finish times in business days (offset from project_start)
    est_days = {}
    eft_days = {}
    
    for uid in topo_order:
        # Earliest start = max of predecessors' earliest finish
        if preds[uid]:
            est_days[uid] = max(eft_days[p] for p in preds[uid])
        else:
            est_days[uid] = 0.0
        
        dur_days = duration_days[uid]
        eft_days[uid] = est_days[uid] + dur_days
    
    # Convert day offsets to actual dates using business calendar
    uid_to_sched = {}
    for uid in topo_order:
        start_date = add_business_days(project_start_date, est_days[uid])
        finish_date = add_business_days(start_date, duration_days[uid])
        
        uid_to_sched[uid] = {
            "start": start_date,
            "finish": finish_date,
            "duration_days": duration_days[uid]
        }
    
    return uid_to_sched


def rollup_parent_dates(rows: List[Dict], uid_to_sched: Dict[int, Dict]) -> Dict[int, Dict]:
    """
    Roll up start/finish dates from children to parents using WBS hierarchy.
    Parent start = MIN(child starts), parent finish = MAX(child finishes).
    
    Args:
        rows: List of task dictionaries with 'UID', 'WBS', 'OutlineLevel'
        uid_to_sched: Dict mapping UID to {"start": datetime, "finish": datetime}
    
    Returns:
        Updated uid_to_sched with parent dates rolled up from children
    """
    # Build parent-child relationships from WBS
    wbs_to_uid = {r["WBS"]: r["UID"] for r in rows}
    uid_to_row = {r["UID"]: r for r in rows}
    
    def get_parent_wbs(wbs: str):
        """Get parent WBS code by removing last segment"""
        parts = wbs.split('.')
        if len(parts) <= 1:
            return None
        return '.'.join(parts[:-1])
    
    def get_children_uids(parent_uid: int) -> List[int]:
        """Get all direct child UIDs for a parent"""
        parent_wbs = uid_to_row[parent_uid]["WBS"]
        children = []
        for r in rows:
            if get_parent_wbs(r["WBS"]) == parent_wbs:
                children.append(r["UID"])
        return children
    
    # Sort rows by outline level (deepest first) to roll up bottom-up
    sorted_rows = sorted(rows, key=lambda r: r.get("OutlineLevel", 0), reverse=True)
    
    # Process parents (outline level <= 5)
    for r in sorted_rows:
        uid = r["UID"]
        outline_level = r.get("OutlineLevel", 0)
        
        # Only roll up parents (L3 and above, outline <= 5)
        if outline_level > 5:
            continue
        
        children_uids = get_children_uids(uid)
        if not children_uids:
            continue
        
        # Get child schedules
        child_starts = [uid_to_sched[child]["start"] for child in children_uids if child in uid_to_sched]
        child_finishes = [uid_to_sched[child]["finish"] for child in children_uids if child in uid_to_sched]
        
        if not child_starts or not child_finishes:
            continue
        
        # Roll up: min start, max finish
        parent_start = min(child_starts)
        parent_finish = max(child_finishes)
        
        # Calculate duration in business days
        parent_duration = business_day_diff(parent_start.date(), parent_finish.date())
        
        # Update parent schedule
        uid_to_sched[uid] = {
            "start": parent_start,
            "finish": parent_finish,
            "duration_days": parent_duration
        }
    
    return uid_to_sched
