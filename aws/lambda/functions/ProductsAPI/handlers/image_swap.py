"""Handle ``action = "sold-out-image-check"`` events.

Triggered by a Shopify ``products/update`` webhook. When all registration-
relevant variants are sold out, swaps the product image to the sport-specific
sold-out image (GID fetched from SSM).

Relevant variants: those whose title contains vet/bipoc/trans/wtnb/early/open
but NOT wait/team. If no relevant variants exist, no action is taken.

Event shape: Shopify products/update webhook payload (REST format):
    {
        "id":                   7350462185566,
        "admin_graphql_api_id": "gid://shopify/Product/7350462185566",
        "title":                "2026 Summer Kickball Monday Open Division",
        "tags":                 "kickball, summer-2026",
        "variants": [
            {"title": "Open Registration", "inventory_quantity": 0, "inventory_policy": "deny"},
            {"title": "Waitlist", "inventory_quantity": 5, "inventory_policy": "deny"},
            ...
        ]
    }
"""

import logging
from typing import Any

from ..config import load_sold_out_images
from ..responses import err, ok
from ..shopify_ops import apply_shopify

logger = logging.getLogger(__name__)

_SPORT_KEYWORDS: list[str] = ["bowling", "dodgeball", "kickball", "pickleball"]

# Variant title substrings that indicate a registration slot (not waitlist/team).
_RELEVANT_TERMS = {"vet", "bipoc", "trans", "wtnb", "early", "open"}
_EXCLUDED_TERMS = {"wait", "team"}


def _detect_sport(title: str, tags: str) -> str | None:
    combined = (title + " " + tags).lower()
    for sport in _SPORT_KEYWORDS:
        if sport in combined:
            return sport
    return None


def _is_relevant(variant_title: str) -> bool:
    t = variant_title.lower()
    has_required = any(term in t for term in _RELEVANT_TERMS)
    has_excluded = any(term in t for term in _EXCLUDED_TERMS)
    return has_required and not has_excluded


def _all_relevant_closed(variants: list[dict[str, Any]]) -> bool:
    relevant = [v for v in variants if _is_relevant(v.get("title", ""))]
    if not relevant:
        logger.info("no relevant variants found — skipping")
        return False
    return all(
        v.get("inventory_quantity", 1) == 0 and v.get("inventory_policy", "deny") != "continue"
        for v in relevant
    )


def handle(raw_event: dict[str, Any]) -> dict[str, Any]:
    product_gid: str | None = raw_event.get("admin_graphql_api_id")
    product_title: str = raw_event.get("title", "")
    product_tags: str = raw_event.get("tags", "")
    variants: list[dict[str, Any]] = raw_event.get("variants", [])

    if not product_gid or not variants:
        missing = [f for f in ("admin_graphql_api_id", "variants") if not raw_event.get(f)]
        return err(400, "Missing required webhook fields", missing=missing)

    if not _all_relevant_closed(variants):
        return ok({
            "message": "Product still has open inventory — no action taken",
            "productGid": product_gid,
        })

    sport = _detect_sport(product_title, product_tags)
    if not sport:
        logger.info("sold-out product %s: sport not detected from title/tags", product_gid)
        return ok({
            "message": "Unrecognized sport — no sold-out image applied",
            "productTitle": product_title,
            "supportedSports": _SPORT_KEYWORDS,
        })

    try:
        sold_out_images = load_sold_out_images()
    except Exception as exc:
        logger.exception("failed to load sold-out images from SSM")
        return err(500, "Could not load sold-out image config", reason=str(exc))

    image_gid = sold_out_images.get(sport)
    if not image_gid:
        logger.warning("no sold-out image configured for sport %r", sport)
        return err(500, f"No sold-out image configured for sport: {sport}")

    try:
        apply_shopify(
            shopify_product_id=product_gid,
            title=None,
            tags=None,
            image=image_gid,
            target_variant_id=None,
            source_variant_id=None,
            inventory_to_add=None,
        )
    except Exception as exc:
        logger.exception("image swap failed for %s", product_gid)
        return err(502, "Sold-out image swap failed", reason=str(exc))

    return ok({
        "message": f"Sold-out image applied for {sport}",
        "productGid": product_gid,
        "sport": sport,
        "imageGid": str(image_gid),
    })
