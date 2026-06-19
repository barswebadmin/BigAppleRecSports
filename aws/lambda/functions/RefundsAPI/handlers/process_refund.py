"""Refund-execution handler for ``action in {create_refund, cancel_order}``.

STUB. The real Shopify ``orderCancel`` / ``refundCreate`` mutations land here in
a later stage. For now it acknowledges the routed action without mutating
anything, so the approval flow has somewhere to land during cutover.
"""

from typing import Any


def handle_process_refund(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "not_implemented",
        "action": payload.get("action"),
        "order_number": payload.get("order_number"),
        "idempotency_key": payload.get("idempotency_key"),
    }
