"""Parse HH:MM AM/PM time strings."""

from datetime import datetime
from datetime import time as dt_time


def parse_time(time_str: str) -> dt_time:
    """
    Parse a time string in HH:MM AM/PM format.

    Raises:
        ValueError: If time string is invalid
    """
    try:
        return datetime.strptime(time_str.strip(), "%I:%M %p").time()
    except Exception as exc:
        raise ValueError(
            f"Invalid time format. Expected HH:MM AM/PM, got: {time_str}"
        ) from exc
