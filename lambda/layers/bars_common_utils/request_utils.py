import time
from datetime import datetime, timedelta

def wait_until_next_minute():
    """Pause until the top of the next full minute (e.g., XX:01:00)."""
    now = datetime.utcnow()
    next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
    wait_seconds = (next_minute - now).total_seconds()

    print(f"⏳ Waiting {wait_seconds:.2f} seconds until {next_minute.isoformat()} UTC...")
    time.sleep(wait_seconds)