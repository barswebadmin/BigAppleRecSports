"""
Webhook Signature Verification

Handles HMAC-SHA256 signature verification for webhook security.
"""

import hmac
import hashlib
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SignatureVerifier:
    """Handles webhook signature verification for security"""
    
    def __init__(self, webhook_secret: Optional[str]):
        self.webhook_secret = webhook_secret
    
    def verify(self, body: bytes, signature: str) -> bool:
        """Verify webhook signature using HMAC-SHA256"""
        if not self.webhook_secret:
            logger.error("Missing webhook secret - rejecting request")
            return False
            
        if not signature:
            logger.warning("Missing webhook signature - rejecting request") 
            return False
            
        try:
            expected = hmac.new(
                self.webhook_secret.encode('utf-8'),
                body,
                hashlib.sha256
            ).digest()
            
            received = base64.b64decode(signature)
            return hmac.compare_digest(expected, received)
            
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return False
