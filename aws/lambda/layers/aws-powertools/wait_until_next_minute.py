"""Pause execution until the top of the next full minute."""

import time
from datetime import datetime, timedelta


def wait_until_next_minute() -> None:
    """Pause until the top of the next full minute (e.g., XX:01:00)."""
    now = datetime.utcnow()
    next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
    wait_seconds = (next_minute - now).total_seconds()
    print(f"⏳ Waiting {wait_seconds:.2f} seconds until {next_minute.isoformat()} UTC...")
    time.sleep(wait_seconds)


def wait_until_next_minute_from(start_time: datetime) -> float:
    """
    Wait until second 59 of the current minute from start_time.
    
    This allows data collection to happen immediately, then waits until :59
    of the same minute before executing mutations, giving them ~1 second to
    complete before the minute boundary.
    
    If the next minute has already started by the time we check, execute
    immediately (don't wait until :59 of the new minute).
    
    Args:
        start_time: The reference time (typically when lambda execution started)
    
    Returns:
        The actual wait time in seconds (0 if already past target or in next minute)
    
    Logic:
        - If start_time is 10:30:15, target is 10:30:59
        - If current time is 10:30:45, wait 14 seconds until 10:30:59
        - If current time is 10:31:05 (next minute), execute immediately (no wait)
        - If current time is 10:30:59+, execute immediately (already at target)
    
    Example:
        start = datetime.utcnow()  # 10:30:15
        # ... do data collection (3 seconds) ...
        # now = 10:30:18
        wait_until_next_minute_from(start)  # Waits 41s until 10:30:59
        # ... execute mutations at 10:30:59 ...
    """
    now = datetime.utcnow()
    
    # Target is :59 of the same minute as start_time
    target_time = start_time.replace(second=59, microsecond=0)
    
    # Calculate the next minute boundary from start_time
    next_minute_boundary = (start_time + timedelta(minutes=1)).replace(second=0, microsecond=0)
    
    # If we've crossed into the next minute, execute immediately
    if now >= next_minute_boundary:
        print(f"⏭️  Already in next minute at {now.isoformat()} UTC (past {next_minute_boundary.isoformat()}), executing immediately")
        return 0.0
    
    # If we're already at or past :59 of the current minute, execute immediately
    if now >= target_time:
        print(f"⏭️  Already at {now.isoformat()} UTC (past {target_time.isoformat()}), executing immediately")
        return 0.0
    
    wait_seconds = (target_time - now).total_seconds()
    print(f"⏳ Waiting {wait_seconds:.2f}s until {target_time.isoformat()} UTC (1s before minute boundary)...")
    time.sleep(wait_seconds)
    return wait_seconds
