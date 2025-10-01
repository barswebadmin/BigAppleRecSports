"""
Unified webhook signature verification for all services.
Handles signature verification for Slack, Shopify, and other webhook sources.
"""

import os
import hmac
import hashlib
import base64
import logging
from typing import Optional
from config import config
from config.slack import SlackBot
from ..signature_verification import SignatureFormat, verify_hmac_signature

logger = logging.getLogger(__name__)


def verify_webhook_signature(
    source: str,
    body: bytes,
    headers: dict,
    webhook_secret: Optional[str] = None,
    bot: Optional[SlackBot] = None
) -> bool:
    """
    Unified webhook signature verification for all services.
    
    Args:
        source: The webhook source ("slack", "shopify", etc.)
        body: Raw request body bytes
        headers: Request headers dict
        webhook_secret: Optional explicit webhook secret
        bot: Optional Slack bot configuration
        
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Skip verification in dev/test environments
        env = config.environment
        if "dev" in env or "test" in env:
            logger.info(f"Skipping signature verification in {env} environment")
            return True
        
        # Get the signing secret
        if webhook_secret:
            secret = webhook_secret
        else:
            secret = get_signing_secret(source, bot)
        
        if not secret:
            logger.error(f"Cannot resolve signing secret for source: {source}")
            return False
        
        # Extract signature and timestamp from headers
        signature_data = extract_signature_from_headers(source, headers)
        if not signature_data:
            logger.warning(f"Missing or invalid signature headers for {source}")
            return False
        
        signature = signature_data["signature"]
        timestamp = signature_data.get("timestamp")
        
        # Generate expected signature based on source
        if source == "slack":
            if not timestamp:
                logger.error("Timestamp is required for Slack signature verification")
                return False
            
            # Slack signature format: v0:{timestamp}:{body}
            sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
            expected_hex = hmac.new(secret.encode(), sig_basestring.encode(), hashlib.sha256).hexdigest()
            expected_signature = f"v0={expected_hex}"
            signature_format = SignatureFormat.HEX_WITH_PREFIX
            
        elif source == "shopify":
            # Shopify signature format: base64(hmac_digest)
            expected_digest = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).digest()
            expected_signature = base64.b64encode(expected_digest).decode('utf-8')
            signature_format = SignatureFormat.BASE64
            
            # Diagnostic logging for Shopify (masked)
            try:
                masked_exp = f"{expected_signature[:4]}...{expected_signature[-4:]}"
                masked_sig = f"{signature[:4]}...{signature[-4:]}" if signature else "<none>"
                logger.info(
                    f"Shopify HMAC verify: env={env} have_secret={bool(secret)} "
                    f"secret_len={len(secret)} body_len={len(body)} "
                    f"expected={masked_exp} provided={masked_sig}"
                )
            except Exception:
                pass
                
        else:
            logger.error(f"Unsupported webhook source: {source}")
            return False
        
        # Use shared signature verification utility
        return verify_hmac_signature(expected_signature, signature, signature_format)
        
    except Exception as e:
        logger.error(f"Webhook signature verification failed for {source}: {e}")
        return False


def extract_signature_from_headers(source: str, headers: dict) -> Optional[dict]:
    """
    Extract signature and timestamp from request headers based on source.
    
    Args:
        source: The webhook source ("slack", "shopify", etc.)
        headers: Request headers dict (case-insensitive)
        
    Returns:
        Dict with "signature" and optionally "timestamp", or None if missing
    """
    # Normalize headers to lowercase for case-insensitive lookup
    normalized_headers = {k.lower(): v for k, v in headers.items()}
    
    if source == "slack":
        signature = normalized_headers.get("x-slack-signature")
        timestamp = normalized_headers.get("x-slack-request-timestamp")
        
        if not signature or not timestamp:
            return None
            
        return {
            "signature": signature,
            "timestamp": timestamp
        }
        
    elif source == "shopify":
        signature = normalized_headers.get("x-shopify-hmac-sha256")
        
        if not signature:
            return None
            
        return {
            "signature": signature
        }
        
    else:
        logger.warning(f"Unknown webhook source for signature extraction: {source}")
        return None


def get_signing_secret(source: str, bot: Optional[SlackBot] = None) -> Optional[str]:
    """Get the signing secret for a given source and bot."""
    try:
        if source == "slack":
            # Try bot-specific secret first
            if bot:
                bot_config = getattr(config.Slack, bot, None)
                if bot_config and hasattr(bot_config, 'signing_secret'):
                    return bot_config.signing_secret
            
            # Fallback to general Slack signing secret
            if hasattr(config.Slack, 'signing_secret'):
                return config.Slack.signing_secret
            
            # Environment variable fallback
            return os.getenv("SLACK_SIGNING_SECRET")
            
        elif source == "shopify":
            # Try config first
            if hasattr(config.Shopify, 'webhook_secret'):
                return config.Shopify.webhook_secret
            
            # Environment variable fallback
            return os.getenv("SHOPIFY_SECRET_WEBHOOK")
            
        else:
            logger.warning(f"Unknown webhook source: {source}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting signing secret for {source}: {e}")
        return None
