import base64
import hashlib
import hmac
import os
import json

import pytest

from new_structure_target.clients.shopify.core.shopify_security import ShopifySecurity


def _compute_shopify_signature(secret: str, body_bytes: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


@pytest.fixture()
def sample_webhook_body_bytes() -> bytes:
    # Trimmed, safe example payload (structure similar to Shopify product update)
    payload = {
        "id": 7461773082718,
        "title": "Example Product",
        "tags": "waitlist-only",
        "variants": [
            {"id": 42053854199902, "inventory_quantity": 0},
            {"id": 42053854167134, "inventory_quantity": 0},
        ],
    }
    # Use compact encoding to simulate real webhook body bytes
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def test_verify_shopify_webhook_valid_signature(sample_webhook_body_bytes: bytes, monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "r4Nd0mS3cr3tK3y9AZ7bQ81PcmF"
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("SHOPIFY_DEV_SECRET_WEBHOOK", secret)
    signature = _compute_shopify_signature(secret, sample_webhook_body_bytes)

    verifier = ShopifySecurity(webhook_secret=None)
    assert verifier.verify_shopify_webhook(sample_webhook_body_bytes, signature) is True


def test_verify_shopify_webhook_invalid_signature(sample_webhook_body_bytes: bytes, monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "r4Nd0mS3cr3tK3y9AZ7bQ81PcmF"
    wrong_secret = "wrong_secret_value"
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("SHOPIFY_DEV_SECRET_WEBHOOK", secret)
    signature = _compute_shopify_signature(wrong_secret, sample_webhook_body_bytes)

    verifier = ShopifySecurity(webhook_secret=None)
    assert verifier.verify_shopify_webhook(sample_webhook_body_bytes, signature) is False


