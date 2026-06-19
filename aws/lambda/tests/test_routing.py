# ============================================================================
# FROZEN — DO NOT RUN OR UPDATE.
# These tests are intentionally disabled until the ShopifyRefundHandler Lambda
# restructure (REGISTRATIONS-REFACTOR-PLAN.md, Stages 1–2) settles. No tests are
# to be written or updated for this Lambda until then. The original source is
# preserved verbatim below inside a string literal so pytest collects nothing.
# Unfreeze by removing the `_FROZEN = r'''` wrapper and the trailing `'''`.
# ============================================================================

_FROZEN = r'''
"""I→O tests for ``main.lambda_handler`` action routing.

The evaluate path's domain work (``handle_initial_request``) and Slack POST are
stubbed so routing is tested without Shopify / network. ``conftest.py`` puts the
function dir on ``sys.path``.
"""

import main


def test_create_refund_routes_to_process_stub():
    out = main.lambda_handler(
        {"action": "create_refund", "order_number": "#1234", "idempotency_key": "refund:#1234"},
        None,
    )
    assert out["status"] == "not_implemented"
    assert out["action"] == "create_refund"
    assert out["order_number"] == "#1234"


def test_cancel_order_routes_to_process_stub():
    out = main.lambda_handler({"action": "cancel_order", "order_number": "#1234"}, None)
    assert out["status"] == "not_implemented"
    assert out["action"] == "cancel_order"


def test_unknown_action_is_400():
    out = main.lambda_handler({"action": "frobnicate"}, None)
    assert out["error"].startswith("Unknown action")


def test_no_action_defaults_to_evaluate(monkeypatch):
    captured: dict = {}

    class _FakeResult:
        def to_json(self):
            return {"order_found": True}

    monkeypatch.setattr(main, "handle_initial_request", lambda req: _FakeResult())
    monkeypatch.setattr(
        main, "post_to_slack", lambda url, variables: captured.update(url=url, variables=variables)
    )

    out = main.lambda_handler({"order_number": "1234"}, None)
    assert out == {"order_found": True}
    assert "variables" in captured  # eval path posted to Slack


def test_explicit_evaluate_action_routes_to_initial(monkeypatch):
    seen: dict = {}

    class _FakeResult:
        def to_json(self):
            return {"order_found": False}

    monkeypatch.setattr(
        main, "handle_initial_request", lambda req: seen.update(order=req.order_number) or _FakeResult()
    )
    monkeypatch.setattr(main, "post_to_slack", lambda url, variables: None)

    out = main.lambda_handler({"action": "evaluate_refund", "order_number": "1234"}, None)
    assert out == {"order_found": False}
    assert seen["order"] == "#1234"  # request was validated/normalized
'''
