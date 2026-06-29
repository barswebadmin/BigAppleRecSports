import json
import types
import pytest

from .shopify_client import ShopifyClient




def _fake_resp(status_code: int, body: dict) -> types.SimpleNamespace:
    return types.SimpleNamespace(status_code=status_code, json=lambda: body, text=json.dumps(body))


def test_send_request_success(monkeypatch):
    body = {"data": {"orders": {"edges": [{"node": {"id": "gid://shopify/Order/1"}}]}}}
    monkeypatch.setattr("shopify_client.requests.post", lambda url, json, headers, timeout: _fake_resp(200, body))
    cli = ShopifyClient()
    out = cli.send_request({"query": "{}", "variables": {}})
    assert out.success and out.status_code == 200


def test_send_request_client_error(monkeypatch):
    body = {"errors": [{"message": "bad"}]}
    monkeypatch.setattr("shopify_client.requests.post", lambda url, json, headers, timeout: _fake_resp(400, body))
    cli = ShopifyClient()
    out = cli.send_request({"query": "{}", "variables": {}})
    assert not out.success and out.status_code == 400


def test_send_request_unauthorized(monkeypatch):
    body = {"errors": [{"message": "unauth"}]}
    monkeypatch.setattr("shopify_client.requests.post", lambda url, json, headers, timeout: _fake_resp(401, body))
    cli = ShopifyClient()
    out = cli.send_request({"query": "{}", "variables": {}})
    assert not out.success and out.status_code == 401


def test_send_request_transport_error(monkeypatch):
    def raiser(*args, **kwargs):
        raise RuntimeError("boom")
    monkeypatch.setattr("shopify_client.requests.post", raiser)
    cli = ShopifyClient()
    with pytest.raises(RuntimeError):
        cli.send_request({"query": "{}", "variables": {}})

