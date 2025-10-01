"""
Slack security and parsing methods.
Handles signature verification, button parsing, and text extraction from Slack blocks.
"""

import logging
from typing import Dict, Any, Optional
from config.slack import SlackBot
from shared.security import verify_webhook_signature

logger = logging.getLogger(__name__)


# Wrapper function removed - use verify_webhook_signature directly from shared.security