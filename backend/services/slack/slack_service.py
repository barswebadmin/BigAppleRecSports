"""
Main Slack service for handling refund notifications.
Refactored to use helper modules for better organization.
"""

from typing import Dict, Any, Optional, List
import logging
from config import settings
from .message_builder import SlackMessageBuilder
from .api_client import SlackApiClient, MockSlackApiClient, _is_test_mode

logger = logging.getLogger(__name__)


class SlackService:
    """
    Main service for handling Slack notifications for refund requests.
    
    This service coordinates message building and API communication
    through specialized helper classes.
    """
    
    def __init__(self):
        # Slack configuration - dynamic based on environment
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
        
        # Initialize helper components
        self.message_builder = SlackMessageBuilder(self.sport_groups)
        
        # Use mock API client during tests to prevent real Slack requests
        if _is_test_mode():
            logger.info("🧪 Test mode detected - using MockSlackApiClient")
            self.api_client = MockSlackApiClient(
                self.refunds_channel["bearer_token"],
                self.refunds_channel["channel_id"]
            )
        else:
            logger.info("🚀 Production mode - using real SlackApiClient")
            self.api_client = SlackApiClient(
                self.refunds_channel["bearer_token"],
                self.refunds_channel["channel_id"]
            )
    
    def send_refund_request_notification(
        self,
        requestor_info: Dict[str, Any],
        sheet_link: str,
        order_data: Optional[Dict[str, Any]] = None,
        refund_calculation: Optional[Dict[str, Any]] = None,
        error_type: Optional[str] = None,
        raw_order_number: Optional[str] = None,
        order_customer_email: Optional[str] = None
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
            logger.info("Building Slack refund notification message")
            
            # Determine message type and build appropriate message
            if error_type:
                # Error messages (order not found, email mismatch, etc.)
                message_data = self.message_builder.build_error_message(
                    error_type=error_type,
                    requestor_info=requestor_info,
                    sheet_link=sheet_link,
                    raw_order_number=raw_order_number or "",
                    order_customer_email=order_customer_email or ""
                )
                
            elif order_data and refund_calculation and refund_calculation.get("success"):
                # Check if season info is missing - use fallback format if so
                if refund_calculation.get("missing_season_info"):
                    message_data = self.message_builder.build_fallback_message(
                        order_data=order_data,
                        requestor_info=requestor_info,
                        sheet_link=sheet_link,
                        error_message=refund_calculation.get("message", ""),
                        refund_calculation=refund_calculation
                    )
                else:
                    # Successful refund calculation with season info
                    message_data = self.message_builder.build_success_message(
                        order_data=order_data,
                        refund_calculation=refund_calculation,
                        requestor_info=requestor_info,
                        sheet_link=sheet_link
                    )
                
            elif order_data:
                # Fallback message when order is found but calculation failed
                error_message = ""
                if refund_calculation:
                    error_message = refund_calculation.get("message", "")
                
                message_data = self.message_builder.build_fallback_message(
                    order_data=order_data,
                    requestor_info=requestor_info,
                    sheet_link=sheet_link,
                    error_message=error_message
                )
                
            else:
                # Generic error message
                message_data = self.message_builder.build_error_message(
                    error_type="unknown",
                    requestor_info=requestor_info,
                    sheet_link=sheet_link
                )
            
            # Send the message using the new API client with blocks and action buttons
            logger.info(f"Sending refund notification to {self.refunds_channel['name']}")
            result = self.api_client.send_message(
                message_text=message_data["text"],
                action_buttons=message_data.get("action_buttons", []),
                slack_text=message_data.get("slack_text", "New refund request notification")
            )
            
            if result["success"]:
                logger.info("Refund notification sent successfully to Slack")
            else:
                logger.error(f"Failed to send refund notification to Slack: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error in send_refund_request_notification: {str(e)}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
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
        product_id_digits = product_id.split('/')[-1] if '/' in product_id else product_id
        return f"https://admin.shopify.com/store/09fe59-3/products/{product_id_digits}"
    
    def _get_request_type_text(self, refund_type: str) -> str:
        """Get request type text (wrapper for tests)"""
        return self.message_builder._get_request_type_text(refund_type)
    
    def _get_sheet_link_line(self, sheet_link: Optional[str]) -> str:
        """Get formatted sheet link line (wrapper for tests)"""
        return self.message_builder._get_sheet_link_line(sheet_link)
    
    def _get_requestor_line(self, requestor_name: Dict[str, str], requestor_email: str) -> str:
        """Get formatted requestor line (wrapper for tests)"""
        return self.message_builder._get_requestor_line(requestor_name, requestor_email)
    
    def _get_optional_request_notes(self, notes: Optional[str]) -> str:
        """Get formatted optional notes (wrapper for tests)"""
        return self.message_builder._get_optional_request_notes(notes or "")
    
    def _send_slack_message(self, channel_id: str, text: str, blocks: Optional[List[Dict[str, Any]]] = None,
                          thread_ts: Optional[str] = None) -> Dict[str, Any]:
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
    
    def update_slack_message(self, channel_id: str, message_ts: str, text: str, 
                           blocks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Update an existing Slack message (wrapper for compatibility)"""
        # Extract message text from blocks if needed
        message_text = text
        if blocks:
            for block in blocks:
                if block.get("type") == "section" and "text" in block:
                    message_text = block["text"]["text"]
                    break
        
        return self.api_client.update_message(message_ts, message_text)
    
    def _create_standard_blocks(self, text: str, include_actions: bool = False, 
                               action_buttons: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Create standard Slack message blocks (wrapper for compatibility)"""
        return self.api_client._create_standard_blocks(text, action_buttons if include_actions else None) 