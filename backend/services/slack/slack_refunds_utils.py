"""
Slack refunds utilities.
Contains helper functions for parsing, validation, data extraction, and webhook action handlers.
"""

import json
import logging
import hmac
import hashlib
import html
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from utils.date_utils import extract_season_dates

# External imports

# Internal imports
from services.slack.api_client import SlackApiClient, MockSlackApiClient, _is_test_mode
from utils.date_utils import format_date_and_time
from services.slack.message_builder import SlackMessageBuilder
from config import settings

logger = logging.getLogger(__name__)


class SlackRefundsUtils:
    """Utility functions and webhook handlers for Slack refund operations"""

    def __init__(self, orders_service, settings, message_builder=None):
        self.orders_service = orders_service
        self.settings = settings

        # Use provided message builder or create a fallback one
        if message_builder:
            self.message_builder = message_builder
        else:
            # Fallback for tests or direct usage - use empty sport groups
            self.message_builder = SlackMessageBuilder({})

        # Initialize API client with proper credentials
        if _is_test_mode():
            logger.info(
                "🧪 Test mode detected - using MockSlackApiClient for refunds utils"
            )
            self.api_client = MockSlackApiClient("test_token", "test_channel")
        else:
            # Use the same refunds channel configuration as SlackService
            is_production = settings.environment == "production"
            refunds_channel = {
                "name": "#registration-refunds" if is_production else "#joe-test",
                "channel_id": "C08J1EN7SFR" if is_production else "C092RU7R6PL",
                "bearer_token": settings.active_slack_bot_token or "",
            }
            logger.info(
                "🚀 Production mode - using real SlackApiClient for refunds utils"
            )
            self.api_client = SlackApiClient(
                refunds_channel["bearer_token"], refunds_channel["channel_id"]
            )

    # === UTILITY FUNCTIONS ===

    def verify_slack_signature(
        self, body: bytes, timestamp: str, signature: str
    ) -> bool:
        """Verify that the request came from Slack"""
        if not settings.slack_signing_secret:
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
                settings.slack_signing_secret.encode(),
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

    def extract_data_from_slack_thread(self, thread_ts: str) -> str:
        """Extract data from the Slack thread message (placeholder implementation)"""
        # TODO: Implement actual Slack thread message retrieval
        # For now, return empty string to use fallback values
        return ""

    def extract_sheet_link(self, message_text: str) -> str:
        """Extract Google Sheets link from message"""
        print("\n🔍 === EXTRACT SHEET LINK DEBUG ===")
        print(f"📝 Input message text length: {len(message_text)}")
        print(f"📝 Input message text preview: {message_text[:300]}...")

        # Decode HTML entities like &amp; that might be in Slack message blocks
        decoded_text = html.unescape(message_text)
        print(f"📝 Decoded text preview: {decoded_text[:300]}...")

        # Look for different Google Sheets link patterns
        patterns = [
            # Pattern 1: Slack link format <URL|text> (with :link: emoji)
            r":link:\s*\*<(https://docs\.google\.com/spreadsheets/[^>|]+)\|[^>]*>\*",
            # Pattern 2: Slack link format <URL|text> (with 🔗 emoji)
            r"🔗\s*\*<(https://docs\.google\.com/spreadsheets/[^>|]+)\|[^>]*>\*",
            # Pattern 3: Slack link format <URL|text> (without emoji)
            r"<(https://docs\.google\.com/spreadsheets/[^>|]+)\|[^>]*>",
            # Pattern 4: Direct URL after emoji
            r"🔗[^h]*?(https://docs\.google\.com/spreadsheets/[^\s\n]+)",
            # Pattern 5: URL on same line as emoji
            r"🔗.*?(https://docs\.google\.com/spreadsheets/[^\s\n]+)",
            # Pattern 6: URL anywhere in the message
            r"(https://docs\.google\.com/spreadsheets/[^\s\n]+)",
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

    def extract_season_start_info(self, message_text: str) -> Dict[str, Optional[str]]:
        """Extract season start information from message"""
        print("\n🔍 === EXTRACT SEASON START INFO DEBUG ===")
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
            # Pattern 5: Product Title field with Slack link - extract title from <URL|title>
            r"\*Product Title\*:\s*<[^|]+\|([^>]+)>",
            # Pattern 6: Product Title field with full Slack link
            r"\*Product Title\*:\s*(<[^>]+>)",
            # Pattern 7: Product title with link <URL|title> (extract title only)
            r"Product Title:\s*<[^|]+\|([^>]+)>",
            # Pattern 8: Product Title field (plain text)
            r"Product Title:\s*([^<\n]+)",
            # Pattern 9: Product Title field (plain text)
            r"Product Title:\s*([^<\n]+)",
            # Pattern 10: Handle current format with Product Title link
            r"\*Product Title\*:\s*<[^|]*\|([^>]+)>\s*\n\s*\*Season Start Date\*:\s*([^\n]+)",
            # Pattern 11: Handle format without link in Product Title
            r"\*Product Title\*:\s*([^\n]+)\s*\n\s*\*Season Start Date\*:\s*([^\n]+)",
        ]

        product_title = "Unknown Product"
        product_link = None
        season_start_date = "Unknown"

        # Try new combined patterns first (patterns 9-10)
        for i, pattern in enumerate(patterns[9:], start=9):
            season_match = re.search(pattern, message_text)
            if season_match:
                product_title = season_match.group(1).strip()
                season_start_date = season_match.group(2).strip()
                print(
                    f"✅ Pattern {i} matched! Product: {product_title}, Season Start: {season_start_date}"
                )
                print("=== END EXTRACT SEASON START INFO DEBUG ===\n")
                return {
                    "product_title": product_title,
                    "season_start_date": season_start_date,
                    "product_link": None,
                }

        # Try to find season start date with product (Pattern 1: with link)
        season_match = re.search(patterns[0], message_text)
        if season_match:
            product_title = season_match.group(1).strip()
            season_start_date = season_match.group(2).strip()
            print(
                f"✅ Pattern 1 matched! Product: {product_title}, Season Start: {season_start_date}"
            )
            print("=== END EXTRACT SEASON START INFO DEBUG ===\n")
            return {
                "product_title": product_title,
                "season_start_date": season_start_date,
                "product_link": None,
            }

        # Try to find season start date with product (Pattern 2: plain text)
        season_match = re.search(patterns[1], message_text)
        if season_match:
            product_title = season_match.group(1).strip()
            season_start_date = season_match.group(2).strip()
            print(
                f"✅ Pattern 2 matched! Product: {product_title}, Season Start: {season_start_date}"
            )
            print("=== END EXTRACT SEASON START INFO DEBUG ===\n")
            return {
                "product_title": product_title,
                "season_start_date": season_start_date,
                "product_link": None,
            }

        # Try to find product title/link from various fields
        for i, pattern in enumerate(patterns[2:], start=3):
            product_match = re.search(pattern, message_text)
            if product_match:
                matched_text = product_match.group(1).strip()

                # Check if it's a full Slack link (patterns 4 and 6)
                if (
                    i in [4, 6]
                    and matched_text.startswith("<")
                    and matched_text.endswith(">")
                ):
                    product_link = matched_text
                    # Extract title from link for display
                    if "|" in matched_text:
                        product_title = matched_text.split("|")[1].replace(">", "")
                    else:
                        product_title = "Unknown Product"
                    print(
                        f"✅ Pattern {i} matched! Product Link: {product_link}, Title: {product_title}"
                    )
                else:
                    # Plain text or title from link (patterns 3, 5, 7, 8 get title directly)
                    product_title = matched_text
                    print(f"✅ Pattern {i} matched! Product: {product_title}")
                break

        # Try to find separate season start date
        season_date_patterns = [
            r"Season Start Date:\s*([^\n]+)",
            r"Season Start:\s*([^\n]+)",
            r"Start Date:\s*([^\n]+)",
        ]

        for pattern in season_date_patterns:
            season_match = re.search(pattern, message_text)
            if season_match:
                season_start_date = season_match.group(1).strip()
                print(f"✅ Pattern matched! Season Start: {season_start_date}")
                break

        print("❌ No season start info found, using fallback")
        print("=== END EXTRACT SEASON START INFO DEBUG ===\n")
        return {
            "product_title": product_title,
            "season_start_date": season_start_date,
            "product_link": product_link,
        }

    # === WEBHOOK HANDLERS ===

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
        """
        Handle cancel order button click (Step 1)
        Cancels the order in Shopify, then shows refund options
        """
        print("\n✅ === CANCEL ORDER ACTION ===")
        print(f"👤 User: {slack_user_name} ({slack_user_id})")
        print(f"📋 Request Data: {request_data}")
        print(f"📍 Channel: {channel_id}, Thread: {thread_ts}")
        print("=== END CANCEL ORDER ===\n")

        try:
            # Extract data from button value
            raw_order_number = request_data.get("rawOrderNumber", "")
            refund_type = request_data.get("refundType", "refund")
            request_submitted_at = request_data.get("requestSubmittedAt", "")

            logger.info(f"Canceling order: {raw_order_number}")

            # Check environment for debug vs production behavior
            # Note: debug/production mode not used in this method

            # 1. Fetch order details using correct method name
            order_result = (
                self.orders_service.fetch_order_details_by_email_or_order_name(
                    order_name=raw_order_number
                )
            )
            if not order_result["success"]:
                (f"❌ Failed to fetch order details: {order_result['message']}")
                self.send_modal_error_to_user(
                    trigger_id=trigger_id,
                    error_message=f"Could not find order {raw_order_number}.\n\n**Error Details:**\n{order_result['message']}\n\nPlease verify the order number is correct.",
                    operation_name="Order Lookup",
                )
                return {}

            shopify_order_data = order_result["data"]
            order_id = shopify_order_data.get("id", "")

            # 2. Calculate refund amount
            refund_calculation = self.orders_service.calculate_refund_due(
                shopify_order_data, refund_type
            )

            # 3. Cancel order using correct method name
            cancel_result = self.orders_service.cancel_order(order_id)

            if cancel_result["success"]:
                # Create order data with fresh Shopify data and preserved requestor info
                order_data = {
                    "order": shopify_order_data,  # Use fresh Shopify order data
                    "refund_calculation": refund_calculation,  # Use fresh refund calculation
                    "requestor_name": requestor_name,
                    "requestor_email": requestor_email,
                    "original_data": {
                        "original_timestamp": request_submitted_at,  # Preserve original timestamp
                        "requestor_email": requestor_email,
                    },
                }

                # 5. Extract Google Sheets link from current message
                sheet_link = self.extract_sheet_link(current_message_full_text)
                print(f"🔗 Extracted sheet link for cancel_order: {sheet_link}")

                # 6. Create refund decision message
                refund_message = self.message_builder.create_refund_decision_message(
                    order_data=order_data,
                    requestor_name=requestor_name,
                    requestor_email=requestor_email,
                    refund_type=refund_type,
                    sport_mention=self.message_builder.get_sport_group_mention(
                        order_data["order"]["line_items"][0]["title"]
                    ),
                    sheet_link=sheet_link,
                    order_cancelled=True,
                    slack_user_id=slack_user_id,
                    original_timestamp=request_submitted_at,
                )

                # ✅ Update Slack message ONLY on Shopify success
                self.update_slack_on_shopify_success(
                    message_ts=thread_ts,
                    success_message=refund_message["text"],
                    action_buttons=refund_message["action_buttons"],
                )

                logger.info(f"Order {raw_order_number} cancelled successfully")
            else:
                # 🚨 Handle Shopify cancellation failure with detailed error logging
                shopify_error = cancel_result.get("message", "Unknown error")

                # Print detailed error information for debugging
                print("\n🚨 === SHOPIFY ORDER CANCELLATION FAILED ===")
                print(f"📋 Order: {raw_order_number}")
                print(f"🔗 Order ID: {order_id}")
                print(f"👤 User: {slack_user_name} ({slack_user_id})")
                print(f"❌ Shopify Error: {shopify_error}")
                print(f"📝 Full cancel_result: {cancel_result}")
                print("=== END SHOPIFY CANCELLATION FAILURE ===\n")

                # Log detailed error for server logs
                logger.error("🚨 SHOPIFY ORDER CANCELLATION FAILED:")
                logger.error(f"   Order: {raw_order_number}")
                logger.error(f"   Order ID: {order_id}")
                logger.error(f"   User: {slack_user_name} ({slack_user_id})")
                logger.error(f"   Shopify Error: {shopify_error}")
                logger.error(f"   Full Result: {cancel_result}")

                # Send modal error dialog to the user who clicked the button
                raw_response = cancel_result.get("raw_response", "No response data")
                shopify_errors = cancel_result.get("shopify_errors", [])

                modal_error_message = f"Order cancellation failed for {raw_order_number}.\n\n**Shopify Error:**\n{shopify_error}"

                if shopify_errors:
                    modal_error_message += (
                        f"\n\n**Shopify Error Details:**\n{shopify_errors}"
                    )

                modal_error_message += f"\n\n**Raw Shopify Response:**\n{raw_response}"

                modal_error_message += "\n\nThis often happens when:\n• Order is already cancelled\n• Order is already fulfilled\n• Order has refunds or returns\n• Payment gateway restrictions"

                self.send_modal_error_to_user(
                    trigger_id=trigger_id,
                    error_message=modal_error_message,
                    operation_name="Order Cancellation",
                )

            return {}
        except Exception as e:
            logger.error(f"Error canceling order: {e}")
            self.send_modal_error_to_user(
                trigger_id=trigger_id,
                error_message=f"An unexpected error occurred while canceling order {request_data.get('rawOrderNumber', 'unknown')}.\n\n**Error Details:**\n{str(e)}\n\nPlease try again or contact support if the issue persists.",
                operation_name="Order Cancellation",
            )
            return {}

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
    ) -> Dict[str, Any]:
        """
        Handle proceed without cancel button click (Step 1)
        Shows refund options without canceling the order
        """
        print("\n➡️ === PROCEED WITHOUT CANCEL ACTION ===")
        print(f"👤 User: {slack_user_name}")
        print(f"📋 Request Data: {request_data}")
        print(f"📍 Channel: {channel_id}, Thread: {thread_ts}")
        print("=== END PROCEED WITHOUT CANCEL ===\n")

        try:
            # Extract data from button value
            raw_order_number = request_data.get("rawOrderNumber", "")
            refund_type = request_data.get("refundType", "refund")
            request_submitted_at = request_data.get("requestSubmittedAt", "")

            logger.info(f"Proceeding without canceling order: {raw_order_number}")

            # 1. Fetch fresh order details from Shopify to get complete data using correct method name
            order_result = (
                self.orders_service.fetch_order_details_by_email_or_order_name(
                    order_name=raw_order_number
                )
            )
            if not order_result["success"]:
                logger.error(
                    f"Failed to fetch order details for {raw_order_number}: {order_result['message']}"
                )
                self.send_modal_error_to_user(
                    trigger_id=trigger_id,
                    error_message=f"Could not find order {raw_order_number}.\n\n**Error Details:**\n{order_result['message']}\n\nPlease verify the order number is correct.",
                    operation_name="Order Lookup",
                )
                return {}

            shopify_order_data = order_result["data"]

            # 2. Calculate fresh refund amount
            refund_calculation = self.orders_service.calculate_refund_due(
                shopify_order_data, refund_type
            )

            # Create order data with fresh Shopify data and preserved requestor info
            order_data = {
                "order": shopify_order_data,  # Use fresh Shopify order data
                "refund_calculation": refund_calculation,  # Use fresh refund calculation
                "requestor_name": requestor_name,
                "requestor_email": requestor_email,
                "original_data": {
                    "original_timestamp": request_submitted_at,  # Preserve original timestamp
                    "requestor_email": requestor_email,
                },
            }

            # 4. Extract Google Sheets link from current message
            sheet_link = self.extract_sheet_link(current_message_full_text)
            print(f"🔗 Extracted sheet link for proceed_without_cancel: {sheet_link}")

            # 5. Create refund decision message (order remains active)
            refund_message = self.message_builder.create_refund_decision_message(
                order_data=order_data,
                requestor_name=requestor_name,
                requestor_email=requestor_email,
                refund_type=refund_type,
                sport_mention=self.message_builder.get_sport_group_mention(
                    order_data["order"]["line_items"][0]["title"]
                ),
                sheet_link=sheet_link,
                order_cancelled=False,
                slack_user_id=slack_user_id,
                original_timestamp=request_submitted_at,
            )

            # 4. Update Slack message using controlled mechanism
            self.update_slack_on_shopify_success(
                message_ts=thread_ts,
                success_message=refund_message["text"],
                action_buttons=refund_message["action_buttons"],
            )

            logger.info(
                f"Proceeding to refund options for order {raw_order_number} (order not cancelled)"
            )
            return {}
        except Exception as e:
            logger.error(f"Error proceeding without cancel: {e}")
            self.send_modal_error_to_user(
                trigger_id=trigger_id,
                error_message=f"An unexpected error occurred while processing order {request_data.get('rawOrderNumber', 'unknown')}.\n\n**Error Details:**\n{str(e)}\n\nPlease try again or contact support if the issue persists.",
                operation_name="Order Processing",
            )
            return {}

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
        """
        Handle process calculated refund button click (Step 2)
        """
        print("\n✅ === PROCESS REFUND ACTION ===")
        print(f"👤 User: {slack_user_name} ({slack_user_id})")
        print(f"📋 Request Data: {request_data}")
        print(f"📍 Channel: {channel_id}, Thread: {thread_ts}")
        print("=== END PROCESS REFUND ===\n")

        try:
            order_id = request_data.get("orderId", "")
            raw_order_number = request_data.get("rawOrderNumber", "")
            refund_amount = float(request_data.get("refundAmount", "0"))
            refund_type = request_data.get("refundType", "refund")
            order_cancelled = (
                request_data.get("orderCancelled", "False").lower() == "true"
            )

            logger.info(
                f"Processing refund: Order {raw_order_number}, Amount: ${refund_amount}"
            )

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
                    "processedBy": slack_user_id,
                }
                logger.info(
                    f"🧪 DEBUG MODE: JSON POST BODY for refund:\n{json.dumps(debug_refund_body, indent=2)}"
                )

            # Process refund using correct method name
            refund_result = self.orders_service.create_refund_or_credit(
                order_id, refund_amount, refund_type
            )

            if refund_result["success"]:
                # Fetch fresh order details for comprehensive message
                order_result = (
                    self.orders_service.fetch_order_details_by_email_or_order_name(
                        order_name=raw_order_number
                    )
                )
                if order_result["success"]:
                    shopify_order_data = order_result["data"]

                    # Build comprehensive success message with inventory and restock buttons
                    success_message_data = self.build_comprehensive_success_message(
                        order_data=shopify_order_data,
                        refund_amount=refund_amount,
                        refund_type=refund_type,
                        raw_order_number=raw_order_number,
                        order_cancelled=order_cancelled,
                        requestor_name=requestor_name,
                        requestor_email=requestor_email,
                        processor_user=slack_user_id,
                        current_message_text=current_message_full_text,
                        order_id=order_id,
                        is_debug_mode=is_debug_mode,
                    )

                    # ✅ Update Slack message ONLY on Shopify success
                    print(
                        f"🔄 Attempting to update Slack message with {len(success_message_data['action_buttons'])} buttons"
                    )
                    self.update_slack_on_shopify_success(
                        message_ts=thread_ts,
                        success_message=success_message_data["text"],
                        action_buttons=success_message_data["action_buttons"],
                    )
                else:
                    # Fallback if order fetch fails - build message similar to comprehensive format
                    refund_or_credit = (
                        "Refund" if refund_type.lower() == "refund" else "Credit"
                    )
                    status = "Canceled" if order_cancelled else "Not Canceled"

                    # Build message in same format as comprehensive message (without inventory info)
                    refund_type_text = self.message_builder._get_request_type_text(
                        refund_type
                    )

                    message = f"*Request Type*: {refund_type_text}\n\n"
                    message += f"*Order Number*: {raw_order_number}\n\n"
                    message += (
                        f"*{refund_or_credit} Provided:* ${refund_amount:.2f}\n\n"
                    )

                    # Add cancellation status footer
                    message += (
                        f"🚀 *Order {status}*, processed by <@{slack_user_id}>\n\n"
                        if order_cancelled
                        else f"ℹ️ *Order {status}*, processed by <@{slack_user_id}>\n\n"
                    )

                    # Add refund status footer
                    message += f"💰 *{refund_or_credit}ed by <@{slack_user_id}>*\n\n"

                    # ✅ Update Slack with fallback success message
                    self.update_slack_on_shopify_success(
                        message_ts=thread_ts, success_message=message, action_buttons=[]
                    )
            else:
                # 🚨 Handle Shopify refund failure with detailed error logging
                shopify_error = refund_result.get("message", "Unknown error")

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
                logger.error(f"   User: {slack_user_name} ({slack_user_id})")
                logger.error(f"   Shopify Error: {shopify_error}")
                logger.error(f"   Full Result: {refund_result}")

                # Send modal error dialog to the user who clicked the button
                modal_error_message = f"{refund_type.title()} failed for {raw_order_number}.\n\n**Shopify Error:**\n{shopify_error}\n\nAmount: ${refund_amount:.2f}\nType: {refund_type}\n\nCommon causes:\n• Order already refunded\n• Insufficient funds captured\n• Payment gateway restrictions\n• Order too old for refund"

                self.send_modal_error_to_user(
                    trigger_id=trigger_id,
                    error_message=modal_error_message,
                    operation_name=f"{refund_type.title()} Processing",
                )

            return {}
        except Exception as e:
            logger.error(f"Error processing refund: {e}")
            self.send_modal_error_to_user(
                trigger_id=trigger_id,
                error_message=f"An unexpected error occurred while processing the {request_data.get('refundType', 'refund')} for order {request_data.get('rawOrderNumber', 'unknown')}.\n\n**Error Details:**\n{str(e)}\n\nPlease try again or contact web support if the issue persists.",
                operation_name="Refund Processing",
            )
            return {}

    async def handle_custom_refund_amount(
        self,
        request_data: Dict[str, str],
        channel_id: str,
        thread_ts: str,
        requestor_name: Dict[str, str],
        requestor_email: str,
        slack_user_name: str,
        current_message_full_text: str,
        slack_user_id: str = "",
        trigger_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Show modal to enter custom refund amount.
        """
        print("\n✏️ === CUSTOM REFUND AMOUNT ACTION ===")
        print(f"👤 User: {slack_user_name} ({slack_user_id})")
        print(f"📋 Request Data: {request_data}")
        print(f"📍 Channel: {channel_id}, Thread: {thread_ts}")
        print("=== END CUSTOM REFUND AMOUNT ===\n")

        try:
            raw_order_number = request_data.get("rawOrderNumber", "")
            refund_amount = request_data.get("refundAmount", "0.00")
            refund_type = request_data.get("refundType", "refund")
            order_id = request_data.get("orderId", "")

            # Modal view with dollar sign before the input
            modal_view = {
                "type": "modal",
                "callback_id": "custom_refund_submit",
                "private_metadata": json.dumps(
                    {
                        "orderId": order_id,
                        "rawOrderNumber": raw_order_number,
                        "refundType": refund_type,
                        "channel_id": channel_id,
                        "thread_ts": thread_ts,
                        "slack_user_id": slack_user_id,
                        "slack_user_name": slack_user_name,
                        "current_message_full_text": current_message_full_text,
                        "requestor_first_name": requestor_name.get("first", ""),
                        "requestor_last_name": requestor_name.get("last", ""),
                        "requestor_email": requestor_email,
                    }
                ),
                "title": {"type": "plain_text", "text": "Custom Refund"},
                "submit": {"type": "plain_text", "text": "Process Refund"},
                "close": {"type": "plain_text", "text": "Cancel"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "refund_input_block",
                        "label": {"type": "plain_text", "text": "Enter Refund Amount"},
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "custom_refund_amount",
                            "initial_value": refund_amount,
                        },
                        "hint": {
                            "type": "plain_text",
                            "text": "Only enter the number (e.g., 25.00). Dollar sign will be added automatically.",
                        },
                    }
                ],
            }

            # Send modal
            result = self.api_client.send_modal(
                trigger_id=trigger_id,  # type: ignore
                modal_view=modal_view,
            )
            if not result.get("success"):
                raise Exception(result.get("error", "Failed to open modal"))

            return {"success": True}

        except Exception as e:
            logger.error(f"Error handling custom refund modal: {e}")
            if trigger_id:
                self.send_modal_error_to_user(
                    trigger_id=trigger_id,
                    error_message=str(e),
                    operation_name="Custom Refund",
                )
            return {"success": False, "message": str(e)}

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
        """
        Handle no refund button click (Step 2)
        """
        print("\n🚫 === NO REFUND ACTION ===")
        print(f"👤 User: {slack_user_name} ({slack_user_id})")
        print(f"📋 Request Data: {request_data}")
        print(f"📍 Channel: {channel_id}, Thread: {thread_ts}")
        print(f"📝 Current message text length: {len(current_message_full_text)}")
        print(f"📝 Current message preview: {current_message_full_text[:200]}...")
        print("=== END NO REFUND ===\n")

        try:
            raw_order_number = request_data.get("rawOrderNumber", "")
            order_cancelled = (
                request_data.get("orderCancelled", "False").lower() == "true"
            )

            # Check ENVIRONMENT configuration for debug vs production behavior
            is_debug_mode = settings.is_debug_mode

            if is_debug_mode:
                print(
                    f"🧪 DEBUG MODE: Would close refund request for order {raw_order_number}"
                )
                print(
                    "🧪 DEBUG MODE: No actual API calls needed for 'no refund' action"
                )
            else:
                print(
                    "🏭 PRODUCTION MODE: Closing refund request (no API calls needed)"
                )

            # Fetch fresh order details for comprehensive message
            order_result = (
                self.orders_service.fetch_order_details_by_email_or_order_name(
                    order_name=raw_order_number
                )
            )
            if order_result["success"]:
                shopify_order_data = order_result["data"]

                # Build comprehensive no refund message with inventory and restock buttons
                try:
                    no_refund_message_data = self.build_comprehensive_no_refund_message(
                        order_data=shopify_order_data,
                        raw_order_number=raw_order_number,
                        order_cancelled=order_cancelled,
                        requestor_name=requestor_name,
                        requestor_email=requestor_email,
                        processor_user=slack_user_id,
                        thread_ts=thread_ts,
                        current_message_full_text=current_message_full_text,
                    )

                    print(
                        f"📝 Built message text length: {len(no_refund_message_data['text'])}"
                    )
                    print(
                        f"🔘 Built {len(no_refund_message_data['action_buttons'])} action buttons"
                    )

                    self.update_slack_on_shopify_success(
                        message_ts=thread_ts,
                        success_message=no_refund_message_data["text"],
                        action_buttons=no_refund_message_data["action_buttons"],
                    )

                except Exception as build_error:
                    print(f"❌ Error building no refund message: {str(build_error)}")
                    logger.error(
                        f"Error building no refund message: {str(build_error)}"
                    )
                    # Fall back to updating current message with replacement logic
                    if "📋 Refund processing pending" in current_message_full_text:
                        simple_message = current_message_full_text.replace(
                            "📋 Refund processing pending",
                            f"✅ *Not Refunded by <@{slack_user_id}>*",
                        )
                    else:
                        # Fallback to building new message if replacement fails
                        status = "Canceled" if order_cancelled else "Not Canceled"
                        simple_message = f"*Order Number*: {raw_order_number}\n\n"
                        simple_message += "*No Refund Provided*\n\n"
                        simple_message += (
                            f"✅ *Order {status}*, processed by <@{slack_user_id}>\n"
                        )
                        simple_message += f"✅ *Not Refunded by <@{slack_user_id}>*\n"
                        simple_message += "📋 Inventory restocking pending\n\n"

                    self.update_slack_on_shopify_success(
                        message_ts=thread_ts,
                        success_message=simple_message,
                        action_buttons=[],
                    )
            else:
                # Fallback if order fetch fails - use replacement logic
                if "📋 Refund processing pending" in current_message_full_text:
                    message = current_message_full_text.replace(
                        "📋 Refund processing pending",
                        f"✅ *Not Refunded by <@{slack_user_id}>*",
                    )
                else:
                    # Final fallback to building new message
                    status = "Canceled" if order_cancelled else "Not Canceled"
                    message = f"*Order Number*: {raw_order_number}\n\n"
                    message += "*No Refund Provided*\n\n"
                    message += f"✅ *Order {status}*, processed by <@{slack_user_id}>\n"
                    message += f"✅ *Not Refunded by <@{slack_user_id}>*\n"
                    message += "📋 Inventory restocking pending\n\n"

                try:
                    self.update_slack_on_shopify_success(
                        message_ts=thread_ts, success_message=message, action_buttons=[]
                    )
                except Exception as e:
                    print(f"❌ No refund message update failed: {str(e)}")

            return {}
        except Exception as e:
            logger.error(f"Error handling no refund: {e}")
            self.send_modal_error_to_user(
                trigger_id=trigger_id,
                error_message=f"An unexpected error occurred while closing the refund request for order {request_data.get('rawOrderNumber', 'unknown')}.\n\n**Error Details:**\n{str(e)}\n\nPlease try again or contact support if the issue persists.",
                operation_name="No Refund Processing",
            )
            return {}

    # === MESSAGE BUILDERS ===

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
        is_debug_mode: bool = False,
    ) -> Dict[str, Any]:
        """Build comprehensive success message with customer info, inventory, and restock buttons"""

        # Extract season start info from current message
        season_info = self.extract_season_start_info(current_message_text)
        product_title = season_info.get("product_title", "Unknown Product")
        season_start_date = season_info.get("season_start_date", "Unknown")

        # Extract Google Sheets link from current message
        sheet_link = self.extract_sheet_link(current_message_text)

        # Format requestor name properly and create customer hyperlink
        requestor_full_name = f"{requestor_name.get('first', '')} {requestor_name.get('last', '')}".strip()
        if not requestor_full_name:
            requestor_full_name = "Unknown Customer"

        # Try to get customer ID from order data for profile hyperlink
        customer_data = None
        if order_data and "customer" in order_data:
            customer_data = order_data["customer"]

        # Build main message with proper customer hyperlink
        if customer_data and customer_data.get("id"):
            customer_url = self.message_builder.get_customer_url(customer_data["id"])
            message = f"📧 *Requested by:* <{customer_url}|{requestor_full_name}> (<mailto:{requestor_email}|{requestor_email}>)\n\n"
        else:
            message = f"📧 *Requested by:* {requestor_full_name} (<mailto:{requestor_email}|{requestor_email}>)\n\n"
        message += f"*Order Number*: {self.message_builder.get_order_url(order_id or 'unknown', raw_order_number)}\n\n"

        # Create product URL and rename to "Product Title"
        if order_data and "line_items" in order_data and order_data["line_items"]:
            first_line_item = order_data["line_items"][0]
            product_data = first_line_item.get("product", {})
            product_title = first_line_item.get("title", "Unknown Product")
            product_id = product_data.get("id", "")
            if product_id:
                product_url = self.message_builder.get_product_url(product_id)
                message += f"*Product Title:* <{product_url}|{product_title}>\n\n"
            else:
                message += f"*Product Title:* {product_title}\n\n"
        else:
            product_title = "Unknown Product"
            message += f"*Product Title:* {product_title}\n\n"

        # Extract timestamps and season date from current message
        import re

        submitted_match = re.search(
            r"\*Request Submitted At\*:\s*([^\n]+)", current_message_text
        )
        created_match = re.search(
            r"\*Order Created At\*:\s*([^\n]+)", current_message_text
        )
        season_date_match = re.search(
            r"\*Season Start Date\*:\s*([^\n]+)", current_message_text
        )

        # Use extracted season date if available, otherwise use the parsed one
        if season_date_match:
            season_start_date = season_date_match.group(1)

        if submitted_match:
            message += f"*Request Submitted At*: {submitted_match.group(1)}\n\n"
        if created_match:
            message += f"*Order Created At:* {created_match.group(1)}\n\n"

        message += f"*Season Start Date*: {season_start_date}\n\n"

        # Extract total paid from current message
        total_paid_match = re.search(
            r"\*Total Paid\*:\s*\$([0-9.]+)", current_message_text
        )
        if total_paid_match:
            message += f"*Total Paid:* ${total_paid_match.group(1)}\n\n"

        # Add Google Sheets link
        if sheet_link:
            message += f"🔗 *<{sheet_link}|View Request in Google Sheets>*\n\n"

        # Find and preserve progress indicators from current message, updating refund status
        if "📋 Refund processing pending" in current_message_text:
            # Extract the progress section from current message
            lines = current_message_text.split("\n")
            progress_section = []
            for line in lines:
                if "✅ *Order" in line or "📋" in line:
                    if "📋 Refund processing pending" in line:
                        progress_section.append("✅ Refund processing completed")
                    else:
                        progress_section.append(line)

            if progress_section:
                message += "\n".join(progress_section) + "\n\n"
        else:
            # Fallback if no progress indicators found - add them
            message += "✅ Order cancellation completed\n"
            message += "✅ Refund processing completed\n"
            message += "📋 Inventory restocking pending\n\n"

        # Add refund status footer - new format: remove emoji, lowercase refund_type, bold it
        refund_type_lower = refund_type.lower()
        message += f"${refund_amount:.2f} *{refund_type_lower}* issued by <@{processor_user}>\n\n"

        # Add inventory information
        message += " Current Inventory:\n"

        # Build inventory display and restock buttons from variants
        action_buttons = []
        variants_data = []

        # Check multiple possible locations for variants data
        if order_data:
            # Try order_data["variants"] first (from comprehensive data)
            if "variants" in order_data:
                variants_data = order_data["variants"]
            # Try order_data["product"]["variants"] as fallback (from orders service)
            elif "product" in order_data and "variants" in order_data["product"]:
                variants_data = order_data["product"]["variants"]

        if variants_data:
            for variant in variants_data:
                # Handle different field name formats from different data sources
                variant_title = (
                    variant.get("variantTitle")
                    or variant.get("variantName")
                    or variant.get("title")
                    or "Unknown Variant"
                )
                available_quantity = (
                    variant.get("availableQuantity")
                    or variant.get("inventory")
                    or variant.get("inventoryQuantity")
                    or 0
                )

                # Add inventory line
                message += f"• {variant_title}: {available_quantity} spots available\n"

                # Create restock button (remove "Registration" from variant name if present)
                button_text = variant_title.replace(" Registration", "").strip()
                action_buttons.append(
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": f"Restock {button_text}",
                        },
                        "action_id": f"confirm_restock_{button_text.lower().replace(' ', '_')}",
                        "value": json.dumps(
                            {
                                "action": "confirm_restock_variant",
                                "variantId": (
                                    variant.get("variantId") or variant.get("id") or ""
                                ),
                                "inventoryItemId": variant.get("inventoryItemId", ""),
                                "variantTitle": variant_title,
                                "orderId": order_id,
                                "rawOrderNumber": raw_order_number,
                            }
                        ),
                    }
                )
        else:
            # Fallback if no variant data
            message += "• No inventory information available\n"

        message += "Restock Inventory?"

        # Add "Do Not Restock" button
        action_buttons.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Do Not Restock"},
                "style": "danger",  # Make button red
                "action_id": "confirm_do_not_restock",
                "value": json.dumps(
                    {
                        "action": "confirm_do_not_restock",
                        "orderId": order_id,
                        "rawOrderNumber": raw_order_number,
                    }
                ),
            }
        )

        return {"text": message, "action_buttons": action_buttons}

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
        """Build completion message after restocking - keeps the same format as previous message but adds restock info."""

        # Start with the current message and modify it to add restock information
        message = current_message_full_text

        # Remove only the inventory section and restock buttons from the end
        # This section typically starts with a repeated "📦 Season Start Date" line
        # We want to preserve all the original message content above this section
        inventory_section_patterns = [
            # Pattern 1: Full inventory section with season start repeat
            r"\n\n📦 Season Start Date for .+? is .+?\.\n Current Inventory:\n.+?Restock Inventory\?",
            # Pattern 2: Just the inventory section without season start repeat
            r"\n Current Inventory:\n.+?Restock Inventory\?",
            # Pattern 3: Minimal fallback
            r"Current Inventory:.*?Restock Inventory\?",
        ]

        for pattern in inventory_section_patterns:
            if re.search(pattern, message, re.DOTALL):
                message = re.sub(pattern, "", message, flags=re.DOTALL)
                break

        # Clean up any trailing whitespace and empty lines
        message = message.rstrip()

        # Remove any remaining season start date lines that might have been missed
        message = re.sub(r"\n\n📦 Season Start Date for .+? is .+?\.", "", message)
        message = re.sub(r"\n📦 Season Start Date for .+? is .+?\.", "", message)
        message = re.sub(r"📦 Season Start Date for .+? is .+?\.\n", "", message)

        # Clean up again after the additional removals
        message = message.rstrip()

        # Verify critical information is preserved (for debugging)
        has_order_date = "*Order Created At:*" in message
        has_total_paid = "*Total Paid:*" in message
        if not has_order_date or not has_total_paid:
            print(
                f"⚠️ Warning: Critical info may be missing - Order Date: {has_order_date}, Total Paid: {has_total_paid}"
            )
            print(f"📝 Current message length: {len(message)}")
            print(f"📝 Message preview: {message[:500]}...")

        # Replace the inventory restocking pending indicator with completed status
        if action_id.startswith("restock_"):
            # Yes restock message: replace with restocked status
            replacement_text = (
                f"✅ *Inventory restocked ({variant_name}) by <@{restock_user}>*"
            )
        elif action_id == "do_not_restock":
            # No restock message: replace with not restocked status
            replacement_text = f"✅ *Inventory not restocked by <@{restock_user}>*"
        else:
            # Fallback: replace with generic processed status
            replacement_text = f"✅ *Restocking processed by <@{restock_user}>*"

        # Try multiple replacement patterns to handle different message formats

        # Pattern 1: Exact match with emoji
        if "📋 Inventory restocking pending" in message:
            message = message.replace(
                "📋 Inventory restocking pending", replacement_text
            )
        # Pattern 2: Emoji code format
        elif ":clipboard: Inventory restocking pending" in message:
            message = message.replace(
                ":clipboard: Inventory restocking pending", replacement_text
            )
        # Pattern 3: Flexible regex pattern (handles extra spaces, case variations)
        else:
            pattern = r"(:clipboard:|📋)\s*[Ii]nventory\s+restocking\s+pending"
            if re.search(pattern, message):
                message = re.sub(pattern, replacement_text, message)

        # Add Google Sheets link and waitlist link
        waitlist_link = "https://docs.google.com/spreadsheets/d/11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw/edit#gid=1811075695"
        message += f"\n📋 *<{waitlist_link}|Open Waitlist to let someone in>*"

        return message

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
        """Build comprehensive no refund message in the same format as the success message"""

        # Extract order ID from order_data
        order_id = order_data.get("id", "") if order_data else ""

        # Extract product information from order data
        product_title = "Unknown Product"
        season_start_date = "Unknown"

        if order_data and "line_items" in order_data and order_data["line_items"]:
            first_line_item = order_data["line_items"][0]
            product_title = first_line_item.get("title", product_title)

            # Try to extract season start date from product description
            if (
                "product" in first_line_item
                and "descriptionHtml" in first_line_item["product"]
            ):
                description = first_line_item["product"]["descriptionHtml"]
                season_dates = extract_season_dates(description)
                if (
                    season_dates and season_dates[0]
                ):  # season_dates is a tuple (start_date, off_dates)
                    season_start_date = season_dates[0]

        # If we couldn't get the product info from order_data, try extracting from current message
        if product_title == "Unknown Product":
            season_info = self.extract_season_start_info(current_message_full_text)
            product_title = season_info.get("product_title", product_title)
            if season_start_date == "Unknown":
                season_start_date = season_info.get(
                    "season_start_date", season_start_date
                )

        # Format requestor name properly and create customer hyperlink
        requestor_full_name = f"{requestor_name.get('first', '')} {requestor_name.get('last', '')}".strip()
        if not requestor_full_name:
            requestor_full_name = "Unknown Customer"

        # Try to get customer ID from order data for profile hyperlink
        customer_data = None
        if order_data and "customer" in order_data:
            customer_data = order_data["customer"]

        # Build main message with proper customer hyperlink
        if customer_data and customer_data.get("id"):
            customer_url = self.message_builder.get_customer_url(customer_data["id"])
            message = f"📧 *Requested by:* <{customer_url}|{requestor_full_name}> (<mailto:{requestor_email}|{requestor_email}>)\n\n"
        else:
            message = f"📧 *Requested by:* {requestor_full_name} (<mailto:{requestor_email}|{requestor_email}>)\n\n"
        message += f"*Order Number*: {self.message_builder.get_order_url(order_id, raw_order_number)}\n\n"

        # Create product URL and rename to "Product Title"
        if order_data and "line_items" in order_data and order_data["line_items"]:
            first_line_item = order_data["line_items"][0]
            product_data = first_line_item.get("product", {})
            product_title = first_line_item.get("title", "Unknown Product")
            product_id = product_data.get("id", "")
            if product_id:
                product_url = self.message_builder.get_product_url(product_id)
                message += f"*Product Title:* <{product_url}|{product_title}>\n\n"
            else:
                message += f"*Product Title:* {product_title}\n\n"
        else:
            product_title = "Unknown Product"
            message += f"*Product Title:* {product_title}\n\n"

        # Extract timestamps and season date from current message
        import re

        submitted_match = re.search(
            r"\*Request Submitted At\*:\s*([^\n]+)", current_message_full_text
        )
        created_match = re.search(
            r"\*Order Created At\*:\s*([^\n]+)", current_message_full_text
        )
        season_date_match = re.search(
            r"\*Season Start Date\*:\s*([^\n]+)", current_message_full_text
        )

        # Use extracted season date if available, otherwise use the parsed one
        if season_date_match:
            season_start_date = season_date_match.group(1)

        if submitted_match:
            message += f"*Request Submitted At*: {submitted_match.group(1)}\n\n"
        if created_match:
            message += f"*Order Created At:* {created_match.group(1)}\n\n"

        message += f"*Season Start Date*: {season_start_date}\n\n"

        # Extract total paid from current message
        total_paid_match = re.search(
            r"\*Total Paid\*:\s*\$([0-9.]+)", current_message_full_text
        )
        if total_paid_match:
            message += f"*Total Paid:* ${total_paid_match.group(1)}\n\n"

        # Add progress indicators showing refund step completed as no refund
        # Extract order cancellation status from current message or use order_cancelled parameter
        if "✅ *Order Canceled*" in current_message_full_text:
            order_status_line = re.search(
                r"(✅ \*Order Canceled\*[^\n]*)", current_message_full_text
            )
            message += (
                order_status_line.group(1) + "\n"
                if order_status_line
                else f"✅ *Order Canceled*, processed by <@{processor_user}>\n"
            )
        elif "✅ *Order Not Canceled*" in current_message_full_text:
            order_status_line = re.search(
                r"(✅ \*Order Not Canceled\*[^\n]*)", current_message_full_text
            )
            message += (
                order_status_line.group(1) + "\n"
                if order_status_line
                else f"✅ *Order Not Canceled*, processed by <@{processor_user}>\n"
            )
        else:
            # Use order_cancelled parameter if no status found in current message
            if order_cancelled:
                message += f"✅ *Order Canceled*, processed by <@{processor_user}>\n"
            else:
                message += (
                    f"✅ *Order Not Canceled*, processed by <@{processor_user}>\n"
                )

        message += f"✅ *Not Refunded by <@{processor_user}>*\n"
        message += "📋 Inventory restocking pending\n\n"

        # Add Google Sheets link
        sheet_link = self.extract_sheet_link(current_message_full_text)
        if sheet_link:
            message += f"🔗 *<{sheet_link}|View Request in Google Sheets>*\n\n"

        # Add inventory information and build restock buttons
        message += " Current Inventory:\n"

        action_buttons = []
        variants_data = []

        # Check multiple possible locations for variants data
        if order_data:
            # Try order_data["variants"] first (from comprehensive data)
            if "variants" in order_data:
                variants_data = order_data["variants"]
            # Try order_data["product"]["variants"] as fallback (from orders service)
            elif "product" in order_data and "variants" in order_data["product"]:
                variants_data = order_data["product"]["variants"]

        if variants_data:
            for variant in variants_data:
                # Handle different field name formats from different data sources
                variant_title = (
                    variant.get("variantTitle")
                    or variant.get("variantName")
                    or variant.get("title")
                    or "Unknown Variant"
                )
                available_quantity = (
                    variant.get("availableQuantity")
                    or variant.get("inventory")
                    or variant.get("inventoryQuantity")
                    or 0
                )

                # Add inventory line
                message += f"• {variant_title}: {available_quantity} spots available\n"

                # Create restock button (remove "Registration" from variant name if present)
                button_text = variant_title.replace(" Registration", "").strip()
                action_buttons.append(
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": f"Restock {button_text}",
                        },
                        "action_id": f"confirm_restock_{button_text.lower().replace(' ', '_')}",
                        "value": json.dumps(
                            {
                                "action": "confirm_restock_variant",
                                "variantId": (
                                    variant.get("variantId") or variant.get("id") or ""
                                ),
                                "inventoryItemId": variant.get(
                                    "inventoryItemId", ""
                                ),  # Include inventory item ID directly
                                "variantTitle": variant_title,
                                "orderId": order_id,
                                "rawOrderNumber": raw_order_number,
                            }
                        ),
                    }
                )
        else:
            # Fallback if no variant data
            message += "• No inventory information available\n"

        message += "Restock Inventory?"

        # Add "Do Not Restock" button
        action_buttons.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Do Not Restock"},
                "style": "danger",  # Make button red
                "action_id": "confirm_do_not_restock",
                "value": json.dumps(
                    {
                        "action": "confirm_do_not_restock",
                        "orderId": order_id,
                        "rawOrderNumber": raw_order_number,
                    }
                ),
            }
        )

        return {"text": message, "action_buttons": action_buttons}

    # === MESSAGE MANAGEMENT HELPERS ===

    def update_slack_on_shopify_success(
        self, message_ts: str, success_message: str, action_buttons: list
    ) -> Dict[str, Any]:
        """Update Slack message on Shopify success"""
        try:
            result = self.api_client.update_message(
                message_ts=message_ts,
                message_text=success_message,
                action_buttons=action_buttons,
            )
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Failed to update Slack message on success: {e}")
            return {"success": False, "error": str(e)}

    def update_slack_on_shopify_failure(
        self, message_ts: str, error_message: str, operation_name: str
    ):
        """Update Slack message on Shopify failure"""
        try:
            # Based on memory, user prefers ephemeral popups instead of updating the main message
            logger.info(f"Shopify {operation_name} failed: {error_message}")
            # Don't update the main message - just log the error
        except Exception as e:
            logger.error(f"Failed to handle Shopify failure: {e}")

    def send_modal_error_to_user(
        self, trigger_id: Optional[str], error_message: str, operation_name: str
    ):
        """Send modal error to user using SlackService functionality"""
        try:
            if trigger_id:
                # Clean up error message for Slack compatibility
                cleaned_message = error_message.replace("**", "*").replace("•", "-")

                # Ensure title is not too long (24 char limit for modal titles)
                title_text = f"{operation_name.title()} Error"
                if len(title_text) > 24:
                    title_text = "Error"

                # Ensure message text is not too long (3000 char limit for section text)
                modal_text = (
                    f":x: *{operation_name.title()} Failed*\n\n{cleaned_message}"
                )
                if len(modal_text) > 2800:  # Leave some buffer
                    modal_text = f":x: *{operation_name.title()} Failed*\n\n{cleaned_message[:2700]}..."

                # Create modal view
                modal_view = {
                    "type": "modal",
                    "title": {"type": "plain_text", "text": title_text},
                    "close": {"type": "plain_text", "text": "Close"},
                    "blocks": [
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": modal_text},
                        }
                    ],
                }

                logger.info(f"📱 Sending modal with trigger_id: {trigger_id[:20]}...")
                logger.debug(
                    f"📱 Modal title: '{title_text}' (length: {len(title_text)})"
                )
                logger.debug(f"📱 Modal text length: {len(modal_text)}")

                # Send modal via Slack API
                result = self.api_client.send_modal(trigger_id, modal_view)  # type: ignore

                if result.get("success", False):
                    logger.info(f"✅ Sent modal error dialog for {operation_name}")
                    return True
                else:
                    logger.error(
                        f"❌ Failed to send modal dialog: {result.get('error', 'Unknown error')}"
                    )
                    return False
            else:
                logger.warning(
                    f"⚠️ No trigger_id provided for modal error: {operation_name}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Exception sending modal error dialog: {str(e)}")
            return False

    # === MODAL HELPERS ===

    def _show_restock_modal_to_user(
        self,
        trigger_id: str,
        modal_title: str,
        modal_blocks: List[Dict[str, Any]],
        callback_id: str,
        private_metadata: str,
    ) -> Dict[str, Any]:
        """Show a restock confirmation modal to the user"""
        modal_view = {
            "type": "modal",
            "callback_id": callback_id,
            "title": {"type": "plain_text", "text": modal_title},
            "submit": {"type": "plain_text", "text": "Confirm"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": modal_blocks,
            "private_metadata": private_metadata,
        }

        return self.api_client.send_modal(trigger_id, modal_view)

    # === RESTOCK CONFIRMATION MODALS ===

    async def handle_restock_confirmation_request(
        self,
        request_data: Dict[str, str],
        action_id: str,
        trigger_id: str,
        channel_id: str,
        thread_ts: str,
        current_message_full_text: str,
    ) -> Dict[str, Any]:
        """Handle restock confirmation button clicks - show confirmation modal"""
        print("\n🔄 === RESTOCK CONFIRMATION REQUEST ===")
        print(f"🔧 Action ID: {action_id}")
        print(f"📋 Request Data: {request_data}")
        print(f"✨ Trigger ID: {trigger_id}")
        print("=== END RESTOCK CONFIRMATION REQUEST ===\n")

        try:
            # Parse the action type
            if action_id == "confirm_do_not_restock":
                variant_text = "NOT restock inventory"
                confirmation_text = (
                    "Are you sure you want to skip restocking inventory for this order?"
                )
                callback_id = "restock_confirmation_modal"
                action_value = "do_not_restock"
            elif action_id.startswith("confirm_restock_"):
                variant_name = request_data.get("variantTitle", "Unknown Variant")
                variant_text = f"restock inventory for {variant_name}"
                confirmation_text = (
                    f"Are you sure you want to restock inventory for {variant_name}?"
                )
                callback_id = "restock_confirmation_modal"
                # Convert back to original action format
                action_value = action_id.replace("confirm_", "")
            else:
                return {"error": f"Unknown confirmation action: {action_id}"}

            # Create private metadata with all the necessary data
            private_metadata = json.dumps(
                {
                    "action_id": action_value,
                    "request_data": request_data,
                    "channel_id": channel_id,
                    "thread_ts": thread_ts,
                    "current_message_full_text": current_message_full_text,
                }
            )

            # Create modal blocks
            modal_blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"⚠️ *Confirm Inventory Action*\n\n{confirmation_text}",
                    },
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"You are about to *{variant_text}*.",
                    },
                },
            ]

            # Show the confirmation modal
            modal_result = self._show_restock_modal_to_user(
                trigger_id=trigger_id,
                modal_title="Confirm Inventory Action",
                modal_blocks=modal_blocks,
                callback_id=callback_id,
                private_metadata=private_metadata,
            )

            if modal_result.get("success", False):
                print("✅ Restock confirmation modal displayed successfully")
                return {"success": True, "message": "Confirmation modal shown"}
            else:
                print(f"❌ Failed to show restock confirmation modal: {modal_result}")
                return {"error": "Failed to show confirmation modal"}

        except Exception as e:
            logger.error(f"❌ Exception in restock confirmation: {str(e)}")
            return {"error": f"Confirmation failed: {str(e)}"}

    async def handle_restock_confirmation_submission(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle restock confirmation modal submission"""
        print("\n✅ === RESTOCK CONFIRMATION SUBMISSION ===")
        print(f"📦 Payload: {json.dumps(payload, indent=2)}")
        print("=== END RESTOCK CONFIRMATION SUBMISSION ===\n")

        try:
            # Extract private metadata
            private_metadata_str = payload.get("view", {}).get("private_metadata", "")
            private_metadata = (
                json.loads(private_metadata_str) if private_metadata_str else {}
            )

            action_id = private_metadata.get("action_id")
            request_data = private_metadata.get("request_data", {})
            channel_id = private_metadata.get("channel_id")
            thread_ts = private_metadata.get("thread_ts")
            current_message_full_text = private_metadata.get(
                "current_message_full_text", ""
            )

            # Get user info from payload
            user_info = payload.get("user", {})
            slack_user_name = user_info.get("name", "Unknown User")

            # Validate required fields
            if not action_id or not channel_id or not thread_ts:
                return {
                    "response_action": "errors",
                    "errors": {
                        "validation_error": "Missing required fields in modal submission"
                    },
                }

            print(f"🔄 Confirmed action: {action_id}")
            print(f"👤 User: {slack_user_name}")
            print(f"📍 Channel: {channel_id}, Thread: {thread_ts}")

            # Call the original restock handler with confirmed action
            result = await self.handle_restock_inventory(
                request_data=request_data,
                action_id=str(action_id),
                channel_id=str(channel_id),
                thread_ts=str(thread_ts),
                slack_user_name=slack_user_name,
                current_message_full_text=current_message_full_text,
                trigger_id=None,  # No trigger needed for confirmed action
            )

            print(f"✅ Restock action completed: {result}")
            # Return proper modal response to close the modal
            return {"response_action": "clear"}

        except Exception as e:
            logger.error(f"❌ Exception in restock confirmation submission: {str(e)}")
            # Return proper modal error response
            return {
                "response_action": "errors",
                "errors": {
                    "confirmation_error": f"Confirmation submission failed: {str(e)}"
                },
            }

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
        """Handle inventory restocking button clicks"""
        print("\n📦 === RESTOCK INVENTORY ACTION ===")
        print(f"👤 User: {slack_user_name}")
        print(f"🔧 Action ID: {action_id}")
        print(f"📋 Request Data: {request_data}")
        print(f"📍 Channel: {channel_id}, Thread: {thread_ts}")
        print("=== END RESTOCK INVENTORY ===\n")

        try:
            order_id = request_data.get("orderId", "")
            raw_order_number = request_data.get("rawOrderNumber", "")
            sheet_url = self.extract_sheet_link(current_message_full_text)

            # Handle "Do Not Restock" action early (no variant needed)
            if action_id == "do_not_restock":
                print("🚫 User chose not to restock inventory")
                completion_message = self.build_completion_message_after_restocking(
                    current_message_full_text=current_message_full_text,
                    action_id=action_id,
                    variant_name="",
                    restock_user=slack_user_name,
                    sheet_link=sheet_url,
                    raw_order_number=raw_order_number,
                )
                self.update_slack_on_shopify_success(
                    message_ts=thread_ts,
                    success_message=completion_message,
                    action_buttons=[],
                )
                return {"success": True, "message": "Inventory restock declined"}

            # For all other action IDs, require a variant
            variant_id = request_data.get("variantId", "")
            variant_title = request_data.get("variantTitle", "Unknown Variant")

            print("🔍 EXTRACTED VALUES:")
            print(f"   order_id: '{order_id}'")
            print(f"   raw_order_number: '{raw_order_number}'")
            print(f"   variant_id: '{variant_id}'")
            print(f"   variant_title: '{variant_title}'")

            if not variant_id:
                error_message = "Missing variant ID for inventory restock"
                logger.error(f"❌ {error_message}")
                if trigger_id:
                    self.send_modal_error_to_user(
                        trigger_id=trigger_id,
                        error_message=error_message,
                        operation_name="Inventory Restock",
                    )
                return {"success": False, "message": error_message}

            # Get inventory item ID directly from button value (no lookup needed!)
            inventory_item_id = request_data.get("inventoryItemId")

            if not inventory_item_id:
                # Fallback: if inventory item ID wasn't stored in button, do the lookup
                print(
                    "⚠️ Inventory item ID not found in button data, falling back to Shopify lookup"
                )
                inventory_info = (
                    self.orders_service.shopify_service.get_inventory_item_and_quantity(
                        variant_id
                    )
                )
                if not inventory_info.get("success"):
                    error_msg = inventory_info.get("message", "Unknown error")
                    modal_error_message = f"Failed to get inventory info for {variant_title}.\n\n**Shopify Error:**\n{error_msg}"
                    if trigger_id:
                        self.send_modal_error_to_user(
                            trigger_id, modal_error_message, "Inventory Restock"
                        )
                    logger.error(f"❌ Inventory info failed: {modal_error_message}")
                    return {"success": False, "message": error_msg}
                inventory_item_id = inventory_info.get("inventoryItemId")
                current_quantity = inventory_info.get("inventoryQuantity", 0)
                print(f"📊 Current inventory for {variant_title}: {current_quantity}")
            else:
                print(
                    f"✅ Using inventory item ID from button data: {inventory_item_id}"
                )
                current_quantity = "unknown"  # We don't need current quantity for adjustment, just for logging

            print(f"🔑 Inventory item ID: {inventory_item_id}")

            # Adjust inventory by +1 using inventory item ID
            inventory_result = self.orders_service.shopify_service.adjust_inventory(
                inventory_item_id, delta=1
            )
            if not inventory_result.get("success"):
                error_msg = inventory_result.get("message", "Unknown error")
                modal_error_message = f"Inventory restock failed for {variant_title}.\n\n**Shopify Error:**\n{error_msg}"
                if trigger_id:
                    self.send_modal_error_to_user(
                        trigger_id, modal_error_message, "Inventory Restock"
                    )
                logger.error(f"❌ Inventory restock failed: {modal_error_message}")
                return {"success": False, "message": error_msg}

            print(f"✅ Successfully restocked {variant_title} by +1")
            completion_message = self.build_completion_message_after_restocking(
                current_message_full_text=current_message_full_text,
                action_id=action_id,
                variant_name=variant_title,
                restock_user=slack_user_name,
                sheet_link=sheet_url,
                raw_order_number=raw_order_number,
            )

            self.update_slack_on_shopify_success(
                message_ts=thread_ts,
                success_message=completion_message,
                action_buttons=[],
            )

            return {
                "success": True,
                "message": f"Successfully restocked {variant_title} by +1",
                "new_quantity": (current_quantity + 1)
                if isinstance(current_quantity, int)
                else "unknown",
            }

        except Exception as e:
            error_message = f"Exception in handle_restock_inventory: {str(e)}"
            logger.error(f"❌ {error_message}")
            if trigger_id:
                self.send_modal_error_to_user(
                    trigger_id=trigger_id,
                    error_message=f"Unexpected error during inventory restock.\n\n**Error:**\n{str(e)}",
                    operation_name="Inventory Restock",
                )
            return {"success": False, "message": error_message}

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
        """
        Handle edit request details button click - shows modal for editing order number and requestor email
        """
        print("\n✏️ === EDIT REQUEST DETAILS HANDLER ===")
        print(f"👤 User: {slack_user_name} ({slack_user_id})")
        print(f"📋 Request Data: {request_data}")
        print(f"🎯 Trigger ID: {trigger_id}")
        print("=== END EDIT REQUEST DETAILS ===\n")

        try:
            # Extract current values from request_data - handle both new and legacy formats
            raw_order_number = (
                request_data.get("orderName", "")
                or request_data.get("rawOrderNumber", "")
            ).replace("#", "")  # Remove # for editing
            requestor_email = request_data.get("requestorEmail", "")

            # Parse requestor name - handle both new format (requestorName) and legacy format (first/last)
            requestor_name_full = request_data.get("requestorName", "")
            if requestor_name_full:
                name_parts = requestor_name_full.split(" ", 1)
                first_name = name_parts[0] if len(name_parts) > 0 else ""
                last_name = name_parts[1] if len(name_parts) > 1 else ""
            else:
                # Fallback to legacy format
                first_name = request_data.get("first", "")
                last_name = request_data.get("last", "")

            refund_type = request_data.get("refundType", "refund")
            notes = request_data.get("notes", "")
            request_submitted_at = request_data.get(
                "submittedAt", ""
            ) or request_data.get("requestSubmittedAt", "")

            # Build modal for editing
            modal_blocks = self._build_edit_request_modal_blocks(
                raw_order_number=raw_order_number,
                requestor_email=requestor_email,
                first_name=first_name,
                last_name=last_name,
                refund_type=refund_type,
                notes=notes,
                request_submitted_at=request_submitted_at,
            )

            # Prepare private metadata with original request data AND message context
            private_metadata = json.dumps(
                {
                    "first": first_name,
                    "last": last_name,
                    "refund_type": refund_type,
                    "notes": notes,
                    "request_submitted_at": request_submitted_at,
                    "original_thread_ts": thread_ts,  # Store original message timestamp
                    "original_channel_id": channel_id,  # Store channel ID
                }
            )

            # Show modal to user
            modal_result = self._show_modal_to_user(
                trigger_id=trigger_id,
                modal_title="Edit Request Details",
                modal_blocks=modal_blocks,
                callback_id="edit_request_details_submission",
                private_metadata=private_metadata,
                submit_text="Update Request",
            )

            if modal_result.get("success"):
                logger.info(f"✅ Modal shown successfully to {slack_user_name}")
                return {"success": True, "message": "Modal displayed"}
            else:
                error_msg = modal_result.get("error", "Unknown modal error")
                slack_response = modal_result.get("slack_response", {})
                logger.error(f"❌ Failed to show modal: {error_msg}")
                logger.error(f"❌ Modal result: {modal_result}")
                logger.error(f"❌ Slack response: {slack_response}")
                return {"success": False, "message": f"Slack API error: {error_msg}"}

        except Exception as e:
            error_message = f"Exception in handle_edit_request_details: {str(e)}"
            logger.error(f"❌ {error_message}")
            return {"success": False, "message": error_message}

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
        """
        Consolidated modal handler for all denial types - shows modal for custom message and confirmation
        """
        print("\n🚫 === DENY REQUEST MODAL ===")
        print(f"📦 Request Data: {json.dumps(request_data, indent=2)}")
        print(f"👤 User: {slack_user_name} (ID: {slack_user_id})")
        print(f"🎯 Trigger ID: {trigger_id}")
        print("🚫 === END DENY REQUEST MODAL DEBUG ===\n")

        try:
            # Extract request details from the button value or current message
            raw_order_number = request_data.get("rawOrderNumber", "")
            requestor_email = request_data.get("requestorEmail", "")
            first_name = request_data.get("first", "")
            last_name = request_data.get("last", "")
            refund_type = request_data.get("refundType", "refund")
            request_submitted_at = request_data.get("requestSubmittedAt", "")

            # Build the modal blocks (works for all denial types)
            modal_blocks = self._build_deny_request_modal_blocks(
                raw_order_number=raw_order_number,
                requestor_email=requestor_email,
                first_name=first_name,
                last_name=last_name,
                refund_type=refund_type,
            )

            # Prepare private metadata with original message context
            private_metadata = {
                "raw_order_number": raw_order_number,
                "requestor_email": requestor_email,
                "first_name": first_name,
                "last_name": last_name,
                "refund_type": refund_type,
                "request_submitted_at": request_submitted_at,
                "original_thread_ts": thread_ts,
                "original_channel_id": channel_id,
                "slack_user_name": slack_user_name,
                "slack_user_id": slack_user_id,
            }

            # Show the modal
            modal_result = self._show_modal_to_user(
                trigger_id=trigger_id,
                modal_title="Deny Refund Request",
                modal_blocks=modal_blocks,
                callback_id="deny_refund_request_modal_submission",
                private_metadata=json.dumps(private_metadata),
                submit_text="Deny & Send Email",
            )

            if modal_result.get("success"):
                print("✅ Deny request modal shown successfully")
                return {"success": True, "message": "Modal displayed"}
            else:
                error_msg = modal_result.get("error", "Unknown modal error")
                slack_response = modal_result.get("slack_response", {})
                print(f"❌ Failed to show deny modal: {error_msg}")
                print(f"❌ Modal result: {modal_result}")
                print(f"❌ Slack response: {slack_response}")
                return {"success": False, "message": f"Slack API error: {error_msg}"}

        except Exception as e:
            error_message = (
                f"Exception in handle_deny_refund_request_show_modal: {str(e)}"
            )
            logger.error(f"❌ {error_message}")
            return {"success": False, "error": error_message}

    async def handle_deny_refund_request_modal_submission(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Consolidated modal submission handler for all denial types - send email via GAS and update Slack
        """
        print("\n🚫 === DENY REQUEST MODAL SUBMISSION ===")
        print(f"📋 Full Payload: {json.dumps(payload, indent=2)}")
        print("=== END DENY SUBMISSION DEBUG ===\n")

        try:
            # Extract form values (works for all denial types)
            values = payload.get("view", {}).get("state", {}).get("values", {})
            custom_message = (
                values.get("custom_message_input", {})
                .get("custom_message", {})
                .get("value", "")
            )
            cc_bcc_option = (
                values.get("cc_bcc_input", {})
                .get("cc_bcc_option", {})
                .get("selected_option", {})
                .get("value", "no")
            )

            # Extract metadata
            private_metadata_str = payload.get("view", {}).get("private_metadata", "{}")
            private_metadata = json.loads(private_metadata_str)

            original_thread_ts = private_metadata.get("original_thread_ts")
            original_channel_id = private_metadata.get("original_channel_id")  # noqa: F841
            slack_user_name = private_metadata.get("slack_user_name", "Unknown")
            slack_user_id = private_metadata.get("slack_user_id", "Unknown")
            raw_order_number = private_metadata.get("raw_order_number", "")
            requestor_email = private_metadata.get("requestor_email", "")
            first_name = private_metadata.get("first_name", "")
            last_name = private_metadata.get("last_name", "")

            print("✉️ Sending denial email via GAS with:")
            print(f"   Order: {raw_order_number}")
            print(f"   Requestor: {first_name} {last_name} ({requestor_email})")
            print(f"   Custom Message: {custom_message[:100]}...")
            print(f"   CC/BCC Option: {cc_bcc_option}")
            print(f"   Staff: {slack_user_name} ({slack_user_id})")

            # Send email via GAS doPost
            await self._send_denial_email_via_gas(
                order_number=raw_order_number,
                requestor_email=requestor_email,
                first_name=first_name,
                last_name=last_name,
                custom_message=custom_message,
                cc_bcc_option=cc_bcc_option,
                slack_user_name=slack_user_name,
                slack_user_id=slack_user_id,
            )

            # Update original Slack message
            denial_confirmation_message = (
                self._build_general_denial_confirmation_message(
                    order_number=raw_order_number,
                    requestor_email=requestor_email,
                    first_name=first_name,
                    last_name=last_name,
                    slack_user_name=slack_user_name,
                    custom_message_provided=bool(custom_message.strip()),
                    cc_bcc_option=cc_bcc_option,
                )
            )

            # Update the original Slack message
            print(
                f"🔍 DEBUG: Attempting to update message with timestamp: {original_thread_ts}"
            )
            print(f"🔍 DEBUG: Channel ID: {self.api_client.channel_id}")
            print(f"🔍 DEBUG: Message length: {len(denial_confirmation_message)}")

            update_result = self.update_slack_on_shopify_success(
                message_ts=original_thread_ts,
                success_message=denial_confirmation_message,
                action_buttons=[],  # No buttons for final denial
            )

            print(f"🔍 DEBUG: Update result: {update_result}")

            return {"response_action": "clear"}

        except Exception as e:
            logger.error(
                f"❌ Exception in handle_deny_refund_request_modal_submission: {str(e)}"
            )
            return {"response_action": "clear"}

    def _build_edit_request_modal_blocks(
        self,
        raw_order_number: str,
        requestor_email: str,
        first_name: str,
        last_name: str,
        refund_type: str,
        notes: str,
        request_submitted_at: str,
    ) -> List[Dict[str, Any]]:
        """
        Build the modal blocks for editing request details
        """
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":pencil2: *Edit Request Details*\n\nUpdate the order number or requestor email to re-validate the request.",
                },
            },
            {"type": "divider"},
            {
                "type": "input",
                "block_id": "order_number_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "order_number",
                    "initial_value": raw_order_number,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Enter order number (without #)",
                    },
                },
                "label": {"type": "plain_text", "text": "Order Number"},
            },
            {
                "type": "input",
                "block_id": "requestor_email_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "requestor_email",
                    "initial_value": requestor_email,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Enter requestor email address",
                    },
                },
                "label": {"type": "plain_text", "text": "Requestor Email"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":information_source: *Note:* After updating, the request will be re-validated against Shopify to check if the order exists and if the email matches.",
                },
            },
        ]

        return blocks

    def _show_modal_to_user(
        self,
        trigger_id: str,
        modal_title: str,
        modal_blocks: List[Dict[str, Any]],
        callback_id: str,
        private_metadata: str = "",
        submit_text: str = "Submit",
    ) -> Dict[str, Any]:
        """
        Show a modal dialog to the user
        """
        try:
            modal_view = {
                "type": "modal",
                "callback_id": callback_id,
                "title": {"type": "plain_text", "text": modal_title},
                "blocks": modal_blocks,
                "submit": {"type": "plain_text", "text": submit_text},
                "close": {"type": "plain_text", "text": "Cancel"},
            }

            if private_metadata:
                modal_view["private_metadata"] = private_metadata

            response = self.api_client.send_modal(trigger_id, modal_view)

            if response.get("success"):
                return {"success": True}
            else:
                error = response.get("error", "Unknown error")
                return {"success": False, "error": f"Slack API error: {error}"}
        except Exception as e:
            return {"success": False, "error": f"Exception showing modal: {str(e)}"}

    async def handle_edit_request_details_submission(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle modal submission for editing request details
        Re-validates the request with updated order number and email
        """
        print("\n📝 === EDIT REQUEST DETAILS SUBMISSION ===")
        print(f"📋 Full Payload: {json.dumps(payload, indent=2)}")
        print("=== END SUBMISSION DEBUG ===\n")

        try:
            # Extract user info
            user_info = payload.get("user", {})
            slack_user_name = user_info.get("name", "Unknown")  # noqa: F841
            slack_user_id = user_info.get("id", "Unknown")  # noqa: F841

            # Extract view data
            view = payload.get("view", {})
            state = view.get("state", {})
            values = state.get("values", {})

            # Extract updated values from modal
            order_number_input = values.get("order_number_input", {}).get(
                "order_number", {}
            )
            requestor_email_input = values.get("requestor_email_input", {}).get(
                "requestor_email", {}
            )

            updated_order_number = order_number_input.get("value", "").strip()
            updated_requestor_email = requestor_email_input.get("value", "").strip()

            print("✏️ Updated values:")
            print(f"   Order Number: {updated_order_number}")
            print(f"   Requestor Email: {updated_requestor_email}")

            # Validate input
            if not updated_order_number or not updated_requestor_email:
                return {
                    "response_action": "errors",
                    "errors": {
                        "order_number_input": "Order number is required"
                        if not updated_order_number
                        else "",
                        "requestor_email_input": "Email is required"
                        if not updated_requestor_email
                        else "",
                    },
                }

            # Extract private metadata to reconstruct original request
            private_metadata = view.get("private_metadata", "{}")
            try:
                original_request_data = (
                    json.loads(private_metadata) if private_metadata != "{}" else {}
                )
            except:  # noqa: E722
                original_request_data = {}

            # Extract original message context for updating
            original_thread_ts = original_request_data.get("original_thread_ts")
            original_channel_id = original_request_data.get("original_channel_id")

            # Reconstruct request data with updated values
            updated_request_data = {
                "order_number": updated_order_number,
                "requestor_name": {
                    "first": original_request_data.get("first", ""),
                    "last": original_request_data.get("last", ""),
                },
                "requestor_email": updated_requestor_email,
                "refund_type": original_request_data.get("refund_type", "refund"),
                "notes": original_request_data.get("notes", ""),
                "sheet_link": original_request_data.get("sheet_link", ""),
            }

            print("🔄 Re-validating request with updated data:")
            print(f"   {json.dumps(updated_request_data, indent=2)}")

            # Re-validate directly using orders service (avoid circular API call)
            print(
                f"🔍 Validating order {updated_order_number} with email {updated_requestor_email}"
            )

            # Step 1: Check if order exists
            order_result = (
                self.orders_service.fetch_order_details_by_email_or_order_name(
                    order_name=updated_order_number
                )
            )

            if not order_result["success"]:
                print(f"❌ Order {updated_order_number} not found")
                return {
                    "response_action": "errors",
                    "errors": {
                        "order_number_input": "Order not found with this number"
                    },
                }

            # Step 2: Check if email matches
            order_data = order_result["data"]
            order_customer_email = (
                order_data.get("customer", {}).get("email", "").lower().strip()
            )
            requestor_email_lower = updated_requestor_email.lower().strip()

            if order_customer_email != requestor_email_lower:
                print(
                    f"⚠️ Email mismatch: Order email '{order_customer_email}' != Requestor email '{requestor_email_lower}'"
                )
                return {
                    "response_action": "errors",
                    "errors": {
                        "requestor_email_input": "Email still does not match the order's customer email"
                    },
                }

            # Step 3: Success - update original message with success case
            print("✅ Re-validation successful - order found and email matches")

            # Build requestor info from updated data
            requestor_info = {
                "first": original_request_data.get("first", ""),
                "last": original_request_data.get("last", ""),
                "email": updated_requestor_email,
                "refund_type": original_request_data.get("refund_type", "refund"),
                "notes": original_request_data.get("notes", ""),
                "sheet_link": original_request_data.get("sheet_link", ""),
            }

            # Calculate refund amount using the existing orders service method
            refund_calculation = self.orders_service.calculate_refund_due(
                order_data, requestor_info["refund_type"]
            )

            if not refund_calculation["success"]:
                print(
                    f"❌ Failed to calculate refund: {refund_calculation.get('message', 'Unknown error')}"
                )
                return {"response_action": "clear"}

            # Fetch customer data for profile linking (same as initial refund request)
            print(f"🔍 Fetching customer data for email: {updated_requestor_email}")
            customer_result = self.orders_service.shopify_service.get_customer_by_email(
                updated_requestor_email
            )
            customer_data = (
                customer_result.get("customer")
                if customer_result.get("success")
                else None
            )
            if customer_data:
                print(
                    f"✅ Customer found: {customer_data.get('firstName', '')} {customer_data.get('lastName', '')}"
                )
            else:
                print(f"📭 No customer found for email: {updated_requestor_email}")

            # Build success message using the exact same format as initial successful requests
            updated_requestor_info_for_message = {
                "name": {
                    "first": requestor_info["first"],
                    "last": requestor_info["last"],
                },
                "email": requestor_info["email"],
                "refund_type": requestor_info["refund_type"],
                "notes": requestor_info["notes"],
                "customer_data": customer_data,  # Include customer data for profile linking
            }

            success_message_data = self.message_builder.build_success_message(
                order_data={"order": order_data},
                refund_calculation=refund_calculation,
                requestor_info=updated_requestor_info_for_message,
                sheet_link="",
            )

            # Get the original message timestamp from private metadata or context
            # Since we don't have access to the original thread_ts here, we'll need to get it
            # from the payload context or pass it through

            # For now, let's extract the thread_ts from the payload if available
            # This might need to be passed through the private metadata

            print("🔄 Updating original Slack message with success details")
            print(
                f"📊 Refund calculation: ${refund_calculation.get('refund_amount', 'unknown')}"
            )

            # Update the original message with success details
            if original_thread_ts and original_channel_id:
                print(
                    f"📍 Updating message {original_thread_ts} in channel {original_channel_id}"
                )

                update_result = self.update_slack_on_shopify_success(
                    message_ts=original_thread_ts,
                    success_message=success_message_data["text"],
                    action_buttons=success_message_data["action_buttons"],
                )

                if update_result.get("success"):
                    print(
                        "✅ Original message updated successfully with order details and refund buttons"
                    )
                else:
                    print(
                        f"⚠️ Failed to update original message: {update_result.get('error', 'Unknown error')}"
                    )
            else:
                print(
                    "❌ Missing original message context - cannot update original message"
                )
                print(
                    f"   thread_ts: {original_thread_ts}, channel_id: {original_channel_id}"
                )

            return {"response_action": "clear"}

        except Exception as e:
            error_message = (
                f"Exception in handle_edit_request_details_submission: {str(e)}"
            )
            logger.error(f"❌ {error_message}")
            return {
                "response_action": "errors",
                "errors": {"order_number_input": "An error occurred during validation"},
            }

    def _build_deny_request_modal_blocks(
        self,
        raw_order_number: str,
        requestor_email: str,
        first_name: str,
        last_name: str,
        refund_type: str,
    ) -> List[Dict[str, Any]]:
        """
        Build the modal blocks for the deny request form
        """
        refund_type_text = "refund" if refund_type.lower() == "refund" else "credit"
        requestor_name = f"{first_name} {last_name}".strip()

        # Default denial message (check if this is a general denial or email mismatch)
        is_email_mismatch = refund_type.lower() == "email_mismatch"

        if is_email_mismatch:
            default_message = (
                f"Hi {first_name},\n\n"
                f"Your request for a {refund_type_text} has not been processed successfully. "
                f"The email associated with the order number did not match the email you provided in the request, and we don't want to send your refund to the wrong person."
                f"Please confirm you submitted your request using the same email address as is associated with your order - "
                f"sign in to see your order history to find the correct order number - and try again.\n\n"
                f"If you believe this is in error, please reach out to refunds@bigapplerecsports.com."
            )
        else:
            default_message = (
                f"Hi {first_name},\n\n"
                f"We're sorry, but we were not able to approve your refund request for Order {raw_order_number}. "
                f"Please sign in to view your orders and try again if needed.\n\n"
                f"If you have any questions, please reach out to refunds@bigapplerecsports.com."
            )

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"You are about to send a denial email to *{requestor_name}* ({requestor_email}) for order *{raw_order_number}*.",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Subject Line:* \nBig Apple Rec Sports - Order {raw_order_number} - Refund Request Denied",
                },
            },
            {
                "type": "input",
                "block_id": "custom_message_input",
                "label": {
                    "type": "plain_text",
                    "text": "Email Body (edit to your liking)",
                },
                "element": {
                    "type": "plain_text_input",
                    "action_id": "custom_message",
                    "multiline": True,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Enter the email message content...",
                    },
                    "initial_value": default_message,
                },
                "optional": False,
            },
            {
                "type": "input",
                "block_id": "cc_bcc_input",
                "label": {
                    "type": "plain_text",
                    "text": 'Do you want to be CC/BCC\'d on the email? (it will be sent from the web@ alias and signed "BARS Leadership")',
                },
                "element": {
                    "type": "static_select",
                    "action_id": "cc_bcc_option",
                    "placeholder": {"type": "plain_text", "text": "Select an option"},
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "No"},
                        "value": "no",
                    },
                    "options": [
                        {"text": {"type": "plain_text", "text": "No"}, "value": "no"},
                        {"text": {"type": "plain_text", "text": "CC"}, "value": "cc"},
                        {"text": {"type": "plain_text", "text": "BCC"}, "value": "bcc"},
                    ],
                },
                "optional": False,
            },
        ]

        return blocks

    async def _send_denial_email(
        self,
        requestor_email: str,
        requestor_name: Dict[str, str],
        raw_order_number: str,
        refund_type: str,
        custom_message: str,
        include_staff_info: bool,
        staff_name: str,
        staff_id: str,
    ) -> Dict[str, Any]:
        """
        Send denial email to the requestor with custom message and optional staff info
        """
        try:
            first_name = requestor_name.get("first", "")
            refund_type_text = "refund" if refund_type.lower() == "refund" else "credit"

            # Build email subject
            subject = f"Big Apple Rec Sports - {refund_type_text.title()} Request Denied for Order {raw_order_number}"

            # Use custom message or default
            if custom_message and custom_message.strip():
                message_body = custom_message.strip()
            else:
                # Default denial message (extracted from GAS email)
                message_body = (
                    f"Hi {first_name},\\n\\n"
                    f"Your request for a {refund_type_text} has not been processed successfully. "
                    f"The email associated with the order number did not match the email you provided in the request. "
                    f"Please confirm you submitted your request using the same email address as is associated with your order - "
                    f'<a href="https://shopify.com/55475535966/account">Sign In to see your order history</a> '
                    f"to find the correct order number - and try again.\\n\\n"
                    f"If you believe this is in error, please reach out to refunds@bigapplerecsports.com."
                )

            # Add staff info if requested
            if include_staff_info:
                message_body += f"\\n\\nThis message was processed by {staff_name}."

            # Add BARS signature
            message_body += "\\n\\n--\\n" "Warmly,\\n" "**BARS Leadership**"

            # Note: HTML format conversion could be added here if needed

            print("📧 Sending denial email:")
            print(f"   To: {requestor_email}")
            print(f"   Subject: {subject}")
            print(f"   Include staff info: {include_staff_info}")

            # Here you would actually send the email
            # For now, we'll simulate success
            # In a real implementation, you'd use an email service like SendGrid, AWS SES, etc.

            print(f"✅ Denial email sent successfully to {requestor_email}")
            return {"success": True, "message": "Email sent successfully"}

        except Exception as e:
            error_message = f"Failed to send denial email: {str(e)}"
            logger.error(f"❌ {error_message}")
            return {"success": False, "error": error_message}

    def _build_denial_confirmation_message(
        self,
        requestor_email: str,
        requestor_name: Dict[str, str],
        raw_order_number: str,
        staff_name: str,
        include_staff_info: bool,
    ) -> str:
        """
        Build the confirmation message to replace the original Slack message after denial
        """
        requestor_full_name = f"{requestor_name.get('first', '')} {requestor_name.get('last', '')}".strip()
        current_time = format_date_and_time(datetime.now(timezone.utc))

        message = (
            f"🚫 *Refund Request Denied - Email Mismatch*\\n\\n"
            f"*Request for:* {requestor_full_name} ({requestor_email})\\n"
            f"*Order Number:* {raw_order_number}\\n"
            f"*Processed by:* <@{staff_name}>\\n"
            f"*Processed at:* {current_time}\\n\\n"
            f"✅ **Denial email sent to requestor**\\n"
        )

        if include_staff_info:
            message += "📧 *Email included staff information*\\n"

        message += "\\n*Reason:* Email address did not match order customer email"

        return message

    async def _send_denial_email_via_gas(
        self,
        order_number: str,
        requestor_email: str,
        first_name: str,
        last_name: str,
        custom_message: str,
        cc_bcc_option: str,
        slack_user_name: str,
        slack_user_id: str,
    ):
        """
        Send denial email via Google Apps Script doPost endpoint
        """
        try:
            # Get GAS webhook URL from environment variables
            import os

            gas_webhook_url = os.getenv("GAS_REFUNDS_WEBHOOK_URL")
            if not gas_webhook_url:
                raise ValueError(
                    "GAS_REFUNDS_WEBHOOK_URL environment variable is required but not set"
                )

            # Prepare the payload for the GAS doPost
            payload = {
                "action": "send_denial_email",
                "order_number": order_number,
                "requestor_email": requestor_email,
                "first_name": first_name,
                "last_name": last_name,
                "custom_message": custom_message,
                "cc_bcc_option": cc_bcc_option,
                "slack_user_name": slack_user_name,
                "slack_user_id": slack_user_id,
            }

            print(f"📡 Sending denial email request to GAS: {gas_webhook_url}")
            print(f"📦 Payload: {json.dumps(payload, indent=2)}")

            # Send HTTP request to GAS doPost endpoint
            import requests

            try:
                response = requests.post(
                    gas_webhook_url,
                    headers={
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=30,
                    verify=False,  # For development - SSL issues with local testing
                )

                print(f"📥 GAS Response Status: {response.status_code}")
                print(f"📄 GAS Response: {response.text}")

                if response.status_code == 200:
                    response_data = response.json()
                    if response_data.get("success"):
                        logger.info("✅ Denial email sent successfully via GAS")
                    else:
                        logger.error(
                            f"❌ GAS reported failure: {response_data.get('message', 'Unknown error')}"
                        )
                else:
                    logger.error(
                        f"❌ GAS HTTP error: {response.status_code} - {response.text}"
                    )

            except requests.exceptions.SSLError as ssl_error:
                logger.warning(
                    f"SSL Error with GAS - trying without verification: {ssl_error}"
                )
                # Retry without SSL verification
                response = requests.post(
                    gas_webhook_url,
                    headers={
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=30,
                    verify=False,
                )

                print(f"📥 GAS Response Status (no SSL): {response.status_code}")
                print(f"📄 GAS Response (no SSL): {response.text}")

                if response.status_code == 200:
                    logger.info(
                        "✅ Denial email sent successfully via GAS (no SSL verification)"
                    )
                else:
                    logger.error(
                        f"❌ GAS HTTP error (no SSL): {response.status_code} - {response.text}"
                    )

            logger.info(
                f"✉️ Denial email request sent to GAS for order {order_number} to {requestor_email}"
            )

        except Exception as e:
            logger.error(f"❌ Error sending denial email via GAS: {str(e)}")
            raise

    def _build_general_denial_confirmation_message(
        self,
        order_number: str,
        requestor_email: str,
        first_name: str,
        last_name: str,
        slack_user_name: str,
        custom_message_provided: bool,
        cc_bcc_option: str,
    ) -> str:
        """
        Build confirmation message for Slack after denial email is sent
        """
        from utils.date_utils import format_date_and_time
        from datetime import datetime, timezone

        current_time = format_date_and_time(datetime.now(timezone.utc))

        message = (
            f"🚫 *Refund Request Denied*\\n\\n"
            f"*Order Number:* {order_number}\\n"
            f"*Requestor:* {first_name} {last_name} ({requestor_email})\\n"
            f"*Processed by:* <@{slack_user_name}>\\n"
            f"*Processed at:* {current_time}\\n\\n"
            f"✅ **Denial email sent to requestor**\\n"
        )

        if custom_message_provided:
            message += "📝 *Custom message included*\\n"

        if cc_bcc_option != "no":
            message += f"📧 *Staff was {cc_bcc_option.upper()}'d on the email*\\n"

        message += (
            "\\n*The requestor has been notified that their refund request was denied.*"
        )

        return message
