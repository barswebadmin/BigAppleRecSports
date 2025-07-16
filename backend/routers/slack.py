from fastapi import APIRouter, HTTPException, Request, Form
from typing import Dict, Any, Optional, List
import logging
import json

from services.orders import OrdersService
from services.slack import SlackService
from services.shopify_service import ShopifyService
from config import settings
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/slack", tags=["slack"])

orders_service = OrdersService()
slack_service = SlackService()
shopify_service = ShopifyService()

@router.post("/webhook")
async def handle_slack_webhook(request: Request):
    """Handle Slack webhook URL verification"""
    try:
        body = await request.json()
        
        # Handle URL verification challenge
        if body.get("type") == "url_verification":
            return {"challenge": body.get("challenge")}
        
        return {"text": "Webhook received"}
    
    except Exception as e:
        logger.error(f"Error handling Slack webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/interactive")
async def handle_interactive(request: Request):
    """Handle Slack interactive components"""
    return await slack_service.handle_slack_interactions(request)

@router.get("/health")
async def health_check():
    """Health check endpoint for the Slack service"""
    return {"status": "healthy", "service": "slack"}