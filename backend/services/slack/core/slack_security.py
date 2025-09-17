"""
Slack security and parsing methods.
Handles signature verification, button parsing, and text extraction from Slack blocks.
"""

import hmac
import hashlib
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SlackSecurity:
    """Slack security and parsing methods"""

    def __init__(self, signing_secret: Optional[str] = None):
        self.signing_secret = signing_secret

    def verify_slack_signature(self, body: bytes, timestamp: str, signature: str) -> bool:
        """Verify that the request came from Slack"""
        if not self.signing_secret:
            logger.warning(
                "No Slack signing secret configured - skipping signature verification"
            )
            return True  # Skip verification in development

        # Create the signature base string
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"

        # Create the expected signature
        expected_signature = (
            "v0="
            + hmac.new(
                self.signing_secret.encode(),
                sig_basestring.encode(),
                hashlib.sha256,
            ).hexdigest()
        )

        # Compare signatures
        return hmac.compare_digest(expected_signature, signature)

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
