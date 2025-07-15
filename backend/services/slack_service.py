import requests
import json
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
from config import settings
from utils.date_utils import format_date_and_time

logger = logging.getLogger(__name__)

class SlackService:
    def __init__(self):
        # Slack configuration - dynamic based on environment (like Google Apps Script MODE)
        is_production = settings.environment == "production"
        
        self.refunds_channel = {
            "name": "#refunds" if is_production else "#joe-test",
            "channel_id": "C08J1EN7SFR" if is_production else "C092RU7R6PL",
            "bearer_token": settings.slack_refunds_bot_token or ""
        }
        
        # Sport-specific team mentions
        self.sport_groups = {
            "kickball": "<!subteam^S08L2521XAM>",
            "bowling": "<!subteam^S08KJJ02738>", 
            "pickleball": "<!subteam^S08KTJ33Z9R>",
            "dodgeball": "<!subteam^S08KJJ5CL4W>"
        }
    
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
        """Create Shopify admin product URL"""
        product_id_digits = product_id.split('/')[-1] if '/' in product_id else product_id
        return f"https://admin.shopify.com/store/09fe59-3/products/{product_id_digits}"
    
    def send_refund_notification(self, order_data: Dict[str, Any], refund_data: Dict[str, Any], 
                               sheet_link: Optional[str] = None, user_name: str = "API") -> Dict[str, Any]:
        """
        Send a refund completion notification to Slack
        Based on the approveRefundRequest function from the original script
        """
        try:
            order = order_data["order"]
            product = order["product"]
            customer = order["customer"]
            
            # Extract season info if available
            season_start_date = "Unknown"
            if "refund_calculation" in order_data and order_data["refund_calculation"].get("season_start_date"):
                season_start_date = order_data["refund_calculation"]["season_start_date"]
            
            # Build inventory text
            inventory_text = self._build_inventory_text(order_data, product["title"], season_start_date)
            
            # Create Slack message blocks
            refund_type = refund_data.get("refund_type", "refund")
            refund_amount = refund_data.get("refund_amount", 0)
            
            order_url = self.get_order_url(order["orderId"], order["orderName"])
            
            # Main message text
            main_text = f"✅ *Request to provide a ${refund_amount:.2f} {refund_type} for Order {order_url} for {customer.get('email', 'Unknown')} has been processed by {user_name}*"
            
            if sheet_link:
                main_text += f"\n🔗 *<{sheet_link}|View Request in Google Sheets>*"
            
            main_text += f"\n{inventory_text}"
            
            # Create message blocks
            blocks = [
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": main_text
                    }
                },
                {"type": "divider"}
            ]
            
            # Send to Slack
            result = self._send_slack_message(
                channel_id=self.refunds_channel["channel_id"],
                text=f"✅ Refund processed for {order['orderName']}",
                blocks=blocks
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending refund notification to Slack: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def send_refund_request_notification(self, order_data: Dict[str, Any], refund_calculation: Dict[str, Any],
                                       requestor_info: Dict[str, Any], sheet_link: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a new refund request notification to Slack for approval
        Matches the format from getSlackMessageText in the Google Apps Script
        """
        try:
            logger.info(f"🔍 Slack service received order_data: {json.dumps(order_data, indent=2)}")
            
            order = order_data["order"]
            product = order["product"]
            customer = order["customer"]
            
            # Extract requestor info
            requestor_name = requestor_info["name"]
            requestor_email = requestor_info["email"]
            refund_type = requestor_info["refund_type"]
            request_notes = requestor_info["notes"]
            
            # Format request type text
            request_type_text = "💵 Refund back to original form of payment" if refund_type == "refund" else "🎟️ Store Credit to use toward a future order"
            
            # Optional request notes
            optional_request_notes = f"*Notes provided by requestor*: {request_notes}\n\n" if request_notes else ""
            
            # Get sport group mention
            sport_mention = self.get_sport_group_mention(product["title"])
            
            # Format timestamps using the new utility functions
            from utils.date_utils import format_date_and_time
            current_time = format_date_and_time(datetime.now())
            order_created_time = format_date_and_time(order.get("orderCreatedAt", datetime.now()))
            
            # URLs
            order_url = self.get_order_url(order["orderId"], order["orderName"])
            product_url = self.get_product_url(product["productId"])
            
            # Check if refund calculation failed (missing season info)
            if not refund_calculation.get("success"):
                logger.warning(f"Refund calculation failed for order {order['orderName']}: {refund_calculation.get('message', 'Unknown error')}")
                
                # Fallback refund amount calculation (90% for refund, 95% for credit)
                total_paid = order.get("totalAmountPaid", 0)
                fallback_refund_amount = total_paid * 0.9 if refund_type == "refund" else total_paid * 0.95
                
                return self._send_fallback_season_info_message(
                    requestor_name=requestor_name,
                    requestor_email=requestor_email,
                    refund_type=refund_type,
                    request_notes=request_notes,
                    order=order,
                    product=product,
                    total_paid=total_paid,
                    fallback_refund_amount=fallback_refund_amount,
                    sheet_link=sheet_link,
                    sport_mention=sport_mention,
                    current_time=current_time,
                    order_url=order_url,
                    request_type_text=request_type_text,
                    optional_request_notes=optional_request_notes
                )
            
            # Build refund calculation text
            refund_amount = refund_calculation.get("refund_amount", 0)
            refund_text = refund_calculation.get("refund_text", "")
            season_start_date = refund_calculation.get("season_start_date", "Unknown")
            
            # Header and body text
            header_text = "📌 *New Refund Request!*\n\n"
            
            body_text = f"{header_text}"
            body_text += f"*Request Type*: {request_type_text}\n\n"
            body_text += f"📧 *Requested by:* {requestor_name['first']} {requestor_name['last']} ({requestor_email})\n\n"
            body_text += f"*Request Submitted At*: {current_time}\n\n"
            body_text += f"*Order Number:* {order_url}\n\n"
            body_text += f"*Order Created At:* {order_created_time}\n\n"
            body_text += f"*Sport/Season/Day:* <{product_url}|{product['title']}>\n\n"
            body_text += f"*Season Start Date*: {season_start_date}\n\n"
            body_text += f"*Total Paid:* ${order.get('totalAmountPaid', 0):.2f}\n\n"
            body_text += f"{refund_text}\n\n"
            body_text += optional_request_notes
            
            if sheet_link:
                body_text += f"\n \n \n 🔗 *<{sheet_link}|View Request in Google Sheets>*\n\n"
            
            body_text += f"*Attn*: {sport_mention}"
            
            # Create action buttons matching the Google Apps Script format
            action_buttons = [
                self._create_confirm_button(order["orderId"], order["orderName"], requestor_name, requestor_email, refund_type, refund_amount),
                self._create_refund_different_amount_button(order["orderId"], order["orderName"], requestor_name, requestor_email, refund_type, refund_amount),
                self._create_cancel_button(order["orderName"])
            ]
            
            # Remove any None buttons
            action_buttons = [btn for btn in action_buttons if btn is not None]
            
            blocks = [
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": body_text}
                },
                {
                    "type": "actions",
                    "elements": action_buttons
                },
                {"type": "divider"}
            ]
            
            result = self._send_slack_message(
                channel_id=self.refunds_channel["channel_id"],
                text=header_text,
                blocks=blocks
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending refund request notification to Slack: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def send_error_notification(self, error_message: str, order_number: Optional[str] = None, 
                              context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send error notifications to Slack"""
        try:
            text = f"❌ **BARS API Error**\n"
            if order_number:
                text += f"**Order:** {order_number}\n"
            text += f"**Error:** {error_message}"
            
            if context:
                text += f"\n**Context:** ```{json.dumps(context, indent=2)}```"
            
            blocks = [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": text}
                }
            ]
            
            result = self._send_slack_message(
                channel_id=self.refunds_channel["channel_id"],
                text=f"❌ API Error{f' - Order {order_number}' if order_number else ''}",
                blocks=blocks
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending error notification to Slack: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _build_inventory_text(self, order_data: Dict[str, Any], product_title: str, season_start_date: str) -> str:
        """Build the inventory status text for Slack messages"""
        try:
            inventory_summary = order_data.get("inventory_summary", {})
            
            if not inventory_summary.get("success"):
                return "📦 *Inventory information unavailable*"
            
            inventory_list = inventory_summary.get("inventory_list", {})
            inventory_order = ["veteran", "early", "open", "waitlist"]
            
            product_url = self.get_product_url(order_data["order"]["product"]["productId"])
            
            text = f"📦 *Season Start Date for <{product_url}|{product_title}> is {season_start_date}.*\n*Current Inventory:*\n"
            
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
            logger.error(f"Error building inventory text: {str(e)}")
            return "📦 *Error fetching inventory information*"
    
    def _create_confirm_button(self, order_id: str, order_name: str, requestor_name: Dict[str, str], 
                             requestor_email: str, refund_type: str, refund_amount: float) -> Dict[str, Any]:
        """Create the confirm/approve button matching Google Apps Script format"""
        formatted_amount = int(refund_amount) if refund_amount == int(refund_amount) else f"{refund_amount:.2f}"
        
        button_text = f"✅ Process ${formatted_amount} Refund" if refund_type == "refund" else f"✅ Issue ${formatted_amount} Store Credit"
        
        return {
            "type": "button",
            "text": {"type": "plain_text", "text": button_text},
            "action_id": "approve_refund",
            "value": f"rawOrderNumber={order_name}|orderId={order_id}|refundAmount={refund_amount}",
            "style": "primary",
            "confirm": {
                "title": {"type": "plain_text", "text": "Confirm Approval"},
                "text": {"type": "plain_text", "text": f"You are about to issue {requestor_name['first']} {requestor_name['last']} a {refund_type} for ${formatted_amount}. Proceed?"},
                "confirm": {"type": "plain_text", "text": "Yes, confirm"},
                "deny": {"type": "plain_text", "text": "Cancel"}
            }
        }
    
    def _create_refund_different_amount_button(self, order_id: str, order_name: str, requestor_name: Dict[str, str], 
                                             requestor_email: str, refund_type: str, refund_amount: float) -> Dict[str, Any]:
        """Create the custom amount button matching Google Apps Script format"""
        button_text = "✏️ Process custom Refund amt" if refund_type == "refund" else "✏️ Issue custom Store Credit amt"
        
        return {
            "type": "button",
            "text": {"type": "plain_text", "text": button_text},
            "action_id": "refund_different_amount",
            "value": f"orderId={order_id}|refundAmount={refund_amount}|rawOrderNumber={order_name}"
        }
    
    def _create_cancel_button(self, order_name: str) -> Dict[str, Any]:
        """Create the cancel button matching Google Apps Script format"""
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

    def _send_fallback_season_info_message(self, requestor_name: Dict[str, str], requestor_email: str, 
                                         refund_type: str, request_notes: str, order: Dict[str, Any],
                                         product: Dict[str, Any], total_paid: float, fallback_refund_amount: float,
                                         sheet_link: Optional[str], sport_mention: str, current_time: str,
                                         order_url: str, request_type_text: str, optional_request_notes: str) -> Dict[str, Any]:
        """Send fallback message when season info cannot be parsed"""

        request_type_text = "💵 Refund back to original form of payment" if refund_type == "refund" else "🎟️ Store Credit to use toward a future order"
        current_time = format_date_and_time(datetime.now())
        order_created_time = format_date_and_time(order.get("orderCreatedAt", datetime.now()))
        
        header_text = "📌 *New Refund Request!*\n\n"
        fallback_text = f"{header_text}"

        fallback_text += f"⚠️ *Order Found in Shopify but Missing Season Info (or Product Is Not a Regular Season)*\n\n"
        fallback_text += f"*Request Type*: {request_type_text}\n\n"
        fallback_text += f"*Requested by*: {requestor_name['first']} {requestor_name['last']} ({requestor_email})\n\n"
        fallback_text += f"*Request Submitted At*: {current_time}\n\n"
        fallback_text += f"*Order Number Provided*: {order_url}\n\n"
        fallback_text += f"*Order Created At:* {order_created_time}\n\n"
        fallback_text += f"*Product Title*: {product['title']}\n\n"
        fallback_text += f"*Total Paid:* ${total_paid:.2f}\n\n"
        fallback_text += f"⚠️ *Could not parse 'Season Dates' from this order's description (in order to calculate a refund amount).*\n\n"
        fallback_text += f"Please verify the product and either contact the requestor or process anyway.\n\n"
        fallback_text += optional_request_notes
        
        if sheet_link:
            fallback_text += f"\n \n 🔗 *<{sheet_link}|View Request in Google Sheets>*\n\n"
        
        fallback_text += f"*Attn*: {sport_mention}"
        
        # Create action buttons with fallback amount
        action_buttons = [
            self._create_confirm_button(order["orderId"], order["orderName"], requestor_name, requestor_email, refund_type, fallback_refund_amount),
            self._create_refund_different_amount_button(order["orderId"], order["orderName"], requestor_name, requestor_email, refund_type, fallback_refund_amount),
            self._create_cancel_button(order["orderName"])
        ]
        
        # Remove any None buttons
        action_buttons = [btn for btn in action_buttons if btn is not None]
        
        blocks = [
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": fallback_text}
            },
            {
                "type": "actions",
                "elements": action_buttons
            },
            {"type": "divider"}
        ]
        
        return self._send_slack_message(
            channel_id=self.refunds_channel["channel_id"],
            text="⚠️ *Refund Request Missing Season Info*",
            blocks=blocks
        )

    def send_order_not_found_error(self, requestor_name: Dict[str, str], requestor_email: str, 
                                  refund_type: str, request_notes: str, raw_order_number: str,
                                  sheet_link: Optional[str] = None) -> Dict[str, Any]:
        """Send error message when order is not found in Shopify"""
        
        request_type_text = "💵 Refund back to original form of payment" if refund_type == "refund" else "🎟️ Store Credit to use toward a future order"
        optional_request_notes = f"*Notes provided by requestor*: {request_notes}\n" if request_notes else ""
        
        current_time = format_date_and_time(datetime.now())
        
        error_text = f"❌ *Error with Refund Request - Order Not Found in Shopify*\n\n"
        error_text += f"*Request Type*: {request_type_text}\n\n"
        error_text += f"*Request Submitted At*: {current_time}\n\n"
        error_text += f"📧 *Requested by:* {requestor_name['first']} {requestor_name['last']} ({requestor_email})\n\n"
        error_text += f"🔎 *Order Number Provided:* {raw_order_number} - this order cannot be found in Shopify\n\n"
        error_text += optional_request_notes
        error_text += f"\n\n📩 *The requestor has been emailed to please provide correct order info. No action needed at this time.*\n"
        
        if sheet_link:
            error_text += f"\n \n 🔗 *<{sheet_link}|View Request in Google Sheets>*\n\n"
        
        blocks = [
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": error_text}
            },
            {"type": "divider"}
        ]
        
        return self._send_slack_message(
            channel_id=self.refunds_channel["channel_id"],
            text="❌ *Refund Request Submitted with Error*",
            blocks=blocks
        )

    def send_email_mismatch_error(self, requestor_name: Dict[str, str], requestor_email: str, 
                                 refund_type: str, request_notes: str, order: Dict[str, Any],
                                 order_customer_email: str, sheet_link: Optional[str] = None) -> Dict[str, Any]:
        """Send error message when email doesn't match order customer email"""
        
        request_type_text = "💵 Refund back to original form of payment" if refund_type == "refund" else "🎟️ Store Credit to use toward a future order"
        optional_request_notes = f"*Notes provided by requestor*: {request_notes}\n\n" if request_notes else ""
        
        current_time = format_date_and_time(datetime.now())
        
        order_url = self.get_order_url(order["orderId"], order["orderName"])
        
        error_text = f"❌ *Error with Refund Request - Email provided did not match order*\n\n"
        error_text += f"*Request Type*: {request_type_text}\n\n"
        error_text += f"*Request Submitted At*: {current_time}\n\n"
        error_text += f"📧 *Requested by:* {requestor_name['first']} {requestor_name['last']} ({requestor_email})\n\n"
        error_text += f"*Email Associated with Order:* {order_customer_email}\n\n"
        error_text += f"*Order Number:* {order_url}\n\n"
        error_text += optional_request_notes
        error_text += f"📩 *The requestor has been emailed to please provide correct order info. No action needed at this time.*\n"
        
        if sheet_link:
            error_text += f"\n \n 🔗 *<{sheet_link}|View Request in Google Sheets>*\n"
        
        blocks = [
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": error_text}
            },
            {"type": "divider"}
        ]
        
        return self._send_slack_message(
            channel_id=self.refunds_channel["channel_id"],
            text="❌ *Refund Request Submitted with Error*",
            blocks=blocks
        )

    def _send_slack_message(self, channel_id: str, text: str, blocks: Optional[List[Dict[str, Any]]] = None,
                          thread_ts: Optional[str] = None) -> Dict[str, Any]:
        """Send a message to Slack using the Web API"""
        try:
            url = "https://slack.com/api/chat.postMessage"
            
            payload = {
                "channel": channel_id,
                "text": text
            }
            
            if blocks:
                payload["blocks"] = blocks
            
            if thread_ts:
                payload["thread_ts"] = thread_ts
            
            headers = {
                "Authorization": f"Bearer {self.refunds_channel['bearer_token']}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("ok"):
                logger.info(f"✅ Slack message sent successfully to {channel_id}")
                return {
                    "success": True,
                    "ts": response_data.get("ts"),
                    "channel": response_data.get("channel")
                }
            else:
                error_msg = response_data.get("error", "Unknown Slack API error")
                logger.error(f"❌ Slack API error: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"❌ Error sending Slack message: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def update_slack_message(self, channel_id: str, message_ts: str, text: str, 
                           blocks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Update an existing Slack message"""
        try:
            url = "https://slack.com/api/chat.update"
            
            payload = {
                "channel": channel_id,
                "ts": message_ts,
                "text": text
            }
            
            if blocks:
                payload["blocks"] = blocks
            
            headers = {
                "Authorization": f"Bearer {self.refunds_channel['bearer_token']}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("ok"):
                logger.info(f"✅ Slack message updated successfully")
                return {"success": True, "ts": response_data.get("ts")}
            else:
                error_msg = response_data.get("error", "Unknown Slack API error")
                logger.error(f"❌ Slack update error: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"❌ Error updating Slack message: {str(e)}")
            return {"success": False, "error": str(e)} 