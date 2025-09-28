import re
from typing import List, Set

import pytest

from backend.models.shopify.requests import FetchOrderRequest
from backend.new_structure_target.clients.shopify.builders.shopify_request_builders import (
    render_selection,
    build_return_fields,
    _paths_to_fields,
    _build_search_variable,
    _derive_allowlist_and_leaves,
    _gather_requested_python_paths,
    _convert_and_validate_paths,
    _expand_to_scalar_leaves,
    build_order_fetch_request_payload,
    FieldSpec,
)


def test__build_search_variable_variants():
    assert _build_search_variable(FetchOrderRequest(order_id="12345")) == {"q": "id:12345"}
    assert _build_search_variable(FetchOrderRequest(order_number="43298")) == {"q": "name:#43298"}
    assert _build_search_variable(FetchOrderRequest(email="user@example.com")) == {"q": "email:user@example.com"}
    with pytest.raises(ValueError):
        _build_search_variable(FetchOrderRequest())


def test__derive_allowlist_and_leaves_contains_expected_paths():
    allowed, scalar_leaves = _derive_allowlist_and_leaves()
    # Allowed should include object and nested paths
    assert "id" in allowed
    assert "name" in allowed
    assert "customer" in allowed
    assert "customer.id" in allowed
    # Scalar leaves should include common scalars
    assert "id" in scalar_leaves
    assert "name" in scalar_leaves
    assert "customer.id" in scalar_leaves


def test__gather_requested_python_paths_merges_lists():
    out = _gather_requested_python_paths(["id", "customer"], ["total_price_set.shop_money.amount"])
    assert out == ["id", "customer", "total_price_set.shop_money.amount"]


def test__convert_and_validate_paths_converts_and_validates():
    allowed, _ = _derive_allowlist_and_leaves()
    # Python names should convert to GraphQL aliases
    requested_py = ["total_price_set.shop_money.amount", "customer"]
    out = _convert_and_validate_paths(requested_py, allowed)
    assert "totalPriceSet.shopMoney.amount" in out
    assert "customer" in out
    # Invalid path should raise
    with pytest.raises(ValueError):
        _convert_and_validate_paths(["does.not.exist"], allowed)


def test__expand_to_scalar_leaves_object_and_scalar_cases():
    _, scalar_leaves = _derive_allowlist_and_leaves()
    # Expands object path to all scalar leaves below it
    expanded = _expand_to_scalar_leaves(["customer"], scalar_leaves)
    assert "customer.id" in expanded and "customer.email" in expanded
    # Scalar leaf remains itself
    expanded2 = _expand_to_scalar_leaves(["id"], scalar_leaves)
    assert expanded2 == ["id"]
    # Empty requested list returns all scalar leaves by default
    expanded3 = _expand_to_scalar_leaves([], scalar_leaves)
    assert set(expanded3) == set(scalar_leaves)


def test__paths_to_fields_and_render_selection_roundtrip():
    paths = [
        "id",
        "customer.id",
        "totalPriceSet.shopMoney.amount",
    ]
    node_spec = _paths_to_fields(paths)
    # Render within edges/node wrapper like the real query
    selection: FieldSpec = {"edges": {"node": node_spec}}
    rendered = render_selection(selection)
    # Expect scalars to render without braces and objects with braces
    assert "edges {" in rendered and "node {" in rendered
    assert "id" in rendered
    assert re.search(r"customer\s*{\s*id\s*}", rendered)
    assert re.search(r"totalPriceSet\s*{\s*shopMoney\s*{\s*amount\s*}\s*}", rendered)


def test_build_return_fields_wraps_base_and_selection():
    base = "FetchOrder($q: String!) { orders(first: 1, query: $q)"
    selection: FieldSpec = {"edges": {"node": {"id": [], "customer": {"id": []}}}}
    query = build_return_fields("query", base, selection)
    assert query.startswith("query ")
    assert "orders(first: 1, query: $q)" in query
    # Do not assume strict ordering beyond structural presence
    assert re.search(r"node\s*{[^}]*\bid\b[^}]*customer\s*{\s*id\s*}[^}]*}\s*}\s*}\s*", query)


def test_build_order_fetch_request_payload_defaults_to_curated_selection():
    req = FetchOrderRequest(order_number="43298")
    payload = build_order_fetch_request_payload(req)
    assert payload["variables"] == {"q": "name:#43298"}
    q = payload["query"]
    assert "orders(first: 1, query: $q)" in q
    # Curated defaults include these selections
    assert re.search(r"node\s*{[^}]*\bid\b", q)
    assert re.search(r"\bname\b", q)
    assert re.search(r"totalPriceSet\s*{\s*shopMoney\s*{\s*amount\s*currencyCode\s*}\s*}", q)
    assert re.search(r"customer\s*{\s*(?:id.*email|email.*id)\s*}", q)
    # Transactions block contains id, kind, gateway, and parentTransaction { id } in any order
    m = re.search(r"transactions\s*{([^}]*)}", q)
    assert m is not None
    tx_block = m.group(1)
    assert re.search(r"\bid\b", tx_block)
    assert re.search(r"\bkind\b", tx_block)
    assert re.search(r"\bgateway\b", tx_block)
    assert re.search(r"parentTransaction\s*{\s*id\s*}", q)
    assert re.search(r"refunds\s*{[^}]*createdAt[^}]*staffMember\s*{[^}]*firstName[^}]*lastName[^}]*}[^}]*totalRefundedSet\s*{[^}]*presentmentMoney\s*{[^}]*amount[^}]*currencyCode[^}]*}[^}]*shopMoney\s*{[^}]*amount[^}]*currencyCode[^}]*}[^}]*}[^}]*}", q)
    assert re.search(r"\bcancelledAt\b", q)


def test_allowed_selection_paths_validate_and_render():
    # Python-notation selection paths that map to the curated selection
    requested_py = [
        "id",
        "name",
        "customer",
        "transactions.parent_transaction.id",
        "refunds.total_refunded_set.shop_money.currency_code",
        "total_price_set.shop_money.amount",
    ]

    allowed, _ = _derive_allowlist_and_leaves()
    # Should not raise and should convert to GraphQL aliases
    out = _convert_and_validate_paths(requested_py, allowed)
    assert "id" in out
    assert "name" in out
    assert "customer" in out
    assert "transactions.parentTransaction.id" in out
    assert "refunds.totalRefundedSet.shopMoney.currencyCode" in out
    assert "totalPriceSet.shopMoney.amount" in out

    # Also ensure the builder accepts these paths and renders them
    req = FetchOrderRequest(order_number="43298")
    payload = build_order_fetch_request_payload(req, selection_paths=requested_py)
    q = payload["query"]
    assert "orders(first: 1, query: $q)" in q
    assert re.search(r"customer\s*{\s*(?:id.*email|email.*id)\s*}", q)
    assert re.search(r"transactions\s*{[^}]*parentTransaction\s*{\s*id\s*}[^}]*}", q)
    # Only shopMoney.currencyCode is requested under refunds in requested_py
    assert re.search(r"refunds\s*{[^}]*totalRefundedSet\s*{[^}]*shopMoney\s*{[^}]*\bcurrencyCode\b[^}]*}[^}]*}[^}]*}", q)
    # totalPriceSet.shopMoney.amount requested
    assert re.search(r"totalPriceSet\s*{\s*shopMoney\s*{[^}]*\bamount\b[^}]*}\s*}", q)


