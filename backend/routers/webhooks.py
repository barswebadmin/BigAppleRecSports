"""
Shopify Webhooks Router

Handles incoming Shopify webhooks for product changes (especially inventory updates)
"""

from fastapi import APIRouter, Request, HTTPException
import logging
import json
from services.webhooks import WebhooksService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["shopify-webhooks"])

webhooks_service = WebhooksService()

@router.get("/shopify/debug")
async def debug_webhook_secret():
    """Debug endpoint to check if webhook secret is loaded"""
    import os
    from dotenv import load_dotenv
    load_dotenv('../.env')
    
    secret = os.getenv("SHOPIFY_WEBHOOK_SECRET")
    return {
        "secret_loaded": bool(secret),
        "secret_length": len(secret) if secret else 0,
        "secret_preview": secret[:10] + "..." if secret else None
    }

@router.post("/shopify")
async def handle_shopify_webhook(request: Request):
    """Handle Shopify webhooks asynchronously - routes based on event type"""
    headers = dict(request.headers)
    body = await request.body()
    
    # Verify signature for all webhooks
    signature = headers.get("x-shopify-hmac-sha256", "")
    if not webhooks_service.verify_webhook_signature(body, signature):
        logger.error("Invalid webhook signature")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event_type = headers.get("x-shopify-topic")

    # logger.info(f"🎯 SHOPIFY WEBHOOK RECEIVED: {event_type}")
    # logger.info(f"🎯 SHOPIFY WEBHOOK BODY: {body.decode('utf-8', errors='replace')}")
    
    # Route based on event type
    if event_type == "products/update":
        logger.info("🔄 Processing products/update webhook through existing flow")
        result = webhooks_service.handle_shopify_webhook(headers, body)
        logger.info(f"🎯 SHOPIFY WEBHOOK RESULT: {json.dumps(result, indent=2)}")
        return result
    elif event_type == "orders/create":
        logger.info("🔄 Processing orders/create webhook through existing flow")
        result = webhooks_service.handle_shopify_webhook(headers, body)
        logger.info(f"🎯 SHOPIFY WEBHOOK RESULT: {json.dumps(result, indent=2)}")
        return result
    else:
        # Log the request body for other event types
        try:
            body_json = json.loads(body.decode("utf-8"))
            logger.info(f"📋 Unexpected webhook received:")
            logger.info(f"   Event Type: {event_type}")
            logger.info(f"   Request Body: {json.dumps(body_json, indent=2)}")
        except json.JSONDecodeError:
            logger.info(f"📋 Non-product-update webhook received (non-JSON body):")
            logger.info(f"   Event Type: {event_type}")
            logger.info(f"   Raw Body: {body.decode('utf-8', errors='replace')}")
        except Exception as e:
            logger.error(f"❌ Error processing webhook body: {e}")
            logger.info(f"   Event Type: {event_type}")
            logger.info(f"   Raw Body: {body}")
        
        return {
            "success": True, 
            "message": f"Webhook received and logged for event type: {event_type}",
            "event_type": event_type
        }
