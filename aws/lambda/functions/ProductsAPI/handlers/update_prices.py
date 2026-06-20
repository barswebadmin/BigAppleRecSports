"""Handle ``action = "update-prices"`` events.

Validates that the product's encoded season dates still match the scheduler's
payload (guards against schedule/product drift), then bulk-updates the open
and waitlist variant prices via the Shopify gql/DSL client.

Status codes mirror the legacy lambda for downstream-caller compatibility:
400 (bad request) · 406 (date mismatch) · 502 (Shopify failure) · 500 (crash).

Event shape (camelCase keys; may be wrapped in API-Gateway ``{body: "..."}``):
    {
        "action":                   "update-prices",  # optional — inferred
        "productGid":               "gid://shopify/Product/...",
        "openVariantGid":           "gid://shopify/ProductVariant/...",
        "waitlistVariantGid":       "gid://shopify/ProductVariant/...",
        "updatedPrice":             25.00,
        "seasonStartDate":          "9/8/25",
        "offDatesCommaSeparated":   "11/3/25,11/10/25"  # optional
    }
"""

import logging
import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from shop_client import ShopifyClient, schema

from ..responses import err, ok
from ..season_dates import extract_season_dates, format_date_only, split_off_dates

logger = logging.getLogger(__name__)

# Module-level client: reads env once per cold start. Fails fast at import time
# if SHOPIFY__* vars are absent — intentional for Lambda.
_client = ShopifyClient(
    store_id=os.environ["SHOPIFY__STORE_ID"],
    api_version=os.environ["SHOPIFY__API_VERSION"],
    token=os.environ["SHOPIFY__TOKEN__ADMIN"],
)

_PRODUCT_FIELDS = ["id", "title", "description_html"]
_VARIANT_FIELDS = ["id", "title", "price"]


class _Event(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    schedule_name: str | None = Field(default=None, alias="scheduleName")
    product_gid: str = Field(alias="productGid")
    open_variant_gid: str = Field(alias="openVariantGid")
    waitlist_variant_gid: str = Field(alias="waitlistVariantGid")
    updated_price: float | str = Field(alias="updatedPrice")
    season_start_date: str = Field(alias="seasonStartDate")
    off_dates_comma_separated: str | None = Field(
        default=None, alias="offDatesCommaSeparated"
    )


def _format_price(updated_price: float | str) -> str:
    return f"{float(updated_price):.2f}"


class _ShopifyMutationError(RuntimeError):
    def __init__(self, user_errors: list[dict[str, Any]]):
        super().__init__(f"productVariantsBulkUpdate failed: {user_errors}")
        self.user_errors = user_errors


def handle(raw_event: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = _Event.model_validate(raw_event)
    except ValidationError as exc:
        return err(400, "Missing or invalid fields", detail=exc.errors())

    # Guard: confirm scheduler's season dates still match the live product
    try:
        product = _client.run(
            schema.products.queries.by_id,
            id=payload.product_gid,
            returns=_PRODUCT_FIELDS,
        )
    except Exception as exc:
        logger.exception("product fetch failed")
        return err(500, "Season-date validation failed", reason=str(exc))

    if not product:
        return err(404, f"Product not found: {payload.product_gid}")

    expected_start, expected_off_str = extract_season_dates(
        product.description_html or ""
    )
    received_start = format_date_only(payload.season_start_date)
    received_off = [
        format_date_only(d) for d in split_off_dates(payload.off_dates_comma_separated)
    ]
    expected_off = split_off_dates(expected_off_str)

    dates_match = (
        expected_start == received_start
        and sorted(received_off) == sorted(expected_off)
    )
    validation_detail = {
        "match": dates_match,
        "productTitle": product.title or "",
        "expected": {"seasonStartDate": expected_start, "offDates": expected_off},
        "received": {
            "seasonStartDate": received_start,
            "offDates": [d for d in received_off if d is not None],
        },
    }

    if not dates_match:
        return err(406, "Season dates mismatch", details=validation_detail)

    # Apply price update
    price = _format_price(payload.updated_price)
    variants = [
        {"id": payload.open_variant_gid, "price": price},
        {"id": payload.waitlist_variant_gid, "price": price},
    ]

    try:
        result = _client.run(
            schema.products.mutations.bulk_update_variants,
            product_id=payload.product_gid,
            variants=variants,
            returns=[f"product_variants.{f}" for f in _VARIANT_FIELDS],
        )
    except Exception as exc:
        logger.exception("price update failed")
        return err(502, "Price update failed", reason=str(exc))

    if result.user_errors:
        logger.error("shopify userErrors: %s", result.user_errors)
        return err(502, "Price update rejected by Shopify", userErrors=list(result.user_errors))

    updated = list(result.product_variants or [])
    logger.info("updated %d variants for %s @ %s", len(updated), payload.product_gid, price)

    return ok({
        "message": "Price update successful",
        "updatedVariants": updated,
        "validatedAgainst": validation_detail,
    })
