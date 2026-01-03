"""
Standard Data Transfer Objects for cross-layer communication.

These DTOs allow domain services to request notifications without
knowing about specific notification channels (Slack, email, SMS, etc.).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime


class NotificationType(Enum):
    """Types of notifications that can be sent."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    ALERT = "alert"


class NotificationPriority(Enum):
    """Priority levels for notifications."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class NotificationRecipient:
    """Identifies who should receive a notification."""
    id: str  # User/channel ID in the target system
    type: str = "user"  # "user" or "channel"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationRequest:
    """
    Standard DTO for requesting notifications from domain services.
    
    Domain services create this object when they need to notify someone.
    Integration layers (Slack, email, etc.) translate this into their format.
    """
    recipient: NotificationRecipient
    message_type: NotificationType
    title: str
    body: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    data: Dict[str, Any] = field(default_factory=dict)
    actions: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    thread_id: Optional[str] = None  # For threaded notifications
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "recipient": {
                "id": self.recipient.id,
                "type": self.recipient.type,
                "metadata": self.recipient.metadata
            },
            "message_type": self.message_type.value,
            "title": self.title,
            "body": self.body,
            "priority": self.priority.value,
            "data": self.data,
            "actions": self.actions,
            "metadata": self.metadata,
            "thread_id": self.thread_id
        }


@dataclass
class NotificationResult:
    """
    Result of sending a notification.
    
    Returned by integration layers to confirm delivery.
    """
    success: bool
    message_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    channel: Optional[str] = None  # Which channel was used (slack, email, etc.)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def success_result(
        cls, 
        message_id: str, 
        channel: str,
        metadata: Dict[str, Any] = None
    ) -> "NotificationResult":
        """Create a successful result."""
        return cls(
            success=True,
            message_id=message_id,
            timestamp=datetime.now(),
            channel=channel,
            metadata=metadata or {}
        )
    
    @classmethod
    def error_result(
        cls, 
        error: str, 
        metadata: Dict[str, Any] = None
    ) -> "NotificationResult":
        """Create an error result."""
        return cls(
            success=False,
            error=error,
            metadata=metadata or {}
        )

