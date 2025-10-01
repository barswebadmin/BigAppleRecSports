"""
Shopify Webhooks Router

Handles incoming Shopify webhooks for product changes (especially inventory updates)
"""

from fastapi import APIRouter, Request, HTTPException
import logging
import json
# WebhooksService not yet implemented in new architecture
# from modules.integrations.webhooks import WebhooksService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["shopify-webhooks"])

# webhooks_service = WebhooksService()  # TODO: Implement WebhooksService in new architecture

@router.post("/shopify")
async def handle_shopify_webhook(request: Request):
    """Handle Shopify webhooks asynchronously - routes based on event type"""
    headers = dict(request.headers)
    body = await request.body()
    # logger.info(f"🎯 SHOPIFY WEBHOOK headers: {headers}")
    try:
        parsed = json.loads(body.decode('utf-8'))
        logger.info("🎯 SHOPIFY WEBHOOK BODY:\n%s", json.dumps(parsed, indent=2, ensure_ascii=False))
    except Exception:
        logger.info("🎯 SHOPIFY WEBHOOK BODY (raw): %s", body.decode('utf-8', errors='replace'))
    
    # Verify signature for all webhooks
    signature = headers.get("x-shopify-hmac-sha256", "")
    # TODO: Implement webhook signature verification
    # if not webhooks_service.verify_webhook_signature(body, signature):
    #     logger.error("Invalid webhook signature")
    #     raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event_type = headers.get("x-shopify-topic")

    # logger.info(f"🎯 SHOPIFY WEBHOOK RECEIVED: {event_type}")
    # logger.info(f"🎯 SHOPIFY WEBHOOK BODY: {body.decode('utf-8', errors='replace')}")
    
    # Route based on event type
    if event_type == "products/update":
        logger.info("🔄 Processing products/update webhook")
        # TODO: Implement product update webhook handler
        result = {"status": "not_implemented", "message": "WebhooksService not yet implemented"}
        logger.info(f"🎯 SHOPIFY WEBHOOK RESULT: {json.dumps(result, indent=2)}")
        return result
    elif event_type == "orders/create":
        logger.info("🔄 Processing orders/create webhook")
        # TODO: Implement order create webhook handler
        result = {"status": "not_implemented", "message": "WebhooksService not yet implemented"}
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
