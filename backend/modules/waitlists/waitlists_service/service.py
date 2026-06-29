"""Waitlists domain functions.

Persistence is not yet wired — the existing `modules/waitlist/` is a seam that
raises `NotImplementedError`. Each function returns a clear placeholder dict
naming the stub state. The real storage layer lands when its consumer arrives
(likely a Shopify customer-tag write or a DynamoDB table in `lib/`)."""

from typing import Any

from services.waitlists.requests import WaitlistSignupRequest


async def signup(body: WaitlistSignupRequest) -> dict[str, Any]:
    """Accept a waitlist signup. Today: acknowledges receipt only —
    persistence lands when the storage layer exists in lib/."""
    return {
        "status": "pending",
        "message": "waitlist storage not yet wired",
        "product_id": body.product_id,
        "email": body.email,
    }


async def list_for_product(product_id: str) -> dict[str, Any]:
    """List waitlist entries for a product. Today: returns an empty list +
    stub note; real query lands with the storage layer."""
    return {
        "status": "pending",
        "message": "waitlist storage not yet wired",
        "product_id": product_id,
        "entries": [],
    }


async def remove(entry_id: str) -> dict[str, Any]:
    """Remove a waitlist entry. Today: acknowledges receipt only;
    real deletion lands with the storage layer."""
    return {
        "status": "pending",
        "message": "waitlist storage not yet wired",
        "entry_id": entry_id,
    }
