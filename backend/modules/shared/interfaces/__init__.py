"""
Domain service interfaces and DTOs.
Standard contracts for cross-layer communication.
"""

from .domain_service import DomainService
from .notification_dto import (
    NotificationRequest,
    NotificationResult,
    NotificationType,
    NotificationPriority
)

__all__ = [
    "DomainService",
    "NotificationRequest",
    "NotificationResult",
    "NotificationType",
    "NotificationPriority",
]

