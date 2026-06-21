"""Date and datetime utilities.

Organized by concern:
  - Timezone      get_eastern_timezone, convert_to_eastern_time
  - Parsing       parse_shopify_datetime, parse_iso_datetime, parse_date,
                  parse_time, parse_off_dates
  - Formatting    format_date_only, format_date_and_time, format_schedule_time,
                  normalize_date_str
  - Extraction    extract_season_dates, split_off_dates
  - Calculations  calculate_weeks_between_dates, calculate_discounted_schedule,
                  get_discount_dates_and_prices
"""

from warnings import deprecated
import logging
import re
from datetime import datetime
from datetime import time as dt_time
from datetime import timedelta, timezone
from typing import Any

from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# =============================================================================
# ENTIRE FILE IS DEPRECATED - REGEX PARSING WILL BE REPLACED BY DYNAMO RECORDS
# =============================================================================

_INPUT_DATE_FORMATS = ("%m/%d/%y", "%m/%d/%Y")

# Matches "Season Dates: <start> – <end> (<weeks> weeks, off <off_dates>)".
# Tolerant of hyphen/en-dash/em-dash separators, missing weeks clause, missing
# off-dates clause.
_SEASON_DATES_REGEX = re.compile(
    r"Season Dates[^:\d]*[:\s]*?"
    r"(\d{1,2}/\d{1,2}/\d{2,4})\s*[–—-]\s*(\d{1,2}/\d{1,2}/\d{2,4})"
    r"(?:\s*\(\d+\s+weeks(?:,\s*off\s+([^)]+))?\))?",
    re.IGNORECASE,
)


# =============================================================================
# Timezone
# =============================================================================
@deprecated("""Use ZoneInfo('America/New_York') instead. one-liner thin wrappers are a clear anti-pattern.
as are no-arg functions. there HAS to be a library method that handles this more gracefully.
""")
def get_eastern_timezone() -> ZoneInfo:
    """Return the Eastern timezone (handles EST/EDT automatically)."""
    return ZoneInfo("America/New_York")


def convert_to_eastern_time(dt: datetime) -> datetime:
    """Convert a datetime to Eastern time."""
    if dt is None:
        return datetime.now(get_eastern_timezone())

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    eastern = get_eastern_timezone()

    try:
        if dt.utcoffset() == eastern.utcoffset(dt):
            return dt.astimezone(eastern)
    except Exception:
        pass

    return dt.astimezone(eastern)


# =============================================================================
# Parsing
# =============================================================================
@deprecated("this should have used a library method.")
def parse_shopify_datetime(date_str: str) -> datetime | None:
    """Parse a Shopify ISO8601 datetime string to a timezone-aware datetime.

    Accepts strings with 'Z' (UTC) or explicit offsets like '-04:00'.
    If no tzinfo is present, assumes UTC.

    Applies a midnight-correction heuristic: a UTC timestamp at exactly
    04:00:00 is treated as Eastern midnight and adjusted back one day.
    """
    if not date_str:
        return None

    try:
        iso_str = date_str
        if iso_str.endswith("Z"):
            iso_str = iso_str[:-1] + "+00:00"

        dt = datetime.fromisoformat(iso_str)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

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


@deprecated("this should have used a library method.")
def parse_iso_datetime(datetime_str: str) -> datetime:
    """Parse an ISO 8601 datetime string with optional 'Z' suffix.

    Returns a timezone-aware datetime (UTC if no offset given).
    Raises ValueError on invalid input.
    """
    try:
        if datetime_str.endswith("Z"):
            return datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        return datetime.fromisoformat(datetime_str).replace(tzinfo=ZoneInfo("UTC"))
    except Exception:
        raise ValueError(
            f"Invalid ISO datetime format. Expected YYYY-MM-DDTHH:MM:SS[Z], got: {datetime_str}"
        )

@deprecated("this should have used a library method.")
def parse_date(date_str: str, default_century: int = 2000) -> datetime:
    """Parse a date string in MM/DD/YY or MM/DD/YYYY format.

    Raises ValueError on invalid input.
    """
    try:
        month, day, year = map(int, date_str.strip().split("/"))
        if year < 100:
            year += default_century
        return datetime(year, month, day)
    except Exception:
        raise ValueError(
            f"Invalid date format. Expected MM/DD/YY or MM/DD/YYYY, got: {date_str}"
        )


@deprecated("this should have used a library method. and one-line wrapper methods (minus the try/except, which doesn't count) are anti-patterns.")
def parse_time(time_str: str) -> dt_time:
    """Parse a time string in HH:MM AM/PM format.

    Raises ValueError on invalid input.
    """
    try:
        return datetime.strptime(time_str.strip(), "%I:%M %p").time()
    except Exception:
        raise ValueError(f"Invalid time format. Expected HH:MM AM/PM, got: {time_str}")

@deprecated("use a library.")
def parse_off_dates(dates_str: str | None, sport_time: dt_time) -> list[datetime]:
    """Parse a comma-separated list of off-dates combined with a sport time.

    Accepts both YYYY-MM-DD and MM/DD/YY formats per entry.
    """
    off_dates = []
    if not dates_str or not dates_str.strip():
        return off_dates

    for date_str in dates_str.split(","):
        date_str = date_str.strip()
        if not date_str:
            continue
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            date = parse_date(date_str)
        off_dates.append(datetime.combine(date, sport_time))

    return off_dates


# =============================================================================
# Formatting
# =============================================================================
@deprecated("this should have used a library method, and the level of cognitive complexity is an extreme anti-pattern.")
def format_date_only(date: Any) -> str | None:
    """Format any date value to MM/DD/YY in Eastern time.

    Accepts: datetime object, ISO8601 string, int/float timestamp.
    Returns None for empty strings.
    """
    if isinstance(date, str):
        if not date.strip():
            return None
        parsed_date = parse_shopify_datetime(date)
        if parsed_date is None:
            return date
        date = parsed_date
    elif not isinstance(date, datetime):
        try:
            date = (
                datetime.fromtimestamp(date, tz=timezone.utc)
                if isinstance(date, (int, float))
                else datetime.now(timezone.utc)
            )
        except Exception:
            return "Unknown Date"

    eastern_date = convert_to_eastern_time(date)
    return eastern_date.strftime("%m/%d/%y")

@deprecated("this should have used a library method, and the level of cognitive complexity is an extreme anti-pattern.")
def format_date_and_time(date: Any) -> str:
    """Format any date value to 'MM/DD/YY at H:MM AM/PM' in Eastern time."""
    if isinstance(date, str):
        logger.info(f"using parse_shopify_datetime: {date}")
        date = parse_shopify_datetime(date)
        if date is None:
            return "Unknown Date/Time"
    elif not isinstance(date, datetime):
        logger.info(f"using datetime.fromtimestamp: {date}")
        try:
            date = (
                datetime.fromtimestamp(date, tz=timezone.utc)
                if isinstance(date, (int, float))
                else datetime.now(timezone.utc)
            )
        except Exception:
            return "Unknown Date/Time"

    eastern_date = convert_to_eastern_time(date)
    date_part = eastern_date.strftime("%m/%d/%y")
    time_part = eastern_date.strftime("%I:%M %p").lstrip("0")
    return f"{date_part} at {time_part}"

@deprecated("use library methods.")
def format_schedule_time(
    datetime_str: str,
    tz: str = "America/New_York",
    offset_minutes: int = 0,
) -> str:
    """Convert an ISO 8601 datetime string to a target timezone for EventBridge.

    Raises ValueError on invalid input.
    """
    try:
        dt = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S")
        dt = dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(tz))
        if offset_minutes:
            dt = dt + timedelta(minutes=offset_minutes)
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        raise ValueError(
            f"Invalid datetime format. Expected YYYY-MM-DDTHH:MM:SS, got: {datetime_str}"
        )

@deprecated("use library methods, and inner nesting is anti pattern.")
def normalize_date_str(date_str: str | None) -> str | None:
    """Canonicalize M/D/YY or M/D/YYYY to M/D/YY (no zero-padding).

    Returns None for empty input. Raises ValueError on unrecognized format.
    """
    if not date_str:
        return None

    for fmt in _INPUT_DATE_FORMATS:
        try:
            dt = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue
    else:
        raise ValueError(f"Unrecognized date format: {date_str}")

    # Portable equivalent of strftime("%-m/%-d/%y"); %- is glibc-only.
    return f"{dt.month}/{dt.day}/{dt:%y}"


# =============================================================================
# HTML / text extraction
# =============================================================================

def extract_season_dates(description_html: str) -> tuple[str | None, str | None]:
    """Return ``(start_date, off_dates_comma_str)`` from a Shopify descriptionHtml.

    Both elements may be None if not present.
    """
    stripped = re.sub(r"<[^>]+>", "", description_html).replace("&nbsp;", " ").strip()
    match = _SEASON_DATES_REGEX.search(stripped)
    if not match:
        return None, None
    return match.group(1), match.group(3)


def split_off_dates(off_dates_comma_separated: str | None) -> list[str]:
    """Split a comma-separated off-dates string into a list of trimmed entries."""
    if not off_dates_comma_separated:
        return []
    return [d.strip() for d in off_dates_comma_separated.split(",") if d.strip()]


# =============================================================================
# Calculations
# =============================================================================

def calculate_weeks_between_dates(start_date: Any, end_date: Any) -> int:
    """Return the number of weeks between two dates (rounded, minimum 1 if positive)."""
    if isinstance(start_date, str):
        start_date = parse_shopify_datetime(start_date)
        if start_date is None:
            return 0
    if isinstance(end_date, str):
        end_date = parse_shopify_datetime(end_date)
        if end_date is None:
            return 0

    if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
        return 0

    days = (end_date - start_date).days
    weeks = round(days / 7)
    return max(1, weeks) if days > 0 else 0


def calculate_discounted_schedule(
    season_start_date: datetime,
    off_dates: list[datetime],
    base_price: float,
    discount_tiers: list[float] | None = None,
) -> list[dict]:
    """Build a list of {timestamp, updated_price} dicts across discount weeks.

    Default tiers: 85%, 75%, 65%, 55% of base_price.
    Off-dates shift all subsequent weeks by one week.
    """
    if discount_tiers is None:
        discount_tiers = [0.85, 0.75, 0.65, 0.55]

    week_dates = [season_start_date]
    for i in range(1, len(discount_tiers)):
        week_dates.append(week_dates[i - 1] + timedelta(days=7))

    for off_date in sorted(off_dates):
        for i in range(len(week_dates)):
            if week_dates[i].date() == off_date.date():
                for j in range(i, len(week_dates)):
                    week_dates[j] += timedelta(days=7)
                break

    return [
        {"timestamp": date.isoformat(), "updated_price": round(base_price * mult, 2)}
        for date, mult in zip(week_dates, discount_tiers)
    ]


def get_discount_dates_and_prices(
    season_start_date: str,
    off_dates_comma_separated: str | None,
    sport_start_time: str,
    price: float,
) -> list[dict]:
    """Calculate a schedule of discounted prices based on season dates."""
    # Lazy imports: shared_utilities is a runtime dep not always present in tests.
    from shared_utilities.calculate_discounted_schedule import (  # type: ignore[import]
        calculate_discounted_schedule as _calc,
    )
    from shared_utilities.date_utils.parse_date import parse_date as _parse_date  # type: ignore[import]
    from shared_utilities.date_utils.parse_off_dates import parse_off_dates as _parse_off_dates  # type: ignore[import]
    from shared_utilities.date_utils.parse_time import parse_time as _parse_time  # type: ignore[import]

    print("📍 Entered get_discount_dates_and_prices()")
    print(
        f"🔎 Inputs:\n- season_start_date: {season_start_date}\n"
        f"- off_dates_comma_separated: {off_dates_comma_separated}\n"
        f"- sport_start_time: {sport_start_time}\n- price: {price}"
    )

    try:
        try:
            season_date = datetime.strptime(season_start_date, "%Y-%m-%d").date()
            print(f"✅ Parsed season start date (YYYY-MM-DD): {season_date}")
        except ValueError:
            season_date = _parse_date(season_start_date)
            print(f"✅ Parsed season start date (MM/DD/YY): {season_date}")

        sport_start_time_parsed = _parse_time(sport_start_time)
        print(f"✅ Parsed sport start time: {sport_start_time_parsed}")

        season_start = datetime.combine(season_date, sport_start_time_parsed)
        print(f"✅ Combined season start datetime: {season_start}")

        off_dates = _parse_off_dates(off_dates_comma_separated, sport_start_time_parsed)
        if off_dates:
            print(f"📅 Parsed off dates: {[d.isoformat() for d in off_dates]}")
        else:
            print("ℹ️ No off dates provided.")

        discount_schedule = _calc(season_start_date=season_start, off_dates=off_dates, base_price=price)
        print(f"📈 Final discount schedule: {discount_schedule}")
        print("✅ Exiting get_discount_dates_and_prices() successfully")
        return discount_schedule

    except ValueError as e:
        msg = f"❌ {e}"
        print(msg)
        raise ValueError(msg)
    except Exception as e:
        msg = f"❌ Unexpected error: {e}"
        print(msg)
        raise ValueError(msg)
