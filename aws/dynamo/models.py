"""Pydantic models for BARS DynamoDB tables.

Each model maps 1:1 to a DynamoDB table schema. Pass a model instance to
``writes.put_item`` or ``writes.batch_write`` — it is validated on construction
and serialized (``model_dump(exclude_none=True)``) before the DynamoDB write.

Dependency: ``pydantic>=2.0`` must be available in the Lambda runtime.
TODO: publish a ``lib-pydantic`` Lambda layer and add its ARN to each
      function's pyproject.toml layers list.

Annotated types
---------------
Validation is expressed as field-level ``Annotated`` types created by
``str_matching``, so constraints are declared in one place and reused across
both models without duplicating validator bodies.

Usage:
    from aws.dynamo.models import Refund, WaitlistEntry
    from aws.dynamo import writes

    item = Refund(
        id="rf-a1b2c3d4e5f6a7b8",
        email="Player@BARS.com",      # normalized → player@bars.com
        first_name="Jane",
        last_name="Smith",
        order_number="#12345",
        refund_to="original_method",
        status="pending",
        submitted_at="2026-06-01T12:00:00+00:00",
        created_at="2026-06-01T12:01:00+00:00",
    )
    writes.put_item(TABLE, item, "refunds")
"""

import re
from decimal import Decimal
from functools import partial
from typing import Annotated, Literal, TypeAlias

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict


# ── Shared validation primitives ──────────────────────────────────────────────

def check_format(v: str, pattern: str, msg: str) -> str:
    """Return ``v`` unchanged when it matches ``pattern``; raise ValueError otherwise."""
    if not re.match(pattern, v):
        raise ValueError(f"{msg}, got {v!r}")
    return v


# ── Annotated field types ─────────────────────────────────────────────────────
# ``partial`` pre-fills ``pattern`` and ``msg`` so each alias is a pure str
# annotation — no duplicate validator bodies.

LowercaseEmail: TypeAlias = Annotated[str, BeforeValidator(lambda v: v.strip().lower())]
RefundId: TypeAlias       = Annotated[str, AfterValidator(partial(check_format, pattern=r"^rf-[0-9a-f]{16}$", msg="id must be rf-{hex16}"))]
WaitlistId: TypeAlias     = Annotated[str, AfterValidator(partial(check_format, pattern=r"^wl-[0-9a-f]{16}$", msg="id must be wl-{hex16}"))]
OrderNumber: TypeAlias    = Annotated[str, AfterValidator(partial(check_format, pattern=r"^#\d+$",              msg="order_number must be #NNNNN"))]
LeagueKeySlug: TypeAlias  = Annotated[str, AfterValidator(partial(check_format, pattern=r"^[a-z0-9-]+$",       msg="league_key must be a lowercase hyphenated slug"))]


# ── Table models ──────────────────────────────────────────────────────────────

class Refund(BaseModel):
    """``refunds`` table item.

    customer-index GSI requires ``customer_id`` (PK) + ``created_at`` (SK).
    Items without ``customer_id`` are not visible in that GSI until backfilled
    via a Shopify lookup pass.
    """

    model_config = ConfigDict(extra="forbid")

    id: RefundId
    customer_id: str | None = None   # gid://shopify/Customer/N — needed for GSI
    order_id: str | None = None      # gid://shopify/Order/N
    email: LowercaseEmail
    first_name: str
    last_name: str
    order_number: OrderNumber
    refund_to: Literal["original_method", "store_credit"]
    amount: Decimal | None = None
    status: Literal["pending", "completed", "cancelled"]
    submitted_at: str   # ISO 8601 — when the Google Form was submitted
    created_at: str     # ISO 8601 — when this DynamoDB record was created
    note: str | None = None
    admin_notes: str | None = None
    transfer_request: str | None = None
    deleted_at: str | None = None


class WaitlistEntry(BaseModel):
    """``waitlists`` table item.

    league-index GSI requires ``league_key`` (PK) + ``created_at`` (SK).
    Items are returned oldest-first (``ScanIndexForward=True``) to preserve
    sign-up queue order.
    """

    model_config = ConfigDict(extra="forbid")

    id: WaitlistId
    email: LowercaseEmail
    first_name: str
    last_name: str
    sport: str
    day: str
    division: str
    league_key: LeagueKeySlug   # e.g. kickball-monday-open-division
    position: int               # 1-based queue position assigned at ingestion
    status: Literal["active", "joined", "removed", "denied"]
    created_at: str             # ISO 8601 — GSI sort key
    phone_number: str | None = None
    gender: str | None = None
    pronouns: str | None = None
    deleted_at: str | None = None
