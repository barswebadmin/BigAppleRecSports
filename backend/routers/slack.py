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

# Note: parse_original_message_data function removed - data now preserved in button values

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
        
        # Process button actions
        if payload.get("type") == "block_actions":
            actions = payload.get("actions", [])
            if actions:
                action = actions[0]
                action_id = action.get("action_id")
                action_value = action.get("value", "")
                slack_user_id = payload.get("user", {}).get("id", "Unknown")
                slack_user_name = payload.get("user", {}).get("name", "Unknown")
                
                # Parse button data
                request_data = parse_button_value(action_value)
                
                # Get message info for updating
                thread_ts = payload.get("message", {}).get("ts")
                channel_id = payload.get("channel", {}).get("id")
                
                # Note: Button values now contain all necessary preserved data
                
                logger.info(f"Button clicked: {action_id} with data: {request_data}")
                
                # Route to appropriate handler - NEW DECOUPLED FLOW
                if action_id == "cancel_order":
                    return await handle_cancel_order(request_data, channel_id, thread_ts, slack_user_id, slack_user_name, {})
                elif action_id == "proceed_without_cancel":
                    return await handle_proceed_without_cancel(request_data, channel_id, thread_ts, slack_user_id, slack_user_name, {})
                # elif action_id == "cancel_and_close_request":
                #     return await handle_cancel_and_close_request(request_data, channel_id, thread_ts, slack_user_name)
                # elif action_id == "process_refund":
                #     return await handle_process_refund(request_data, channel_id, thread_ts, slack_user_name)
                # elif action_id == "custom_refund_amount":
                #     return await handle_custom_refund_amount(request_data, channel_id, thread_ts, slack_user_name)
                # elif action_id == "no_refund":
                #     return await handle_no_refund(request_data, channel_id, thread_ts, slack_user_name)
                # elif action_id.startswith("restock"):
                #     return await handle_restock_inventory(request_data, action_id, channel_id, thread_ts, slack_user_name)
                else:
                    logger.warning(f"Unknown action_id: {action_id}")
                    return {"response_type": "ephemeral", "text": f"Unknown action: {action_id}"}
        
        # Return success response to Slack
        return {"text": "✅ Webhook received and logged successfully!"}
    
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

# === STEP 1 HANDLERS: INITIAL DECISION (Cancel Order / Proceed / Cancel & Close) ===

async def handle_cancel_order(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_id: str, slack_user_name: str, original_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle cancel order button click (Step 1)
    Cancels the order in Shopify, then shows refund options
    """
    print(f"\n✅ === CANCEL ORDER ACTION ===")
    print(f"👤 User: {slack_user_name}")
    print(f"📋 Request Data: {request_data}")
    print(f"📍 Channel: {channel_id}, Thread: {thread_ts}")
    print("=== END CANCEL ORDER ===\n")
    
    try:
        # Extract data from button value
        raw_order_number = request_data.get("rawOrderNumber", "")
        refund_type = request_data.get("refundType", "refund")
        requestor_email = request_data.get("requestorEmail", "unknown@example.com")
        requestor_first_name = request_data.get("requestorFirstName", "")
        requestor_last_name = request_data.get("requestorLastName", "")
        request_submitted_at = request_data.get("requestSubmittedAt", "")
        
        logger.info(f"Canceling order: {raw_order_number}")
        
        # 1. Fetch fresh order details from Shopify to get complete data
        order_result = orders_service.fetch_order_details(order_name=raw_order_number)
        if not order_result["success"]:
            logger.error(f"Failed to fetch order details for {raw_order_number}: {order_result['message']}")
            error_message = f"❌ Failed to fetch order details: {order_result['message']}"
            slack_service.api_client.update_message(message_ts=thread_ts, message_text=error_message)
            return {}
        
        shopify_order_data = order_result["data"]
        order_id = shopify_order_data.get("orderId", "")
        
        # 2. Calculate fresh refund amount
        refund_calculation = orders_service.calculate_refund_due(shopify_order_data, refund_type)
        
        # 3. Cancel order in Shopify
        cancel_result = orders_service.cancel_order(order_id)
        
        if cancel_result["success"]:
            # 4. Create requestor name display
            requestor_name_display = f"{requestor_first_name} {requestor_last_name}".strip()
            if not requestor_name_display:
                requestor_name_display = "Unknown User"
            
            # Create order data with fresh Shopify data and preserved requestor info
            order_data = {
                "order": shopify_order_data,  # Use fresh Shopify order data
                "refund_calculation": refund_calculation,  # Use fresh refund calculation
                "requestor_name": {"display": requestor_name_display},
                "requestor_email": requestor_email,
                "original_data": {
                    "original_timestamp": request_submitted_at,  # Preserve original timestamp
                    "requestor_name_display": requestor_name_display,
                    "requestor_email": requestor_email
                }
            }
            
            # 5. Create refund decision message
            from services.slack.message_builder import SlackMessageBuilder
            message_builder = SlackMessageBuilder({})
            refund_message = message_builder.create_refund_decision_message(
                order_data, refund_type, "@channel", 
                order_cancelled=True, 
                slack_user=f"<@{slack_user_id}>",
                original_timestamp=request_submitted_at
            )
            
            # 4. Update Slack message
            slack_service.api_client.update_message(
                message_ts=thread_ts,
                message_text=refund_message["text"],
                action_buttons=refund_message["action_buttons"]
            )
            
            logger.info(f"Order {raw_order_number} cancelled successfully")
        else:
            error_message = f"❌ Failed to cancel order {raw_order_number}: {cancel_result.get('message', 'Unknown error')}"
            slack_service.api_client.update_message(message_ts=thread_ts, message_text=error_message)
        
        return {}
    except Exception as e:
        logger.error(f"Error canceling order: {e}")
        error_message = f"❌ Error canceling order: {str(e)}"
        slack_service.api_client.update_message(message_ts=thread_ts, message_text=error_message)
        return {}
    

async def handle_proceed_without_cancel(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_id: str, slack_user_name: str, original_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle proceed without cancel button click (Step 1)
    Shows refund options without canceling the order
    """
    print(f"\n➡️ === PROCEED WITHOUT CANCEL ACTION ===")
    print(f"👤 User: {slack_user_name}")
    print(f"📋 Request Data: {request_data}")
    print(f"📍 Channel: {channel_id}, Thread: {thread_ts}")
    print("=== END PROCEED WITHOUT CANCEL ===\n")
    
    try:
        # Extract data from button value
        raw_order_number = request_data.get("rawOrderNumber", "")
        refund_type = request_data.get("refundType", "refund")
        requestor_email = request_data.get("requestorEmail", "unknown@example.com")
        requestor_first_name = request_data.get("requestorFirstName", "")
        requestor_last_name = request_data.get("requestorLastName", "")
        request_submitted_at = request_data.get("requestSubmittedAt", "")
        
        logger.info(f"Proceeding without canceling order: {raw_order_number}")
        
        # 1. Fetch fresh order details from Shopify to get complete data
        order_result = orders_service.fetch_order_details(order_name=raw_order_number)
        if not order_result["success"]:
            logger.error(f"Failed to fetch order details for {raw_order_number}: {order_result['message']}")
            error_message = f"❌ Failed to fetch order details: {order_result['message']}"
            slack_service.api_client.update_message(message_ts=thread_ts, message_text=error_message)
            return {}
        
        shopify_order_data = order_result["data"]
        
        # 2. Calculate fresh refund amount
        refund_calculation = orders_service.calculate_refund_due(shopify_order_data, refund_type)
        
        # 3. Create requestor name display
        requestor_name_display = f"{requestor_first_name} {requestor_last_name}".strip()
        if not requestor_name_display:
            requestor_name_display = "Unknown User"
        
        # Create order data with fresh Shopify data and preserved requestor info
        order_data = {
            "order": shopify_order_data,  # Use fresh Shopify order data
            "refund_calculation": refund_calculation,  # Use fresh refund calculation
            "requestor_name": {"display": requestor_name_display},
            "requestor_email": requestor_email,
            "original_data": {
                "original_timestamp": request_submitted_at,  # Preserve original timestamp
                "requestor_name_display": requestor_name_display,
                "requestor_email": requestor_email
            }
        }
        
        # 4. Create refund decision message (order remains active)
        from services.slack.message_builder import SlackMessageBuilder
        message_builder = SlackMessageBuilder({})
        refund_message = message_builder.create_refund_decision_message(
            order_data, refund_type, "@channel", 
            order_cancelled=False, 
            slack_user=f"<@{slack_user_id}>",
            original_timestamp=request_submitted_at
        )
        
        # 4. Update Slack message
        slack_service.api_client.update_message(
            message_ts=thread_ts,
            message_text=refund_message["text"],
            action_buttons=refund_message["action_buttons"]
        )
        
        logger.info(f"Proceeding to refund options for order {raw_order_number} (order not cancelled)")
        return {}
    except Exception as e:
        logger.error(f"Error proceeding without cancel: {e}")
        error_message = f"❌ Error proceeding: {str(e)}"
        slack_service.api_client.update_message(message_ts=thread_ts, message_text=error_message)
        return {}

async def handle_cancel_and_close_request(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str) -> Dict[str, Any]:
    """
    Handle cancel and close request button click (Step 1)
    Same as the old logic - cancel order and close request
    """
    print(f"\n❌ === CANCEL AND CLOSE REQUEST ACTION ===")
    print(f"👤 User: {slack_user_name}")
    print(f"📋 Request Data: {request_data}")
    print(f"📍 Channel: {channel_id}, Thread: {thread_ts}")
    print("=== END CANCEL AND CLOSE ===\n")
    
    # TODO: Uncomment when ready to implement (this is the same as old cancel logic)
    # try:
    #     raw_order_number = request_data.get("rawOrderNumber", "")
    #     
    #     logger.info(f"Canceling and closing request for order: {raw_order_number}")
    #     
    #     # Cancel order and close request (same as old logic)
    #     message = f"❌ *Request cancelled and closed by {slack_user_name}*\\n\\nOrder {raw_order_number} request has been cancelled."
    #     
    #     slack_service.api_client.update_message(
    #         message_ts=thread_ts,
    #         message_text=message,
    #         action_buttons=[]
    #     )
    #     
    #     logger.info(f"Request cancelled and closed for order {raw_order_number}")
    #     return {}
    # except Exception as e:
    #     logger.error(f"Error canceling and closing request: {e}")
    #     error_message = f"❌ Error: {str(e)}"
    #     slack_service.api_client.update_message(message_ts=thread_ts, message_text=error_message)
    #     return {}
    
    return {"text": "✅ Cancel and close request action received and logged!"}

# === STEP 2 HANDLERS: REFUND DECISION (Process / Custom / No Refund) ===

async def handle_process_refund(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str) -> Dict[str, Any]:
    """
    Handle process calculated refund button click (Step 2)
    """
    print(f"\n✅ === PROCESS REFUND ACTION ===")
    print(f"👤 User: {slack_user_name}")
    print(f"📋 Request Data: {request_data}")
    print(f"📍 Channel: {channel_id}, Thread: {thread_ts}")
    print("=== END PROCESS REFUND ===\n")
    
    # TODO: Uncomment when ready to implement
    # try:
    #     order_id = request_data.get("orderId", "")
    #     raw_order_number = request_data.get("rawOrderNumber", "")
    #     refund_amount = float(request_data.get("refundAmount", "0"))
    #     refund_type = request_data.get("refundType", "refund")
    #     order_cancelled = request_data.get("orderCancelled", "False").lower() == "true"
    #     
    #     logger.info(f"Processing refund: Order {raw_order_number}, Amount: ${refund_amount}")
    #     
    #     # Process refund (create refund/store credit)
    #     refund_result = orders_service.process_refund(order_id, refund_amount, refund_type)
    #     
    #     if refund_result["success"]:
    #         status = "cancelled" if order_cancelled else "active"
    #         message = f"✅ *Refund processed by {slack_user_name}*\\n\\nOrder {raw_order_number} ({status}) - ${refund_amount:.2f} {refund_type} processed successfully."
    #     else:
    #         message = f"❌ *Refund failed*\\n\\nError: {refund_result.get('message', 'Unknown error')}"
    #     
    #     slack_service.api_client.update_message(
    #         message_ts=thread_ts,
    #         message_text=message,
    #         action_buttons=[]
    #     )
    #     
    #     return {}
    # except Exception as e:
    #     logger.error(f"Error processing refund: {e}")
    #     error_message = f"❌ Error processing refund: {str(e)}"
    #     slack_service.api_client.update_message(message_ts=thread_ts, message_text=error_message)
    #     return {}
    
    return {"text": "✅ Process refund action received and logged!"}

async def handle_custom_refund_amount(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str) -> Dict[str, Any]:
    """
    Handle custom refund amount button click (Step 2)
    """
    print(f"\n✏️ === CUSTOM REFUND AMOUNT ACTION ===")
    print(f"👤 User: {slack_user_name}")
    print(f"📋 Request Data: {request_data}")
    print(f"📍 Channel: {channel_id}, Thread: {thread_ts}")
    print("=== END CUSTOM REFUND AMOUNT ===\n")
    
    # TODO: Uncomment when ready to implement
    # try:
    #     raw_order_number = request_data.get("rawOrderNumber", "")
    #     
    #     message = f"✏️ *Custom refund amount requested by {slack_user_name}*\\n\\nOrder {raw_order_number} - Please process manually in Shopify admin."
    #     
    #     slack_service.api_client.update_message(
    #         message_ts=thread_ts,
    #         message_text=message,
    #         action_buttons=[]
    #     )
    #     
    #     return {}
    # except Exception as e:
    #     logger.error(f"Error handling custom refund amount: {e}")
    #     error_message = f"❌ Error: {str(e)}"
    #     slack_service.api_client.update_message(message_ts=thread_ts, message_text=error_message)
    #     return {}
    
    return {"text": "✅ Custom refund amount action received and logged!"}

async def handle_no_refund(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str) -> Dict[str, Any]:
    """
    Handle no refund button click (Step 2)
    """
    print(f"\n🚫 === NO REFUND ACTION ===")
    print(f"👤 User: {slack_user_name}")
    print(f"📋 Request Data: {request_data}")
    print(f"📍 Channel: {channel_id}, Thread: {thread_ts}")
    print("=== END NO REFUND ===\n")
    
    # TODO: Uncomment when ready to implement
    # try:
    #     raw_order_number = request_data.get("rawOrderNumber", "")
    #     order_cancelled = request_data.get("orderCancelled", "False").lower() == "true"
    #     
    #     status = "cancelled" if order_cancelled else "active"
    #     message = f"🚫 *No refund by {slack_user_name}*\\n\\nOrder {raw_order_number} ({status}) - Request closed without refund."
    #     
    #     slack_service.api_client.update_message(
    #         message_ts=thread_ts,
    #         message_text=message,
    #         action_buttons=[]
    #     )
    #     
    #     return {}
    # except Exception as e:
    #     logger.error(f"Error handling no refund: {e}")
    #     error_message = f"❌ Error: {str(e)}"
    #     slack_service.api_client.update_message(message_ts=thread_ts, message_text=error_message)
    #     return {}
    
    return {"text": "✅ No refund action received and logged!"}

# === LEGACY/SUPPORT HANDLERS ===

async def handle_restock_inventory(request_data: Dict[str, str], action_id: str, channel_id: str, thread_ts: str, slack_user_name: str) -> Dict[str, Any]:
    """Handle inventory restocking button clicks"""
    print(f"\n📦 === RESTOCK INVENTORY ACTION ===")
    print(f"👤 User: {slack_user_name}")
    print(f"🔧 Action ID: {action_id}")
    print(f"📋 Request Data: {request_data}")
    print(f"📍 Channel: {channel_id}, Thread: {thread_ts}")
    print("=== END RESTOCK INVENTORY ===\n")
    
    return {"text": "✅ Restock inventory action received and logged!"}

# Legacy handler for backwards compatibility
async def handle_approve_refund(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str) -> Dict[str, Any]:
    """Legacy handler - now redirects to process_refund"""
    print(f"\n⚠️ === LEGACY APPROVE REFUND (redirecting to process_refund) ===")
    return await handle_process_refund(request_data, channel_id, thread_ts, slack_user_name)

# Legacy handler for backwards compatibility  
async def handle_custom_amount_request(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str) -> Dict[str, Any]:
    """Legacy handler - now redirects to custom_refund_amount"""
    print(f"\n⚠️ === LEGACY CUSTOM AMOUNT (redirecting to custom_refund_amount) ===")
    return await handle_custom_refund_amount(request_data, channel_id, thread_ts, slack_user_name)

# Legacy handler for backwards compatibility
async def handle_cancel_request(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str) -> Dict[str, Any]:
    """Legacy handler - now redirects to cancel_and_close_request"""
    print(f"\n⚠️ === LEGACY CANCEL REQUEST (redirecting to cancel_and_close_request) ===")
    return await handle_cancel_and_close_request(request_data, channel_id, thread_ts, slack_user_name)

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