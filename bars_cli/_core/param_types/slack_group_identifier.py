"""Click parameter type for Slack usergroup identifiers."""

from typing import Dict, Any

from bars_cli.backend_services.slack.slack_service import SlackService
from .base import ValidatedParamType


def _convert_slack_group_identifier(identifier: str) -> Dict[str, Any]:
    """Convert Slack usergroup identifier input to dict format.
    
    Delegates to SlackService.normalize_group_identifier().
    """
    return SlackService.normalize_group_identifier(identifier)


class SlackGroupIdentifierParam(ValidatedParamType):
    """Click parameter type for Slack usergroup identifiers.
    
    Supports multiple formats:
    - Group ID: Returns {group_id: str}
    - Handle/Name: Returns {name: str} (with or without leading @ or #)
    """
    
    def __init__(self):
        super().__init__(
            converter_function=_convert_slack_group_identifier,
            prompt_text="Enter Slack usergroup identifier (name, handle, or group ID)"
        )


SLACK_GROUP_IDENTIFIER = SlackGroupIdentifierParam()



