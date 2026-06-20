"""Parse comma-separated off-date strings into datetime objects."""

from datetime import datetime
from datetime import time as dt_time
from typing import List, Optional

from shared_utilities.date_utils.parse_date import parse_date


def parse_off_dates(dates_str: Optional[str], sport_time: dt_time) -> List[datetime]:
    """
    Parse a comma-separated list of dates and combine with sport time.

    Accepts YYYY-MM-DD or MM/DD/YY format per entry.
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
            date = parse_date(date_str).date()
        off_dates.append(datetime.combine(date, sport_time))
    return off_dates
