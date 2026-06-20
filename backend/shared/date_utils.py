"""Date utilities for backend - thin wrappers over lib.tooling.datetime.

For pure datetime utilities, import directly from lib.tooling.datetime:
    from lib.tooling.datetime import (
        get_eastern_timezone,
        convert_to_eastern_time,
        parse_shopify_datetime,
        format_date_only,
        format_date_and_time,
        calculate_weeks_between_dates,
    )

This module provides additional backend-specific utilities.
"""

from datetime import datetime
from typing import TypedDict

from lib.tooling.datetime import (  # noqa: F401 — re-exported for callers
    calculate_weeks_between_dates,
    convert_to_eastern_time,
    format_date_and_time,
    format_date_only,
    get_eastern_timezone,
    parse_shopify_datetime,
)


class SeasonBound(TypedDict):
    start_month: int
    start_day: int
    start_year_offset: int
    end_month: int
    end_day: int
    end_year_offset: int


SEASON_BOUNDS: dict[str, SeasonBound] = {
    "Winter": SeasonBound(start_month=12, start_day= 1, start_year_offset=-1, end_month= 2, end_day= 1, end_year_offset=0),
    "Spring": SeasonBound(start_month= 3, start_day= 1, start_year_offset= 0, end_month= 5, end_day=31, end_year_offset=0),
    "Summer": SeasonBound(start_month= 5, start_day=15, start_year_offset= 0, end_month= 7, end_day=31, end_year_offset=0),
    "Fall":   SeasonBound(start_month= 8, start_day=15, start_year_offset= 0, end_month=10, end_day= 1, end_year_offset=0),
}


def get_season_start_and_end(season: str, year: int) -> tuple[str, str]:
    """Return (start, end) ISO dates for a given season and year.

    Winter start is Dec of the prior year; all others start/end within `year`.
    """
    if season not in SEASON_BOUNDS:
        raise ValueError(f"Invalid season: {season!r}. Must be one of: {list(SEASON_BOUNDS)}")

    bounds = SEASON_BOUNDS[season]
    fmt = "%Y-%m-%dT00:00:00Z"
    start = datetime(year + bounds["start_year_offset"], bounds["start_month"], bounds["start_day"]).strftime(fmt)
    end   = datetime(year + bounds["end_year_offset"],   bounds["end_month"],   bounds["end_day"]  ).strftime(fmt)
    return start, end


def format_league_play_times(start_time: str, end_time: str) -> str:
    """Format a play-time range, collapsing a shared PM suffix.

    "8:00 PM" + "11:00 PM" → "8:00 – 11:00 PM"
    "8:00 PM" + "11:00 AM" → "8:00 PM – 11:00 AM"
    """
    start, end = (start_time or "").strip(), (end_time or "").strip()
    if not start or not end:
        return f"{start} – {end}"
    both_pm = start.upper().endswith(" PM") and end.upper().endswith(" PM")
    return f"{start[:-3].strip()} – {end}" if both_pm else f"{start} – {end}"
