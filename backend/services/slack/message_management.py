"""
Slack message management utilities.
Handles updating, sending, and managing Slack messages.
"""

from typing import Dict, Any, Optional, List
import logging
from .slack_service import SlackService

logger = logging.getLogger(__name__)


class SlackMessageManager:
    """Manages Slack message operations"""
    
    def __init__(self):
        self.slack_service = SlackService()
    
    def should_update_slack_on_shopify_failure(self) -> bool:
        """
        Determine whether to update Slack messages when Shopify operations fail.
        In production, we might want to avoid updating Slack on failures.
        """
        # Check environment - in production, you can disable error message updates
        # by changing this logic based on your environment settings
        
        # Option 1: Always allow error messages (current behavior)
        # return True
        
        # Option 2: Disable error messages in production (uncomment to enable)
        # return not getattr(settings, 'is_production_mode', False)
        
        # Option 3: Never send error messages (uncomment to enable)  
        return False

    def update_slack_on_shopify_success(
        self,
        message_ts: str, 
        success_message: str, 
        action_buttons: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Update Slack message only for successful Shopify operations.
        Returns True if update was attempted, False if skipped.
        """
        try:
            update_result = self.slack_service.api_client.update_message(
                message_ts=message_ts,
                message_text=success_message,
                action_buttons=action_buttons or []
            )
            
            if update_result.get('success', False):
                logger.info("✅ Slack message updated successfully after Shopify success")
                return True
            else:
                logger.error(f"❌ Slack message update failed: {update_result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception during Slack message update: {str(e)}")
            return False

    def send_modal_error_to_user(
        self,
        trigger_id: str,
        error_message: str,
        operation_name: str = "operation"
    ) -> bool:
        """
        Send a modal dialog error message to the user who clicked the button.
        Modals automatically dismiss when the user clicks outside or takes action.
        
        Args:
            trigger_id: The trigger ID from the Slack interaction
            error_message: The error message to display
            operation_name: The name of the operation that failed
            
        Returns:
            True if modal was sent successfully, False otherwise
        """
        try:
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
            logger.debug(f"📱 Modal view: {modal_view}")
            
            # Send modal via Slack API
            result = self.slack_service.api_client.send_modal(trigger_id, modal_view)
            
            if result.get('success', False):
                logger.info(f"✅ Sent modal error dialog for {operation_name}")
                return True
            else:
                logger.error(f"❌ Failed to send modal dialog: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception sending modal error dialog: {str(e)}")
            return False

    def update_slack_on_shopify_failure(
        self,
        message_ts: str, 
        error_message: str, 
        operation_name: str = "Shopify operation"
    ) -> bool:
        """
        Update Slack message for failed Shopify operations.
        Only updates if should_update_slack_on_shopify_failure() returns True.
        """
        if not self.should_update_slack_on_shopify_failure():
            logger.info(f"⏭️ Skipping Slack update for {operation_name} failure (configured to skip)")
            return False
        
        try:
            update_result = self.slack_service.api_client.update_message(
                message_ts=message_ts,
                message_text=error_message,
                action_buttons=[]
            )
            
            if update_result.get('success', False):
                logger.info(f"✅ Slack error message updated for {operation_name} failure")
                return True
            else:
                logger.error(f"❌ Slack error message update failed: {update_result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception during Slack error message update: {str(e)}")
            return False 