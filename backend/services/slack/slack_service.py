"""
Main Slack service for handling refund notifications.
Refactored to use helper modules for better organization.
"""

from typing import Dict, Any, Optional, List
import logging
import hashlib
import hmac
import time
from config import settings
from .message_builder import SlackMessageBuilder
from .slack_refunds_utils import SlackRefundsUtils
from services.orders import OrdersService
from .api_client import SlackApiClient, MockSlackApiClient, _is_test_mode

logger = logging.getLogger(__name__)


class SlackService:
    """
    Main service for handling Slack notifications for refund requests.

    This service coordinates message building and API communication
    through specialized helper classes.
    """

    def __init__(self):
        # Consistent test mode detection for all configurations
        is_test_mode = _is_test_mode()
        is_production = settings.environment == "production" and not is_test_mode

        self.refunds_channel = {
            "name": "#registration-refunds" if is_production else "#joe-test",
            "channel_id": "C08J1EN7SFR" if is_production else "C092RU7R6PL",
            "bearer_token": settings.active_slack_bot_token or "",
        }

        # Sport-specific team mentions
        # Production team mentions:
        sport_groups_production = {
            "kickball": "<!subteam^S08L2521XAM>",
            "bowling": "<!subteam^S08KJJ02738>",
            "pickleball": "<!subteam^S08KTJ33Z9R>",
            "dodgeball": "<!subteam^S08KJJ5CL4W>",
        }

        # Testing configuration - all sports tag personal channel
        sport_groups_joe_testing = {
            "kickball": "<@U0278M72535>",
            "bowling": "<@U0278M72535>",
            "pickleball": "<@U0278M72535>",
            "dodgeball": "<@U0278M72535>",
        }

        self.sport_groups = (
            sport_groups_production if is_production else sport_groups_joe_testing
        )

        self.orders_service = OrdersService()
        self.settings = settings

        # Initialize helper components
        self.message_builder = SlackMessageBuilder(self.sport_groups)
        self.refunds_utils = SlackRefundsUtils(
            self.orders_service, self.settings, self.message_builder
        )

        # Use mock API client during tests and development to prevent real Slack requests
        logger.info(
            f"🔍 BACKEND DEBUG: env='{settings.environment}', test_mode={is_test_mode}, debug_mode={settings.environment.lower() in ['development', 'debug', 'test']}"
        )

        if is_test_mode or settings.environment.lower() in [
            "development",
            "debug",
            "test",
        ]:
            logger.info("🧪 Test/Debug mode detected - using MockSlackApiClient")
            self.api_client = MockSlackApiClient(
                self.refunds_channel["bearer_token"], self.refunds_channel["channel_id"]
            )
        else:
            logger.info("🚀 Production mode - using real SlackApiClient")
            self.api_client = SlackApiClient(
                self.refunds_channel["bearer_token"], self.refunds_channel["channel_id"]
            )

        # Deduplication cache - stores message hashes to prevent duplicates
        # Format: {message_hash: timestamp}
        self._message_cache = {}
        self._cache_expiry_seconds = 300  # 5 minutes

    def _generate_message_hash(
        self, order_data: Dict[str, Any], requestor_info: Dict[str, Any]
    ) -> str:
        """
        Generate a unique hash for deduplication based on order and requestor info.
        This prevents the same refund request from being posted multiple times.
        """
        try:
            order = order_data.get("order", {}) if order_data else {}
            order_number = (
                order.get("orderNumber")
                or order.get("orderName")
                or order.get("name")
                or "unknown"
            )
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
                key
                for key, timestamp in self._message_cache.items()
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
                    logger.info(
                        f"🔄 Duplicate message detected (hash: {message_hash[:8]}...)"
                    )
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

    def _resolve_channel_and_mention_strategy(
        self, slack_channel_name: Optional[str], mention_strategy: Optional[str]
    ) -> tuple:
        """
        Resolve the target channel and mention strategy based on parameters and environment.

        Priority:
        1. Use provided query parameters if they exist in config
        2. Only fallback to environment defaults if parameters are None or not found in config

        Returns: (channel_config, resolved_mention_strategy)
        """
        is_dev = self.settings.environment.lower() in ["development", "debug", "test"]

        # Resolve channel - prioritize query parameter
        channel_config = None

        if slack_channel_name is not None:
            # Query parameter was provided - try to use it
            if slack_channel_name in self.settings.slack_channels:
                # Found in config - use it
                channel_config = self.settings.slack_channels[slack_channel_name]
            else:
                # Provided but not found in config - use hardcoded fallback
                # This ensures invalid channel names don't silently use environment defaults
                channel_config = {
                    "channelId": "C092RU7R6PL" if is_dev else "C08J1EN7SFR",
                    "name": "#joe-test" if is_dev else "#registration-refunds",
                }
        else:
            # No query parameter provided - use environment-based defaults
            if is_dev:
                channel_config = self.settings.slack_channels.get("joe-test")
            else:
                channel_config = self.settings.slack_channels.get("refund-requests")

            # If environment default not found in config, use hardcoded fallback
            if not channel_config:
                channel_config = {
                    "channelId": "C092RU7R6PL" if is_dev else "C08J1EN7SFR",
                    "name": "#joe-test" if is_dev else "#registration-refunds",
                }

        # Resolve mention strategy - prioritize query parameter
        if mention_strategy is not None:
            # Query parameter was provided - use it as-is (even if empty string)
            resolved_mention_strategy = mention_strategy
        else:
            # No query parameter provided - use environment-based defaults
            resolved_mention_strategy = "user|joe" if is_dev else "sportAliases"

        return channel_config, resolved_mention_strategy

    def _resolve_mention(self, product_title: str, mention_strategy: str) -> str:
        """
        Resolve the mention based on the strategy.

        Args:
            product_title: Product title to check for sport
            mention_strategy: Strategy for mentions - "sportAliases", "user|{name}", or empty string

        Returns:
            Resolved mention string
        """
        # Handle empty string strategy (explicit empty strategy from query param)
        if mention_strategy == "":
            # Empty string means no mention - could return empty or fallback to joe
            return self.settings.slack_users.get("joe", "<@U0278M72535>")

        # Handle user mention strategy
        if mention_strategy and "|" in mention_strategy:
            strategy_parts = mention_strategy.split("|", 1)
            if len(strategy_parts) == 2 and strategy_parts[0] == "user":
                user_name = strategy_parts[1]
                if user_name in self.settings.slack_users:
                    return self.settings.slack_users[user_name]
                # Invalid user name - fallback
                return self.settings.slack_users.get("joe", "<@U0278M72535>")

        # Handle sport aliases strategy
        if mention_strategy == "sportAliases":
            product_lower = product_title.lower()
            for sport, subgroup_mention in self.settings.slack_subgroups.items():
                if sport in product_lower:
                    return subgroup_mention
            # No sport found, fallback to @here
            return "@here"

        # Fallback to joe's user ID for any unrecognized strategy
        return self.settings.slack_users.get("joe", "<@U0278M72535>")

    def send_refund_request_notification(
        self,
        requestor_info: Dict[str, Any],
        sheet_link: str,
        order_data: Optional[Dict[str, Any]] = None,
        refund_calculation: Optional[Dict[str, Any]] = None,
        error_type: Optional[str] = None,
        raw_order_number: Optional[str] = None,
        order_customer_email: Optional[str] = None,
        existing_refunds_data: Optional[Dict[str, Any]] = None,
        request_initiated_at: Optional[str] = None,
        slack_channel_name: Optional[str] = None,
        mention_strategy: Optional[str] = None,
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
            # Check if we need custom channel/mention behavior
            # Only use custom config if parameters are provided AND meaningful
            using_custom_config = (
                slack_channel_name is not None and slack_channel_name.strip()
            ) or (mention_strategy is not None and mention_strategy.strip())

            if using_custom_config:
                # Resolve target channel and mention strategy
                channel_config, resolved_mention_strategy = (
                    self._resolve_channel_and_mention_strategy(
                        slack_channel_name, mention_strategy
                    )
                )

                # Create dynamic API client for the resolved channel

                # Note: Now using unified Slack client instead of dynamic API client creation

                # Create a dynamic message builder with resolved mention strategy
                from .message_builder import SlackMessageBuilder

                dynamic_message_builder = SlackMessageBuilder(self.sport_groups)

                # Override the get_sport_group_mention method to use our resolved strategy
                def dynamic_mention_resolver(product_title: str) -> str:
                    return self._resolve_mention(
                        product_title, resolved_mention_strategy
                    )

                dynamic_message_builder.get_sport_group_mention = (
                    dynamic_mention_resolver
                )

                logger.info(
                    f"Using custom config - Channel: {channel_config['name']}, Strategy: {resolved_mention_strategy}"
                )
            else:
                # Use default configuration for backward compatibility
                dynamic_message_builder = self.message_builder
                channel_config = self.refunds_channel
                logger.info(f"Using default config - Channel: {channel_config['name']}")

            # Generate message hash for deduplication
            message_hash = self._generate_message_hash(order_data or {}, requestor_info)

            # Check for duplicates
            if self._is_duplicate_message(message_hash):
                logger.info("🔄 Skipping duplicate message")
                return {
                    "success": True,
                    "message": "Duplicate message skipped",
                    "duplicate": True,
                }

            # Build the appropriate message based on available data
            if order_data and refund_calculation and refund_calculation.get("success"):
                # Full success message with calculated refund
                message_data = dynamic_message_builder.build_success_message(
                    order_data=order_data,
                    refund_calculation=refund_calculation,
                    requestor_info=requestor_info,
                    sheet_link=sheet_link,
                    request_initiated_at=request_initiated_at,
                    slack_channel_name=slack_channel_name,
                    mention_strategy=mention_strategy,
                )

            elif error_type:
                # Error message for various failure scenarios
                customer_orders_url = None

                # For email mismatch, try to get customer-specific orders URL
                if error_type == "email_mismatch" and requestor_info:
                    requestor_email = requestor_info.get("email", "")
                    if requestor_email:
                        customer_orders_url = self._get_customer_orders_url(
                            requestor_email
                        )

                message_data = dynamic_message_builder.build_error_message(
                    error_type=error_type,
                    requestor_info=requestor_info,
                    sheet_link=sheet_link,
                    raw_order_number=raw_order_number or "",
                    order_customer_email=order_customer_email or "",
                    order_data=order_data,
                    customer_orders_url=customer_orders_url,
                    existing_refunds_data=existing_refunds_data,
                )

            elif order_data:
                # Fallback message when order is found but calculation failed
                error_message = ""
                if refund_calculation:
                    error_message = refund_calculation.get("message", "")

                message_data = dynamic_message_builder.build_fallback_message(
                    order_data=order_data,
                    requestor_info=requestor_info,
                    sheet_link=sheet_link,
                    error_message=error_message,
                )

            else:
                # Generic error message
                message_data = dynamic_message_builder.build_error_message(
                    error_type="unknown",
                    requestor_info=requestor_info,
                    sheet_link=sheet_link,
                )

            # Send the message using the dynamic API client with blocks and action buttons
            logger.info(f"Sending refund notification to {channel_config['name']}")

            # Log message details for debugging
            slack_text = message_data.get(
                "slack_text", "New refund request notification"
            )
            print("📤 === SLACK MESSAGE SEND ===")
            print(f"📋 Message Type: {slack_text}")
            print(f"📍 Channel: {channel_config.get('channelId', 'unknown')}")

            # Add metadata to preserve channel and mention strategy for interactions
            metadata = {}
            if slack_channel_name:
                metadata["originalChannel"] = slack_channel_name
            if mention_strategy:
                metadata["originalMention"] = mention_strategy

            # Use unified Slack client instead of dynamic client
            from .unified_slack_client import slack_client

            result = slack_client.send_message(
                channel_id=channel_config["channelId"],
                bearer_token=channel_config.get(
                    "botToken", settings.active_slack_bot_token or ""
                ),
                message_text=message_data["text"],
                action_buttons=message_data.get("action_buttons", []),
                slack_text=slack_text,
                metadata=metadata,
            )

            if result["success"]:
                logger.info("Refund notification sent successfully to Slack")
            else:
                logger.error(
                    f"Failed to send refund notification to Slack: {result.get('error')}"
                )
                # Remove from cache if sending failed, allow retry
                if message_hash in self._message_cache:
                    del self._message_cache[message_hash]

            return result

        except Exception as e:
            logger.error(
                f"Unexpected error in send_refund_request_notification: {str(e)}"
            )
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

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
        product_id_digits = (
            product_id.split("/")[-1] if "/" in product_id else product_id
        )
        return f"https://admin.shopify.com/store/09fe59-3/products/{product_id_digits}"

    def _get_request_type_text(self, refund_type: str) -> str:
        """Get request type text (wrapper for tests)"""
        return self.message_builder._get_request_type_text(refund_type)

    def _get_sheet_link_line(self, sheet_link: Optional[str]) -> str:
        """Get formatted sheet link line (wrapper for tests)"""
        return self.message_builder._get_sheet_link_line(sheet_link)

    def _get_requestor_line(
        self, requestor_name: Dict[str, str], requestor_email: str
    ) -> str:
        """Get formatted requestor line (wrapper for tests)"""
        return self.message_builder._get_requestor_line(requestor_name, requestor_email)

    def _get_optional_request_notes(self, notes: Optional[str]) -> str:
        """Get formatted optional notes (wrapper for tests)"""
        return self.message_builder._get_optional_request_notes(notes or "")

    def _send_slack_message(
        self,
        channel_id: str,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
        thread_ts: Optional[str] = None,
    ) -> Dict[str, Any]:
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

    def update_slack_message(
        self,
        channel_id: str,
        message_ts: str,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Update an existing Slack message (wrapper for compatibility)"""
        # Extract message text from blocks if needed
        message_text = text
        if blocks:
            for block in blocks:
                if block.get("type") == "section" and "text" in block:
                    message_text = block["text"]["text"]
                    break

        return self.api_client.update_message(message_ts, message_text)

    def _create_standard_blocks(
        self,
        text: str,
        include_actions: bool = False,
        action_buttons: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Create standard Slack message blocks (wrapper for compatibility)"""
        return self.api_client._create_standard_blocks(
            text, action_buttons if include_actions else None
        )

    def should_update_slack_on_shopify_failure(self) -> bool:
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
        self,
        message_ts: str,
        success_message: str,
        action_buttons: Optional[List[Dict]] = None,
    ) -> bool:
        """
        Update Slack message only for successful Shopify operations.
        Returns True if update was attempted, False if skipped.
        """
        try:
            update_result = self.api_client.update_message(
                message_ts=message_ts,
                message_text=success_message,
                action_buttons=action_buttons or [],
            )

            if update_result.get("success", False):
                logger.info(
                    "✅ Slack message updated successfully after Shopify success"
                )
                return True
            else:
                logger.error(
                    f"❌ Slack message update failed: {update_result.get('error', 'Unknown error')}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Exception during Slack message update: {str(e)}")
            return False

    def send_ephemeral_error_to_user(
        self,
        channel_id: str,
        user_id: str,
        error_message: str,
        operation_name: str = "operation",
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
                            "text": f"❌ **{operation_name.title()} Failed**\n\n{error_message}",
                        },
                    }
                ],
            }

            # Send ephemeral message via Slack API
            result = self.api_client.send_ephemeral_message(ephemeral_payload)

            if result.get("success", False):
                logger.info(f"✅ Sent ephemeral error message to user {user_id}")
                return True
            else:
                logger.error(
                    f"❌ Failed to send ephemeral message: {result.get('error', 'Unknown error')}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Exception sending ephemeral error message: {str(e)}")
            return False

    def send_modal_error_to_user(
        self, trigger_id: str, error_message: str, operation_name: str = "operation"
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
            cleaned_message = error_message.replace("**", "*").replace("•", "-")

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
                "title": {"type": "plain_text", "text": title_text},
                "close": {"type": "plain_text", "text": "Close"},
                "blocks": [
                    {"type": "section", "text": {"type": "mrkdwn", "text": modal_text}}
                ],
            }

            logger.info(f"📱 Sending modal with trigger_id: {trigger_id[:20]}...")
            logger.debug(f"📱 Modal title: '{title_text}' (length: {len(title_text)})")
            logger.debug(f"📱 Modal text length: {len(modal_text)}")
            logger.debug(f"📱 Modal view: {modal_view}")

            # Send modal via Slack API
            result = self.api_client.send_modal(trigger_id, modal_view)

            if result.get("success", False):
                logger.info(f"✅ Sent modal error dialog for {operation_name}")
                return True
            else:
                logger.error(
                    f"❌ Failed to send modal dialog: {result.get('error', 'Unknown error')}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Exception sending modal error dialog: {str(e)}")
            return False

    def update_slack_on_shopify_failure(
        self,
        message_ts: str,
        error_message: str,
        operation_name: str = "Shopify operation",
    ) -> bool:
        """
        Update Slack message for failed Shopify operations.
        Only updates if should_update_slack_on_shopify_failure() returns True.
        """
        if not self.should_update_slack_on_shopify_failure():
            logger.info(
                f"⏭️ Skipping Slack update for {operation_name} failure (configured to skip)"
            )
            return False

        try:
            update_result = self.api_client.update_message(
                message_ts=message_ts, message_text=error_message, action_buttons=[]
            )

            if update_result.get("success", False):
                logger.info(
                    f"✅ Slack error message updated for {operation_name} failure"
                )
                return True
            else:
                logger.error(
                    f"❌ Slack error message update failed: {update_result.get('error', 'Unknown error')}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Exception during Slack error message update: {str(e)}")
            return False

    def verify_slack_signature(
        self, body: bytes, timestamp: str, signature: str
    ) -> bool:
        """Verify that the request came from Slack"""
        if not self.settings.slack_signing_secret:
            logger.warning(
                "No Slack signing secret configured - skipping signature verification"
            )
            return True  # Skip verification in development

        # Create the signature base string
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"

        # Create the expected signature
        expected_signature = (
            "v0="
            + hmac.new(
                self.settings.slack_signing_secret.encode(),
                sig_basestring.encode(),
                hashlib.sha256,
            ).hexdigest()
        )

        # Compare signatures
        return hmac.compare_digest(expected_signature, signature)

    def parse_button_value(self, value: str) -> Dict[str, str]:
        """Parse button value like 'rawOrderNumber=#12345|orderId=gid://shopify/Order/12345|refundAmount=36.00'"""
        request_data = {}
        button_values = value.split("|")

        for button_value in button_values:
            if "=" in button_value:
                key, val = button_value.split("=", 1)  # Split only on first =
                request_data[key] = val

        return request_data

    def extract_text_from_blocks(self, blocks: list) -> str:
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
                                    if (
                                        isinstance(sub_element, dict)
                                        and "text" in sub_element
                                    ):
                                        text_parts.append(sub_element["text"])

            return "\n".join(text_parts)

        except Exception as e:
            logger.error(f"Error extracting text from blocks: {e}")
            return ""

    # Forwarding from SlackRefundsUtils
    async def handle_cancel_order(
        self,
        request_data: Dict[str, str],
        channel_id: str,
        requestor_name: Dict[str, str],
        requestor_email: str,
        thread_ts: str,
        slack_user_id: str,
        slack_user_name: str,
        current_message_full_text: str,
        trigger_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self.refunds_utils.handle_cancel_order(
            request_data,
            channel_id,
            requestor_name,
            requestor_email,
            thread_ts,
            slack_user_id,
            slack_user_name,
            current_message_full_text,
            trigger_id,
        )

    async def handle_proceed_without_cancel(
        self,
        request_data: Dict[str, str],
        channel_id: str,
        requestor_name: Dict[str, str],
        requestor_email: str,
        thread_ts: str,
        slack_user_id: str,
        slack_user_name: str,
        current_message_full_text: str,
        trigger_id: Optional[str] = None,
        original_channel: Optional[str] = None,
        original_mention: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self.refunds_utils.handle_proceed_without_cancel(
            request_data,
            channel_id,
            requestor_name,
            requestor_email,
            thread_ts,
            slack_user_id,
            slack_user_name,
            current_message_full_text,
            trigger_id,
            original_channel,
            original_mention,
        )

    async def handle_deny_refund_request_show_modal(
        self,
        request_data: Dict[str, str],
        channel_id: str,
        thread_ts: str,
        slack_user_name: str,
        slack_user_id: str,
        trigger_id: str,
        current_message_full_text: str,
    ) -> Dict[str, Any]:
        return await self.refunds_utils.handle_deny_refund_request_show_modal(
            request_data,
            channel_id,
            thread_ts,
            slack_user_name,
            slack_user_id,
            trigger_id,
            current_message_full_text,
        )

    async def handle_process_refund(
        self,
        request_data: Dict[str, str],
        channel_id: str,
        requestor_name: Dict[str, str],
        requestor_email: str,
        thread_ts: str,
        slack_user_name: str,
        current_message_full_text: str,
        slack_user_id: str = "",
        trigger_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self.refunds_utils.handle_process_refund(
            request_data,
            channel_id,
            requestor_name,
            requestor_email,
            thread_ts,
            slack_user_name,
            current_message_full_text,
            slack_user_id,
            trigger_id,
        )

    async def handle_custom_refund_amount(
        self,
        request_data: Dict[str, str],
        channel_id: str,
        requestor_name: Dict[str, str],
        requestor_email: str,
        thread_ts: str,
        slack_user_name: str,
        current_message_full_text: str,
        slack_user_id: str = "",
        trigger_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self.refunds_utils.handle_custom_refund_amount(
            request_data=request_data,
            channel_id=channel_id,
            thread_ts=thread_ts,
            requestor_name=requestor_name,
            requestor_email=requestor_email,
            slack_user_name=slack_user_name,
            current_message_full_text=current_message_full_text,
            slack_user_id=slack_user_id,
            trigger_id=trigger_id,
        )

    async def handle_no_refund(
        self,
        request_data: Dict[str, str],
        channel_id: str,
        requestor_name: Dict[str, str],
        requestor_email: str,
        thread_ts: str,
        slack_user_name: str,
        slack_user_id: str,
        current_message_full_text: str,
        trigger_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self.refunds_utils.handle_no_refund(
            request_data,
            channel_id,
            requestor_name,
            requestor_email,
            thread_ts,
            slack_user_name,
            slack_user_id,
            current_message_full_text,
            trigger_id,
        )

    async def handle_edit_request_details(
        self,
        request_data: Dict[str, str],
        channel_id: str,
        thread_ts: str,
        slack_user_name: str,
        slack_user_id: str,
        trigger_id: str,
        current_message_full_text: str,
    ) -> Dict[str, Any]:
        return await self.refunds_utils.handle_edit_request_details(
            request_data,
            channel_id,
            thread_ts,
            slack_user_name,
            slack_user_id,
            trigger_id,
            current_message_full_text,
        )

    async def handle_edit_request_details_submission(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        return await self.refunds_utils.handle_edit_request_details_submission(payload)

    async def handle_deny_refund_request_modal_submission(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        return await self.refunds_utils.handle_deny_refund_request_modal_submission(
            payload
        )

    async def handle_restock_confirmation_request(
        self,
        request_data: Dict[str, str],
        action_id: str,
        trigger_id: str,
        channel_id: str,
        thread_ts: str,
        current_message_full_text: str,
    ) -> Dict[str, Any]:
        return await self.refunds_utils.handle_restock_confirmation_request(
            request_data,
            action_id,
            trigger_id,
            channel_id,
            thread_ts,
            current_message_full_text,
        )

    async def handle_restock_confirmation_submission(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        return await self.refunds_utils.handle_restock_confirmation_submission(payload)

    def build_comprehensive_success_message(
        self,
        order_data: Dict[str, Any],
        refund_amount: float,
        refund_type: str,
        raw_order_number: str,
        order_cancelled: bool,
        requestor_name: Dict[str, str],
        requestor_email: str,
        processor_user: str,
        current_message_text: str,
        order_id: str = "",
    ) -> Dict[str, Any]:
        return self.refunds_utils.build_comprehensive_success_message(
            order_data,
            refund_amount,
            refund_type,
            raw_order_number,
            order_cancelled,
            requestor_name,
            requestor_email,
            processor_user,
            current_message_text,
            order_id,
        )

    def build_completion_message_after_restocking(
        self,
        current_message_full_text: str,
        action_id: str,
        variant_name: str,
        restock_user: str,
        sheet_link: str,
        raw_order_number: str,
        order_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        return self.refunds_utils.build_completion_message_after_restocking(
            current_message_full_text,
            action_id,
            variant_name,
            restock_user,
            sheet_link,
            raw_order_number,
            order_data,
        )

    async def handle_restock_inventory(
        self,
        request_data: Dict[str, str],
        action_id: str,
        channel_id: str,
        thread_ts: str,
        slack_user_name: str,
        current_message_full_text: str,
        trigger_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self.refunds_utils.handle_restock_inventory(
            request_data,
            action_id,
            channel_id,
            thread_ts,
            slack_user_name,
            current_message_full_text,
            trigger_id,
        )

    def extract_sheet_link(self, message_text: str) -> str:
        return self.refunds_utils.extract_sheet_link(message_text)

    def _get_customer_orders_url(self, requestor_email: str) -> Optional[str]:
        """
        Get Shopify admin URL for viewing orders by customer ID for a given email.
        Returns None if no customer found with that email.
        """
        try:
            logger.info(f"🔍 Looking up customer by email: {requestor_email}")

            # Use the OrdersService to access Shopify API
            from services.orders import OrdersService

            orders_service = OrdersService()

            # Query to find customer by email
            customer_query = """
            query findCustomerByEmail($email: String!) {
                customers(first: 1, query: $email) {
                    edges {
                        node {
                            id
                            email
                        }
                    }
                }
            }
            """

            query_payload = {
                "query": customer_query,
                "variables": {"email": requestor_email},
            }
            customer_result = orders_service.shopify_service._make_shopify_request(
                query_payload
            )

            if customer_result and customer_result.get("data"):
                customers = (
                    customer_result["data"].get("customers", {}).get("edges", [])
                )
                if customers:
                    customer_id = customers[0]["node"]["id"]
                    # Extract numeric ID from GID format (gid://shopify/Customer/123456)
                    numeric_id = (
                        customer_id.split("/")[-1]
                        if "/" in customer_id
                        else customer_id
                    )

                    # Build the customer-specific orders URL
                    customer_orders_url = f"https://admin.shopify.com/store/09fe59-3/orders?customer_id={numeric_id}&customers_redirect=true"
                    logger.info(
                        f"✅ Found customer {numeric_id} for email {requestor_email}"
                    )
                    return customer_orders_url
                else:
                    logger.info(f"❌ No customer found for email: {requestor_email}")
                    return None
            else:
                error_msg = (
                    "No customer data returned"
                    if customer_result
                    else "Failed to query customers"
                )
                logger.warning(f"⚠️ {error_msg}")
                return None

        except Exception as e:
            logger.error(
                f"❌ Error looking up customer by email {requestor_email}: {str(e)}"
            )
            return None

    def extract_season_start_info(self, message_text: str) -> Dict[str, Optional[str]]:
        return self.refunds_utils.extract_season_start_info(message_text)

    def build_comprehensive_no_refund_message(
        self,
        order_data: Dict[str, Any],
        raw_order_number: str,
        order_cancelled: bool,
        requestor_name: Dict[str, str],
        requestor_email: str,
        processor_user: str,
        thread_ts: str,
        current_message_full_text: str,
    ) -> Dict[str, Any]:
        return self.refunds_utils.build_comprehensive_no_refund_message(
            order_data,
            raw_order_number,
            order_cancelled,
            requestor_name,
            requestor_email,
            processor_user,
            thread_ts,
            current_message_full_text,
        )
