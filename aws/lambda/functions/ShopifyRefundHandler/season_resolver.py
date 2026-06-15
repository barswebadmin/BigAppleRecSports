"""Resolve a product's ``SeasonDates`` (start + off weeks).

This is the single seam for *where* season timing comes from. Today it greps
the Shopify product ``descriptionHtml`` via
``SeasonDates.from_html``. When season dates move to a more reliable source
(product metafields, a DynamoDB league table keyed by product id, etc.), swap
the body of :func:`resolve_season_dates` — nothing else in the refund flow
needs to change.
"""

from __future__ import annotations

from typing import Protocol

from registrations.refund_calculator import SeasonDates


class _Product(Protocol):
    description_html: str | None


def resolve_season_dates(product: _Product | None) -> SeasonDates:
    """Return the season's start/off dates for ``product``.

    Returns an all-``None`` :class:`SeasonDates` when the product is missing or
    the source has no parseable season info; the refund calculator treats that
    as "can't estimate" rather than erroring the whole request.
    """
    if product is None:
        return SeasonDates()
    return SeasonDates.from_html(getattr(product, "description_html", None) or "")
