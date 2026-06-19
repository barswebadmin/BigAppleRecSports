"""Parse ISO 8601 datetime strings."""

from datetime import datetime
from zoneinfo import ZoneInfo


def parse_iso_datetime(datetime_str: str) -> datetime:
    """
    Parse an ISO 8601 datetime string with optional 'Z' suffix.

    Raises:
        ValueError: If datetime string is invalid
    """
    try:
        if datetime_str.endswith("Z"):
            return datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        return datetime.fromisoformat(datetime_str).replace(tzinfo=ZoneInfo("UTC"))
    except Exception as exc:
        raise ValueError(
            f"Invalid ISO datetime format. Expected YYYY-MM-DDTHH:MM:SS[Z], got: {datetime_str}"
        ) from exc
