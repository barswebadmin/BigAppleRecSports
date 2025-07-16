"""
Comprehensive Slack message building utilities.
Consolidated from multiple message builder modules for better organization.
"""

from typing import Dict, Any, Optional, List
import logging
import json
import requests
import re
import html
from datetime import datetime, timezone
from utils.date_utils import format_date_and_time, parse_shopify_datetime, convert_to_eastern_time, get_eastern_timezone
from config import settings

logger = logging.getLogger(__name__)


class SlackMessageBuilder:
    """Comprehensive Slack message builder with all formatting and utility methods."""
    
    def __init__(self, sport_groups: Optional[Dict[str, str]] = None):
        self.sport_groups = sport_groups or {}
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
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
    
    # =============================================================================
    # TEXT EXTRACTION METHODS
    # =============================================================================
    
    def extract_sheet_link(self, message_text: str) -> str:
        """Extract Google Sheets link from Slack message text"""
        try:
            # Handle different Slack link formats
            patterns = [
                r'<(https://docs\.google\.com/spreadsheets/[^|>]+)\|[^>]*>',
                r'<(https://docs\.google\.com/spreadsheets/[^>]+)>',
                r'https://docs\.google\.com/spreadsheets/[^\s]+',
                r'View Request in Google Sheets.*?<([^|>]+)\|',
                r'🔗.*?<([^|>]+)\|[^>]*>',
                r'.*?<(https://docs\.google\.com/[^>]+)>'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, message_text)
                if match:
                    link = match.group(1)
                    if link.startswith('https://docs.google.com'):
                        return link
            
            return ""
        except Exception as e:
            print(f"Error extracting sheet link: {e}")
            return ""
    
    def extract_season_start_info(self, message_text: str) -> Dict[str, Optional[str]]:
        """Extract season start and product info from message text"""
        try:
            result: Dict[str, Optional[str]] = {"season_start_date": None, "product_title": None}
            
            # Extract season start date
            season_patterns = [
                r'Season starts:\*\*\s*([^*\n]+)',
                r'Season starts\*\*\s*([^*\n]+)',
                r'Season Start:\*\*\s*([^*\n]+)',
                r'Season Start\*\*\s*([^*\n]+)',
                r'📅.*?Season.*?(\w{3}\s+\d{1,2},?\s+\d{4})',
                r'Season.*?starts.*?(\w{3}\s+\d{1,2},?\s+\d{4})'
            ]
            
            for pattern in season_patterns:
                match = re.search(pattern, message_text, re.IGNORECASE)
                if match:
                    result["season_start_date"] = match.group(1).strip()
                    break
            
            # Extract product title
            product_patterns = [
                r'Product:\*\*\s*([^*\n]+)',
                r'Product\*\*\s*([^*\n]+)',
                r'🏈\s*([^*\n]+)',
                r'⚽\s*([^*\n]+)',
                r'🏀\s*([^*\n]+)',
                r'🎳\s*([^*\n]+)'
            ]
            
            for pattern in product_patterns:
                match = re.search(pattern, message_text, re.IGNORECASE)
                if match:
                    result["product_title"] = match.group(1).strip()
                    break
            
            return result
        except Exception as e:
            print(f"Error extracting season start info: {e}")
            return {"season_start_date": None, "product_title": None}
    
    # =============================================================================
    # BUTTON CREATION METHODS
    # =============================================================================
    
    def _create_confirm_button(self, order_id: str, order_name: str, requestor_name: Dict[str, str],
                              requestor_email: str, refund_amount: float, refund_type: str,
                              request_notes: str, sheet_link: str, request_submitted_at: str) -> Dict[str, Any]:
        """Create confirm refund button"""
        
        # Format requestor name for button value
        first_name = requestor_name.get("first", "")
        last_name = requestor_name.get("last", "")
        
        button_value = f"orderId={order_id}|rawOrderNumber={order_name}|refundAmount={refund_amount}|refundType={refund_type}|requestorEmail={requestor_email}|requestorFirstName={first_name}|requestorLastName={last_name}|requestSubmittedAt={request_submitted_at}"
        
        if request_notes and request_notes.strip():
            button_value += f"|requestNotes={request_notes}"
        if sheet_link and sheet_link.strip():
            button_value += f"|sheetLink={sheet_link}"
        
        return {
            "type": "button",
            "text": {
                "type": "plain_text", 
                "text": f"✅ Confirm ${refund_amount:.2f} {refund_type.title()}"
            },
            "style": "primary",
            "action_id": "process_refund",
            "value": button_value
        }
    
    def _create_refund_different_amount_button(self, order_id: str, order_name: str, requestor_name: Dict[str, str],
                                              requestor_email: str, refund_type: str, request_notes: str,
                                              sheet_link: str, request_submitted_at: str) -> Dict[str, Any]:
        """Create refund different amount button"""
        
        # Format requestor name for button value
        first_name = requestor_name.get("first", "")
        last_name = requestor_name.get("last", "")
        
        button_value = f"orderId={order_id}|rawOrderNumber={order_name}|refundType={refund_type}|requestorEmail={requestor_email}|requestorFirstName={first_name}|requestorLastName={last_name}|requestSubmittedAt={request_submitted_at}"
        
        if request_notes and request_notes.strip():
            button_value += f"|requestNotes={request_notes}"
        if sheet_link and sheet_link.strip():
            button_value += f"|sheetLink={sheet_link}"
        
        return {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "💰 Different Amount"
            },
            "action_id": "custom_refund_amount",
            "value": button_value
        }
    
    def _create_cancel_order_button(self, order_id: str, order_name: str, requestor_name: Dict[str, str],
                                   requestor_email: str, refund_type: str, request_notes: str,
                                   sheet_link: str, request_submitted_at: str) -> Dict[str, Any]:
        """Create cancel order button"""
        
        # Format requestor name for button value
        first_name = requestor_name.get("first", "")
        last_name = requestor_name.get("last", "")
        
        button_value = f"orderId={order_id}|rawOrderNumber={order_name}|refundType={refund_type}|requestorEmail={requestor_email}|requestorFirstName={first_name}|requestorLastName={last_name}|requestSubmittedAt={request_submitted_at}"
        
        if request_notes and request_notes.strip():
            button_value += f"|requestNotes={request_notes}"
        if sheet_link and sheet_link.strip():
            button_value += f"|sheetLink={sheet_link}"
        
        return {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "❌ Cancel Order & Process Refund"
            },
            "style": "danger",
            "action_id": "cancel_order",
            "value": button_value
        }
    
    def _create_proceed_without_cancel_button(self, order_id: str, order_name: str, requestor_name: Dict[str, str],
                                             requestor_email: str, refund_type: str, request_notes: str,
                                             sheet_link: str, request_submitted_at: str) -> Dict[str, Any]:
        """Create proceed without cancel button"""
        
        # Format requestor name for button value
        first_name = requestor_name.get("first", "")
        last_name = requestor_name.get("last", "")
        
        button_value = f"orderId={order_id}|rawOrderNumber={order_name}|refundType={refund_type}|requestorEmail={requestor_email}|requestorFirstName={first_name}|requestorLastName={last_name}|requestSubmittedAt={request_submitted_at}"
        
        if request_notes and request_notes.strip():
            button_value += f"|requestNotes={request_notes}"
        if sheet_link and sheet_link.strip():
            button_value += f"|sheetLink={sheet_link}"
        
        return {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "➡️ Proceed Without Cancel"
            },
            "action_id": "proceed_without_cancel",
            "value": button_value
        }
    
    def _create_cancel_and_close_button(self, order_name: str) -> Dict[str, Any]:
        """Create cancel and close button"""
        button_value = f"rawOrderNumber={order_name}|action=cancel_and_close"
        
        return {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "🚫 Cancel & Close Request"
            },
            "style": "danger",
            "action_id": "cancel_and_close_request",
            "value": button_value
        }
    
    def _create_process_refund_button(self, order_id: str, order_name: str, requestor_name: Dict[str, str],
                                     requestor_email: str, refund_amount: float, refund_type: str,
                                     request_notes: str, sheet_link: str, request_submitted_at: str,
                                     order_cancelled: bool = False) -> Dict[str, Any]:
        """Create process refund button"""
        
        # Format requestor name for button value
        first_name = requestor_name.get("first", "")
        last_name = requestor_name.get("last", "")
        
        button_value = f"orderId={order_id}|rawOrderNumber={order_name}|refundAmount={refund_amount}|refundType={refund_type}|orderCancelled={order_cancelled}|requestorEmail={requestor_email}|requestorFirstName={first_name}|requestorLastName={last_name}|requestSubmittedAt={request_submitted_at}"
        
        if request_notes and request_notes.strip():
            button_value += f"|requestNotes={request_notes}"
        if sheet_link and sheet_link.strip():
            button_value += f"|sheetLink={sheet_link}"
        
        return {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": f"✅ Process ${refund_amount:.2f} {refund_type.title()}"
            },
            "style": "primary",
            "action_id": "process_refund",
            "value": button_value
        }
    
    def _create_custom_refund_button(self, order_id: str, order_name: str, requestor_name: Dict[str, str],
                                    requestor_email: str, refund_type: str, request_notes: str,
                                    sheet_link: str, request_submitted_at: str) -> Dict[str, Any]:
        """Create custom refund amount button"""
        
        # Format requestor name for button value  
        first_name = requestor_name.get("first", "")
        last_name = requestor_name.get("last", "")
        
        button_value = f"orderId={order_id}|rawOrderNumber={order_name}|refundType={refund_type}|requestorEmail={requestor_email}|requestorFirstName={first_name}|requestorLastName={last_name}|requestSubmittedAt={request_submitted_at}"
        
        return {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "💰 Custom Amount"
            },
            "action_id": "custom_refund_amount",
            "value": button_value
        }
    
    def _create_no_refund_button(self, order_id: str, order_name: str, order_cancelled: bool = False) -> Dict[str, Any]:
        """Create no refund button"""
        button_value = f"orderId={order_id}|rawOrderNumber={order_name}|orderCancelled={order_cancelled}"
        
        return {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "🚫 No Refund"
            },
            "style": "danger",
            "action_id": "no_refund",
            "value": button_value
        }
    
    # =============================================================================
    # COMPREHENSIVE MESSAGE BUILDING METHODS
    # =============================================================================
    
    def build_comprehensive_success_message(self, order_data: Dict[str, Any], refund_amount: float, refund_type: str,
                                          raw_order_number: str, order_cancelled: bool, processor_user: str,
                                          is_debug_mode: bool, current_message_text: str, order_id: str = "") -> Dict[str, Any]:
        """Build comprehensive success message matching Google Apps Script format"""
        try:
            print(f"\n🏗️ === BUILD COMPREHENSIVE SUCCESS MESSAGE DEBUG ===")
            print(f"📝 Current message text length: {len(current_message_text)}")
            print(f"📝 Current message text preview: {current_message_text[:500]}...")
            
            # CRITICAL: Check if we got the full text or the short fallback text
            if len(current_message_text) < 200:
                print(f"⚠️ WARNING: Received very short message text, might be fallback instead of full blocks text!")
                # Add stack trace to see where this is coming from
                import traceback
                print("📍 CALL STACK:")
                traceback.print_stack()
            else:
                print(f"✅ Good: Received full message text ({len(current_message_text)} characters)")
            
            # Extract data from order
            customer = order_data.get("customer", {})
            product = order_data.get("product", {})
            
            # Get customer name from email if available
            customer_email = customer.get("email", "")
            customer_name = customer_email.split("@")[0].replace(".", " ").title() if customer_email else "Unknown Customer"
            
            # Build order URL with debugging (use passed order_id parameter)
            print(f"🔗 Order ID passed to function: {order_id}")
            print(f"🔗 Raw order number: {raw_order_number}")
            
            if order_id:
                order_url = self.get_order_url(order_id, raw_order_number)
                print(f"🔗 Built order URL: {order_url}")
            else:
                order_url = raw_order_number
                print(f"🔗 No order ID, using raw number: {order_url}")
            
            # Extract sheet link from current message
            sheet_link = self.extract_sheet_link(current_message_text)
            print(f"🔗 Extracted sheet link: {sheet_link}")
            
            # Extract season start info
            season_info = self.extract_season_start_info(current_message_text)
            season_start_date = season_info.get("season_start_date")
            product_title = season_info.get("product_title") or product.get("title", "Unknown Product")
            print(f"📅 Season start: {season_start_date}")
            print(f"🏷️ Product title: {product_title}")
            
            # Get product URL if we have product ID
            product_url = ""
            if product.get("id"):
                product_url = self.get_product_url(product.get("id"))
                print(f"🔗 Product URL: {product_url}")
            
            # Build inventory display
            inventory_text = self._build_inventory_text(order_data, product_title, season_start_date)
            print(f"📦 Inventory text: {inventory_text[:100]}...")
            
            # Create success message
            action_text = "🔄 *REFUND PROCESSED*" if not order_cancelled else "❌ *ORDER CANCELLED & REFUND PROCESSED*"
            refund_emoji = "💵" if refund_type.lower() == "refund" else "🎟️"
            
            message_parts = [
                f"{action_text}\n\n",
                f"👤 *Customer:* {customer_name}\n",
                f"📧 *Email:* {customer_email}\n",
                f"📦 *Order:* {order_url}\n"
            ]
            
            if product_url:
                message_parts.append(f"🏷️ *Product:* <{product_url}|{product_title}>\n")
            else:
                message_parts.append(f"🏷️ *Product:* {product_title}\n")
            
            if season_start_date:
                message_parts.append(f"📅 *Season Start:* {season_start_date}\n")
            
            message_parts.extend([
                f"\n{refund_emoji} *{refund_type.title()} Amount:* ${refund_amount:.2f}\n",
                f"👨‍💼 *Processed by:* {processor_user}\n"
            ])
            
            if is_debug_mode:
                message_parts.append("\n🧪 *DEBUG MODE - NO ACTUAL REFUND PROCESSED*\n")
            
            # Add inventory information
            if inventory_text:
                message_parts.append(f"\n{inventory_text}")
            
            # Add sheet link if available
            if sheet_link:
                message_parts.append(f"\n🔗 *<{sheet_link}|View Request in Google Sheets>*\n")
            
            # Build blocks for Slack message
            message_text = "".join(message_parts)
            
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message_text
                    }
                }
            ]
            
            # Add restock buttons if we have inventory data and line items
            line_items = order_data.get("line_items", [])
            if line_items and any(item.get("variant_id") for item in line_items):
                action_buttons = []
                
                for item in line_items:
                    variant_id = item.get("variant_id")
                    variant_title = item.get("title", "Unknown Variant")
                    quantity = item.get("quantity", 1)
                    
                    if variant_id:
                        restock_button_value = f"orderId={order_id}|variantId={variant_id}|variantName={variant_title}|quantity={quantity}"
                        action_buttons.append({
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": f"📈 Restock {variant_title} (+{quantity})"
                            },
                            "action_id": f"restock_{variant_id.split('/')[-1] if '/' in str(variant_id) else variant_id}",
                            "value": restock_button_value
                        })
                
                # Add "Do Not Restock" button
                do_not_restock_value = f"orderId={order_id}|rawOrderNumber={raw_order_number}"
                action_buttons.append({
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🚫 Do Not Restock"
                    },
                    "action_id": "do_not_restock",
                    "value": do_not_restock_value
                })
                
                if action_buttons:
                    blocks.append({
                        "type": "actions",
                        "elements": action_buttons
                    })
            
            result = {
                "text": f"Refund processed for {raw_order_number}",
                "blocks": blocks
            }
            
            print(f"✅ Built comprehensive success message with {len(blocks)} blocks")
            return result
            
        except Exception as e:
            print(f"❌ Error building comprehensive success message: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback simple message
            return {
                "text": f"✅ Refund of ${refund_amount:.2f} processed for {raw_order_number}"
            }
    
    def build_completion_message(self, current_message_full_text: str, action_id: str, variant_name: str,
                               processor_user: str, order_id: str, quantity: Optional[int] = None, 
                               is_debug_mode: bool = False) -> Dict[str, Any]:
        """Build completion message preserving original request details"""
        try:
            print(f"\n🏗️ === BUILD COMPLETION MESSAGE DEBUG ===")
            print(f"🎬 Action ID: {action_id}")
            print(f"📦 Variant: {variant_name}")
            print(f"👤 Processor: {processor_user}")
            print(f"🔢 Order ID: {order_id}")
            print(f"📊 Quantity: {quantity}")
            print(f"🧪 Debug mode: {is_debug_mode}")
            
            # Extract sheet link from current message
            sheet_link = self.extract_sheet_link(current_message_full_text)
            print(f"🔗 Extracted sheet link: {sheet_link}")
            
            # Preserve the original message text but add completion status
            if action_id == "do_not_restock":
                completion_text = f"\n\n✅ *COMPLETED - No Inventory Restocking*\n👨‍💼 *Processed by:* {processor_user}"
                if is_debug_mode:
                    completion_text += "\n🧪 *DEBUG MODE - NO ACTUAL CHANGES MADE*"
            elif action_id.startswith("restock_"):
                completion_text = f"\n\n📈 *INVENTORY RESTOCKED*\n📦 *Variant:* {variant_name}"
                if quantity:
                    completion_text += f"\n📊 *Quantity Added:* +{quantity}"
                completion_text += f"\n👨‍💼 *Processed by:* {processor_user}"
                if is_debug_mode:
                    completion_text += "\n🧪 *DEBUG MODE - NO ACTUAL INVENTORY CHANGES*"
            else:
                completion_text = f"\n\n✅ *COMPLETED*\n👨‍💼 *Processed by:* {processor_user}"
                if is_debug_mode:
                    completion_text += "\n🧪 *DEBUG MODE*"
            
            # Build the complete message
            message_text = current_message_full_text + completion_text
            
            # Add sheet link if available
            if sheet_link:
                message_text += f"\n\n🔗 *<{sheet_link}|View Request in Google Sheets>*"
            
            result = {
                "text": f"Request completed by {processor_user}",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": message_text
                        }
                    }
                ]
            }
            
            print(f"✅ Built completion message")
            return result
            
        except Exception as e:
            print(f"❌ Error building completion message: {e}")
            return {
                "text": f"✅ Request completed by {processor_user}"
            }
    
    def build_comprehensive_no_refund_message(self, order_data: Dict[str, Any], raw_order_number: str,
                                            processor_user: str, is_debug_mode: bool, current_message_text: str,
                                            order_id: str = "", order_cancelled: bool = False) -> Dict[str, Any]:
        """Build comprehensive no refund message with inventory options"""
        try:
            print(f"\n🏗️ === BUILD NO REFUND MESSAGE DEBUG ===")
            print(f"📦 Order: {raw_order_number}")
            print(f"👤 Processor: {processor_user}")
            print(f"🧪 Debug mode: {is_debug_mode}")
            print(f"🔢 Order ID: {order_id}")
            print(f"❌ Order cancelled: {order_cancelled}")
            
            # Extract data from order
            customer = order_data.get("customer", {})
            product = order_data.get("product", {})
            
            # Get customer info
            customer_email = customer.get("email", "")
            customer_name = customer_email.split("@")[0].replace(".", " ").title() if customer_email else "Unknown Customer"
            
            # Build order URL
            if order_id:
                order_url = self.get_order_url(order_id, raw_order_number)
            else:
                order_url = raw_order_number
            
            # Extract sheet link from current message
            sheet_link = self.extract_sheet_link(current_message_text)
            print(f"🔗 Extracted sheet link: {sheet_link}")
            
            # Extract season start info
            season_info = self.extract_season_start_info(current_message_text)
            season_start_date = season_info.get("season_start_date")
            product_title = season_info.get("product_title") or product.get("title", "Unknown Product")
            
            # Get product URL
            product_url = ""
            if product.get("id"):
                product_url = self.get_product_url(product.get("id"))
            
            # Build inventory display
            inventory_text = self._build_inventory_text(order_data, product_title, season_start_date)
            
            # Create no refund message
            if order_cancelled:
                action_text = "❌ *ORDER CANCELLED - NO REFUND ISSUED*"
            else:
                action_text = "🚫 *NO REFUND ISSUED*"
            
            message_parts = [
                f"{action_text}\n\n",
                f"👤 *Customer:* {customer_name}\n",
                f"📧 *Email:* {customer_email}\n",
                f"📦 *Order:* {order_url}\n"
            ]
            
            if product_url:
                message_parts.append(f"🏷️ *Product:* <{product_url}|{product_title}>\n")
            else:
                message_parts.append(f"🏷️ *Product:* {product_title}\n")
            
            if season_start_date:
                message_parts.append(f"📅 *Season Start:* {season_start_date}\n")
            
            message_parts.append(f"\n👨‍💼 *Processed by:* {processor_user}\n")
            
            if is_debug_mode:
                message_parts.append("\n🧪 *DEBUG MODE - NO ACTUAL CHANGES MADE*\n")
            
            # Add inventory information
            if inventory_text:
                message_parts.append(f"\n{inventory_text}")
            
            # Add sheet link if available
            if sheet_link:
                message_parts.append(f"\n🔗 *<{sheet_link}|View Request in Google Sheets>*\n")
            
            # Build blocks for Slack message
            message_text = "".join(message_parts)
            
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message_text
                    }
                }
            ]
            
            # Add restock buttons if we have inventory data and this was a cancellation
            line_items = order_data.get("line_items", [])
            if order_cancelled and line_items and any(item.get("variant_id") for item in line_items):
                action_buttons = []
                
                for item in line_items:
                    variant_id = item.get("variant_id")
                    variant_title = item.get("title", "Unknown Variant")
                    quantity = item.get("quantity", 1)
                    
                    if variant_id:
                        restock_button_value = f"orderId={order_id}|variantId={variant_id}|variantName={variant_title}|quantity={quantity}"
                        action_buttons.append({
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": f"📈 Restock {variant_title} (+{quantity})"
                            },
                            "action_id": f"restock_{variant_id.split('/')[-1] if '/' in str(variant_id) else variant_id}",
                            "value": restock_button_value
                        })
                
                # Add "Do Not Restock" button
                do_not_restock_value = f"orderId={order_id}|rawOrderNumber={raw_order_number}"
                action_buttons.append({
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🚫 Do Not Restock"
                    },
                    "action_id": "do_not_restock",
                    "value": do_not_restock_value
                })
                
                if action_buttons:
                    blocks.append({
                        "type": "actions",
                        "elements": action_buttons
                    })
            
            result = {
                "text": f"No refund processed for {raw_order_number}",
                "blocks": blocks
            }
            
            print(f"✅ Built no refund message with {len(blocks)} blocks")
            return result
            
        except Exception as e:
            print(f"❌ Error building no refund message: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback simple message
            return {
                "text": f"🚫 No refund processed for {raw_order_number}"
            }
    
    # =============================================================================
    # BACKWARD COMPATIBILITY METHODS
    # =============================================================================
    
    def build_success_message(
        self,
        order_data: Dict[str, Any], 
        refund_calculation: Optional[Dict[str, Any]] = None,
        requestor_info: Optional[Dict[str, Any]] = None,
        sheet_link: Optional[str] = None,
        refund_amount: Optional[float] = None,
        refund_type: Optional[str] = None,
        requestor_name: Optional[Dict[str, str]] = None,
        requestor_email: Optional[str] = None,
        request_notes: Optional[str] = None,
        processor_user: Optional[str] = None,
        is_debug_mode: bool = False
    ) -> Dict[str, Any]:
        """Build success message with backward compatibility for different calling patterns"""
        try:
            # Handle the old calling pattern with refund_calculation and requestor_info
            if refund_calculation is not None and requestor_info is not None:
                # Extract data from the old format
                order = order_data.get("order", {})
                customer = order_data.get("customer", {})
                product = order_data.get("product", {})
                
                order_name = order.get("orderName", order.get("name", ""))
                customer_email = customer.get("email", "")
                product_title = product.get("title", "")
                
                # Format order number
                raw_order_number = order_name if order_name.startswith('#') else f"#{order_name}"
                
                # Build order URL
                order_id = order.get("orderId", order.get("id", ""))
                order_url = self.get_order_url(order_id, raw_order_number)
                
                # Build product URL
                product_url = ""
                product_id = product.get("productId", product.get("id", ""))
                if product_id:
                    product_url = self.get_product_url(product_id)
                
                # Extract refund info
                calculated_refund_amount = refund_calculation.get("refund_amount", 0.0)
                calculated_refund_text = refund_calculation.get("message", "")
                season_start_date = refund_calculation.get("season_start_date", "Unknown")
                
                # Extract requestor info
                requestor_name_dict = requestor_info.get("name", {})
                requestor_email_str = requestor_info.get("email", "")
                refund_type_str = requestor_info.get("refund_type", "refund")
                request_notes_str = requestor_info.get("notes", "")
                
                # Get original cost vs total paid for display
                total_paid = order.get("totalAmountPaid", 0) or order.get("total_price", 0) or 0
                if isinstance(total_paid, str):
                    try:
                        total_paid = float(total_paid)
                    except (ValueError, TypeError):
                        total_paid = 0
                
                # Get formatted strings
                request_type_text = self._get_request_type_text(refund_type_str)
                optional_notes = self._get_optional_request_notes(request_notes_str)
                requestor_line = self._get_requestor_line(requestor_name_dict, requestor_email_str)
                sheet_link_line = self._get_sheet_link_line(sheet_link)
                order_created_time = self._get_order_created_time(order)
                sport_group = self.get_sport_group_mention(product_title)
                
                # Build inventory information
                inventory_text = self._build_inventory_text(order_data, product_title, season_start_date)
                
                # Create message text
                message_parts = [
                    f"📌 *New Refund Request!*\n\n",
                    f"*Request Type*: {request_type_text}\n\n",
                    requestor_line,
                    f"*Request Submitted At*: {format_date_and_time(datetime.now(timezone.utc))}\n\n",
                    f"*Order Number*: {order_url}\n\n",
                    f"*Order Created At:* {order_created_time}\n\n"
                ]
                
                if product_url:
                    message_parts.append(f"*Sport/Season/Day:* <{product_url}|{product_title}>\n\n")
                else:
                    message_parts.append(f"*Sport/Season/Day:* {product_title}\n\n")
                
                message_parts.extend([
                    f"*Season Start Date*: {season_start_date}\n\n",
                    f"*Total Paid:* ${total_paid:.2f}\n\n"
                ])
                
                if calculated_refund_text:
                    message_parts.append(f"{calculated_refund_text}\n\n")
                
                message_parts.append(optional_notes)
                
                # Add inventory information if available
                if inventory_text:
                    message_parts.append(f"{inventory_text}\n\n")
                
                message_parts.append(sheet_link_line)
                message_parts.append(f"*Attn*: {sport_group}")
                
                message_text = "".join(message_parts)
                
                # Create action buttons for the initial request
                first_name = requestor_name_dict.get("first", "")
                last_name = requestor_name_dict.get("last", "")
                current_time = format_date_and_time(datetime.now(timezone.utc))
                
                action_buttons = [
                    self._create_cancel_order_button(
                        order_id, raw_order_number, requestor_name_dict, requestor_email_str,
                        refund_type_str, request_notes_str, sheet_link or "", current_time
                    ),
                    self._create_proceed_without_cancel_button(
                        order_id, raw_order_number, requestor_name_dict, requestor_email_str,
                        refund_type_str, request_notes_str, sheet_link or "", current_time
                    ),
                    self._create_cancel_and_close_button(raw_order_number)
                ]
                
                return {
                    "text": message_text,
                    "action_buttons": action_buttons,
                    "slack_text": "📌 *New Refund Request!*"
                }
            
            # Handle the new calling pattern with individual parameters
            else:
                # Use the new consolidated method
                return self.build_success_message_new(
                    order_data=order_data,
                    refund_amount=refund_amount or 0.0,
                    refund_type=refund_type or "refund",
                    requestor_name=requestor_name or {},
                    requestor_email=requestor_email or "",
                    request_notes=request_notes or "",
                    sheet_link=sheet_link or "",
                    processor_user=processor_user or "",
                    is_debug_mode=is_debug_mode
                )
                
        except Exception as e:
            logger.error(f"Error building success message: {e}")
            return self.build_fallback_message(
                order_data.get("order", {}).get("orderNumber", "Unknown"),
                f"Error creating message: {str(e)}"
            )
    
    def build_success_message_new(
        self,
        order_data: Dict[str, Any], 
        refund_amount: float,
        refund_type: str,
        requestor_name: Dict[str, str],
        requestor_email: str,
        request_notes: str,
        sheet_link: str,
        processor_user: str,
        is_debug_mode: bool = False
    ) -> Dict[str, Any]:
        """Build success message after processing refund (new format)"""
        try:
            # Extract order information
            order = order_data.get("order", {})
            customer = order_data.get("customer", {})
            product = order_data.get("product", {})
            
            order_name = order.get("order_number", order.get("name", ""))
            customer_email = customer.get("email", "")
            product_title = product.get("title", "")
            
            # Format order number
            raw_order_number = order_name if order_name.startswith('#') else f"#{order_name}"
            
            # Build order URL
            order_id = order.get("id", "")
            order_url = self.get_order_url(order_id, raw_order_number)
            
            # Build product URL
            product_url = ""
            if product.get("id"):
                product_url = self.get_product_url(product.get("id"))
            
            # Get request type icon
            refund_emoji = "💵" if refund_type.lower() == "refund" else "🎟️"
            
            # Build success message
            message_parts = [
                f"✅ *REFUND PROCESSED*\n\n",
                f"📦 *Order:* {order_url}\n",
                f"👤 *Customer:* {customer_email}\n"
            ]
            
            if product_url:
                message_parts.append(f"🏷️ *Product:* <{product_url}|{product_title}>\n")
            else:
                message_parts.append(f"🏷️ *Product:* {product_title}\n")
            
            message_parts.extend([
                f"{refund_emoji} *{refund_type.title()} Amount:* ${refund_amount:.2f}\n",
                f"👨‍💼 *Processed by:* {processor_user}\n"
            ])
            
            if is_debug_mode:
                message_parts.append("\n🧪 *DEBUG MODE - NO ACTUAL REFUND PROCESSED*\n")
            
            # Add requestor info
            requestor_line = self._get_requestor_line(requestor_name, requestor_email)
            message_parts.append(f"\n{requestor_line}")
            
            # Add optional notes
            optional_notes = self._get_optional_request_notes(request_notes)
            message_parts.append(optional_notes)
            
            # Add sheet link
            sheet_link_line = self._get_sheet_link_line(sheet_link)
            message_parts.append(sheet_link_line)
            
            message_text = "".join(message_parts)
            
            return {
                "text": f"Refund processed for {raw_order_number}",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": message_text
                        }
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error building success message: {e}")
            return self.build_fallback_message(
                order_data.get("order", {}).get("order_number", "Unknown"),
                f"Refund processed but error formatting message: {str(e)}"
            )
    
    def build_fallback_message(
        self,
        order_number: Optional[str] = None,
        message: Optional[str] = None,
        season_start_date: Optional[str] = None,
        order_data: Optional[Dict[str, Any]] = None,
        requestor_info: Optional[Dict[str, Any]] = None,
        sheet_link: Optional[str] = None,
        error_message: Optional[str] = None,
        refund_calculation: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build a fallback message with backward compatibility"""
        try:
            # Handle old calling pattern with order_data and requestor_info
            if order_data is not None and requestor_info is not None:
                order = order_data.get("order", {})
                product = order.get("product", {})
                
                # Safely get order ID and name with fallbacks
                order_id = order.get("orderId") or order.get("id") or "unknown"
                order_name = order.get("orderName") or order.get("name") or "unknown"
                
                order_url = self.get_order_url(order_id, order_name)
                
                # Safely get product title
                product_title = product.get("title", "Unknown Product")
                sport_mention = self.get_sport_group_mention(product_title)
                
                # Extract requestor data
                requestor_name = requestor_info.get("name", {})
                requestor_email = requestor_info.get("email", "unknown@example.com")
                refund_type = requestor_info.get("refund_type", "refund")
                request_notes = requestor_info.get("notes", "")
                
                # Calculate fallback refund amount
                total_paid = order.get("totalAmountPaid", 0) or order.get("total_price", 0) or 0
                if isinstance(total_paid, str):
                    try:
                        total_paid = float(total_paid)
                    except (ValueError, TypeError):
                        total_paid = 0
                
                # Use refund calculation if available, otherwise calculate fallback
                if refund_calculation and refund_calculation.get("missing_season_info"):
                    fallback_refund_amount = refund_calculation.get("refund_amount", 0)
                    calculation_message = refund_calculation.get("message", "")
                else:
                    fallback_refund_amount = total_paid * 0.9 if refund_type == "refund" else total_paid * 0.95
                    calculation_message = ""
                
                # Build message text
                current_time = format_date_and_time(datetime.now(timezone.utc))
                order_created_time = self._get_order_created_time(order)
                
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
                
                # Get product URL
                product_id = product.get("productId") or product.get("id") or ""
                product_url = self.get_product_url(product_id) if product_id else "#"
                message_text += f"*Product Title*: <{product_url}|{product_title}>\n\n"
                message_text += f"*Total Paid:* ${total_paid:.2f}\n\n"
                
                # Show refund calculation or generic warning
                if calculation_message:
                    message_text += f"{calculation_message}\n\n"
                else:
                    message_text += f"⚠️ *Could not parse 'Season Dates' from this order's description (in order to calculate a refund amount).*\n\n"
                    message_text += f"Please verify the product and either contact the requestor or process anyway.\n\n"
                
                message_text += self._get_optional_request_notes(request_notes)
                message_text += self._get_sheet_link_line(sheet_link)
                message_text += f"*Attn*: {sport_mention}"
                
                # Create action buttons
                action_buttons = [
                    self._create_cancel_order_button(
                        order_id, order_name, requestor_name, requestor_email,
                        refund_type, request_notes, sheet_link or "", current_time
                    ),
                    self._create_proceed_without_cancel_button(
                        order_id, order_name, requestor_name, requestor_email,
                        refund_type, request_notes, sheet_link or "", current_time
                    ),
                    self._create_cancel_and_close_button(order_name)
                ]
                
                return {
                    "text": message_text,
                    "action_buttons": action_buttons,
                    "slack_text": "⚠️ *Refund Request Missing Season Info*"
                }
            
            # Handle new simple calling pattern
            else:
                fallback_text = f"📦 *Order:* #{order_number or 'Unknown'}\n{message or 'Error processing request'}"
                
                if season_start_date:
                    fallback_text += f"\n📅 *Season Start:* {season_start_date}"
                
                return {
                    "text": f"Order {order_number or 'Unknown'}: {message or 'Error'}",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": fallback_text
                            }
                        }
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error building fallback message: {e}")
            return {
                "text": f"Order {order_number or 'Unknown'}: {message or 'Error'}"
            }
    
    def build_error_message(
        self,
        error_type: Optional[str] = None,
        requestor_info: Optional[Dict[str, Any]] = None,
        sheet_link: Optional[str] = None,
        raw_order_number: Optional[str] = None,
        order_customer_email: Optional[str] = None,
        order_number: Optional[str] = None,
        error_message: Optional[str] = None,
        requestor_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build error message with backward compatibility"""
        try:
            # Handle old calling pattern with error_type and requestor_info
            if error_type is not None and requestor_info is not None:
                # Validate error type
                if error_type not in ["order_not_found", "email_mismatch", "unknown"]:
                    error_type = "unknown"
                
                current_time = format_date_and_time(datetime.now(timezone.utc))
                
                # Safely extract requestor info
                requestor_name = requestor_info.get("name", {})
                requestor_email_str = requestor_info.get("email", "unknown@example.com")
                refund_type = requestor_info.get("refund_type", "refund")
                request_notes = requestor_info.get("notes", "")
     
                # Build unified error message
                if error_type == "order_not_found":
                    error_text = "❌ *Error with Refund Request - Order Not Found in Shopify*\n\n"
                    error_text += f"*Request Type*: {self._get_request_type_text(refund_type)}\n\n"
                    error_text += f"*Request Submitted At*: {current_time}\n\n"
                    error_text += self._get_requestor_line(requestor_name, requestor_email_str)
                    error_text += f"🔎 *Order Number Provided:* {raw_order_number or 'N/A'} - this order cannot be found in Shopify\n\n"
                    error_text += self._get_optional_request_notes(request_notes)
                    error_text += f"📩 *The requestor has been emailed to please provide correct order info. No action needed at this time.*\n"
                    error_text += self._get_sheet_link_line(sheet_link)
                    
                elif error_type == "email_mismatch":
                    error_text = "❌ *Error with Refund Request - Email provided did not match order*\n\n"
                    error_text += f"*Request Type*: {self._get_request_type_text(refund_type)}\n\n"
                    error_text += f"*Request Submitted At*: {current_time}\n\n"
                    error_text += self._get_requestor_line(requestor_name, requestor_email_str)
                    error_text += f"*Email Associated with Order:* {order_customer_email or 'N/A'}\n\n"
                    error_text += f"*Order Number:* {raw_order_number or 'N/A'}\n\n"
                    error_text += self._get_optional_request_notes(request_notes)
                    error_text += f"📩 *The requestor has been emailed to please provide correct order info. No action needed at this time.*\n"
                    error_text += self._get_sheet_link_line(sheet_link)
                    
                else:
                    error_text = "❌ *Error with Refund Request*\n\n"
                    error_text += f"*Request Type*: {self._get_request_type_text(refund_type)}\n\n"
                    error_text += f"*Request Submitted At*: {current_time}\n\n"
                    error_text += self._get_requestor_line(requestor_name, requestor_email_str)
                    error_text += self._get_optional_request_notes(request_notes)
                    error_text += self._get_sheet_link_line(sheet_link)
                
                slack_text = "❌ *Refund Request Submitted with Error*"
                
                return {
                    "text": error_text,
                    "action_buttons": [],
                    "slack_text": slack_text
                }
            
            # Handle new calling pattern
            else:
                message_parts = [
                    f"❌ *ERROR PROCESSING REQUEST*\n\n",
                    f"📦 *Order:* #{order_number or 'Unknown'}\n"
                ]
                
                if requestor_email:
                    message_parts.append(f"📧 *Requestor:* {requestor_email}\n")
                
                message_parts.append(f"⚠️ *Error:* {error_message or 'Unknown error'}\n")
                
                if sheet_link:
                    message_parts.append(f"\n🔗 *<{sheet_link}|View Request in Google Sheets>*\n")
                
                message_text = "".join(message_parts)
                
                return {
                    "text": f"Error processing refund for {order_number or 'Unknown'}",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": message_text
                            }
                        }
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error building error message: {e}")
            # Ultra-safe fallback
            email = requestor_email or "unknown@example.com"
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

    # =============================================================================
    # ORIGINAL MESSAGE BUILDING METHODS
    # =============================================================================
    
    def create_refund_decision_message(self, order_data: Dict[str, Any], refund_type: str,
                                     requestor_name: Dict[str, str], requestor_email: str,
                                     request_notes: str, sheet_link: str, request_submitted_at: str,
                                     refund_amount: float) -> Dict[str, Any]:
        """Create the main refund decision message with all action buttons"""
        try:
            # Extract order information
            order = order_data.get("order", {})
            customer = order_data.get("customer", {})
            product = order_data.get("product", {})
            
            order_id = order.get("id", "")
            order_name = order.get("order_number", order.get("name", ""))
            customer_email = customer.get("email", "")
            product_title = product.get("title", "")
            
            # Format order number
            raw_order_number = order_name if order_name.startswith('#') else f"#{order_name}"
            
            # Build inventory information
            inventory_text = self._build_inventory_text(order_data, product_title, "")
            
            # Build order URL
            order_url = self.get_order_url(order_id, raw_order_number)
            
            # Build product URL
            product_url = ""
            if product.get("id"):
                product_url = self.get_product_url(product.get("id"))
            
            # Get sport group mention
            sport_group = self.get_sport_group_mention(product_title)
            
            # Get formatted strings
            request_type_text = self._get_request_type_text(refund_type)
            optional_notes = self._get_optional_request_notes(request_notes)
            requestor_line = self._get_requestor_line(requestor_name, requestor_email)
            sheet_link_line = self._get_sheet_link_line(sheet_link)
            order_created_time = self._get_order_created_time(order)
            
            # Create message text
            message_parts = [
                f"🚨 *NEW REFUND REQUEST* {sport_group}\n\n",
                f"📦 *Order:* {order_url}\n",
                f"👤 *Customer:* {customer_email}\n"
            ]
            
            if product_url:
                message_parts.append(f"🏷️ *Product:* <{product_url}|{product_title}>\n")
            else:
                message_parts.append(f"🏷️ *Product:* {product_title}\n")
            
            message_parts.extend([
                f"📅 *Order Date:* {order_created_time}\n",
                f"💰 *Refund Amount:* ${refund_amount:.2f}\n",
                f"🎯 *Request Type:* {request_type_text}\n\n",
                optional_notes,
                requestor_line
            ])
            
            if inventory_text:
                message_parts.append(f"{inventory_text}\n")
            
            message_parts.append(sheet_link_line)
            
            message_text = "".join(message_parts)
            
            # Create action buttons
            action_buttons = [
                self._create_confirm_button(
                    order_id, raw_order_number, requestor_name, requestor_email,
                    refund_amount, refund_type, request_notes, sheet_link, request_submitted_at
                ),
                self._create_refund_different_amount_button(
                    order_id, raw_order_number, requestor_name, requestor_email,
                    refund_type, request_notes, sheet_link, request_submitted_at
                ),
                self._create_cancel_order_button(
                    order_id, raw_order_number, requestor_name, requestor_email,
                    refund_type, request_notes, sheet_link, request_submitted_at
                )
            ]
            
            return {
                "text": f"New refund request for {raw_order_number}",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": message_text
                        }
                    },
                    {
                        "type": "actions",
                        "elements": action_buttons
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error creating refund decision message: {e}")
            return self.build_fallback_message(
                order_data.get("order", {}).get("order_number", "Unknown"),
                f"Error creating refund message: {str(e)}"
            )
    
    def _build_inventory_text(self, order_data: Dict[str, Any], product_title: str, season_start_date: Optional[str]) -> str:
        """Build inventory information text"""
        try:
            line_items = order_data.get("line_items", [])
            if not line_items:
                return ""
            
            inventory_parts = ["📋 *Current Inventory:*\n"]
            
            for item in line_items:
                title = item.get("title", "Unknown Item")
                quantity = item.get("quantity", 0)
                inventory_quantity = item.get("inventory_quantity", 0)
                
                inventory_parts.append(f"• {title}: {inventory_quantity} available (ordered: {quantity})\n")
            
            return "".join(inventory_parts)
            
        except Exception:
            return "" 