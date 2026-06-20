"""Handle ``action = "phase-transition"`` events.

Reads a RegularSeason record from DynamoDB, derives Shopify title/tags/image
from the YAML period config, applies side-effects to Shopify, then upserts
the season's status back to DynamoDB.

Event shape (all keys required; null allowed where semantically optional):
    {
        "action":        "phase-transition",  # optional — inferred when absent
        "seasonId":      "1234567",
        "targetPeriod":  "early",
        "sourcePeriod":  "veteran" | null,
        "inventoryToAdd": 120 | null
    }
"""

import json
from typing import Any

from box import Box

from ..config import PERIOD_CONFIG, load_images
from ..repo import get_season, upsert_season
from ..responses import err, ok
from ..shopify_ops import apply_shopify

_REQUIRED = {"seasonId", "targetPeriod"}


def handle(raw_event: dict[str, Any]) -> dict[str, Any]:
    missing = _REQUIRED - raw_event.keys()
    if missing:
        return err(400, "Missing required fields", missing=sorted(missing))

    event = Box(raw_event)

    try:
        season = get_season(event.seasonId)
    except Exception as exc:
        return err(404, f"Season not found: {event.seasonId}", reason=str(exc))

    if event.targetPeriod not in PERIOD_CONFIG.periods:
        known = sorted(PERIOD_CONFIG.periods.keys())
        return err(400, f"Unknown targetPeriod: {event.targetPeriod!r}", known=known)

    images = load_images()
    period = PERIOD_CONFIG.periods[event.targetPeriod]
    division = PERIOD_CONFIG.divisions.get(season.division, season.division)

    bracket = period.displayBracket.format(division=division)
    title = f"{season.baseTitle} {bracket}"
    tags = sorted(set(season.tags) | set(period.requiredTags))
    image = images[season.sport]

    target_variant_id = season.registrationPeriods[event.targetPeriod].shopifyVariantId
    source_variant_id = (
        season.registrationPeriods[event.sourcePeriod].shopifyVariantId
        if event.get("sourcePeriod")
        else None
    )

    apply_shopify(
        shopify_product_id=season.shopifyProductId,
        title=title,
        tags=tags,
        image=image,
        target_variant_id=target_variant_id,
        source_variant_id=source_variant_id,
        inventory_to_add=event.get("inventoryToAdd"),
    )

    upsert_season(event.seasonId, status=period.statusValue)

    return ok({
        "seasonId": event.seasonId,
        "newStatus": period.statusValue,
        "newTitle": title,
    })
