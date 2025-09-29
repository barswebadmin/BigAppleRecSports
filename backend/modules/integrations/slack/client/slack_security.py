"""
Slack security and parsing methods.
Handles signature verification, button parsing, and text extraction from Slack blocks.
"""

import os
import hmac
import hashlib
import logging
import base64
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SlackSecurity:
    """Slack security and parsing methods"""

    def __init__(self, signing_secret: Optional[str] = None, bot: Optional[str] = None):
        self.signing_secret = signing_secret
        self.bot = bot

    def verify_slack_signature(self, body: bytes, timestamp: str, signature: str) -> bool:
        """Verify that the request came from Slack (v0=hex HMAC scheme)."""
        try:
            # Determine environment
            env = os.getenv("ENVIRONMENT", "dev").lower()
            is_prod = env == "production"

            # Resolve signing secret precedence:
            # 1) Explicitly provided to constructor
            secret = self.signing_secret

            # 2) For staging/production: use real bot secrets (per-bot),
            #    try specified bot if provided; otherwise try all known bots
            if not secret and env in ("staging", "production"):
                def _suffix_from_bot(name: str) -> str:
                    # Normalize to UPPER_SNAKE, alnum only with underscores
                    out = []
                    last_underscore = False
                    for ch in name:
                        if ch.isalnum():
                            out.append(ch.upper())
                            last_underscore = False
                        else:
                            if not last_underscore:
                                out.append('_')
                                last_underscore = True
                    suffix = ''.join(out).strip('_')
                    return suffix

                if self.bot:
                    suffix = _suffix_from_bot(self.bot)
                    if suffix:
                        secret = os.getenv(f"SLACK_SIGNING_SECRET_{suffix}")
                else:
                    # Try any env var that looks like a Slack signing secret
                    for key, val in os.environ.items():
                        if key.startswith("SLACK_SIGNING_SECRET_") and val:
                            if self._verify_slack_signature_with_secret(val, body, timestamp, signature):
                                return True

            # 3) For test env: use a common test signing secret if available, otherwise a default
            if not secret and env == "test":
                secret = os.getenv("SLACK_TEST_SIGNING_SECRET", "test_signing_secret_123456")

            # 4) For dev env: allow missing secret (skip verification)
            if not secret and env == "dev":
                logger.warning("Missing Slack signing secret - skipping verification in dev")
                return True

            if not secret:
                logger.error("Missing Slack signing secret - rejecting request")
                return False

            if not signature:
                logger.warning("Missing webhook signature - rejecting request")
                return False

            # Slack style: signature like 'v0=hex'
            return self._verify_slack_signature_with_secret(secret, body, timestamp, signature)

        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return False

    def _verify_slack_signature_with_secret(self, secret: str, body: bytes, timestamp: str, signature: str) -> bool:
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
        expected_hex = hmac.new(secret.encode(), sig_basestring.encode(), hashlib.sha256).hexdigest()
        expected_slack = f"v0={expected_hex}"
        return hmac.compare_digest(expected_slack, signature)

    def parse_button_value(self, value: str) -> Dict[str, str]:
        """Parse button value like 'rawOrderNumber=#12345|orderId=gid://shopify/Order/12345|refundAmount=36.00'"""
        request_data = {}
        button_values = value.split("|")

        for button_value in button_values:
            if "=" in button_value:
                key, val = button_value.split("=", 1)  # Split only on first =
                request_data[key] = val

        return request_data

    def extract_text_from_blocks(self, blocks: list) -> str:
        """Extract text content from Slack blocks structure"""
        try:
            text_parts = []

            for block in blocks:
                if not isinstance(block, dict):
                    continue

                block_type = block.get("type", "")

                # Extract text from section blocks
                if block_type == "section":
                    text_obj = block.get("text", {})
                    if isinstance(text_obj, dict) and "text" in text_obj:
                        text_parts.append(text_obj["text"])

                # Extract text from context blocks
                elif block_type == "context":
                    elements = block.get("elements", [])
                    for element in elements:
                        if isinstance(element, dict) and "text" in element:
                            text_parts.append(element["text"])

                # Extract text from rich_text blocks
                elif block_type == "rich_text":
                    elements = block.get("elements", [])
                    for element in elements:
                        if isinstance(element, dict):
                            if element.get("type") == "rich_text_section":
                                sub_elements = element.get("elements", [])
                                for sub_element in sub_elements:
                                    if (
                                        isinstance(sub_element, dict)
                                        and "text" in sub_element
                                    ):
                                        text_parts.append(sub_element["text"])

            return "\n".join(text_parts)

        except Exception as e:
            logger.warning(f"Failed to extract text from blocks: {e}")
            return "Message content"
