"""
Shared testing utilities and fixtures.

Provides common test helpers, fixtures, and utilities used across all test suites.
"""

from .slack_fixtures import (
    mock_slack_user,
    mock_slack_message,
    mock_button_action,
    mock_slack_channel,
    mock_modal_submission
)
from .domain_fixtures import (
    mock_order_data,
    mock_customer_data,
    mock_refund_request
)

__all__ = [
    # Slack fixtures
    "mock_slack_user",
    "mock_slack_message",
    "mock_button_action",
    "mock_slack_channel",
    "mock_modal_submission",
    # Domain fixtures
    "mock_order_data",
    "mock_customer_data",
    "mock_refund_request",
]

