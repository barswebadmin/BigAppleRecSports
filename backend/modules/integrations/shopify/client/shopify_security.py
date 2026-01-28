"""
Shopify Security Utilities

Provides HMAC-SHA256 verification for Shopify webhooks.
"""

import os
import hmac
import hashlib
import base64
import logging
from typing import Optional

from backend.config import config

logger = logging.getLogger(__name__)


class ShopifySecurity:
    def __init__(self):
        self.webhook_secret = config.shopify.webhook_secret
        self.env = config.environment

    def verify_shopify_webhook(self, body: bytes, signature: str) -> bool:
        """Verify Shopify webhook using base64(HMAC-SHA256(body, secret)).
        Temporary diagnostics are logged to help troubleshoot mismatches (masked).
        """
        try:
            secret = self.webhook_secret

            if not secret:
                if self.env != 'production':
                    logger.warning("Missing webhook secret - skipping verification in non-production")
                    return True
                logger.error("Missing webhook secret - rejecting request")
                return False

            if not signature:
                logger.warning("Missing webhook signature - rejecting request")
                return False

            expected = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).digest()
            try:
                received = base64.b64decode(signature)
            except Exception:
                logger.warning("Invalid webhook signature encoding - rejecting request")
                return False

            # TEMP DIAGNOSTIC (masked)
            try:
                exp_b64 = base64.b64encode(expected).decode("utf-8")
                masked_exp = f"{exp_b64[:4]}...{exp_b64[-4:]}"
                masked_sig = f"{signature[:4]}...{signature[-4:]}" if signature else "<none>"
                logger.info(
                    "Shopify HMAC verify: env=%s source=%s have_secret=%s secret_len=%s body_len=%s expected=%s provided=%s",
                    bool(secret),
                    len(secret or ""),
                    len(body or b""),
                    masked_exp,
                    masked_sig,
                )
            except Exception:
                pass

            return hmac.compare_digest(expected, received)

        except Exception as e:
            logger.error(f"Shopify webhook verification failed: {e}")
            return False


