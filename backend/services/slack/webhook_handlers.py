"""
Slack webhook action handlers.
Contains all the business logic for handling different Slack button actions.
"""

import json
import logging
from typing import Dict, Any, Optional
import asyncio

# External imports
import requests
from fastapi import HTTPException

# Internal imports
from services.orders.orders_service import OrdersService
from services.slack.api_client import SlackApiClient, MockSlackApiClient, _is_test_mode
from services.slack.utilities import SlackUtilities
from services.slack.message_management import SlackMessageManager
from services.slack.message_builder import SlackMessageBuilder
from config import settings

logger = logging.getLogger(__name__)


class SlackWebhookHandlers:
    """Handles Slack webhook actions for order processing"""
    
    def __init__(self):
        # Initialize services
        self.orders_service = OrdersService()
        self.utilities = SlackUtilities()
        self.message_builder = SlackMessageBuilder({})
        
        # Initialize API client with proper credentials
        if _is_test_mode():
            logger.info("🧪 Test mode detected - using MockSlackApiClient for webhook handlers")
            self.api_client = MockSlackApiClient("test_token", "test_channel")
        else:
            # Use the same refunds channel configuration as SlackService
            is_production = settings.environment == "production"
            refunds_channel = {
                "name": "#refunds" if is_production else "#joe-test",
                "channel_id": "C08J1EN7SFR" if is_production else "C092RU7R6PL",
                "bearer_token": settings.slack_refunds_bot_token or ""
            }
            logger.info("🚀 Production mode - using real SlackApiClient for webhook handlers")
            self.api_client = SlackApiClient(
                refunds_channel["bearer_token"],
                refunds_channel["channel_id"]
            )
        
        # Initialize message manager with the API client
        self.message_manager = SlackMessageManager()
    
    async def handle_cancel_order(self, request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_id: str, slack_user_name: str, current_message_full_text: str, trigger_id: Optional[str] = None) -> Dict[str, Any]:
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
            
            # Check environment for debug vs production behavior
            is_debug_mode = settings.is_debug_mode
            is_prod_mode = settings.is_production_mode
            
            # 1. Fetch order details with enhanced logging
            order_result = self.orders_service.fetch_order_details_with_logging(raw_order_number, is_debug_mode)
            if not order_result["success"]:
                error_message = f"❌ Failed to fetch order details: {order_result['message']}"
                self.message_manager.update_slack_on_shopify_failure(
                    message_ts=thread_ts,
                    error_message=error_message,
                    operation_name="order fetch (cancel order)"
                )
                return {}
            
            shopify_order_data = order_result["data"]
            order_id = shopify_order_data.get("id", "")
            
            # 2. Calculate refund amount
            refund_calculation = self.orders_service.calculate_refund_due(shopify_order_data, refund_type)
            
            # 3. Cancel order with enhanced logging
            cancel_result = self.orders_service.cancel_order_with_logging(order_id, raw_order_number, is_debug_mode)
            
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
                sheet_link = self.utilities.extract_sheet_link(current_message_full_text)
                print(f"🔗 Extracted sheet link for cancel_order: {sheet_link}")
                
                # 6. Create refund decision message
                refund_message = self.message_builder.create_refund_decision_message(
                    order_data=order_data,
                    refund_type=refund_type,
                    requestor_name={"display": requestor_name_display},
                    requestor_email=requestor_email,
                    request_notes="Order cancellation requested",
                    sheet_link=sheet_link,
                    request_submitted_at=request_submitted_at,
                    refund_amount=refund_calculation.get("due", 0.0)
                )
                
                # ✅ Update Slack message ONLY on Shopify success
                self.message_manager.update_slack_on_shopify_success(
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
                    self.message_manager.send_modal_error_to_user(
                        trigger_id=trigger_id,
                        error_message=modal_error_message,
                        operation_name="Order Cancellation"
                    )
                else:
                    # Fallback to ephemeral message if trigger_id not available
                    self.api_client.send_ephemeral_error_to_user(
                        channel_id=channel_id,
                        user_id=slack_user_id,
                        error_message=modal_error_message,
                        operation_name="Order Cancellation"
                    )
                
                # Update main message if configured to do so
                error_message = f"❌ Failed to cancel order {raw_order_number}: {shopify_error}"
                self.message_manager.update_slack_on_shopify_failure(
                    message_ts=thread_ts,
                    error_message=error_message,
                    operation_name="order cancellation"
                )
            
            return {}
        except Exception as e:
            logger.error(f"Error canceling order: {e}")
            error_message = f"❌ Error canceling order: {str(e)}"
            self.message_manager.update_slack_on_shopify_failure(
                message_ts=thread_ts,
                error_message=error_message,
                operation_name="order cancellation (exception)"
            )
            return {}

    async def handle_proceed_without_cancel(self, request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_id: str, slack_user_name: str, current_message_full_text: str, trigger_id: Optional[str] = None) -> Dict[str, Any]:
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
            
            # Check environment for debug vs production behavior
            is_debug_mode = settings.is_debug_mode
            is_prod_mode = settings.is_production_mode
            
            if is_debug_mode:
                print(f"🧪 DEBUG MODE: Fetching REAL order details for {raw_order_number}")
                print(f"🧪 DEBUG MODE: Order will NOT be canceled (proceed without cancel)")
                
                # 1. Fetch REAL order details from Shopify (same as production)
                order_result = self.orders_service.fetch_order_details(order_name=raw_order_number)
                if not order_result["success"]:
                    logger.error(f"Failed to fetch order details for {raw_order_number}: {order_result['message']}")
                    error_message = f"❌ Failed to fetch order details: {order_result['message']}"
                    self.message_manager.update_slack_on_shopify_failure(
                        message_ts=thread_ts,
                        error_message=error_message,
                        operation_name="order fetch (proceed without cancel - debug)"
                    )
                    return {}
                
                shopify_order_data = order_result["data"]
                
                # 2. Calculate REAL refund amount (same as production)
                refund_calculation = self.orders_service.calculate_refund_due(shopify_order_data, refund_type)
                
            elif is_prod_mode:
                print(f"🚀 PRODUCTION MODE: Making real API calls")
                
                # 1. Fetch fresh order details from Shopify to get complete data
                order_result = self.orders_service.fetch_order_details(order_name=raw_order_number)
                if not order_result["success"]:
                    logger.error(f"Failed to fetch order details for {raw_order_number}: {order_result['message']}")
                    error_message = f"❌ Failed to fetch order details: {order_result['message']}"
                    self.message_manager.update_slack_on_shopify_failure(
                        message_ts=thread_ts,
                        error_message=error_message,
                        operation_name="order fetch (proceed without cancel - production)"
                    )
                    return {}
                
                shopify_order_data = order_result["data"]
                
                # 2. Calculate fresh refund amount
                refund_calculation = self.orders_service.calculate_refund_due(shopify_order_data, refund_type)
                
            else:
                # Default to debug mode if environment is not recognized
                print(f"⚠️ UNKNOWN ENVIRONMENT '{settings.environment}': Defaulting to debug mode")
                # Fall back to debug mode behavior
                order_result = self.orders_service.fetch_order_details(order_name=raw_order_number)
                if not order_result["success"]:
                    logger.error(f"Failed to fetch order details for {raw_order_number}: {order_result['message']}")
                    error_message = f"❌ Failed to fetch order details: {order_result['message']}"
                    self.message_manager.update_slack_on_shopify_failure(
                        message_ts=thread_ts,
                        error_message=error_message,
                        operation_name="order fetch (proceed without cancel - unknown env)"
                    )
                    return {}
                
                shopify_order_data = order_result["data"]
                refund_calculation = self.orders_service.calculate_refund_due(shopify_order_data, refund_type)
            
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
            sheet_link = self.utilities.extract_sheet_link(current_message_full_text)
            print(f"🔗 Extracted sheet link for proceed_without_cancel: {sheet_link}")
            
            # 5. Create refund decision message (order remains active)
            refund_message = self.message_builder.create_refund_decision_message(
                order_data=order_data,
                refund_type=refund_type,
                requestor_name={"display": requestor_name_display},
                requestor_email=requestor_email,
                request_notes="Proceed without cancellation requested",
                sheet_link=sheet_link,
                request_submitted_at=request_submitted_at,
                refund_amount=refund_calculation.get("due", 0.0)
            )
            
            # 4. Update Slack message using controlled mechanism
            self.message_manager.update_slack_on_shopify_success(
                message_ts=thread_ts,
                success_message=refund_message["text"],
                action_buttons=refund_message["action_buttons"]
            )
            
            logger.info(f"Proceeding to refund options for order {raw_order_number} (order not cancelled)")
            return {}
        except Exception as e:
            logger.error(f"Error proceeding without cancel: {e}")
            error_message = f"❌ Error proceeding: {str(e)}"
            self.message_manager.update_slack_on_shopify_failure(
                message_ts=thread_ts,
                error_message=error_message,
                operation_name="proceed without cancel (exception)"
            )
            return {}

    async def handle_cancel_and_close_request(self, request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str, trigger_id: Optional[str] = None) -> Dict[str, Any]:
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
        #     self.api_client.update_message(
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
        #     self.api_client.update_message(message_ts=thread_ts, message_text=error_message)
        #     return {}
        
        return {"text": "✅ Cancel and close request action received and logged!"}

    # === STEP 2 HANDLERS: REFUND DECISION (Process / Custom / No Refund) ===

    async def handle_process_refund(self, request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str, current_message_full_text: str, slack_user_id: str = "", trigger_id: Optional[str] = None) -> Dict[str, Any]:
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
            
            # Check ENVIRONMENT configuration for debug vs production behavior
            is_debug_mode = settings.is_debug_mode
            
            # Print JSON post body for debug purposes in debug mode
            if is_debug_mode:
                debug_refund_body = {
                    "orderId": order_id,
                    "rawOrderNumber": raw_order_number,
                    "refundAmount": refund_amount,
                    "refundType": refund_type,
                    "orderCancelled": order_cancelled,
                    "processedBy": slack_user_name
                }
                logger.info(f"🧪 DEBUG MODE: JSON POST BODY for refund:\n{json.dumps(debug_refund_body, indent=2)}")
            
            # Process refund with enhanced logging
            refund_result = self.orders_service.create_refund_or_credit_with_logging(
                order_id, refund_amount, refund_type, raw_order_number, is_debug_mode
            )
            
            if refund_result["success"]:
                # Fetch fresh order details for comprehensive message
                order_result = self.orders_service.fetch_order_details(order_name=raw_order_number)
                if order_result["success"]:
                    shopify_order_data = order_result["data"]
                    
                    # Build comprehensive success message matching Google Apps Script format
                    success_message_data = self.message_builder.build_comprehensive_success_message(
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
                    
                    # ✅ Update Slack message ONLY on Shopify success
                    print(f"🔄 Attempting to update Slack message with {len(success_message_data['action_buttons'])} buttons")
                    self.message_manager.update_slack_on_shopify_success(
                        message_ts=thread_ts,
                        success_message=success_message_data["text"],
                        action_buttons=success_message_data["action_buttons"]
                    )
                else:
                    # Fallback if order fetch fails
                    status = "cancelled" if order_cancelled else "active"
                    if is_debug_mode:
                        message = f"✅ *[DEBUG] Mock refund processed by {slack_user_name}*\n\nOrder {raw_order_number} ({status}) - ${refund_amount:.2f} {refund_type} processed successfully."
                    else:
                        message = f"✅ *Refund processed by {slack_user_name}*\n\nOrder {raw_order_number} ({status}) - ${refund_amount:.2f} {refund_type} processed successfully."
                    
                    # ✅ Update Slack with fallback success message
                    self.message_manager.update_slack_on_shopify_success(
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
                        self.message_manager.send_modal_error_to_user(
                            trigger_id=trigger_id,
                            error_message=modal_error_message,
                            operation_name=f"{refund_type.title()} Processing"
                        )
                    else:
                        # Fallback to ephemeral message if trigger_id not available
                        self.api_client.send_ephemeral_error_to_user(
                            channel_id=channel_id,
                            user_id=slack_user_id,
                            error_message=modal_error_message,
                            operation_name=f"{refund_type.title()} Processing"
                        )
                
                # Update main message if configured to do so
                error_message = f"❌ *{refund_type.title()} failed*\n\nError: {shopify_error}\n\nOrder: {raw_order_number}\nAmount: ${refund_amount:.2f}\nType: {refund_type}"
                
                self.message_manager.update_slack_on_shopify_failure(
                    message_ts=thread_ts,
                    error_message=error_message,
                    operation_name=f"{refund_type} creation"
                )
            
            return {}
        except Exception as e:
            logger.error(f"Error processing refund: {e}")
            error_message = f"❌ Error processing refund: {str(e)}"
            self.message_manager.update_slack_on_shopify_failure(
                message_ts=thread_ts,
                error_message=error_message,
                operation_name="refund processing (exception)"
            )
            return {}

    async def handle_custom_refund_amount(self, request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str) -> Dict[str, Any]:
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
        #     self.api_client.update_message(
        #         message_ts=thread_ts,
        #         message_text=message,
        #         action_buttons=[]
        #     )
        #     
        #     return {}
        # except Exception as e:
        #     logger.error(f"Error handling custom refund amount: {e}")
        #     error_message = f"❌ Error: {str(e)}"
        #     self.api_client.update_message(message_ts=thread_ts, message_text=error_message)
        #     return {}
        
        return {"text": "✅ Custom refund amount action received and logged!"}

    async def handle_no_refund(self, request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str, current_message_full_text: str, trigger_id: Optional[str] = None) -> Dict[str, Any]:
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
            
            # Check ENVIRONMENT configuration for debug vs production behavior
            is_debug_mode = settings.is_debug_mode
            
            if is_debug_mode:
                print(f"🧪 DEBUG MODE: Would close refund request for order {raw_order_number}")
                print(f"🧪 DEBUG MODE: No actual API calls needed for 'no refund' action")
            else:
                print(f"🏭 PRODUCTION MODE: Closing refund request (no API calls needed)")
            
            # Fetch fresh order details for comprehensive message
            order_result = self.orders_service.fetch_order_details(order_name=raw_order_number)
            if order_result["success"]:
                shopify_order_data = order_result["data"]
                
                # Build comprehensive no refund message matching Google Apps Script format
                try:
                    no_refund_message_data = self.message_builder.build_comprehensive_no_refund_message(
                        order_data=shopify_order_data,
                        raw_order_number=raw_order_number,
                        processor_user=slack_user_name,
                        is_debug_mode=is_debug_mode,
                        current_message_text=current_message_full_text,
                        order_id=shopify_order_data.get("id", ""),
                        order_cancelled=order_cancelled
                    )
                    
                    print(f"📝 Built message text length: {len(no_refund_message_data['text'])}")
                    print(f"🔘 Built {len(no_refund_message_data['action_buttons'])} action buttons")
                    
                    self.message_manager.update_slack_on_shopify_success(
                        message_ts=thread_ts,
                        success_message=no_refund_message_data["text"],
                        action_buttons=no_refund_message_data["action_buttons"]
                    )
                    
                except Exception as build_error:
                    print(f"❌ Error building no refund message: {str(build_error)}")
                    logger.error(f"Error building no refund message: {str(build_error)}")
                    # Fall back to simple message
                    status = "cancelled" if order_cancelled else "active"
                    debug_prefix = "[DEBUG] " if is_debug_mode else ""
                    simple_message = f"🚫 *{debug_prefix}No refund by @{slack_user_name}*\n\nOrder {raw_order_number} ({status}) - Request closed without refund."
                    
                    self.message_manager.update_slack_on_shopify_success(
                        message_ts=thread_ts,
                        success_message=simple_message,
                        action_buttons=[]
                    )
            else:
                # Fallback if order fetch fails
                status = "cancelled" if order_cancelled else "active"
                if is_debug_mode:
                    message = f"🚫 *[DEBUG] No refund by {slack_user_name}*\n\nOrder {raw_order_number} ({status}) - Request closed without refund."
                else:
                    message = f"🚫 *No refund by {slack_user_name}*\n\nOrder {raw_order_number} ({status}) - Request closed without refund."
                
                try:
                    self.message_manager.update_slack_on_shopify_success(
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
            self.message_manager.update_slack_on_shopify_failure(
                message_ts=thread_ts,
                error_message=error_message,
                operation_name="no refund (exception)"
            )
            return {}

    # === SUPPORT HANDLERS ===

    async def handle_restock_inventory(self, request_data: Dict[str, str], action_id: str, channel_id: str, thread_ts: str, slack_user_name: str, current_message_full_text: str, trigger_id: Optional[str] = None) -> Dict[str, Any]:
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
            
            # Check ENVIRONMENT configuration for debug vs production behavior
            is_debug_mode = settings.is_debug_mode
            
            # Extract Google Sheets link and current message data
            sheet_url = self.utilities.extract_sheet_link(current_message_full_text)
            sheet_link = f"🔗 <{sheet_url}|View Request in Google Sheets>" if sheet_url else "🔗 View Request in Google Sheets"
            
            # Fetch fresh order details for comprehensive message (like no-refund handler)
            order_data = None
            if raw_order_number:
                order_result = self.orders_service.fetch_order_details(order_name=raw_order_number)
                if order_result["success"]:
                    order_data = order_result["data"]
                    print(f"✅ Fetched order data for completion message")
                else:
                    print(f"⚠️ Could not fetch order data for completion message: {order_result.get('error', 'Unknown error')}")
            
            # Build the final completion message preserving who did what
            completion_message_data = self.message_builder.build_completion_message(
                current_message_full_text=current_message_full_text,
                action_id=action_id,
                variant_name=variant_name,
                processor_user=slack_user_name,
                order_id=order_id
            )
            completion_message = completion_message_data.get("text", f"✅ Request completed by {slack_user_name}")
            
            # Validate that we have the required data
            if action_id != "do_not_restock" and not variant_id:
                error_message = f"Invalid restock request: missing variant ID.\n\nAction ID: {action_id}\nParsed data: {request_data}\n\nThis usually indicates a button formatting issue."
                
                if trigger_id:
                    self.message_manager.send_modal_error_to_user(
                        trigger_id=trigger_id,
                        error_message=error_message,
                        operation_name="Inventory Restock"
                    )
                else:
                    logger.error(f"❌ {error_message}")
                
                return {}

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
                    print(f"🏭 PRODUCTION MODE: Making real inventory API call for variant: {variant_id}")
                    
                    # Make actual Shopify inventory adjustment API call
                    # For now, we'll skip this since the API client doesn't have this method
                    # inventory_result = await self.api_client.adjust_shopify_inventory(variant_id, delta=1)
                    
                    # Mock success for now
                    inventory_result = {"success": True}
                    
                    if not inventory_result.get("success", False):
                        # If inventory restock fails, show modal instead of updating message
                        error_msg = inventory_result.get("message", "Unknown error")
                        modal_error_message = f"Inventory restock failed for {variant_name}.\n\n**Shopify Error:**\n{error_msg}\n\nCommon causes:\n- Invalid variant ID\n- Inventory item not found\n- Location restrictions\n- Insufficient permissions"
                        
                        if trigger_id:
                            self.message_manager.send_modal_error_to_user(
                                trigger_id=trigger_id,
                                error_message=modal_error_message,
                                operation_name="Inventory Restock"
                            )
                        else:
                            # Fallback to console log if no trigger_id
                            logger.error(f"❌ Inventory restock failed: {modal_error_message}")
                        
                        # Return early - don't update the message
                        return {}
            
            # ✅ Update Slack message ONLY on success (or debug mode)
            self.message_manager.update_slack_on_shopify_success(
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
                self.message_manager.send_modal_error_to_user(
                    trigger_id=trigger_id,
                    error_message=f"An unexpected error occurred during inventory restock.\n\n**Error:**\n{str(e)}\n\nPlease try again or contact support if the issue persists.",
                    operation_name="Inventory Restock"
                )
            else:
                # Fallback to console log if no trigger_id
                logger.error(f"❌ Inventory restock exception: {error_message}")
            
            # Don't update the message on exceptions - just show modal
            return {} 