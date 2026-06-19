"""
AWS client factory helpers for Lambda modules.
"""

import os
import boto3
from mypy_boto3_scheduler import EventBridgeSchedulerClient


def get_scheduler_client() -> EventBridgeSchedulerClient:
    """Create an EventBridge Scheduler client with region from env or default."""
    region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    return boto3.Session().client("scheduler", region_name=region)
