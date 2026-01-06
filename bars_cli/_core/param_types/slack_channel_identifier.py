"""Click parameter type for Slack channel identifiers."""

from typing import Dict, Any
import sys
import re

sys.path.insert(0, 'backend')
from modules.integrations.slack.models.slack_channel import SlackChannel

from .base import ValidatedParamType


def _convert_slack_channel_identifier(identifier: str) -> Dict[str, Any]:
    """Convert Slack channel identifier input to dict format.
    
    Slack channels can be identified by channel ID (e.g., C092RU7R6PL) or name
    (e.g., "general", "#general", "kickball-leadership").
    
    Channel names can contain:
    - Alphanumeric characters
    - Hyphens (-)
    - Underscores (_)
    - Optional leading hash (#)
    
    Args:
        identifier: Raw identifier string from user input
        
    Returns:
        Dict with keys: "channel_id" or "name"
        
    Raises:
        ValueError: If identifier format is invalid
    """
    identifier = identifier.strip() if identifier else ""
    if not identifier:
        raise ValueError("Slack channel identifier cannot be empty")
    
    params: Dict[str, Any] = {}
    
    # Check if it's a valid Slack channel ID using model validation
    if SlackChannel.is_valid_channel_id(identifier):
        params["channel_id"] = identifier
        return params
    
    # Check if it's a valid channel name
    # Remove leading # if present
    name = identifier.lstrip('#')
    
    # Validate channel name: alphanumeric, hyphens, underscores only
    # Slack channel names must be 1-80 characters
    if not name:
        raise ValueError(
            f"Invalid Slack channel identifier: '{identifier}'\n"
            f"   Channel name cannot be empty (only '#' provided)"
        )
    
    if len(name) > 80:
        raise ValueError(
            f"Invalid Slack channel identifier: '{identifier}'\n"
            f"   Channel name must be 80 characters or less, got {len(name)}"
        )
    
    # Validate characters: alphanumeric, hyphens, underscores only
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        raise ValueError(
            f"Invalid Slack channel identifier: '{identifier}'\n"
            f"   Channel name can only contain alphanumeric characters, hyphens, and underscores"
        )
    
    params["name"] = name
    return params


class SlackChannelIdentifierParam(ValidatedParamType):
    """Click parameter type for Slack channel identifiers.
    
    Supports multiple formats:
    - Channel ID: Returns {channel_id: str}
    - Channel name: Returns {name: str} (with or without leading #)
    """
    
    def __init__(self):
        super().__init__(
            converter_function=_convert_slack_channel_identifier,
            prompt_text="Enter Slack channel identifier (name or channel ID)"
        )


SLACK_CHANNEL_IDENTIFIER = SlackChannelIdentifierParam()

