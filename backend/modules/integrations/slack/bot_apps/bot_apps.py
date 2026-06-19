"""
Slack Bot Apps - DEPRECATED

This module is deprecated. Slack commands should instantiate clients directly.
"""


class SlackBot:
    """DEPRECATED: Use shared_utilities.clients directly."""

    def __init__(self) -> None:
        raise NotImplementedError(
            "SlackBot is deprecated. Use shared_utilities.clients directly."
        )


# Stub instances for backward compatibility
admin_bot = None
leadership_bot = None
