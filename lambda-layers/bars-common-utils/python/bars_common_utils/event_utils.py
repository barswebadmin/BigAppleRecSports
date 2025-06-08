"""
Event parsing and validation utilities for Lambda functions
"""

import json
from typing import Any, Dict, List, Union

def parse_event_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standardize event body parsing from API Gateway or direct invocation
    
    Args:
        event: Lambda event dictionary
        
    Returns:
        Parsed event body
        
    Raises:
        ValueError: If event body cannot be parsed
    """
    try:
        if isinstance(event, dict) and "body" in event:
            return json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        return event
    except Exception as e:
        raise ValueError(f"Could not parse event body: {str(e)}")

def validate_required_fields(
    event_body: Dict[str, Any], 
    required_fields: List[str]
) -> Dict[str, Any]:
    """
    Check for required fields in the event body
    
    Args:
        event_body: Parsed event body dictionary
        required_fields: List of required field names
        
    Returns:
        Validated event body
        
    Raises:
        ValueError: If any required fields are missing
    """
    missing = [f for f in required_fields if not event_body.get(f)]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")
    return event_body

def get_field_safe(
    event_body: Dict[str, Any],
    field_name: str,
    default: Any = None
) -> Any:
    """
    Safely get a field from the event body with a default value
    
    Args:
        event_body: Event body dictionary
        field_name: Name of the field to get
        default: Default value if field is missing
        
    Returns:
        Field value or default
    """
    return event_body.get(field_name, default) 