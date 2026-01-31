import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin

import click_extra as click
import requests


import sys
from pathlib import Path

# Add shared utilities to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared_utilities"))
from paths import get_repo_root

def _repo_root() -> Path:
    return get_repo_root()


def _normalize_base_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        raw = "bars-backend.loca.lt"
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    return raw.rstrip("/")


def _get_shopify_webhook_secret() -> Optional[str]:
    for k in (
        "SHOPIFY.SECRET_WEBHOOK",
        "SHOPIFY_SECRET_WEBHOOK",
        "SHOPIFY_WEBHOOK_SECRET",
        "SHOPIFY.DEV.SECRET_WEBHOOK",
        "SHOPIFY_DEV_SECRET_WEBHOOK",
        "SHOPIFY_DEV_WEBHOOK_SECRET",
    ):
        v = os.getenv(k)
        if v:
            return v
    return None


def _compute_hmac_signature(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def _load_sample(sample_filename: str) -> tuple[dict[str, str], Any]:
    path = _repo_root() / sample_filename
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise click.ClickException(f"Sample file is not a JSON object: {path}")
    headers = data.get("headers") or {}
    body = data.get("body")
    if not isinstance(headers, dict):
        raise click.ClickException(f"Sample headers is not an object: {path}")
    if body is None:
        raise click.ClickException(f"Sample file missing 'body': {path}")
    return {str(k): str(v) for k, v in headers.items()}, body


def _build_shopify_headers(sample_headers: dict[str, str], *, topic: str, signature: str) -> dict[str, str]:
    out: dict[str, str] = {
        "content-type": "application/json",
        "x-shopify-topic": topic,
        "x-shopify-hmac-sha256": signature,
    }
    for k, v in sample_headers.items():
        lk = k.lower()
        if lk.startswith("x-shopify-") and lk not in ("x-shopify-topic", "x-shopify-hmac-sha256"):
            out[lk] = v
    return out


def _post_sample(
    *,
    base_url: str,
    path: str,
    sample_filename: str,
    topic: str,
    timeout_seconds: float,
) -> None:
    sample_headers, body_obj = _load_sample(sample_filename)
    body_bytes = json.dumps(body_obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    secret = _get_shopify_webhook_secret()
    signature = _compute_hmac_signature(body_bytes, secret) if secret else (sample_headers.get("x-shopify-hmac-sha256") or "")

    headers = _build_shopify_headers(sample_headers, topic=topic, signature=signature)
    url = urljoin(_normalize_base_url(base_url) + "/", path.lstrip("/"))

    resp = requests.post(url, data=body_bytes, headers=headers, timeout=timeout_seconds)
    click.echo(f"{resp.status_code} {resp.reason}")
    ct = resp.headers.get("content-type", "")
    if "application/json" in ct:
        try:
            click.echo(json.dumps(resp.json(), indent=2, ensure_ascii=False))
            return
        except Exception:
            pass
    text = (resp.text or "").strip()
    if text:
        click.echo(text)


@click.group(name='webhooks', aliases=['webhook'])
def shopify_webhooks() -> None:
    """Send sample Shopify webhooks to a target URL."""


@shopify_webhooks.command(name='orders-create', aliases=['orders-create'])
@click.option("--url", "base_url", default="bars-backend.loca.lt", show_default=True)
@click.option("--timeout", "timeout_seconds", default=10.0, show_default=True, type=float)
def orders_create(base_url: str, timeout_seconds: float) -> None:
    _post_sample(
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        path="/shopify/webhooks/orders-create",
        sample_filename="sample_shopify_webhook_orders_create.json",
        topic="orders/create",
    )


@shopify_webhooks.command(name='orders-cancel', aliases=['orders-cancel'])
@click.option("--url", "base_url", default="bars-backend.loca.lt", show_default=True)
@click.option("--timeout", "timeout_seconds", default=10.0, show_default=True, type=float)
def orders_cancel(base_url: str, timeout_seconds: float) -> None:
    _post_sample(
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        path="/shopify/webhooks/orders-cancel",
        sample_filename="sample_shopify_webhook_orders_cancel.json",
        topic="orders/cancelled",
    )


@shopify_webhooks.command(name='refunds-create', aliases=['refunds-create'])
@click.option("--url", "base_url", default="bars-backend.loca.lt", show_default=True)
@click.option("--timeout", "timeout_seconds", default=10.0, show_default=True, type=float)
def refunds_create(base_url: str, timeout_seconds: float) -> None:
    _post_sample(
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        path="/shopify/webhooks/refunds-create",
        sample_filename="sample_shopify_webhook_refunds_create.json",
        topic="refunds/create",
    )


@shopify_webhooks.command(name='orders-update', aliases=['orders-update'])
@click.option(
    "--scenario",
    type=click.Choice(["refund-create", "order-cancel"], case_sensitive=False),
    default="refund-create",
    show_default=True,
)
@click.option("--url", "base_url", default="bars-backend.loca.lt", show_default=True)
@click.option("--timeout", "timeout_seconds", default=10.0, show_default=True, type=float)
def orders_update(scenario: str, base_url: str, timeout_seconds: float) -> None:
    scenario = scenario.lower()
    sample = {
        "refund-create": "sample_shopify_webhook_orders_update_on_refund_create.json",
        "order-cancel": "sample_shopify_webhook_orders_update_on_order_cancel.json",
    }[scenario]
    _post_sample(
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        path="/shopify/webhooks/orders-update",
        sample_filename=sample,
        topic="orders/updated",
    )


@shopify_webhooks.command(name='products-update', aliases=['products-update'])
@click.option(
    "--scenario",
    type=click.Choice(["plain", "on-order"], case_sensitive=False),
    default="plain",
    show_default=True,
)
@click.option("--url", "base_url", default="bars-backend.loca.lt", show_default=True)
@click.option("--timeout", "timeout_seconds", default=10.0, show_default=True, type=float)
def products_update(scenario: str, base_url: str, timeout_seconds: float) -> None:
    scenario = scenario.lower()
    sample = {
        "plain": "sample_shopify_webhook_products_update.json",
        "on-order": "sample_shopify_webhook_products_update_on_order.json",
    }[scenario]
    _post_sample(
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        path="/shopify/webhooks/products-update",
        sample_filename=sample,
        topic="products/update",
    )


__all__ = ["shopify_webhooks"]

