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

def extract_text_from_blocks(blocks: list) -> str:
    """Extract text content from Slack blocks structure"""
    try:
        text_parts = []
        
        for block in blocks:
            if not isinstance(block, dict):
                continue
                
            block_type = block.get("type", "")
            
            # Extract text from section blocks
            if block_type == "section":
                text_obj = block.get("text", {})
                if isinstance(text_obj, dict) and "text" in text_obj:
                    text_parts.append(text_obj["text"])
            
            # Extract text from context blocks
            elif block_type == "context":
                elements = block.get("elements", [])
                for element in elements:
                    if isinstance(element, dict) and "text" in element:
                        text_parts.append(element["text"])
            
            # Extract text from rich_text blocks
            elif block_type == "rich_text":
                elements = block.get("elements", [])
                for element in elements:
                    if isinstance(element, dict):
                        if element.get("type") == "rich_text_section":
                            sub_elements = element.get("elements", [])
                            for sub_element in sub_elements:
                                if isinstance(sub_element, dict) and "text" in sub_element:
                                    text_parts.append(sub_element["text"])
        
        return "\n".join(text_parts)
        
    except Exception as e:
        logger.error(f"Error extracting text from blocks: {e}")
        return ""

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
                
                # Extract current message content for data preservation
                # Use blocks structure instead of just text field for complete data
                current_message_blocks = payload.get("message", {}).get("blocks", [])
                current_message_text = payload.get("message", {}).get("text", "")  # Keep as fallback
                
                # Convert blocks back to text for parsing
                current_message_full_text = extract_text_from_blocks(current_message_blocks)
                
                print(f"\n📨 === SLACK WEBHOOK MESSAGE DEBUG ===")
                print(f"📝 Extracted current_message_text length: {len(current_message_text)}")
                print(f"📝 Extracted blocks count: {len(current_message_blocks)}")
                print(f"📝 Extracted current_message_full_text length: {len(current_message_full_text)}")
                print(f"📝 Current message full text: {current_message_full_text[:500]}...")
                print(f"🔘 Action ID: {action_id}")
                print("=== END SLACK WEBHOOK MESSAGE DEBUG ===\n")
                
                # Route to appropriate handler - NEW DECOUPLED FLOW
                if action_id == "cancel_order":
                    return await handle_cancel_order(request_data, channel_id, thread_ts, slack_user_id, slack_user_name, current_message_full_text)
                elif action_id == "proceed_without_cancel":
                    return await handle_proceed_without_cancel(request_data, channel_id, thread_ts, slack_user_id, slack_user_name, current_message_full_text)
                elif action_id == "cancel_and_close_request":
                    return await handle_cancel_and_close_request(request_data, channel_id, thread_ts, slack_user_name)
                elif action_id == "process_refund":
                    return await handle_process_refund(request_data, channel_id, thread_ts, slack_user_name, current_message_full_text)
                # elif action_id == "custom_refund_amount":
                #     return await handle_custom_refund_amount(request_data, channel_id, thread_ts, slack_user_name)
                elif action_id == "no_refund":
                    return await handle_no_refund(request_data, channel_id, thread_ts, slack_user_name, current_message_full_text)
                elif action_id.startswith("restock") or action_id == "do_not_restock":
                    return await handle_restock_inventory(request_data, action_id, channel_id, thread_ts, slack_user_name, current_message_full_text)
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

async def handle_cancel_order(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_id: str, slack_user_name: str, current_message_full_text: str) -> Dict[str, Any]:
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
        
        # Check mode for debug vs production behavior
        is_debug_mode = 'debug' in settings.mode.lower()
        is_prod_mode = 'prod' in settings.mode.lower()
        
        if is_debug_mode:
            print(f"🧪 DEBUG MODE: Fetching REAL order details for {raw_order_number}")
            print(f"🧪 DEBUG MODE: Will MOCK order cancellation (no real API call)")
            
            # 1. Fetch REAL order details from Shopify (same as production)
            order_result = orders_service.fetch_order_details(order_name=raw_order_number)
            if not order_result["success"]:
                logger.error(f"Failed to fetch order details for {raw_order_number}: {order_result['message']}")
                error_message = f"❌ Failed to fetch order details: {order_result['message']}"
                slack_service.api_client.update_message(message_ts=thread_ts, message_text=error_message)
                return {}
            
            shopify_order_data = order_result["data"]
            
            # 2. Calculate REAL refund amount (same as production)
            refund_calculation = orders_service.calculate_refund_due(shopify_order_data, refund_type)
            
            # 3. MOCK the order cancellation (debug mode difference)
            print(f"🧪 DEBUG MODE: Would cancel order {shopify_order_data.get('orderId', 'unknown')} in Shopify")
            cancel_result = {"success": True, "message": "Mock order cancellation in debug mode"}
            
        elif is_prod_mode:
            print(f"🚀 PRODUCTION MODE: Making real API calls")
            
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
            
        else:
            # Default to debug mode if mode is not recognized
            print(f"⚠️ UNKNOWN MODE '{settings.mode}': Defaulting to debug mode")
            # Fall back to debug mode behavior
            order_result = orders_service.fetch_order_details(order_name=raw_order_number)
            if not order_result["success"]:
                logger.error(f"Failed to fetch order details for {raw_order_number}: {order_result['message']}")
                error_message = f"❌ Failed to fetch order details: {order_result['message']}"
                slack_service.api_client.update_message(message_ts=thread_ts, message_text=error_message)
                return {}
            
            shopify_order_data = order_result["data"]
            refund_calculation = orders_service.calculate_refund_due(shopify_order_data, refund_type)
            cancel_result = {"success": True, "message": "Mock order cancellation in debug mode"}
        
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
            
            # 5. Extract Google Sheets link from current message
            sheet_link = extract_sheet_link(current_message_full_text)
            print(f"🔗 Extracted sheet link for cancel_order: {sheet_link}")
            
            # 6. Create refund decision message
            from services.slack.message_builder import SlackMessageBuilder
            message_builder = SlackMessageBuilder({})
            refund_message = message_builder.create_refund_decision_message(
                order_data, refund_type, "@channel", 
                sheet_link=sheet_link,
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
    

async def handle_proceed_without_cancel(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_id: str, slack_user_name: str, current_message_full_text: str) -> Dict[str, Any]:
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
        
        # Check mode for debug vs production behavior
        is_debug_mode = 'debug' in settings.mode.lower()
        is_prod_mode = 'prod' in settings.mode.lower()
        
        if is_debug_mode:
            print(f"🧪 DEBUG MODE: Fetching REAL order details for {raw_order_number}")
            print(f"🧪 DEBUG MODE: Order will NOT be canceled (proceed without cancel)")
            
            # 1. Fetch REAL order details from Shopify (same as production)
            order_result = orders_service.fetch_order_details(order_name=raw_order_number)
            if not order_result["success"]:
                logger.error(f"Failed to fetch order details for {raw_order_number}: {order_result['message']}")
                error_message = f"❌ Failed to fetch order details: {order_result['message']}"
                slack_service.api_client.update_message(message_ts=thread_ts, message_text=error_message)
                return {}
            
            shopify_order_data = order_result["data"]
            
            # 2. Calculate REAL refund amount (same as production)
            refund_calculation = orders_service.calculate_refund_due(shopify_order_data, refund_type)
            
        elif is_prod_mode:
            print(f"🚀 PRODUCTION MODE: Making real API calls")
            
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
            
        else:
            # Default to debug mode if mode is not recognized
            print(f"⚠️ UNKNOWN MODE '{settings.mode}': Defaulting to debug mode")
            # Fall back to debug mode behavior
            order_result = orders_service.fetch_order_details(order_name=raw_order_number)
            if not order_result["success"]:
                logger.error(f"Failed to fetch order details for {raw_order_number}: {order_result['message']}")
                error_message = f"❌ Failed to fetch order details: {order_result['message']}"
                slack_service.api_client.update_message(message_ts=thread_ts, message_text=error_message)
                return {}
            
            shopify_order_data = order_result["data"]
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
        
        # 4. Extract Google Sheets link from current message
        sheet_link = extract_sheet_link(current_message_full_text)
        print(f"🔗 Extracted sheet link for proceed_without_cancel: {sheet_link}")
        
        # 5. Create refund decision message (order remains active)
        from services.slack.message_builder import SlackMessageBuilder
        message_builder = SlackMessageBuilder({})
        refund_message = message_builder.create_refund_decision_message(
            order_data, refund_type, "@channel", 
            sheet_link=sheet_link,
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

async def handle_process_refund(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str, current_message_full_text: str) -> Dict[str, Any]:
    """
    Handle process calculated refund button click (Step 2)
    """
    print(f"\n✅ === PROCESS REFUND ACTION ===")
    print(f"👤 User: {slack_user_name}")
    print(f"📋 Request Data: {request_data}")
    print(f"📍 Channel: {channel_id}, Thread: {thread_ts}")
    print("=== END PROCESS REFUND ===\n")
    
    try:
        order_id = request_data.get("orderId", "")
        raw_order_number = request_data.get("rawOrderNumber", "")
        refund_amount = float(request_data.get("refundAmount", "0"))
        refund_type = request_data.get("refundType", "refund")
        order_cancelled = request_data.get("orderCancelled", "False").lower() == "true"
        
        logger.info(f"Processing refund: Order {raw_order_number}, Amount: ${refund_amount}")
        
        # Check MODE configuration for debug vs production behavior
        is_debug_mode = 'debug' in settings.mode.lower()
        
        if is_debug_mode:
            print(f"🧪 DEBUG MODE: Would process refund for order {raw_order_number}")
            print(f"🧪 DEBUG MODE: Would create ${refund_amount:.2f} {refund_type}")
            
            # Print JSON post body for debug purposes
            debug_refund_body = {
                "orderId": order_id,
                "rawOrderNumber": raw_order_number,
                "refundAmount": refund_amount,
                "refundType": refund_type,
                "orderCancelled": order_cancelled,
                "processedBy": slack_user_name
            }
            print(f"🧪 DEBUG MODE: JSON POST BODY for refund:\n{json.dumps(debug_refund_body, indent=2)}")
            
            # Mock successful refund result for debug mode
            refund_result = {"success": True, "refund_id": f"mock-refund-{raw_order_number.replace('#', '')}"}
        else:
            # Production mode - make actual Shopify API call
            print(f"🏭 PRODUCTION MODE: Making real refund API call")
            refund_result = orders_service.create_refund_only(order_id, refund_amount)
        
        if refund_result["success"]:
            # Fetch fresh order details for comprehensive message
            order_result = orders_service.fetch_order_details(order_name=raw_order_number)
            if order_result["success"]:
                shopify_order_data = order_result["data"]
                
                # Build comprehensive success message matching Google Apps Script format
                success_message_data = build_comprehensive_success_message(
                    order_data=shopify_order_data,
                    refund_amount=refund_amount,
                    refund_type=refund_type,
                    raw_order_number=raw_order_number,
                    order_cancelled=order_cancelled,
                    processor_user=slack_user_name,
                    is_debug_mode=is_debug_mode,
                    current_message_text=current_message_full_text,
                    order_id=order_id  # Pass the order_id for proper URL building
                )
                
                # Update message with debugging
                try:
                    print(f"🔄 Attempting to update Slack message with {len(success_message_data['action_buttons'])} buttons")
                    update_result = slack_service.api_client.update_message(
                        message_ts=thread_ts,
                        message_text=success_message_data["text"],
                        action_buttons=success_message_data["action_buttons"]
                    )
                    print(f"✅ Message update result: {update_result.get('success', False)}")
                    if not update_result.get('success', False):
                        print(f"❌ Message update failed: {update_result.get('error', 'Unknown error')}")
                        print(f"📝 Slack response: {update_result.get('slack_response', {})}")
                except Exception as update_error:
                    print(f"❌ Exception during message update: {str(update_error)}")
                    logger.error(f"Message update exception: {str(update_error)}")
            else:
                # Fallback if order fetch fails
                status = "cancelled" if order_cancelled else "active"
                if is_debug_mode:
                    message = f"✅ *[DEBUG] Mock refund processed by {slack_user_name}*\n\nOrder {raw_order_number} ({status}) - ${refund_amount:.2f} {refund_type} processed successfully."
                else:
                    message = f"✅ *Refund processed by {slack_user_name}*\n\nOrder {raw_order_number} ({status}) - ${refund_amount:.2f} {refund_type} processed successfully."
                
                try:
                    slack_service.api_client.update_message(
                        message_ts=thread_ts,
                        message_text=message,
                        action_buttons=[]
                    )
                except Exception as e:
                    print(f"❌ Fallback message update failed: {str(e)}")
        else:
            message = f"❌ *Refund failed*\n\nError: {refund_result.get('message', 'Unknown error')}"
            try:
                slack_service.api_client.update_message(
                    message_ts=thread_ts,
                    message_text=message,
                    action_buttons=[]
                )
            except Exception as e:
                print(f"❌ Error message update failed: {str(e)}")
        
        return {}
    except Exception as e:
        logger.error(f"Error processing refund: {e}")
        error_message = f"❌ Error processing refund: {str(e)}"
        try:
            slack_service.api_client.update_message(message_ts=thread_ts, message_text=error_message)
        except Exception as update_e:
            print(f"❌ Process refund exception handler message update failed: {str(update_e)}")
        return {}

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

async def handle_no_refund(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str, current_message_full_text: str) -> Dict[str, Any]:
    """
    Handle no refund button click (Step 2)
    """
    print(f"\n🚫 === NO REFUND ACTION ===")
    print(f"👤 User: {slack_user_name}")
    print(f"📋 Request Data: {request_data}")
    print(f"📍 Channel: {channel_id}, Thread: {thread_ts}")
    print("=== END NO REFUND ===\n")
    
    try:
        raw_order_number = request_data.get("rawOrderNumber", "")
        order_cancelled = request_data.get("orderCancelled", "False").lower() == "true"
        
        # Check MODE configuration for debug vs production behavior
        is_debug_mode = 'debug' in settings.mode.lower()
        
        if is_debug_mode:
            print(f"🧪 DEBUG MODE: Would close refund request for order {raw_order_number}")
            print(f"🧪 DEBUG MODE: No actual API calls needed for 'no refund' action")
        else:
            print(f"🏭 PRODUCTION MODE: Closing refund request (no API calls needed)")
        
        # Fetch fresh order details for comprehensive message
        order_result = orders_service.fetch_order_details(order_name=raw_order_number)
        if order_result["success"]:
            shopify_order_data = order_result["data"]
            
            # Build comprehensive no refund message matching Google Apps Script format
            no_refund_message_data = build_comprehensive_no_refund_message(
                order_data=shopify_order_data,
                raw_order_number=raw_order_number,
                order_cancelled=order_cancelled,
                processor_user=slack_user_name,
                is_debug_mode=is_debug_mode,
                thread_ts=thread_ts
            )
            
            slack_service.api_client.update_message(
                message_ts=thread_ts,
                message_text=no_refund_message_data["text"],
                action_buttons=no_refund_message_data["action_buttons"]
            )
        else:
            # Fallback if order fetch fails
            status = "cancelled" if order_cancelled else "active"
            if is_debug_mode:
                message = f"🚫 *[DEBUG] No refund by {slack_user_name}*\n\nOrder {raw_order_number} ({status}) - Request closed without refund."
            else:
                message = f"🚫 *No refund by {slack_user_name}*\n\nOrder {raw_order_number} ({status}) - Request closed without refund."
            
            try:
                slack_service.api_client.update_message(
                    message_ts=thread_ts,
                    message_text=message,
                    action_buttons=[]
                )
            except Exception as e:
                print(f"❌ No refund message update failed: {str(e)}")
        
        return {}
    except Exception as e:
        logger.error(f"Error handling no refund: {e}")
        error_message = f"❌ Error: {str(e)}"
        try:
            slack_service.api_client.update_message(message_ts=thread_ts, message_text=error_message)
        except Exception as update_e:
            print(f"❌ Exception handler message update failed: {str(update_e)}")
        return {}

# === LEGACY/SUPPORT HANDLERS ===

async def handle_restock_inventory(request_data: Dict[str, str], action_id: str, channel_id: str, thread_ts: str, slack_user_name: str, current_message_full_text: str) -> Dict[str, Any]:
    """Handle inventory restocking button clicks"""
    print(f"\n📦 === RESTOCK INVENTORY ACTION ===")
    print(f"👤 User: {slack_user_name}")
    print(f"🔧 Action ID: {action_id}")
    print(f"📋 Request Data: {request_data}")
    print(f"📍 Channel: {channel_id}, Thread: {thread_ts}")
    print("=== END RESTOCK INVENTORY ===\n")
    
    try:
        order_id = request_data.get("orderId", "")
        raw_order_number = request_data.get("rawOrderNumber", "")
        variant_id = request_data.get("variantId", "")
        variant_name = request_data.get("variantName", "")
        
        # Check MODE configuration for debug vs production behavior
        is_debug_mode = 'debug' in settings.mode.lower()
        
        # Extract Google Sheets link and current message data
        sheet_url = extract_sheet_link(current_message_full_text)
        sheet_link = f"🔗 <{sheet_url}|View Request in Google Sheets>" if sheet_url else "🔗 View Request in Google Sheets"
        
        # Build the final completion message preserving who did what
        completion_message = build_completion_message(
            current_message_full_text=current_message_full_text,
            action_id=action_id,
            variant_name=variant_name,
            restock_user=slack_user_name,
            sheet_link=sheet_link,
            raw_order_number=raw_order_number,
            is_debug_mode=is_debug_mode
        )
        
        if action_id != "do_not_restock":
            # Handle actual inventory restocking
            if is_debug_mode:
                print(f"🧪 DEBUG MODE: Would restock inventory for {variant_name}")
                
                # Print JSON post body for debug purposes
                debug_inventory_body = {
                    "action": "inventoryAdjustQuantities",
                    "variantId": variant_id,
                    "variantName": variant_name,
                    "orderId": order_id,
                    "rawOrderNumber": raw_order_number,
                    "delta": 1,
                    "reason": "movement_created",
                    "locationId": "gid://shopify/Location/61802217566",
                    "processedBy": slack_user_name
                }
                print(f"🧪 DEBUG MODE: JSON POST BODY for inventory restock:\n{json.dumps(debug_inventory_body, indent=2)}")
                
                # Use debug completion message
                completion_message = completion_message.replace("*Inventory restocked", "*[DEBUG] Mock inventory restocked")
            else:
                print(f"🏭 PRODUCTION MODE: Making real inventory API call")
                
                # Make actual Shopify inventory adjustment API call
                # Note: This would need to be implemented in orders_service
                inventory_result = await adjust_shopify_inventory(variant_id, delta=1)
                
                if not inventory_result.get("success", False):
                    # If inventory restock fails, update the message accordingly
                    completion_message = completion_message.replace(
                        f"✅ *Inventory restocked to {variant_name} successfully",
                        f"❌ *Inventory restock to {variant_name} failed"
                    )
        
        # Update Slack message with final completion state
        slack_service.api_client.update_message(
            message_ts=thread_ts,
            message_text=completion_message,
            action_buttons=[]  # No more buttons - process is complete
        )
        
        return {}
        
    except Exception as e:
        logger.error(f"Error handling restock inventory: {e}")
        error_message = f"❌ Error processing inventory restock: {str(e)}"
        slack_service.api_client.update_message(message_ts=thread_ts, message_text=error_message)
        return {}

# Legacy handler for backwards compatibility
async def handle_approve_refund(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str) -> Dict[str, Any]:
    """Legacy handler - now redirects to process_refund"""
    print(f"\n⚠️ === LEGACY APPROVE REFUND (redirecting to process_refund) ===")
    return await handle_process_refund(request_data, channel_id, thread_ts, slack_user_name, "")

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

def build_comprehensive_success_message(order_data: Dict[str, Any], refund_amount: float, refund_type: str,
                                      raw_order_number: str, order_cancelled: bool, processor_user: str,
                                      is_debug_mode: bool, current_message_text: str, order_id: str = "") -> Dict[str, Any]:
    """Build comprehensive success message matching Google Apps Script format"""
    try:
        print(f"\n🏗️ === BUILD COMPREHENSIVE SUCCESS MESSAGE DEBUG ===")
        print(f"📝 Current message text length: {len(current_message_text)}")
        print(f"📝 Current message text preview: {current_message_text[:500]}...")
        
        # CRITICAL: Check if we got the full text or the short fallback text
        if len(current_message_text) < 200:
            print(f"⚠️ WARNING: Received very short message text, might be fallback instead of full blocks text!")
            # Add stack trace to see where this is coming from
            import traceback
            print("📍 CALL STACK:")
            traceback.print_stack()
        else:
            print(f"✅ Good: Received full message text ({len(current_message_text)} characters)")
        
        # Extract data from order
        customer = order_data.get("customer", {})
        product = order_data.get("product", {})
        
        # Get customer name from email if available
        customer_email = customer.get("email", "")
        customer_name = customer_email.split("@")[0].replace(".", " ").title() if customer_email else "Unknown Customer"
        
        # Build order URL with debugging (use passed order_id parameter)
        print(f"🔗 Order ID passed to function: {order_id}")
        print(f"🔗 Raw order number: {raw_order_number}")
        
        if order_id:
            # Extract numeric ID from Shopify GID format
            order_numeric_id = order_id.split('/')[-1] if '/' in order_id else order_id
            order_url = f"<https://admin.shopify.com/store/09fe59-3/orders/{order_numeric_id}|{raw_order_number}>"
            print(f"🔗 Built order URL with link: {order_url}")
        else:
            order_url = raw_order_number
            print(f"🔗 Using raw order number (no order ID): {order_url}")
        
        # Build comprehensive message
        debug_prefix = "[DEBUG] " if is_debug_mode else ""
        message_text = ""
        
        # Cancellation message (if order was cancelled)
        if order_cancelled:
            message_text += f"✅ *{debug_prefix}Cancellation Request for Order {order_url} for {customer_name} has been processed by @{processor_user}*\n"
        
        # Refund processing message
        refund_action = "credit" if refund_type == "credit" else "refund"
        message_text += f"✅ *{debug_prefix}Request to provide a ${refund_amount:.2f} {refund_action} for Order {order_url} has been processed by @{processor_user}*\n"
        
        # Extract data from current message to preserve Google Sheets link and season info
        try:
            sheet_url = extract_sheet_link(current_message_text)
            season_info = extract_season_start_info(current_message_text)
            print(f"🔗 Extracted sheet URL: {sheet_url}")
            print(f"🏷️ Extracted season info: {season_info}")
            # Format the URL for display
            sheet_link = f"🔗 <{sheet_url}|View Request in Google Sheets>" if sheet_url else "🔗 View Request in Google Sheets"
        except Exception as e:
            print(f"❌ Error in extraction: {e}")
            sheet_link = "🔗 View Request in Google Sheets"
            season_info = {"product_title": product.get("title", "Unknown Product"), "season_start": "Unknown"}
        
        message_text += f"\n{sheet_link}\n"
        
        # Season and inventory information
        product_title = season_info.get("product_title", product.get("title", "Unknown Product"))
        product_link = season_info.get("product_link")
        season_start = season_info.get("season_start", "Unknown")
        
        # Use product link if available, otherwise fallback to title or create link from product data
        if product_link:
            product_display = product_link
            print(f"🏷️ Using extracted product link: {product_link}")
        elif product.get("productId") and product_title != "*":
            # Create product link from Shopify data using extracted product title
            product_id = product.get("productId", "").split('/')[-1]
            product_display = f"<https://admin.shopify.com/store/09fe59-3/products/{product_id}|{product_title}>"
            print(f"🏷️ Created product link from Shopify data: {product_display}")
        elif product.get("productId"):
            # Fallback: create link with product title from Shopify data if extraction failed
            product_id = product.get("productId", "").split('/')[-1]
            shopify_title = product.get("title", "Unknown Product")
            product_display = f"<https://admin.shopify.com/store/09fe59-3/products/{product_id}|{shopify_title}>"
            product_title = shopify_title  # Update for display
            print(f"🏷️ Created product link from Shopify fallback: {product_display}")
        else:
            product_display = product_title if product_title != "*" else "Unknown Product"
            print(f"🏷️ Using plain product title: {product_display}")
        
        print(f"📅 Final season start: {season_start}")
        print(f"🏷️ Final product title: {product_title}")
        
        message_text += f"📦 *Season Start Date for {product_display} is {season_start}.*\n"
        message_text += "*Current Inventory:*\n"
        
        # Fetch current inventory
        variants = product.get("variants", [])
        for variant in variants:
            variant_name = variant.get("variantName", "Unknown Variant")
            inventory = variant.get("inventory", 0)
            message_text += f"• *{variant_name}*: {inventory} spots available\n"
        
        # Create restock buttons for each variant
        restock_buttons = []
        for variant in variants:
            variant_name = variant.get("variantName", "Unknown Variant")
            variant_id = variant.get("variantId", "")
            if variant_id:
                # Clean variant ID for action_id (only alphanumeric and underscores)
                clean_variant_id = ''.join(c if c.isalnum() or c == '_' else '_' for c in str(variant_id))
                # Truncate button text to stay under 75 character limit
                button_text = f"Restock {variant_name}"
                if len(button_text) > 70:
                    button_text = f"Restock {variant_name[:60]}..."
                
                # Clean variant name for value (no pipes or special chars that could break parsing)
                clean_variant_name = variant_name.replace("|", "-").replace("=", "-")
                
                restock_buttons.append({
                    "type": "button",
                    "text": {"type": "plain_text", "text": button_text, "emoji": True},
                    "action_id": f"restock_{clean_variant_id}",
                    "value": f"orderId={order_id}|variantId={variant_id}|variantName={clean_variant_name}",
                    "style": "primary"
                })
        
        # Add general restock button if no specific variants
        if not restock_buttons:
            restock_buttons.append({
                "type": "button",
                "text": {"type": "plain_text", "text": "📦 Restock Inventory", "emoji": True},
                "action_id": "restock_inventory",
                "value": f"orderId={order_id}|rawOrderNumber={raw_order_number}",
                "style": "primary"
            })
        
        # Always add "Do Not Restock - All Done!" button (no style = default gray)
        restock_buttons.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "✅ Do Not Restock - All Done!", "emoji": True},
            "action_id": "do_not_restock",
            "value": f"orderId={order_id}|rawOrderNumber={raw_order_number}"
        })
        
        # Debug button validation
        print(f"🔘 Created {len(restock_buttons)} restock buttons:")
        for i, button in enumerate(restock_buttons):
            button_text = button.get("text", {}).get("text", "")
            action_id = button.get("action_id", "")
            value = button.get("value", "")
            print(f"  Button {i+1}: text='{button_text}' (len={len(button_text)}), action_id='{action_id}', value_len={len(value)}")
            
            # Check for potential issues
            if len(button_text) > 75:
                print(f"    ⚠️ WARNING: Button text too long ({len(button_text)} > 75)")
            if len(value) > 2000:
                print(f"    ⚠️ WARNING: Button value too long ({len(value)} > 2000)")
            if not action_id.replace("_", "").replace("-", "").isalnum():
                print(f"    ⚠️ WARNING: Action ID contains special characters: {action_id}")
        
        print(f"✅ Final message built successfully")
        print("=== END BUILD COMPREHENSIVE SUCCESS MESSAGE DEBUG ===\n")
        
        return {
            "text": message_text,
            "action_buttons": restock_buttons
        }
        
    except Exception as e:
        logger.error(f"Error building comprehensive success message: {str(e)}")
        print(f"❌ Error building comprehensive success message: {str(e)}")
        # Fallback to simple message
        status = "cancelled" if order_cancelled else "active"
        debug_prefix = "[DEBUG] " if is_debug_mode else ""
        
        return {
            "text": f"✅ *{debug_prefix}Refund processed by @{processor_user}*\n\nOrder {raw_order_number} ({status}) - ${refund_amount:.2f} {refund_type} processed successfully.",
            "action_buttons": []
        }

def build_completion_message(current_message_full_text: str, action_id: str, variant_name: str, 
                            restock_user: str, sheet_link: str, raw_order_number: str, is_debug_mode: bool) -> str:
    """Build final completion message preserving who processed cancellation, refund, and inventory"""
    try:
        # Parse the current message to extract the completion state
        debug_prefix = "[DEBUG] " if is_debug_mode else ""
        
        # Start with the existing message and modify it for completion
        message_lines = current_message_full_text.split('\n')
        completion_message = ""
        
        # Preserve existing content until we find the Google Sheets link
        for line in message_lines:
            if "View Request in Google Sheets" in line:
                break
            completion_message += line + '\n'
        
        # Add inventory status based on action
        if action_id == "do_not_restock":
            completion_message += f"\n🚫 *{debug_prefix}No inventory was restocked - Process completed by @{restock_user}*\n"
        else:
            # Extract variant name from action_id if not provided
            if not variant_name:
                variant_name = action_id.replace("restock_", "").replace("_", " ").title()
            
            completion_message += f"\n✅ *{debug_prefix}Inventory restocked to {variant_name} successfully by @{restock_user}*\n"
        
        # Add the Google Sheets link
        completion_message += f"\n{sheet_link}\n"
        
        return completion_message
        
    except Exception as e:
        print(f"❌ Error building completion message: {e}")
        # Fallback message
        debug_prefix = "[DEBUG] " if is_debug_mode else ""
        status = "completed" if action_id == "do_not_restock" else f"inventory restocked to {variant_name}"
        return f"✅ *{debug_prefix}Refund request {status} by @{restock_user}*\n\n{sheet_link}"

async def adjust_shopify_inventory(variant_id: str, delta: int = 1) -> Dict[str, Any]:
    """Adjust Shopify inventory using the GraphQL API"""
    try:
        # This would need to be implemented to make actual Shopify GraphQL calls
        # For now, return a mock success
        print(f"🏭 PRODUCTION MODE: Would adjust inventory for variant {variant_id} by {delta}")
        
        # Mock GraphQL mutation similar to the Google Apps Script
        mutation_body = {
            "query": """
                mutation inventoryAdjustQuantities($input: InventoryAdjustQuantitiesInput!) {
                    inventoryAdjustQuantities(input: $input) {
                        userErrors { field message }
                        inventoryAdjustmentGroup {
                            createdAt
                            reason
                            changes { name delta }
                        }
                    }
                }
            """,
            "variables": {
                "input": {
                    "reason": "movement_created",
                    "name": "available", 
                    "changes": [
                        {
                            "delta": delta,
                            "inventoryItemId": variant_id,
                            "locationId": "gid://shopify/Location/61802217566"
                        }
                    ]
                }
            }
        }
        
        print(f"🏭 PRODUCTION MODE: GraphQL mutation body:\n{json.dumps(mutation_body, indent=2)}")
        
        # TODO: Implement actual Shopify GraphQL API call here
        # For now, return mock success
        return {"success": True, "message": "Mock inventory adjustment"}
        
    except Exception as e:
        logger.error(f"Error adjusting Shopify inventory: {e}")
        return {"success": False, "message": str(e)}

def extract_data_from_slack_thread(thread_ts: str) -> str:
    """Extract data from the Slack thread message (placeholder implementation)"""
    # TODO: Implement actual Slack thread message retrieval
    # For now, return empty string to use fallback values
    return ""

def extract_sheet_link(message_text: str) -> str:
    """Extract Google Sheets link from message"""
    import re
    import html
    
    print(f"\n🔍 === EXTRACT SHEET LINK DEBUG ===")
    print(f"📝 Input message text length: {len(message_text)}")
    print(f"📝 Input message text preview: {message_text[:300]}...")
    
    # Decode HTML entities like &amp; that might be in Slack message blocks
    decoded_text = html.unescape(message_text)
    print(f"📝 Decoded text preview: {decoded_text[:300]}...")
    
    # Look for different Google Sheets link patterns
    patterns = [
        # Pattern 1: Slack link format <URL|text> (with :link: emoji)
        r':link:\s*\*<(https://docs\.google\.com/spreadsheets/[^>|]+)\|[^>]*>\*',
        # Pattern 2: Slack link format <URL|text> (with 🔗 emoji)
        r'🔗\s*\*<(https://docs\.google\.com/spreadsheets/[^>|]+)\|[^>]*>\*',
        # Pattern 3: Slack link format <URL|text> (without emoji)
        r'<(https://docs\.google\.com/spreadsheets/[^>|]+)\|[^>]*>',
        # Pattern 4: Direct URL after emoji
        r'🔗[^h]*?(https://docs\.google\.com/spreadsheets/[^\s\n]+)',
        # Pattern 5: URL on same line as emoji
        r'🔗.*?(https://docs\.google\.com/spreadsheets/[^\s\n]+)',
        # Pattern 6: URL anywhere in the message
        r'(https://docs\.google\.com/spreadsheets/[^\s\n]+)'
    ]
    
    for i, pattern in enumerate(patterns):
        print(f"🔍 Testing pattern {i+1}: {pattern}")
        match = re.search(pattern, decoded_text)
        if match:
            url = match.group(1)
            # Clean up the URL (remove any remaining HTML entities)
            url = html.unescape(url)
            print(f"✅ Pattern {i+1} matched! URL: {url}")
            print(f"✅ Returning URL: {url}")
            print("=== END EXTRACT SHEET LINK DEBUG ===\n")
            return url
        else:
            print(f"❌ Pattern {i+1} no match")
    
    # Fallback if no URL found - use the user-provided fallback URL
    fallback_url = "https://docs.google.com/spreadsheets/d/11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw/edit"
    print("❌ No patterns matched, using fallback")
    print(f"✅ Fallback URL: {fallback_url}")
    print("=== END EXTRACT SHEET LINK DEBUG ===\n")
    return fallback_url

def extract_season_start_info(message_text: str) -> Dict[str, Optional[str]]:
    """Extract season start information from message"""
    import re
    
    print(f"\n🔍 === EXTRACT SEASON START INFO DEBUG ===")
    print(f"📝 Input message text length: {len(message_text)}")
    print(f"📝 Input message text preview: {message_text[:200]}...")
    
    # Look for different product/season patterns
    patterns = [
        # Pattern 1: Season Start Date line with product (with link)
        r"Season Start Date for <[^|]+\|([^>]+)> is (.+?)\.",
        # Pattern 2: Season Start Date line with product (plain text)
        r"Season Start Date for (.+?) is (.+?)\.",
        # Pattern 3: Product Title field with Slack link - extract title from <URL|title>
        r"\*Product Title\*:\s*<[^|]+\|([^>]+)>",
        # Pattern 4: Product Title field with full Slack link
        r"\*Product Title\*:\s*(<[^>]+>)",
        # Pattern 5: Sport/Season/Day field with Slack link - extract title from <URL|title>
        r"\*Sport/Season/Day\*:\s*<[^|]+\|([^>]+)>",
        # Pattern 6: Sport/Season/Day field with full Slack link  
        r"\*Sport/Season/Day\*:\s*(<[^>]+>)",
        # Pattern 7: Product title with link <URL|title> (extract title only)
        r"Product Title:\s*<[^|]+\|([^>]+)>",
        r"Sport/Season/Day:\s*<[^|]+\|([^>]+)>",
        # Pattern 8: Product Title field (plain text)
        r"Product Title:\s*([^<\n]+)",
        # Pattern 9: Sport/Season/Day field (plain text)
        r"Sport/Season/Day:\s*([^<\n]+)"
    ]
    
    product_title = "Unknown Product"
    product_link = None
    season_start = "Unknown"
    
    # Try to find season start date with product (Pattern 1: with link)
    season_match = re.search(patterns[0], message_text)
    if season_match:
        product_title = season_match.group(1).strip()
        season_start = season_match.group(2).strip()
        print(f"✅ Pattern 1 matched! Product: {product_title}, Season Start: {season_start}")
        print("=== END EXTRACT SEASON START INFO DEBUG ===\n")
        return {"product_title": product_title, "season_start": season_start, "product_link": None}
    
    # Try to find season start date with product (Pattern 2: plain text)
    season_match = re.search(patterns[1], message_text)
    if season_match:
        product_title = season_match.group(1).strip()
        season_start = season_match.group(2).strip()
        print(f"✅ Pattern 2 matched! Product: {product_title}, Season Start: {season_start}")
        print("=== END EXTRACT SEASON START INFO DEBUG ===\n")
        return {"product_title": product_title, "season_start": season_start, "product_link": None}
    
    # Try to find product title/link from various fields
    for i, pattern in enumerate(patterns[2:], start=3):
        product_match = re.search(pattern, message_text)
        if product_match:
            matched_text = product_match.group(1).strip()
            
            # Check if it's a full Slack link (patterns 4 and 6) 
            if i in [4, 6] and matched_text.startswith('<') and matched_text.endswith('>'):
                product_link = matched_text
                # Extract title from link for display
                if '|' in matched_text:
                    product_title = matched_text.split('|')[1].replace('>', '')
                else:
                    product_title = "Unknown Product"
                print(f"✅ Pattern {i} matched! Product Link: {product_link}, Title: {product_title}")
            else:
                # Plain text or title from link (patterns 3, 5, 7, 8 get title directly)
                product_title = matched_text
                print(f"✅ Pattern {i} matched! Product: {product_title}")
            break
    
    # Try to find separate season start date
    season_date_patterns = [
        r"Season Start Date:\s*([^\n]+)",
        r"Season Start:\s*([^\n]+)",
        r"Start Date:\s*([^\n]+)"
    ]
    
    for pattern in season_date_patterns:
        season_match = re.search(pattern, message_text)
        if season_match:
            season_start = season_match.group(1).strip()
            print(f"✅ Pattern {len(season_date_patterns) + patterns.index(pattern) + 2} matched! Season Start: {season_start}")
            break
    
    print("❌ No season start info found, using fallback")
    print("=== END EXTRACT SEASON START INFO DEBUG ===\n")
    return {"product_title": product_title, "season_start": season_start, "product_link": product_link}

def build_comprehensive_no_refund_message(order_data: Dict[str, Any], raw_order_number: str, 
                                         order_cancelled: bool, processor_user: str,
                                         is_debug_mode: bool, thread_ts: str) -> Dict[str, Any]:
    """Build comprehensive no refund message matching Google Apps Script format"""
    try:
        # Extract data from order
        order_id = order_data.get("orderId", "")
        customer = order_data.get("customer", {})
        product = order_data.get("product", {})
        
        # Get customer name from email if available
        customer_email = customer.get("email", "")
        customer_name = customer_email.split("@")[0].replace(".", " ").title() if customer_email else "Unknown Customer"
        
        # Build order URL
        order_url = f"<https://admin.shopify.com/store/09fe59-3/orders/{order_id.split('/')[-1]}|{raw_order_number}>" if order_id else raw_order_number
        
        # Build comprehensive message
        debug_prefix = "[DEBUG] " if is_debug_mode else ""
        message_text = ""
        
        # Cancellation message (if order was cancelled)
        if order_cancelled:
            message_text += f"✅ *{debug_prefix}Cancellation Request for Order {order_url} for {customer_name} has been processed by @{processor_user}*\n"
        
        # No refund message
        message_text += f"🚫 *{debug_prefix}No refund provided for Order {order_url} - Request closed by @{processor_user}*\n"
        
        # Extract data from current message on thread to preserve Google Sheets link and season info
        try:
            existing_message_text = extract_data_from_slack_thread(thread_ts)
            sheet_url = extract_sheet_link(existing_message_text)
            season_info = extract_season_start_info(existing_message_text)
            # Format the URL for display
            sheet_link = f"🔗 <{sheet_url}|View Request in Google Sheets>" if sheet_url else "🔗 View Request in Google Sheets"
        except:
            sheet_link = "🔗 View Request in Google Sheets"
            season_info = {"product_title": product.get("title", "Unknown Product"), "season_start": "Unknown"}
        
        message_text += f"\n{sheet_link}\n"
        
        # Season and inventory information
        product_title = season_info.get("product_title", product.get("title", "Unknown Product"))
        season_start = season_info.get("season_start", "Unknown")
        
        message_text += f"📦 *Season Start Date for {product_title} is {season_start}.*\n"
        message_text += "*Current Inventory:*\n"
        
        # Fetch current inventory
        variants = product.get("variants", [])
        for variant in variants:
            variant_name = variant.get("variantName", "Unknown Variant")
            inventory = variant.get("inventory", 0)
            message_text += f"• *{variant_name}*: {inventory} spots available\n"
        
        # Create restock buttons for each variant (same as refund case)
        restock_buttons = []
        for variant in variants:
            variant_name = variant.get("variantName", "Unknown Variant")
            variant_id = variant.get("variantId", "")
            if variant_id:
                restock_buttons.append({
                    "type": "button",
                    "text": {"type": "plain_text", "text": f"📦 Restock {variant_name}"},
                    "action_id": f"restock_{variant_id}",
                    "value": f"orderId={order_id}|variantId={variant_id}|variantName={variant_name}",
                    "style": "primary"
                })
        
        # Add general restock button if no specific variants
        if not restock_buttons:
            restock_buttons.append({
                "type": "button",
                "text": {"type": "plain_text", "text": "📦 Restock Inventory"},
                "action_id": "restock_inventory",
                "value": f"orderId={order_id}|rawOrderNumber={raw_order_number}",
                "style": "primary"
            })
        
        # Always add "Do Not Restock - All Done!" button
        restock_buttons.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "✅ Do Not Restock - All Done!"},
            "action_id": "do_not_restock",
            "value": f"orderId={order_id}|rawOrderNumber={raw_order_number}",
            "style": "secondary"
        })
        
        return {
            "text": message_text,
            "action_buttons": restock_buttons
        }
        
    except Exception as e:
        logger.error(f"Error building comprehensive no refund message: {str(e)}")
        # Fallback to simple message
        status = "cancelled" if order_cancelled else "active"
        debug_prefix = "[DEBUG] " if is_debug_mode else ""
        
        return {
            "text": f"🚫 *{debug_prefix}No refund by @{processor_user}*\n\nOrder {raw_order_number} ({status}) - Request closed without refund.",
            "action_buttons": []
        }

@router.get("/health")
async def health_check():
    """Health check endpoint for the Slack service"""
    return {"status": "healthy", "service": "slack"} 