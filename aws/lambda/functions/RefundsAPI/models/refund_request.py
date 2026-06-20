"""Inbound refund request model and request↔order validation."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from models._text import match_field
from models.shopify_order import ShopifyOrder

# Naive form-submission timestamps are assumed to be in BARS's operational tz.
# A naive ISO string from GAS (e.g. "2026-03-11T00:30:00") is almost certainly
# NY-local; interpreting it as UTC would shift submissions 4-5h and could
# mis-tier requests submitted near a refund-window boundary day.
_BARS_TZ = ZoneInfo("America/New_York")

logger = logging.getLogger(__name__)

ORIGINAL_METHOD = "original_method"
STORE_CREDIT = "store_credit"
_REFUND_TYPES = frozenset({ORIGINAL_METHOD, STORE_CREDIT})


@dataclass
class FieldMatch:
    matched: bool
    request_value: str
    candidates: list[str] = field(default_factory=list)
    matched_against: str | None = None


@dataclass
class OrderMatchResult:
    """Result of matching refund request fields against order data."""
    email: FieldMatch
    first_name: FieldMatch
    last_name: FieldMatch

    @property
    def all_passed(self) -> bool:
        return self.email.matched and self.first_name.matched and self.last_name.matched

    @property
    def warnings(self) -> list[str]:
        out: list[str] = []
        if not self.email.matched:
            out.append(
                f"Email mismatch: request '{self.email.request_value}' did not match "
                f"any of {self.email.candidates or ['(no candidates found on order)']}"
            )
        if not self.first_name.matched:
            out.append(
                f"First name mismatch: request '{self.first_name.request_value}' did not match "
                f"any of {self.first_name.candidates or ['(no candidates found on order)']}"
            )
        if not self.last_name.matched:
            out.append(
                f"Last name mismatch: request '{self.last_name.request_value}' did not match "
                f"any of {self.last_name.candidates or ['(no candidates found on order)']}"
            )
        return out


def _to_field_match(request_value: str, candidates: list[tuple[str, str]]) -> FieldMatch:
    matched, values, matched_against = match_field(request_value, candidates)
    return FieldMatch(
        matched=matched,
        request_value=request_value,
        candidates=values,
        matched_against=matched_against,
    )


class RefundRequest(BaseModel):
    """JSON payload POSTed by the refund-form ingress for ``action=evaluate_refund``."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="ignore",
    )

    order_number: str = Field(default="")
    email: str = Field(default="")
    first_name: str = Field(default="")
    last_name: str = Field(default="")
    refund_to: str = Field(
        default=STORE_CREDIT,
        description='"original_method" or "store_credit".',
    )
    submitted_at: datetime | None = Field(
        default=None,
        validate_default=True,
        description="Form submission timestamp (ISO 8601). Naïve → America/New_York; missing → now UTC.",
    )
    is_test: bool = Field(
        default=True,
        description="Routes the review to the test channel. Default test-safe.",
    )
    notes: str | None = None
    slack_trigger_url: str | None = Field(
        default=None,
        description="Override Slack eval webhook; defaults to SLACK__REFUND_EVAL_TRIGGER_URL.",
    )

    @model_validator(mode="before")
    @classmethod
    def _warn_unexpected_keys(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        unexpected = sorted(set(data) - set(cls.model_fields))
        if unexpected:
            logger.warning(
                "RefundRequest received unexpected key(s): %s",
                ", ".join(unexpected),
            )
        return data

    @field_validator("order_number", mode="after")
    @classmethod
    def _normalize_order_number(cls, v: str) -> str:
        if not v:
            return ""
        return v if v.startswith("#") else f"#{v}"

    @field_validator("refund_to", mode="after")
    @classmethod
    def _validate_refund_to(cls, v: str) -> str:
        if v not in _REFUND_TYPES:
            raise ValueError(f"refund_to must be one of {sorted(_REFUND_TYPES)}, got {v!r}")
        return v

    @field_validator("submitted_at", mode="after")
    @classmethod
    def _resolve_submitted_at(cls, v: datetime | None) -> datetime:
        if v is None:
            return datetime.now(timezone.utc)
        if v.tzinfo is None:
            return v.replace(tzinfo=_BARS_TZ)
        return v

    def validate_against_order(self, order: ShopifyOrder) -> OrderMatchResult:
        return OrderMatchResult(
            email=_to_field_match(str(self.email), order.candidate_emails()),
            first_name=_to_field_match(self.first_name, order.candidate_first_names()),
            last_name=_to_field_match(self.last_name, order.candidate_last_names()),
        )
