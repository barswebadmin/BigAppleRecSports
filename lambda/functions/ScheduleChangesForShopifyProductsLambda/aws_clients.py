"""
AWS client factory helpers for Lambda modules.
"""

import os


def get_scheduler_client():
    """Create an EventBridge Scheduler client with region from env or default.

    boto3 is imported lazily to avoid hard dependency during test collection.
    """
    # Lazy import to avoid requiring boto3 at module import time in tests
    import boto3  # type: ignore

    region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    return boto3.client("scheduler", region_name=region)


