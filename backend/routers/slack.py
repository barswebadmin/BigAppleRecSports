from fastapi import APIRouter, HTTPException, Request, Form
from typing import Dict, Any, Optional
import logging
import json
import hmac
import hashlib
from services.orders import OrdersService
from services.slack import SlackService
from config import settings
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/slack", tags=["slack"])

orders_service = OrdersService()
slack_service = SlackService()

def verify_slack_signature(body: bytes, timestamp: str, signature: str) -> bool:
    """Verify that the request came from Slack"""
    if not settings.slack_signing_secret:
        logger.warning("No Slack signing secret configured - skipping signature verification")
        return True  # Skip verification in development
    
    # Create the signature base string
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    
    # Create the expected signature
    expected_signature = 'v0=' + hmac.new(
        settings.slack_signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures
    return hmac.compare_digest(expected_signature, signature)

def parse_button_value(value: str) -> Dict[str, str]:
    """Parse button value like 'rawOrderNumber=#12345|orderId=gid://shopify/Order/12345|refundAmount=36.00'"""
    request_data = {}
    button_values = value.split('|')
    
    for button_value in button_values:
        if '=' in button_value:
            key, val = button_value.split('=', 1)  # Split only on first =
            request_data[key] = val
    
    return request_data

@router.post("/interactions")
async def handle_slack_interactions(request: Request):
    """
    Handle Slack button interactions and other interactive components - DEBUG VERSION
    This endpoint receives webhooks when users click buttons in Slack messages
    """
    try:
        # Get raw request data
        body = await request.body()
        
        # Get headers for verification
        timestamp = request.headers.get("X-Slack-Request-Timestamp")
        signature = request.headers.get("X-Slack-Signature")
        content_type = request.headers.get("Content-Type")
        
        print(f"\n🔍 === SLACK WEBHOOK DEBUG ===")
        print(f"📋 Headers:")
        print(f"   X-Slack-Request-Timestamp: {timestamp}")
        print(f"   X-Slack-Signature: {signature}")
        print(f"   Content-Type: {content_type}")
        print(f"   User-Agent: {request.headers.get('User-Agent', 'Not provided')}")
        
        print(f"📦 Raw Body ({len(body)} bytes):")
        body_str = body.decode('utf-8', errors='replace')
        print(f"   {body_str}")
        
        # Verify signature if present
        if timestamp and signature:
            signature_valid = verify_slack_signature(body, timestamp, signature)
            print(f"🔐 Signature Valid: {signature_valid}")
            if not signature_valid:
                print("❌ SIGNATURE VERIFICATION FAILED - but continuing for debug...")
        else:
            print("⚠️  No signature headers provided")
        
        # Parse form data (Slack sends as application/x-www-form-urlencoded)
        try:
            form_data = await request.form()
            payload_str = form_data.get("payload")
            
            if payload_str:
                print(f"📝 Form payload found:")
                print(f"   {payload_str}")
                
                # Parse JSON payload
                payload = json.loads(str(payload_str))
                print(f"✅ Parsed JSON successfully!")
                print(f"   Type: {payload.get('type', 'Not specified')}")
                print(f"   Keys: {list(payload.keys())}")
                
                # Show user info
                user_info = payload.get("user", {})
                print(f"👤 User: {user_info.get('name', 'Unknown')} (ID: {user_info.get('id', 'Unknown')})")
                
                # Show action info if it's a button click
                if payload.get("type") == "block_actions":
                    actions = payload.get("actions", [])
                    if actions:
                        action = actions[0]
                        print(f"🔘 Action:")
                        print(f"   Action ID: {action.get('action_id', 'Not specified')}")
                        print(f"   Value: {action.get('value', 'Not specified')}")
                        print(f"   Text: {action.get('text', {}).get('text', 'Not specified')}")
                
            else:
                print("❌ No 'payload' found in form data")
                print(f"   Form keys: {list(form_data.keys())}")
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error: {e}")
        except Exception as e:
            print(f"❌ Form Parse Error: {e}")
        
        print("=== END DEBUG ===\n")
        
        # Return success response to Slack
        return {"text": "✅ Webhook received and logged successfully!"}
        
        # TODO: Uncomment and update the below when ready to process actions
        #
        # action_id = action.get("action_id")
        # action_value = action.get("value", "")
        # 
        # # Parse button data
        # request_data = parse_button_value(action_value)
        # 
        # # Get message info for updating
        # thread_ts = payload.get("message", {}).get("ts")
        # channel_id = payload.get("channel", {}).get("id")
        # 
        # logger.info(f"Button clicked: {action_id} with data: {request_data}")
        # 
        # # Route to appropriate handler
        # if action_id == "approve_refund":
        #     return await handle_approve_refund(request_data, channel_id, thread_ts, slack_user_name)
        # elif action_id == "refund_different_amount":
        #     return await handle_custom_amount_request(request_data, channel_id, thread_ts, slack_user_name)
        # elif action_id == "cancel_refund_request":
        #     return await handle_cancel_request(request_data, channel_id, thread_ts, slack_user_name)
        # elif action_id.startswith("restock"):
        #     return await handle_restock_inventory(request_data, action_id, channel_id, thread_ts, slack_user_name)
        # else:
        #     logger.warning(f"Unknown action_id: {action_id}")
        #     return {"response_type": "ephemeral", "text": f"Unknown action: {action_id}"}
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON payload: {e}")
        print(f"❌ JSON Decode Error: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    except Exception as e:
        logger.error(f"Error handling Slack interaction: {e}")
        print(f"❌ General Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")

async def handle_approve_refund(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str) -> Dict[str, Any]:
    """
    Handle the approve refund button click - equivalent to approveRefundRequest() in Google Apps Script
    """
    try:
        raw_order_number = request_data.get("rawOrderNumber", "")
        order_id = request_data.get("orderId", "")
        refund_amount = float(request_data.get("refundAmount", "0"))
        
        logger.info(f"Processing refund approval for order {raw_order_number}, amount ${refund_amount}")
        
        # 1. Fetch order details from Shopify
        order_result = orders_service.fetch_order_details(order_name=raw_order_number)
        if not order_result["success"]:
            raise Exception(f"Failed to fetch order: {order_result['message']}")
        
        order_data = order_result["data"]
        
        # 2. Determine refund type from original calculation (would need to be stored or re-calculated)
        # For now, default to "refund" - you might want to store this in the button value
        refund_type = "refund"  # Could be extracted from button data or re-calculated
        
        # 3. Cancel the order and create refund/credit
        cancel_result = orders_service.cancel_order_with_refund(
            order_id=order_id,
            refund_amount=refund_amount,
            should_restock=False,  # We'll handle restocking separately with buttons
            send_slack_notification=False  # We're updating the message manually
        )
        
        if not cancel_result["success"]:
            raise Exception(f"Failed to process refund: {cancel_result['message']}")
        
        # 4. Build success message with restock buttons
        success_message = build_refund_success_message(
            order_data=order_data,
            refund_amount=refund_amount,
            refund_type=refund_type,
            slack_user_name=slack_user_name,
            raw_order_number=raw_order_number
        )
        
        # 5. Update the Slack message
        update_result = slack_service.api_client.update_message(
            message_ts=thread_ts,
            message_text=success_message["text"],
            action_buttons=success_message.get("action_buttons", [])
        )
        
        if not update_result["success"]:
            logger.error(f"Failed to update Slack message: {update_result}")
        
        logger.info(f"Refund processed successfully for order {raw_order_number}")
        return {}
    
    except Exception as e:
        logger.error(f"Error processing refund approval: {str(e)}")
        
        # Send error message to Slack
        error_message = f"❌ Error processing refund: {str(e)}"
        slack_service.api_client.update_message(
            message_ts=thread_ts,
            message_text=error_message
        )
        
        return {}

async def handle_custom_amount_request(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str) -> Dict[str, Any]:
    """Handle custom refund amount button click"""
    # Update message to indicate custom amount processing
    message = f"🔄 *Custom refund amount requested by {slack_user_name}*\n\nPlease process manually in Shopify admin."
    
    slack_service.api_client.update_message(
        message_ts=thread_ts,
        message_text=message
    )
    
    return {}

async def handle_cancel_request(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str) -> Dict[str, Any]:
    """Handle cancel request button click"""
    raw_order_number = request_data.get("rawOrderNumber", "")
    
    # Update message to show cancellation
    message = f"❌ *Refund request for Order {raw_order_number} cancelled by {slack_user_name}*"
    
    slack_service.api_client.update_message(
        message_ts=thread_ts,
        message_text=message,
        action_buttons=[]  # Remove all buttons
    )
    
    return {}

async def handle_restock_inventory(request_data: Dict[str, str], action_id: str, channel_id: str, thread_ts: str, slack_user_name: str) -> Dict[str, Any]:
    """Handle inventory restocking button clicks"""
    order_id = request_data.get("orderId", "")
    
    # Extract variant info from action_id (would need to be encoded in button)
    # For now, just update message
    message = f"📦 *Inventory restocking initiated by {slack_user_name}*\n\nProcessing..."
    
    slack_service.api_client.update_message(
        message_ts=thread_ts,
        message_text=message
    )
    
    return {}

def build_refund_success_message(order_data: Dict[str, Any], refund_amount: float, refund_type: str, 
                                slack_user_name: str, raw_order_number: str) -> Dict[str, Any]:
    """Build the success message after refund processing"""
    
    # Get product info
    product = order_data.get("product", {})
    customer = order_data.get("customer", {})
    product_title = product.get("title", "Unknown Product")
    customer_name = f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip()
    
    # Build order URL
    order_id = order_data.get("orderId", "")
    order_url = f"<https://admin.shopify.com/store/09fe59-3/orders/{order_id.split('/')[-1]}|{raw_order_number}>" if order_id else raw_order_number
    
    # Main success text
    success_text = f"✅ *Request to provide a ${refund_amount:.2f} {refund_type} for Order {order_url} for {customer_name} has been processed by {slack_user_name}*\n\n"
    
    # Add product and inventory info
    success_text += f"📦 *Product:* {product_title}\n\n"
    success_text += "*Restock Inventory?*"
    
    # Create restock buttons (simplified for now)
    restock_buttons = [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "📦 Restock Inventory"},
            "action_id": "restock_inventory",
            "value": f"orderId={order_id}|rawOrderNumber={raw_order_number}",
            "style": "primary"
        }
    ]
    
    return {
        "text": success_text,
        "action_buttons": restock_buttons
    }

@router.get("/health")
async def health_check():
    """Health check endpoint for the Slack service"""
    return {"status": "healthy", "service": "slack"} 