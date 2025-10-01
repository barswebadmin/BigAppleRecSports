"""
Test utilities for Slack service testing.
Provides clean interfaces for common test operations.
"""

from typing import Any, Dict, Optional
from unittest.mock import Mock


def create_mock_slack_orchestrator() -> Mock:
    """
    Create a properly configured mock SlackOrchestrator for testing.
    
    Returns:
        Mock SlackOrchestrator with common test methods configured
    """
    from unittest.mock import AsyncMock
    
    mock_service = Mock()
    
    # Add convenience methods that delegate to the actual nested structure
    mock_service.verify_slack_signature = Mock(return_value=True)
    
    # Set up the nested structure that the real service uses
    mock_service.slack_security.verify_slack_signature = mock_service.verify_slack_signature
    mock_service.slack_security.extract_text_from_blocks = Mock(return_value="Extracted message text")
    
    # Mock the main async method that the router calls
    mock_service.handle_slack_interaction = AsyncMock(
        return_value={"text": "✅ Webhook received and logged successfully!"}
    )
    
    return mock_service


def create_mock_config(environment: str = "debug") -> Mock:
    """
    Create a mock config object for testing.
    
    Args:
        environment: The environment to simulate (default: "debug")
        
    Returns:
        Mock config object with common test properties
    """
    mock_config = Mock()
    mock_config.environment = environment
    mock_config.is_production_mode = False
    return mock_config
