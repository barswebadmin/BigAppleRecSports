# ============================================================================
# FROZEN — DO NOT RUN OR UPDATE.
# These tests are intentionally disabled until the ShopifyRefundHandler Lambda
# restructure (REGISTRATIONS-REFACTOR-PLAN.md, Stages 1–2) settles. No tests are
# to be written or updated for this Lambda until then. The original source is
# preserved verbatim below inside a string literal so pytest collects nothing.
# Unfreeze by removing the `_FROZEN = r'''` wrapper and the trailing `'''`.
# ============================================================================

_FROZEN = r'''
"""Contract-level I→O tests for the refund request model.

Asserts the **canonical-only / full-cutover** contract: canonical snake_case
keys validate and normalize; legacy keys (``refund_or_credit``/``created_at``/
``isTest``) are rejected — no dual-accept.

``models`` lives in ``aws/lambda/functions/ShopifyRefundHandler``; ``conftest.py``
puts that dir on ``sys.path``.
"""

from datetime import datetime

import pytest
from models import RefundRequest
from pydantic import ValidationError


def test_canonical_payload_validates():
    req = RefundRequest.model_validate({
        "order_number": "1234",
        "email": "a@b.com",
        "refund_to": "store_credit",
        "submitted_at": "2026-03-11T00:30:00Z",
        "is_test": True,
    })
    assert req.refund_to == "store_credit"
    assert req.is_test is True
    assert req.order_number == "#1234"
    assert req.submitted_at is not None and req.submitted_at.tzinfo is not None


def test_legacy_keys_are_rejected():
    with pytest.raises(ValidationError):
        RefundRequest.model_validate({
            "refund_or_credit": "credit",
            "created_at": "2026-03-11T00:30:00Z",
            "isTest": True,
        })


def test_invalid_refund_to_is_rejected():
    with pytest.raises(ValidationError):
        RefundRequest.model_validate({"refund_to": "banana"})


def test_refund_to_defaults_to_store_credit():
    assert RefundRequest.model_validate({}).refund_to == "store_credit"


def test_order_number_normalization():
    assert RefundRequest.model_validate({"order_number": "1234"}).order_number == "#1234"
    assert RefundRequest.model_validate({"order_number": "#1234"}).order_number == "#1234"
    assert RefundRequest.model_validate({}).order_number == ""


def test_submitted_at_absent_defaults_to_aware_now():
    req = RefundRequest.model_validate({})
    assert isinstance(req.submitted_at, datetime)
    assert req.submitted_at.tzinfo is not None


def test_naive_submitted_at_is_tagged_new_york():
    req = RefundRequest.model_validate({"submitted_at": "2026-03-11T00:30:00"})
    assert req.submitted_at.tzinfo is not None
    # America/New_York in March DST is UTC-4.
    assert req.submitted_at.utcoffset().total_seconds() == -4 * 3600


def test_is_test_defaults_test_safe():
    assert RefundRequest.model_validate({}).is_test is True
    assert RefundRequest.model_validate({"is_test": False}).is_test is False
'''
