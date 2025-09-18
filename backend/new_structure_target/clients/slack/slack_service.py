"""
Main Slack service - Table of Contents.
Provides a clean interface to all Slack functionality organized by concern.
"""

import sys
import os
import logging
from typing import Dict, Any, Optional, List

# Slack SDK
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError, SlackClientError

# Our systems
from .core.slack_config import SlackConfig
from models.slack import Slack, RefundType, SlackMessageType

# Existing services
from services.orders import OrdersService

# Core functionality
try:
    from .core import SlackClient, SlackSecurity, SlackUtilities, MockSlackClient
    from .builders import SlackMessageBuilder, ModernMessageBuilder, SlackCacheManager, SlackMetadataBuilder, SlackMessageParsers, SlackOrderHandlers
    from .slack_refunds_utils import SlackRefundsUtils
except ImportError:
    from core import SlackClient, SlackSecurity, SlackUtilities, MockSlackClient
    from builders import SlackMessageBuilder, ModernMessageBuilder, SlackCacheManager, SlackMetadataBuilder, SlackMessageParsers, SlackOrderHandlers
    from slack_refunds_utils import SlackRefundsUtils

logger = logging.getLogger(__name__)


def _is_test_mode() -> bool:
    """Detect if we're running in test mode."""
    if "pytest" in sys.modules:
                    return True
    if any("pytest" in arg for arg in sys.argv):
        return True
    if os.getenv("TESTING", "").lower() in ("true", "1", "yes"):
        return True
    if any("test_" in arg or arg.endswith("_test.py") for arg in sys.argv):
        return True
    return False


class SlackService:
    """
    Main Slack service - Table of Contents for all Slack functionality.
    
    This service provides a clean interface to all Slack operations organized by concern:
    - Core API operations (send, update, ephemeral messages)
    - Security and parsing (signature verification, button parsing)
    - Business logic (refund notifications, custom messages)
    - Utilities (convenience methods, URL building)
    - Order handling (workflow coordination)
    """

    def __init__(self, token: Optional[str] = None, default_channel: Optional[str] = None):
        """Initialize the Slack service with all components."""
        
        # Initialize services
        self.orders_service = OrdersService()
        
        # Get configuration from our new system
        self.config = SlackConfig()
        self.environment = self.config.get_environment()
        self.is_production = self.config.is_production_mode()
        
        # Initialize core components (no token storage in service)
        # SlackClient will be created on-demand with provided tokens
        self.slack_client = None  # Will be created per-operation with specific token
        self.slack_security = SlackSecurity(self.config.Token.get_signing_secret())
        self.slack_utilities = SlackUtilities(
            self._get_message_builder(),
            self._get_message_parsers()
        )
        # No longer need SlackBusiness - using WebClient directly

        # Initialize helper components
        self.message_builder = self._get_message_builder()
        self.refunds_utils = SlackRefundsUtils(
            self.orders_service, 
            self._get_settings(),
            self.message_builder
        )
        
        # Initialize modern utility classes
        self.modern_message_builder = ModernMessageBuilder()
        self.cache_manager = self._get_cache_manager()
        self.metadata_builder = SlackMetadataBuilder()
        self.message_parsers = self._get_message_parsers()
        self.order_handlers = SlackOrderHandlers(self.orders_service, self, self.message_builder)
        
        logger.info(f"🚀 SlackService initialized for {self.environment} environment")

    def _get_default_channel(self) -> str:
        """Get the default channel for messages."""
        return self.config.Channel.JoeTest

    def _get_sport_groups(self) -> Dict[str, str]:
        """Get sport groups configuration."""
        return self.config.Group.get_all()

    # ============================================================================
    # CLIENT FACTORY METHODS
    # ============================================================================
    
    def _create_slack_client(self, token: str) -> SlackClient:
        """Create a SlackClient with the specified token."""
        if _is_test_mode():
            client = MockSlackClient(token, self._get_default_channel())
        else:
            client = WebClient(token=token)
        return SlackClient(client)  # type: ignore
    
    

    # ============================================================================
    # CONVENIENCE METHODS FOR TESTING
    # ============================================================================
    
    def verify_slack_signature(self, body: bytes, timestamp: str, signature: str) -> bool:
        """Convenience method for tests - delegates to slack_security"""
        return self.slack_security.verify_slack_signature(body, timestamp, signature)

    async def handle_slack_interaction(self, payload: Optional[Dict[str, Any]], body: bytes, timestamp: Optional[str], signature: Optional[str]) -> Dict[str, Any]:
        """
        Handle Slack interactions - main entry point for processing Slack events.

        Args:
            payload: Parsed Slack payload
            body: Raw request body for signature verification
            timestamp: Request timestamp
            signature: Request signature

        Returns:
            Response dictionary for Slack
        """
        try:
            # Verify signature if present
            if timestamp and signature:
                signature_valid = self.slack_security.verify_slack_signature(body, timestamp, signature)
                logger.info(f"Signature verification: {'valid' if signature_valid else 'invalid'}")
                if not signature_valid:
                    logger.warning("Signature verification failed - but continuing for debug...")
            else:
                logger.warning("No signature headers provided")

            # Process modal submissions
            if payload and payload.get("type") == "view_submission":
                return await self._handle_modal_submission(payload)

            # Process button actions
            if payload and payload.get("type") == "block_actions":
                return await self._handle_button_action(payload)

            # Return success response to Slack
            return {"text": "✅ Webhook received and logged successfully!"}

        except Exception as e:
            logger.error(f"Error handling Slack interaction: {e}")
            raise

    async def _handle_modal_submission(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle modal submission events."""
        logger.info("Processing modal submission")
        
        view = payload.get("view", {})
        callback_id = view.get("callback_id")

        if callback_id == "edit_request_details_submission":
            return await self.handle_edit_request_details_submission(payload)
        elif callback_id == "deny_refund_request_modal_submission":
            return await self.handle_deny_refund_request_modal_submission(payload)
        elif callback_id == "restock_confirmation_modal":
            return await self.handle_restock_confirmation_submission(payload)
        elif callback_id == "custom_refund_submit":
            return await self._handle_custom_refund_submission(payload)
        else:
            logger.warning(f"Unknown modal callback_id: {callback_id}")
            return {"response_action": "clear"}

    async def _handle_custom_refund_submission(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle custom refund modal submission."""
        logger.info("Processing custom refund modal submission")

        # Extract values from the modal input
        values = payload["view"]["state"]["values"]
        refund_amount = values["refund_input_block"]["custom_refund_amount"]["value"]

        # Extract metadata
        private_metadata = payload["view"].get("private_metadata")
        if not private_metadata:
            raise ValueError("Missing private_metadata in view submission")

        import json
        metadata = json.loads(private_metadata)

        # Extract requestor information from metadata or Slack user
        slack_user_name = metadata.get("slack_user_name", "Unknown User")
        requestor_name = {
            "first": metadata.get("requestor_first_name", ""),
            "last": metadata.get("requestor_last_name", ""),
        }
        requestor_email = metadata.get("requestor_email", "")

        # Build the request_data to match what process_refund expects
        request_data = {
            "orderId": metadata["orderId"],
            "rawOrderNumber": metadata["rawOrderNumber"],
            "refundAmount": refund_amount,
            "refundType": metadata["refundType"],
            "orderCancelled": "false",
        }

        # Call process_refund with the updated amount
        return await self.handle_process_refund(
            request_data=request_data,
            channel_id=metadata["channel_id"],
            requestor_name=requestor_name,
            requestor_email=requestor_email,
            thread_ts=metadata["thread_ts"],
            slack_user_name=slack_user_name,
            current_message_full_text=metadata["current_message_full_text"],
            slack_user_id=payload["user"]["id"],
            trigger_id=payload.get("trigger_id", ""),
        )

    async def _handle_button_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle button action events."""
        logger.info("Processing button action")
        
        actions = payload.get("actions", [])
        if not actions:
            return {"text": "No actions found"}

        action = actions[0]
        action_id = action.get("action_id")
        action_value = action.get("value", "")
        slack_user_id = payload.get("user", {}).get("id", "Unknown")
        slack_user_name = payload.get("user", {}).get("name", "Unknown")
        trigger_id = payload.get("trigger_id")

        # Parse button data to get request data
        if action_value.startswith("{") and action_value.endswith("}"):
            # JSON format (newer restock buttons)
            try:
                import json
                request_data = json.loads(action_value)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON action value: {action_value}")
                request_data = {}
            else:
                # Pipe-separated format (older buttons)
                request_data = self.slack_security.parse_button_value(action_value)

        # Extract requestor info from parsed data
        requestor_name = {
            "first": request_data.get("first", "Unknown"),
            "last": request_data.get("last", "Unknown"),
        }
        requestor_email = request_data.get("email", "Unknown")

        # Get message info for updating
        thread_ts = payload.get("message", {}).get("ts")
        channel_id = payload.get("channel", {}).get("id")

        # Extract metadata from the original message
        message_metadata = payload.get("message", {}).get("metadata", {})
        original_channel = None
        original_mention = None

        if message_metadata and message_metadata.get("event_type") == "refund_request":
            event_payload = message_metadata.get("event_payload", {})
            original_channel = event_payload.get("originalChannel")
            original_mention = event_payload.get("originalMention")

        # Extract current message content for data preservation
        current_message_blocks = payload.get("message", {}).get("blocks", [])
        current_message_text = payload.get("message", {}).get("text", "")

        # Convert blocks back to text for parsing
        current_message_full_text = self.slack_security.extract_text_from_blocks(current_message_blocks)

        # If blocks extraction fails, fall back to the simple text field
        if not current_message_full_text and current_message_text:
            current_message_full_text = current_message_text
            logger.warning("Using fallback message text since blocks extraction failed")

        logger.info(f"Button clicked: {action_id} with data: {request_data}")

        # Route to appropriate handler based on action_id
        return await self._route_button_action(
            action_id=action_id,
            request_data=request_data,
            channel_id=channel_id,
            requestor_name=requestor_name,
            requestor_email=requestor_email,
            thread_ts=thread_ts,
            slack_user_id=slack_user_id,
            slack_user_name=slack_user_name,
            current_message_full_text=current_message_full_text,
            trigger_id=trigger_id,
            original_channel=original_channel,
            original_mention=original_mention,
        )

    async def _route_button_action(self, action_id: str, request_data: Dict[str, Any], 
                                 channel_id: str, requestor_name: Dict[str, str], 
                                 requestor_email: str, thread_ts: str, slack_user_id: str, 
                                 slack_user_name: str, current_message_full_text: str, 
                                 trigger_id: Optional[str], original_channel: Optional[str] = None, 
                                 original_mention: Optional[str] = None) -> Dict[str, Any]:
        """Route button actions to appropriate handlers."""
        
        # === STEP 1 HANDLERS: INITIAL DECISION (Cancel Order / Proceed Without Canceling) ===
        if action_id == "cancel_order":
            return await self.handle_cancel_order(
                request_data, channel_id, requestor_name, requestor_email,
                thread_ts, slack_user_id, slack_user_name, current_message_full_text, trigger_id or ""
            )

        elif action_id == "proceed_without_cancel":
            return await self.handle_proceed_without_cancel(
                request_data, channel_id, requestor_name, requestor_email,
                thread_ts, slack_user_id, slack_user_name, current_message_full_text,
                trigger_id or "", original_channel or "", original_mention or ""
            )

        elif action_id == "deny_refund_request_show_modal":
            return await self.handle_deny_refund_request_show_modal(
                request_data=request_data, channel_id=channel_id, thread_ts=thread_ts,
                slack_user_name=slack_user_name, slack_user_id=slack_user_id,
                trigger_id=trigger_id or "", current_message_full_text=current_message_full_text
            )

        # === STEP 2 HANDLERS: REFUND DECISION (Process / Custom / No Refund) ===
        elif action_id == "process_refund":
            return await self.handle_process_refund(
                request_data=request_data, channel_id=channel_id,
                requestor_name=requestor_name, requestor_email=requestor_email,
                thread_ts=thread_ts, slack_user_name=slack_user_name,
                current_message_full_text=current_message_full_text,
                slack_user_id=slack_user_id, trigger_id=trigger_id or ""
            )

        elif action_id == "custom_refund_amount":
            return await self.handle_custom_refund_amount(
                request_data=request_data, channel_id=channel_id, thread_ts=thread_ts,
                requestor_name=requestor_name, requestor_email=requestor_email,
                slack_user_name=slack_user_name, current_message_full_text=current_message_full_text,
                slack_user_id=slack_user_id, trigger_id=trigger_id or ""
            )

        elif action_id == "no_refund":
            return await self.handle_no_refund(
                request_data, channel_id, requestor_name, requestor_email,
                thread_ts, slack_user_name, slack_user_id, current_message_full_text, trigger_id or ""
            )

        # === EMAIL MISMATCH HANDLERS ===
        elif action_id == "edit_request_details":
            return await self.handle_edit_request_details(
                request_data=request_data, channel_id=channel_id, thread_ts=thread_ts,
                slack_user_name=slack_user_name, slack_user_id=slack_user_id,
                trigger_id=trigger_id or "", current_message_full_text=current_message_full_text
            )

        # === STEP 3 HANDLERS: RESTOCK INVENTORY (Restock / Do Not Restock) ===
        elif action_id and (action_id.startswith("confirm_restock") or action_id == "confirm_do_not_restock"):
            return await self.handle_restock_confirmation_request(
                request_data, action_id, trigger_id or "", channel_id, thread_ts, current_message_full_text
            )
        elif action_id and (action_id.startswith("restock") or action_id == "do_not_restock"):
            return await self.handle_restock_inventory(
                request_data, action_id, channel_id, thread_ts,
                slack_user_name, current_message_full_text, trigger_id or ""
            )
        else:
            if not action_id:
                raise ValueError("Missing action_id in request")
            logger.warning(f"Unknown action_id: {action_id}")
            return {
                "response_type": "ephemeral",
                "text": f"Unknown action: {action_id}",
            }

    # === DELEGATED HANDLER METHODS ===
    # These methods delegate to the SlackRefundsUtils for backward compatibility
    
    async def handle_edit_request_details_submission(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle edit request details modal submission."""
        # This method should be implemented in SlackRefundsUtils
        logger.warning("handle_edit_request_details_submission not implemented")
        return {"response_action": "clear"}

    async def handle_deny_refund_request_modal_submission(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle deny refund request modal submission."""
        # This method should be implemented in SlackRefundsUtils
        logger.warning("handle_deny_refund_request_modal_submission not implemented")
        return {"response_action": "clear"}

    async def handle_restock_confirmation_submission(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle restock confirmation modal submission."""
        # This method should be implemented in SlackRefundsUtils
        logger.warning("handle_restock_confirmation_submission not implemented")
        return {"response_action": "clear"}

    async def handle_process_refund(self, request_data: Dict[str, Any], channel_id: str, 
                                  requestor_name: Dict[str, str], requestor_email: str, 
                                  thread_ts: str, slack_user_name: str, 
                                  current_message_full_text: str, slack_user_id: str, 
                                  trigger_id: str) -> Dict[str, Any]:
        """Handle process refund action."""
        # This method should be implemented in SlackRefundsUtils
        logger.warning("handle_process_refund not implemented")
        return {"text": "Process refund functionality not yet implemented"}

    async def handle_cancel_order(self, request_data: Dict[str, Any], channel_id: str, 
                                requestor_name: Dict[str, str], requestor_email: str, 
                                thread_ts: str, slack_user_id: str, slack_user_name: str, 
                                current_message_full_text: str, trigger_id: str) -> Dict[str, Any]:
        """Handle cancel order action."""
        # This method should be implemented in SlackRefundsUtils
        logger.warning("handle_cancel_order not implemented")
        return {"text": "Cancel order functionality not yet implemented"}

    async def handle_proceed_without_cancel(self, request_data: Dict[str, Any], channel_id: str, 
                                          requestor_name: Dict[str, str], requestor_email: str, 
                                          thread_ts: str, slack_user_id: str, slack_user_name: str, 
                                          current_message_full_text: str, trigger_id: str, 
                                          original_channel: str, original_mention: str) -> Dict[str, Any]:
        """Handle proceed without cancel action."""
        # This method should be implemented in SlackRefundsUtils
        logger.warning("handle_proceed_without_cancel not implemented")
        return {"text": "Proceed without cancel functionality not yet implemented"}

    async def handle_deny_refund_request_show_modal(self, request_data: Dict[str, Any], 
                                                  channel_id: str, thread_ts: str, 
                                                  slack_user_name: str, slack_user_id: str, 
                                                  trigger_id: str, current_message_full_text: str) -> Dict[str, Any]:
        """Handle deny refund request show modal action."""
        # This method should be implemented in SlackRefundsUtils
        logger.warning("handle_deny_refund_request_show_modal not implemented")
        return {"text": "Deny refund request modal functionality not yet implemented"}

    async def handle_custom_refund_amount(self, request_data: Dict[str, Any], channel_id: str, 
                                        thread_ts: str, requestor_name: Dict[str, str], 
                                        requestor_email: str, slack_user_name: str, 
                                        current_message_full_text: str, slack_user_id: str, 
                                        trigger_id: str) -> Dict[str, Any]:
        """Handle custom refund amount action."""
        # This method should be implemented in SlackRefundsUtils
        logger.warning("handle_custom_refund_amount not implemented")
        return {"text": "Custom refund amount functionality not yet implemented"}

    async def handle_no_refund(self, request_data: Dict[str, Any], channel_id: str, 
                             requestor_name: Dict[str, str], requestor_email: str, 
                             thread_ts: str, slack_user_name: str, slack_user_id: str, 
                             current_message_full_text: str, trigger_id: str) -> Dict[str, Any]:
        """Handle no refund action."""
        # This method should be implemented in SlackRefundsUtils
        logger.warning("handle_no_refund not implemented")
        return {"text": "No refund functionality not yet implemented"}

    async def handle_edit_request_details(self, request_data: Dict[str, Any], channel_id: str, 
                                        thread_ts: str, slack_user_name: str, slack_user_id: str, 
                                        trigger_id: str, current_message_full_text: str) -> Dict[str, Any]:
        """Handle edit request details action."""
        # This method should be implemented in SlackRefundsUtils
        logger.warning("handle_edit_request_details not implemented")
        return {"text": "Edit request details functionality not yet implemented"}

    async def handle_restock_confirmation_request(self, request_data: Dict[str, Any], 
                                                action_id: str, trigger_id: str, 
                                                channel_id: str, thread_ts: str, 
                                                current_message_full_text: str) -> Dict[str, Any]:
        """Handle restock confirmation request action."""
        # This method should be implemented in SlackRefundsUtils
        logger.warning("handle_restock_confirmation_request not implemented")
        return {"text": "Restock confirmation request functionality not yet implemented"}

    async def handle_restock_inventory(self, request_data: Dict[str, Any], action_id: str, 
                                     channel_id: str, thread_ts: str, slack_user_name: str, 
                                     current_message_full_text: str, trigger_id: str) -> Dict[str, Any]:
        """Handle restock inventory action."""
        # This method should be implemented in SlackRefundsUtils
        logger.warning("handle_restock_inventory not implemented")
        return {"text": "Restock inventory functionality not yet implemented"}

    def _get_settings(self):
        """Get settings object for backward compatibility."""
        class Config:
            def __init__(self, config):
                self.slack_subgroups = config.Group.get_all()
        return Config(self.config)

    def _get_message_builder(self):
        """Get message builder instance."""
        return SlackMessageBuilder(self._get_sport_groups())

    def _get_cache_manager(self):
        """Get cache manager instance."""
        return SlackCacheManager()


    def _get_message_parsers(self):
        """Get message parsers instance."""
        return SlackMessageParsers()

    # ============================================================================
    # CORE API METHODS (delegated to SlackClient)
    # ============================================================================

    def send_message(
        self,
        channel: str,
        token: str,
        message_text: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None,
        action_buttons: Optional[List[Dict[str, Any]]] = None,
        slack_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        thread_ts: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a message to a Slack channel.
        
        Args:
            channel: Channel name as class name from SlackConfig.Channel, resolves to its ID
            token: Bot token as SlackConfig.Token, resolves to its secret
            message_text: Plain text message (used as fallback if blocks provided fail to resolve)
            blocks: Slack blocks for rich formatting
            action_buttons: Action buttons for the message
            slack_text: Alternative text for notifications
            metadata: Additional metadata
            thread_ts: Thread timestamp for replies
            
        Returns:
            Dict containing success status and response details
        """
        
        if not token or not channel:
            raise ValueError("Slack message cannot be sent; token and channel are required")
        
        # Create Slack client with resolved token
        slack_client = self._create_slack_client(token)
        
        # Send message using appropriate method based on content type
        if blocks:
            return slack_client.send_message_with_blocks(
                channel, blocks, message_text or "Message", slack_text, metadata, thread_ts
            )
        else:
            return slack_client.send_message(
                channel, message_text or "Empty message", action_buttons, slack_text, metadata, thread_ts
            )

    def update_message(
        self,
        channel_id: str,
        message_ts: str,
        message_text: str,
        token: str,
        action_buttons: Optional[List[Dict[str, Any]]] = None,
        slack_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update an existing Slack message."""
        slack_client = self._create_slack_client(token)
        return slack_client.update_message(
            channel_id, message_ts, message_text, action_buttons, slack_text, metadata
        )

    def send_ephemeral_message(
        self,
        channel_id: str,
        user_id: str,
        message_text: str,
        token: str,
        action_buttons: Optional[List[Dict[str, Any]]] = None,
        slack_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an ephemeral message to a user in a channel."""
        slack_client = self._create_slack_client(token)
        return slack_client.send_ephemeral_message(
            channel_id, user_id, message_text, action_buttons, slack_text
        )

    # ============================================================================
    # SECURITY AND PARSING METHODS (delegated to SlackSecurity)
    # ============================================================================



    # ============================================================================
    # BUSINESS LOGIC METHODS (delegated to SlackBusiness)
    # ============================================================================



    # ============================================================================
    # UTILITY METHODS (delegated to SlackUtilities)
    # ============================================================================

    def get_sport_group_mention(self, product_title: str) -> str:
        """Get sport group mention for a product."""
        return self.slack_utilities.get_sport_group_mention(product_title)

    def get_order_url(self, order_id: str, order_number: str) -> str:
        """Get formatted order URL."""
        return self.slack_utilities.get_order_url(order_id, order_number)

    def get_product_url(self, product_id: str) -> str:
        """Get formatted product URL."""
        return self.slack_utilities.get_product_url(product_id)

    def extract_sheet_link(self, message_text: str) -> str:
        """Extract sheet link from message text."""
        return self.slack_utilities.extract_sheet_link(message_text)

    def extract_season_start_info(self, message_text: str) -> Dict[str, Optional[str]]:
        """Extract season start info from message text."""
        return self.slack_utilities.extract_season_start_info(message_text)

    def extract_order_number(self, message_text: str) -> Optional[str]:
        """Extract order number from message text."""
        return self.slack_utilities.extract_order_number(message_text)

    def extract_email(self, message_text: str) -> Optional[str]:
        """Extract email address from message text."""
        return self.slack_utilities.extract_email(message_text)

    def extract_refund_amount(self, message_text: str) -> Optional[float]:
        """Extract refund amount from message text."""
        return self.slack_utilities.extract_refund_amount(message_text)

    # ============================================================================
    # ORDER HANDLING METHODS (delegated to OrderHandlers)
    # ============================================================================

    async def handle_cancel_order_request(
        self,
        order_number: str,
        refund_type: str,
        requestor_name: Dict[str, str],
        requestor_email: str,
        slack_user_id: str,
        slack_user_name: str,
        channel_id: str,
        thread_ts: str,
        current_message_text: str,
        trigger_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle order cancellation request from Slack."""
        return await self.order_handlers.handle_cancel_order_request(
            order_number, refund_type, requestor_name, requestor_email,
            slack_user_id, slack_user_name, channel_id, thread_ts,
            current_message_text, trigger_id
        )


# ============================================================================
# FACTORY FUNCTION (backward compatibility)
# ============================================================================

def create_slack_client(token: str, channel_id: str) -> SlackService:
    """Create a Slack client (backward compatibility)."""
    return SlackService(token=token, default_channel=channel_id)
