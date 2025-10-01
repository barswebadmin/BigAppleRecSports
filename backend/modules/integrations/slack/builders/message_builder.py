"""
Slack message building utilities.

"""

from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone
import logging
from shared.date_utils import format_date_and_time, parse_shopify_datetime
from modules.integrations.shopify.builders.shopify_url_builders import build_customer_url, build_order_url, build_product_url
from config import config
from config.slack import SlackGroup

logger = logging.getLogger(__name__)

slack_groups = SlackGroup()


class SlackMessageBuilder:
    """Helper class for building Slack messages with consistent formatting."""

    def __init__(self, sport_groups: dict[str, dict[str, str]]):
        self.sport_groups = slack_groups.all()

    def build_header_block(self, header_text: str) -> Dict[str, Any]:
        """Build a header block for Slack"""
        return {
            "type": "header",
            "text": {"type": "plain_text", "text": header_text}
        }

    def build_section_block(self, text: str) -> Dict[str, Any]:
        """Build a section block for Slack"""
        return {
            "type": "section",
            "text": {"type": "mrkdwn", "text": text}
        }
    
    def get_group_mention(self, text: str) -> str:
        """Resolve a group mention using SlackConfig.Group mapping; fallback to @here.

        Attempts exact key match first, then substring match on known keys.
        """
        try:
            if not isinstance(text, str) or not text.strip():
                return "@here"

            target = text.lower().strip()

            group_info = SlackGroup.get(target)
            return group_info["id"] if "id" in group_info else "@here"
        except Exception:
            return "@here"

    def build_hyperlink(self, url: str, text: str) -> str:
        """Build a hyperlink for Slack"""
        return f"<{url}|{text}>"

    def _get_request_type_text(self, refund_type: str) -> str:
        """Get detailed request type text for messages"""
        if refund_type.lower() == "refund":
            return "💵 Refund back to original form of payment"
        elif refund_type.lower() == "credit":
            return "🎟️ Store Credit to use toward a future order"
        else:
            return f"❓ {refund_type.title()}"

    def _get_optional_request_notes(self, request_notes: str) -> str:
        """Get formatted optional request notes"""
        try:
            if (
                request_notes
                and isinstance(request_notes, str)
                and request_notes.strip()
            ):
                return f"*Notes provided by requestor*: {request_notes}\n\n"
            return ""
        except Exception:
            return ""

    def _get_requestor_line(
        self,
        requestor_name: Dict[str, str],
        requestor_email: str,
        customer_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Get formatted requestor line with optional customer profile hyperlink"""
        try:
            if isinstance(requestor_name, dict):
                first_name = requestor_name.get("first", "")
                last_name = requestor_name.get("last", "")
                full_name = f"{first_name} {last_name}".strip()

                if full_name and customer_data and customer_data.get("id"):
                    # Create hyperlinked name to customer profile
                    customer_url = self.build_hyperlink(build_customer_url(customer_data["id"]), full_name)
                    return f"📧 *Requested by:* <{customer_url}|{full_name}> ({requestor_email})\n\n"
                elif full_name:
                    # Fallback to plain text name
                    return f"📧 *Requested by:* {full_name} ({requestor_email})\n\n"
            return f"📧 *Requested by:* {requestor_email}\n\n"
        except Exception:
            return f"📧 *Requested by:* {requestor_email}\n\n"

    def _get_sheet_link_line(self, sheet_link: Optional[str]) -> str:
        """Get formatted sheet link line"""
        try:
            if sheet_link and isinstance(sheet_link, str) and sheet_link.strip():
                return f"\n \n 🔗 *<{sheet_link}|View Request in Google Sheets>*\n\n"
            return ""
        except Exception:
            return ""

    def _get_order_created_time(self, order: Dict[str, Any]) -> str:
        """Extract and format order creation time from order data"""
        try:
            # Try different possible field names for order creation time
            created_at_fields = [
                "created_at",
                "createdAt",
                "orderCreatedAt",
                "order_created_at",
                "processedAt",
                "processed_at",
            ]

            for field in created_at_fields:
                if field in order and order[field]:
                    created_at = parse_shopify_datetime(order[field])
                    if created_at:
                        return format_date_and_time(created_at)

            # If no creation time found, return unknown
            return "Unknown"

        except Exception:
            return "Unknown"

    # === INITIAL DECISION BUTTONS (Step 1: Cancel Order or Proceed) ===

    def _create_cancel_order_button(
        self,
        order_id: str,
        order_number: str,
        requestor_name: Dict[str, str],
        requestor_email: str,
        refund_type: str,
        refund_amount: float,
        request_submitted_at: str = "",
    ) -> Dict[str, Any]:
        """Create the cancel order button (Step 1)"""
        try:
            first_name = requestor_name.get("first", "")
            last_name = requestor_name.get("last", "")

            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "✅ Cancel Order → Proceed"},
                "style": "primary",
                "action_id": "cancel_order",
                "value": f"rawOrderNumber={order_number}|refundType={refund_type}|requestorEmail={requestor_email}|first={first_name}|last={last_name}|email={requestor_email}|requestSubmittedAt={request_submitted_at}",
                "confirm": {
                    "title": {"type": "plain_text", "text": "Cancel Order"},
                    "text": {
                        "type": "plain_text",
                        "text": f"Cancel order {order_number} in Shopify? This will show refund options next.",
                    },
                    "confirm": {"type": "plain_text", "text": "Yes, cancel order"},
                    "deny": {"type": "plain_text", "text": "No, keep order"},
                },
            }
        except Exception:
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "✅ Cancel Order → Proceed"},
                "style": "primary",
                "action_id": "cancel_order",
                "value": f"rawOrderNumber={order_number}",
            }

    def _create_proceed_without_cancel_button(
        self,
        order_id: str,
        order_number: str,
        requestor_name: Dict[str, str],
        requestor_email: str,
        refund_type: str,
        refund_amount: float,
        request_submitted_at: str = "",
    ) -> Dict[str, Any]:
        """Create the proceed without canceling button (Step 1)"""
        try:
            first_name = requestor_name.get("first", "")
            last_name = requestor_name.get("last", "")

            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "➡️ Do Not Cancel → Proceed"},
                "action_id": "proceed_without_cancel",
                "value": f"rawOrderNumber={order_number}|refundType={refund_type}|requestorEmail={requestor_email}|first={first_name}|last={last_name}|email={requestor_email}|requestSubmittedAt={request_submitted_at}",
                "confirm": {
                    "title": {
                        "type": "plain_text",
                        "text": "Proceed Without Canceling",
                    },
                    "text": {
                        "type": "plain_text",
                        "text": f"Keep order {order_number} active and proceed to refund options?",
                    },
                    "confirm": {"type": "plain_text", "text": "Yes, proceed"},
                    "deny": {"type": "plain_text", "text": "Cancel"},
                },
            }
        except Exception:
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "➡️ Do Not Cancel → Proceed"},
                "action_id": "proceed_without_cancel",
                "value": f"rawOrderNumber={order_number}",
                "confirm": {
                    "title": {
                        "type": "plain_text",
                        "text": "Proceed Without Canceling",
                    },
                    "text": {
                        "type": "plain_text",
                        "text": f"Keep order {order_number} active and proceed to refund options?",
                    },
                    "confirm": {"type": "plain_text", "text": "Yes, proceed"},
                    "deny": {"type": "plain_text", "text": "Cancel"},
                },
            }

    def _create_deny_request_button(
        self,
        order_id: str,
        order_number: str,
        requestor_name: Dict[str, str],
        requestor_email: str,
        refund_type: str,
        refund_amount: float,
        request_submitted_at: str = "",
    ) -> Dict[str, Any]:
        """Create the deny request button (Step 1)"""
        try:
            first_name = requestor_name.get("first", "")
            last_name = requestor_name.get("last", "")

            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "🚫 Deny Request"},
                "style": "danger",
                "action_id": "deny_refund_request_show_modal",
                "value": f"rawOrderNumber={order_number}|refundType={refund_type}|requestorEmail={requestor_email}|first={first_name}|last={last_name}|email={requestor_email}|requestSubmittedAt={request_submitted_at}",
            }
        except Exception:
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "🚫 Deny Request"},
                "style": "danger",
                "action_id": "deny_refund_request_show_modal",
                "value": f"rawOrderNumber={order_number}",
            }

    # === REFUND DECISION BUTTONS (Step 2: After Cancel/Proceed) ===

    def _create_process_refund_button(
        self,
        order_id: str,
        order_number: str,
        requestor_name: Dict[str, str],
        requestor_email: str,
        refund_type: str,
        refund_amount: float,
        order_cancelled: bool = False,
    ) -> Dict[str, Any]:
        """Create the process calculated refund button (Step 2)"""
        first_name = requestor_name.get("first", "")
        last_name = requestor_name.get("last", "")

        try:
            formatted_amount = (
                int(refund_amount)
                if refund_amount == int(refund_amount)
                else f"{refund_amount:.2f}"
            )

            button_text = (
                f"✅ Process ${formatted_amount} Refund"
                if refund_type == "refund"
                else f"✅ Issue ${formatted_amount} Store Credit"
            )

            return {
                "type": "button",
                "text": {"type": "plain_text", "text": button_text},
                "action_id": "process_refund",
                "value": f"rawOrderNumber={order_number}|orderId={order_id}|refundAmount={refund_amount}|refundType={refund_type}|orderCancelled={order_cancelled}|first={first_name}|last={last_name}|email={requestor_email}",
                "style": "primary",
                "confirm": {
                    "title": {"type": "plain_text", "text": "Confirm Refund"},
                    "text": {
                        "type": "plain_text",
                        "text": f"Issue {first_name} {last_name} a {refund_type} for ${formatted_amount}?",
                    },
                    "confirm": {"type": "plain_text", "text": "Yes, process refund"},
                    "deny": {"type": "plain_text", "text": "Cancel"},
                },
            }
        except Exception:
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "✅ Process Refund"},
                "action_id": "process_refund",
                "value": f"rawOrderNumber={order_number}|orderId={order_id}|refundAmount={refund_amount}|first={first_name}|last={last_name}|email={requestor_email}",
                "style": "primary",
            }

    def _create_custom_refund_button(
        self,
        order_id: str,
        order_number: str,
        requestor_name: Dict[str, str],
        requestor_email: str,
        refund_type: str,
        refund_amount: float,
        order_cancelled: bool = False,
    ) -> Dict[str, Any]:
        """Create the custom refund amount button (Step 2)"""
        first_name = requestor_name.get("first", "")
        last_name = requestor_name.get("last", "")

        try:
            button_text = (
                "✏️ Custom Refund Amount"
                if refund_type == "refund"
                else "✏️ Custom Store Credit Amount"
            )

            return {
                "type": "button",
                "text": {"type": "plain_text", "text": button_text},
                "action_id": "custom_refund_amount",
                "value": f"orderId={order_id}|refundAmount={refund_amount}|rawOrderNumber={order_number}|refundType={refund_type}|orderCancelled={order_cancelled}|first={first_name}|last={last_name}|email={requestor_email}",
            }
        except Exception:
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "✏️ Custom Amount"},
                "action_id": "custom_refund_amount",
                "value": f"orderId={order_id}|refundAmount={refund_amount}|rawOrderNumber={order_number}|first={first_name}|last={last_name}|email={requestor_email}",
            }

    def _create_no_refund_button(
        self,
        order_id: str,
        order_number: str,
        order_cancelled: bool = False,
        requestor_name: Dict[str, str] = {},
        requestor_email: str = "",
    ) -> Dict[str, Any]:
        """Create the no refund button (Step 2)"""
        first_name = requestor_name.get("first", "")
        last_name = requestor_name.get("last", "")

        try:
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "🚫 Do Not Provide Refund"},
                "style": "danger",
                "action_id": "no_refund",
                "value": f"rawOrderNumber={order_number}|orderId={order_id}|orderCancelled={order_cancelled}|first={first_name}|last={last_name}|email={requestor_email}",
                "confirm": {
                    "title": {"type": "plain_text", "text": "No Refund"},
                    "text": {
                        "type": "plain_text",
                        "text": "Proceed to next step without providing any refund?",
                    },
                    "confirm": {"type": "plain_text", "text": "Yes, no refund"},
                    "deny": {"type": "plain_text", "text": "Cancel"},
                },
            }
        except Exception:
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "🚫 No Refund"},
                "style": "danger",
                "action_id": "no_refund",
                "value": f"rawOrderNumber={order_number}|orderId={order_id}|first={first_name}|last={last_name}|email={requestor_email}",
            }

    def _create_edit_request_details_button(
        self,
        raw_order_number: str,
        requestor_name: Dict[str, str],
        requestor_email: str,
        refund_type: str,
        request_notes: str,
        current_time: str,
    ) -> Dict[str, Any]:
        """Create the edit request details button for email mismatch"""
        try:
            first_name = requestor_name.get("first", "")
            last_name = requestor_name.get("last", "")
            full_name = f"{first_name} {last_name}".strip()

            # Ensure order number has # prefix for consistency
            order_number = (
                raw_order_number
                if raw_order_number.startswith("#")
                else f"#{raw_order_number}"
            )

            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "✏️ Edit Request Details"},
                "style": "primary",
                "action_id": "edit_request_details",
                "value": f"orderName={order_number}|requestorName={full_name}|requestorEmail={requestor_email}|refundType={refund_type}|submittedAt={current_time}",
            }
        except Exception:
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "✏️ Edit Request Details"},
                "style": "primary",
                "action_id": "edit_request_details",
                "value": f"rawOrderNumber={raw_order_number}|requestorEmail={requestor_email}",
            }

    def _create_deny_email_mismatch_button(
        self,
        raw_order_number: str,
        requestor_name: Dict[str, str],
        requestor_email: str,
        refund_type: str,
        current_time: str,
    ) -> Dict[str, Any]:
        """Create the deny request button for email mismatch"""
        try:
            first_name = requestor_name.get("first", "")
            last_name = requestor_name.get("last", "")

            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "🚫 Deny Request"},
                "style": "danger",
                "action_id": "deny_refund_request_show_modal",
                "value": f"rawOrderNumber={raw_order_number}|refundType={refund_type}|requestorEmail={requestor_email}|first={first_name}|last={last_name}|requestSubmittedAt={current_time}",
            }
        except Exception:
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "🚫 Deny Request"},
                "style": "danger",
                "action_id": "deny_refund_request_show_modal",
                "value": f"rawOrderNumber={raw_order_number}|requestorEmail={requestor_email}",
            }

    # === MESSAGE CREATION FOR REFUND DECISION (Step 2) ===

    def create_refund_decision_message(
        self,
        order_data: Dict[str, Any],
        requestor_name: Dict[str, str],
        requestor_email: str,
        refund_type: str,
        sport_mention: str,
        sheet_link: str = "",
        order_cancelled: bool = False,
        slack_user_id: str = "Unknown User",
        original_timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create message for refund decision step (after cancel order or proceed without cancel)"""
        requestor_name.get("first", "")
        requestor_name.get("last", "")

        try:
            # Extract order information
            order = order_data.get("order", {})
            order_id = order.get("orderId", order.get("id", "unknown"))
            order_number = order.get("name", "unknown")

            # Extract refund calculation
            refund_calc = order_data.get("refund_calculation", {})
            refund_amount = refund_calc.get("refund_amount", 0)

            # Get original data if passed
            original_data = order_data.get("original_data", {})

            # Use preserved timing details
            if original_timestamp:
                current_time = original_timestamp
            else:
                current_time = format_date_and_time(datetime.now(timezone.utc))

            # Use preserved order created at
            if original_data.get("order_created_at"):
                order_created_time = original_data["order_created_at"]
            else:
                order_created_time = self._get_order_created_time(order)

            # Use preserved season start date
            if original_data.get("season_start_date"):
                season_start_date = original_data["season_start_date"]
            else:
                season_start_date = refund_calc.get("season_start_date", "Unknown")

            # Use preserved product/sport display
            if original_data.get("product_display"):
                product_display = original_data["product_display"]
                product_field_name = original_data.get(
                    "product_field_name", "Product Title"
                )
            else:
                # Fallback to generating product info
                product = order.get("product", {})
                product_id = product.get("productId") or product.get("id") or ""
                product_title = product.get("title", "Unknown Product")
                product_url = self.build_hyperlink(build_product_url(product_id), product_title) if product_id else "#"
                product_display = f"<{product_url}|{product_title}>"
                product_field_name = "Product Title"

            # Use preserved order number display (preserves links)
            if original_data.get("order_number_display"):
                order_number_display = original_data["order_number_display"]
            else:
                order_url = self.build_hyperlink(build_order_url(order_id), order_number)
                order_number_display = order_url

            # Use preserved pricing details
            if original_data.get("total_paid"):
                total_paid = float(original_data["total_paid"].replace(",", ""))
            else:
                total_paid = (
                    order.get("totalAmountPaid", 0) or order.get("total_price", 0) or 0
                )
                if isinstance(total_paid, str):
                    try:
                        total_paid = float(total_paid)
                    except (ValueError, TypeError):
                        total_paid = 0

            # Use preserved original cost
            original_cost = None
            if original_data.get("original_price"):
                try:
                    original_cost = float(
                        original_data["original_price"].replace(",", "")
                    )
                except (ValueError, TypeError):
                    pass
            elif refund_calc.get("original_cost"):
                original_cost = refund_calc.get("original_cost")

            # Build message text - start without header (we'll add status at the bottom)
            message_text = ""
            message_text += (
                f"*Request Type*: {self._get_request_type_text(refund_type)}\n\n"
            )
            # Extract customer data from order for profile hyperlink
            customer_data = None
            if order and "customer" in order:
                customer_data = order["customer"]
            message_text += self._get_requestor_line(
                requestor_name, requestor_email, customer_data
            )
            message_text += f"*Order Number*: {order_number_display}\n\n"
            message_text += f"*{product_field_name}:* {product_display}\n\n"
            message_text += f"*Request Submitted At*: {current_time}\n\n"
            message_text += f"*Order Created At:* {order_created_time}\n\n"
            message_text += f"*Season Start Date*: {season_start_date}\n\n"

            # Add Original Price field if different from Total Paid
            if original_cost is not None and abs(original_cost - total_paid) > 0.01:
                message_text += f"*Original Price:* ${original_cost:.2f}\n\n"

            message_text += f"*Total Paid:* ${total_paid:.2f}\n\n"

            # Add refund calculation details if available
            calc_message = refund_calc.get("message", "")
            if calc_message:
                message_text += f"{calc_message}\n\n"
            else:
                message_text += "\n"

            # Add inventory information if available
            inventory_text = ""  # Initialize to avoid UnboundLocalError
            if order_data.get("inventory_summary"):
                product_title = original_data.get("product_display", "Unknown Product")
                # Remove link formatting for inventory display
                if "|" in product_title:
                    product_title = product_title.split("|")[1].replace(">", "")
                inventory_text = self._build_inventory_text(
                    order_data, product_title, season_start_date
                )
            if inventory_text:
                message_text += f"{inventory_text}\n\n"

            message_text += self._get_sheet_link_line(sheet_link)

            # Add progress indicators showing order step completed, other steps pending
            if order_cancelled:
                updated_status = f"✅ *Order Canceled*, processed by <@{slack_user_id}>"
            else:
                updated_status = (
                    f"✅ *Order Not Canceled*, processed by <@{slack_user_id}>"
                )

            # Add the 3-step progress indicator system
            message_text += f"{updated_status}\n"
            message_text += "📋 Refund processing pending\n"
            message_text += "📋 Inventory restocking pending\n\n"

            # Create refund decision buttons (Step 2)
            action_buttons = [
                self._create_process_refund_button(
                    order_id,
                    order_number,
                    requestor_name,
                    requestor_email,
                    refund_type,
                    refund_amount,
                    order_cancelled,
                ),
                self._create_custom_refund_button(
                    order_id,
                    order_number,
                    requestor_name,
                    requestor_email,
                    refund_type,
                    refund_amount,
                    order_cancelled,
                ),
                self._create_no_refund_button(
                    order_id,
                    order_number,
                    order_cancelled,
                    requestor_name,
                    requestor_email,
                ),
            ]

            return {
                "text": message_text,
                "action_buttons": action_buttons,
                "slack_text": f"Order {'Canceled' if order_cancelled else 'Not Canceled'}",
            }

        except Exception as e:
            # Fallback message
            return {
                "text": f"⚠️ Error creating refund decision message: {str(e)}",
                "action_buttons": [],
                "slack_text": "Refund Decision Error",
            }

    def _build_inventory_text(
        self, order_data: Dict[str, Any], product_title: str, season_start_date: str
    ) -> str:
        """Build the inventory status text for Slack messages"""
        try:
            inventory_summary = order_data.get("inventory_summary", {})

            if not inventory_summary.get("success"):
                return "📦 *Inventory information unavailable*"

            inventory_list = inventory_summary.get("inventory_list", {})
            inventory_order = ["veteran", "early", "open", "waitlist"]

            # Safely get product info
            order = order_data.get("order", {})
            product = order.get("product", {})
            product.get("productId", "")

            # Remove the duplicate season start date line as requested - keep only "Current Inventory:"
            text = "*Current Inventory:*\n"

            for key in inventory_order:
                if (
                    key in inventory_list
                    and inventory_list[key].get("inventory") is not None
                ):
                    variant_info = inventory_list[key]
                    inventory_count = variant_info.get("inventory", 0)
                    variant_name = variant_info.get("name", key.title())

                    if isinstance(inventory_count, (int, float)):
                        inventory_text = f"{int(inventory_count)} spots available"
                    else:
                        inventory_text = "Error fetching current inventory"

                    text += f"• *{variant_name}*: {inventory_text}\n"

            return text.rstrip()

        except Exception as e:
            return f"📦 *Error fetching inventory information: {str(e)}*"

    def build_success_message(
        self,
        order_data: Dict[str, Any],
        refund_calculation: Dict[str, Any],
        requestor_info: Dict[str, Any],
        sheet_link: str,
        request_initiated_at: Optional[str] = None,
        slack_channel_name: Optional[str] = None,
        mention_strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a successful refund request message with action buttons"""
        try:
            order = order_data.get("order", {})
            product = order.get("product", {})

            # Common elements - use safe access
            if request_initiated_at:
                current_time = request_initiated_at
            else:
                current_time = format_date_and_time(datetime.now(timezone.utc))
            order_created_time = self._get_order_created_time(order)

            # Safely get order ID and name with fallbacks
            order_id = order.get("orderId") or order.get("id") or "unknown"
            order_number = (
                order.get("orderNumber")
                or order.get("orderName")
                or order.get("name")
                or "unknown"
            )

            order_url = self.build_hyperlink(build_order_url(order_id), order_number)

            # Safely get product info - try multiple locations
            product_id = product.get("productId") or product.get("id") or ""
            product_title = product.get("title", "Unknown Product")

            # If product title is still unknown, try extracting from line_items (Shopify structure)
            if product_title == "Unknown Product" and order.get("line_items"):
                line_items = order.get("line_items", [])
                if line_items and isinstance(line_items, list) and len(line_items) > 0:
                    first_item = line_items[0]
                    product_title = first_item.get("title", "Unknown Product")
                    # Also try to get product_id from line_items if not found above
                    if not product_id:
                        product_data = first_item.get("product", {})
                        product_id = product_data.get("id", "")

            product_url = self.build_hyperlink(build_product_url(product_id), product_title) if product_id else "#"
            sport_mention = self.get_group_mention(product_title)

            # Extract data
            requestor_name = requestor_info.get("name", {})
            requestor_email = requestor_info.get("email", "unknown@example.com")
            refund_type = requestor_info.get("refund_type", "refund")
            request_notes = requestor_info.get("notes", "")
            customer_data = requestor_info.get("customer_data")

            season_start_date = refund_calculation.get("season_start_date", "Unknown")
            refund_amount = refund_calculation.get("refund_amount", 0.0)
            refund_text = refund_calculation.get("message", "")

            # Get both original cost (early bird variant price) and total paid amounts
            original_cost = refund_calculation.get("original_cost")
            total_paid = (
                order.get("totalAmountPaid", 0) or order.get("total_price", 0) or 0
            )
            if isinstance(total_paid, str):
                try:
                    total_paid = float(total_paid)
                except (ValueError, TypeError):
                    total_paid = 0

            # Header
            header_text = "📌 *New Refund Request!*\n\n"

            # Build message text
            message_text = f"{header_text}"
            message_text += (
                f"*Request Type*: {self._get_request_type_text(refund_type)}\n\n"
            )
            message_text += self._get_requestor_line(
                requestor_name, requestor_email, customer_data
            )
            message_text += f"*Request Submitted At*: {current_time}\n\n"
            message_text += f"*Order Number*: {order_url}\n\n"
            message_text += f"*Order Created At:* {order_created_time}\n\n"
            message_text += f"*Product Title:* <{product_url}|{product_title}>\n\n"
            message_text += f"*Season Start Date*: {season_start_date}\n\n"
            # Add Original Price field if different from Total Paid
            if original_cost is not None and abs(original_cost - total_paid) > 0.01:
                message_text += f"*Original Price:* ${original_cost:.2f}\n\n"
            message_text += f"*Total Paid:* ${total_paid:.2f}\n\n"
            # message_text += f"*Estimated Refund Due:* ${refund_amount:.2f}\n"
            if refund_text:
                message_text += f"{refund_text}\n\n"
            else:
                message_text += "\n"
            message_text += self._get_optional_request_notes(request_notes)

            # Add progress indicators (3-step system: order canceled/not → refund provided/not → restocked/not)
            message_text += "📋 Order cancellation pending\n"
            message_text += "📋 Refund processing pending\n"
            message_text += "📋 Inventory restocking pending\n\n"

            # Add inventory information if available
            if order_data.get("inventory_summary"):
                inventory_text = self._build_inventory_text(
                    order_data, product_title, season_start_date
                )
                message_text += f"{inventory_text}\n\n"

            # Add Google Sheets link
            message_text += self._get_sheet_link_line(sheet_link)
            message_text += f"*Attn*: {sport_mention}"

            # Create initial decision buttons (Step 1: Cancel Order, Proceed, or Deny)
            action_buttons = [
                self._create_cancel_order_button(
                    order_id,
                    order_number,
                    requestor_name,
                    requestor_email,
                    refund_type,
                    refund_amount,
                    current_time,
                ),
                self._create_proceed_without_cancel_button(
                    order_id,
                    order_number,
                    requestor_name,
                    requestor_email,
                    refund_type,
                    refund_amount,
                    current_time,
                ),
                self._create_deny_request_button(
                    order_id,
                    order_number,
                    requestor_name,
                    requestor_email,
                    refund_type,
                    refund_amount,
                    current_time,
                ),
            ]

            return {
                "text": message_text,
                "action_buttons": action_buttons,
                "slack_text": header_text,
            }

        except Exception as e:
            # If all else fails, provide a very basic success message
            requestor_email = "unknown@example.com"
            try:
                requestor_email = requestor_info.get("email", "unknown@example.com")
            except:  # noqa: E722
                pass

            error_text = f"❌ *Error building success message*\n\nError: {str(e)}\n\nRequestor: {requestor_email}\n\nPlease check the order data manually."
            return {
                "text": error_text,
                "action_buttons": [],
                "slack_text": "❌ Error building message",
            }

    def build_fallback_message(
        self,
        order_data: Dict[str, Any],
        requestor_info: Dict[str, Any],
        sheet_link: str,
        error_message: str = "",
        refund_calculation: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a fallback message when season info is missing"""
        try:
            order = order_data.get("order", {})
            product = order.get("product", {})

            # Common elements - use safe access
            current_time = format_date_and_time(datetime.now(timezone.utc))
            order_created_time = self._get_order_created_time(order)

            # Safely get order ID and name with fallbacks
            order_id = order.get("orderId") or order.get("id") or "unknown"
            order_number = order.get("orderName") or order.get("name") or "unknown"

            order_url = self.build_hyperlink(build_order_url(order_id), order_number)

            # Safely get product title
            product_title = product.get("title", "Unknown Product")
            sport_mention = self.get_group_mention(product_title)

            # Extract data
            requestor_name = requestor_info.get("name", {})
            requestor_email = requestor_info.get("email", "unknown@example.com")
            refund_type = requestor_info.get("refund_type", "refund")
            request_notes = requestor_info.get("notes", "")

            # Calculate fallback refund amount (90% for refund, 95% for credit)
            total_paid = (
                order.get("totalAmountPaid", 0) or order.get("total_price", 0) or 0
            )
            if isinstance(total_paid, str):
                try:
                    total_paid = float(total_paid)
                except (ValueError, TypeError):
                    total_paid = 0

            # Try to get original cost from early bird variant
            original_cost = None
            try:
                variants = product.get("variants", [])
                for variant in variants:
                    variant_name = variant.get(
                        "variantName", variant.get("title", "")
                    ).lower()
                    if "trans" in variant_name:
                        variant_price = variant.get("price")
                        if variant_price:
                            original_cost = float(variant_price)
                            break
            except (ValueError, TypeError):
                pass

            # Use refund calculation if available, otherwise calculate fallback
            if refund_calculation and refund_calculation.get("missing_season_info"):
                fallback_refund_amount = refund_calculation.get("refund_amount", 0)
                calculation_message = refund_calculation.get("message", "")
            else:
                fallback_refund_amount = (
                    total_paid * 0.9 if refund_type == "refund" else total_paid * 0.95
                )
                calculation_message = ""

            # Header
            header_text = "📌 *New Refund Request!*\n\n"

            # Build message text
            message_text = f"{header_text}"
            message_text += "⚠️ *Order Found in Shopify but Missing Season Info (or Product Is Not a Regular Season)*\n\n"
            message_text += (
                f"*Request Type*: {self._get_request_type_text(refund_type)}\n\n"
            )
            customer_data = requestor_info.get("customer_data")
            message_text += self._get_requestor_line(
                requestor_name, requestor_email, customer_data
            )
            message_text += f"*Request Submitted At*: {current_time}\n\n"
            message_text += f"*Order Number Provided*: {order_url}\n\n"
            message_text += f"*Order Created At:* {order_created_time}\n\n"
            # Get product URL
            product_id = product.get("productId") or product.get("id") or ""
            product_url = self.build_hyperlink(build_product_url(product_id), product_title) if product_id else "#"
            message_text += f"*Product Title*: <{product_url}|{product_title}>\n\n"
            # Add Original Price field if different from Total Paid
            if original_cost is not None and abs(original_cost - total_paid) > 0.01:
                message_text += f"*Original Price:* ${original_cost:.2f}\n\n"
            message_text += f"*Total Paid:* ${total_paid:.2f}\n\n"

            # Show refund calculation or generic warning
            if calculation_message:
                # message_text += f"*Estimated Refund Due:* ${fallback_refund_amount:.2f}\n"
                message_text += f"{calculation_message}\n\n"
            else:
                message_text += "⚠️ *Could not parse 'Season Dates' from this order's description (in order to calculate a refund amount).*\n\n"
                message_text += "Please verify the product and either contact the requestor or process anyway.\n\n"
            message_text += self._get_optional_request_notes(request_notes)
            message_text += self._get_sheet_link_line(sheet_link)
            message_text += f"*Attn*: {sport_mention}"

            # Create initial decision buttons (Step 1: Cancel Order, Proceed, or Deny)
            action_buttons = [
                self._create_cancel_order_button(
                    order_id,
                    order_number,
                    requestor_name,
                    requestor_email,
                    refund_type,
                    fallback_refund_amount,
                    current_time,
                ),
                self._create_proceed_without_cancel_button(
                    order_id,
                    order_number,
                    requestor_name,
                    requestor_email,
                    refund_type,
                    fallback_refund_amount,
                    current_time,
                ),
                self._create_deny_request_button(
                    order_id,
                    order_number,
                    requestor_name,
                    requestor_email,
                    refund_type,
                    fallback_refund_amount,
                    current_time,
                ),
            ]

            return {
                "text": message_text,
                "action_buttons": action_buttons,
                "slack_text": "⚠️ *Refund Request Missing Season Info*",
            }

        except Exception as e:
            # If all else fails, provide a very basic fallback message
            requestor_email = "unknown@example.com"
            try:
                requestor_email = requestor_info.get("email", "unknown@example.com")
            except:  # noqa: E722
                pass

            error_text = f"❌ *Error building fallback message*\n\nError: {str(e)}\n\nRequestor: {requestor_email}\n\nPlease check the order data manually."
            return {
                "text": error_text,
                "action_buttons": [],
                "slack_text": "❌ Error building message",
            }

    def build_error_message(
        self,
        error_type: str,
        requestor_info: Dict[str, Any],
        sheet_link: str,
        raw_order_number: str = "",
        order_customer_email: str = "",
        order_data: Optional[Dict[str, Any]] = None,
        customer_orders_url: Optional[str] = None,
        existing_refunds_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build an error message for various error scenarios"""
        try:
            # Validate error type
            if error_type not in [
                "order_not_found",
                "email_mismatch",
                "duplicate_refund",
                "unknown",
            ]:
                error_type = "unknown"

            current_time = format_date_and_time(datetime.now(timezone.utc))

            # Safely extract requestor info
            requestor_name = requestor_info.get("name", {})
            requestor_email = requestor_info.get("email", "unknown@example.com")
            refund_type = requestor_info.get("refund_type", "refund")
            request_notes = requestor_info.get("notes", "")

            # Build unified error message
            if error_type == "order_not_found":
                error_text = (
                    "❌ *Error with Refund Request - Order Not Found in Shopify*\n\n"
                )
                error_text += (
                    f"*Request Type*: {self._get_request_type_text(refund_type)}\n\n"
                )
                error_text += f"*Request Submitted At*: {current_time}\n\n"
                customer_data = requestor_info.get("customer_data")
                error_text += self._get_requestor_line(
                    requestor_name, requestor_email, customer_data
                )
                error_text += f"🔎 *Order Number Provided:* {raw_order_number or 'N/A'} - this order cannot be found in Shopify\n\n"
                error_text += self._get_optional_request_notes(request_notes)
                error_text += "📩 *The requestor has been emailed to please provide correct order info. No action needed at this time.*\n"
                error_text += self._get_sheet_link_line(sheet_link)

            elif error_type == "email_mismatch":
                # This is now handled by build_email_mismatch_message instead
                # Return early to use the new method with the provided order_data
                return self.build_email_mismatch_message(
                    requestor_info={
                        "name": requestor_name,
                        "email": requestor_email,
                        "refund_type": refund_type,
                        "notes": request_notes,
                    },
                    raw_order_number=raw_order_number,
                    order_customer_email=order_customer_email,
                    sheet_link=sheet_link,
                    order_data=order_data or {},
                    customer_orders_url=customer_orders_url,
                )

            elif error_type == "duplicate_refund":
                return self.build_duplicate_refund_message(
                    requestor_info=requestor_info,
                    raw_order_number=raw_order_number,
                    sheet_link=sheet_link,
                    order_data=order_data,
                    existing_refunds_data=existing_refunds_data,
                )

            else:
                error_text = "❌ *Error with Refund Request*\n\n"
                error_text += (
                    f"*Request Type*: {self._get_request_type_text(refund_type)}\n\n"
                )
                error_text += f"*Request Submitted At*: {current_time}\n\n"
                customer_data = requestor_info.get("customer_data")
                error_text += self._get_requestor_line(
                    requestor_name, requestor_email, customer_data
                )
                error_text += self._get_optional_request_notes(request_notes)
                error_text += self._get_sheet_link_line(sheet_link)

            slack_text = "❌ *Refund Request Submitted with Error*"

            return {"text": error_text, "action_buttons": [], "slack_text": slack_text}

        except Exception as e:
            # Ultra-safe fallback
            email = "unknown@example.com"
            try:
                if isinstance(requestor_info, dict):
                    email = requestor_info.get("email", "unknown@example.com")
            except:  # noqa: E722
                pass

            error_text = f"❌ *Error building error message*\n\nError: {str(e)}\n\nRequestor: {email}"
            return {
                "text": error_text,
                "action_buttons": [],
                "slack_text": "❌ Error building message",
            }

    def build_email_mismatch_message(
        self,
        requestor_info: Dict[str, Any],
        raw_order_number: str,
        order_customer_email: str,
        sheet_link: str,
        order_data: Dict[str, Any],
        customer_orders_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build Slack message for email mismatch scenario with action buttons

        Args:
            requestor_info: Requestor details (name, email, refund_type, notes)
            raw_order_number: Order number from the request
            order_customer_email: Actual email associated with the order
            sheet_link: Link to the Google Sheet
            order_data: Optional order data for sport mention

        Returns:
            Dict with message text, action buttons, and slack text
        """
        try:
            requestor_name = requestor_info.get("name", {})
            requestor_email = requestor_info.get("email", "")
            refund_type = requestor_info.get("refund_type", "refund")
            request_notes = requestor_info.get("notes", "")

            current_time = format_date_and_time(datetime.now(timezone.utc))

            # Get order URL for linking
            order_id = order_data.get("order", {}).get("id", "")
            order_number = order_data.get("order", {}).get("name", raw_order_number)
            order_url = self.build_hyperlink(
                build_order_url(order_id),
                order_number,
            )

            # Build main message with enhanced content
            message_text = "⚠️ *Email Mismatch - Action Required*\n\n"
            message_text += (
                f"*Request Type*: {self._get_request_type_text(refund_type)}\n\n"
            )
            message_text += f"*Request Submitted At*: {current_time}\n\n"

            # Enhanced requestor line with customer profile hyperlink and orders link
            requestor_full_name = f"{requestor_name.get('first', '')} {requestor_name.get('last', '')}".strip()
            customer_data = requestor_info.get("customer_data")

            # Build requestor line with customer profile hyperlink if available
            if requestor_full_name and customer_data and customer_data.get("id"):
                customer_url = self.build_hyperlink(build_customer_url(customer_data["id"]), requestor_full_name)
                requestor_line = f"📧 *Requested by:* {customer_url} (<mailto:{requestor_email}|{requestor_email}>)"
            else:
                requestor_line = f"📧 *Requested by:* {requestor_full_name} (<mailto:{requestor_email}|{requestor_email}>)"

            # Use provided customer orders URL or show no customer found message
            if customer_orders_url:
                orders_link_text = f"(<{customer_orders_url}|Click here to view orders associated with {requestor_email}>)"
            else:
                # No customer found with that email in Shopify
                orders_link_text = f"(No Shopify customer found associated with the email {requestor_email})"

            message_text += f"{requestor_line} \n{orders_link_text}\n\n"

            message_text += f"*Email Associated with Order:* <mailto:{order_customer_email}|{order_customer_email}>\n\n"

            # Enhanced order number with hyperlink
            if order_data and "order" in order_data:
                # Extract order ID and create proper Shopify URL
                order = order_data["order"]
                order_id = order.get("id", "")
                if order_id:
                    # Create the order URL using the helper method
                    formatted_order_number = (
                        raw_order_number
                        if raw_order_number.startswith("#")
                        else f"#{raw_order_number}"
                    )
                    order_url = self.build_hyperlink(build_order_url(order_id), formatted_order_number)
                    message_text += f"*Order Number:* {order_url}\n\n"
                else:
                    message_text += f"*Order Number:* {raw_order_number}\n\n"
            else:
                message_text += f"*Order Number:* {raw_order_number}\n\n"

            message_text += self._get_optional_request_notes(request_notes)
            message_text += (
                "⚠️ *The email provided does not match the order's customer email.*\n"
            )
            message_text += "Please either view orders above to edit with the correct details, reach out to the requestor to confirm, or click Deny Request to notify the player their request has been denied due to mismatching details.\n\n"
            message_text += "*Please choose an action:*\n"
            message_text += "• *Edit Request Details*: Update the order number or email and re-validate\n"
            message_text += (
                "• *Deny Request*: Send custom denial email to requestor\n\n"
            )
            message_text += self._get_sheet_link_line(sheet_link)

            # Add sport mention if available
            sport_mention = ""
            if order_data and "order" in order_data:
                order = order_data["order"]
                if "line_items" in order and order["line_items"]:
                    product_title = order["line_items"][0].get("title", "")
                    sport_mention = self.get_group_mention(product_title)
                    if sport_mention:
                        message_text += f"*Attn*: {sport_mention}"

            # Create action buttons
            action_buttons = [
                self._create_edit_request_details_button(
                    raw_order_number=raw_order_number,
                    requestor_name=requestor_name,
                    requestor_email=requestor_email,
                    refund_type=refund_type,
                    request_notes=request_notes,
                    current_time=current_time,
                ),
                self._create_deny_email_mismatch_button(
                    raw_order_number=raw_order_number,
                    requestor_name=requestor_name,
                    requestor_email=requestor_email,
                    refund_type=refund_type,
                    current_time=current_time,
                ),
            ]

            return {
                "text": message_text,
                "action_buttons": action_buttons,
                "slack_text": "⚠️ *Refunds - Email Mismatch - Action Required*",
            }

        except Exception as e:
            logger.error(f"Error building email mismatch message: {str(e)}")
            return {
                "text": f"❌ *Error building email mismatch message*\n\nError: {str(e)}\n\nRequestor: {requestor_info.get('email', 'unknown')}",
                "action_buttons": [],
                "slack_text": "❌ Error building email mismatch message",
            }

    def build_duplicate_refund_message(
        self,
        requestor_info: Dict[str, Any],
        raw_order_number: str,
        sheet_link: str,
        order_data: Optional[Dict[str, Any]] = None,
        existing_refunds_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a message for duplicate refund requests with options to update or deny"""
        try:
            current_time = format_date_and_time(datetime.now(timezone.utc))

            # Safely extract requestor info
            requestor_name = requestor_info.get("name", {})
            requestor_email = requestor_info.get("email", "unknown@example.com")
            refund_type = requestor_info.get("refund_type", "refund")
            request_notes = requestor_info.get("notes", "")

            # Extract order info
            order_number = raw_order_number
            order_admin_url = ""

            if order_data and order_data.get("order"):
                order = order_data["order"]
                order_id = order["id"]
                order_number = order.get("name", raw_order_number)
                # Create Shopify admin URL
                order_admin_url = f"https://admin.shopify.com/store/09fe59-3/orders/{order_id.split('/')[-1]}"

            # Extract existing refunds info
            total_refunds = 0
            total_refunded_amount = 0.0
            refunds_list = []

            if existing_refunds_data:
                total_refunds = existing_refunds_data.get("total_refunds", 0)
                refunds = existing_refunds_data.get("refunds", [])

                for refund in refunds:
                    refund_amount = float(refund.get("total_refunded", 0))
                    total_refunded_amount += refund_amount
                    refund_date = refund.get("created_at", "Unknown")

                    # Use status_display if available, otherwise format manually
                    if refund.get("status_display"):
                        amount_text = refund["status_display"]
                    else:
                        amount_text = f"${refund_amount:.2f}"

                    # Format date as M/d/yy
                    formatted_date = refund_date
                    if refund_date != "Unknown":
                        try:
                            # Parse ISO date and format as M/d/yy
                            parsed_date = datetime.fromisoformat(
                                refund_date.replace("Z", "+00:00")
                            )
                            formatted_date = parsed_date.strftime("%-m/%-d/%y")
                        except Exception:
                            # Fallback to original format if parsing fails
                            formatted_date = refund_date[:10]

                    refunds_list.append(f"• {amount_text}, issued on {formatted_date}")

            # Build message text
            message_text = "❌ *Refund request – Refund Already Processed*\n\n"
            message_text += (
                f"*Request Type*: {self._get_request_type_text(refund_type)}\n\n"
            )
            message_text += f"*Request Submitted At*: {current_time}\n\n"
            customer_data = requestor_info.get("customer_data")
            message_text += self._get_requestor_line(
                requestor_name, requestor_email, customer_data
            )

            if order_admin_url:
                message_text += f"*Order Number*: <{order_admin_url}|{order_number}>\n\n"
            else:
                message_text += f"*Order Number*: {order_number}\n\n"

            message_text += (
                f"🚨 *This order already has {total_refunds} refund(s) processed:*\n"
            )
            if refunds_list:
                message_text += "\n".join(refunds_list)
                message_text += (
                    f"\n\n💰 *Total Already Refunded*: ${total_refunded_amount:.2f}\n\n"
                )
            else:
                message_text += f"• {total_refunds} refund(s) found\n\n"

            message_text += self._get_optional_request_notes(request_notes)
            message_text += self._get_sheet_link_line(sheet_link)

            # Create action buttons for update details or deny refund
            action_buttons = [
                self._create_update_refund_details_button(
                    order_number=order_number,
                    requestor_name=requestor_name,
                    requestor_email=requestor_email,
                    refund_type=refund_type,
                    current_time=current_time,
                ),
                self._create_deny_duplicate_refund_button(
                    order_number=order_number,
                    requestor_name=requestor_name,
                    requestor_email=requestor_email,
                    refund_type=refund_type,
                    current_time=current_time,
                ),
            ]

            return {
                "text": message_text,
                "action_buttons": action_buttons,
                "slack_text": "❌ ERROR: Refund Already Processed (Update Details/Deny)",
            }

        except Exception as e:
            logger.error(f"Error building duplicate refund message: {str(e)}")
            return {
                "text": f"❌ *Error building duplicate refund message*\n\nError: {str(e)}\n\nOrder: {raw_order_number}\nRequestor: {requestor_info.get('email', 'unknown')}",
                "action_buttons": [],
                "slack_text": "❌ Error building duplicate refund message",
            }

    def _create_update_refund_details_button(
        self,
        order_number: str,
        requestor_name: Union[str, Dict[str, str]],
        requestor_email: str,
        refund_type: str,
        current_time: str,
    ) -> Dict[str, Any]:
        """Create an 'Update Refund Details' button for duplicate refund scenarios"""
        try:
            # Ensure order_number has # prefix
            if not order_number.startswith("#"):
                order_number = f"#{order_number}"

            # Format requestor name
            if isinstance(requestor_name, dict):
                first_name = requestor_name.get("first", "")
                last_name = requestor_name.get("last", "")
                full_name = f"{first_name} {last_name}".strip()
            else:
                full_name = str(requestor_name)

            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "🔄 Update Request Details"},
                "style": "primary",
                "action_id": "edit_request_details",
                "value": f"orderName={order_number}|requestorName={full_name}|requestorEmail={requestor_email}|refundType={refund_type}|submittedAt={current_time}",
            }

        except Exception as e:
            logger.error(f"Error creating update refund details button: {str(e)}")
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "🔄 Update Details"},
                "action_id": "update_duplicate_refund_details",
                "value": "error=button_creation_failed",
            }

    def _create_deny_duplicate_refund_button(
        self,
        order_number: str,
        requestor_name: Union[str, Dict[str, str]],
        requestor_email: str,
        refund_type: str,
        current_time: str,
    ) -> Dict[str, Any]:
        """Create a 'Deny Duplicate Refund' button for duplicate refund scenarios"""
        try:
            # Ensure order_number has # prefix
            if not order_number.startswith("#"):
                order_number = f"#{order_number}"

            # Format requestor name
            if isinstance(requestor_name, dict):
                first_name = requestor_name.get("first", "")
                last_name = requestor_name.get("last", "")
                full_name = f"{first_name} {last_name}".strip()
            else:
                full_name = str(requestor_name)

            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "❌ Deny Refund Request"},
                "style": "danger",
                "action_id": "deny_duplicate_refund_request",
                "value": f"orderName={order_number}|requestorName={full_name}|requestorEmail={requestor_email}|refundType={refund_type}|submittedAt={current_time}",
                "confirm": {
                    "title": {"type": "plain_text", "text": "Deny Refund Request?"},
                    "text": {
                        "type": "plain_text",
                        "text": f"This will deny the refund request for {order_number}. The requestor will be notified. Are you sure?",
                    },
                    "confirm": {"type": "plain_text", "text": "Yes, deny request"},
                    "deny": {"type": "plain_text", "text": "Cancel"},
                },
            }

        except Exception as e:
            logger.error(f"Error creating deny duplicate refund button: {str(e)}")
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "❌ Deny Request"},
                "style": "danger",
                "action_id": "deny_duplicate_refund_request",
                "value": "error=button_creation_failed",
            }
