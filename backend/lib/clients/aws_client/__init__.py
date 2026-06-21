"""AWS client package — SSM, EventBridge Scheduler."""

from .client import AWSClient, ScheduleNotFoundError

__all__ = [
    "AWSClient",
    "ScheduleNotFoundError",
]
