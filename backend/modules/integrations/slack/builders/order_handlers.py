"""
Order handling logic for Slack interactions.
Handles order cancellation and refund processing workflows.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SlackOrderHandlers:
    """Handles order-related Slack interactions"""

    def __init__(self, orders_service, slack_service, message_builder):
        self.orders_service = orders_service
        self.slack_service = slack_service
        self.message_builder = message_builder

    async def handle_cancel_order_request(
        self,
        order_number: str,
        refund_type: str,
        requestor_name: Dict[str, str],
        requestor_email: str,
        slack_user_id: str,
        slack_user_name: str,
        channel_id: str,
        thread_ts: str,
        current_message_text: str,
        trigger_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Handle order cancellation request from Slack.
        
        Args:
            order_number: Order number to cancel
            refund_type: Type of refund
            requestor_name: Requestor's name
            requestor_email: Requestor's email
            slack_user_id: Slack user ID who initiated the request
            slack_user_name: Slack user name who initiated the request
            channel_id: Slack channel ID
            thread_ts: Slack thread timestamp
            current_message_text: Current Slack message text
            trigger_id: Slack trigger ID for modals
            
        Returns:
            Dict containing success status and result details
        """
        try:
            logger.info(f"Processing cancel order request for {order_number} by {slack_user_name}")
            
            # 1. Cancel order using OrdersService
            cancel_result = self.orders_service.cancel_order_with_refund_calculation(
                order_number=order_number,
                refund_type=refund_type
            )
            
            if not cancel_result["success"]:
                # Handle cancellation failure
                error_message = cancel_result.get("error", "Unknown error")
                shopify_errors = cancel_result.get("shopify_errors", [])
                
                logger.error(f"Order cancellation failed for {order_number}: {error_message}")
                
                # Send error modal to user
                if trigger_id:
                    await self._send_cancellation_error_modal(
                        trigger_id=trigger_id,
                        order_number=order_number,
                        error_message=error_message,
                        shopify_errors=shopify_errors
                    )
                
                return {
                    "success": False,
                    "error": error_message,
                    "shopify_errors": shopify_errors
                }
            
            # 2. Build success message
            order_data = cancel_result["order_data"]
            refund_calculation = cancel_result["refund_calculation"]
            
            # Extract sheet link from current message
            sheet_link = self.slack_service.extract_sheet_link(current_message_text)
            
            # Build refund decision message
            refund_message = self.message_builder.create_refund_decision_message(
                order_data={
                    "order": order_data,
                    "refund_calculation": refund_calculation,
                    "requestor_name": requestor_name,
                    "requestor_email": requestor_email,
                },
                requestor_name=requestor_name,
                requestor_email=requestor_email,
                refund_type=refund_type,
                sport_mention=self.message_builder.get_sport_group_mention(
                    order_data.get("line_items", [{}])[0].get("title", "")
                ),
                sheet_link=sheet_link,
                order_cancelled=True,
                slack_user_id=slack_user_id,
                original_timestamp=datetime.now().isoformat(),
            )
            
            # 3. Update Slack message with success
            update_result = self.slack_service.update_message(
                channel_id=channel_id,
                message_ts=thread_ts,
                message_text=refund_message["text"],
                action_buttons=refund_message["action_buttons"]
            )
            
            if update_result["success"]:
                logger.info(f"Order {order_number} cancelled successfully and Slack message updated")
                return {
                    "success": True,
                    "order_data": order_data,
                    "refund_calculation": refund_calculation,
                    "slack_update": update_result
                }
            else:
                logger.error(f"Order cancelled but failed to update Slack message: {update_result.get('error')}")
                return {
                    "success": True,  # Order was cancelled successfully
                    "order_data": order_data,
                    "refund_calculation": refund_calculation,
                    "slack_update_error": update_result.get("error")
                }
                
        except Exception as e:
            logger.error(f"Error in handle_cancel_order_request: {str(e)}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }

    async def _send_cancellation_error_modal(
        self,
        trigger_id: str,
        order_number: str,
        error_message: str,
        shopify_errors: list
    ) -> None:
        """Send error modal to user when order cancellation fails"""
        try:
            modal_text = f"Order cancellation failed for {order_number}.\n\n**Error:**\n{error_message}"
            
            if shopify_errors:
                modal_text += f"\n\n**Shopify Error Details:**\n{shopify_errors}"
            
            # Note: This would need to be implemented in the SlackOrchestrator
            # For now, we'll just log the error
            logger.error(f"Would send error modal: {modal_text}")
            
        except Exception as e:
            logger.error(f"Failed to send cancellation error modal: {str(e)}")

    def build_cancellation_success_message(
        self,
        order_data: Dict[str, Any],
        refund_calculation: Dict[str, Any],
        requestor_name: Dict[str, str],
        requestor_email: str,
        refund_type: str,
        sheet_link: str,
        slack_user_id: str
    ) -> Dict[str, Any]:
        """
        Build success message for order cancellation.
        
        Returns:
            Dict containing message text and action buttons
        """
        try:
            return self.message_builder.create_refund_decision_message(
                order_data={
                    "order": order_data,
                    "refund_calculation": refund_calculation,
                    "requestor_name": requestor_name,
                    "requestor_email": requestor_email,
                },
                requestor_name=requestor_name,
                requestor_email=requestor_email,
                refund_type=refund_type,
                sport_mention=self.message_builder.get_sport_group_mention(
                    order_data.get("line_items", [{}])[0].get("title", "")
                ),
                sheet_link=sheet_link,
                order_cancelled=True,
                slack_user_id=slack_user_id,
                original_timestamp=datetime.now().isoformat(),
            )
        except Exception as e:
            logger.error(f"Error building cancellation success message: {str(e)}")
            return {
                "text": f"Order cancelled successfully, but failed to build message: {str(e)}",
                "action_buttons": []
            }
