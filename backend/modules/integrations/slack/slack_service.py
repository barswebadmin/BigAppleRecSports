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
from config import config
from config_old_deprecated.slack import SlackBot, SlackChannel
# from models.slack import Slack, RefundType, SlackMessageType

# Existing services
# from modules.orders.services import OrdersService

# Core functionality

from .client.main import SlackClient
from .client.slack_security import SlackSecurity
from .parsers.message_parsers import SlackMessageParsers
from .builders import (
    SlackMessageBuilder,
    # ModernMessageBuilder,
    # SlackCacheManager,
    # SlackMetadataBuilder,
    # SlackOrderHandlers,
)

logger = logging.getLogger(__name__)


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
        # self.orders_service = OrdersService()
        
        # Get configuration from our new system
        self.config = config
        self.security = SlackSecurity()
        
        # Initialize core components (no token storage in service)
        # SlackClient will be created on-demand with provided tokens
        self.slack_client = None  # Will be created per-operation with specific token

        # self.slack_security = SlackSecurity(self.config.SlackBot.get_signing_secret())

        # Initialize helper components
        self.message_builder = SlackMessageBuilder(self.config.SlackGroup.all())
        # self.refunds_utils = SlackRefundsUtils(
        #     self.orders_service, 
        #     self._get_settings(),
        #     self.message_builder
        # )
        self.message_parsers = SlackMessageParsers()
        
        # Initialize modern utility classes
        # self.modern_message_builder = ModernMessageBuilder()
        # self.cache_manager = self._get_cache_manager()
        # self.metadata_builder = SlackMetadataBuilder()
        # self.message_parsers = self._get_message_parsers()
        # self.order_handlers = SlackOrderHandlers(self.orders_service, self, self.message_builder)

    # ============================================================================
    # IDENTIFIER NORMALIZATION METHODS (for CLI parameter types)
    # ============================================================================
    
    @staticmethod
    def normalize_user_identifier(identifier: str) -> Dict[str, Any]:
        """Convert Slack user identifier input to dict format.
        
        Slack users can be identified by:
        - Email address
        - User ID (e.g., U03LZKQSHEU)
        - Handle/username (e.g., "jrandazzo")
        - Display name (e.g., "John Randazzo")
        
        Args:
            identifier: Raw identifier string from user input
            
        Returns:
            Dict with keys: "email", "user_id", "handle", or "display_name"
            
        Raises:
            ValueError: If identifier format is invalid
        """
        import validators
        import re
        from modules.integrations.slack.models.slack_user import SlackUser
        
        identifier = identifier.strip() if identifier else ""
        if not identifier:
            raise ValueError("Slack user identifier cannot be empty")
        
        params: Dict[str, Any] = {}
        
        # Check if it's a valid email
        if validators.email(identifier):
            params["email"] = identifier
            return params
        
        # Check if it's a valid Slack user ID using model validation
        if SlackUser.is_valid_user_id(identifier):
            params["user_id"] = identifier
            return params
        
        # Check if it's a valid handle (username)
        # Slack usernames are 1-80 characters, alphanumeric, hyphens, underscores, periods
        # Cannot start with period
        if re.match(r'^[a-zA-Z0-9_-][a-zA-Z0-9_.-]{0,79}$', identifier):
            params["handle"] = identifier
            return params
        
        # Otherwise, treat as display name (can contain spaces and other characters)
        # Display names are typically 1-80 characters but can be longer
        if len(identifier) > 0:
            params["display_name"] = identifier
            return params
        
        raise ValueError(
            f"Invalid Slack user identifier: '{identifier}'\n"
            f"   Must be a valid email, user ID (e.g., U03LZKQSHEU), handle, or display name"
        )
    
    @staticmethod
    def normalize_channel_identifier(identifier: str) -> Dict[str, Any]:
        """Convert Slack channel identifier input to dict format.
        
        Slack channels can be identified by channel ID (e.g., C092RU7R6PL) or name
        (e.g., "general", "#general", "kickball-leadership").
        
        Channel names can contain:
        - Alphanumeric characters
        - Hyphens (-)
        - Underscores (_)
        - Optional leading hash (#)
        
        Args:
            identifier: Raw identifier string from user input
            
        Returns:
            Dict with keys: "channel_id" or "name"
            
        Raises:
            ValueError: If identifier format is invalid
        """
        import re
        from modules.integrations.slack.models.slack_channel import SlackChannel
        
        identifier = identifier.strip() if identifier else ""
        if not identifier:
            raise ValueError("Slack channel identifier cannot be empty")
        
        params: Dict[str, Any] = {}
        
        # Check if it's a valid Slack channel ID using model validation
        if SlackChannel.is_valid_channel_id(identifier):
            params["channel_id"] = identifier
            return params
        
        # Check if it's a valid channel name
        # Remove leading # if present
        name = identifier.lstrip('#')
        
        # Validate channel name: alphanumeric, hyphens, underscores only
        # Slack channel names must be 1-80 characters
        if not name:
            raise ValueError(
                f"Invalid Slack channel identifier: '{identifier}'\n"
                f"   Channel name cannot be empty (only '#' provided)"
            )
        
        if len(name) > 80:
            raise ValueError(
                f"Invalid Slack channel identifier: '{identifier}'\n"
                f"   Channel name must be 80 characters or less, got {len(name)}"
            )
        
        # Validate characters: alphanumeric, hyphens, underscores only
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            raise ValueError(
                f"Invalid Slack channel identifier: '{identifier}'\n"
                f"   Channel name can only contain alphanumeric characters, hyphens, and underscores"
            )
        
        params["name"] = name
        return params
    
    @staticmethod
    def normalize_group_identifier(identifier: str) -> Dict[str, Any]:
        """Convert Slack usergroup identifier input to dict format.
        
        Slack usergroups can be identified by:
        - Group ID (e.g., S03LZKQSHEU)
        - Handle (e.g., "leadership", "@leadership", "dodgeball-monday")
        - Name (e.g., "Leadership Team", "#leadership")
        
        Usergroup handles/names can contain:
        - Alphanumeric characters
        - Hyphens (-)
        - Underscores (_)
        - Optional leading @ or #
        
        Args:
            identifier: Raw identifier string from user input
            
        Returns:
            Dict with keys: "group_id", "handle", or "name"
            
        Raises:
            ValueError: If identifier format is invalid
        """
        import re
        
        identifier = identifier.strip() if identifier else ""
        if not identifier:
            raise ValueError("Slack usergroup identifier cannot be empty")
        
        params: Dict[str, Any] = {}
        
        # Check if it's a valid Slack usergroup ID
        # Usergroup IDs start with 'S' and are 11 characters long, alphanumeric
        if identifier.startswith('S') and len(identifier) == 11 and identifier.isalnum():
            params["group_id"] = identifier
            return params
        
        # Check if it's a valid handle/name
        # Remove leading @ or # if present (normalize both for convenience)
        name = identifier.lstrip('@#')
        
        # Validate name: alphanumeric, hyphens, underscores only
        # Slack usergroup handles/names must be 1-255 characters
        if not name:
            raise ValueError(
                f"Invalid Slack usergroup identifier: '{identifier}'\n"
                f"   Name/handle cannot be empty (only '@' or '#' provided)"
            )
        
        if len(name) > 255:
            raise ValueError(
                f"Invalid Slack usergroup identifier: '{identifier}'\n"
                f"   Name/handle must be 255 characters or less, got {len(name)}"
            )
        
        # Validate characters: alphanumeric, hyphens, underscores only
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            raise ValueError(
                f"Invalid Slack usergroup identifier: '{identifier}'\n"
                f"   Name/handle can only contain alphanumeric characters, hyphens, and underscores"
            )
        
        # Return as "name" to match user's request (handle and name are often the same in practice)
        params["name"] = name
        return params

    # ============================================================================
    # CLIENT AND SERVICE FACTORY METHODS (for CLI commands)
    # ============================================================================
    
    def get_web_client(self, bot_name: str = 'leadership') -> WebClient:
        """Get a WebClient instance for a specific bot.
        
        Args:
            bot_name: Name of the bot (dev, exec, leadership, etc.)
            
        Returns:
            WebClient instance with bot token configured
            
        Raises:
            ValueError: If bot name is invalid
        """
        bot_name = bot_name.lower()
        
        bot_map = {
            'dev': self.config.Slack.Bots.Dev,
            'exec': self.config.Slack.Bots.Exec,
            'leadership': self.config.Slack.Bots.Leadership,
            'payment_assistance': self.config.Slack.Bots.PaymentAssistance,
            'refunds': self.config.Slack.Bots.Refunds,
            'registrations': self.config.Slack.Bots.Registrations,
            'web': self.config.Slack.Bots.Web,
        }
        
        bot = bot_map.get(bot_name)
        if not bot:
            available = ', '.join(bot_map.keys())
            raise ValueError(
                f"Unknown bot: {bot_name}. Available: {available}"
            )
        
        return WebClient(token=bot.token)
    
    def get_usergroup_service(self, bot_name: str = 'leadership') -> 'UsergroupService':  # type: ignore
        """Get a UsergroupService instance for a specific bot.
        
        Args:
            bot_name: Name of the bot (dev, exec, leadership, etc.)
            
        Returns:
            UsergroupService instance with WebClient configured
            
        Raises:
            ValueError: If bot name is invalid
        """
        from .services import UsergroupService
        client = self.get_web_client(bot_name)
        return UsergroupService(client)
    
    def get_usergroup_provisioner(self, bot_name: str = 'leadership') -> 'UsergroupProvisioner':  # type: ignore
        """Get a UsergroupProvisioner instance for a specific bot.
        
        Args:
            bot_name: Name of the bot (dev, exec, leadership, etc.)
            
        Returns:
            UsergroupProvisioner instance with UsergroupService configured
            
        Raises:
            ValueError: If bot name is invalid
        """
        from .services import UsergroupProvisioner
        service = self.get_usergroup_service(bot_name)
        return UsergroupProvisioner(service)
    
    def resolve_group_identifier(self, identifier: Dict[str, Any], bot_name: str = 'leadership') -> Optional[Dict[str, Any]]:
        """Resolve a group identifier dict to a group dict.
        
        Args:
            identifier: Dict with keys: "group_id", "name", or "handle"
            bot_name: Name of the bot to use
            
        Returns:
            Group dict if found, None otherwise
        """
        service = self.get_usergroup_service(bot_name)
        
        if 'group_id' in identifier:
            return service.get_group_by_id(identifier['group_id'])
        elif 'name' in identifier:
            # Try handle first (most common)
            group_data = service.get_group_by_handle(identifier['name'])
            if group_data:
                return group_data
            # Try name field
            groups = service.list_groups(include_disabled=True)
            return next((g for g in groups if g.get('name') == identifier['name']), None)
        
        return None
    
    def resolve_user_identifier(self, identifier: Dict[str, Any], bot_name: str = 'leadership') -> Optional[Dict[str, Any]]:
        """Resolve a user identifier dict to a user dict.
        
        Args:
            identifier: Dict with keys: "email", "user_id", "handle", or "display_name"
            bot_name: Name of the bot to use
            
        Returns:
            User dict if found, None otherwise
        """
        from .user_lookup import lookup_user, list_all_users
        from .client.main import SlackUserIdentifier
        
        client = self.get_web_client(bot_name)
        
        if 'user_id' in identifier:
            lookup_id = SlackUserIdentifier(user_id=identifier['user_id'])
            return lookup_user(client, lookup_id)
        elif 'email' in identifier:
            lookup_id = SlackUserIdentifier(email=identifier['email'])
            return lookup_user(client, lookup_id)
        elif 'handle' in identifier or 'display_name' in identifier:
            # Search through all users (this is less efficient but necessary)
            search_term = identifier.get('handle') or identifier.get('display_name', '')
            users = list_all_users(client)
            
            for user_dict in users:
                # Check handle (name field)
                if identifier.get('handle') and user_dict.get('name', '').lower() == search_term.lower():
                    return user_dict
                # Check display_name
                if identifier.get('display_name'):
                    profile = user_dict.get('profile', {})
                    display_name = profile.get('display_name', '') or profile.get('real_name', '')
                    if display_name.lower() == search_term.lower():
                        return user_dict
        
        return None

    # ============================================================================
    # CONVENIENCE METHODS FOR TESTING
    # ============================================================================
    
    def verify_slack_signature(self, body: bytes, timestamp: str, signature: str) -> bool:
        """Convenience method for tests - delegates to slack_security"""
        return self.security.verify_slack_signature(body, timestamp, signature)

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
                signature_valid = self.security.verify_slack_signature(body, timestamp, signature)
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
                request_data = self.security.parse_button_value(action_value)

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
        current_message_full_text = self.security.extract_text_from_blocks(current_message_blocks)

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



    # def _get_cache_manager(self):
    #     """Get cache manager instance."""
    #     return SlackCacheManager()





    # ============================================================================
    # ORDER HANDLING METHODS (delegated to OrderHandlers)
    # ============================================================================

    # async def handle_cancel_order_request(
    #     self,
    #     order_number: str,
    #     refund_type: str,
    #     requestor_name: Dict[str, str],
    #     requestor_email: str,
    #     slack_user_id: str,
    #     slack_user_name: str,
    #     channel_id: str,
    #     thread_ts: str,
    #     current_message_text: str,
    #     trigger_id: Optional[str] = None,
    # ) -> Dict[str, Any]:
    #     """Handle order cancellation request from Slack."""
    #     return await self.order_handlers.handle_cancel_order_request(
    #         order_number, refund_type, requestor_name, requestor_email,
    #         slack_user_id, slack_user_name, channel_id, thread_ts,
    #         current_message_text, trigger_id
    #     )


# ============================================================================
# FACTORY FUNCTION (backward compatibility)
# ============================================================================


def create_slack_client(token: str, channel_id: str) -> SlackService:
    """Create a Slack client (backward compatibility)."""
    return SlackService(token=token, default_channel=channel_id)
