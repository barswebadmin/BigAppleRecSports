"""Click parameter type for Slack user identifiers."""

from typing import Dict, Any
import sys
import validators

sys.path.insert(0, 'backend')
from modules.integrations.slack.models.slack_user import SlackUser

from .base import ValidatedParamType


def _convert_slack_user_identifier(identifier: str) -> Dict[str, Any]:
    """Convert Slack user identifier input to dict format.
    
    Slack users can be identified by email or Slack user ID (e.g., U03LZKQSHEU).
    
    Args:
        identifier: Raw identifier string from user input
        
    Returns:
        Dict with keys: "email" or "user_id"
        
    Raises:
        ValueError: If identifier format is invalid
    """
    identifier = identifier.strip() if identifier else ""
    if not identifier:
        raise ValueError("Slack user identifier cannot be empty")
    
    params: Dict[str, Any] = {}
    
    # Check if it's a valid email
    if validators.email(identifier):
        params["email"] = identifier
        return params
    
    # Check if it's a valid Slack user ID using model validation
    if SlackUser.is_valid_user_id(identifier):
        params["user_id"] = identifier
        return params
    
    raise ValueError(
        f"Invalid Slack user identifier: '{identifier}'\n"
        f"   Must be a valid email address or Slack user ID (e.g., U03LZKQSHEU)"
    )


class SlackUserIdentifierParam(ValidatedParamType):
    """Click parameter type for Slack user identifiers.
    
    Supports multiple formats:
    - Email: Returns {email: str}
    - User ID: Returns {user_id: str}
    """
    
    def __init__(self):
        super().__init__(
            converter_function=_convert_slack_user_identifier,
            prompt_text="Enter Slack user identifier (email or user ID)"
        )


SLACK_USER_IDENTIFIER = SlackUserIdentifierParam()

