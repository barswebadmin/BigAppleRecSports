"""
Tests for the Shopify webhook endpoints.
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def _headers(topic: str) -> dict[str, str]:
    return {
        "x-shopify-topic": topic,
        "x-shopify-hmac-sha256": "test-signature",
        "content-type": "application/json",
    }


def test_product_update_valid_signature(client):
    with patch("modules.integrations.shopify.client.shopify_security.ShopifySecurity.verify_shopify_webhook", return_value=True):
        resp = client.post(
            "/shopify/webhooks/products-update",
            headers=_headers("products/update"),
            json={"id": 123},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True


def test_order_create_valid_signature(client):
    with patch("modules.integrations.shopify.client.shopify_security.ShopifySecurity.verify_shopify_webhook", return_value=True):
        resp = client.post(
            "/shopify/webhooks/orders-create",
            headers=_headers("orders/create"),
            json={"order_number": 999},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True


def test_refund_create_valid_signature(client):
    with patch("modules.integrations.shopify.client.shopify_security.ShopifySecurity.verify_shopify_webhook", return_value=True):
        resp = client.post(
            "/shopify/webhooks/refunds-create",
            headers=_headers("refunds/create"),
            json={"id": 555},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True


def test_invalid_signature_returns_401(client):
    with patch("modules.integrations.shopify.client.shopify_security.ShopifySecurity.verify_shopify_webhook", return_value=False):
        resp = client.post(
            "/shopify/webhooks/products-update",
            headers=_headers("products/update"),
            json={"id": 123},
        )
    assert resp.status_code == 401
    assert "Invalid webhook signature" in resp.json()["detail"]


def test_missing_topic_returns_400(client):
    with patch("modules.integrations.shopify.client.shopify_security.ShopifySecurity.verify_shopify_webhook", return_value=True):
        resp = client.post(
            "/shopify/webhooks/products-update",
            headers={"x-shopify-hmac-sha256": "test-signature", "content-type": "application/json"},
            json={"id": 123},
        )
    assert resp.status_code == 400
    assert "Missing x-shopify-topic" in resp.json()["detail"]


def test_topic_mismatch_returns_409(client):
    with patch("modules.integrations.shopify.client.shopify_security.ShopifySecurity.verify_shopify_webhook", return_value=True):
        resp = client.post(
            "/shopify/webhooks/products-update",
            headers=_headers("orders/create"),
            json={"id": 123},
        )
    assert resp.status_code == 409
    assert "Unexpected x-shopify-topic" in resp.json()["detail"]


def test_orders_update_valid_signature(client):
    with patch("modules.integrations.shopify.client.shopify_security.ShopifySecurity.verify_shopify_webhook", return_value=True):
        resp = client.post(
            "/shopify/webhooks/orders-update",
            headers=_headers("orders/updated"),
            json={"id": 1},
        )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_orders_cancel_valid_signature(client):
    with patch("modules.integrations.shopify.client.shopify_security.ShopifySecurity.verify_shopify_webhook", return_value=True):
        resp = client.post(
            "/shopify/webhooks/orders-cancel",
            headers=_headers("orders/cancelled"),
            json={"id": 1},
        )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
