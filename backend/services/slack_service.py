import requests
import json
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
from config import settings

logger = logging.getLogger(__name__)

class SlackService:
    def __init__(self):
        # Slack configuration from the original Google Apps Script
        self.refunds_channel = {
            "name": "#refunds",
            "channel_id": "C08J1EN7SFR",
            "bearer_token": settings.slack_refunds_bot_token
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
                               sheet_link: str = None, user_name: str = "API") -> Dict[str, Any]:
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
                                       requestor_info: Dict[str, Any], sheet_link: str = None) -> Dict[str, Any]:
        """
        Send a new refund request notification to Slack for approval
        This would be used when a new refund request comes in
        """
        try:
            logger.info(f"🔍 Slack service received order_data: {json.dumps(order_data, indent=2)}")
            
            order = order_data["order"]
            logger.info(f"🔍 Extracted order: {json.dumps(order, indent=2)}")
            
            product = order["product"]
            customer = order["customer"]
            
            # Get sport group mention
            sport_mention = self.get_sport_group_mention(product["title"])
            
            # Build the approval message
            refund_amount = refund_calculation.get("refund_amount", 0)
            refund_text = refund_calculation.get("refund_text", "")
            
            order_url = self.get_order_url(order["orderId"], order["orderName"])
            product_url = self.get_product_url(product["productId"])
            
            main_text = f"{sport_mention} New refund request for {order_url}\n"
            main_text += f"**Customer:** {customer.get('email', 'Unknown')}\n"
            main_text += f"**Product:** <{product_url}|{product['title']}>\n"
            main_text += f"**Amount Paid:** ${order.get('totalAmountPaid', 0):.2f}\n"
            main_text += f"**{refund_text}**"
            
            if sheet_link:
                main_text += f"\n🔗 *<{sheet_link}|View Request in Google Sheets>*"
            
            # Create approval buttons (these would need webhook handling)
            action_buttons = [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": f"✅ Process ${refund_amount:.2f} Refund"},
                    "action_id": "approve_refund",
                    "value": f"order_id={order['orderId']}|amount={refund_amount}",
                    "style": "primary"
                },
                {
                    "type": "button", 
                    "text": {"type": "plain_text", "text": "❌ Deny"},
                    "action_id": "deny_refund",
                    "value": f"order_id={order['orderId']}",
                    "style": "danger"
                }
            ]
            
            blocks = [
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": main_text}
                },
                {
                    "type": "actions",
                    "elements": action_buttons
                },
                {"type": "divider"}
            ]
            
            result = self._send_slack_message(
                channel_id=self.refunds_channel["channel_id"],
                text=f"New refund request for {order['orderName']}",
                blocks=blocks
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending refund request notification to Slack: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def send_error_notification(self, error_message: str, order_number: str = None, 
                              context: Dict[str, Any] = None) -> Dict[str, Any]:
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
    
    def _send_slack_message(self, channel_id: str, text: str, blocks: List[Dict[str, Any]] = None,
                          thread_ts: str = None) -> Dict[str, Any]:
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
                           blocks: List[Dict[str, Any]] = None) -> Dict[str, Any]:
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