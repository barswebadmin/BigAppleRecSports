from datetime import datetime, timezone
from typing import Annotated, Literal, Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

_BARS_TZ = ZoneInfo("America/New_York")


class EstimateRefundRequest(BaseModel):
    """Identifies an order and the moment the refund was submitted; both ladders
    (refund-to-original + store credit) are returned regardless of the user's
    eventual choice."""

    number: Optional[str] = Field(None, min_length=5, max_length=5)
    id: Optional[str] = Field(None, min_length=10, max_length=128)
    submitted_at: Optional[datetime] = None
    total_weeks: Optional[int] = Field(None, ge=1)

    @model_validator(mode="after")
    def exactly_one_identifier(self) -> "EstimateRefundRequest":
        if not self.number and not self.id:
            raise ValueError("Must provide 'number' or 'id'")
        if self.number and self.id:
            raise ValueError("Provide only one of 'number' or 'id'")
        return self


class RefundSubmitRequest(BaseModel):
    """Customer refund request for `POST /refunds/submit` — estimate, build eval
    payload, POST to Slack webhook (`evaluation_json`)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    number: Optional[str] = Field(None, min_length=5, max_length=5)
    id: Optional[str] = Field(None, min_length=10, max_length=128)
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    refund_to: Literal["original_method", "store_credit"] = "store_credit"
    notes: Optional[str] = None
    phone: Optional[str] = None
    submitted_at: Optional[datetime] = None
    total_weeks: Optional[int] = Field(None, ge=1)
    is_test: bool = True
    slack_trigger_url: Optional[str] = Field(
        default=None,
        description="Override env SLACK__REFUND_EVAL_TRIGGER_URL for this request only.",
    )

    @model_validator(mode="after")
    def exactly_one_identifier(self) -> "RefundSubmitRequest":
        if not self.number and not self.id:
            raise ValueError("Must provide 'number' or 'id'")
        if self.number and self.id:
            raise ValueError("Provide only one of 'number' or 'id'")
        return self

    @field_validator("submitted_at", mode="after")
    @classmethod
    def resolve_submitted_at(cls, v: datetime | None) -> datetime:
        if v is None:
            return datetime.now(timezone.utc)
        if v.tzinfo is None:
            return v.replace(tzinfo=_BARS_TZ)
        return v

    def to_estimate_refund_request(self) -> EstimateRefundRequest:
        return EstimateRefundRequest(
            number=self.number,
            id=self.id,
            submitted_at=self.submitted_at,
            total_weeks=self.total_weeks,
        )

    @property
    def order_number_display(self) -> str:
        if self.number:
            return self.number if self.number.startswith("#") else f"#{self.number}"
        return ""


class RefundExecuteRequest(BaseModel):
    """Slack-approved execution for `POST /refunds/create` — optional order cancel
    then Shopify `refundCreate` when amount > 0."""

    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True)

    cancel_order: bool = Field(False, alias="cancelOrder")
    order_id: str = Field(..., alias="orderId", min_length=10, max_length=128)
    order_number: Optional[str] = Field(None, alias="orderNumber")
    refund_to: Literal["original_method", "store_credit"] = Field(..., alias="refundTo")
    amount: Annotated[float, Field(ge=0)]
    transactions: list[dict] = Field(default_factory=list)
    currency: Optional[str] = None
    approved_by: str = Field(..., alias="approvedBy", min_length=1, max_length=64)
    is_test: bool = Field(False, alias="isTest")
    note: Optional[str] = None
    notify: bool = False
    idempotency_key: Optional[str] = Field(None, alias="idempotencyKey")


class CreateRefundRequest(BaseModel):
    """Low-level inputs passed straight to `schema.refunds.mutations.create`."""

    order_id: str
    currency: Optional[str] = None
    note: Optional[str] = None
    notify: bool = False
    transactions: list[dict] = Field(default_factory=list)
    refund_line_items: list[dict] = Field(default_factory=list)
    refund_methods: list[dict] = Field(default_factory=list)
    shipping: Optional[dict] = None


class RefundRequestSubmission(BaseModel):
    """Customer-submitted refund-request form for `POST /refunds/request`."""

    email: EmailStr
    order_number: str = Field(min_length=5, max_length=5)
    request_submitted_at: datetime


class RefundEstimateTier(BaseModel):
    """One ladder's tier estimate. Exposed as a sub-model of `RefundEstimate`."""

    amount: float
    percentage: int
    penalty: int
    message: str


class RefundEstimate(BaseModel):
    """Both ladders side-by-side plus order facts (used by internal estimate helpers)."""

    order_id: str
    order_name: str
    order_total: float
    currency: Optional[str] = None
    refund_to_original: Optional[RefundEstimateTier] = None
    store_credit: Optional[RefundEstimateTier] = None
    note: Optional[str] = None


Ladder = Literal["refund_to_original", "store_credit"]
