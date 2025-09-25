import json
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from new_structure_target.routers.refunds import router


def create_app():
    app = FastAPI()
    app.include_router(router)
    return app


def test_missing_fields_returns_422_and_lists_missing_messages():
    app = create_app()
    client = TestClient(app)

    # Missing both
    resp = client.post("/refunds/submit-request", json={})
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert "Email is required" in detail
    assert "Order number is required" in detail

    # Missing one
    resp = client.post("/refunds/submit-request", json={"email": "a@b.com"})
    assert resp.status_code == 422
    assert "Order number is required" in resp.json()["detail"]


def test_validation_rules_enforced():
    app = create_app()
    client = TestClient(app)

    # Invalid email
    resp = client.post(
        "/refunds/submit-request",
        json={"email": "bad", "orderNumber": "#1234"},
    )
    assert resp.status_code == 422
    assert "Invalid email" in resp.json()["detail"]

    # Invalid order number (<4 digits)
    resp = client.post(
        "/refunds/submit-request",
        json={"email": "a@b.cd", "orderNumber": "#123"},
    )
    assert resp.status_code == 422
    assert "Invalid order number" in resp.json()["detail"]


def test_calls_service_when_valid_inputs():
    app = create_app()
    client = TestClient(app)

    # Patch the symbol used by the router module (imported into its namespace)
    with patch(
        "new_structure_target.routers.refunds.process_initial_refund_request",
        return_value={"success": True},
    ) as mocked:
        resp = client.post(
            "/refunds/submit-request",
            json={"email": "user@example.com", "orderNumber": "#12345"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data == {"success": True}
        assert mocked.called
        # Ensure called with parsed values
        args, kwargs = mocked.call_args
        assert kwargs["email"] == "user@example.com"
        assert kwargs["order_number"] == "#12345"
        assert "request_submitted_at" in kwargs


