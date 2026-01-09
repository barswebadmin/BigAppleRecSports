"""Click parameter type for Slack user identifiers."""

from typing import Dict, Any

from bars_cli.backend_services.slack.slack_service import SlackService
from .base import ValidatedParamType


def _convert_slack_user_identifier(identifier: str) -> Dict[str, Any]:
    """Convert Slack user identifier input to dict format.
    
    Delegates to SlackService.normalize_user_identifier().
    """
    return SlackService.normalize_user_identifier(identifier)


class SlackUserIdentifierParam(ValidatedParamType):
    """Click parameter type for Slack user identifiers.
    
    Supports multiple formats:
    - Email: Returns {email: str}
    - User ID: Returns {user_id: str}
    - Handle/username: Returns {handle: str}
    - Display name: Returns {display_name: str}
    """
    
    def __init__(self):
        super().__init__(
            converter_function=_convert_slack_user_identifier,
            prompt_text="Enter Slack user identifier (email, user ID, handle, or display name)"
        )


SLACK_USER_IDENTIFIER = SlackUserIdentifierParam()

