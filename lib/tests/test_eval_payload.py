# ============================================================================
# FROZEN — DO NOT RUN OR UPDATE.
# These tests are intentionally disabled until the ShopifyRefundHandler Lambda
# restructure (REGISTRATIONS-REFACTOR-PLAN.md, Stages 1–2) settles. No tests are
# to be written or updated for this Lambda until then. The original source is
# preserved verbatim below inside a string literal so pytest collects nothing.
# Unfreeze by removing the `_FROZEN = r'''` wrapper and the trailing `'''`.
# ============================================================================

_FROZEN = r'''
"""I→O test that the eval payload echoes the order's transactions + currency.

A fake Shopify order (2 transactions) is fed through ``handle_initial_request``
with the Shopify client stubbed, asserting ``RefundResponse.to_json()`` carries
both transactions in canonical ``{id,kind,status,gateway,parent_id}`` shape and
the presentment ``currency_code``. ``conftest.py`` puts the function dir on
``sys.path``.
"""

from types import SimpleNamespace

import handlers.handle_initial_request as h
from models import RefundRequest


def _ns(**kw):
    return SimpleNamespace(**kw)


def _fake_order():
    money = _ns(amount="100.00", currency_code="USD")
    line_item = _ns(
        custom_attributes=[_ns(key="Best Contact Email Address", value="jane@example.com")],
        product=_ns(
            id="gid://shopify/Product/1",
            title="Kickball Monday Open",
            tags=["kickball", "monday", "open"],
            description_html="",
        ),
    )
    return _ns(
        name="#1234",
        id="gid://shopify/Order/9",
        email="jane@example.com",
        customer=_ns(email="jane@example.com", first_name="Jane", last_name="Doe"),
        total_price_set=_ns(shop_money=money),
        refunds=[],
        transactions=[
            _ns(
                id="gid://shopify/OrderTransaction/1",
                kind="SALE",
                status="SUCCESS",
                gateway="shopify_payments",
                parent_transaction=None,
            ),
            _ns(
                id="gid://shopify/OrderTransaction/2",
                kind="CAPTURE",
                status="SUCCESS",
                gateway="shopify_payments",
                parent_transaction=_ns(id="gid://shopify/OrderTransaction/1"),
            ),
        ],
        cancelled_at=None,
        line_items=_ns(nodes=[line_item]),
    )


def test_eval_payload_populates_transactions_and_currency(monkeypatch):
    monkeypatch.setattr(h, "_client", lambda: _ns(get_order_by_name=lambda name: _fake_order()))

    resp = h.handle_initial_request(
        RefundRequest.model_validate({
            "order_number": "1234",
            "email": "jane@example.com",
            "first_name": "Jane",
            "last_name": "Doe",
            "refund_to": "original_method",
        })
    )
    data = resp.to_json()

    assert data["currency_code"] == "USD"
    assert data["refund_to"] == "original_method"
    assert data["is_test"] is True
    assert len(data["transactions"]) == 2
    assert data["transactions"][0] == {
        "id": "gid://shopify/OrderTransaction/1",
        "kind": "SALE",
        "status": "SUCCESS",
        "gateway": "shopify_payments",
        "parent_id": None,
    }
    assert data["transactions"][1]["parent_id"] == "gid://shopify/OrderTransaction/1"


def test_validation_passes_when_email_matches_line_item_attribute(monkeypatch):
    monkeypatch.setattr(h, "_client", lambda: _ns(get_order_by_name=lambda name: _fake_order()))

    resp = h.handle_initial_request(
        RefundRequest.model_validate({
            "order_number": "1234",
            "email": "jane@example.com",
            "first_name": "Jane",
            "last_name": "Doe",
        })
    )
    assert resp.email_matched_against == "Best Contact Email Address"
'''
