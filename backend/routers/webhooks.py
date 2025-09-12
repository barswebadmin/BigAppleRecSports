"""
Shopify Webhooks Router

Handles incoming Shopify webhooks for product changes (especially inventory updates)
"""

from fastapi import APIRouter, Request, HTTPException
import logging
from services.webhooks_service import WebhooksService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["shopify-webhooks"])

webhooks_service = WebhooksService()

@router.post("/shopify/product-update")
async def handle_product_webhook(request: Request):
    """Handle Shopify product webhooks asynchronously"""
    headers = dict(request.headers)
    body = await request.body()
    
    signature = headers.get("x-shopify-hmac-sha256", "")
    if not webhooks_service.verify_webhook_signature(body, signature):
        logger.error("Invalid webhook signature")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    result = webhooks_service.handle_shopify_webhook(headers, body)
    return {"success": True, "message": "Webhook received and processed"}
