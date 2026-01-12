"""
Slack message building utilities.
Extracted from the main SlackService to improve modularity.
"""

import hashlib
import time
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone
import logging
from shared.date_utils import format_date_and_time, parse_shopify_datetime
# Add backend to path early
import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Lazy import Shopify URL builders to avoid circular dependencies
def _get_shopify_url_builders():
    """Lazy import of Shopify URL builders to avoid circular dependencies."""
    from modules.integrations.shopify.builders.shopify_url_builders import (
        build_customer_url,
        build_order_url,
        build_product_url
    )
    return build_customer_url, build_order_url, build_product_url
from config_old_deprecated.slack import SlackGroup
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
                    build_customer_url, _, _ = _get_shopify_url_builders()
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

    # === REFUND MESSAGE METHODS ===
    
    def _get_order_created_time(self, order: Dict[str, Any]) -> str:
        """Extract and format order creation time from order data"""
        try:
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

            return "Unknown"

        except Exception:
            return "Unknown"

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
        """Create blocks for refund decision step (after cancel order or proceed without cancel)"""
        try:
            order = order_data.get("order", {})
            order_id = order.get("orderId", order.get("id", "unknown"))
            order_number = order.get("name", "unknown")

            refund_calc = order_data.get("refund_calculation", {})
            refund_amount = refund_calc.get("refund_amount", 0)

            original_data = order_data.get("original_data", {})

            if original_timestamp:
                current_time = original_timestamp
            else:
                current_time = format_date_and_time(datetime.now(timezone.utc))

            if original_data.get("order_created_at"):
                order_created_time = original_data["order_created_at"]
            else:
                order_created_time = self._get_order_created_time(order)

            if original_data.get("season_start_date"):
                season_start_date = original_data["season_start_date"]
            else:
                season_start_date = refund_calc.get("season_start_date", "Unknown")

            if original_data.get("product_display"):
                product_display = original_data["product_display"]
                product_field_name = original_data.get(
                    "product_field_name", "Product Title"
                )
            else:
                product = order.get("product", {})
                product_id = product.get("productId") or product.get("id") or ""
                product_title = product.get("title", "Unknown Product")
                _, _, build_product_url = _get_shopify_url_builders()
                product_url = self.build_hyperlink(build_product_url(product_id), product_title) if product_id else "#"
                product_display = f"<{product_url}|{product_title}>"
                product_field_name = "Product Title"

            if original_data.get("order_number_display"):
                order_number_display = original_data["order_number_display"]
            else:
                _, build_order_url, _ = _get_shopify_url_builders()
                order_url = self.build_hyperlink(build_order_url(order_id), order_number)
                order_number_display = order_url

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

            message_text = ""
            message_text += (
                f"*Request Type*: {self._get_request_type_text(refund_type)}\n\n"
            )
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

            if original_cost is not None and abs(original_cost - total_paid) > 0.01:
                message_text += f"*Original Price:* ${original_cost:.2f}\n\n"

            message_text += f"*Total Paid:* ${total_paid:.2f}\n\n"

            calc_message = refund_calc.get("message", "")
            if calc_message:
                message_text += f"{calc_message}\n\n"
            else:
                message_text += "\n"

            inventory_text = ""
            if order_data.get("inventory_summary"):
                product_title = original_data.get("product_display", "Unknown Product")
                if "|" in product_title:
                    product_title = product_title.split("|")[1].replace(">", "")
                inventory_text = self._build_inventory_text(
                    order_data, product_title, season_start_date
                )
            if inventory_text:
                message_text += f"{inventory_text}\n\n"

            message_text += self._get_sheet_link_line(sheet_link)

            if order_cancelled:
                updated_status = f"✅ *Order Canceled*, processed by <@{slack_user_id}>"
            else:
                updated_status = (
                    f"✅ *Order Not Canceled*, processed by <@{slack_user_id}>"
                )

            message_text += f"{updated_status}\n"
            message_text += "📋 Refund processing pending\n"
            message_text += "📋 Inventory restocking pending\n\n"

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

            blocks = [
                self.build_section_block(message_text)
            ]

            if action_buttons:
                blocks.append({
                    "type": "actions",
                    "elements": action_buttons
                })

            return {"blocks": blocks}

        except Exception as e:
            error_block = self.build_section_block(
                f"⚠️ Error creating refund decision message: {str(e)}"
            )
            return {"blocks": [error_block]}

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

            order = order_data.get("order", {})
            product = order.get("product", {})
            product.get("productId", "")

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
            if not order_number.startswith("#"):
                order_number = f"#{order_number}"

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
            if not order_number.startswith("#"):
                order_number = f"#{order_number}"

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
                "action_id": "deny_duplicate_refund_request",
                "value": "error=button_creation_failed",
            }


class SlackCacheManager:
    """
    Utility class for managing Slack message deduplication cache.
    Handles cache operations, expiration, and cleanup.
    """
    
    def __init__(self, cache_expiry_seconds: int = 300):
        """
        Initialize the cache manager.
        
        Args:
            cache_expiry_seconds: How long to keep cache entries (default: 5 minutes)
        """
        self._cache = {}
        self._cache_expiry_seconds = cache_expiry_seconds
    
    def generate_message_hash(self, order_data: Dict[str, Any], requestor_info: Dict[str, Any]) -> str:
        """Generate a unique hash for deduplication based on order and requestor info."""
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
            return hashlib.md5(dedup_string.encode()).hexdigest()

        except Exception as e:
            logger.warning(f"Failed to generate message hash: {e}")
            return str(time.time())  # Fallback to timestamp
    
    def is_duplicate_message(self, message_hash: str) -> bool:
        """Check if this message has already been sent recently."""
        try:
            self._clean_expired_cache()
            
            if message_hash in self._cache:
                logger.info(f"Duplicate message detected: {message_hash}")
                return True
            
            # Add to cache
            self._cache[message_hash] = time.time()
            return False

        except Exception as e:
            logger.warning(f"Failed to check duplicate message: {e}")
            return False
    
    def _clean_expired_cache(self):
        """Remove expired entries from the cache."""
        try:
            current_time = time.time()
            expired_keys = [
                key
                for key, timestamp in self._cache.items()
                if current_time - timestamp > self._cache_expiry_seconds
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.info(f"Cleaned {len(expired_keys)} expired cache entries")

        except Exception as e:
            logger.warning(f"Failed to clean cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        return {
            "total_entries": len(self._cache),
            "cache_expiry_seconds": self._cache_expiry_seconds,
            "oldest_entry": min(self._cache.values()) if self._cache else None,
            "newest_entry": max(self._cache.values()) if self._cache else None
        }


class SlackMetadataBuilder:
    """
    Utility class for building consistent Slack message metadata.
    Handles metadata creation for different message types.
    
    Note: This class uses Pydantic models from models.slack which may need
    to be updated if you're not using those models in your workflow.
    """
    
    def build_refund_request_metadata(
        self,
        refund_request: Any,  # Type: Slack.RefundNotification
        order_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build metadata for refund request messages.
        
        Args:
            refund_request: Slack.RefundNotification Pydantic model instance
            order_data: Optional order data dict
        
        Returns:
            Dict with metadata fields
        """
        try:
            from models.slack import SlackMessageType
            
            metadata = {
                "order_number": refund_request.order_number,
                "requestor_email": refund_request.requestor_email,
                "refund_type": refund_request.refund_type.value,
                "message_type": SlackMessageType.REFUND_REQUEST.value,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            if order_data:
                order = order_data.get("order", {})
                metadata.update({
                    "order_id": order.get("id"),
                    "order_total": order.get("totalPrice"),
                    "order_status": order.get("fulfillmentStatus")
                })
            
            return metadata
        except ImportError:
            logger.warning("models.slack not available, returning basic metadata")
            return {
                "order_number": str(refund_request.order_number if hasattr(refund_request, 'order_number') else 'unknown'),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
    
    def build_confirmation_metadata(self, confirmation: Any) -> Dict[str, Any]:
        """
        Build metadata for refund confirmation messages.
        
        Args:
            confirmation: Slack.RefundConfirmation Pydantic model instance
        
        Returns:
            Dict with metadata fields
        """
        try:
            from models.slack import SlackMessageType
            
            return {
                "order_number": confirmation.order_number,
                "refund_amount": str(confirmation.refund_amount),
                "processed_by": confirmation.processed_by,
                "message_type": SlackMessageType.REFUND_CONFIRMATION.value,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "shopify_refund_id": confirmation.shopify_refund_id
            }
        except ImportError:
            logger.warning("models.slack not available, returning basic metadata")
            return {
                "order_number": str(confirmation.order_number if hasattr(confirmation, 'order_number') else 'unknown'),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
    
    def build_denial_metadata(self, denial: Any) -> Dict[str, Any]:
        """
        Build metadata for refund denial messages.
        
        Args:
            denial: Slack.RefundDenial Pydantic model instance
        
        Returns:
            Dict with metadata fields
        """
        try:
            from models.slack import SlackMessageType
            
            return {
                "order_number": denial.order_number,
                "denial_reason": denial.denial_reason,
                "denied_by": denial.denied_by,
                "message_type": SlackMessageType.REFUND_DENIAL.value,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        except ImportError:
            logger.warning("models.slack not available, returning basic metadata")
            return {
                "order_number": str(denial.order_number if hasattr(denial, 'order_number') else 'unknown'),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
    
    def build_order_update_metadata(self, update: Any) -> Dict[str, Any]:
        """
        Build metadata for order update messages.
        
        Args:
            update: Slack.OrderUpdate Pydantic model instance
        
        Returns:
            Dict with metadata fields
        """
        try:
            from models.slack import SlackMessageType
            
            return {
                "order_number": update.order_number,
                "update_type": update.update_type,
                "updated_by": update.updated_by,
                "message_type": SlackMessageType.ORDER_UPDATE.value,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "old_status": update.old_status,
                "new_status": update.new_status
            }
        except ImportError:
            logger.warning("models.slack not available, returning basic metadata")
            return {
                "order_number": str(update.order_number if hasattr(update, 'order_number') else 'unknown'),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
    
    def build_leadership_metadata(self, notification: Any) -> Dict[str, Any]:
        """
        Build metadata for leadership notification messages.
        
        Args:
            notification: Slack.LeadershipNotification Pydantic model instance
        
        Returns:
            Dict with metadata fields
        """
        try:
            from models.slack import SlackMessageType
            
            return {
                "notification_type": notification.notification_type,
                "processed_by": notification.processed_by,
                "message_type": SlackMessageType.LEADERSHIP_NOTIFICATION.value,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "year": notification.year,
                "records_processed": notification.records_processed
            }
        except ImportError:
            logger.warning("models.slack not available, returning basic metadata")
            return {
                "notification_type": str(notification.notification_type if hasattr(notification, 'notification_type') else 'unknown'),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
