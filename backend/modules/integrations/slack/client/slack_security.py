"""
Slack security and parsing methods.
Handles signature verification, button parsing, and text extraction from Slack blocks.
"""

import logging
from shared.security.webhook_signature_verification import (
    is_valid_webhook_signature,
    extract_slack_webhook_signature,
    MissingSlackSigningSecretError
)

logger = logging.getLogger(__name__)


def verify_slack_signature(headers: dict, body: bytes, app_id: str, bots_config) -> bool:
    """
    Verify Slack signature using the raw request body and app_id.
    
    Args:
        headers: Request headers containing x-slack-signature and x-slack-request-timestamp
        body: Raw request body bytes
        app_id: Slack app ID to identify the bot
        bots_config: Bots configuration object with by_app_id method
        
    Returns:
        True if signature is valid
        
    Raises:
        MissingSlackSigningSecretError: If signing secret cannot be found for app_id
        Various SlackSignatureError subclasses: For missing headers, body, or app_id
        InvalidSlackSignatureError: If signature verification fails
    """
    # Find bot by app_id
    bot_info = bots_config.by_app_id(app_id)
    if not bot_info:
        raise MissingSlackSigningSecretError(f"No bot found with app_id: {app_id}")
    
    signing_secret = bot_info["signing_secret"]
    
    # Calculate the expected signature (this will raise errors for missing data)
    expected_signature = extract_slack_webhook_signature(headers, signing_secret, body, app_id)
    
    # Get the received signature from headers
    received_signature = headers.get("x-slack-signature")
    
    # Compare the signatures (this will raise InvalidSlackSignatureError if they don't match)
    return is_valid_webhook_signature(received_signature, expected_signature)