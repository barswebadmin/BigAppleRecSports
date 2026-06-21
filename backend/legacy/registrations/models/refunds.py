from __future__ import annotations

from datetime import datetime
from typing import Literal, Self

from pydantic import EmailStr, Field, model_validator

from .api_base_model import ApiBaseModel
from .types import NormalizedInt

RefundMethod = Literal["store_credit", "original_payment"]


class RefundEstimateBreakdown(ApiBaseModel):
    amount: float
    percentage: int
    penalty: int
    message: str


class RequestRefundAnalysisData(ApiBaseModel):
    order_id: str
    order_name: str | None = None
    email_address: str
    product_id: str | None = None
    order_total: float
    total_refunded: float
    refundable_balance: float
    is_cancelled: bool
    has_existing_refunds: bool
    estimated_refund_to_original: RefundEstimateBreakdown | None = None
    estimated_store_credit: RefundEstimateBreakdown | None = None
    eligible: bool
    warnings: list[str] = Field(default_factory=list)


class RefundRequestInput(ApiBaseModel):
    """Route 1: POST /orders/request-refund

    Validates the initial refund request — order lookup + eligibility check.
    At least one of order_id or order_number is required.
    email_address is required for identity verification against the order.
    """

    order_id: NormalizedInt | None = None
    order_number: NormalizedInt | None = None
    email_address: EmailStr
    refund_method: RefundMethod
    created_at: datetime
    notes: str | None = None

    @model_validator(mode="after")
    def _require_order_identifier(self) -> Self:
        if self.order_id is None and self.order_number is None:
            raise ValueError("One of order_id or order_number is required")
        return self


class RefundCreateInput(ApiBaseModel):
    """Route 2: POST /orders/{order_id}/refunds

    Validates the confirmed refund execution. Separate lifecycle from the request —
    the client got the resolved order_id from the request step and sends it back.

    The service layer calls model_dump() on this and passes the dict to the Shopify client.
    The Shopify RefundInput model parses from that dict using AliasChoices to map
    should_notify → notify, notes → note, refund_method → refund_type.
    """

    order_id: NormalizedInt
    amount: float = Field(gt=0)
    refund_method: RefundMethod
    should_notify: bool
    notes: str | None = None


class RefundRequest(ApiBaseModel):
    """POST /registrations/refunds body — lookup + execute (until split into request-refund + create)."""

    order_id: NormalizedInt | None = None
    order_number: NormalizedInt | None = None
    amount: float = Field(gt=0)
    refund_method: RefundMethod
    should_notify: bool
    notes: str | None = None

    @model_validator(mode="after")
    def _require_order_identifier(self) -> Self:
        if self.order_id is None and self.order_number is None:
            raise ValueError("One of order_id or order_number is required")
        return self

    @property
    def notify_player(self) -> bool:
        return self.should_notify
