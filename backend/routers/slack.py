from fastapi import APIRouter, HTTPException, Request, Form
from typing import Dict, Any, Optional, List
import logging
import json
import hmac
import hashlib
import requests # Added for Shopify GraphQL API calls

from services.orders import OrdersService
from services.slack import SlackService
from config import settings
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/slack", tags=["slack"])

orders_service = OrdersService()
slack_service = SlackService()

def should_update_slack_on_shopify_failure() -> bool:
    """
    Determine whether to update Slack messages when Shopify operations fail.
    In production, we might want to avoid updating Slack on failures.
    """
    # Check environment - in production, you can disable error message updates
    # by changing this logic based on your environment settings
    
    # Option 1: Always allow error messages (current behavior)
    # return True
    
    # Option 2: Disable error messages in production (uncomment to enable)
    # return not getattr(settings, 'is_production_mode', False)
    
    # Option 3: Never send error messages (uncomment to enable)  
    return False

def update_slack_on_shopify_success(
    message_ts: str, 
    success_message: str, 
    action_buttons: Optional[List[Dict]] = None
) -> bool:
    """
    Update Slack message only for successful Shopify operations.
    Returns True if update was attempted, False if skipped.
    """
    try:
        update_result = slack_service.api_client.update_message(
            message_ts=message_ts,
            message_text=success_message,
            action_buttons=action_buttons or []
        )
        
        if update_result.get('success', False):
            logger.info("✅ Slack message updated successfully after Shopify success")
            return True
        else:
            logger.error(f"❌ Slack message update failed: {update_result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Exception during Slack message update: {str(e)}")
        return False

def send_ephemeral_error_to_user(
    channel_id: str,
    user_id: str, 
    error_message: str,
    operation_name: str = "operation"
) -> bool:
    """
    Send an ephemeral (private) error message to the user who clicked the button.
    This shows up as a temporary pop-up that only the user can see.
    """
    try:
        # Create ephemeral message payload
        ephemeral_payload = {
            "channel": channel_id,
            "user": user_id,
            "text": f"❌ **{operation_name.title()} Failed**",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"❌ **{operation_name.title()} Failed**\n\n{error_message}"
                    }
                }
            ]
        }
        
        # Send ephemeral message via Slack API
        result = slack_service.api_client.send_ephemeral_message(ephemeral_payload)
        
        if result.get('success', False):
            logger.info(f"✅ Sent ephemeral error message to user {user_id}")
            return True
        else:
            logger.error(f"❌ Failed to send ephemeral message: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Exception sending ephemeral error message: {str(e)}")
        return False

def send_modal_error_to_user(
    trigger_id: str,
    error_message: str,
    operation_name: str = "operation"
) -> bool:
    """
    Send a modal dialog error message to the user who clicked the button.
    Modals automatically dismiss when the user clicks outside or takes action.
    
    Args:
        trigger_id: The trigger ID from the Slack interaction
        error_message: The error message to display
        operation_name: The name of the operation that failed
        
    Returns:
        True if modal was sent successfully, False otherwise
    """
    try:
        # Clean up error message for Slack compatibility
        cleaned_message = error_message.replace('**', '*').replace('•', '-')
        
        # Ensure title is not too long (24 char limit for modal titles)
        title_text = f"{operation_name.title()} Error"
        if len(title_text) > 24:
            title_text = "Error"
        
        # Ensure message text is not too long (3000 char limit for section text)
        modal_text = f":x: *{operation_name.title()} Failed*\n\n{cleaned_message}"
        if len(modal_text) > 2800:  # Leave some buffer
            modal_text = f":x: *{operation_name.title()} Failed*\n\n{cleaned_message[:2700]}..."
        
        # Create modal view
        modal_view = {
            "type": "modal",
            "title": {
                "type": "plain_text",
                "text": title_text
            },
            "close": {
                "type": "plain_text",
                "text": "Close"
            },
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": modal_text
                    }
                }
            ]
        }
        
        logger.info(f"📱 Sending modal with trigger_id: {trigger_id[:20]}...")
        logger.debug(f"📱 Modal title: '{title_text}' (length: {len(title_text)})")
        logger.debug(f"📱 Modal text length: {len(modal_text)}")
        logger.debug(f"📱 Modal view: {modal_view}")
        
        # Send modal via Slack API
        result = slack_service.api_client.send_modal(trigger_id, modal_view)
        
        if result.get('success', False):
            logger.info(f"✅ Sent modal error dialog for {operation_name}")
            return True
        else:
            logger.error(f"❌ Failed to send modal dialog: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Exception sending modal error dialog: {str(e)}")
        return False

def update_slack_on_shopify_failure(
    message_ts: str, 
    error_message: str, 
    operation_name: str = "Shopify operation"
) -> bool:
    """
    Update Slack message for failed Shopify operations.
    Only updates if should_update_slack_on_shopify_failure() returns True.
    """
    if not should_update_slack_on_shopify_failure():
        logger.info(f"⏭️ Skipping Slack update for {operation_name} failure (configured to skip)")
        return False
    
    try:
        update_result = slack_service.api_client.update_message(
            message_ts=message_ts,
            message_text=error_message,
            action_buttons=[]
        )
        
        if update_result.get('success', False):
            logger.info(f"✅ Slack error message updated for {operation_name} failure")
            return True
        else:
            logger.error(f"❌ Slack error message update failed: {update_result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Exception during Slack error message update: {str(e)}")
        return False

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
        payload = None  # Initialize payload to avoid UnboundLocalError
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
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        except Exception as e:
            print(f"❌ Form Parse Error: {e}")
            raise HTTPException(status_code=400, detail="Invalid form data")
        
        print("=== END DEBUG ===\n")
        
        # Process button actions
        if payload and payload.get("type") == "block_actions":
            actions = payload.get("actions", [])
            if actions:
                action = actions[0]
                action_id = action.get("action_id")
                action_value = action.get("value", "")
                slack_user_id = payload.get("user", {}).get("id", "Unknown")
                slack_user_name = payload.get("user", {}).get("name", "Unknown")
                
                # Extract trigger_id for modal dialogs
                trigger_id = payload.get("trigger_id")
                
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
                
                # If blocks extraction fails, fall back to the simple text field
                if not current_message_full_text and current_message_text:
                    current_message_full_text = current_message_text
                    print(f"⚠️ Using fallback message text since blocks extraction failed")
                
                print(f"\n📨 === SLACK WEBHOOK MESSAGE DEBUG ===")
                print(f"📝 Extracted current_message_text length: {len(current_message_text)}")
                print(f"📝 Extracted blocks count: {len(current_message_blocks)}")
                print(f"📝 Extracted current_message_full_text length: {len(current_message_full_text)}")
                print(f"📝 Current message full text: {current_message_full_text[:500]}...")
                print(f"📝 Blocks structure: {current_message_blocks}")
                print(f"🔘 Action ID: {action_id}")
                print("=== END SLACK WEBHOOK MESSAGE DEBUG ===\n")
                
                # Route to appropriate handler - NEW DECOUPLED FLOW
                if action_id == "cancel_order":
                    return await handle_cancel_order(request_data, channel_id, thread_ts, slack_user_id, slack_user_name, current_message_full_text, trigger_id)
                elif action_id == "proceed_without_cancel":
                    return await handle_proceed_without_cancel(request_data, channel_id, thread_ts, slack_user_id, slack_user_name, current_message_full_text, trigger_id)
                elif action_id == "cancel_and_close_request":
                    return await handle_cancel_and_close_request(request_data, channel_id, thread_ts, slack_user_name, trigger_id)
                elif action_id == "process_refund":
                    return await handle_process_refund(request_data, channel_id, thread_ts, slack_user_name, current_message_full_text, slack_user_id, trigger_id)
                # elif action_id == "custom_refund_amount":
                #     return await handle_custom_refund_amount(request_data, channel_id, thread_ts, slack_user_name)
                elif action_id == "no_refund":
                    return await handle_no_refund(request_data, channel_id, thread_ts, slack_user_name, current_message_full_text, trigger_id)
                elif action_id and (action_id.startswith("restock") or action_id == "do_not_restock"):
                    return await handle_restock_inventory(request_data, action_id, channel_id, thread_ts, slack_user_name, current_message_full_text, trigger_id)
                else:
                    if not action_id:
                        raise HTTPException(status_code=400, detail="Missing action_id in request")
                    logger.warning(f"Unknown action_id: {action_id}")
                    return {"response_type": "ephemeral", "text": f"Unknown action: {action_id}"}
        
        # Return success response to Slack
        return {"text": "✅ Webhook received and logged successfully!"}
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON payload: {e}")
        print(f"❌ JSON Decode Error: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    except HTTPException:
        # Re-raise HTTPExceptions as-is to preserve status codes
        raise
    except Exception as e:
        logger.error(f"Error handling Slack interaction: {e}")
        print(f"❌ General Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/webhook")
async def handle_slack_webhook(request: Request):
    """
    Handle Slack webhook - supports both URL verification and button interactions
    This is a compatibility endpoint that delegates to the main interactions handler
    """
    try:
        # Check if this is a URL verification challenge (JSON body)
        content_type = request.headers.get("Content-Type", "")
        
        if "application/json" in content_type:
            # Handle URL verification challenge
            body = await request.json()
            if "challenge" in body:
                # Slack URL verification - echo back the challenge
                return {"challenge": body["challenge"]}
        
        # Otherwise, delegate to the main interactions handler
        # Reset request body for the interactions handler to process
        return await handle_slack_interactions(request)
        
    except HTTPException:
        # Re-raise HTTPExceptions as-is to preserve status codes
        raise
    except Exception as e:
        logger.error(f"Error handling Slack webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# === STEP 1 HANDLERS: INITIAL DECISION (Cancel Order / Proceed / Cancel & Close) ===

async def handle_cancel_order(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_id: str, slack_user_name: str, current_message_full_text: str, trigger_id: Optional[str] = None) -> Dict[str, Any]:
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
        
        # Fetch fresh order details from Shopify to get complete data
        print(f"📦 Fetching order details for: {raw_order_number}")
        order_result = orders_service.fetch_order_details_by_email_or_order_name(order_name=raw_order_number)
        print(f"📦 Order fetch result: success={order_result.get('success')}, keys={list(order_result.keys())}")
        
        if not order_result["success"]:
            logger.error(f"Failed to fetch order details for {raw_order_number}: {order_result['message']}")
            print(f"❌ Order fetch failed: {order_result.get('message', 'Unknown error')}")
            error_message = f"❌ Failed to fetch order details: {order_result['message']}"
            update_slack_on_shopify_failure(
                message_ts=thread_ts,
                error_message=error_message,
                operation_name="order fetch (cancel order)"
            )
            return {}
        
        shopify_order_data = order_result["data"]
        order_id = shopify_order_data.get("id", "")
        print(f"📦 Order data keys: {list(shopify_order_data.keys()) if shopify_order_data else 'None'}")
        print(f"📦 Extracted order ID: '{order_id}'")
        
        # Calculate fresh refund amount
        refund_calculation = orders_service.calculate_refund_due(shopify_order_data, refund_type)
        
        # Cancel order in Shopify
        print(f"🛑 Attempting to cancel order ID: '{order_id}'")
        cancel_result = {"success": True, "message": "Skipped cancellation in debug mode"} if settings.is_debug_mode else orders_service.cancel_order(order_id)
        print(f"🛑 Cancel result: {cancel_result}")
        
        if cancel_result["success"]:
            # Create requestor name display
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
            
            # Extract Google Sheets link from current message
            sheet_link = extract_sheet_link(current_message_full_text)
            print(f"🔗 Extracted sheet link for cancel_order: {sheet_link}")
            
            # Create refund decision message
            from services.slack.message_builder import SlackMessageBuilder
            message_builder = SlackMessageBuilder({})
            refund_message = message_builder.create_refund_decision_message(
                order_data, refund_type, "@channel", 
                sheet_link=sheet_link,
                order_cancelled=True, 
                slack_user=f"<@{slack_user_id}>",
                original_timestamp=request_submitted_at
            )
            
            # ✅ Update Slack message ONLY on Shopify success
            update_slack_on_shopify_success(
                message_ts=thread_ts,
                success_message=refund_message["text"],
                action_buttons=refund_message["action_buttons"]
            )
            
            logger.info(f"Order {raw_order_number} cancelled successfully")
        else:
            # 🚨 Handle Shopify cancellation failure with detailed error logging
            shopify_error = cancel_result.get('message', 'Unknown error')
            
            # Print detailed error information for debugging
            print(f"\n🚨 === SHOPIFY ORDER CANCELLATION FAILED ===")
            print(f"📋 Order: {raw_order_number}")
            print(f"🔗 Order ID: {order_id}")
            print(f"👤 User: {slack_user_name} ({slack_user_id})")
            print(f"❌ Shopify Error: {shopify_error}")
            print(f"📝 Full cancel_result: {cancel_result}")
            print("=== END SHOPIFY CANCELLATION FAILURE ===\n")
            
            # Log detailed error for server logs
            logger.error(f"🚨 SHOPIFY ORDER CANCELLATION FAILED:")
            logger.error(f"   Order: {raw_order_number}")
            logger.error(f"   Order ID: {order_id}")
            logger.error(f"   User: {slack_user_name}")
            logger.error(f"   Shopify Error: {shopify_error}")
            logger.error(f"   Full Result: {cancel_result}")
            
            # Send modal error dialog to the user who clicked the button
            raw_response = cancel_result.get("raw_response", "No response data")
            shopify_errors = cancel_result.get("shopify_errors", [])
            
            modal_error_message = f"Order cancellation failed for {raw_order_number}.\n\n**Shopify Error:**\n{shopify_error}"
            
            if shopify_errors:
                modal_error_message += f"\n\n**Shopify Error Details:**\n{shopify_errors}"
            
            modal_error_message += f"\n\n**Raw Shopify Response:**\n{raw_response}"
            
            modal_error_message += f"\n\nThis often happens when:\n• Order is already cancelled\n• Order is already fulfilled\n• Order has refunds or returns\n• Payment gateway restrictions"
            
            if trigger_id:
                send_modal_error_to_user(
                    trigger_id=trigger_id,
                    error_message=modal_error_message,
                    operation_name="Order Cancellation"
                )
            else:
                # Fallback to ephemeral message if trigger_id not available
                send_ephemeral_error_to_user(
                    channel_id=channel_id,
                    user_id=slack_user_id,
                    error_message=modal_error_message,
                    operation_name="Order Cancellation"
                )
            
            # Update main message if configured to do so
            error_message = f"❌ Failed to cancel order {raw_order_number}: {shopify_error}"
            update_slack_on_shopify_failure(
                message_ts=thread_ts,
                error_message=error_message,
                operation_name="order cancellation"
            )
        
        return {}
    except Exception as e:
        logger.error(f"Error canceling order: {e}")
        error_message = f"❌ Error canceling order: {str(e)}"
        update_slack_on_shopify_failure(
            message_ts=thread_ts,
            error_message=error_message,
            operation_name="order cancellation (exception)"
        )
        return {}
    

async def handle_proceed_without_cancel(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_id: str, slack_user_name: str, current_message_full_text: str, trigger_id: Optional[str] = None) -> Dict[str, Any]:
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
        
        # Fetch fresh order details from Shopify to get complete data
        order_result = orders_service.fetch_order_details_by_email_or_order_name(order_name=raw_order_number)
        if not order_result["success"]:
            logger.error(f"Failed to fetch order details for {raw_order_number}: {order_result['message']}")
            error_message = f"❌ Failed to fetch order details: {order_result['message']}"
            update_slack_on_shopify_failure(
                message_ts=thread_ts,
                error_message=error_message,
                operation_name="order fetch (proceed without cancel)"
            )
            return {}
        
        shopify_order_data = order_result["data"]
        
        # Calculate fresh refund amount
        refund_calculation = orders_service.calculate_refund_due(shopify_order_data, refund_type)
        
        # Create requestor name display
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
        
        # Extract Google Sheets link from current message
        sheet_link = extract_sheet_link(current_message_full_text)
        print(f"🔗 Extracted sheet link for proceed_without_cancel: {sheet_link}")
        
        # Create refund decision message (order remains active)
        from services.slack.message_builder import SlackMessageBuilder
        message_builder = SlackMessageBuilder({})
        refund_message = message_builder.create_refund_decision_message(
            order_data, refund_type, "@channel", 
            sheet_link=sheet_link,
            order_cancelled=False, 
            slack_user=f"<@{slack_user_id}>",
            original_timestamp=request_submitted_at
        )
        
        # Update Slack message using controlled mechanism
        update_slack_on_shopify_success(
            message_ts=thread_ts,
            success_message=refund_message["text"],
            action_buttons=refund_message["action_buttons"]
        )
        
        logger.info(f"Proceeding to refund options for order {raw_order_number} (order not cancelled)")
        return {}
    except Exception as e:
        logger.error(f"Error proceeding without cancel: {e}")
        error_message = f"❌ Error proceeding: {str(e)}"
        update_slack_on_shopify_failure(
            message_ts=thread_ts,
            error_message=error_message,
            operation_name="proceed without cancel (exception)"
        )
        return {}

async def handle_cancel_and_close_request(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str, trigger_id: Optional[str] = None) -> Dict[str, Any]:
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

async def handle_process_refund(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str, current_message_full_text: str, slack_user_id: str = "", trigger_id: Optional[str] = None) -> Dict[str, Any]:
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
        
        # Make actual Shopify API call
        print(f"🏭 Making real {refund_type} API call")
        refund_result = orders_service.create_refund_or_credit(order_id, refund_amount, refund_type)
        
        # Add detailed logging for debugging
        if not refund_result["success"]:
            logger.error(f"🚨 REFUND FAILED: Order {raw_order_number}, Amount ${refund_amount}, Type: {refund_type}")
            logger.error(f"🚨 ERROR DETAILS: {refund_result.get('message', 'Unknown error')}")
        else:
            logger.info(f"✅ REFUND SUCCESS: Order {raw_order_number}, Amount ${refund_amount}, Type: {refund_type}")
        
        if refund_result["success"]:
            # Fetch fresh order details for comprehensive message
            order_result = orders_service.fetch_order_details_by_email_or_order_name(order_name=raw_order_number)
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
                    current_message_text=current_message_full_text,
                    order_id=order_id
                )
                
                # ✅ Update Slack message ONLY on Shopify success
                print(f"🔄 Attempting to update Slack message with {len(success_message_data['action_buttons'])} buttons")
                update_slack_on_shopify_success(
                    message_ts=thread_ts,
                    success_message=success_message_data["text"],
                    action_buttons=success_message_data["action_buttons"]
                )
            else:
                # Fallback if order fetch fails
                status = "cancelled" if order_cancelled else "active"
                message = f"✅ *Refund processed by {slack_user_name}*\n\nOrder {raw_order_number} ({status}) - ${refund_amount:.2f} {refund_type} processed successfully."
                
                # ✅ Update Slack with fallback success message
                update_slack_on_shopify_success(
                    message_ts=thread_ts,
                    success_message=message,
                    action_buttons=[]
                )
        else:
            # 🚨 Handle Shopify refund failure with detailed error logging
            shopify_error = refund_result.get('message', 'Unknown error')
            
            # Print detailed error information for debugging
            print(f"\n🚨 === SHOPIFY {refund_type.upper()} FAILED ===")
            print(f"📋 Order: {raw_order_number}")
            print(f"🔗 Order ID: {order_id}")
            print(f"💰 Amount: ${refund_amount:.2f}")
            print(f"🏷️ Type: {refund_type}")
            print(f"👤 User: {slack_user_name} ({slack_user_id})")
            print(f"❌ Shopify Error: {shopify_error}")
            print(f"📝 Full refund_result: {refund_result}")
            print(f"=== END SHOPIFY {refund_type.upper()} FAILURE ===\n")
            
            # Log detailed error information for server logs
            logger.error(f"🚨 SHOPIFY {refund_type.upper()} FAILED:")
            logger.error(f"   Order: {raw_order_number}")
            logger.error(f"   Order ID: {order_id}")
            logger.error(f"   Amount: ${refund_amount}")
            logger.error(f"   Type: {refund_type}")
            logger.error(f"   User: {slack_user_name}")
            logger.error(f"   Shopify Error: {shopify_error}")
            logger.error(f"   Full Result: {refund_result}")
            
            # Send modal error dialog to the user who clicked the button (if available)
            if slack_user_id:
                modal_error_message = f"{refund_type.title()} failed for {raw_order_number}.\n\n**Shopify Error:**\n{shopify_error}\n\nAmount: ${refund_amount:.2f}\nType: {refund_type}\n\nCommon causes:\n• Order already refunded\n• Insufficient funds captured\n• Payment gateway restrictions\n• Order too old for refund"
                
                if trigger_id:
                    send_modal_error_to_user(
                        trigger_id=trigger_id,
                        error_message=modal_error_message,
                        operation_name=f"{refund_type.title()} Processing"
                    )
                else:
                    # Fallback to ephemeral message if trigger_id not available
                    send_ephemeral_error_to_user(
                        channel_id=channel_id,
                        user_id=slack_user_id,
                        error_message=modal_error_message,
                        operation_name=f"{refund_type.title()} Processing"
                    )
            
            # Update main message if configured to do so
            error_message = f"❌ *{refund_type.title()} failed*\n\nError: {shopify_error}\n\nOrder: {raw_order_number}\nAmount: ${refund_amount:.2f}\nType: {refund_type}"
            
            update_slack_on_shopify_failure(
                message_ts=thread_ts,
                error_message=error_message,
                operation_name=f"{refund_type} creation"
            )
        
        return {}
    except Exception as e:
        logger.error(f"Error processing refund: {e}")
        error_message = f"❌ Error processing refund: {str(e)}"
        update_slack_on_shopify_failure(
            message_ts=thread_ts,
            error_message=error_message,
            operation_name="refund processing (exception)"
        )
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

async def handle_no_refund(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str, current_message_full_text: str, trigger_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Handle no refund button click (Step 2)
    """
    print(f"\n🚫 === NO REFUND ACTION ===")
    print(f"👤 User: {slack_user_name}")
    print(f"📋 Request Data: {request_data}")
    print(f"📍 Channel: {channel_id}, Thread: {thread_ts}")
    print(f"📝 Current message text length: {len(current_message_full_text)}")
    print(f"📝 Current message preview: {current_message_full_text[:200]}...")
    print("=== END NO REFUND ===\n")
    
    try:
        raw_order_number = request_data.get("rawOrderNumber", "")
        order_cancelled = request_data.get("orderCancelled", "False").lower() == "true"
        
        print(f"🏭 Closing refund request (no API calls needed)")
        
        # Fetch fresh order details for comprehensive message
        order_result = orders_service.fetch_order_details_by_email_or_order_name(order_name=raw_order_number)
        if order_result["success"]:
            shopify_order_data = order_result["data"]
            
            # Build comprehensive no refund message matching Google Apps Script format
            try:
                no_refund_message_data = build_comprehensive_no_refund_message(
                    order_data=shopify_order_data,
                    raw_order_number=raw_order_number,
                    order_cancelled=order_cancelled,
                    processor_user=slack_user_name,
                    thread_ts=thread_ts,
                    current_message_full_text=current_message_full_text
                )
                
                print(f"📝 Built message text length: {len(no_refund_message_data['text'])}")
                print(f"🔘 Built {len(no_refund_message_data['action_buttons'])} action buttons")
                
                update_slack_on_shopify_success(
                    message_ts=thread_ts,
                    success_message=no_refund_message_data["text"],
                    action_buttons=no_refund_message_data["action_buttons"]
                )
                
            except Exception as build_error:
                print(f"❌ Error building no refund message: {str(build_error)}")
                logger.error(f"Error building no refund message: {str(build_error)}")
                # Fall back to simple message
                status = "cancelled" if order_cancelled else "active"
                simple_message = f"🚫 *No refund by {slack_user_name}*\n\nOrder {raw_order_number} ({status}) - Request closed without refund."
                
                update_slack_on_shopify_success(
                    message_ts=thread_ts,
                    success_message=simple_message,
                    action_buttons=[]
                )
        else:
            # Fallback if order fetch fails
            status = "cancelled" if order_cancelled else "active"
            message = f"🚫 *No refund by {slack_user_name}*\n\nOrder {raw_order_number} ({status}) - Request closed without refund."
            
            try:
                update_slack_on_shopify_success(
                    message_ts=thread_ts,
                    success_message=message,
                    action_buttons=[]
                )
            except Exception as e:
                print(f"❌ No refund message update failed: {str(e)}")
        
        return {}
    except Exception as e:
        logger.error(f"Error handling no refund: {e}")
        error_message = f"❌ Error: {str(e)}"
        update_slack_on_shopify_failure(
            message_ts=thread_ts,
            error_message=error_message,
            operation_name="no refund (exception)"
        )
        return {}

# === LEGACY/SUPPORT HANDLERS ===

async def handle_restock_inventory(request_data: Dict[str, str], action_id: str, channel_id: str, thread_ts: str, slack_user_name: str, current_message_full_text: str, trigger_id: Optional[str] = None) -> Dict[str, Any]:
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
        
        # Debug: Print the extracted values
        print(f"🔍 EXTRACTED VALUES:")
        print(f"   order_id: '{order_id}'")
        print(f"   raw_order_number: '{raw_order_number}'") 
        print(f"   variant_id: '{variant_id}'")
        print(f"   variant_name: '{variant_name}'")
        
        # If variant_id is empty, try to extract from action_id
        if not variant_id and action_id.startswith("restock_"):
            # Extract variant ID from action_id like: restock_gid___shopify_ProductVariant_41791409848414
            action_variant_part = action_id.replace("restock_", "")
            if action_variant_part.startswith("gid___shopify_ProductVariant_"):
                # Convert back to proper GID format
                variant_id = action_variant_part.replace("___", "://").replace("_", "/")
                print(f"✅ Recovered variant_id from action_id: '{variant_id}'")
        
        # If variant_name is still empty, use a fallback
        if not variant_name:
            variant_name = "Unknown Variant"
        
        # Extract Google Sheets link and current message data
        sheet_url = extract_sheet_link(current_message_full_text)
        sheet_link = f"🔗 <{sheet_url}|View Request in Google Sheets>" if sheet_url else "🔗 View Request in Google Sheets"
        
        # Fetch fresh order details for comprehensive message (like no-refund handler)
        order_data = None
        if raw_order_number:
            order_result = orders_service.fetch_order_details_by_email_or_order_name(order_name=raw_order_number)
            if order_result["success"]:
                order_data = order_result["data"]
                print(f"✅ Fetched order data for completion message")
            else:
                print(f"⚠️ Could not fetch order data for completion message: {order_result.get('error', 'Unknown error')}")
        
        # Build the final completion message preserving who did what
        completion_message = build_completion_message(
            current_message_full_text=current_message_full_text,
            action_id=action_id,
            variant_name=variant_name,
            restock_user=slack_user_name,
            sheet_link=sheet_link,
            raw_order_number=raw_order_number,
            order_data=order_data
        )
        
        # Validate that we have the required data
        if action_id != "do_not_restock" and not variant_id:
            error_message = f"Invalid restock request: missing variant ID.\n\nAction ID: {action_id}\nParsed data: {request_data}\n\nThis usually indicates a button formatting issue."
            
            if trigger_id:
                send_modal_error_to_user(
                    trigger_id=trigger_id,
                    error_message=error_message,
                    operation_name="Inventory Restock"
                )
            else:
                logger.error(f"❌ {error_message}")
            
            return {}

        if action_id != "do_not_restock":
            # Handle actual inventory restocking
            print(f"🏭 Making real inventory API call for variant: {variant_id}")
            
            # Make actual Shopify inventory adjustment API call
            inventory_result = await adjust_shopify_inventory(variant_id, delta=1)
            
            if not inventory_result.get("success", False):
                # If inventory restock fails, show modal instead of updating message
                error_msg = inventory_result.get("message", "Unknown error")
                modal_error_message = f"Inventory restock failed for {variant_name}.\n\n**Shopify Error:**\n{error_msg}\n\nCommon causes:\n- Invalid variant ID\n- Inventory item not found\n- Location restrictions\n- Insufficient permissions"
                
                if trigger_id:
                    send_modal_error_to_user(
                        trigger_id=trigger_id,
                        error_message=modal_error_message,
                        operation_name="Inventory Restock"
                    )
                else:
                    # Fallback to console log if no trigger_id
                    logger.error(f"❌ Inventory restock failed: {modal_error_message}")
                
                # Return early - don't update the message
                return {}
        
        # ✅ Update Slack message ONLY on success
        update_slack_on_shopify_success(
            message_ts=thread_ts,
            success_message=completion_message,
            action_buttons=[]  # No more buttons - process is complete
        )
        
        return {}
        
    except Exception as e:
        logger.error(f"Error handling restock inventory: {e}")
        error_message = f"❌ Error processing inventory restock: {str(e)}"
        
        # Show modal for exceptions too
        if trigger_id:
            send_modal_error_to_user(
                trigger_id=trigger_id,
                error_message=f"An unexpected error occurred during inventory restock.\n\n**Error:**\n{str(e)}\n\nPlease try again or contact support if the issue persists.",
                operation_name="Inventory Restock"
            )
        else:
            # Fallback to console log if no trigger_id
            logger.error(f"❌ Inventory restock exception: {error_message}")
        
        # Don't update the message on exceptions - just show modal
        return {}

# Legacy handler for backwards compatibility
async def handle_approve_refund(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str) -> Dict[str, Any]:
    """Legacy handler - now redirects to process_refund"""
    print(f"\n⚠️ === LEGACY APPROVE REFUND (redirecting to process_refund) ===")
    return await handle_process_refund(request_data, channel_id, thread_ts, slack_user_name, "", "")

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
                                      current_message_text: str, order_id: str = "", is_debug_mode: bool = False) -> Dict[str, Any]:
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
        message_text = ""
        
        # Cancellation message (if order was cancelled)
        if order_cancelled:
            message_text += f"✅ *Cancellation Request for Order {order_url} for {customer_email} has been processed by @{processor_user}*\n"
        
        # Refund processing message
        refund_action = "credit" if refund_type == "credit" else "refund"
        message_text += f"✅ *Request to provide a ${refund_amount:.2f} {refund_action} for Order {order_url} has been processed by @{processor_user}*\n"
        
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
                    "text": {"type": "plain_text", "text": button_text},
                    "action_id": f"restock_{clean_variant_id}",
                    "value": f"orderId={order_id}|variantId={variant_id}|variantName={clean_variant_name}",
                                         "style": "primary",
                     "confirm": {
                         "title": {"type": "plain_text", "text": "Confirm Restock"},
                         "text": {"type": "plain_text", "text": f"Restock inventory to {clean_variant_name}?"},
                         "confirm": {"type": "plain_text", "text": "Yes, restock"},
                         "deny": {"type": "plain_text", "text": "Cancel"}
                     },
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
        
        # Always add "Do Not Restock - All Done!" button (no style = default gray)
        restock_buttons.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "✅ Do Not Restock - All Done!"},
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
        
        return {
            "text": f"✅ *Refund processed by @{processor_user}*\n\nOrder {raw_order_number} ({status}) - ${refund_amount:.2f} {refund_type} processed successfully.",
            "action_buttons": []
        }

def build_completion_message(current_message_full_text: str, action_id: str, variant_name: str, 
                            restock_user: str, sheet_link: str, raw_order_number: str,
                            order_data: Optional[Dict[str, Any]] = None) -> str:
    """Build final completion message preserving who processed cancellation, refund, and inventory"""
    try:
        # Parse the current message to extract the completion state
        
        # Build order URL if we have order data
        order_url = raw_order_number  # Default fallback
        customer_name = "Unknown Customer"
        
        if order_data:
            order_id = order_data.get("id", "")
            if order_id and "Order/" in order_id:
                order_numeric_id = order_id.split("/")[-1]
                order_url = f"<https://admin.shopify.com/store/09fe59-3/orders/{order_numeric_id}|{raw_order_number}>"
            
            # Extract customer name
            customer = order_data.get("customer", {})
            first_name = customer.get("firstName", "")
            last_name = customer.get("lastName", "")
            
            if first_name or last_name:
                customer_name = f"{first_name} {last_name}".strip()
            else:
                # Fallback to email-based name if no firstName/lastName
                customer_email = customer.get("email", "")
                if customer_email:
                    name_part = customer_email.split("@")[0]
                    name_parts = name_part.replace(".", " ").replace("_", " ").split()
                    customer_name = " ".join([part.capitalize() for part in name_parts])
        
        # Build product info if we have product data
        product_info = ""
        if order_data and order_data.get("product"):
            product = order_data["product"]
            product_title = product.get("title", "Unknown Product")
            product_id = product.get("productId") or product.get("id", "")
            
            if product_id:
                from services.slack.message_builder import SlackMessageBuilder
                message_builder = SlackMessageBuilder({})
                product_url = message_builder.get_product_url(product_id)
                product_info = f"\n📦 *Product*: <{product_url}|{product_title}>\n"
            else:
                product_info = f"\n📦 *Product*: {product_title}\n"
        
        # Build the new completion message instead of modifying existing
        completion_message = f"✅ *Request for Order {order_url} for {customer_name} has been completed by @{restock_user}.*\n"
        
        # Add product info after the no refund line
        if product_info:
            completion_message += product_info
        
        # Add inventory status based on action
        if action_id == "do_not_restock":
            completion_message += f"\n🚫 *No inventory was restocked - Process completed by @{restock_user}*\n"
        else:
            # Extract variant name from action_id if not provided
            if not variant_name:
                variant_name = action_id.replace("restock_", "").replace("_", " ").title()
            
            completion_message += f"✅ *Inventory restocked to {variant_name} successfully by @{restock_user}*\n"
        
        # Build waitlist link if we have product data
        waitlist_link = ""
        if order_data and order_data.get("product"):
            product = order_data["product"]
            product_id = product.get("productId") or product.get("id", "")
            if product_id:
                # Extract numeric product ID for waitlist URL
                if "Product/" in product_id:
                    product_numeric_id = product_id.split("/")[-1]
                    waitlist_url = f"https://bigapplerecsports.com/products/{product_numeric_id}?variant=waitlist"
                    waitlist_link = f"\n🔗 <{waitlist_url}|Open Waitlist to let someone in>\n"
        
        # Add waitlist link and Google Sheets link
        completion_message += f"{sheet_link}\n\n"
        if waitlist_link:
            completion_message += waitlist_link
        
        
        return completion_message
        
    except Exception as e:
        print(f"❌ Error building completion message: {e}")
        # Fallback message
        status = "completed" if action_id == "do_not_restock" else f"inventory restocked to {variant_name}"
        return f"✅ *Refund request {status} by @{restock_user}*\n\n{sheet_link}"

async def adjust_shopify_inventory(variant_id: str, delta: int = 1) -> Dict[str, Any]:
    """Adjust Shopify inventory using the GraphQL API"""
    try:
        print(f"🏭 Making real inventory adjustment for variant {variant_id}")
        
        # Step 1: Fetch variant details to get inventory item ID (like Google Apps Script)
        variant_query = {
            "query": """
                query getVariant($id: ID!) {
                    productVariant(id: $id) {
                        id
                        title
                        inventoryItem {
                            id
                        }
                    }
                }
            """,
            "variables": {
                "id": variant_id
            }
        }
        
        print(f"🔍 Fetching variant details for {variant_id}")
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": settings.shopify_token
        }
        
        variant_response = requests.post(
            settings.graphql_url,
            headers=headers,
            json=variant_query,
            timeout=30
        )
        
        if variant_response.status_code != 200:
            error_msg = f"Failed to fetch variant details: HTTP {variant_response.status_code}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        
        variant_result = variant_response.json()
        
        if "errors" in variant_result:
            error_msg = f"GraphQL errors fetching variant: {variant_result['errors']}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        
        variant_data = variant_result.get("data", {}).get("productVariant")
        if not variant_data or not variant_data.get("inventoryItem", {}).get("id"):
            error_msg = f"No inventory item found for variant {variant_id}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        
        inventory_item_id = variant_data["inventoryItem"]["id"]
        variant_title = variant_data.get("title", "Unknown")
        print(f"✅ Found inventory item ID: {inventory_item_id} for variant: {variant_title}")
        
        # Step 2: Adjust inventory using the correct inventory item ID
        inventory_mutation = {
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
                            "inventoryItemId": inventory_item_id,
                            "locationId": "gid://shopify/Location/61802217566"
                        }
                    ]
                }
            }
        }
        
        # Make the actual GraphQL API call to Shopify
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": settings.shopify_token
        }
        
        print(f"🏭 Sending inventory adjustment mutation to {settings.graphql_url}")
        response = requests.post(
            settings.graphql_url,
            headers=headers,
            json=inventory_mutation,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Check for GraphQL errors
            if "errors" in result:
                error_msg = f"GraphQL errors: {result['errors']}"
                logger.error(f"Shopify GraphQL errors during inventory adjustment: {error_msg}")
                return {"success": False, "message": error_msg}
            
            # Check for user errors in the mutation response
            data = result.get("data", {})
            inventory_adjust = data.get("inventoryAdjustQuantities", {})
            user_errors = inventory_adjust.get("userErrors", [])
            
            if user_errors:
                error_msg = f"Inventory adjustment user errors: {user_errors}"
                logger.error(f"Shopify inventory adjustment user errors: {error_msg}")
                return {"success": False, "message": error_msg}
            
            # Success case
            adjustment_group = inventory_adjust.get("inventoryAdjustmentGroup", {})
            logger.info(f"✅ Successfully adjusted inventory for variant {variant_id} by {delta}")
            return {
                "success": True, 
                "message": "Inventory adjusted successfully",
                "adjustment_group": adjustment_group
            }
            
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            logger.error(f"Failed to adjust Shopify inventory: {error_msg}")
            return {"success": False, "message": error_msg}
        
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
                                         thread_ts: str, 
                                         current_message_full_text: str) -> Dict[str, Any]:
    """Build comprehensive no refund message matching Google Apps Script format"""
    try:
        print(f"\n🔍 === BUILD NO REFUND MESSAGE DEBUG ===")
        print(f"📦 Raw order data keys: {list(order_data.keys())}")
        print(f"📦 Order data preview: {str(order_data)[:500]}...")
        
        # Extract data from order
        order_id = order_data.get("id", "")
        customer = order_data.get("customer", {})
        product = order_data.get("product", {})
        
        print(f"🔗 Order ID: {order_id}")
        print(f"👤 Customer: {customer}")
        print(f"🎯 Product keys: {list(product.keys()) if product else 'None'}")
        print(f"🎯 Product title: {product.get('title', 'None') if product else 'No product'}")
        
        # Get customer name from email if available
        customer_email = customer.get("email", "")
        customer_name = customer_email.split("@")[0].replace(".", " ").title() if customer_email else "Unknown Customer"
        
        # Build order URL with link - extract numeric ID from GraphQL ID
        order_numeric_id = ""
        if order_id and "Order/" in order_id:
            order_numeric_id = order_id.split("/")[-1]
        order_url = f"<https://admin.shopify.com/store/09fe59-3/orders/{order_numeric_id}|{raw_order_number}>" if order_numeric_id else raw_order_number
        print(f"🔗 Built order URL: {order_url}")
        
        # Build comprehensive message
        message_text = ""
        
        # Cancellation message (if order was cancelled)
        if order_cancelled:
            message_text += f"✅ *Cancellation Request for Order {order_url} for {customer_email} has been processed by @{processor_user}*\n\n"
        
        # No refund message
        message_text += f"🚫 *No refund provided for Order {order_url} - Request closed by @{processor_user}*\n\n"
        
        # Get product info - USE ACTUAL PRODUCT DATA, not extracted from message
        product_title = product.get("title", "Unknown Product")
        print(f"🎯 Using actual product title: {product_title}")
        
        # Extract season start info from current message (but don't use its product title)
        season_info = extract_season_start_info(current_message_full_text)
        season_start = season_info.get("season_start", "Unknown")
        
        # If season start not found in message, try to extract from product description
        if season_start == "Unknown" or not season_start:
            try:
                description_html = product.get("descriptionHtml", "")
                if description_html:
                    print(f"🔍 Trying to extract season start from description: {description_html}")
                    
                    import re
                    from datetime import datetime
                    
                    # Look for various date patterns in the description
                    date_patterns = [
                        # Pattern for "Season Dates: 7/9/25 – 8/27/25"
                        r"Season dates?:\s*(\d{1,2}/\d{1,2}/\d{2,4})",
                        # Pattern for plain dates like "7/9/25 – 8/27/25"
                        r"(\d{1,2}/\d{1,2}/\d{2,4})\s*[–-]\s*\d{1,2}/\d{1,2}/\d{2,4}",
                        # Legacy patterns for full month names
                        r"Season dates?:\s*([A-Za-z]+ \d{1,2}, \d{4})",
                        r"Start date?:\s*([A-Za-z]+ \d{1,2}, \d{4})",
                        r"([A-Za-z]+ \d{1,2}, \d{4})\s*-\s*[A-Za-z]+ \d{1,2}, \d{4}",
                    ]
                    
                    for i, pattern in enumerate(date_patterns):
                        match = re.search(pattern, description_html, re.IGNORECASE)
                        if match:
                            date_str = match.group(1)
                            try:
                                # Handle different date formats
                                if i < 2:  # MM/DD/YY or MM/DD/YYYY formats
                                    # Already in the right format, just ensure YY format
                                    if '/' in date_str:
                                        parts = date_str.split('/')
                                        if len(parts) == 3:
                                            month, day, year = parts
                                            # Convert YYYY to YY if needed
                                            if len(year) == 4:
                                                year = year[-2:]
                                            season_start = f"{month.zfill(2)}/{day.zfill(2)}/{year}"
                                        else:
                                            season_start = date_str
                                    else:
                                        season_start = date_str
                                    print(f"✅ Extracted season start from description (format {i}): {season_start}")
                                    break
                                else:  # Full month name formats
                                    # Parse the date and format it as MM/DD/YY
                                    parsed_date = datetime.strptime(date_str, "%B %d, %Y")
                                    season_start = parsed_date.strftime("%m/%d/%y")
                                    print(f"✅ Extracted season start from description (format {i}): {season_start}")
                                    break
                            except ValueError as ve:
                                print(f"⚠️ Could not parse date '{date_str}' with pattern {i}: {ve}")
                                continue
                                
            except Exception as e:
                print(f"⚠️ Could not extract season start from description: {e}")
        
        # Build product URL link
        product_id = product.get("productId") or product.get("id", "")
        print(f"🎯 Product ID for URL: {product_id}")
        print(f"🎯 Product title for link: {product_title}")
        
        if product_id:
            from services.slack.message_builder import SlackMessageBuilder
            message_builder = SlackMessageBuilder({})
            product_url = message_builder.get_product_url(product_id)
            product_title_with_link = f"<{product_url}|{product_title}>"
            print(f"🎯 Built product URL: {product_url}")
            print(f"🎯 Product with link: {product_title_with_link}")
        else:
            product_title_with_link = product_title
            print(f"⚠️ No product ID found, using plain title: {product_title_with_link}")
        
        message_text += f"📦 *Season Start Date for {product_title_with_link} is {season_start}.*\n\n"
        print(f"🔍 Final season start line: 📦 *Season Start Date for {product_title_with_link} is {season_start}.*")
        print(f"=== END BUILD NO REFUND MESSAGE DEBUG ===\n")
        message_text += "*Current Inventory:*\n\n"
        
        # Fetch current inventory
        variants = product.get("variants", [])
        for variant in variants:
            variant_name = variant.get("variantName", "Unknown Variant")
            inventory = variant.get("inventory", 0)
            message_text += f"• *{variant_name}*: {inventory} spots available\n\n"
        
        # Extract Google Sheets link from current message
        sheet_url = extract_sheet_link(current_message_full_text)
        sheet_link = f"🔗 <{sheet_url}|View Request in Google Sheets>" if sheet_url else "🔗 View Request in Google Sheets"
        
        message_text += f"\n{sheet_link}\n"

        # Create restock buttons for each variant (same as refund case)
        restock_buttons = []
        for variant in variants:
            variant_name = variant.get("variantName", "Unknown Variant")
            variant_id = variant.get("variantId", "")
            if variant_id:
                # Clean variant ID for action_id (only alphanumeric and underscores)
                clean_variant_id = ''.join(c if c.isalnum() or c == '_' else '_' for c in str(variant_id))
                # Truncate button text to stay under 75 character limit
                button_text = f"📦 Restock {variant_name}"
                if len(button_text) > 70:
                    button_text = f"📦 Restock {variant_name[:55]}..."
                
                # Clean variant name for value (no pipes or special chars that could break parsing)
                clean_variant_name = variant_name.replace("|", "-").replace("=", "-")
                
                restock_buttons.append({
                    "type": "button",
                    "text": {"type": "plain_text", "text": button_text},
                    "action_id": f"restock_{clean_variant_id}",
                    "value": f"orderId={order_id}|variantId={variant_id}|variantName={clean_variant_name}",
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
            "value": f"orderId={order_id}|rawOrderNumber={raw_order_number}"
        })
        
        return {
            "text": message_text,
            "action_buttons": restock_buttons,
            "slack_text": message_text
        }
        
    except Exception as e:
        logger.error(f"Error building comprehensive no refund message: {str(e)}")
        # Fallback to simple message
        status = "cancelled" if order_cancelled else "active"
        
        return {
            "text": f"🚫 *No refund by @{processor_user}*\n\nOrder {raw_order_number} ({status}) - Request closed without refund.",
            "action_buttons": []
        }

@router.get("/health")
async def health_check():
    """Health check endpoint for the Slack service"""
    return {"status": "healthy", "service": "slack"} 