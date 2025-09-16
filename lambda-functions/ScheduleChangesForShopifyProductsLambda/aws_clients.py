"""
AWS client factory helpers for Lambda modules.
"""

import os
import boto3  # type: ignore


def get_scheduler_client():
    """Create an EventBridge Scheduler client with region from env or default."""
    region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    return boto3.client("scheduler", region_name=region)


