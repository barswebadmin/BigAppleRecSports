"""
Slack-related Pydantic models for the Big Apple Rec Sports system.
Provides type-safe models for Slack notifications, interactions, and data structures.
"""

from pydantic import BaseModel, field_validator, ConfigDict
from typing import List, Optional, Dict, Union, Any
from enum import Enum
import re
from datetime import datetime


class RefundType(str, Enum):
    """Enum for refund types"""
    REFUND = "refund"
    CREDIT = "credit"


class SlackActionType(str, Enum):
    """Enum for Slack action types"""
    BUTTON = "button"
    SELECT = "select"
    TEXT_INPUT = "text_input"


class SlackMessageType(str, Enum):
    """Enum for Slack message types"""
    REFUND_REQUEST = "refund_request"
    REFUND_CONFIRMATION = "refund_confirmation"
    REFUND_DENIAL = "refund_denial"
    ORDER_UPDATE = "order_update"
    LEADERSHIP_NOTIFICATION = "leadership_notification"


class SlackUser(BaseModel):
    """Slack user information"""
    id: str
    name: Optional[str] = None
    email: Optional[str] = None
    display_name: Optional[str] = None


class SlackChannel(BaseModel):
    """Slack channel information"""
    id: str
    name: Optional[str] = None


class SlackAction(BaseModel):
    """Slack action button/input definition"""
    type: SlackActionType
    action_id: str
    text: str
    value: Optional[str] = None
    style: Optional[str] = None  # "primary", "danger", etc.
    confirm: Optional[Dict[str, Any]] = None


class SlackBlock(BaseModel):
    """Slack block for rich message formatting"""
    type: str
    text: Optional[Dict[str, str]] = None
    elements: Optional[List[SlackAction]] = None
    accessory: Optional[Dict[str, Any]] = None


class SlackMessage(BaseModel):
    """Base Slack message structure"""
    channel: str
    text: str
    blocks: Optional[List[SlackBlock]] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class RefundSlackNotificationRequest(BaseModel):
    """
    Request model for sending refund notifications to Slack.
    This is the main model for refund-related Slack notifications.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "order_number": "#12345",
                "requestor_name": {"first": "John", "last": "Doe"},
                "requestor_email": "john.doe@example.com",
                "refund_type": "refund",
                "notes": "Customer requested refund due to schedule conflict",
                "sheet_link": "https://docs.google.com/spreadsheets/d/11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw/edit#gid=1435845892&range=A5",
                "request_submitted_at": "2024-09-10T15:30:00Z"
            }
        }
    )
    
    order_number: str
    requestor_name: Union[str, Dict[str, str]]  # Can be string or {"first": "John", "last": "Doe"}
    requestor_email: str
    refund_type: RefundType
    notes: Optional[str] = None
    sheet_link: Optional[str] = None  # Google Sheets link to the specific row
    request_submitted_at: Optional[str] = None  # ISO 8601 timestamp when form was submitted
    
    @field_validator('requestor_name')
    @classmethod
    def convert_requestor_name(cls, v):
        """Convert string requestor_name to dict format if needed"""
        if isinstance(v, str):
            # If it's a string, try to split into first and last
            parts = v.strip().split(' ', 1)  # Split on first space only
            if len(parts) == 2:
                return {"first": parts[0], "last": parts[1]}
            else:
                # If only one name, put it in first name
                return {"first": v.strip(), "last": ""}
        elif isinstance(v, dict):
            # Ensure required keys exist
            return {
                "first": v.get("first", ""),
                "last": v.get("last", "")
            }
        else:
            raise ValueError(f"requestor_name must be string or dict, got {type(v)}")
    
    @field_validator('requestor_email')
    @classmethod
    def validate_email(cls, v):
        """Validate email format"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError(f"Invalid email format: {v}")
        return v


class SlackRefundConfirmation(BaseModel):
    """
    Model for refund confirmation messages sent to Slack.
    Used when a refund has been processed and confirmed.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "order_number": "#12345",
                "customer_name": "John Doe",
                "customer_email": "john.doe@example.com",
                "refund_amount": 25.00,
                "refund_type": "refund",
                "processed_by": "joe",
                "processed_at": "2024-09-10T16:30:00Z",
                "notes": "Refund processed successfully"
            }
        }
    )
    
    order_number: str
    customer_name: str
    customer_email: str
    refund_amount: float
    refund_type: RefundType
    processed_by: str
    processed_at: str
    notes: Optional[str] = None
    shopify_refund_id: Optional[str] = None


class SlackRefundDenial(BaseModel):
    """
    Model for refund denial messages sent to Slack.
    Used when a refund request has been denied.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "order_number": "#12345",
                "customer_name": "John Doe",
                "customer_email": "john.doe@example.com",
                "denial_reason": "Event already occurred",
                "denied_by": "joe",
                "denied_at": "2024-09-10T16:30:00Z",
                "notes": "Customer contacted after event date"
            }
        }
    )
    
    order_number: str
    customer_name: str
    customer_email: str
    denial_reason: str
    denied_by: str
    denied_at: str
    notes: Optional[str] = None


class SlackOrderUpdate(BaseModel):
    """
    Model for order update notifications sent to Slack.
    Used for general order status changes and updates.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "order_number": "#12345",
                "customer_name": "John Doe",
                "update_type": "status_change",
                "old_status": "pending",
                "new_status": "confirmed",
                "updated_by": "system",
                "updated_at": "2024-09-10T16:30:00Z",
                "notes": "Order confirmed after payment processing"
            }
        }
    )
    
    order_number: str
    customer_name: str
    update_type: str  # "status_change", "payment_update", "inventory_update", etc.
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    updated_by: str
    updated_at: str
    notes: Optional[str] = None
    order_data: Optional[Dict[str, Any]] = None


class ProcessLeadershipCSVRequest(BaseModel):
    """
    Request model for processing leadership CSV data.
    Originally from requests.py, now part of the Slack models system.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "csv_data": [
                    ["Email", "First Name", "Last Name", "Other Data"],
                    ["user1@example.com", "John", "Doe", "Some data"],
                    ["user2@example.com", "Jane", "Smith", "More data"],
                    ["not-an-email", "Invalid", "Entry", "Will be filtered"]
                ],
                "spreadsheet_title": "2024 Leadership List",
                "year": 2024
            }
        }
    )
    
    csv_data: List[List[str]]  # Array of arrays representing CSV rows
    spreadsheet_title: Optional[str] = None
    year: Optional[int] = None


class SlackLeadershipNotification(BaseModel):
    """
    Model for leadership-related notifications sent to Slack.
    Used for leadership CSV processing and updates.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "notification_type": "csv_processed",
                "spreadsheet_title": "2024 Leadership List",
                "year": 2024,
                "records_processed": 25,
                "records_added": 20,
                "records_updated": 5,
                "processed_by": "system",
                "processed_at": "2024-09-10T16:30:00Z",
                "notes": "Leadership CSV processed successfully"
            }
        }
    )
    
    notification_type: str  # "csv_processed", "leadership_update", "sync_complete", etc.
    spreadsheet_title: Optional[str] = None
    year: Optional[int] = None
    records_processed: Optional[int] = None
    records_added: Optional[int] = None
    records_updated: Optional[int] = None
    processed_by: str
    processed_at: str
    notes: Optional[str] = None
    csv_data: Optional[List[List[str]]] = None


class SlackInteractionPayload(BaseModel):
    """
    Model for Slack interaction payloads (button clicks, form submissions, etc.)
    """
    type: str
    user: Optional[SlackUser] = None
    channel: Optional[SlackChannel] = None
    actions: Optional[List[Dict[str, Any]]] = None
    trigger_id: Optional[str] = None
    view: Optional[Dict[str, Any]] = None
    response_url: Optional[str] = None


class SlackModalSubmission(BaseModel):
    """
    Model for Slack modal form submissions
    """
    type: str
    user: SlackUser
    view: Dict[str, Any]
    trigger_id: str
    
    def get_form_values(self) -> Dict[str, Any]:
        """Extract form values from the modal submission"""
        values = {}
        if "state" in self.view and "values" in self.view["state"]:
            for block_id, block_values in self.view["state"]["values"].items():
                for action_id, action_data in block_values.items():
                    if "value" in action_data:
                        values[action_id] = action_data["value"]
        return values


class SlackWebhookEvent(BaseModel):
    """
    Model for Slack webhook events
    """
    token: str
    team_id: str
    api_app_id: str
    event: Dict[str, Any]
    type: str
    event_id: str
    event_time: int
    authorizations: Optional[List[Dict[str, Any]]] = None
    is_ext_shared_channel: Optional[bool] = None
    event_context: Optional[str] = None


# Button Classes for Slack Actions
class SlackButton:
    """Base class for Slack button definitions"""
    
    @staticmethod
    def create_button(
        text: str,
        action_id: str,
        value: str,
        style: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a Slack button dictionary"""
        button = {
            "type": "button",
            "text": {"type": "plain_text", "text": text},
            "action_id": action_id,
            "value": value
        }
        if style:
            button["style"] = style
        return button


class RefundButtons:
    """Button definitions for refund-related actions"""
    
    @staticmethod
    def process_refund(order_number: str) -> Dict[str, Any]:
        """Create a 'Process Refund' button"""
        return SlackButton.create_button(
            text="Process Refund",
            action_id="process_refund",
            value=order_number,
            style="primary"
        )
    
    @staticmethod
    def custom_amount(order_number: str) -> Dict[str, Any]:
        """Create a 'Custom Amount' button"""
        return SlackButton.create_button(
            text="Custom Amount",
            action_id="custom_refund_amount",
            value=order_number
        )
    
    @staticmethod
    def no_refund(order_number: str) -> Dict[str, Any]:
        """Create a 'No Refund' button"""
        return SlackButton.create_button(
            text="No Refund",
            action_id="no_refund",
            value=order_number,
            style="danger"
        )
    
    @staticmethod
    def edit_details(order_number: str) -> Dict[str, Any]:
        """Create an 'Edit Details' button"""
        return SlackButton.create_button(
            text="Edit Details",
            action_id="edit_request_details",
            value=order_number
        )
    
    @staticmethod
    def deny_request(order_number: str) -> Dict[str, Any]:
        """Create a 'Deny Request' button"""
        return SlackButton.create_button(
            text="Deny Request",
            action_id="deny_refund_request",
            value=order_number,
            style="danger"
        )
    
    @staticmethod
    def get_error_buttons(order_number: str) -> List[Dict[str, Any]]:
        """Get buttons for error scenarios"""
        return [
            RefundButtons.edit_details(order_number),
            RefundButtons.deny_request(order_number)
        ]
    
    @staticmethod
    def get_success_buttons(order_number: str) -> List[Dict[str, Any]]:
        """Get buttons for successful refund calculation"""
        return [
            RefundButtons.process_refund(order_number),
            RefundButtons.custom_amount(order_number),
            RefundButtons.no_refund(order_number)
        ]


# Convenience classes for easy access
class Slack:
    """
    Main Slack models namespace for easy access to all Slack-related models.
    
    Usage:
        Slack.RefundConfirmation(...)
        Slack.RefundDenial(...)
        Slack.OrderUpdate(...)
        Slack.LeadershipNotification(...)
    """
    
    # Request models
    RefundNotification = RefundSlackNotificationRequest
    ProcessLeadershipCSV = ProcessLeadershipCSVRequest
    
    # Confirmation/Status models
    RefundConfirmation = SlackRefundConfirmation
    RefundDenial = SlackRefundDenial
    OrderUpdate = SlackOrderUpdate
    LeadershipNotification = SlackLeadershipNotification
    
    # Interaction models
    InteractionPayload = SlackInteractionPayload
    ModalSubmission = SlackModalSubmission
    WebhookEvent = SlackWebhookEvent
    
    # Base models
    User = SlackUser
    Channel = SlackChannel
    Action = SlackAction
    Block = SlackBlock
    Message = SlackMessage
    
    # Button classes
    Button = SlackButton
    RefundButtons = RefundButtons
    
    # Enums
    RefundType = RefundType
    ActionType = SlackActionType
    MessageType = SlackMessageType
