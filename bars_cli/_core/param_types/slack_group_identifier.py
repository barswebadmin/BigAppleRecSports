"""Click parameter type for Slack usergroup identifiers."""

from typing import Dict, Any
import sys
import re

sys.path.insert(0, 'backend')

from .base import ValidatedParamType


def _is_valid_group_id(group_id: str) -> bool:
    """Check if a string is a valid Slack usergroup ID format.
    
    Usergroup IDs start with 'S' and are 11 characters long, alphanumeric.
    
    Args:
        group_id: String to validate
        
    Returns:
        True if valid usergroup ID format, False otherwise
    """
    if not group_id or not isinstance(group_id, str):
        return False
    return group_id.startswith('S') and len(group_id) == 11 and group_id.isalnum()


def _convert_slack_group_identifier(identifier: str) -> Dict[str, Any]:
    """Convert Slack usergroup identifier input to dict format.
    
    Slack usergroups can be identified by group ID (e.g., S03LZKQSHEU) or handle
    (e.g., "leadership", "@leadership", "dodgeball-monday").
    
    Usergroup handles can contain:
    - Alphanumeric characters
    - Hyphens (-)
    - Underscores (_)
    - Optional leading @
    
    Args:
        identifier: Raw identifier string from user input
        
    Returns:
        Dict with keys: "group_id" or "handle"
        
    Raises:
        ValueError: If identifier format is invalid
    """
    identifier = identifier.strip() if identifier else ""
    if not identifier:
        raise ValueError("Slack usergroup identifier cannot be empty")
    
    params: Dict[str, Any] = {}
    
    # Check if it's a valid Slack usergroup ID
    if _is_valid_group_id(identifier):
        params["group_id"] = identifier
        return params
    
    # Check if it's a valid handle/name
    # Remove leading @ if present
    handle = identifier.lstrip('@')
    
    # Validate handle: alphanumeric, hyphens, underscores only
    # Slack usergroup handles must be 1-255 characters
    if not handle:
        raise ValueError(
            f"Invalid Slack usergroup identifier: '{identifier}'\n"
            f"   Handle cannot be empty (only '@' provided)"
        )
    
    if len(handle) > 255:
        raise ValueError(
            f"Invalid Slack usergroup identifier: '{identifier}'\n"
            f"   Handle must be 255 characters or less, got {len(handle)}"
        )
    
    # Validate characters: alphanumeric, hyphens, underscores only
    if not re.match(r'^[a-zA-Z0-9_-]+$', handle):
        raise ValueError(
            f"Invalid Slack usergroup identifier: '{identifier}'\n"
            f"   Handle can only contain alphanumeric characters, hyphens, and underscores"
        )
    
    params["handle"] = handle
    return params


class SlackGroupIdentifierParam(ValidatedParamType):
    """Click parameter type for Slack usergroup identifiers.
    
    Supports multiple formats:
    - Group ID: Returns {group_id: str}
    - Handle: Returns {handle: str} (with or without leading @)
    """
    
    def __init__(self):
        super().__init__(
            converter_function=_convert_slack_group_identifier,
            prompt_text="Enter Slack usergroup identifier (handle or group ID)"
        )


SLACK_GROUP_IDENTIFIER = SlackGroupIdentifierParam()



