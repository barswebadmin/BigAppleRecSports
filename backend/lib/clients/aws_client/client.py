"""Unified AWS client for SSM and EventBridge Scheduler operations."""

import boto3
from botocore.config import Config


class ScheduleNotFoundError(Exception):
    """Raised when an EventBridge schedule does not exist."""


class AWSClient:
    """Unified AWS client with SSM and EventBridge Scheduler operations.

    Usage:
        aws = AWSClient()
        params = aws.get_params_by_path("/prod/config")
        aws.create_schedule(Name=..., ...)
    """

    _AWS_REGION = "us-east-1"
    _BOTO_CONFIG = Config(
        connect_timeout=5,
        read_timeout=60,
        retries={"max_attempts": 3}
    )

    def __init__(self, region: str | None = None) -> None:
        region = region or self._AWS_REGION
        self.ssm = boto3.client("ssm", region_name=region, config=self._BOTO_CONFIG)
        self.scheduler = boto3.client("scheduler", region_name=region, config=self._BOTO_CONFIG)

    def get_params_by_path(self, path: str) -> dict[str, str]:
        """Fetch all SSM parameters under path recursively."""
        paginator = self.ssm.get_paginator("get_parameters_by_path")
        params: dict[str, str] = {}
        prefix = path.rstrip("/") + "/"
        for page in paginator.paginate(Path=path, WithDecryption=True, Recursive=True):
            for p in page["Parameters"]:
                key = p["Name"].removeprefix(prefix)
                params[key] = p["Value"]
        return params

    def create_schedule(self, **kwargs) -> dict:
        return self.scheduler.create_schedule(**kwargs)

    def get_schedule(self, name: str, group_name: str) -> dict:
        try:
            return self.scheduler.get_schedule(Name=name, GroupName=group_name)
        except self.scheduler.exceptions.ResourceNotFoundException as exc:
            raise ScheduleNotFoundError(
                f"Schedule '{name}' not found in group '{group_name}': {exc}"
            ) from exc

    def delete_schedule(self, name: str, group_name: str) -> dict:
        return self.scheduler.delete_schedule(Name=name, GroupName=group_name)

    def update_schedule(self, **kwargs) -> dict:
        return self.scheduler.update_schedule(**kwargs)

    def standardize_scheduler_result(
        self,
        schedule_name: str,
        expression: str,
        aws_response: dict
    ) -> dict:
        return {
            "message": f"✅ Schedule '{schedule_name}' created successfully!",
            "new_expression": expression,
            "aws_response": aws_response,
        }

    def standardize_scheduler_error(
        self,
        reason: str,
        schedule_name: str | None = None,
        details: dict | None = None,
    ) -> tuple[int, dict]:
        body: dict = {"error": reason}
        if schedule_name:
            body["scheduleName"] = schedule_name
        if details:
            body["details"] = details
        return 500, body
