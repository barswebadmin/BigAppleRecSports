"""
Main Slack service - Table of Contents.
Provides a clean interface to all Slack functionality organized by concern.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple

# Slack SDK
from slack_sdk import WebClient

# Our systems
from config import Config
config = Config()
# from models.slack import Slack, RefundType, SlackMessageType

# Existing services
# from modules.orders.services import OrdersService

# Core functionality

from .client.slack_security import SlackSecurity
from .parsers.message_parsers import SlackMessageParsers

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
        from validator_collection import is_email
        import re
        from modules.integrations.slack.models.slack_user import SlackUser
        
        identifier = identifier.strip() if identifier else ""
        if not identifier:
            raise ValueError("Slack user identifier cannot be empty")
        
        params: Dict[str, Any] = {}
        
        # Check if it's a valid email
        if is_email(identifier):
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
    
    def lookup_group(
        self,
        identifier: str,
        bot_name: str = 'leadership'
    ) -> Optional[Dict[str, Any]]:
        """
        Look up a Slack usergroup by handle or ID.
        
        Args:
            identifier: Group handle (with or without @) or group ID (e.g., 'S03LZKQSHEU')
            bot_name: Name of the bot to use (default: 'leadership')
        
        Returns:
            Group dict if found, None otherwise
        """
        service = self.get_usergroup_service(bot_name)
        
        if identifier.startswith('S') and len(identifier) == 11 and identifier.isalnum():
            return service.get_group_by_id(identifier)
        else:
            handle = identifier.lstrip('@')
            return service.get_group_by_handle(handle)
    
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
    
    def lookup_user(
        self,
        identifier: Dict[str, Any],
        bot_name: str = 'leadership'
    ) -> Optional[Dict[str, Any]]:
        """
        Look up a Slack user by identifier.
        
        Args:
            identifier: Dict with keys: "email", "user_id", "handle", or "display_name"
            bot_name: Name of the bot to use (default: 'leadership')
        
        Returns:
            User dict if found, None otherwise
        """
        return self.resolve_user_identifier(identifier, bot_name)
    
    def list_users(
        self,
        bot_name: str = 'leadership',
        include_bots: bool = False,
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List all Slack users with optional filtering.
        
        Args:
            bot_name: Name of the bot to use (default: 'leadership')
            include_bots: If True, include bot accounts
            include_deleted: If True, include deleted users
        
        Returns:
            List of user dicts
        """
        from .user_lookup import list_all_users
        
        client = self.get_web_client(bot_name)
        users = list_all_users(client)
        
        if not include_bots:
            users = [u for u in users if not u.get('is_bot', False)]
        
        if not include_deleted:
            users = [u for u in users if not u.get('deleted', False)]
        
        return users
    
    def update_user_profile(
        self,
        user_id: str,
        profile_updates: Dict[str, Any],
        bot_name: str = 'leadership'
    ) -> Dict[str, Any]:
        """
        Update a Slack user's profile.
        
        Args:
            user_id: Slack user ID
            profile_updates: Dict of profile fields to update
            bot_name: Name of the bot to use (default: 'leadership')
        
        Returns:
            Dict with keys: 'success' (bool), 'response' (dict), 'error' (str, if failed), 'scope_info' (dict, if error)
        """
        import os
        from .client.main import SlackClient, SlackUserProfileUpdate
        
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
        
        user_token_env_map = {
            'leadership': 'SLACK.LEADERSHIP_BOT.USER_TOKEN',
        }
        
        user_token = None
        if bot_name in user_token_env_map:
            user_token = os.getenv(user_token_env_map[bot_name])
        
        client = SlackClient(token=bot.token, user_token=user_token)
        
        profile_update: SlackUserProfileUpdate = profile_updates  # type: ignore[assignment]
        
        result = client.update_user_profile(
            user_id=user_id,
            profile=profile_update
        )
        
        return result  # type: ignore[return-value]
    
    def extract_pronouns_from_display_name(self, display_name: str) -> Optional[str]:
        """
        Extract pronouns from display_name if present (typically in parentheses).
        
        Args:
            display_name: Display name string that may contain pronouns in parentheses
        
        Returns:
            Extracted pronouns string, or None if not found
        """
        import re
        
        if not display_name:
            return None
        
        match = re.search(r'\(([^)]+)\)', display_name)
        if match:
            return match.group(1)
        return None
    
    def append_pronouns_to_display_name(
        self,
        display_name: str,
        pronouns: Optional[str] = None
    ) -> str:
        """
        Append or replace pronouns in display_name.
        
        If pronouns are provided, removes any existing parentheses and appends new ones.
        If pronouns are None/empty, removes existing parentheses.
        
        Args:
            display_name: Current display_name (may already have pronouns in parentheses)
            pronouns: New pronouns to append, or None to remove
        
        Returns:
            Updated display_name with pronouns appended or removed
        """
        import re
        
        if not display_name:
            return display_name
        
        base_name = re.sub(r'\s*\([^)]+\)\s*$', '', display_name).rstrip()
        
        if not pronouns:
            return base_name
        
        return f"{base_name} ({pronouns})"
    
    def sync_pronouns_with_display_name(
        self,
        profile_updates: Dict[str, Any],
        current_profile: Dict[str, Any],
        pronouns: Optional[str] = None
    ) -> None:
        """
        Sync pronouns with display_name in profile_updates.
        
        If pronouns are provided, updates display_name to include them.
        If display_name is updated and pronouns exist, preserves pronouns in display_name.
        
        Args:
            profile_updates: Dictionary of profile updates to modify (modified in place)
            current_profile: Current user profile dict
            pronouns: Optional new pronouns value (if None, uses current profile pronouns)
        """
        if pronouns is None:
            profile = current_profile.get('profile', {}) if isinstance(current_profile, dict) else getattr(current_profile, 'profile', {})
            pronouns = profile.get('pronouns') if isinstance(profile, dict) else getattr(profile, 'pronouns', None)
        
        display_name_to_update = profile_updates.get('display_name')
        if not display_name_to_update:
            if isinstance(current_profile, dict):
                profile = current_profile.get('profile', {})
                display_name_to_update = profile.get('display_name', '') if isinstance(profile, dict) else ''
            else:
                display_name_to_update = getattr(current_profile, 'display_name', '') or ''
        
        updated_display_name = self.append_pronouns_to_display_name(display_name_to_update, pronouns)
        
        if updated_display_name:
            profile_updates["display_name"] = updated_display_name
            profile_updates["display_name_normalized"] = updated_display_name
    
    def build_profile_updates(
        self,
        profile_fields: Dict[str, Any],
        current_user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build profile_updates dictionary from field values.
        
        Handles special formatting (e.g., status_emoji) and syncs pronouns with display_name.
        
        Args:
            profile_fields: Dictionary of field values from command-line flags or other input
            current_user: Current user dict
        
        Returns:
            Dictionary of profile updates ready for API call
        """
        profile_updates = {}
        
        for field, value in profile_fields.items():
            if value:
                if field == 'status_emoji':
                    emoji = value
                    if not emoji.startswith(":"):
                        emoji = f":{emoji}"
                    if not emoji.endswith(":"):
                        emoji = f"{emoji}:"
                    profile_updates[field] = emoji
                else:
                    profile_updates[field] = value
        
        if 'pronouns' in profile_updates:
            self.sync_pronouns_with_display_name(profile_updates, current_user, profile_updates['pronouns'])
        
        if 'display_name' in profile_updates and 'pronouns' not in profile_updates:
            self.sync_pronouns_with_display_name(profile_updates, current_user)
        
        return profile_updates

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

        return {"text": "✅ Modal submission received"}




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
        # Refund-related actions removed - functionality deprecated
        logger.warning(f"Refund-related action '{action_id}' received but functionality has been removed")
        return {
            "response_type": "ephemeral",
            "text": f"Refund functionality has been removed. Action '{action_id}' is no longer supported.",
        }




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
