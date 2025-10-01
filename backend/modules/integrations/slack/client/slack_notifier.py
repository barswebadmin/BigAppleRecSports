from typing import Protocol, Dict, Any, Optional


class SlackNotifierProtocol(Protocol):
    """Typed facade for Slack notifications.

    This interface is intentionally transport-agnostic. Implementations should
    orchestrate message composition (via builders) and delivery (via client)
    without embedding business logic (orders/products decisions).
    """

    # Generic messaging
    def send_plain_text(self, channel: "SlackConfig.Channels._Channel", bot: "SlackConfig.Bots._Bot", text: str, *, thread_ts: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]: ...
    def send_blocks(self, channel: "SlackConfig.Channels._Channel", bot: "SlackConfig.Bots._Bot", blocks: list[Dict[str, Any]], *, thread_ts: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, action_buttons: Optional[list[Dict[str, Any]]] = None) -> Dict[str, Any]: ...

    # Domain-oriented notification facades (no business rules here)
    def refund_requested(self, event: Dict[str, Any]) -> Dict[str, Any]: ...
    def order_cancelled(self, event: Dict[str, Any]) -> Dict[str, Any]: ...
    def restock_required(self, event: Dict[str, Any]) -> Dict[str, Any]: ...


# Concrete notifier implementation
import logging
from typing import List

from modules.integrations.slack.slack_orchestrator import SlackOrchestrator
from modules.integrations.slack.builders.message_builder import SlackMessageBuilder
from config import config


logger = logging.getLogger(__name__)


class SlackNotifier:
    """Thin orchestrator that formats Slack messages via builders and delivers via client.

    - No business logic (decisions about when/what to notify live in domain services)
    - Converts provided text/DTOs into Slack blocks and calls SlackClient
    """

    def __init__(self, client: Optional[SlackClient] = None, builder: Optional[SlackMessageBuilder] = None) -> None:
        self.client = client or SlackClient()
        # sport groups are resolved internally by SlackMessageBuilder
        self.builder = builder or SlackMessageBuilder(sport_groups={})

    # Generic messaging -----------------------------------------------------
    def send_plain_text(
        self,
        channel: "SlackConfig.Channels._Channel",
        bot: "SlackConfig.Bots._Bot",
        text: str,
        *,
        thread_ts: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        block = self.builder.build_section_block(text)
        return self.client.send_message(
            channel=channel,
            bot=bot,
            blocks=[block],
            metadata=metadata,
            thread_ts=thread_ts,
        )

    def send_blocks(
        self,
        channel: "SlackConfig.Channels._Channel",
        bot: "SlackConfig.Bots._Bot",
        blocks: List[Dict[str, Any]],
        *,
        action_buttons: Optional[List[Dict[str, Any]]] = None,
        thread_ts: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self.client.send_message(
            channel=channel,
            bot=bot,
            blocks=blocks,
            action_buttons=action_buttons,
            metadata=metadata,
            thread_ts=thread_ts,
        )

    # Domain-oriented facades ----------------------------------------------
    def refund_requested(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Format and send a refund request notification.

        Expected event keys (producer-owned contract):
        - channel: SlackConfig channel object
        - bot: SlackConfig bot object
        - order_data, refund_calculation, requestor_info, sheet_link
        """
        try:
            channel = event["channel"]
            bot = event["bot"]
            order_data = event.get("order_data", {})
            refund_calculation = event.get("refund_calculation", {})
            requestor_info = event.get("requestor_info", {})
            sheet_link = event.get("sheet_link", "")

            built = self.builder.build_success_message(
                order_data=order_data,
                refund_calculation=refund_calculation,
                requestor_info=requestor_info,
                sheet_link=sheet_link,
                request_initiated_at=event.get("request_initiated_at"),
                slack_channel_name=event.get("slack_channel_name"),
                mention_strategy=event.get("mention_strategy"),
            )

            text = built.get("text", "")
            block = self.builder.build_section_block(text)
            action_buttons = built.get("action_buttons") or []

            return self.send_blocks(channel, bot, [block], action_buttons=action_buttons, metadata=event.get("metadata"))
        except Exception as e:
            logger.error(f"SlackNotifier.refund_requested error: {e}")
            return {"success": False, "error": str(e)}

    def order_cancelled(self, event: Dict[str, Any]) -> Dict[str, Any]:
        # Placeholder for future specialized formatting
        try:
            channel = event["channel"]
            bot = event["bot"]
            message = event.get("message", "Order cancelled")
            return self.send_plain_text(channel, bot, message, thread_ts=event.get("thread_ts"))
        except Exception as e:
            logger.error(f"SlackNotifier.order_cancelled error: {e}")
            return {"success": False, "error": str(e)}

    def restock_required(self, event: Dict[str, Any]) -> Dict[str, Any]:
        # Placeholder for future specialized formatting
        try:
            channel = event["channel"]
            bot = event["bot"]
            message = event.get("message", "Restock required")
            return self.send_plain_text(channel, bot, message, thread_ts=event.get("thread_ts"))
        except Exception as e:
            logger.error(f"SlackNotifier.restock_required error: {e}")
            return {"success": False, "error": str(e)}
