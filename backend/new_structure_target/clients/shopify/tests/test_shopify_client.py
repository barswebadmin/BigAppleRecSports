import json
import requests
import pytest

from backend.models.shopify.orders import OrderId, OrderNumber
from backend.new_structure_target.clients.shopify.core.shopify_client import ShopifyClient


def make_order_id(value: str) -> OrderId:
    return OrderId(digits_only=value, gid=f"gid://shopify/Order/{value}")


def make_order_number(value: str) -> OrderNumber:
    n = value if value.startswith("#") else f"#{value}"
    return OrderNumber(digits_only=n.replace("#", ""), with_hash=n)


def _fake_resp(status: int, body: dict):
    class R:
        def __init__(self, s: int, b: dict):
            self.status_code = s
            self._b = b
        def json(self):
            return self._b
    return R(status, body)


def _load_fixture(body: dict):
    return body


def test_mock_success_by_id(monkeypatch):
    body = _load_fixture({
        "data": {"orders": {"edges": [{"node": {"id": "gid://shopify/Order/1", "name": "#1", "email": "a@b.com", "totalPriceSet": {"shopMoney": {"amount": "10.0", "currencyCode": "USD"}}}}]}},
        "extensions": {"cost": {"actualQueryCost": 3, "requestedQueryCost": 3, "throttleStatus": {"currentlyAvailable": 1997, "maximumAvailable": 2000.0, "restoreRate": 100.0}}}
    })
    monkeypatch.setattr("backend.new_structure_target.clients.shopify.core.shopify_client.requests.post", lambda url, json, headers, timeout: _fake_resp(200, body))
    res = ShopifyClient().fetch_order_details(order_id=make_order_id("1"))
    assert res["status_code"] == 200 and res.get("order")


def test_mock_not_found_by_name(monkeypatch):
    body = _load_fixture({
        "data": {"orders": {"edges": []}},
        "extensions": {"cost": {"actualQueryCost": 2, "requestedQueryCost": 3, "throttleStatus": {"currentlyAvailable": 1997, "maximumAvailable": 2000.0, "restoreRate": 100.0}}}
    })
    monkeypatch.setattr("backend.new_structure_target.clients.shopify.core.shopify_client.requests.post", lambda url, json, headers, timeout: _fake_resp(200, body))
    res = ShopifyClient().fetch_order_details(order_number=make_order_number("99999"))
    assert res["status_code"] == 204 and res.get("order") is None


def test_mock_malformed_errors(monkeypatch):
    body = _load_fixture({"errors": ["Syntax error"]})
    monkeypatch.setattr("backend.new_structure_target.clients.shopify.core.shopify_client.requests.post", lambda url, json, headers, timeout: _fake_resp(200, body))
    res = ShopifyClient().fetch_order_details(order_id=make_order_id("1"))
    assert res["status_code"] == 400 and res.get("success") is False


def test_mock_bad_token(monkeypatch):
    body = _load_fixture({"errors": "[API] Invalid API key or access token (unrecognized login or wrong password)"})
    monkeypatch.setattr("backend.new_structure_target.clients.shopify.core.shopify_client.requests.post", lambda url, json, headers, timeout: _fake_resp(401, body))
    res = ShopifyClient().fetch_order_details(order_id=make_order_id("1"))
    assert res["status_code"] == 401 and res.get("success") is False


def test_mock_bad_url(monkeypatch):
    def raiser(*args, **kwargs):
        raise requests.ConnectionError("Failed to resolve example.invalid")
    monkeypatch.setattr("backend.new_structure_target.clients.shopify.core.shopify_client.requests.post", raiser)
    res = ShopifyClient().fetch_order_details(order_number=make_order_number("1"))
    assert res["status_code"] == 404 and res.get("success") is False

