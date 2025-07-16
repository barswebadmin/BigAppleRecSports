"""
Main Slack service for handling refund notifications.
Refactored to use helper modules for better organization.
"""

from typing import Dict, Any, Optional, List
import logging
import hashlib
import time
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
        # Production team mentions (commented out for testing):
        # self.sport_groups = {
        #     "kickball": "<!subteam^S08L2521XAM>",
        #     "bowling": "<!subteam^S08KJJ02738>", 
        #     "pickleball": "<!subteam^S08KTJ33Z9R>",
        #     "dodgeball": "<!subteam^S08KJJ5CL4W>"
        # }
        
        # Testing configuration - all sports tag personal channel
        self.sport_groups = {
            "kickball": "<#D026TPC6S3H>",
            "bowling": "<#D026TPC6S3H>", 
            "pickleball": "<#D026TPC6S3H>",
            "dodgeball": "<#D026TPC6S3H>"
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
        
        # Deduplication cache - stores message hashes to prevent duplicates
        # Format: {message_hash: timestamp}
        self._message_cache = {}
        self._cache_expiry_seconds = 300  # 5 minutes
    
    def _generate_message_hash(self, order_data: Dict[str, Any], requestor_info: Dict[str, Any]) -> str:
        """
        Generate a unique hash for deduplication based on order and requestor info.
        This prevents the same refund request from being posted multiple times.
        """
        try:
            order = order_data.get("order", {}) if order_data else {}
            order_number = order.get("orderNumber") or order.get("orderName") or order.get("name") or "unknown"
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
                key for key, timestamp in self._message_cache.items()
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
                    logger.info(f"🔄 Duplicate message detected (hash: {message_hash[:8]}...)")
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
            # Generate message hash for deduplication  
            message_hash = self._generate_message_hash(order_data or {}, requestor_info)
            
            # Check for duplicates
            if self._is_duplicate_message(message_hash):
                logger.info("🔄 Skipping duplicate message")
                return {
                    "success": True,
                    "message": "Duplicate message skipped",
                    "duplicate": True
                }
            
            # Build the appropriate message based on available data
            if order_data and refund_calculation and refund_calculation.get("success"):
                # Full success message with calculated refund
                message_data = self.message_builder.build_success_message(
                    order_data=order_data,
                    refund_calculation=refund_calculation,
                    requestor_info=requestor_info,
                    sheet_link=sheet_link
                )
                
            elif error_type:
                # Error message for various failure scenarios
                message_data = self.message_builder.build_error_message(
                    error_type=error_type,
                    requestor_info=requestor_info,
                    sheet_link=sheet_link,
                    raw_order_number=raw_order_number or "",
                    order_customer_email=order_customer_email or ""
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
                # Remove from cache if sending failed, allow retry
                if message_hash in self._message_cache:
                    del self._message_cache[message_hash]
            
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