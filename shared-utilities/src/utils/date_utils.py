"""
Date Helper Functions
Converted from GAS dateUtils.gs for Python usage
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Union, Tuple

logger = logging.getLogger(__name__)


def format_date_for_shopify(date: datetime) -> str:
    """
    Format a date for Shopify API (ISO 8601 format)

    Args:
        date: The date to format

    Returns:
        ISO 8601 formatted date string

    Raises:
        ValueError: If invalid date provided
    """
    if not isinstance(date, datetime):
        raise ValueError("Invalid date provided")

    return date.isoformat()


def parse_flexible_date(date_string: str) -> datetime:
    """
    Parse a date string in various formats

    Args:
        date_string: Date string to parse

    Returns:
        Parsed date object

    Raises:
        ValueError: If unable to parse date
    """
    if not date_string:
        raise ValueError("Date string is required")

    # Try standard datetime parsing first
    try:
        return datetime.fromisoformat(date_string.replace("Z", "+00:00"))
    except ValueError:
        pass

    # Try common date formats
    date_formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%m-%d-%Y",
        "%d-%m-%Y",
    ]

    for fmt in date_formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue

    # Try MM/DD/YYYY format with regex
    mm_dd_yyyy = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", date_string)
    if mm_dd_yyyy:
        month, day, year = mm_dd_yyyy.groups()
        try:
            return datetime(int(year), int(month), int(day))
        except ValueError:
            pass

    # Try DD/MM/YYYY format with regex
    dd_mm_yyyy = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", date_string)
    if dd_mm_yyyy:
        day, month, year = dd_mm_yyyy.groups()
        try:
            return datetime(int(year), int(month), int(day))
        except ValueError:
            pass

    raise ValueError(f"Unable to parse date: {date_string}")


def get_season_start(date: Optional[datetime] = None) -> datetime:
    """
    Get the start of the current season based on a date

    Args:
        date: Reference date (defaults to now)

    Returns:
        Season start date
    """
    if date is None:
        date = datetime.now()

    year = date.year
    month = date.month

    # Spring: March - May
    if 3 <= month <= 5:
        return datetime(year, 3, 1)
    # Summer: June - August
    elif 6 <= month <= 8:
        return datetime(year, 6, 1)
    # Fall: September - November
    elif 9 <= month <= 11:
        return datetime(year, 9, 1)
    # Winter: December - February
    else:
        if month == 12:
            return datetime(year, 12, 1)
        else:
            return datetime(year - 1, 12, 1)


def format_date_for_slack(date: datetime) -> str:
    """
    Format a date for display in Slack messages

    Args:
        date: Date to format

    Returns:
        Formatted date string
    """
    if not isinstance(date, datetime):
        return "Unknown Date"

    return date.strftime("%a, %b %d, %Y")


def get_business_days_between(start_date: datetime, end_date: datetime) -> int:
    """
    Calculate business days between two dates

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        Number of business days

    Raises:
        ValueError: If invalid dates provided
    """
    if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
        raise ValueError("Valid start and end dates are required")

    count = 0
    current = start_date

    while current <= end_date:
        # Monday = 0, Sunday = 6
        if current.weekday() < 5:  # Monday to Friday
            count += 1
        current += timedelta(days=1)

    return count


def add_business_days(date: datetime, business_days: int) -> datetime:
    """
    Add business days to a date (excludes weekends)

    Args:
        date: Starting date
        business_days: Number of business days to add

    Returns:
        New date with business days added

    Raises:
        ValueError: If invalid date provided
    """
    if not isinstance(date, datetime):
        raise ValueError("Valid date is required")

    result = date
    days_added = 0

    while days_added < business_days:
        result += timedelta(days=1)

        # If it's not a weekend, count it
        if result.weekday() < 5:  # Monday to Friday
            days_added += 1

    return result


def format_date_only(date: Union[datetime, str]) -> Optional[str]:
    """
    Format date only (US format, short year)

    Args:
        date: Date to format

    Returns:
        Formatted date string or None if error
    """
    try:
        if isinstance(date, str):
            date = parse_flexible_date(date)

        return date.strftime("%m/%d/%y")
    except Exception as e:
        logger.error(f"Error formatting date: {e}")
        return None


def format_date_and_time(date: Union[datetime, str]) -> Optional[str]:
    """
    Format date and time together

    Args:
        date: Date to format

    Returns:
        Formatted date and time string if Date is valid, otherwise None
    """
    try:
        if isinstance(date, str):
            date = parse_flexible_date(date)

        date_part = date.strftime("%m/%d/%y")
        time_part = date.strftime("%I:%M %p")
        return f"{date_part} at {time_part}"
    except Exception as e:
        logger.error(f"Error formatting date and time: {e}")
        return None


def extract_season_dates(description_html: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract season dates from product description HTML

    Args:
        description_html: HTML description text

    Returns:
        Tuple of [startDate, offDates] or [None, None] if not found
    """
    # Strip HTML tags and decode entities
    text = re.sub(r"<[^>]+>", "", description_html)
    text = text.replace("&nbsp;", " ")
    text = re.sub(r"\s+", " ", text).strip()

    logger.info(f"Stripped description HTML: {text}")

    season_dates_regex = re.compile(
        r"Season Dates[^:\d]*[:\s]*?(\d{1,2}/\d{1,2}/\d{2,4})\s*[–—-]\s*(\d{1,2}/\d{1,2}/\d{2,4})(?:\s*\(\d+\s+weeks(?:,\s*off\s+([^)]+))?\))?",
        re.IGNORECASE,
    )

    match = season_dates_regex.search(text)
    logger.info(f"Regex match: {match}")

    if not match:
        return None, None

    season_start_date = match.group(1)
    off_dates_str = match.group(3) if len(match.groups()) >= 3 else None

    if not season_start_date or "/" not in season_start_date:
        return None, None

    if off_dates_str and "/" not in off_dates_str:
        return None, None

    return season_start_date, off_dates_str


def format_time_only(date: Union[datetime, str, None]) -> Optional[str]:
    """
    Format time only (useful for events/schedules)

    Args:
        date: Date to format

    Returns:
        Formatted time string or None if invalid
    """
    if not date:
        return None

    try:
        if isinstance(date, str):
            date = parse_flexible_date(date)

        return date.strftime("%I:%M %p")
    except Exception:
        return None


def get_current_season(date: Optional[datetime] = None) -> str:
    """
    Get the current season name based on date

    Args:
        date: Reference date (defaults to now)

    Returns:
        Season name (Spring, Summer, Fall, Winter)
    """
    if date is None:
        date = datetime.now()

    month = date.month

    if 3 <= month <= 5:
        return "Spring"
    elif 6 <= month <= 8:
        return "Summer"
    elif 9 <= month <= 11:
        return "Fall"
    else:
        return "Winter"


def is_business_day(date: datetime) -> bool:
    """
    Check if a date is a business day (Monday-Friday)

    Args:
        date: Date to check

    Returns:
        True if business day, False if weekend
    """
    return date.weekday() < 5


def get_next_business_day(date: datetime) -> datetime:
    """
    Get the next business day after the given date

    Args:
        date: Starting date

    Returns:
        Next business day
    """
    next_day = date + timedelta(days=1)
    while next_day.weekday() >= 5:  # Weekend
        next_day += timedelta(days=1)
    return next_day


def get_previous_business_day(date: datetime) -> datetime:
    """
    Get the previous business day before the given date

    Args:
        date: Starting date

    Returns:
        Previous business day
    """
    prev_day = date - timedelta(days=1)
    while prev_day.weekday() >= 5:  # Weekend
        prev_day -= timedelta(days=1)
    return prev_day
