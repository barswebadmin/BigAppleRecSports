"""
Slack message building utilities.
Extracted from the main SlackService to improve modularity.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from utils.date_utils import format_date_and_time, parse_shopify_datetime, convert_to_eastern_time, get_eastern_timezone


class SlackMessageBuilder:
    """Helper class for building Slack messages with consistent formatting."""
    
    def __init__(self, sport_groups: Dict[str, str]):
        self.sport_groups = sport_groups
    
    def get_sport_group_mention(self, product_title: str) -> str:
        """Get the appropriate Slack group mention based on product title"""
        title_lower = product_title.lower()
        
        for sport, group_id in self.sport_groups.items():
            if sport in title_lower:
                return group_id
        
        return "@here"  # fallback
    
    def get_order_url(self, order_id: str, order_name: str) -> str:
        """Create Shopify admin order URL for Slack"""
        order_id_digits = order_id.split('/')[-1] if '/' in order_id else order_id
        normalized_order_name = order_name if order_name.startswith('#') else f"#{order_name}"
        return f"<https://admin.shopify.com/store/09fe59-3/orders/{order_id_digits}|{normalized_order_name}>"
    
    def get_product_url(self, product_id: str) -> str:
        """Create Shopify admin product URL for Slack"""
        product_id_digits = product_id.split('/')[-1] if '/' in product_id else product_id
        return f"https://admin.shopify.com/store/09fe59-3/products/{product_id_digits}"
    
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
            if request_notes and isinstance(request_notes, str) and request_notes.strip():
                return f"*Notes provided by requestor*: {request_notes}\n\n"
            return ""
        except Exception:
            return ""
    
    def _get_requestor_line(self, requestor_name: Dict[str, str], requestor_email: str) -> str:
        """Get formatted requestor line"""
        try:
            if isinstance(requestor_name, dict):
                first_name = requestor_name.get("first", "")
                last_name = requestor_name.get("last", "")
                full_name = f"{first_name} {last_name}".strip()
                if full_name:
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
                "processed_at"
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
    
    def _create_confirm_button(self, order_id: str, order_name: str, requestor_name: Dict[str, str], 
                             requestor_email: str, refund_type: str, refund_amount: float) -> Dict[str, Any]:
        """Create the confirm/approve button matching Google Apps Script format"""
        try:
            formatted_amount = int(refund_amount) if refund_amount == int(refund_amount) else f"{refund_amount:.2f}"
            
            button_text = f"✅ Process ${formatted_amount} Refund" if refund_type == "refund" else f"✅ Issue ${formatted_amount} Store Credit"
            
            # Safely get names
            first_name = requestor_name.get("first", "") if isinstance(requestor_name, dict) else ""
            last_name = requestor_name.get("last", "") if isinstance(requestor_name, dict) else ""
            
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": button_text},
                "action_id": "approve_refund",
                "value": f"rawOrderNumber={order_name}|orderId={order_id}|refundAmount={refund_amount}",
                "style": "primary",
                "confirm": {
                    "title": {"type": "plain_text", "text": "Confirm Approval"},
                    "text": {"type": "plain_text", "text": f"You are about to issue {first_name} {last_name} a {refund_type} for ${formatted_amount}. Proceed?"},
                    "confirm": {"type": "plain_text", "text": "Yes, confirm"},
                    "deny": {"type": "plain_text", "text": "Cancel"}
                }
            }
        except Exception:
            # Return a basic button if there's any error
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "✅ Process Refund"},
                "action_id": "approve_refund",
                "value": f"rawOrderNumber={order_name}|orderId={order_id}|refundAmount={refund_amount}",
                "style": "primary"
            }
    
    def _create_refund_different_amount_button(self, order_id: str, order_name: str, requestor_name: Dict[str, str], 
                                             requestor_email: str, refund_type: str, refund_amount: float) -> Dict[str, Any]:
        """Create the custom amount button matching Google Apps Script format"""
        try:
            button_text = "✏️ Process custom Refund amt" if refund_type == "refund" else "✏️ Issue custom Store Credit amt"
            
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": button_text},
                "action_id": "refund_different_amount",
                "value": f"orderId={order_id}|refundAmount={refund_amount}|rawOrderNumber={order_name}"
            }
        except Exception:
            # Return a basic button if there's any error
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "✏️ Process custom amount"},
                "action_id": "refund_different_amount",
                "value": f"orderId={order_id}|refundAmount={refund_amount}|rawOrderNumber={order_name}"
            }
    
    def _create_cancel_button(self, order_name: str) -> Dict[str, Any]:
        """Create the cancel button matching Google Apps Script format"""
        try:
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "❌ Cancel and Close Request"},
                "style": "danger",
                "action_id": "cancel_refund_request",
                "value": f"rawOrderNumber={order_name}",
                "confirm": {
                    "title": {"type": "plain_text", "text": "Confirm Cancellation"},
                    "text": {"type": "plain_text", "text": "Are you sure you want to cancel and close this request?"},
                    "confirm": {"type": "plain_text", "text": "Yes, cancel and close it"},
                    "deny": {"type": "plain_text", "text": "No, keep it"}
                }
            }
        except Exception:
            # Return a basic button if there's any error
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "❌ Cancel Request"},
                "style": "danger",
                "action_id": "cancel_refund_request",
                "value": f"rawOrderNumber={order_name or 'unknown'}"
            }
    
    def _build_inventory_text(self, order_data: Dict[str, Any], product_title: str, season_start_date: str) -> str:
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
            product_id = product.get("productId", "")
            
            if product_id:
                product_url = self.get_product_url(product_id)
                text = f"📦 *Season Start Date for <{product_url}|{product_title}> is {season_start_date}.*\n*Current Inventory:*\n"
            else:
                text = f"📦 *Season Start Date for {product_title} is {season_start_date}.*\n*Current Inventory:*\n"
            
            for key in inventory_order:
                if key in inventory_list and inventory_list[key].get("inventory") is not None:
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
        sheet_link: str
    ) -> Dict[str, Any]:
        """Build a successful refund request message with action buttons"""
        try:
            order = order_data.get("order", {})
            product = order.get("product", {})
            
            # Common elements - use safe access
            current_time = format_date_and_time(datetime.now(timezone.utc))
            order_created_time = self._get_order_created_time(order)
            
            # Safely get order ID and name with fallbacks
            order_id = order.get("orderId") or order.get("id") or "unknown"
            order_name = order.get("orderName") or order.get("name") or "unknown"
            
            order_url = self.get_order_url(order_id, order_name)
            
            # Safely get product info
            product_id = product.get("productId") or product.get("id") or ""
            product_title = product.get("title", "Unknown Product")
            product_url = self.get_product_url(product_id) if product_id else "#"
            sport_mention = self.get_sport_group_mention(product_title)
            
            # Extract data
            requestor_name = requestor_info.get("name", {})
            requestor_email = requestor_info.get("email", "unknown@example.com")
            refund_type = requestor_info.get("refund_type", "refund")
            request_notes = requestor_info.get("notes", "")
            
            season_start_date = refund_calculation.get("season_start_date", "Unknown")
            refund_amount = refund_calculation.get("refund_amount", 0.0)
            refund_text = refund_calculation.get("message", "")
            
            # Get both original cost (early bird variant price) and total paid amounts
            original_cost = refund_calculation.get("original_cost")
            total_paid = order.get("totalAmountPaid", 0) or order.get("total_price", 0) or 0
            if isinstance(total_paid, str):
                try:
                    total_paid = float(total_paid)
                except (ValueError, TypeError):
                    total_paid = 0
            
            # Header
            header_text = "📌 *New Refund Request!*\n\n"
            
            # Build message text
            message_text = f"{header_text}"
            message_text += f"*Request Type*: {self._get_request_type_text(refund_type)}\n\n"
            message_text += self._get_requestor_line(requestor_name, requestor_email)
            message_text += f"*Request Submitted At*: {current_time}\n\n"
            message_text += f"*Order Number*: {order_url}\n\n"
            message_text += f"*Order Created At:* {order_created_time}\n\n"
            message_text += f"*Sport/Season/Day:* <{product_url}|{product_title}>\n\n"
            message_text += f"*Season Start Date*: {season_start_date}\n\n"
            # Add Original Price field if different from Total Paid
            if original_cost is not None and abs(original_cost - total_paid) > 0.01:
                message_text += f"*Original Price:* ${original_cost:.2f}\n\n"
            message_text += f"*Total Paid:* ${total_paid:.2f}\n\n"
            message_text += f"{refund_text}\n\n"
            message_text += self._get_optional_request_notes(request_notes)
            
            # Add inventory information if available
            if order_data.get("inventory_summary"):
                inventory_text = self._build_inventory_text(order_data, product_title, season_start_date)
                message_text += f"{inventory_text}\n\n"
            
            message_text += self._get_sheet_link_line(sheet_link)
            message_text += f"*Attn*: {sport_mention}"
            
            # Create action buttons - use safe values
            action_buttons = [
                self._create_confirm_button(order_id, order_name, requestor_name, requestor_email, refund_type, refund_amount),
                self._create_refund_different_amount_button(order_id, order_name, requestor_name, requestor_email, refund_type, refund_amount),
                self._create_cancel_button(order_name)
            ]
            
            return {
                "text": message_text,
                "action_buttons": action_buttons,
                "slack_text": header_text
            }
            
        except Exception as e:
            # If all else fails, provide a very basic success message
            requestor_email = "unknown@example.com"
            try:
                requestor_email = requestor_info.get("email", "unknown@example.com")
            except:
                pass
                
            error_text = f"❌ *Error building success message*\n\nError: {str(e)}\n\nRequestor: {requestor_email}\n\nPlease check the order data manually."
            return {
                "text": error_text,
                "action_buttons": [],
                "slack_text": "❌ Error building message"
            }
    
    def build_fallback_message(
        self,
        order_data: Dict[str, Any],
        requestor_info: Dict[str, Any],
        sheet_link: str,
        error_message: str = ""
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
            order_name = order.get("orderName") or order.get("name") or "unknown"
            
            order_url = self.get_order_url(order_id, order_name)
            
            # Safely get product title
            product_title = product.get("title", "Unknown Product")
            sport_mention = self.get_sport_group_mention(product_title)
            
            # Extract data
            requestor_name = requestor_info.get("name", {})
            requestor_email = requestor_info.get("email", "unknown@example.com")
            refund_type = requestor_info.get("refund_type", "refund")
            request_notes = requestor_info.get("notes", "")
            
            # Calculate fallback refund amount (90% for refund, 95% for credit)
            total_paid = order.get("totalAmountPaid", 0) or order.get("total_price", 0) or 0
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
                    variant_name = variant.get("variantName", variant.get("title", "")).lower()
                    if "trans" in variant_name:
                        variant_price = variant.get("price")
                        if variant_price:
                            original_cost = float(variant_price)
                            break
            except (ValueError, TypeError):
                pass
            
            fallback_refund_amount = total_paid * 0.9 if refund_type == "refund" else total_paid * 0.95
            
            # Header
            header_text = "📌 *New Refund Request!*\n\n"
            
            # Build message text
            message_text = f"{header_text}"
            message_text += f"⚠️ *Order Found in Shopify but Missing Season Info (or Product Is Not a Regular Season)*\n\n"
            message_text += f"*Request Type*: {self._get_request_type_text(refund_type)}\n\n"
            message_text += self._get_requestor_line(requestor_name, requestor_email)
            message_text += f"*Request Submitted At*: {current_time}\n\n"
            message_text += f"*Order Number Provided*: {order_url}\n\n"
            message_text += f"*Order Created At:* {order_created_time}\n\n"
            message_text += f"*Product Title*: {product_title}\n\n"
            # Add Original Price field if different from Total Paid
            if original_cost is not None and abs(original_cost - total_paid) > 0.01:
                message_text += f"*Original Price:* ${original_cost:.2f}\n\n"
            message_text += f"*Total Paid:* ${total_paid:.2f}\n\n"
            message_text += f"⚠️ *Could not parse 'Season Dates' from this order's description (in order to calculate a refund amount).*\n\n"
            message_text += f"Please verify the product and either contact the requestor or process anyway.\n\n"
            message_text += self._get_optional_request_notes(request_notes)
            message_text += self._get_sheet_link_line(sheet_link)
            message_text += f"*Attn*: {sport_mention}"
            
            # Create action buttons - use safe values
            action_buttons = [
                self._create_confirm_button(order_id, order_name, requestor_name, requestor_email, refund_type, fallback_refund_amount),
                self._create_refund_different_amount_button(order_id, order_name, requestor_name, requestor_email, refund_type, fallback_refund_amount),
                self._create_cancel_button(order_name)
            ]
            
            return {
                "text": message_text,
                "action_buttons": action_buttons,
                "slack_text": "⚠️ *Refund Request Missing Season Info*"
            }
            
        except Exception as e:
            # If all else fails, provide a very basic fallback message
            requestor_email = "unknown@example.com"
            try:
                requestor_email = requestor_info.get("email", "unknown@example.com")
            except:
                pass
                
            error_text = f"❌ *Error building fallback message*\n\nError: {str(e)}\n\nRequestor: {requestor_email}\n\nPlease check the order data manually."
            return {
                "text": error_text,
                "action_buttons": [],
                "slack_text": "❌ Error building message"
            }
    
    def build_error_message(
        self,
        error_type: str,
        requestor_info: Dict[str, Any],
        sheet_link: str,
        raw_order_number: str = "",
        order_customer_email: str = ""
    ) -> Dict[str, Any]:
        """Build an error message for various error scenarios"""
        try:
            # Validate error type
            if error_type not in ["order_not_found", "email_mismatch", "unknown"]:
                error_type = "unknown"
            
            current_time = format_date_and_time(datetime.now(timezone.utc))
            
            # Safely extract requestor info
            requestor_name = requestor_info.get("name", {})
            requestor_email = requestor_info.get("email", "unknown@example.com")
            refund_type = requestor_info.get("refund_type", "refund")
            request_notes = requestor_info.get("notes", "")

            # Build unified error message
            if error_type == "order_not_found":
                error_text = "❌ *Error with Refund Request - Order Not Found in Shopify*\n\n"
                error_text += f"*Request Type*: {self._get_request_type_text(refund_type)}\n\n"
                error_text += f"*Request Submitted At*: {current_time}\n\n"
                error_text += self._get_requestor_line(requestor_name, requestor_email)
                error_text += f"🔎 *Order Number Provided:* {raw_order_number or 'N/A'} - this order cannot be found in Shopify\n\n"
                error_text += self._get_optional_request_notes(request_notes)
                error_text += f"📩 *The requestor has been emailed to please provide correct order info. No action needed at this time.*\n"
                error_text += self._get_sheet_link_line(sheet_link)
                
            elif error_type == "email_mismatch":
                error_text = "❌ *Error with Refund Request - Email provided did not match order*\n\n"
                error_text += f"*Request Type*: {self._get_request_type_text(refund_type)}\n\n"
                error_text += f"*Request Submitted At*: {current_time}\n\n"
                error_text += self._get_requestor_line(requestor_name, requestor_email)
                error_text += f"*Email Associated with Order:* {order_customer_email or 'N/A'}\n\n"
                error_text += f"*Order Number:* {raw_order_number or 'N/A'}\n\n"
                error_text += self._get_optional_request_notes(request_notes)
                error_text += f"📩 *The requestor has been emailed to please provide correct order info. No action needed at this time.*\n"
                error_text += self._get_sheet_link_line(sheet_link)
                # Note: sport mention would be added here if order_data was available
                
            else:
                error_text = "❌ *Error with Refund Request*\n\n"
                error_text += f"*Request Type*: {self._get_request_type_text(refund_type)}\n\n"
                error_text += f"*Request Submitted At*: {current_time}\n\n"
                error_text += self._get_requestor_line(requestor_name, requestor_email)
                error_text += self._get_optional_request_notes(request_notes)
                error_text += self._get_sheet_link_line(sheet_link)
            
            slack_text = "❌ *Refund Request Submitted with Error*"
            
            return {
                "text": error_text,
                "action_buttons": [],
                "slack_text": slack_text
            }
            
        except Exception as e:
            # Ultra-safe fallback
            email = "unknown@example.com"
            try:
                if isinstance(requestor_info, dict):
                    email = requestor_info.get("email", "unknown@example.com")
            except:
                pass
                
            error_text = f"❌ *Error building error message*\n\nError: {str(e)}\n\nRequestor: {email}"
            return {
                "text": error_text,
                "action_buttons": [],
                "slack_text": "❌ Error building message"
            } 