"""
Modal handling logic for Slack interactions.
Separated from slack_service.py to keep that file focused on service coordination.
"""

import json
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

from typing import Union, Any
from utils.date_utils import format_date_and_time

logger = logging.getLogger(__name__)


class SlackModalHandlers:
    """Handles Slack modal creation, display, and submission processing"""

    def __init__(self, api_client: Any, gas_webhook_url: str):
        self.api_client = api_client
        self.gas_webhook_url = gas_webhook_url

    async def show_deny_refund_request_modal(
        self,
        request_data: Dict[str, str],
        channel_id: str,
        thread_ts: str,
        slack_user_name: str,
        slack_user_id: str,
        trigger_id: str,
        current_message_full_text: str,
    ) -> Dict[str, Any]:
        """
        Show the denial modal for any refund request type - handles modal construction and display
        """
        print("\n🚫 === SHOWING DENY REFUND REQUEST MODAL ===")
        print(f"📦 Request Data: {json.dumps(request_data, indent=2)}")
        print(f"👤 User: {slack_user_name} (ID: {slack_user_id})")
        print(f"🎯 Trigger ID: {trigger_id}")
        print("🚫 === END MODAL SHOW DEBUG ===\n")

        try:
            # Extract request details from the button value
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
                refund_type=refund_type,
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
                "slack_user_id": slack_user_id,
            }

            # Show the modal
            modal_result = self._show_modal_to_user(
                trigger_id=trigger_id,
                modal_title="Deny Refund Request",
                modal_blocks=modal_blocks,
                callback_id="deny_refund_request_modal_submission",
                private_metadata=json.dumps(private_metadata),
            )

            if modal_result.get("success"):
                print("✅ Deny request modal shown successfully")
                return {"success": True, "message": "Modal displayed"}
            else:
                error_msg = modal_result.get("error", "Unknown modal error")
                print(f"❌ Failed to show deny modal: {error_msg}")
                return {"success": False, "message": f"Slack API error: {error_msg}"}

        except Exception as e:
            error_message = f"Exception in show_deny_refund_request_modal: {str(e)}"
            logger.error(f"❌ {error_message}")
            return {"success": False, "error": error_message}

    async def handle_deny_refund_request_modal_submission(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle modal submission for denial - extract form data, send email via GAS, update Slack
        """
        print("\n🚫 === DENY REQUEST MODAL SUBMISSION ===")
        print(f"📋 Full Payload: {json.dumps(payload, indent=2)}")
        print("=== END DENY SUBMISSION DEBUG ===\n")

        try:
            # Extract form values
            values = payload.get("view", {}).get("state", {}).get("values", {})
            custom_message = (
                values.get("custom_message_input", {})
                .get("custom_message", {})
                .get("value", "")
            )
            include_staff_checkboxes = (
                values.get("include_staff_info", {})
                .get("include_staff_info", {})
                .get("selected_options", [])
            )
            include_staff_info = len(include_staff_checkboxes) > 0

            # Extract metadata
            private_metadata_str = payload.get("view", {}).get("private_metadata", "{}")
            private_metadata = json.loads(private_metadata_str)

            original_thread_ts = private_metadata.get("original_thread_ts")
            original_channel_id = private_metadata.get("original_channel_id")
            slack_user_name = private_metadata.get("slack_user_name", "Unknown")
            slack_user_id = private_metadata.get("slack_user_id", "Unknown")
            raw_order_number = private_metadata.get("raw_order_number", "")
            requestor_email = private_metadata.get("requestor_email", "")
            first_name = private_metadata.get("first_name", "")
            last_name = private_metadata.get("last_name", "")

            print("✉️ Sending denial email via GAS with:")
            print(f"   Order: {raw_order_number}")
            print(f"   Requestor: {first_name} {last_name} ({requestor_email})")
            print(f"   Custom Message: {custom_message[:100]}...")
            print(f"   Include Staff Info: {include_staff_info}")
            print(f"   Staff: {slack_user_name} ({slack_user_id})")

            # NOTE: GAS email integration removed - denial emails no longer sent automatically
            print("✅ Denial processed (GAS email integration removed)")

            # Update original Slack message
            denial_confirmation_message = self._build_denial_confirmation_message(
                order_number=raw_order_number,
                requestor_email=requestor_email,
                first_name=first_name,
                last_name=last_name,
                slack_user_name=slack_user_name,
                custom_message_provided=bool(custom_message.strip()),
                include_staff_info=include_staff_info,
            )

            # Update the original Slack message
            await self._update_slack_message(
                channel_id=original_channel_id,
                message_ts=original_thread_ts,
                message_text=denial_confirmation_message,
            )

            return {"response_action": "clear"}

        except Exception as e:
            logger.error(
                f"❌ Exception in handle_deny_refund_request_modal_submission: {str(e)}"
            )
            return {"response_action": "clear"}

    def _build_deny_request_modal_blocks(
        self,
        raw_order_number: str,
        requestor_email: str,
        first_name: str,
        last_name: str,
        refund_type: str,
    ) -> List[Dict[str, Any]]:
        """Build the modal blocks for the deny request form - use the one from slack_refunds_utils"""
        # Import the slack_refunds_utils to use its method
        from .slack_refunds_utils import SlackRefundsUtils

        # Create a temporary instance to access the method
        # This is a bit of a workaround but avoids duplicating the logic
        temp_utils = SlackRefundsUtils(None, None)  # type: ignore
        return temp_utils._build_deny_request_modal_blocks(
            raw_order_number=raw_order_number,
            requestor_email=requestor_email,
            first_name=first_name,
            last_name=last_name,
            refund_type=refund_type,
        )

    def _show_modal_to_user(
        self,
        trigger_id: str,
        modal_title: str,
        modal_blocks: List[Dict[str, Any]],
        callback_id: str,
        private_metadata: str,
    ) -> Dict[str, Any]:
        """Display a modal to the user"""
        modal_view = {
            "type": "modal",
            "callback_id": callback_id,
            "title": {"type": "plain_text", "text": modal_title},
            "submit": {"type": "plain_text", "text": "Send Denial"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": modal_blocks,
            "private_metadata": private_metadata,
        }

        return self.api_client.send_modal(trigger_id, modal_view)

    # NOTE: GAS denial email integration removed
    # Refund denial emails are no longer sent automatically via Google Apps Script

    def _build_denial_confirmation_message(
        self,
        order_number: str,
        requestor_email: str,
        first_name: str,
        last_name: str,
        slack_user_name: str,
        custom_message_provided: bool,
        include_staff_info: bool,
    ) -> str:
        """Build the Slack message confirming the denial was processed"""
        current_time = format_date_and_time(datetime.now(timezone.utc))

        message = "🚫 *Refund Request Denied*\n\n"
        message += f"*Order Number:* {order_number}\n"
        message += f"*Requestor:* {first_name} {last_name} ({requestor_email})\n"
        message += f"*Denied by:* {slack_user_name}\n"
        message += f"*Denied at:* {current_time}\n\n"

        if custom_message_provided:
            message += "📧 *Custom denial message sent to requestor.*\n"
        else:
            message += "📧 *Default denial message sent to requestor.*\n"

        if include_staff_info:
            message += "👤 *Staff contact info included for direct follow-up.*"
        else:
            message += "📬 *Replies will go to web@bigapplerecsports.com*"

        return message

    async def _update_slack_message(
        self, channel_id: str, message_ts: str, message_text: str
    ) -> Dict[str, Any]:
        """Update a Slack message with new content"""
        try:
            return self.api_client.update_message(
                message_ts=message_ts,
                message_text=message_text,
                action_buttons=[],  # No buttons for denial confirmation
            )
        except Exception as e:
            logger.error(f"❌ Failed to update Slack message: {str(e)}")
            return {"success": False, "error": str(e)}
