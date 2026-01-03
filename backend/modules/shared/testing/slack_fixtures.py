"""
Shared Slack test fixtures.

Provides mock Slack payloads, events, and objects for testing.
"""

import pytest
from typing import Dict, Any
from datetime import datetime


@pytest.fixture
def mock_slack_user() -> Dict[str, Any]:
    """
    Mock Slack user object.
    
    Returns:
        Dict with standard Slack user fields
    """
    return {
        "id": "U12345TEST",
        "name": "test_user",
        "real_name": "Test User",
        "email": "test.user@example.com",
        "is_bot": False,
        "deleted": False
    }


@pytest.fixture
def mock_slack_channel() -> Dict[str, Any]:
    """
    Mock Slack channel object.
    
    Returns:
        Dict with standard Slack channel fields
    """
    return {
        "id": "C12345TEST",
        "name": "test-channel",
        "is_channel": True,
        "is_private": False,
        "is_archived": False
    }


@pytest.fixture
def mock_slack_message() -> Dict[str, Any]:
    """
    Mock Slack message object.
    
    Returns:
        Dict with standard Slack message fields
    """
    return {
        "channel": "C12345TEST",
        "ts": "1234567890.123456",
        "text": "Test message",
        "user": "U12345TEST",
        "type": "message"
    }


@pytest.fixture
def mock_button_action() -> Dict[str, Any]:
    """
    Mock Slack button action payload.
    
    Returns:
        Dict with standard Slack block_actions payload structure
    """
    return {
        "type": "block_actions",
        "user": {
            "id": "U12345TEST",
            "username": "test_user",
            "name": "test_user"
        },
        "channel": {
            "id": "C12345TEST",
            "name": "test-channel"
        },
        "message": {
            "ts": "1234567890.123456",
            "text": "Original message"
        },
        "actions": [
            {
                "action_id": "test_action",
                "block_id": "test_block",
                "value": "test_value",
                "type": "button",
                "action_ts": "1234567890.123456"
            }
        ],
        "response_url": "https://hooks.slack.com/actions/test/url",
        "trigger_id": "test_trigger_id"
    }


@pytest.fixture
def mock_modal_submission() -> Dict[str, Any]:
    """
    Mock Slack modal submission payload.
    
    Returns:
        Dict with standard Slack view_submission payload structure
    """
    return {
        "type": "view_submission",
        "user": {
            "id": "U12345TEST",
            "username": "test_user",
            "name": "test_user"
        },
        "view": {
            "id": "V12345TEST",
            "type": "modal",
            "callback_id": "test_modal",
            "state": {
                "values": {
                    "text_input_block": {
                        "text_input_action": {
                            "type": "plain_text_input",
                            "value": "Test input value"
                        }
                    }
                }
            },
            "private_metadata": ""
        },
        "response_urls": []
    }


@pytest.fixture
def mock_slash_command() -> Dict[str, Any]:
    """
    Mock Slack slash command payload.
    
    Returns:
        Dict with standard Slack slash command structure
    """
    return {
        "command": "/test-command",
        "text": "test argument",
        "user_id": "U12345TEST",
        "user_name": "test_user",
        "channel_id": "C12345TEST",
        "channel_name": "test-channel",
        "team_id": "T12345TEST",
        "team_domain": "test-workspace",
        "trigger_id": "test_trigger_id",
        "response_url": "https://hooks.slack.com/commands/test/url"
    }


@pytest.fixture
def mock_file_shared_event() -> Dict[str, Any]:
    """
    Mock Slack file_shared event payload.
    
    Returns:
        Dict with standard Slack file_shared event structure
    """
    return {
        "type": "event_callback",
        "event": {
            "type": "file_shared",
            "file_id": "F12345TEST",
            "user_id": "U12345TEST",
            "channel_id": "C12345TEST",
            "event_ts": "1234567890.123456"
        },
        "event_time": 1234567890
    }


@pytest.fixture
def mock_slack_file() -> Dict[str, Any]:
    """
    Mock Slack file object.
    
    Returns:
        Dict with standard Slack file fields
    """
    return {
        "id": "F12345TEST",
        "created": 1234567890,
        "timestamp": 1234567890,
        "name": "test_file.csv",
        "title": "Test File",
        "mimetype": "text/csv",
        "filetype": "csv",
        "pretty_type": "CSV",
        "user": "U12345TEST",
        "size": 1024,
        "url_private": "https://files.slack.com/files-pri/test/file.csv",
        "url_private_download": "https://files.slack.com/files-pri/test/download/file.csv",
        "channels": ["C12345TEST"],
        "is_public": False
    }


def create_mock_blocks(num_blocks: int = 3) -> list:
    """
    Create a list of mock Slack blocks.
    
    Args:
        num_blocks: Number of blocks to create
        
    Returns:
        List of Slack block dicts
    """
    blocks = []
    for i in range(num_blocks):
        blocks.append({
            "type": "section",
            "block_id": f"block_{i}",
            "text": {
                "type": "mrkdwn",
                "text": f"Test block {i}"
            }
        })
    return blocks


def create_mock_slack_response(
    ok: bool = True,
    channel: str = "C12345TEST",
    ts: str = "1234567890.123456",
    error: str = None
) -> Dict[str, Any]:
    """
    Create a mock Slack API response.
    
    Args:
        ok: Whether the response was successful
        channel: Channel ID
        ts: Message timestamp
        error: Optional error message
        
    Returns:
        Mock Slack API response dict
    """
    response = {
        "ok": ok,
        "channel": channel,
        "ts": ts
    }
    
    if not ok and error:
        response["error"] = error
    
    return response

