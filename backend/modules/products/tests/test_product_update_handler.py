"""
Tests for product_update_handler evaluation behavior using a realistic sample payload.

Cases:
1) Product tagged as waitlist-only → action_needed False (early exit)
2) Product with inventory > 0 → action_needed False
3) Product sold out, valid payload → action_needed True; blocks include correct date and URL
"""

import json
from unittest.mock import Mock

from new_structure_target.services.webhooks.handlers.product_update_handler import (
    evaluate_product_update_webhook,
)


def _sample_payload_base() -> dict:
    """Minimal subset of the provided sample webhook body required for evaluation."""
    return {
        "admin_graphql_api_id": "gid://shopify/Product/7350462185566",
        "created_at": "2025-03-12T10:13:17-04:00",
        "handle": "joe-test-product",
        "id": 7350462185566,
        "product_type": "",
        "published_at": "2025-03-14T14:21:58-04:00",
        "title": "joe test product - dodgeball",
        "updated_at": "2025-09-24T03:18:03-04:00",
        "vendor": "Big Apple Recreational Sports",
        "status": "active",
        "published_scope": "web",
        # tags and variants will be set per-test
    }


def test_already_waitlisted_action_not_needed():
    gas_client = Mock()
    product = _sample_payload_base()
    product["tags"] = "waitlist-only, something-else"
    product["variants"] = [{"id": 1, "inventory_quantity": 0}]

    body = json.dumps(product).encode("utf-8")
    result = evaluate_product_update_webhook(body)

    assert result["action_needed"] is False
    assert result["reason"] == "already_waitlisted"


def test_inventory_available_action_not_needed():
    gas_client = Mock()
    product = _sample_payload_base()
    product["tags"] = "regular"
    product["published_at"] = "2025-01-01T00:00:00-04:00"  # far in past
    product["variants"] = [{"id": 1, "inventory_quantity": 3}]

    body = json.dumps(product).encode("utf-8")
    result = evaluate_product_update_webhook(body)

    assert result["action_needed"] is False
    assert result["reason"] == "product_not_sold_out"


def test_sold_out_action_needed():
    gas_client = Mock()
    product = _sample_payload_base()
    product["tags"] = "regular"
    product["published_at"] = "2025-01-01T00:00:00-04:00"  # far in past
    product["variants"] = [{"id": 1, "inventory_quantity": 0}]

    body = json.dumps(product).encode("utf-8")
    result = evaluate_product_update_webhook(body)

    assert result["action_needed"] is True
    assert result["reason"] == "product_sold_out"
    # Validate blocks contain a correctly built product URL ending with /products/{id}
    blocks = result.get("slack_blocks", [])
    flat_text = "\n".join(
        b.get("text", {}).get("text", "") for b in blocks if b.get("type") == "section"
    )
    assert "/products/7350462185566" in flat_text
    # Validate date formatted includes the date part from updated_at
    assert "09/24/25" in flat_text

