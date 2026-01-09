"""Click parameter type for Slack channel identifiers."""

from typing import Dict, Any

from bars_cli.backend_services.slack.slack_service import SlackService
from .base import ValidatedParamType


def _convert_slack_channel_identifier(identifier: str) -> Dict[str, Any]:
    """Convert Slack channel identifier input to dict format.
    
    Delegates to SlackService.normalize_channel_identifier().
    """
    return SlackService.normalize_channel_identifier(identifier)


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

