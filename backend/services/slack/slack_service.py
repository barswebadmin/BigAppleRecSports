"""
Main Slack service for handling refund notifications.
Refactored to use helper modules for better organization.
"""

from typing import Dict, Any, Optional, List
import logging
import hashlib
import time
import json
from config import settings
from .message_builder import SlackMessageBuilder
from .api_client import SlackApiClient, MockSlackApiClient, _is_test_mode
from .utilities import SlackUtilities
from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


class SlackService:
    """
    Main service for handling Slack notifications for refund requests.
    
    This service coordinates message building and API communication
    through specialized helper classes.
    """
    
    def __init__(self):
        # Slack configuration - dynamic based on environment
        is_production = settings.environment == "production"
        
        self.refunds_channel = {
            "name": "#refunds" if is_production else "#joe-test",
            "channel_id": "C08J1EN7SFR" if is_production else "C092RU7R6PL",
            "bearer_token": settings.slack_refunds_bot_token or ""
        }
        
        # Sport-specific team mentions
        # Production team mentions (commented out for testing):
        prod_sport_groups = {
            "kickball": "<!subteam^S08L2521XAM>",
            "bowling": "<!subteam^S08KJJ02738>", 
            "pickleball": "<!subteam^S08KTJ33Z9R>",
            "dodgeball": "<!subteam^S08KJJ5CL4W>"
        }
        
        # Testing configuration - all sports tag personal channel
        debug_sport_groups = {
            "kickball": "<@U0278M72535>",
            "bowling": "<@U0278M72535>", 
            "pickleball": "<@U0278M72535>",
            "dodgeball": "<@U0278M72535>"
        }

        # Initialize helper services (excluding message_management to avoid circular import)
        self.utilities = SlackUtilities()
        self._webhook_handlers = None  # Lazy initialization to avoid circular import

        # Select sport groups based on environment and test mode
        if _is_test_mode():
            self.sport_groups = prod_sport_groups
        else:
            self.sport_groups = prod_sport_groups if is_production else debug_sport_groups
        
        # Initialize helper components
        self.message_builder = SlackMessageBuilder(self.sport_groups)
        
        # Use mock API client during tests to prevent real Slack requests
        if _is_test_mode():
            logger.info("🧪 Test mode detected - using MockSlackApiClient")
            self.api_client = MockSlackApiClient(
                self.refunds_channel["bearer_token"],
                self.refunds_channel["channel_id"]
            )
        else:
            logger.info("🚀 Production mode - using real SlackApiClient")
            self.api_client = SlackApiClient(
                self.refunds_channel["bearer_token"],
                self.refunds_channel["channel_id"]
            )
        
        # Deduplication cache - stores message hashes to prevent duplicates
        # Format: {message_hash: timestamp}
        self._message_cache = {}
        self._cache_expiry_seconds = 300  # 5 minutes

    @property
    def webhook_handlers(self):
        """Lazy initialization of webhook handlers to avoid circular imports"""
        if self._webhook_handlers is None:
            from .webhook_handlers import SlackWebhookHandlers
            self._webhook_handlers = SlackWebhookHandlers()
        return self._webhook_handlers

    def _generate_message_hash(self, order_data: Dict[str, Any], requestor_info: Dict[str, Any]) -> str:
        """
        Generate a unique hash for deduplication based on order and requestor info.
        This prevents the same refund request from being posted multiple times.
        """
        try:
            order = order_data.get("order", {}) if order_data else {}
            order_number = order.get("orderNumber") or order.get("orderName") or order.get("name") or "unknown"
            requestor_email = requestor_info.get("email", "unknown")
            refund_type = requestor_info.get("refund_type", "refund")
            
            # Create deduplication key from critical fields
            dedup_string = f"{order_number}|{requestor_email}|{refund_type}"
            
            # Generate hash
            return hashlib.md5(dedup_string.encode()).hexdigest()
            
        except Exception as e:
            logger.warning(f"Failed to generate message hash: {e}")
            return str(time.time())  # Fallback to timestamp
    
    def _clean_expired_cache(self):
        """Remove expired entries from the deduplication cache"""
        try:
            current_time = time.time()
            expired_keys = [
                key for key, timestamp in self._message_cache.items()
                if current_time - timestamp > self._cache_expiry_seconds
            ]
            
            for key in expired_keys:
                del self._message_cache[key]
                
            if expired_keys:
                logger.info(f"Cleaned {len(expired_keys)} expired cache entries")
                
        except Exception as e:
            logger.warning(f"Failed to clean cache: {e}")
    
    def _is_duplicate_message(self, message_hash: str) -> bool:
        """
        Check if this message has already been sent recently.
        Returns True if it's a duplicate, False if it's new.
        """
        try:
            # Clean expired entries first
            self._clean_expired_cache()
            
            current_time = time.time()
            
            # Check if hash exists and is still valid
            if message_hash in self._message_cache:
                timestamp = self._message_cache[message_hash]
                if current_time - timestamp <= self._cache_expiry_seconds:
                    logger.info(f"🔄 Duplicate message detected (hash: {message_hash[:8]}...)")
                    return True
                else:
                    # Expired entry, remove it
                    del self._message_cache[message_hash]
            
            # Not a duplicate, add to cache
            self._message_cache[message_hash] = current_time
            logger.info(f"🆕 New message cached (hash: {message_hash[:8]}...)")
            return False
            
        except Exception as e:
            logger.warning(f"Failed to check for duplicates: {e}")
            return False  # Allow message through if checking fails
    
    def send_refund_request_notification(
        self,
        requestor_info: Dict[str, Any],
        sheet_link: Optional[str] = None,
        order_data: Optional[Dict[str, Any]] = None,
        refund_calculation: Optional[Dict[str, Any]] = None,
        error_type: Optional[str] = None,
        raw_order_number: Optional[str] = None,
        order_customer_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a refund request notification to Slack.
        
        This method handles all types of refund notifications:
        - Successful refund requests with calculated amounts
        - Fallback messages when season info is missing
        - Error messages for various failure scenarios
        
        Args:
            requestor_info: Information about the person requesting the refund
            sheet_link: Google Sheets link for the request
            order_data: Shopify order data (if available)
            refund_calculation: Calculated refund information (if available)
            error_type: Type of error if this is an error notification
            raw_order_number: Original order number for error cases
            order_customer_email: Order customer email for mismatch errors
            
        Returns:
            Dict containing success status and message details
        """
        try:
            # Generate message hash for deduplication  
            message_hash = self._generate_message_hash(order_data or {}, requestor_info)
            
            # Check for duplicates
            if self._is_duplicate_message(message_hash):
                logger.info("🔄 Skipping duplicate message")
                return {
                    "success": True,
                    "message": "Duplicate message skipped",
                    "duplicate": True
                }
            
            # Build the appropriate message based on available data
            if order_data and refund_calculation and refund_calculation.get("success"):
                # Full success message with calculated refund
                message_data = self.message_builder.build_success_message(
                    order_data=order_data,
                    refund_calculation=refund_calculation,
                    requestor_info=requestor_info,
                    sheet_link=sheet_link
                )
                
            elif error_type:
                # Error message for various failure scenarios
                message_data = self.message_builder.build_error_message(
                    error_type=error_type,
                    requestor_info=requestor_info,
                    sheet_link=sheet_link,
                    raw_order_number=raw_order_number or "",
                    order_customer_email=order_customer_email or ""
                )
                
            elif order_data:
                # Fallback message when order is found but calculation failed
                error_message = ""
                if refund_calculation:
                    error_message = refund_calculation.get("message", "")
                
                message_data = self.message_builder.build_fallback_message(
                    order_data=order_data,
                    requestor_info=requestor_info,
                    sheet_link=sheet_link,
                    error_message=error_message
                )
                
            else:
                # Generic error message
                message_data = self.message_builder.build_error_message(
                    error_type="unknown",
                    requestor_info=requestor_info,
                    sheet_link=sheet_link
                )
            
            # Send the message using the new API client with blocks and action buttons
            logger.info(f"Sending refund notification to {self.refunds_channel['name']}")
            result = self.api_client.send_message(
                message_text=message_data["text"],
                action_buttons=message_data.get("action_buttons", []),
                slack_text=message_data.get("slack_text", "New refund request notification")
            )
            
            if result["success"]:
                logger.info("Refund notification sent successfully to Slack")
            else:
                logger.error(f"Failed to send refund notification to Slack: {result.get('error')}")
                # Remove from cache if sending failed, allow retry
                if message_hash in self._message_cache:
                    del self._message_cache[message_hash]
            
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error in send_refund_request_notification: {str(e)}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    # Convenience methods for accessing helper functionality
    def get_sport_group_mention(self, product_title: str) -> str:
        """Get sport group mention for a product (convenience method)"""
        return self.message_builder.get_sport_group_mention(product_title)
    
    def get_order_url(self, order_id: str, order_name: str) -> str:
        """Get formatted order URL (convenience method)"""
        return self.message_builder.get_order_url(order_id, order_name)
    
    # Additional wrapper methods expected by tests
    def get_product_url(self, product_id: str) -> str:
        """Get formatted product URL (convenience method)"""
        # For tests, return just the URL without Slack formatting
        product_id_digits = product_id.split('/')[-1] if '/' in product_id else product_id
        return f"https://admin.shopify.com/store/09fe59-3/products/{product_id_digits}"
    
    def _get_request_type_text(self, refund_type: str) -> str:
        """Get request type text (wrapper for tests)"""
        return self.message_builder._get_request_type_text(refund_type)
    
    def _get_sheet_link_line(self, sheet_link: Optional[str]) -> str:
        """Get formatted sheet link line (wrapper for tests)"""
        return self.message_builder._get_sheet_link_line(sheet_link)
    
    def _get_requestor_line(self, requestor_name: Dict[str, str], requestor_email: str) -> str:
        """Get formatted requestor line (wrapper for tests)"""
        return self.message_builder._get_requestor_line(requestor_name, requestor_email)
    
    def _get_optional_request_notes(self, notes: Optional[str]) -> str:
        """Get formatted optional notes (wrapper for tests)"""
        return self.message_builder._get_optional_request_notes(notes or "")
    
    def _send_slack_message(self, channel_id: str, text: str, blocks: Optional[List[Dict[str, Any]]] = None,
                          thread_ts: Optional[str] = None) -> Dict[str, Any]:
        """Send slack message (wrapper for compatibility with old implementation and tests)"""
        # This method maintains compatibility with the old implementation
        # Extract message text from blocks if needed
        message_text = text
        if blocks:
            for block in blocks:
                if block.get("type") == "section" and "text" in block:
                    message_text = block["text"]["text"]
                    break
        
        # Send via API client
        return self.api_client.send_message(message_text)
    
    def update_slack_message(self, channel_id: str, message_ts: str, text: str, 
                           blocks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Update an existing Slack message (wrapper for compatibility)"""
        # Extract message text from blocks if needed
        message_text = text
        if blocks:
            for block in blocks:
                if block.get("type") == "section" and "text" in block:
                    message_text = block["text"]["text"]
                    break
        
        return self.api_client.update_message(message_ts, message_text)
    
    def _create_standard_blocks(self, text: str, include_actions: bool = False, 
                               action_buttons: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Create standard Slack message blocks (wrapper for compatibility)"""
        return self.api_client._create_standard_blocks(text, action_buttons if include_actions else None)
        
    def send_ephemeral_error_to_user(
        self,
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
            result = self.api_client.send_ephemeral_message(ephemeral_payload)
            
            if result.get('success', False):
                logger.info(f"✅ Sent ephemeral error message to user {user_id}")
                return True
            else:
                logger.error(f"❌ Failed to send ephemeral message: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception sending ephemeral error message: {str(e)}")
            return False 

    async def handle_slack_interactions(self, request: Request):
        """Handle Slack interactive webhook"""
        try:
            # Get raw body and headers for signature verification
            body = await request.body()
            timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
            signature = request.headers.get("X-Slack-Signature", "")
            
            # Verify Slack signature for security
            if not self.utilities.verify_slack_signature(body, timestamp, signature):
                logger.warning("Invalid Slack signature")
                raise HTTPException(status_code=401, detail="Invalid signature")
            
            # Parse form data
            form_data = await request.form()
            payload_data = form_data.get("payload")
            if isinstance(payload_data, str):
                payload = json.loads(payload_data)
            else:
                raise HTTPException(status_code=400, detail="Invalid payload format")
            
            # Extract information from the payload
            trigger_id = payload.get("trigger_id", "")
            user = payload.get("user", {})
            slack_user_id = user.get("id", "")
            slack_user_name = user.get("username", "")
            channel_id = payload.get("channel", {}).get("id", "")
            
            # Get message info
            message = payload.get("message", {})
            message_ts = message.get("ts", "")
            
            # Extract the full message text from blocks for context
            blocks = message.get("blocks", [])
            current_message_full_text = self.utilities.extract_text_from_blocks(blocks)
            
            # Handle button click actions
            actions = payload.get("actions", [])
            for action in actions:
                action_id = action.get("action_id", "")
                button_value = action.get("value", "")
                
                # Parse button data
                request_data = self.utilities.parse_button_value(button_value)
                
                print(f"\n🔧 === SLACK BUTTON INTERACTION ===")
                print(f"🎯 Action ID: {action_id}")
                print(f"📋 Request Data: {request_data}")
                print(f"👤 User: {slack_user_name} ({slack_user_id})")
                print(f"📍 Channel: {channel_id}, Message: {message_ts}")
                print(f"🔑 Trigger ID: {trigger_id}")
                print("=== END SLACK INTERACTION ===\n")
                
                # Route to appropriate handlers based on action_id
                if action_id == "cancel_order":
                    return await self.webhook_handlers.handle_cancel_order(
                        request_data, channel_id, message_ts, slack_user_id, slack_user_name, 
                        current_message_full_text, trigger_id
                    )
                elif action_id == "proceed_without_cancel":
                    return await self.webhook_handlers.handle_proceed_without_cancel(
                        request_data, channel_id, message_ts, slack_user_id, slack_user_name, 
                        current_message_full_text, trigger_id
                    )
                elif action_id == "cancel_and_close_request":
                    return await self.webhook_handlers.handle_cancel_and_close_request(
                        request_data, channel_id, message_ts, slack_user_name, trigger_id
                    )
                elif action_id == "process_refund":
                    return await self.webhook_handlers.handle_process_refund(
                        request_data, channel_id, message_ts, slack_user_name, 
                        current_message_full_text, slack_user_id, trigger_id
                    )
                elif action_id == "custom_refund_amount":
                    return await self.webhook_handlers.handle_custom_refund_amount(
                        request_data, channel_id, message_ts, slack_user_name
                    )
                elif action_id == "no_refund":
                    return await self.webhook_handlers.handle_no_refund(
                        request_data, channel_id, message_ts, slack_user_name, 
                        current_message_full_text, trigger_id
                    )
                elif action_id.startswith("restock_") or action_id == "do_not_restock":
                    return await self.webhook_handlers.handle_restock_inventory(
                        request_data, action_id, channel_id, message_ts, slack_user_name, 
                        current_message_full_text, trigger_id
                    )
                else:
                    logger.warning(f"Unknown action_id: {action_id}")
                    return {"text": f"Unknown action: {action_id}"}
            
            return {"text": "Action processed successfully"}
        
        except HTTPException:
            # Re-raise HTTP exceptions (like 401 from signature validation) as-is
            raise
        except Exception as e:
            logger.error(f"Error handling Slack interaction: {e}")
            raise HTTPException(status_code=500, detail=str(e)) 