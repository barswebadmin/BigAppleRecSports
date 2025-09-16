"""
Date handling utilities for Lambda functions
"""

from datetime import datetime, timedelta
from datetime import time as dt_time
from typing import List, Dict, Optional
from zoneinfo import ZoneInfo

def parse_iso_datetime(datetime_str: str) -> datetime:
    """
    Parse an ISO 8601 datetime string with optional 'Z' suffix
    
    Args:
        datetime_str: ISO datetime string (e.g., "2025-09-18T23:00:00Z" or "2025-09-18T23:00:00")
        
    Returns:
        datetime object with timezone info
        
    Raises:
        ValueError: If datetime string is invalid
    """
    try:
        # Handle ISO 8601 format with 'Z' suffix (UTC)
        if datetime_str.endswith('Z'):
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        else:
            # Handle format without timezone info (assume UTC)
            return datetime.fromisoformat(datetime_str).replace(tzinfo=ZoneInfo("UTC"))
    except Exception:
        raise ValueError(f"Invalid ISO datetime format. Expected YYYY-MM-DDTHH:MM:SS or YYYY-MM-DDTHH:MM:SSZ, got: {datetime_str}")

def parse_date(date_str: str, default_century: int = 2000) -> datetime:
    """
    Parse a date string in MM/DD/YY or MM/DD/YYYY format

    Args:
        date_str: Date string in MM/DD/YY or MM/DD/YYYY format
        default_century: Century to use for 2-digit years

    Returns:
        datetime object

    Raises:
        ValueError: If date string is invalid
    """
    try:
        month, day, year = map(int, date_str.strip().split('/'))
        if year < 100:
            year += default_century
        return datetime(year, month, day)
    except Exception:
        raise ValueError(f"Invalid date format. Expected MM/DD/YY or MM/DD/YYYY, got: {date_str}")

def parse_time(time_str: str) -> dt_time:
    """
    Parse a time string in HH:MM AM/PM format

    Args:
        time_str: Time string in HH:MM AM/PM format

    Returns:
        time object

    Raises:
        ValueError: If time string is invalid
    """
    try:
        return datetime.strptime(time_str.strip(), "%I:%M %p").time()
    except Exception:
        raise ValueError(f"Invalid time format. Expected HH:MM AM/PM, got: {time_str}")

def parse_off_dates(dates_str: Optional[str], sport_time: dt_time) -> List[datetime]:
    """
    Parse a comma-separated list of dates and combine with sport time

    Args:
        dates_str: Comma-separated dates in MM/DD/YY or YYYY-MM-DD format
        sport_time: Time object to combine with dates

    Returns:
        List of datetime objects
    """
    off_dates = []
    if dates_str and dates_str.strip():
        for date_str in dates_str.split(','):
            date_str = date_str.strip()
            if not date_str:
                continue
            
            # Try YYYY-MM-DD format first, then fallback to MM/DD/YY
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                date = parse_date(date_str)
            
            off_dates.append(
                datetime.combine(date, sport_time)
            )
    return off_dates

def calculate_discounted_schedule(
    season_start_date: datetime,
    off_dates: List[datetime],
    base_price: float,
    discount_tiers: Optional[List[float]] = None
) -> List[Dict]:
    """
    Calculate a schedule of discounted prices with dates

    Args:
        season_start_date: Starting datetime
        off_dates: List of datetime objects to skip
        base_price: Base price to discount
        discount_tiers: List of discount multipliers (default: [0.85, 0.75, 0.65, 0.55])

    Returns:
        List of dicts with timestamp and price
    """
    if discount_tiers is None:
        discount_tiers = [0.85, 0.75, 0.65, 0.55]

    # Generate initial week dates
    week_dates = [season_start_date]
    for i in range(1, len(discount_tiers)):
        week_date = week_dates[i - 1] + timedelta(days=7)
        week_dates.append(week_date)

    # Shift weeks for off-dates
    for off_date in sorted(off_dates):
        for i in range(len(week_dates)):
            if week_dates[i].date() == off_date.date():
                for j in range(i, len(week_dates)):
                    week_dates[j] += timedelta(days=7)
                break

    # Calculate discounted prices
    return [
        {
            "timestamp": date.isoformat(),
            "updated_price": round(base_price * multiplier, 2)
        }
        for date, multiplier in zip(week_dates, discount_tiers)
    ]
