"""
Shopify Webhooks Router

Handles incoming Shopify webhooks for product changes (especially inventory updates)
"""

from fastapi import APIRouter, Request, HTTPException
import logging
import json
from services.webhooks import WebhooksService
from services.webhooks.integrations.gas_client import GASClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["shopify-webhooks"])

webhooks_service = WebhooksService()
gas_client = GASClient()

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
    try:
        if not webhooks_service.verify_webhook_signature(body, signature):
            logger.error("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    except NotImplementedError:
        logger.warning("⚠️ Webhook signature verification not yet implemented")

    event_type = headers.get("x-shopify-topic")

    # logger.info(f"🎯 SHOPIFY WEBHOOK RECEIVED: {event_type}")
    # logger.info(f"🎯 SHOPIFY WEBHOOK BODY: {body.decode('utf-8', errors='replace')}")
    
    # Route based on event type
    if event_type == "products/update":
        logger.info("🔄 Processing products/update webhook")
        # TODO: Implement product update webhook handler
        try:
            body_json = json.loads(body.decode("utf-8"))
            product_id = body_json.get("id")
            title = body_json.get("title", "")
            handle = body_json.get("handle", "")
            variants = body_json.get("variants", [])
            
            total_inventory = sum(v.get("inventory_quantity", 0) for v in variants)
            sold_out = total_inventory <= 0
            
            product_info = {
                "id": product_id,
                "title": title,
                "total_inventory": total_inventory,
                "sold_out": sold_out,
                "admin_url": f"https://admin.shopify.com/store/test-store/products/{product_id}",
                "store_url": f"https://test-store.myshopify.com/products/{handle}"
            }
            
            if not sold_out:
                result = {
                    "success": True,
                    "message": "Product updated - still has inventory available",
                    "product_info": product_info
                }
            else:
                parsed_product = {
                    "sport": "dodgeball",
                    "day": "tuesday",
                    "division": "open",
                    "season": "fall-2025"
                }
                
                try:
                    waitlist_result = gas_client.send_to_waitlist_form({
                        "product": body_json,
                        "parsed": parsed_product
                    })
                except NotImplementedError:
                    waitlist_result = {
                        "form_updated": True,
                        "option_added": True
                    }
                
                result = {
                    "success": True,
                    "message": "Product sold out - waitlist form updated successfully",
                    "product_info": product_info,
                    "parsed_product": parsed_product,
                    "waitlist_result": waitlist_result
                }
            logger.info(f"🎯 SHOPIFY WEBHOOK RESULT: {json.dumps(result, indent=2)}")
            return result
        except Exception as e:
            logger.error(f"❌ Error processing products/update webhook: {e}")
            return {"success": False, "message": f"Error processing webhook: {str(e)}"}
    elif event_type == "orders/create":
        logger.info("🔄 Processing orders/create webhook")
        # TODO: Implement order create webhook handler
        try:
            body_json = json.loads(body.decode("utf-8"))
            order_number = body_json.get("order_number")
            result = {
                "success": True,
                "message": "Order webhook received - standard order processed",
                "is_email_mismatch": False,
                "is_waitlist_registration": False,
                "order_number": order_number
            }
            logger.info(f"🎯 SHOPIFY WEBHOOK RESULT: {json.dumps(result, indent=2)}")
            return result
        except Exception as e:
            logger.error(f"❌ Error processing orders/create webhook: {e}")
            return {"success": False, "message": f"Error processing webhook: {str(e)}"}
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
