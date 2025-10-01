from datetime import datetime, timezone, timedelta

try:
    from zoneinfo import ZoneInfo

    TIMEZONE_AVAILABLE = True
except ImportError:
    # For environments without zoneinfo, use a simple UTC offset
    TIMEZONE_AVAILABLE = False
    ZoneInfo = None

from typing import Tuple, Optional
import re
import logging

logger = logging.getLogger(__name__)


def get_eastern_timezone():
    """Get Eastern timezone (handles EST/EDT automatically)"""
    if TIMEZONE_AVAILABLE and ZoneInfo is not None:
        return ZoneInfo("America/New_York")
    else:
        # Fallback to fixed EST offset (this won't handle DST correctly)
        return timezone(timedelta(hours=-5))


def convert_to_eastern_time(dt: datetime) -> datetime:
    """Convert a datetime to Eastern time"""
    if dt is None:
        return datetime.now(get_eastern_timezone())

    # If the datetime is naive (no timezone info), assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    eastern = get_eastern_timezone()

    # If the datetime already carries an offset equal to Eastern at that moment,
    # treat it as already Eastern-local time and avoid altering the wall clock time
    try:
        if dt.utcoffset() == eastern.utcoffset(dt):
            # Normalize tzinfo to Eastern for consistency but preserve wall time
            return dt.astimezone(eastern)
    except Exception:
        pass

    # Otherwise convert from its source tz to Eastern
    return dt.astimezone(eastern)


def parse_shopify_datetime(date_str: str) -> Optional[datetime]:
    """Parse Shopify datetime string to timezone-aware datetime.
    Accepts ISO8601 strings with 'Z' (UTC) or explicit offsets like '-04:00'.
    If no tzinfo is present, assume UTC.
    Preserves correct wall-clock time when the offset already matches Eastern.
    """
    if not date_str:
        return None

    try:
        iso_str = date_str
        if iso_str.endswith("Z"):
            iso_str = iso_str[:-1] + "+00:00"

        dt = datetime.fromisoformat(iso_str)

        # If naive, assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        # Special handling for Shopify "day boundary" timestamps stored as 04:00:00 UTC
        if (
            dt.tzinfo == timezone.utc
            and dt.time().hour == 4
            and dt.time().minute == 0
            and dt.time().second == 0
        ):
            et_dt = dt.astimezone(get_eastern_timezone())
            target_date = et_dt.date()
            if et_dt.time().hour == 0:
                target_date = target_date - timedelta(days=1)
            dt = datetime.combine(target_date, datetime.min.time()).replace(
                tzinfo=get_eastern_timezone()
            ).astimezone(timezone.utc)

        return dt
    except Exception as e:
        logger.warning(f"Could not parse datetime string '{date_str}': {e}")
        return None


def get_season_start_and_end(season: str, year: int) -> Tuple[str, str]:
    """
    Get start and end dates for a given season and year
    Returns dates in ISO format: YYYY-MM-DDTHH:MM:SSZ
    """
    seasons = {
        "Winter": {
            "start_month": 12,
            "start_day": 1,
            "start_year_offset": -1,  # Dec 1 (prev year)
            "end_month": 2,
            "end_day": 1,
            "end_year_offset": 0,  # Feb 1 (current year)
        },
        "Spring": {
            "start_month": 3,
            "start_day": 1,
            "start_year_offset": 0,  # Mar 1
            "end_month": 5,
            "end_day": 31,
            "end_year_offset": 0,  # May 31
        },
        "Summer": {
            "start_month": 5,
            "start_day": 15,
            "start_year_offset": 0,  # May 15
            "end_month": 7,
            "end_day": 31,
            "end_year_offset": 0,  # Jul 31
        },
        "Fall": {
            "start_month": 8,
            "start_day": 15,
            "start_year_offset": 0,  # Aug 15
            "end_month": 10,
            "end_day": 1,
            "end_year_offset": 0,  # Oct 1
        },
    }

    if season not in seasons:
        raise ValueError(
            f"Invalid season: {season}. Must be one of: {list(seasons.keys())}"
        )

    season_info = seasons[season]

    # Calculate start date
    start_year = year + season_info["start_year_offset"]
    start_date = datetime(
        start_year, season_info["start_month"], season_info["start_day"]
    ).strftime("%Y-%m-%dT00:00:00Z")

    # Calculate end date
    end_year = year + season_info["end_year_offset"]
    end_date = datetime(
        end_year, season_info["end_month"], season_info["end_day"]
    ).strftime("%Y-%m-%dT00:00:00Z")

    return start_date, end_date


def extract_season_dates(description_html: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract season start date and off dates from product description HTML
    Based on extractSeasonDates from Utils.gs
    """
    try:
        # Strip HTML tags and decode entities
        text = re.sub(r"<[^>]+>", "", description_html)
        text = text.replace("&nbsp;", " ").replace("&amp;", "&")
        text = re.sub(r"\s+", " ", text).strip()

        logger.info(f"Stripped description HTML: {text}")

        # Pattern to match season dates
        season_dates_pattern = r"Season Dates[^:\d]*[:\s]*?(\d{1,2}\/\d{1,2}\/\d{2,4})\s*[–—-]\s*(\d{1,2}\/\d{1,2}\/\d{2,4})(?:\s*\(\d+\s+weeks(?:,\s*off\s+([^)]+))?\))?"

        match = re.search(season_dates_pattern, text, re.IGNORECASE)
        logger.info(f"Season dates match: {match}")

        if not match:
            return None, None

        season_start_date = match.group(1)
        off_dates_str = match.group(3) if match.group(3) else None

        # Validate date formats
        if not season_start_date or "/" not in season_start_date:
            return None, None

        if off_dates_str and "/" not in off_dates_str:
            return season_start_date, None

        return season_start_date, off_dates_str

    except Exception as e:
        logger.error(f"Error extracting season dates: {str(e)}")
        return None, None


def calculate_refund_amount(
    season_start_date_str: str,
    off_dates_str: Optional[str],
    total_amount_paid: float,
    refund_type: str,
    request_submitted_at: Optional[datetime] = None,
) -> Tuple[float, str]:
    """
    Calculate refund amount based on timing and season dates
    Based on getRefundDue from getRefundDue.gs
    """
    try:
        if not season_start_date_str or not total_amount_paid or not refund_type:
            return 0, "Error calculating refund due - please check order and product"

        if total_amount_paid == 0:
            return 0, "Refund Due: $0 (No payment was made for this order)"

        # Ensure request_submitted_at is timezone-aware
        if request_submitted_at is None:
            request_submitted_at = datetime.now(timezone.utc)
        elif request_submitted_at.tzinfo is None:
            # If naive, assume it's UTC
            request_submitted_at = request_submitted_at.replace(tzinfo=timezone.utc)

        # Parse season start date and make it timezone-aware (UTC)
        month, day, year = map(int, season_start_date_str.split("/"))
        normalized_year = year if year >= 100 else 2000 + year
        season_start_date = datetime(
            normalized_year, month, day, 7, 0, 0, tzinfo=timezone.utc
        )

        # Create week dates (5 weeks starting from season start) - all timezone-aware
        week_dates = [season_start_date]
        for i in range(1, 5):
            next_week_timestamp = week_dates[i - 1].timestamp() + (7 * 24 * 60 * 60)
            next_week = datetime.fromtimestamp(next_week_timestamp, tz=timezone.utc)
            week_dates.append(next_week)

        # Parse off dates and adjust week dates
        if off_dates_str:
            off_dates = []
            for date_str in off_dates_str.split(","):
                date_str = date_str.strip()
                if date_str and "/" in date_str:
                    try:
                        m, d, y = map(int, date_str.split("/"))
                        normalized_year = y if y >= 100 else 2000 + y
                        off_date = datetime(
                            normalized_year, m, d, 7, 0, 0, tzinfo=timezone.utc
                        )
                        off_dates.append(off_date)
                    except ValueError:
                        continue

            # Adjust week dates by shifting subsequent weeks for each off date
            for off_date in sorted(off_dates):
                for i in range(len(week_dates)):
                    if week_dates[i] == off_date:
                        # Shift all subsequent weeks by 7 days
                        for j in range(i, len(week_dates)):
                            shift_timestamp = week_dates[j].timestamp() + (
                                7 * 24 * 60 * 60
                            )
                            week_dates[j] = datetime.fromtimestamp(
                                shift_timestamp, tz=timezone.utc
                            )
                        break

        # Add early tier cutoff (2 weeks before season start) - timezone-aware
        early_tier_cutoff_timestamp = week_dates[0].timestamp() - (14 * 24 * 60 * 60)
        early_tier_cutoff = datetime.fromtimestamp(
            early_tier_cutoff_timestamp, tz=timezone.utc
        )
        week_dates.insert(0, early_tier_cutoff)

        # Define refund tiers
        refund_tiers = (
            [95, 90, 80, 70, 60, 50]
            if refund_type == "refund"
            else [100, 95, 85, 75, 65, 55]
        )
        penalties = [0, 5, 15, 25, 35, 45]
        add_processing = refund_type == "refund"

        refund_percentage = 0
        penalty = 0

        logger.info(f"Season Start Date (UTC @ 7am): {season_start_date.isoformat()}")
        logger.info(f"Request Submitted At (UTC): {request_submitted_at.isoformat()}")

        # Find appropriate refund tier
        for i, week_date in enumerate(week_dates):
            logger.info(
                f"Checking against week {i}: {week_date.isoformat()}. Request before this week? {request_submitted_at < week_date}"
            )
            if request_submitted_at < week_date:
                refund_percentage = refund_tiers[i]
                penalty = penalties[i]
                break

        if refund_percentage == 0:
            return (
                0,
                "*Estimated Refund Due:* $0 (No refund — the request came after week 5 had already started)",
            )

        refund_amount = (refund_percentage / 100) * total_amount_paid
        refund_week_index = refund_tiers.index(refund_percentage)

        # Generate timing description
        if refund_week_index == 0:
            timing_description = "more than 2 weeks before week 1 started"
        elif refund_week_index == 1:
            timing_description = "before week 1 started"
        else:
            # Fix off-by-one error: refund_week_index 2 = week 1, index 3 = week 2, etc.
            timing_description = f"after the start of week {refund_week_index - 1}"

        refund_text = f"*Estimated Refund Due:* ${refund_amount:.2f}\n (This request is calculated to have been submitted {timing_description}. {refund_percentage}% after {penalty}% penalty{' + 5% processing fee' if add_processing else ''})"

        return refund_amount, refund_text

    except Exception as e:
        logger.error(f"Error calculating refund amount: {str(e)}")
        return 0, f"Error calculating refund amount: {str(e)}"


def format_date_only(date) -> Optional[str]:
    """
    Format date to MM/DD/YY format in Eastern time
    Based on formatDateOnly from Google Apps Script Utils.gs

    Args:
        date: datetime object, string, or other convertible type

    Returns:
        Formatted date string (MM/DD/YY) or original string if parsing fails
        Returns None for empty strings
    """
    if isinstance(date, str):
        # Return None for empty strings
        if not date.strip():
            return None

        # Try to parse the string as a datetime
        parsed_date = parse_shopify_datetime(date)
        if parsed_date is None:
            # If parsing fails, return the original string
            return date
        date = parsed_date
    elif not isinstance(date, datetime):
        # Assume it's a timestamp or other convertible type
        try:
            date = (
                datetime.fromtimestamp(date, tz=timezone.utc)
                if isinstance(date, (int, float))
                else datetime.now(timezone.utc)
            )
        except:  # noqa: E722
            return "Unknown Date"

    # Convert to Eastern time
    eastern_date = convert_to_eastern_time(date)
    return eastern_date.strftime("%m/%d/%y")


def format_date_and_time(date) -> str:
    """
    Format date to MM/DD/YY at H:MM AM/PM format in Eastern time
    Based on formatDateAndTime from Google Apps Script Utils.gs
    """
    if isinstance(date, str):
        logger.info(f"using parse_shopify_datetime: {date}")
        date = parse_shopify_datetime(date)
        if date is None:
            return "Unknown Date/Time"
    elif not isinstance(date, datetime):
        logger.info(f"using datetime.fromtimestamp: {date}")
        # Assume it's a timestamp or other convertible type
        try:
            date = (
                datetime.fromtimestamp(date, tz=timezone.utc)
                if isinstance(date, (int, float))
                else datetime.now(timezone.utc)
            )
        except:  # noqa: E722
            return "Unknown Date/Time"

    # Convert to Eastern time
    eastern_date = convert_to_eastern_time(date)

    date_part = eastern_date.strftime("%m/%d/%y")
    time_part = eastern_date.strftime("%I:%M %p").lstrip(
        "0"
    )  # Remove leading zero from hour

    return f"{date_part} at {time_part}"


def calculate_weeks_between_dates(start_date, end_date) -> int:
    """
    Calculate the number of weeks between two dates

    Args:
        start_date: datetime object, string, or other convertible type
        end_date: datetime object, string, or other convertible type

    Returns:
        Number of weeks (rounded to nearest integer)
    """
    # Convert string dates to datetime objects if needed
    if isinstance(start_date, str):
        start_date = parse_shopify_datetime(start_date)
        if start_date is None:
            return 0

    if isinstance(end_date, str):
        end_date = parse_shopify_datetime(end_date)
        if end_date is None:
            return 0

    # If either date is None or invalid, return 0
    if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
        return 0

    # Calculate the difference in days
    delta = end_date - start_date
    days = delta.days

    # Convert to weeks (7 days = 1 week)
    weeks = round(days / 7)

    # Ensure we return at least 1 week if there's any positive duration
    return max(1, weeks) if days > 0 else 0


def format_league_play_times(start_time: str, end_time: str) -> str:
    """
    Format league play times, stripping PM from start time if both times are PM
    Example: "8:00 PM" and "11:00 PM" becomes "8:00 – 11:00 PM"
    """
    if not start_time or not end_time:
        return f"{start_time or ''} – {end_time or ''}"

    start_time = start_time.strip()
    end_time = end_time.strip()

    # Check if both times end with PM
    if start_time.upper().endswith(" PM") and end_time.upper().endswith(" PM"):
        # Strip PM and whitespace from start time
        formatted_start = start_time[:-3].strip()
        return f"{formatted_start} – {end_time}"
    else:
        return f"{start_time} – {end_time}"
