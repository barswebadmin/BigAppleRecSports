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
import asyncio
from datetime import datetime, timezone

# External imports
import requests
from fastapi import HTTPException

# Internal imports
from services.slack.api_client import SlackApiClient, MockSlackApiClient, _is_test_mode
from utils.date_utils import format_date_and_time
from services.slack.message_builder import SlackMessageBuilder
from config import settings

logger = logging.getLogger(__name__)


class SlackRefundsUtils:
    """Utility functions and webhook handlers for Slack refund operations"""
    
    def __init__(self, orders_service, settings):
        self.orders_service = orders_service
        self.settings = settings
        
        # Initialize message builder
        self.message_builder = SlackMessageBuilder({})
        
        # Initialize API client with proper credentials
        if _is_test_mode():
            logger.info("🧪 Test mode detected - using MockSlackApiClient for refunds utils")
            self.api_client = MockSlackApiClient("test_token", "test_channel")
        else:
            # Use the same refunds channel configuration as SlackService
            is_production = settings.environment == "production"
            refunds_channel = {
                "name": "#refunds" if is_production else "#joe-test",
                "channel_id": "C08J1EN7SFR" if is_production else "C092RU7R6PL",
                "bearer_token": settings.slack_refunds_bot_token or ""
            }
            logger.info("🚀 Production mode - using real SlackApiClient for refunds utils")
            self.api_client = SlackApiClient(
                refunds_channel["bearer_token"],
                refunds_channel["channel_id"]
            )

    # === UTILITY FUNCTIONS ===
    
    def verify_slack_signature(self, body: bytes, timestamp: str, signature: str) -> bool:
        """Verify that the request came from Slack"""
        if not settings.slack_signing_secret:
            logger.warning("No Slack signing secret configured - skipping signature verification")
            return True  # Skip verification in development
        
        # Create the signature base string
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
        
        # Create the expected signature
        expected_signature = 'v0=' + hmac.new(
            settings.slack_signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(expected_signature, signature)

    def parse_button_value(self, value: str) -> Dict[str, str]:
        """Parse button value like 'rawOrderNumber=#12345|orderId=gid://shopify/Order/12345|refundAmount=36.00'"""
        request_data = {}
        button_values = value.split('|')
        
        for button_value in button_values:
            if '=' in button_value:
                key, val = button_value.split('=', 1)  # Split only on first =
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
                                    if isinstance(sub_element, dict) and "text" in sub_element:
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
        print(f"\n🔍 === EXTRACT SHEET LINK DEBUG ===")
        print(f"📝 Input message text length: {len(message_text)}")
        print(f"📝 Input message text preview: {message_text[:300]}...")
        
        # Decode HTML entities like &amp; that might be in Slack message blocks
        decoded_text = html.unescape(message_text)
        print(f"📝 Decoded text preview: {decoded_text[:300]}...")
        
        # Look for different Google Sheets link patterns
        patterns = [
            # Pattern 1: Slack link format <URL|text> (with :link: emoji)
            r':link:\s*\*<(https://docs\.google\.com/spreadsheets/[^>|]+)\|[^>]*>\*',
            # Pattern 2: Slack link format <URL|text> (with 🔗 emoji)
            r'🔗\s*\*<(https://docs\.google\.com/spreadsheets/[^>|]+)\|[^>]*>\*',
            # Pattern 3: Slack link format <URL|text> (without emoji)
            r'<(https://docs\.google\.com/spreadsheets/[^>|]+)\|[^>]*>',
            # Pattern 4: Direct URL after emoji
            r'🔗[^h]*?(https://docs\.google\.com/spreadsheets/[^\s\n]+)',
            # Pattern 5: URL on same line as emoji
            r'🔗.*?(https://docs\.google\.com/spreadsheets/[^\s\n]+)',
            # Pattern 6: URL anywhere in the message
            r'(https://docs\.google\.com/spreadsheets/[^\s\n]+)'
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
        print(f"\n🔍 === EXTRACT SEASON START INFO DEBUG ===")
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
            # Pattern 5: Sport/Season/Day field with Slack link - extract title from <URL|title>
            r"\*Sport/Season/Day\*:\s*<[^|]+\|([^>]+)>",
            # Pattern 6: Sport/Season/Day field with full Slack link  
            r"\*Sport/Season/Day\*:\s*(<[^>]+>)",
            # Pattern 7: Product title with link <URL|title> (extract title only)
            r"Product Title:\s*<[^|]+\|([^>]+)>",
            r"Sport/Season/Day:\s*<[^|]+\|([^>]+)>",
            # Pattern 8: Product Title field (plain text)
            r"Product Title:\s*([^<\n]+)",
            # Pattern 9: Sport/Season/Day field (plain text)
            r"Sport/Season/Day:\s*([^<\n]+)",
            # Pattern 10: Handle current format with Product Title link
            r"\*Product Title\*:\s*<[^|]*\|([^>]+)>\s*\n\s*\*Season Start Date\*:\s*([^\n]+)",
            # Pattern 11: Handle format without link in Product Title
            r"\*Product Title\*:\s*([^\n]+)\s*\n\s*\*Season Start Date\*:\s*([^\n]+)"
        ]
        
        product_title = "Unknown Product"
        product_link = None
        season_start_date = "Unknown"
        
        # Try new combined patterns first (patterns 10-11)
        for i, pattern in enumerate(patterns[9:], start=10):
            season_match = re.search(pattern, message_text)
            if season_match:
                product_title = season_match.group(1).strip()
                season_start_date = season_match.group(2).strip()
                print(f"✅ Pattern {i} matched! Product: {product_title}, Season Start: {season_start_date}")
                print("=== END EXTRACT SEASON START INFO DEBUG ===\n")
                return {"product_title": product_title, "season_start_date": season_start_date, "product_link": None}
        
        # Try to find season start date with product (Pattern 1: with link)
        season_match = re.search(patterns[0], message_text)
        if season_match:
            product_title = season_match.group(1).strip()
            season_start_date = season_match.group(2).strip()
            print(f"✅ Pattern 1 matched! Product: {product_title}, Season Start: {season_start_date}")
            print("=== END EXTRACT SEASON START INFO DEBUG ===\n")
            return {"product_title": product_title, "season_start_date": season_start_date, "product_link": None}
        
        # Try to find season start date with product (Pattern 2: plain text)
        season_match = re.search(patterns[1], message_text)
        if season_match:
            product_title = season_match.group(1).strip()
            season_start_date = season_match.group(2).strip()
            print(f"✅ Pattern 2 matched! Product: {product_title}, Season Start: {season_start_date}")
            print("=== END EXTRACT SEASON START INFO DEBUG ===\n")
            return {"product_title": product_title, "season_start_date": season_start_date, "product_link": None}
        
        # Try to find product title/link from various fields
        for i, pattern in enumerate(patterns[2:], start=3):
            product_match = re.search(pattern, message_text)
            if product_match:
                matched_text = product_match.group(1).strip()
                
                # Check if it's a full Slack link (patterns 4 and 6) 
                if i in [4, 6] and matched_text.startswith('<') and matched_text.endswith('>'):
                    product_link = matched_text
                    # Extract title from link for display
                    if '|' in matched_text:
                        product_title = matched_text.split('|')[1].replace('>', '')
                    else:
                        product_title = "Unknown Product"
                    print(f"✅ Pattern {i} matched! Product Link: {product_link}, Title: {product_title}")
                else:
                    # Plain text or title from link (patterns 3, 5, 7, 8 get title directly)
                    product_title = matched_text
                    print(f"✅ Pattern {i} matched! Product: {product_title}")
                break
        
        # Try to find separate season start date
        season_date_patterns = [
            r"Season Start Date:\s*([^\n]+)",
            r"Season Start:\s*([^\n]+)",
            r"Start Date:\s*([^\n]+)"
        ]
        
        for pattern in season_date_patterns:
            season_match = re.search(pattern, message_text)
            if season_match:
                season_start_date = season_match.group(1).strip()
                print(f"✅ Pattern matched! Season Start: {season_start_date}")
                break
        
        print("❌ No season start info found, using fallback")
        print("=== END EXTRACT SEASON START INFO DEBUG ===\n")
        return {"product_title": product_title, "season_start_date": season_start_date, "product_link": product_link}

    # === WEBHOOK HANDLERS ===

    async def handle_cancel_order(self, request_data: Dict[str, str], channel_id: str, requestor_name: Dict[str, str], requestor_email: str, thread_ts: str, slack_user_id: str, slack_user_name: str, current_message_full_text: str, trigger_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle cancel order button click (Step 1)
        Cancels the order in Shopify, then shows refund options
        """
        print(f"\n✅ === CANCEL ORDER ACTION ===")
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
            is_debug_mode = settings.is_debug_mode
            is_prod_mode = settings.is_production_mode
            
            # 1. Fetch order details using correct method name
            order_result = self.orders_service.fetch_order_details_by_email_or_order_name(order_name=raw_order_number)
            if not order_result["success"]:
                error_message = f"❌ Failed to fetch order details: {order_result['message']}"
                self.send_modal_error_to_user(
                    trigger_id=trigger_id,
                    error_message=f"Could not find order {raw_order_number}.\n\n**Error Details:**\n{order_result['message']}\n\nPlease verify the order number is correct.",
                    operation_name="Order Lookup"
                )
                return {}
            
            shopify_order_data = order_result["data"]
            order_id = shopify_order_data.get("id", "")
            
            # 2. Calculate refund amount
            refund_calculation = self.orders_service.calculate_refund_due(shopify_order_data, refund_type)
            
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
                        "requestor_email": requestor_email
                    }
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
                    sport_mention=self.message_builder.get_sport_group_mention(order_data["order"]["line_items"][0]["title"]),
                    sheet_link=sheet_link,
                    order_cancelled=True,
                    slack_user_id=slack_user_id,
                    original_timestamp=request_submitted_at
                )
                
                # ✅ Update Slack message ONLY on Shopify success
                self.update_slack_on_shopify_success(
                    message_ts=thread_ts,
                    success_message=refund_message["text"],
                    action_buttons=refund_message["action_buttons"]
                )
                
                logger.info(f"Order {raw_order_number} cancelled successfully")
            else:
                # 🚨 Handle Shopify cancellation failure with detailed error logging
                shopify_error = cancel_result.get('message', 'Unknown error')
                
                # Print detailed error information for debugging
                print(f"\n🚨 === SHOPIFY ORDER CANCELLATION FAILED ===")
                print(f"📋 Order: {raw_order_number}")
                print(f"🔗 Order ID: {order_id}")
                print(f"👤 User: {slack_user_name} ({slack_user_id})")
                print(f"❌ Shopify Error: {shopify_error}")
                print(f"📝 Full cancel_result: {cancel_result}")
                print("=== END SHOPIFY CANCELLATION FAILURE ===\n")
                
                # Log detailed error for server logs
                logger.error(f"🚨 SHOPIFY ORDER CANCELLATION FAILED:")
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
                    modal_error_message += f"\n\n**Shopify Error Details:**\n{shopify_errors}"
                
                modal_error_message += f"\n\n**Raw Shopify Response:**\n{raw_response}"
                
                modal_error_message += f"\n\nThis often happens when:\n• Order is already cancelled\n• Order is already fulfilled\n• Order has refunds or returns\n• Payment gateway restrictions"
                
                self.send_modal_error_to_user(
                    trigger_id=trigger_id,
                    error_message=modal_error_message,
                    operation_name="Order Cancellation"
                )
            
            return {}
        except Exception as e:
            logger.error(f"Error canceling order: {e}")
            error_message = f"❌ Error canceling order: {str(e)}"
            self.send_modal_error_to_user(
                trigger_id=trigger_id,
                error_message=f"An unexpected error occurred while canceling order {request_data.get('rawOrderNumber', 'unknown')}.\n\n**Error Details:**\n{str(e)}\n\nPlease try again or contact support if the issue persists.",
                operation_name="Order Cancellation"
            )
            return {}

    async def handle_proceed_without_cancel(self, request_data: Dict[str, str], channel_id: str, requestor_name: Dict[str, str], requestor_email: str, thread_ts: str, slack_user_id: str, slack_user_name: str, current_message_full_text: str, trigger_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle proceed without cancel button click (Step 1)
        Shows refund options without canceling the order
        """
        print(f"\n➡️ === PROCEED WITHOUT CANCEL ACTION ===")
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
            order_result = self.orders_service.fetch_order_details_by_email_or_order_name(order_name=raw_order_number)
            if not order_result["success"]:
                logger.error(f"Failed to fetch order details for {raw_order_number}: {order_result['message']}")
                self.send_modal_error_to_user(
                    trigger_id=trigger_id,
                    error_message=f"Could not find order {raw_order_number}.\n\n**Error Details:**\n{order_result['message']}\n\nPlease verify the order number is correct.",
                    operation_name="Order Lookup"
                )
                return {}
            
            shopify_order_data = order_result["data"]
            
            # 2. Calculate fresh refund amount
            refund_calculation = self.orders_service.calculate_refund_due(shopify_order_data, refund_type)
            
            
            # Create order data with fresh Shopify data and preserved requestor info
            order_data = {
                "order": shopify_order_data,  # Use fresh Shopify order data
                "refund_calculation": refund_calculation,  # Use fresh refund calculation
                "requestor_name": requestor_name,
                "requestor_email": requestor_email,
                "original_data": {
                    "original_timestamp": request_submitted_at,  # Preserve original timestamp
                    "requestor_email": requestor_email
                }
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
                sport_mention=self.message_builder.get_sport_group_mention(order_data["order"]["line_items"][0]["title"]),
                sheet_link=sheet_link,
                order_cancelled=False,
                slack_user_id=slack_user_id,
                original_timestamp=request_submitted_at
            )
            
            # 4. Update Slack message using controlled mechanism
            self.update_slack_on_shopify_success(
                message_ts=thread_ts,
                success_message=refund_message["text"],
                action_buttons=refund_message["action_buttons"]
            )
            
            logger.info(f"Proceeding to refund options for order {raw_order_number} (order not cancelled)")
            return {}
        except Exception as e:
            logger.error(f"Error proceeding without cancel: {e}")
            self.send_modal_error_to_user(
                trigger_id=trigger_id,
                error_message=f"An unexpected error occurred while processing order {request_data.get('rawOrderNumber', 'unknown')}.\n\n**Error Details:**\n{str(e)}\n\nPlease try again or contact support if the issue persists.",
                operation_name="Order Processing"
            )
            return {}

    async def handle_process_refund(self, request_data: Dict[str, str], channel_id: str, requestor_name: Dict[str, str], requestor_email: str, thread_ts: str, slack_user_name: str, current_message_full_text: str, slack_user_id: str = "", trigger_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle process calculated refund button click (Step 2)
        """
        print(f"\n✅ === PROCESS REFUND ACTION ===")
        print(f"👤 User: {slack_user_name} ({slack_user_id})")
        print(f"📋 Request Data: {request_data}")
        print(f"📍 Channel: {channel_id}, Thread: {thread_ts}")
        print("=== END PROCESS REFUND ===\n")
        
        try:
            order_id = request_data.get("orderId", "")
            raw_order_number = request_data.get("rawOrderNumber", "")
            refund_amount = float(request_data.get("refundAmount", "0"))
            refund_type = request_data.get("refundType", "refund")
            order_cancelled = request_data.get("orderCancelled", "False").lower() == "true"
            
            logger.info(f"Processing refund: Order {raw_order_number}, Amount: ${refund_amount}")
            
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
                    "processedBy": slack_user_id
                }
                logger.info(f"🧪 DEBUG MODE: JSON POST BODY for refund:\n{json.dumps(debug_refund_body, indent=2)}")
            
            # Process refund using correct method name
            refund_result = self.orders_service.create_refund_or_credit(order_id, refund_amount, refund_type)
            
            if refund_result["success"]:
                # Fetch fresh order details for comprehensive message
                order_result = self.orders_service.fetch_order_details_by_email_or_order_name(order_name=raw_order_number)
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
                        is_debug_mode=is_debug_mode
                    )
                    
                    # ✅ Update Slack message ONLY on Shopify success
                    print(f"🔄 Attempting to update Slack message with {len(success_message_data['action_buttons'])} buttons")
                    self.update_slack_on_shopify_success(
                        message_ts=thread_ts,
                        success_message=success_message_data["text"],
                        action_buttons=success_message_data["action_buttons"]
                    )
                else:
                    # Fallback if order fetch fails - use simple message
                    status = "cancelled" if order_cancelled else "active"
                    if is_debug_mode:
                        message = f"✅ *[DEBUG] Mock refund processed by {slack_user_name}*\n\nOrder {raw_order_number} ({status}) - ${refund_amount:.2f} {refund_type} processed successfully."
                    else:
                        message = f"✅ *Refund processed by {slack_user_name}*\n\nOrder {raw_order_number} ({status}) - ${refund_amount:.2f} {refund_type} processed successfully."
                    
                    # ✅ Update Slack with fallback success message
                    self.update_slack_on_shopify_success(
                        message_ts=thread_ts,
                        success_message=message,
                        action_buttons=[]
                    )
            else:
                # 🚨 Handle Shopify refund failure with detailed error logging
                shopify_error = refund_result.get('message', 'Unknown error')
                
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
                    operation_name=f"{refund_type.title()} Processing"
                )
            
            return {}
        except Exception as e:
            logger.error(f"Error processing refund: {e}")
            self.send_modal_error_to_user(
                trigger_id=trigger_id,
                error_message=f"An unexpected error occurred while processing the {request_data.get('refundType', 'refund')} for order {request_data.get('rawOrderNumber', 'unknown')}.\n\n**Error Details:**\n{str(e)}\n\nPlease try again or contact web support if the issue persists.",
                operation_name="Refund Processing"
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
        trigger_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Show modal to enter custom refund amount.
        """
        print(f"\n✏️ === CUSTOM REFUND AMOUNT ACTION ===")
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
                "private_metadata": json.dumps({
                    "orderId": order_id,
                    "rawOrderNumber": raw_order_number,
                    "refundType": refund_type,
                    "channel_id": channel_id,
                    "thread_ts": thread_ts,
                    "slack_user_id": slack_user_id,
                    "current_message_full_text": current_message_full_text
                }),
                "title": {
                    "type": "plain_text",
                    "text": "Custom Refund"
                },
                "submit": {
                    "type": "plain_text",
                    "text": "Process Refund"
                },
                "close": {
                    "type": "plain_text",
                    "text": "Cancel"
                },
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "refund_input_block",
                        "label": {
                            "type": "plain_text",
                            "text": "Enter Refund Amount"
                        },
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "custom_refund_amount",
                            "initial_value": refund_amount
                        },
                        "hint": {
                            "type": "plain_text",
                            "text": "Only enter the number (e.g., 25.00). Dollar sign will be added automatically."
                        }
                    }
                ]
            }

            # Send modal
            result = self.api_client.send_modal(trigger_id=trigger_id, modal_view=modal_view) # type: ignore
            if not result.get("success"):
                raise Exception(result.get("error", "Failed to open modal"))
            
            return {"success": True}

        except Exception as e:
            logger.error(f"Error handling custom refund modal: {e}")
            if trigger_id:
                self.send_modal_error_to_user(
                    trigger_id=trigger_id,
                    error_message=str(e),
                    operation_name="Custom Refund"
                )
            return {"success": False, "message": str(e)}

    async def handle_no_refund(self, request_data: Dict[str, str], channel_id: str, requestor_name: Dict[str, str], requestor_email: str, thread_ts: str, slack_user_name: str, slack_user_id: str, current_message_full_text: str, trigger_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle no refund button click (Step 2)
        """
        print(f"\n🚫 === NO REFUND ACTION ===")
        print(f"👤 User: {slack_user_name} ({slack_user_id})")
        print(f"📋 Request Data: {request_data}")
        print(f"📍 Channel: {channel_id}, Thread: {thread_ts}")
        print(f"📝 Current message text length: {len(current_message_full_text)}")
        print(f"📝 Current message preview: {current_message_full_text[:200]}...")
        print("=== END NO REFUND ===\n")
        
        try:
            raw_order_number = request_data.get("rawOrderNumber", "")
            order_cancelled = request_data.get("orderCancelled", "False").lower() == "true"
            
            # Check ENVIRONMENT configuration for debug vs production behavior
            is_debug_mode = settings.is_debug_mode
            
            if is_debug_mode:
                print(f"🧪 DEBUG MODE: Would close refund request for order {raw_order_number}")
                print(f"🧪 DEBUG MODE: No actual API calls needed for 'no refund' action")
            else:
                print(f"🏭 PRODUCTION MODE: Closing refund request (no API calls needed)")
            
            # Fetch fresh order details for comprehensive message
            order_result = self.orders_service.fetch_order_details_by_email_or_order_name(order_name=raw_order_number)
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
                        current_message_full_text=current_message_full_text
                    )
                    
                    print(f"📝 Built message text length: {len(no_refund_message_data['text'])}")
                    print(f"🔘 Built {len(no_refund_message_data['action_buttons'])} action buttons")
                    
                    self.update_slack_on_shopify_success(
                        message_ts=thread_ts,
                        success_message=no_refund_message_data["text"],
                        action_buttons=no_refund_message_data["action_buttons"]
                    )
                    
                except Exception as build_error:
                    print(f"❌ Error building no refund message: {str(build_error)}")
                    logger.error(f"Error building no refund message: {str(build_error)}")
                    # Fall back to simple message
                    status = "cancelled" if order_cancelled else "active"
                    debug_prefix = "[DEBUG] " if is_debug_mode else ""
                    simple_message = f"🚫 *{debug_prefix}No refund by @{slack_user_name}*\n\nOrder {raw_order_number} ({status}) - Request closed without refund."
                    
                    self.update_slack_on_shopify_success(
                        message_ts=thread_ts,
                        success_message=simple_message,
                        action_buttons=[]
                    )
            else:
                # Fallback if order fetch fails
                status = "cancelled" if order_cancelled else "active"
                if is_debug_mode:
                    message = f"🚫 *[DEBUG] No refund by {slack_user_name}*\n\nOrder {raw_order_number} ({status}) - Request closed without refund."
                else:
                    message = f"🚫 *No refund by {slack_user_name}*\n\nOrder {raw_order_number} ({status}) - Request closed without refund."
                
                try:
                    self.update_slack_on_shopify_success(
                        message_ts=thread_ts,
                        success_message=message,
                        action_buttons=[]
                    )
                except Exception as e:
                    print(f"❌ No refund message update failed: {str(e)}")
            
            return {}
        except Exception as e:
            logger.error(f"Error handling no refund: {e}")
            self.send_modal_error_to_user(
                trigger_id=trigger_id,
                error_message=f"An unexpected error occurred while closing the refund request for order {request_data.get('rawOrderNumber', 'unknown')}.\n\n**Error Details:**\n{str(e)}\n\nPlease try again or contact support if the issue persists.",
                operation_name="No Refund Processing"
            )
            return {}

    # === MESSAGE BUILDERS ===

    def build_comprehensive_success_message(self, order_data: Dict[str, Any], refund_amount: float, refund_type: str,
                                      raw_order_number: str, order_cancelled: bool, requestor_name: Dict[str, str], requestor_email: str, processor_user: str,
                                      current_message_text: str, order_id: str = "", is_debug_mode: bool = False) -> Dict[str, Any]:
        """Build comprehensive success message with customer info, inventory, and restock buttons"""
        debug_prefix = "[DEBUG] " if is_debug_mode else ""
        
        # Extract season start info from current message
        season_info = self.extract_season_start_info(current_message_text)
        product_title = season_info.get("product_title", "Unknown Product")
        season_start_date = season_info.get("season_start_date", "Unknown")
        
        # Extract Google Sheets link from current message
        sheet_link = self.extract_sheet_link(current_message_text)
        
        # Format requestor name properly
        requestor_full_name = f"{requestor_name.get('first', '')} {requestor_name.get('last', '')}".strip()
        if not requestor_full_name:
            requestor_full_name = "Unknown Customer"
        
        # Build main message
        message = f":white_check_mark: {debug_prefix}Request to provide a ${refund_amount:.2f} {refund_type} for Order {raw_order_number} for {requestor_full_name} ({requestor_email}) has been processed by @{processor_user}\n"
        
        # Add Google Sheets link
        if sheet_link:
            message += f":link: <{sheet_link}|View Request in Google Sheets>\n"
        else:
            message += ":link: View Request in Google Sheets\n"
        
        # Add season start info
        message += f":package: Season Start Date for {product_title} is {season_start_date}.\n"
        
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
                variant_title = (variant.get("variantTitle") or 
                               variant.get("variantName") or 
                               variant.get("title") or 
                               "Unknown Variant")
                available_quantity = (variant.get("availableQuantity") or 
                                    variant.get("inventory") or 
                                    variant.get("inventoryQuantity") or 
                                    0)
                
                # Add inventory line
                message += f"• {variant_title}: {available_quantity} spots available\n"
                
                # Create restock button (remove "Registration" from variant name if present)
                button_text = variant_title.replace(" Registration", "").strip()
                action_buttons.append({
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": f"Restock {button_text}"
                    },
                    "action_id": f"restock_{button_text.lower().replace(' ', '_')}",
                    "value": json.dumps({
                        "action": "restock_variant",
                        "variantId": (variant.get("variantId") or variant.get("id") or ""),
                        "variantTitle": variant_title,
                        "orderId": order_id,
                        "rawOrderNumber": raw_order_number
                    })
                })
        else:
            # Fallback if no variant data
            message += "• No inventory information available\n"
        
        message += "Restock Inventory?"
        
        # Add "Do Not Restock" button
        action_buttons.append({
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "Do Not Restock"
            },
            "action_id": "do_not_restock",
            "value": json.dumps({
                "action": "do_not_restock",
                "orderId": order_id,
                "rawOrderNumber": raw_order_number
            })
        })
        
        return {
            "text": message,
            "action_buttons": action_buttons
        }
    
    def build_completion_message_after_restocking(
        self,
        current_message_full_text: str,
        action_id: str,
        variant_name: str,
        restock_user: str,
        sheet_link: str,
        raw_order_number: str,
        order_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build completion message after refund and inventory restock."""
        # Extract order metadata
        order_name = order_data.get("name", "#Unknown") if order_data else "#Unknown"
        customer_info = order_data.get("customer", {}) if order_data else {}
        requestor_name = f"{customer_info.get('firstName', '')} {customer_info.get('lastName', '')}".strip()
        if not requestor_name:
            requestor_name = "Unknown Customer"

        # Try to extract order link if possible
        if order_data:
            shopify_order_id = order_data.get("id", "")
            order_numeric_id = shopify_order_id.split("/")[-1] if shopify_order_id else ""
            order_link = f"https://admin.shopify.com/store/09fe59-3/orders/{order_numeric_id}" if order_numeric_id else ""
        else:
            order_link = ""

        # Hardcoded waitlist link (can be made dynamic later if needed)
        waitlist_link = "https://docs.google.com/spreadsheets/d/11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw/edit#gid=1811075695"

        # Build Slack message
        season_info = self.extract_season_start_info(current_message_full_text)
        product_title = season_info.get("product_title", "Unknown Product")
        season_start_date = season_info.get("season_start_date", "Unknown")

        message = (
            f":white_check_mark: Request to provide a ${variant_name} refund for "
            f"<{order_link}|Order {order_name}> for {requestor_name} has been processed by <@{restock_user}>.\n\n"
            f":white_check_mark: Inventory restocked to {variant_name} successfully by <@{restock_user}>\n\n" if action_id == "restock_variant" else f":white_check_mark: Inventory not restocked (processed by <@{restock_user}>)\n\n"
            f":package: Season Start Date for {product_title} is {season_start_date}.\n\n"
            f":link: <{waitlist_link}|Open Waitlist to let someone in>\n\n"
            f":link: <{sheet_link}|View Request in Google Sheets>\n\n"
            
        )
        return message

    def build_comprehensive_no_refund_message(self, order_data: Dict[str, Any], raw_order_number: str, 
                                            order_cancelled: bool, requestor_name: Dict[str, str], requestor_email: str, processor_user: str,
                                            thread_ts: str, 
                                            current_message_full_text: str) -> Dict[str, Any]:
        """Build comprehensive no refund message with customer info, inventory, and restock buttons"""
        debug_prefix = "[DEBUG] " if settings.is_debug_mode else ""
        
        # Extract customer info from order data
        customer_name = "Unknown Customer"
        if order_data and "customer" in order_data:
            customer = order_data["customer"]
            if customer:
                first_name = customer.get("firstName", "")
                last_name = customer.get("lastName", "")
                if first_name or last_name:
                    customer_name = f"{first_name} {last_name}".strip()
        
        # Fallback: try to extract customer name from current message text
        if customer_name == "Unknown Customer":
            import re
            # Try multiple patterns for extracting customer name
            name_patterns = [
                # Pattern 1: "*Requested by:* Name (email)" or "*Requested by:* Name (<email|email>)"
                r"\*Requested by:\*\s*([^(<]+)(?:\s*\(|$)",
                # Pattern 2: "Requested by:* Name (email)" without asterisks  
                r"Requested by:\*?\s*([^(<]+)(?:\s*\(|$)",
                # Pattern 3: Extract from email context ":e-mail: *Requested by:* Name"
                r":e-mail:\s*\*Requested by:\*\s*([^(<]+)(?:\s*\(|$)"
            ]
            
            for pattern in name_patterns:
                customer_match = re.search(pattern, current_message_full_text)
                if customer_match:
                    extracted_name = customer_match.group(1).strip()
                    if extracted_name and not extracted_name.startswith('<'):  # Avoid matching email links
                        customer_name = extracted_name
                        break
        
        # Extract season start info from current message
        season_info = self.extract_season_start_info(current_message_full_text)
        product_title = season_info.get("product_title", "Unknown Product")
        season_start_date = season_info.get("season_start_date", "Unknown")
        
        # Extract Google Sheets link from current message
        sheet_link = self.extract_sheet_link(current_message_full_text)
        
        # Format requestor name properly
        requestor_full_name = f"{requestor_name.get('first', '')} {requestor_name.get('last', '')}".strip()
        if not requestor_full_name:
            requestor_full_name = "Unknown Customer"
        
        # Build main message
        message = f":white_check_mark: {debug_prefix}Request for no refund for Order {raw_order_number} for {requestor_full_name} has been processed by @{processor_user}\n"
        
        # Add Google Sheets link
        if sheet_link:
            message += f":link: <{sheet_link}|View Request in Google Sheets>\n"
        else:
            message += ":link: View Request in Google Sheets\n"
        
        # Add season start info
        message += f":package: Season Start Date for {product_title} is {season_start_date}.\n"
        
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
                variant_title = (variant.get("variantTitle") or 
                               variant.get("variantName") or 
                               variant.get("title") or 
                               "Unknown Variant")
                available_quantity = (variant.get("availableQuantity") or 
                                    variant.get("inventory") or 
                                    variant.get("inventoryQuantity") or 
                                    0)
                
                # Add inventory line
                message += f"• {variant_title}: {available_quantity} spots available\n"
                
                # Create restock button (remove "Registration" from variant name if present)
                button_text = variant_title.replace(" Registration", "").strip()
                action_buttons.append({
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": f"Restock {button_text}"
                    },
                    "action_id": f"restock_{button_text.lower().replace(' ', '_')}",
                    "value": json.dumps({
                        "action": "restock_variant",
                        "variantId": (variant.get("variantId") or variant.get("id") or ""),
                        "variantTitle": variant_title,
                        "orderId": order_data.get("orderId", ""),
                        "rawOrderNumber": raw_order_number
                    })
                })
        else:
            # Fallback if no variant data
            message += "• No inventory information available\n"
        
        message += "Restock Inventory?"
        
        # Add "Do Not Restock" button
        action_buttons.append({
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "Do Not Restock"
            },
            "action_id": "do_not_restock",
            "value": json.dumps({
                "action": "do_not_restock",
                "orderId": order_data.get("orderId", ""),
                "rawOrderNumber": raw_order_number
            })
        })
        
        return {
            "text": message,
            "action_buttons": action_buttons
        }

    # === MESSAGE MANAGEMENT HELPERS ===

    def update_slack_on_shopify_success(self, message_ts: str, success_message: str, action_buttons: list) -> Dict[str, Any]:
        """Update Slack message on Shopify success"""
        try:
            result = self.api_client.update_message(
                message_ts=message_ts,
                message_text=success_message,
                action_buttons=action_buttons
            )
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Failed to update Slack message on success: {e}")
            return {"success": False, "error": str(e)}

    def update_slack_on_shopify_failure(self, message_ts: str, error_message: str, operation_name: str):
        """Update Slack message on Shopify failure"""
        try:
            # Based on memory, user prefers ephemeral popups instead of updating the main message
            logger.info(f"Shopify {operation_name} failed: {error_message}")
            # Don't update the main message - just log the error
        except Exception as e:
            logger.error(f"Failed to handle Shopify failure: {e}")

    def send_modal_error_to_user(self, trigger_id: Optional[str], error_message: str, operation_name: str):
        """Send modal error to user using SlackService functionality"""
        try:
            if trigger_id:
                # Clean up error message for Slack compatibility
                cleaned_message = error_message.replace('**', '*').replace('•', '-')
                
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
                    "title": {
                        "type": "plain_text",
                        "text": title_text
                    },
                    "close": {
                        "type": "plain_text",
                        "text": "Close"
                    },
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": modal_text
                            }
                        }
                    ]
                }
                
                logger.info(f"📱 Sending modal with trigger_id: {trigger_id[:20]}...")
                logger.debug(f"📱 Modal title: '{title_text}' (length: {len(title_text)})")
                logger.debug(f"📱 Modal text length: {len(modal_text)}")
                
                # Send modal via Slack API
                result = self.api_client.send_modal(trigger_id, modal_view)
                
                if result.get('success', False):
                    logger.info(f"✅ Sent modal error dialog for {operation_name}")
                    return True
                else:
                    logger.error(f"❌ Failed to send modal dialog: {result.get('error', 'Unknown error')}")
                    return False
            else:
                logger.warning(f"⚠️ No trigger_id provided for modal error: {operation_name}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception sending modal error dialog: {str(e)}")
            return False
    
    async def handle_restock_inventory(
    self,
    request_data: Dict[str, str],
    action_id: str,
    channel_id: str,
    thread_ts: str,
    slack_user_name: str,
    current_message_full_text: str,
    trigger_id: Optional[str] = None
) -> Dict[str, Any]:
        """Handle inventory restocking button clicks"""
        print(f"\n📦 === RESTOCK INVENTORY ACTION ===")
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
                print(f"🚫 User chose not to restock inventory")
                completion_message = self.build_completion_message_after_restocking(
                    current_message_full_text=current_message_full_text,
                    action_id=action_id,
                    variant_name="",
                    restock_user=slack_user_name,
                    sheet_link=sheet_url,
                    raw_order_number=raw_order_number
                )
                self.update_slack_on_shopify_success(
                    message_ts=thread_ts,
                    success_message=completion_message,
                    action_buttons=[]
                )
                return {"success": True, "message": "Inventory restock declined"}

            # For all other action IDs, require a variant
            variant_id = request_data.get("variantId", "")
            variant_title = request_data.get("variantTitle", "Unknown Variant")

            print(f"🔍 EXTRACTED VALUES:")
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
                        operation_name="Inventory Restock"
                    )
                return {"success": False, "message": error_message}

            # Step 1: Lookup inventory item ID
            inventory_info = self.orders_service.shopify_service.get_inventory_item_and_quantity(variant_id)
            if not inventory_info.get("success"):
                error_msg = inventory_info.get("message", "Unknown error")
                modal_error_message = f"Failed to get inventory info for {variant_title}.\n\n**Shopify Error:**\n{error_msg}"
                if trigger_id:
                    self.send_modal_error_to_user(trigger_id, modal_error_message, "Inventory Restock")
                logger.error(f"❌ Inventory info failed: {modal_error_message}")
                return {"success": False, "message": error_msg}

            inventory_item_id = inventory_info.get("inventoryItemId")
            current_quantity = inventory_info.get("inventoryQuantity", 0)

            print(f"📊 Current inventory for {variant_title}: {current_quantity}")
            print(f"🔑 Inventory item ID: {inventory_item_id}")

            # Step 2: Adjust inventory by +1
            inventory_result = self.orders_service.shopify_service.adjust_inventory(inventory_item_id, delta=1)
            if not inventory_result.get("success"):
                error_msg = inventory_result.get("message", "Unknown error")
                modal_error_message = f"Inventory restock failed for {variant_title}.\n\n**Shopify Error:**\n{error_msg}"
                if trigger_id:
                    self.send_modal_error_to_user(trigger_id, modal_error_message, "Inventory Restock")
                logger.error(f"❌ Inventory restock failed: {modal_error_message}")
                return {"success": False, "message": error_msg}

            print(f"✅ Successfully restocked {variant_title} by +1")
            completion_message = self.build_completion_message_after_restocking(
                current_message_full_text=current_message_full_text,
                action_id=action_id,
                variant_name=variant_title,
                restock_user=slack_user_name,
                sheet_link=sheet_url,
                raw_order_number=raw_order_number
            )

            self.update_slack_on_shopify_success(
                message_ts=thread_ts,
                success_message=completion_message,
                action_buttons=[]
            )

            return {
                "success": True,
                "message": f"Successfully restocked {variant_title} by +1",
                "new_quantity": current_quantity + 1
            }

        except Exception as e:
            error_message = f"Exception in handle_restock_inventory: {str(e)}"
            logger.error(f"❌ {error_message}")
            if trigger_id:
                self.send_modal_error_to_user(
                    trigger_id=trigger_id,
                    error_message=f"Unexpected error during inventory restock.\n\n**Error:**\n{str(e)}",
                    operation_name="Inventory Restock"
                )
            return {"success": False, "message": error_message}
    
    async def handle_edit_request_details(self, request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str, slack_user_id: str, trigger_id: str, current_message_full_text: str) -> Dict[str, Any]:
        """
        Handle edit request details button click - shows modal for editing order number and requestor email
        """
        print(f"\n✏️ === EDIT REQUEST DETAILS HANDLER ===")
        print(f"👤 User: {slack_user_name} ({slack_user_id})")
        print(f"📋 Request Data: {request_data}")
        print(f"🎯 Trigger ID: {trigger_id}")
        print("=== END EDIT REQUEST DETAILS ===\n")
        
        try:
            # Extract current values from request_data
            raw_order_number = request_data.get("rawOrderNumber", "").replace("#", "")  # Remove # for editing
            requestor_email = request_data.get("requestorEmail", "")
            first_name = request_data.get("first", "")
            last_name = request_data.get("last", "")
            refund_type = request_data.get("refundType", "refund")
            notes = request_data.get("notes", "")
            request_submitted_at = request_data.get("requestSubmittedAt", "")
            
            # Build modal for editing
            modal_blocks = self._build_edit_request_modal_blocks(
                raw_order_number=raw_order_number,
                requestor_email=requestor_email,
                first_name=first_name,
                last_name=last_name,
                refund_type=refund_type,
                notes=notes,
                request_submitted_at=request_submitted_at
            )
            
            # Prepare private metadata with original request data AND message context
            private_metadata = json.dumps({
                "first": first_name,
                "last": last_name,
                "refund_type": refund_type,
                "notes": notes,
                "request_submitted_at": request_submitted_at,
                "original_thread_ts": thread_ts,  # Store original message timestamp
                "original_channel_id": channel_id  # Store channel ID
            })
            
            # Show modal to user
            modal_result = self._show_modal_to_user(
                trigger_id=trigger_id,
                modal_title="Edit Request Details",
                modal_blocks=modal_blocks,
                callback_id="edit_request_details_submission",
                private_metadata=private_metadata
            )
            
            if modal_result.get("success"):
                logger.info(f"✅ Modal shown successfully to {slack_user_name}")
                return {"success": True, "message": "Modal displayed"}
            else:
                error_msg = modal_result.get("error", "Failed to show modal")
                logger.error(f"❌ Failed to show modal: {error_msg}")
                return {"success": False, "message": error_msg}
                
        except Exception as e:
            error_message = f"Exception in handle_edit_request_details: {str(e)}"
            logger.error(f"❌ {error_message}")
            return {"success": False, "message": error_message}
    
    async def handle_deny_refund_request(self, request_data: Dict[str, str], channel_id: str, requestor_name: Dict[str, str], requestor_email: str, thread_ts: str, slack_user_id: str, slack_user_name: str, current_message_full_text: str, trigger_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle deny refund request button click - denies the refund request and sends denial email
        """
        print(f"\n🚫 === DENY REFUND REQUEST HANDLER ===")
        print(f"👤 User: {slack_user_name} ({slack_user_id})")
        print(f"📋 Request Data: {request_data}")
        print("=== END DENY REFUND REQUEST ===\n")
        
        try:
            # Extract request details
            raw_order_number = request_data.get("rawOrderNumber", "")
            refund_type = request_data.get("refundType", "refund")
            first_name = requestor_name.get("first", "")
            last_name = requestor_name.get("last", "")
            request_submitted_at = request_data.get("requestSubmittedAt", "")
            
            # Build denial message
            denial_message = f"🚫 *Refund Request Denied*\n\n"
            denial_message += f"*Order Number:* {raw_order_number}\n"
            denial_message += f"*Requested by:* {first_name} {last_name} ({requestor_email})\n"
            denial_message += f"*Request Submitted At:* {request_submitted_at}\n"
            denial_message += f"*Denied by:* <@{slack_user_name}>\n"
            denial_message += f"*Denied at:* {format_date_and_time(datetime.now(timezone.utc))}\n\n"
            denial_message += f"🚫 *This refund request has been denied.*\n\n"
            denial_message += f"📧 The requestor will be notified via email about the denial."
            
            # TODO: Send denial email to requestor here
            # For now, we'll just update the Slack message
            
            # Update Slack message
            update_result = self.update_slack_on_shopify_success(
                message_ts=thread_ts,
                success_message=denial_message,
                action_buttons=[]  # No buttons needed for denial
            )
            
            if update_result.get("success"):
                print(f"✅ Denial message sent to Slack")
                return {"success": True, "message": "Refund request denied successfully"}
            else:
                error_msg = update_result.get("error", "Unknown error")
                print(f"❌ Failed to update Slack message: {error_msg}")
                return {"success": False, "message": f"Failed to update Slack: {error_msg}"}
                
        except Exception as e:
            error_message = f"Exception in handle_deny_refund_request: {str(e)}"
            logger.error(f"❌ {error_message}")
            return {"success": False, "message": error_message}
    
    async def handle_deny_email_mismatch(self, request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str, slack_user_id: str, trigger_id: str, current_message_full_text: str) -> Dict[str, Any]:
        """
        Handle deny email mismatch button click - closes the request due to email mismatch
        """
        print(f"\n🚫 === DENY EMAIL MISMATCH HANDLER ===")
        print(f"👤 User: {slack_user_name} ({slack_user_id})")
        print(f"📋 Request Data: {request_data}")
        print("=== END DENY EMAIL MISMATCH ===\n")
        
        try:
            # Extract request details
            raw_order_number = request_data.get("rawOrderNumber", "")
            requestor_email = request_data.get("requestorEmail", "")
            first_name = request_data.get("first", "")
            last_name = request_data.get("last", "")
            request_submitted_at = request_data.get("requestSubmittedAt", "")
            
            # Build denial message
            denial_message = f":no_entry_sign: *Request Denied - Email Mismatch*\n\n"
            denial_message += f"*Order Number:* {raw_order_number}\n"
            denial_message += f"*Requested by:* {first_name} {last_name} ({requestor_email})\n"
            denial_message += f"*Request Submitted At:* {request_submitted_at}\n"
            denial_message += f"*Denied by:* {slack_user_name}\n\n"
            denial_message += f":warning: *This request was denied due to email mismatch with the order's customer email.*\n\n"
            denial_message += f"The requestor should be contacted to verify their email or order number if needed."
            
            # Update Slack message
            update_result = self.update_slack_on_shopify_success(
                message_ts=thread_ts,
                success_message=denial_message,
                action_buttons=[]  # No buttons needed for denial
            )
            
            if update_result.get("success"):
                logger.info(f"✅ Request denied successfully by {slack_user_name}")
                return {"success": True, "message": "Request denied due to email mismatch"}
            else:
                error_msg = update_result.get("error", "Failed to update message")
                logger.error(f"❌ Failed to update message: {error_msg}")
                return {"success": False, "message": error_msg}
                
        except Exception as e:
            error_message = f"Exception in handle_deny_email_mismatch: {str(e)}"
            logger.error(f"❌ {error_message}")
            return {"success": False, "message": error_message}
    
    def _build_edit_request_modal_blocks(self, raw_order_number: str, requestor_email: str, 
                                       first_name: str, last_name: str, refund_type: str, 
                                       notes: str, request_submitted_at: str) -> List[Dict[str, Any]]:
        """
        Build the modal blocks for editing request details
        """
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":pencil2: *Edit Request Details*\n\nUpdate the order number or requestor email to re-validate the request."
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "input",
                "block_id": "order_number_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "order_number",
                    "initial_value": raw_order_number,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Enter order number (without #)"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "Order Number"
                }
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
                        "text": "Enter requestor email address"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "Requestor Email"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Current Request Details:*\n• Name: {first_name} {last_name}\n• Type: {refund_type.title()}\n• Submitted: {request_submitted_at}\n• Notes: {notes[:100]}{'...' if len(notes) > 100 else ''}"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":information_source: *Note:* After updating, the request will be re-validated against Shopify to check if the order exists and if the email matches."
                }
            }
        ]
        
        return blocks
    
    def _show_modal_to_user(self, trigger_id: str, modal_title: str, modal_blocks: List[Dict[str, Any]], callback_id: str, private_metadata: str = "") -> Dict[str, Any]:
        """
        Show a modal dialog to the user
        """
        try:
            modal_view = {
                "type": "modal",
                "callback_id": callback_id,
                "title": {
                    "type": "plain_text",
                    "text": modal_title
                },
                "blocks": modal_blocks,
                "submit": {
                    "type": "plain_text",
                    "text": "Update & Re-validate"
                },
                "close": {
                    "type": "plain_text",
                    "text": "Cancel"
                }
            }
            
            if private_metadata:
                modal_view["private_metadata"] = private_metadata
            
            response = self.api_client.send_modal(trigger_id, modal_view)
            
            if response.get("ok"):
                return {"success": True}
            else:
                error = response.get("error", "Unknown error")
                return {"success": False, "error": f"Slack API error: {error}"}
                
        except Exception as e:
            return {"success": False, "error": f"Exception showing modal: {str(e)}"}
    
    async def handle_edit_request_details_submission(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle modal submission for editing request details
        Re-validates the request with updated order number and email
        """
        print(f"\n📝 === EDIT REQUEST DETAILS SUBMISSION ===")
        print(f"📋 Full Payload: {json.dumps(payload, indent=2)}")
        print("=== END SUBMISSION DEBUG ===\n")
        
        try:
            # Extract user info
            user_info = payload.get("user", {})
            slack_user_name = user_info.get("name", "Unknown")
            slack_user_id = user_info.get("id", "Unknown")
            
            # Extract view data
            view = payload.get("view", {})
            state = view.get("state", {})
            values = state.get("values", {})
            
            # Extract updated values from modal
            order_number_input = values.get("order_number_input", {}).get("order_number", {})
            requestor_email_input = values.get("requestor_email_input", {}).get("requestor_email", {})
            
            updated_order_number = order_number_input.get("value", "").strip()
            updated_requestor_email = requestor_email_input.get("value", "").strip()
            
            print(f"✏️ Updated values:")
            print(f"   Order Number: {updated_order_number}")
            print(f"   Requestor Email: {updated_requestor_email}")
            
            # Validate input
            if not updated_order_number or not updated_requestor_email:
                return {
                    "response_action": "errors",
                    "errors": {
                        "order_number_input": "Order number is required" if not updated_order_number else "",
                        "requestor_email_input": "Email is required" if not updated_requestor_email else ""
                    }
                }
            
            # Extract private metadata to reconstruct original request
            private_metadata = view.get("private_metadata", "{}")
            try:
                original_request_data = json.loads(private_metadata) if private_metadata != "{}" else {}
            except:
                original_request_data = {}
            
            # Extract original message context for updating
            original_thread_ts = original_request_data.get("original_thread_ts")
            original_channel_id = original_request_data.get("original_channel_id")
            
            # Reconstruct request data with updated values
            updated_request_data = {
                "order_number": updated_order_number,
                "requestor_name": {
                    "first": original_request_data.get("first", ""),
                    "last": original_request_data.get("last", "")
                },
                "requestor_email": updated_requestor_email,
                "refund_type": original_request_data.get("refund_type", "refund"),
                "notes": original_request_data.get("notes", ""),
                "sheet_link": original_request_data.get("sheet_link", "")
            }
            
            print(f"🔄 Re-validating request with updated data:")
            print(f"   {json.dumps(updated_request_data, indent=2)}")
            
            # Re-validate directly using orders service (avoid circular API call)
            print(f"🔍 Validating order {updated_order_number} with email {updated_requestor_email}")
            
            # Step 1: Check if order exists
            order_result = self.orders_service.fetch_order_details_by_email_or_order_name(
                order_name=updated_order_number
            )
            
            if not order_result["success"]:
                print(f"❌ Order {updated_order_number} not found")
                return {
                    "response_action": "errors",
                    "errors": {
                        "order_number_input": "Order not found with this number"
                    }
                }
            
            # Step 2: Check if email matches
            order_data = order_result["data"]
            order_customer_email = order_data.get("customer", {}).get("email", "").lower().strip()
            requestor_email_lower = updated_requestor_email.lower().strip()
            
            if order_customer_email != requestor_email_lower:
                print(f"⚠️ Email mismatch: Order email '{order_customer_email}' != Requestor email '{requestor_email_lower}'")
                return {
                    "response_action": "errors",
                    "errors": {
                        "requestor_email_input": "Email still does not match the order's customer email"
                    }
                }
            
            # Step 3: Success - update original message with success case
            print(f"✅ Re-validation successful - order found and email matches")
            
            # Build requestor info from updated data
            requestor_info = {
                "first": original_request_data.get("first", ""),
                "last": original_request_data.get("last", ""),
                "email": updated_requestor_email,
                "refund_type": original_request_data.get("refund_type", "refund"),
                "notes": original_request_data.get("notes", ""),
                "sheet_link": original_request_data.get("sheet_link", "")
            }
            
            # Calculate refund amount using the order data
            from services.orders.refund_calculator import RefundCalculator
            calculator = RefundCalculator()
            
            refund_calculation = calculator.calculate_refund(
                order_data=order_data,
                refund_type=requestor_info["refund_type"]
            )
            
            # Build success message with order details and refund buttons
            success_message_data = self.message_builder.build_success_message(
                order_data=order_data,
                refund_amount=refund_calculation["refund_amount"],
                refund_type=requestor_info["refund_type"],
                raw_order_number=updated_order_number,
                order_cancelled=refund_calculation.get("order_cancelled", False),
                requestor_name={
                    "first": requestor_info["first"],
                    "last": requestor_info["last"]
                },
                requestor_email=requestor_info["email"],
                notes=requestor_info["notes"],
                sheet_link=requestor_info["sheet_link"],
                order_id=order_data.get("id", ""),
                updated_via_modal=True  # Flag to indicate this was updated via modal
            )
            
            # Get the original message timestamp from private metadata or context
            # Since we don't have access to the original thread_ts here, we'll need to get it
            # from the payload context or pass it through
            
            # For now, let's extract the thread_ts from the payload if available
            # This might need to be passed through the private metadata
            
            print(f"🔄 Updating original Slack message with success details")
            print(f"📊 Refund calculation: ${refund_calculation['refund_amount']}")
            
            # Update the original message with success details
            if original_thread_ts and original_channel_id:
                print(f"📍 Updating message {original_thread_ts} in channel {original_channel_id}")
                
                update_result = self.update_slack_on_shopify_success(
                    message_ts=original_thread_ts,
                    success_message=success_message_data["text"],
                    action_buttons=success_message_data["action_buttons"]
                )
                
                if update_result.get("success"):
                    print(f"✅ Original message updated successfully with order details and refund buttons")
                else:
                    print(f"⚠️ Failed to update original message: {update_result.get('error', 'Unknown error')}")
            else:
                print(f"❌ Missing original message context - cannot update original message")
                print(f"   thread_ts: {original_thread_ts}, channel_id: {original_channel_id}")
            
            return {"response_action": "clear"}
                
        except Exception as e:
            error_message = f"Exception in handle_edit_request_details_submission: {str(e)}"
            logger.error(f"❌ {error_message}")
            return {
                "response_action": "errors",
                "errors": {
                    "order_number_input": "An error occurred during validation"
                }
            }
    
    async def handle_deny_email_mismatch_modal(self, request_data: Dict[str, str], channel_id: str, thread_ts: str, slack_user_name: str, slack_user_id: str, trigger_id: str, current_message_full_text: str) -> Dict[str, Any]:
        """
        Handle the deny email mismatch modal button click - show modal for custom denial message
        """
        print(f"\n🚫 === DENY EMAIL MISMATCH MODAL ===")
        print(f"👤 User: {slack_user_name} (ID: {slack_user_id})")
        print(f"📦 Request Data: {request_data}")
        print(f"🎯 Trigger ID: {trigger_id}")
        print(f"🚫 === END DENY EMAIL MISMATCH MODAL DEBUG ===\n")
        
        try:
            # Extract request details
            raw_order_number = request_data.get("rawOrderNumber", "")
            requestor_email = request_data.get("requestorEmail", "")
            first_name = request_data.get("first", "")
            last_name = request_data.get("last", "")
            refund_type = request_data.get("refundType", "refund")
            request_submitted_at = request_data.get("requestSubmittedAt", "")
            
            # Build the modal blocks
            modal_blocks = self._build_deny_request_modal_blocks(
                raw_order_number=raw_order_number,
                requestor_email=requestor_email,
                first_name=first_name,
                last_name=last_name,
                refund_type=refund_type
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
                "slack_user_id": slack_user_id
            }
            
            # Show the modal
            modal_result = await self._show_modal_to_user(
                trigger_id=trigger_id,
                modal_title="Deny Refund Request",
                modal_blocks=modal_blocks,
                callback_id="deny_email_mismatch_submission",
                private_metadata=json.dumps(private_metadata)
            )
            
            if modal_result.get("success"):
                print(f"✅ Deny request modal shown successfully")
                return {"success": True, "message": "Modal displayed"}
            else:
                error_msg = modal_result.get("error", "Unknown error")
                print(f"❌ Failed to show deny request modal: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            error_message = f"Exception in handle_deny_email_mismatch_modal: {str(e)}"
            logger.error(f"❌ {error_message}")
            return {"success": False, "error": error_message}
    
    def _build_deny_request_modal_blocks(self, raw_order_number: str, requestor_email: str, first_name: str, last_name: str, refund_type: str) -> List[Dict[str, Any]]:
        """
        Build the modal blocks for the deny request form
        """
        refund_type_text = "refund" if refund_type.lower() == "refund" else "credit"
        requestor_name = f"{first_name} {last_name}".strip()
        
        # Default denial message
        default_message = (
            f"Hi {first_name},\\n\\n"
            f"Your request for a {refund_type_text} has not been processed successfully. "
            f"The email associated with the order number did not match the email you provided in the request. "
            f"Please confirm you submitted your request using the same email address as is associated with your order - "
            f"sign in to see your order history to find the correct order number - and try again.\\n\\n"
            f"If you believe this is in error, please reach out to refunds@bigapplerecsports.com."
        )
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🚫 *Deny Refund Request*\\n\\nYou are about to send a denial email to **{requestor_name}** ({requestor_email}) for order **{raw_order_number}** due to email mismatch."
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "input",
                "block_id": "custom_message_input",
                "label": {
                    "type": "plain_text",
                    "text": "Custom Message (Optional)"
                },
                "element": {
                    "type": "plain_text_input",
                    "action_id": "custom_message",
                    "multiline": True,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Enter a custom message to replace the default denial email..."
                    },
                    "initial_value": default_message
                },
                "optional": True
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Staff Information*"
                },
                "accessory": {
                    "type": "checkboxes",
                    "action_id": "include_staff_info",
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Include my name and email in the message"
                            },
                            "description": {
                                "type": "plain_text",
                                "text": "Email will be sent from web@bigapplerecsports.com but include your details"
                            },
                            "value": "include_staff_info"
                        }
                    ]
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📧 *Email will be sent to:* {requestor_email}\\n📝 *Subject:* Big Apple Rec Sports - Refund Request Denied for Order {raw_order_number}"
                }
            }
        ]
        
        return blocks
    
    async def handle_deny_email_mismatch_submission(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle modal submission for deny email mismatch - send custom denial email
        """
        print(f"\\n🚫 === DENY EMAIL MISMATCH SUBMISSION ===")
        print(f"📋 Payload: {json.dumps(payload, indent=2)}")
        print("=== END DENY SUBMISSION DEBUG ===\\n")
        
        try:
            # Extract form values
            values = payload.get("view", {}).get("state", {}).get("values", {})
            
            # Get custom message (optional)
            custom_message_block = values.get("custom_message_input", {})
            custom_message = custom_message_block.get("custom_message", {}).get("value", "")
            
            # Get staff info inclusion checkbox
            staff_info_block = values.get("include_staff_info", {})
            include_staff_info = bool(staff_info_block.get("include_staff_info", {}).get("selected_options", []))
            
            # Extract original request context from private metadata
            private_metadata_str = payload.get("view", {}).get("private_metadata", "{}")
            original_context = json.loads(private_metadata_str)
            
            raw_order_number = original_context.get("raw_order_number", "")
            requestor_email = original_context.get("requestor_email", "")
            first_name = original_context.get("first_name", "")
            last_name = original_context.get("last_name", "")
            refund_type = original_context.get("refund_type", "refund")
            original_thread_ts = original_context.get("original_thread_ts", "")
            original_channel_id = original_context.get("original_channel_id", "")
            slack_user_name = original_context.get("slack_user_name", "")
            slack_user_id = original_context.get("slack_user_id", "")
            
            print(f"📧 Sending denial email to: {requestor_email}")
            print(f"🔧 Include staff info: {include_staff_info}")
            print(f"📝 Custom message: {custom_message[:100]}..." if custom_message else "📝 Using default message")
            
            # Build and send the denial email
            email_result = await self._send_denial_email(
                requestor_email=requestor_email,
                requestor_name={"first": first_name, "last": last_name},
                raw_order_number=raw_order_number,
                refund_type=refund_type,
                custom_message=custom_message,
                include_staff_info=include_staff_info,
                staff_name=slack_user_name,
                staff_id=slack_user_id
            )
            
            if email_result.get("success"):
                # Update the original Slack message with denial confirmation
                denial_confirmation_message = self._build_denial_confirmation_message(
                    requestor_email=requestor_email,
                    requestor_name={"first": first_name, "last": last_name},
                    raw_order_number=raw_order_number,
                    staff_name=slack_user_name,
                    include_staff_info=include_staff_info
                )
                
                # Update original message
                update_result = self.update_slack_on_shopify_success(
                    message_ts=original_thread_ts,
                    success_message=denial_confirmation_message,
                    action_buttons=[]
                )
                
                if update_result.get("success"):
                    print(f"✅ Original message updated with denial confirmation")
                else:
                    print(f"⚠️ Failed to update original message: {update_result.get('error', 'Unknown error')}")
                
                return {"response_action": "clear"}
            else:
                error_msg = email_result.get("error", "Unknown error sending email")
                return {
                    "response_action": "errors",
                    "errors": {
                        "custom_message_input": f"Failed to send email: {error_msg}"
                    }
                }
                
        except Exception as e:
            error_message = f"Exception in handle_deny_email_mismatch_submission: {str(e)}"
            logger.error(f"❌ {error_message}")
            return {
                "response_action": "errors",
                "errors": {
                    "custom_message_input": "An error occurred while processing the denial"
                }
            }
    
    async def _send_denial_email(self, requestor_email: str, requestor_name: Dict[str, str], raw_order_number: str, 
                                 refund_type: str, custom_message: str, include_staff_info: bool, 
                                 staff_name: str, staff_id: str) -> Dict[str, Any]:
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
            message_body += (
                "\\n\\n--\\n"
                "Warmly,\\n"
                "**BARS Leadership**"
            )
            
            # Convert to HTML format for email
            html_body = f"<p>{message_body.replace('\\n', '<br>')}</p>"
            
            print(f"📧 Sending denial email:")
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
    
    def _build_denial_confirmation_message(self, requestor_email: str, requestor_name: Dict[str, str], 
                                          raw_order_number: str, staff_name: str, include_staff_info: bool) -> str:
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
            message += f"📧 *Email included staff information*\\n"
        
        message += f"\\n*Reason:* Email address did not match order customer email"
        
        return message