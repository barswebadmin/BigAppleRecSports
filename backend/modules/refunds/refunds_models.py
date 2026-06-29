"""Refund request/response models and Shopify mutation input builders."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel

from lib.tooling.datetime import parse_timestamp_string


def _shopify_id_digits_only(v: int | str) -> int:
    return int(str(v).strip().split("/")[-1].strip("#+"))


NormalizedInt = Annotated[int, BeforeValidator(_shopify_id_digits_only)]
ParsedDatetime = Annotated[datetime, BeforeValidator(parse_timestamp_string)]

RefundMethod = Literal["store_credit", "original_payment", "transfer"]
RestockLane = Literal["veteran", "early", "general", "waitlist"]


class RefundBaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        str_strip_whitespace=True,
    )


class RefundEstimateBreakdown(RefundBaseModel):
    amount: float
    percentage: int
    penalty: int
    message: str


class RequestRefundAnalysisData(RefundBaseModel):
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


class RefundRequest(RefundBaseModel):
    """POST /refunds/{order_number}/validate — form-driven refund request body."""

    first_name: str
    last_name: str
    email: EmailStr = Field(validation_alias="emailAddress")
    refund_method: RefundMethod
    transfer_to: str | None = None
    created_at: ParsedDatetime
    notes: str | None = None
    source: Literal["google"] | None = None


class RefundApproval(RefundBaseModel):
    """POST /refunds/{order_id}/approve and POST /orders/{order_id}/refund — execute refund."""

    amount: Decimal = Field(gt=0)
    refund_method: RefundMethod
    parent_transaction_id: str | None = None
    should_notify: bool = True
    note: str | None = None


class TierEstimate(TypedDict):
    amount: float
    percentage: int
    tierLabel: str
    appliedProcessingFee: float
    notes: list[str]


class OrderInfo(TypedDict):
    id: str
    number: str
    customerName: str
    email: str
    amountPaid: float
    currency: str


class ProductInfo(TypedDict):
    id: str
    url: str
    year: int
    season: str
    sport: str
    day: str
    division: str
    week1Start: str | None
    week2Start: str | None
    week3Start: str | None
    week4Start: str | None
    week5Start: str | None


class EstimateBlock(TypedDict):
    original: TierEstimate
    storeCredit: TierEstimate


class RefundRequestEval(TypedDict, total=False):
    ok: bool
    isValid: bool
    validationErrors: list[str] | None
    order: OrderInfo
    product: ProductInfo
    estimate: EstimateBlock


class SheetRowRef(BaseModel):
    """Sheet-row pointer round-tripped through `/refunds/validate` for diagnostic logging."""

    model_config = ConfigDict(populate_by_name=True)

    spreadsheet_id: str = Field(..., alias="spreadsheetId")
    tab_id: str = Field(..., alias="tabId")
    row_number: int = Field(..., alias="rowNumber")


class CancelOutcome(TypedDict):
    jobId: str
    jobDone: bool


class RefundOutcome(TypedDict):
    refundId: str
    amount: float
    currency: str
    createdAt: str


class CreateRefundResponse(TypedDict, total=False):
    ok: bool
    cancel: CancelOutcome | None
    refund: RefundOutcome | None
    errors: list[dict]
