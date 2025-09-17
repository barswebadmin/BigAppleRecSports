"""
Slack Utilities - Comprehensive Slack functionality
Converted from GAS SlackUtils.gs for Python usage
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from .secrets_utils import get_secret
from .api_utils import (
    make_api_request,
    normalize_order_number,
    format_two_decimal_points,
)

logger = logging.getLogger(__name__)


class SlackClient:
    """Slack API client for sending messages and managing channels"""

    def __init__(
        self, bot_token: Optional[str] = None
    ):
        """
        Initialize Slack client

        Args:
            bot_token: Slack bot token (will try to get from secrets if not provided)
            default_channel: Default channel ID for messages
        """
        self.bot_token = bot_token or self._get_slack_bot_token("general")
        self.api_base_url = "https://slack.com/api"

    def _get_slack_bot_token(self, purpose: str = "general") -> str:
        """
        Get Slack Bot Token from secrets

        Args:
            purpose: Purpose of the token (general, refunds, leadership, etc.)

        Returns:
            Slack bot token
        """
        token_map = {
            "refunds": "SLACK_BOT_TOKEN_REFUNDS",
            "leadership": "SLACK_BOT_TOKEN_LEADERSHIP",
            "payment": "SLACK_BOT_TOKEN_PAYMENT",
            "general": "SLACK_BOT_TOKEN_GENERAL",
            "waitlist": "SLACK_BOT_TOKEN_WAITLIST",
        }
        secret_key = token_map.get(purpose, "SLACK_BOT_TOKEN_GENERAL")

        try:
            token = get_secret(secret_key)
            if not token:
                logger.warning(
                    f"Secret '{secret_key}' not found. Using fallback SLACK_BOT_TOKEN."
                )
                token = get_secret("SLACK_BOT_TOKEN")
            return token or ""
        except Exception as e:
            logger.error(f"Error getting Slack token: {e}")
            raise ValueError(f"Could not retrieve Slack token for purpose: {purpose}")

    def send_message(
        self,
        channel: str,
        text: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None,
        thread_ts: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Send a message to Slack

        Args:
            channel: Channel ID or name
            text: Message text (fallback for blocks)
            blocks: Slack blocks for rich formatting
            thread_ts: Thread timestamp for replies
            **kwargs: Additional Slack API parameters

        Returns:
            API response
        """

        if not channel:
            raise ValueError("Channel is required")

        payload = {
            "channel": channel,
            "text": text,
            "blocks": blocks,
            "thread_ts": thread_ts,
            **kwargs,
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        return make_api_request(
            url=f"{self.api_base_url}/chat.postMessage",
            method="POST",
            headers={"Authorization": f"Bearer {self.bot_token}"},
            payload=payload,
        )

    def update_message(
        self,
        channel: str,
        ts: str,
        text: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Update an existing Slack message

        Args:
            channel: Channel ID
            ts: Message timestamp
            text: Updated message text
            blocks: Updated blocks
            **kwargs: Additional parameters

        Returns:
            API response
        """
        payload = {
            "channel": channel,
            "ts": ts,
            "text": text,
            "blocks": blocks,
            **kwargs,
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        return make_api_request(
            url=f"{self.api_base_url}/chat.update",
            method="POST",
            headers={"Authorization": f"Bearer {self.bot_token}"},
            payload=payload,
        )


def get_order_url(order_id: str, order_number: str) -> str:
    """
    Get formatted order URL for Slack messages

    Args:
        order_id: Order ID from Shopify
        order_number: Order name/number

    Returns:
        Formatted Slack link
    """
    order_id_digits = order_id.split("/")[-1] if "/" in order_id else order_id
    normalized_order = normalize_order_number(order_number)
    return f"<https://admin.shopify.com/store/09fe59-3/orders/{order_id_digits}|{normalized_order}>"


def get_product_url(product: Dict[str, Any]) -> str:
    """
    Get formatted product URL for Slack messages

    Args:
        product: Product object with productId

    Returns:
        Product URL
    """
    product_id = product["productId"].split("/")[-1]
    return f"https://admin.shopify.com/store/09fe59-3/products/{product_id}"


def get_slack_group_id(product_title: str) -> str:
    """
    Get Slack group ID for product notifications

    Args:
        product_title: Product title to check

    Returns:
        Slack group mention string
    """
    title = product_title.lower()

    if "kickball" in title:
        return "<!subteam^S08L2521XAM>"
    elif "bowling" in title:
        return "<!subteam^S08KJJ02738>"
    elif "pickleball" in title:
        return "<!subteam^S08KTJ33Z9R>"
    elif "dodgeball" in title:
        return "<!subteam^S08KJJ5CL4W>"

    return "@here"  # fallback


def create_confirm_button(
    email_matches: bool,
    requestor_name: Dict[str, str],
    refund_or_credit: str,
    refund_amount: Union[str, float],
    raw_order_number: str,
    order_id: str,
) -> Dict[str, Any]:
    """
    Create confirm refund button

    Args:
        email_matches: Whether emails match
        requestor_name: Dict with 'first' and 'last' keys
        refund_or_credit: 'refund' or 'credit'
        refund_amount: Refund amount
        raw_order_number: Order number
        order_id: Order ID

    Returns:
        Slack button object
    """
    formatted_amount = (
        int(refund_amount)
        if float(refund_amount).is_integer()
        else format_two_decimal_points(refund_amount)
    )

    button_text = (
        f"✅ Process ${formatted_amount} Refund"
        if refund_or_credit == "refund"
        else f"✅ Issue ${formatted_amount} Store Credit"
    )

    button = {
        "type": "button",
        "text": {"type": "plain_text", "text": button_text},
        "action_id": "approve_refund",
        "value": f"rawOrderNumber={raw_order_number}|orderId={order_id}|refundAmount={refund_amount}",
        "confirm": {
            "title": {"type": "plain_text", "text": "Confirm Approval"},
            "text": {
                "type": "plain_text",
                "text": f"You are about to issue {requestor_name['first']} {requestor_name['last']} a {refund_or_credit} for ${formatted_amount}. Proceed?",
            },
            "confirm": {"type": "plain_text", "text": "Yes, confirm"},
            "deny": {"type": "plain_text", "text": "Cancel"},
        },
    }

    if email_matches:
        button["style"] = "primary"

    return button


def create_deny_button(raw_order_number: str) -> Dict[str, Any]:
    """
    Create deny refund button

    Args:
        raw_order_number: Order number

    Returns:
        Slack button object
    """
    return {
        "type": "button",
        "text": {"type": "plain_text", "text": "❌ Deny"},
        "style": "danger",
        "action_id": "deny_refund",
        "value": f"rawOrderNumber={raw_order_number}",
        "confirm": {
            "title": {"type": "plain_text", "text": "Confirm Denial"},
            "text": {
                "type": "plain_text",
                "text": "Are you sure? The requestor will be notified.",
            },
            "confirm": {"type": "plain_text", "text": "Yes, Deny"},
            "deny": {"type": "plain_text", "text": "Cancel"},
        },
    }


def create_refund_different_amount_button(
    order_id: str,
    order_number: str,
    requestor_name: Dict[str, str],
    requestor_email: str,
    refund_or_credit: str,
    refund_amount: Union[str, float],
    raw_order_number: str,
) -> Dict[str, Any]:
    """
    Create custom refund amount button

    Returns:
        Slack button object
    """
    button_text = (
        "✏️ Process custom Refund amt"
        if refund_or_credit.lower() == "refund"
        else "✏️ Issue custom Store Credit amt"
    )

    return {
        "type": "button",
        "text": {"type": "plain_text", "text": button_text},
        "action_id": "refund_different_amount",
        "value": f"orderId={order_id}|refundAmount={refund_amount}|rawOrderNumber={raw_order_number}",
    }


def create_cancel_button(raw_order_number: str) -> Dict[str, Any]:
    """
    Create cancel request button

    Args:
        raw_order_number: Order number

    Returns:
        Slack button object
    """
    return {
        "type": "button",
        "text": {"type": "plain_text", "text": "❌ Cancel and Close Request"},
        "style": "danger",
        "action_id": "cancel_refund_request",
        "value": f"rawOrderNumber={raw_order_number}",
        "confirm": {
            "title": {"type": "plain_text", "text": "Confirm Cancellation"},
            "text": {
                "type": "plain_text",
                "text": "Are you sure you want to cancel and close this request?",
            },
            "confirm": {"type": "plain_text", "text": "Yes, cancel and close it"},
            "deny": {"type": "plain_text", "text": "No, keep it"},
        },
    }


def create_restock_inventory_buttons(
    order_id: str,
    refund_amount: Union[str, float],
    formatted_order_number: str,
    inventory_list: Dict[str, Dict[str, Any]],
    inventory_order: List[str],
    slack_user_name: str,
) -> List[Dict[str, Any]]:
    """
    Create inventory restock buttons

    Returns:
        List of Slack button objects
    """
    buttons = []

    for key in inventory_order:
        variant = inventory_list.get(key)
        if variant and variant.get("variantId"):
            name_without_registration = (
                variant["name"].replace(" Registration", "").strip()
            )

            button = {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": f"Restock {name_without_registration}",
                },
                "action_id": f"restock_{name_without_registration.lower()}",
                "value": "|".join(
                    [
                        f"inventoryItemId={variant['inventoryId']}",
                        f"orderId={order_id}",
                        f"refundAmount={refund_amount}",
                        f"orderNumber={formatted_order_number}",
                        f"approverName={slack_user_name}",
                    ]
                ),
                "confirm": {
                    "title": {
                        "type": "plain_text",
                        "text": f"Confirm Restocking {name_without_registration}",
                    },
                    "text": {
                        "type": "plain_text",
                        "text": f"You are about to restock 1 spot to {name_without_registration}. Confirm?",
                    },
                    "confirm": {"type": "plain_text", "text": "Yes, confirm"},
                    "deny": {"type": "plain_text", "text": "No, go back"},
                },
            }
            buttons.append(button)

    # Add "Do not restock" option
    buttons.append(
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Do not restock - all done!"},
            "action_id": "do_not_restock",
            "value": "|".join(
                [
                    f"orderId={order_id}",
                    f"refundAmount={refund_amount}",
                    f"orderNumber={formatted_order_number}",
                ]
            ),
            "confirm": {
                "title": {"type": "plain_text", "text": "Confirm No Restocking"},
                "text": {
                    "type": "plain_text",
                    "text": "Are you sure you do not want to restock inventory?",
                },
                "confirm": {"type": "plain_text", "text": "Yes, confirm"},
                "deny": {"type": "plain_text", "text": "No, go back"},
            },
        }
    )

    return buttons


def send_waitlist_validation_error(
    league: str,
    email: str,
    reason: str,
    product_handle: str,
    slack_client: Optional[SlackClient] = None,
) -> bool:
    """
    Send waitlist validation error to joe-test channel

    Args:
        league: League name
        email: User email
        reason: Validation failure reason
        product_handle: Product handle that was checked
        slack_client: Optional Slack client instance

    Returns:
        Success status
    """
    try:
        if not slack_client:
            slack_client = SlackClient()

        # Hardcoded joe-test channel config (shared utilities don't have access to backend config)
        channel_config = {
            "name": "#joe-test",
            "channel_id": get_secret("SLACK_CHANNEL_JOE_TEST"),
            "bearer_token": get_secret("SLACK_BOT_TOKEN_WAITLIST", get_secret("SLACK_BOT_TOKEN", "")),
        }

        error_icon = "🚫" if "No product found" in reason else "📦"
        title = (
            "Product Not Found"
            if "No product found" in reason
            else "Inventory Available"
        )

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{error_icon} Waitlist Validation Error",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Error Type:*\n{title}"},
                    {"type": "mrkdwn", "text": f"*League:*\n{league}"},
                    {"type": "mrkdwn", "text": f"*User Email:*\n{email}"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Product Handle:*\n`{product_handle}`",
                    },
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Reason:* {reason}"},
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 🤖 Waitlist Script Validation",
                    }
                ],
            },
        ]

        result = slack_client.send_message(
            channel=channel_config["channel_id"],
            text=f"{error_icon} Waitlist Validation Error: {title}",
            blocks=blocks,
        )

        if result.get("ok") or result.get("success"):
            logger.info(f"Sent waitlist validation error to #joe-test for {email}")
            return True
        else:
            logger.error(f"Failed to send waitlist validation error: {result}")
            return False

    except Exception as e:
        logger.error(f"Error in send_waitlist_validation_error: {e}")
        return False


# Convenience functions using default client
def send_slack_message(
    channel: str,
    text: Optional[str] = None,
    blocks: Optional[List[Dict[str, Any]]] = None,
    thread_ts: Optional[str] = None,
    bot_token: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Send a Slack message using default client

    Args:
        channel: Channel ID or name
        text: Message text
        blocks: Slack blocks
        thread_ts: Thread timestamp
        bot_token: Optional bot token override
        **kwargs: Additional parameters

    Returns:
        API response
    """
    client = SlackClient(bot_token=bot_token)
    return client.send_message(channel, text, blocks, thread_ts, **kwargs)


def update_slack_message(
    channel: str,
    ts: str,
    text: Optional[str] = None,
    blocks: Optional[List[Dict[str, Any]]] = None,
    bot_token: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Update a Slack message using default client

    Args:
        channel: Channel ID
        ts: Message timestamp
        text: Updated text
        blocks: Updated blocks
        bot_token: Optional bot token override
        **kwargs: Additional parameters

    Returns:
        API response
    """
    client = SlackClient(bot_token=bot_token)
    return client.update_message(channel, ts, text, blocks, **kwargs)
