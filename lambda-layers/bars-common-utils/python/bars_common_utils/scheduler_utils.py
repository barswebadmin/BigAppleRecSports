"""
EventBridge Scheduler utilities for Lambda functions
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from zoneinfo import ZoneInfo

def format_schedule_time(
    datetime_str: str,
    timezone: str = "America/New_York",
    offset_minutes: int = 0
) -> str:
    """
    Standardize datetime handling for EventBridge Scheduler
    
    Args:
        datetime_str: ISO 8601 datetime string (YYYY-MM-DDTHH:MM:SS)
        timezone: Target timezone name
        offset_minutes: Optional offset in minutes to add/subtract
        
    Returns:
        Formatted datetime string in target timezone
        
    Raises:
        ValueError: If datetime string is invalid
    """
    try:
        dt = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S")
        dt = dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(timezone))
        
        if offset_minutes:
            dt = dt + timedelta(minutes=offset_minutes)
            
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception as e:
        raise ValueError(f"Invalid datetime format. Expected YYYY-MM-DDTHH:MM:SS, got: {datetime_str}")

def create_schedule_target(
    function_arn: str,
    role_arn: str,
    input_data: Dict,
    description: Optional[str] = None
) -> Dict:
    """
    Create a standardized EventBridge Scheduler target configuration
    
    Args:
        function_arn: Target Lambda function ARN
        role_arn: IAM role ARN for scheduler
        input_data: Input data for the target
        description: Optional schedule description
        
    Returns:
        Target configuration dictionary
    """
    import json
    return {
        "Arn": function_arn,
        "RoleArn": role_arn,
        "Input": json.dumps(input_data),
        "Description": description or "Created by BARS Lambda"
    } 