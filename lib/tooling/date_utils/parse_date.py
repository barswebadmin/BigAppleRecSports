"""Parse MM/DD/YY or MM/DD/YYYY date strings."""

from datetime import datetime


def parse_date(date_str: str, default_century: int = 2000) -> datetime:
    """
    Parse a date string in MM/DD/YY or MM/DD/YYYY format.

    Raises:
        ValueError: If date string is invalid
    """
    try:
        month, day, year = map(int, date_str.strip().split("/"))
        if year < 100:
            year += default_century
        return datetime(year, month, day)
    except Exception as exc:
        raise ValueError(
            f"Invalid date format. Expected MM/DD/YY or MM/DD/YYYY, got: {date_str}"
        ) from exc
