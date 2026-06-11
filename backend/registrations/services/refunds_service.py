from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal

from clients.shopify.models.base import ClientError
from clients.shopify.models.shopify_refund import RefundInput
from clients.shopify.shopify_client import shopify_client
from models.refunds import RefundCreateInput, RefundEstimateBreakdown
from utils.refund_calculator import (
    EstimateTierKind,
    RefundResult,
    SeasonDates,
    estimate_refund_due,
)

logger = logging.getLogger(__name__)


def _tier_kind_for_refund_type(refund_type: str) -> EstimateTierKind:
    """Map API ``refund_type`` to the percentage ladder used in :func:`estimate_refund_due`.

    Supported values today (see ``RefundMethod`` / Shopify refund flow):

    - ``store_credit`` → credit ladder (100 / 95 / … / 55).
    - Any other string (e.g. ``original_payment``) → refund-to-original ladder
      (95 / 90 / … / 50). Unknown values are **not** rejected; they use the refund ladder.
    """
    if refund_type == "store_credit":
        return EstimateTierKind.STORE_CREDIT
    return EstimateTierKind.REFUND_TO_ORIGINAL


class RefundsService:
    def __init__(self) -> None:
        self.client = shopify_client

    async def refund_shopify_order(
        self,
        body: RefundCreateInput,
    ) -> tuple[dict | None, list[ClientError]]:
        refund_input = RefundInput.model_validate(body.model_dump(mode="python"))
        refund, client_errors, user_errors = await self.client.create_refund(refund_input)
        errors = list(client_errors)
        for u in user_errors:
            if u.message:
                errors.append(ClientError(message=u.message))
        if not errors:
            logger.info(
                "[RefundsService] refund created for order %s",
                refund_input.order_gid,
            )
        payload = refund.model_dump(mode="json", by_alias=True) if refund is not None else None
        return payload, errors

    def calculate_estimated_refund_due(
        self,
        *,
        order_total: float,
        refund_type: str,
        product_description_html: str | None = None,
        submitted_at: datetime | None = None,
        total_weeks: int | None = None,
    ) -> tuple[float | None, str | None]:
        """Estimate refund or store-credit amount from product HTML season block.

        Returns ``(None, None)`` when ``product_description_html`` is missing or blank
        (no season source). Returns ``(None, str)`` when HTML is present but season dates
        cannot be parsed, when inputs fail validation (e.g. non-positive ``order_total``),
        or when the util reports failure. On success, returns ``(amount, message)`` including
        ``0.0`` for the post–week-5 tier.
        """
        if product_description_html is None or not product_description_html.strip():
            return None, None

        season = SeasonDates.from_html(product_description_html)
        if not season.start_date:
            return None, "Season dates could not be parsed from product description."

        if total_weeks is not None:
            season = season.model_copy(update={"total_weeks": total_weeks})

        tier_kind = _tier_kind_for_refund_type(refund_type)
        result: RefundResult = estimate_refund_due(
            season,
            order_total,
            tier_kind,
            submitted_at=submitted_at,
        )

        if not result.success:
            return None, result.message

        return result.amount, result.message

    def refund_estimate_breakdown(
        self,
        *,
        order_total: float,
        ladder: Literal["store_credit", "original_payment"],
        product_description_html: str | None,
        submitted_at: datetime | None,
        total_weeks: int | None = None,
    ) -> RefundEstimateBreakdown | None:
        """Tier estimate for one ladder; ``None`` when season HTML is missing or unusable."""
        if product_description_html is None or not product_description_html.strip():
            return None

        season = SeasonDates.from_html(product_description_html)
        if not season.start_date:
            return None

        if total_weeks is not None:
            season = season.model_copy(update={"total_weeks": total_weeks})

        tier_kind = _tier_kind_for_refund_type(
            "store_credit" if ladder == "store_credit" else "original_payment",
        )
        result: RefundResult = estimate_refund_due(
            season,
            order_total,
            tier_kind,
            submitted_at=submitted_at,
        )

        if not result.success:
            return None

        return RefundEstimateBreakdown(
            amount=result.amount,
            percentage=result.percentage,
            penalty=result.penalty,
            message=result.message,
        )
