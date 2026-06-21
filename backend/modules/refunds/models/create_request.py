"""Incoming request body for ``POST /refunds/create``.

Pydantic v2 — used for validation of the EXTERNAL request body (D28:
Pydantic is reserved for incoming external objects). Outgoing responses
are plain TypedDicts (see ``create_response.py``).

Per Stage 5 § 5.b: snake_case Python field names with camelCase aliases
to bridge to the wire JSON. ``model_config = {"populate_by_name": True}``
lets both forms parse — the Slack handler sends camelCase JSON; tests
or Python callers may build the model with either form.

Convention notes (D33 — Python 3.14+ style):
  - No ``from __future__ import annotations`` import.
  - ``X | None`` over the deprecated ``typing.Optional`` form.
  - Lowercase generic forms (no deprecated ``typing.List`` / ``typing.Dict``).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CreateRefundRequest(BaseModel):
    """The full ``/refunds/create`` request body sent by the Slack handler.

    Field-requirement deltas vs. the prior ``RefundExecuteRequest`` shape:

    - ``restock_to`` REPLACES the previous ``restock`` boolean. The four
      lanes are ``"veteran" | "early" | "general" | "waitlist"`` (the
      ``"full"`` literal was dropped per design correction C1).
      Field is OMITTED entirely when no restock is intended (no
      ``"none"`` sentinel). Downstream inventory consumers infer
      "full restock" semantics from the field's absence.
    - ``cancel`` / ``refund`` / ``notify`` / ``is_test`` are OPTIONAL
      with ``False`` defaults.
    - ``amount`` is ``float | None`` — ``None`` when cancel-only.
    - NO ``idempotency_key`` (D18) — Shopify's own dedup is sufficient.
    - NO ``slack_channel`` / ``source`` / ``policy_confirmation`` (none
      consumed by the backend).
    """

    model_config = ConfigDict(populate_by_name=True)

    order_id: str = Field(..., alias="orderId")
    """Shopify order GID, round-tripped from ``/refunds/validate`` response."""

    product_id: str = Field(..., alias="productId")
    """Shopify product GID, round-tripped from ``/refunds/validate`` response."""

    refund_to: Literal["original_method", "store_credit"] = Field(
        ..., alias="refundTo"
    )
    """Refund destination — drives the branch in ``schema.refunds.mutations.create``
    (transactions= for original; refund_methods= for store credit)."""

    amount: float | None = None
    """REQUIRED on refund; ``None`` when cancel-only. The controller uses
    ``Decimal(str(amount))`` to avoid float→Decimal precision drift."""

    cancel: bool = False
    refund: bool = False

    restock_to: Literal["veteran", "early", "general", "waitlist"] | None = Field(
        None, alias="restockTo"
    )
    """Restock lane (four-value union). Omitted when no restock intended.
    Maps to ``orderCancel.restock=True/False`` per § 5.e."""

    notify: bool = False
    """Whether Shopify should email the customer about the refund/cancel."""

    approved_by: str = Field(..., alias="approvedBy")
    """Slack user id of the approver (audit trail; written into the
    cancel mutation's ``staff_note``)."""

    is_test: bool = Field(False, alias="isTest")
    """Slack handler omits this when not in test mode; defaults to False
    on the backend."""
