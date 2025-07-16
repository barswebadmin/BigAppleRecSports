from datetime import datetime
import re

def format_date_only(date_str):
    if not date_str:
        return None
    try:
        # Accept formats like 4/28/25 or 04/28/2025
        dt = datetime.strptime(date_str, "%m/%d/%y")
    except ValueError:
        try:
            dt = datetime.strptime(date_str, "%m/%d/%Y")
        except ValueError:
            raise ValueError(f"Unrecognized date format: {date_str}")
    return dt.strftime("%-m/%-d/%y")

def extract_season_dates(description_html):
    # Remove tags and decode basic entities
    stripped = re.sub(r"<[^>]+>", "", description_html).replace("&nbsp;", " ").strip()

    regex = re.compile(
        r"Season Dates[^:\d]*[:\s]*?(\d{1,2}/\d{1,2}/\d{2,4})\s*[–—-]\s*(\d{1,2}/\d{1,2}/\d{2,4})(?:\s*\(\d+\s+weeks(?:,\s*off\s+([^)]+))?\))?",
        re.IGNORECASE
    )

    match = regex.search(stripped)
    if not match:
        return None, None

    season_start_date = match.group(1)
    off_dates_str = match.group(3)
    return season_start_date, off_dates_str