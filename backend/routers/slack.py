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

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/slack", tags=["slack"])

orders_service = OrdersService()
slack_service = SlackService()


# Note: parse_original_message_data function removed - data now preserved in button values

@router.post("/interactions")
async def handle_slack_interactions(request: Request):
    """
    Handle Slack button interactions and other interactive components
    This endpoint receives webhooks when users click buttons in Slack messages
    """
    try:
        # Get raw request data
        body = await request.body()
        
        # Get headers for verification
        timestamp = request.headers.get("X-Slack-Request-Timestamp")
        signature = request.headers.get("X-Slack-Signature")
        content_type = request.headers.get("Content-Type")
        
        print(f"\n🔍 === SLACK INTERACTIONS ROUTER ===")
        # print(f"📋 Headers:")
        # print(f"   X-Slack-Request-Timestamp: {timestamp}")
        # print(f"   X-Slack-Signature: {signature}")
        # print(f"   Content-Type: {content_type}")
        # print(f"   User-Agent: {request.headers.get('User-Agent', 'Not provided')}")
        
        # print(f"📦 Raw Body ({len(body)} bytes):")
        # body_str = body.decode('utf-8', errors='replace')
        # print(f"   {body_str}")
        
        # Verify signature if present
        if timestamp and signature:
            signature_valid = slack_service.verify_slack_signature(body, timestamp, signature)
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
        
        # print("=== END DEBUG ===\n")
        
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
                request_data = slack_service.parse_button_value(action_value)
                
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
                current_message_full_text = slack_service.extract_text_from_blocks(current_message_blocks)
                
                # If blocks extraction fails, fall back to the simple text field
                if not current_message_full_text and current_message_text:
                    current_message_full_text = current_message_text
                    print(f"⚠️ Using fallback message text since blocks extraction failed")
                
                print(f"\n📨 === SLACK MESSAGE DEBUG ===")
                print(f"📝 Extracted current_message_text length: {len(current_message_text)}")
                print(f"📝 Extracted blocks count: {len(current_message_blocks)}")
                print(f"📝 Extracted current_message_full_text length: {len(current_message_full_text)}")
                print(f"📝 Current message full text: {current_message_full_text[:500]}...")
                print(f"📝 Blocks structure: {current_message_blocks}")
                print(f"🔘 Action ID: {action_id}")
                print("=== END SLACK MESSAGE DEBUG ===\n")
                
                # === STEP 1 HANDLERS: INITIAL DECISION (Cancel Order / Proceed Without Canceling) ===
                if action_id == "cancel_order":
                    return await slack_service.handle_cancel_order(request_data, channel_id, thread_ts, slack_user_id, slack_user_name, current_message_full_text, trigger_id)
                elif action_id == "proceed_without_cancel":
                    return await slack_service.handle_proceed_without_cancel(request_data, channel_id, thread_ts, slack_user_id, slack_user_name, current_message_full_text, trigger_id)
                
                # === STEP 2 HANDLERS: REFUND DECISION (Process / Custom / No Refund) ===   
                elif action_id == "process_refund":
                    return await slack_service.handle_process_refund(request_data, channel_id, thread_ts, slack_user_name, current_message_full_text, slack_user_id, trigger_id)
                # elif action_id == "custom_refund_amount":
                #     return await handle_custom_refund_amount(request_data, channel_id, thread_ts, slack_user_name)
                elif action_id == "no_refund":
                    return await slack_service.handle_no_refund(request_data, channel_id, thread_ts, slack_user_name, current_message_full_text, trigger_id)
                
                # === STEP 3 HANDLERS: RESTOCK INVENTORY (Restock / Do Not Restock) ===
                elif action_id and (action_id.startswith("restock") or action_id == "do_not_restock"):
                    return await slack_service.handle_restock_inventory(request_data, action_id, channel_id, thread_ts, slack_user_name, current_message_full_text, trigger_id)
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
        print(f"\n🔍 === SLACK WEBHOOK ROUTER ===")
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





# async def handle_cancel_and_close_request(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str, trigger_id: Optional[str] = None) -> Dict[str, Any]:
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



# === LEGACY/SUPPORT HANDLERS ===

# async def handle_restock_inventory(request_data: Dict[str, str], action_id: str, channel_id: str, thread_ts: str, slack_user_name: str, current_message_full_text: str, trigger_id: Optional[str] = None) -> Dict[str, Any]:
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
        completion_message = build_completion_message_after_restocking(
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
# async def handle_approve_refund(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str) -> Dict[str, Any]:
    """Legacy handler - now redirects to process_refund"""
    print(f"\n⚠️ === LEGACY APPROVE REFUND (redirecting to process_refund) ===")
    return await slack_service.handle_process_refund(request_data, channel_id, thread_ts, slack_user_name, "", "")

# Legacy handler for backwards compatibility  
# async def handle_custom_amount_request(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str) -> Dict[str, Any]:
#     """Legacy handler - now redirects to custom_refund_amount"""
#     print(f"\n⚠️ === LEGACY CUSTOM AMOUNT (redirecting to custom_refund_amount) ===")
#     return await handle_custom_refund_amount(request_data, channel_id, thread_ts, slack_user_name)

# Legacy handler for backwards compatibility
# async def handle_cancel_request(request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str) -> Dict[str, Any]:
#     """Legacy handler - now redirects to cancel_and_close_request"""
#     print(f"\n⚠️ === LEGACY CANCEL REQUEST (redirecting to cancel_and_close_request) ===")
#     return await handle_cancel_and_close_request(request_data, channel_id, thread_ts, slack_user_name)





# def extract_data_from_slack_thread(thread_ts: str) -> str:
    """Extract data from the Slack thread message (placeholder implementation)"""
    # TODO: Implement actual Slack thread message retrieval
    # For now, return empty string to use fallback values
    return ""


@router.get("/health")
async def health_check():
    """Health check endpoint for the Slack service"""
    return {"status": "healthy", "service": "slack"} 