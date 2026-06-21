import asyncio
from datetime import datetime, timezone
from http import HTTPStatus
from unittest.mock import AsyncMock

import pytest
from clients.shopify.models.base import ClientError
from controllers.refunds_controller import RefundsController
from models.refunds import RefundRequestInput
from pydantic import ValidationError


def test_refund_request_input_requires_order_identifier():
    with pytest.raises(ValidationError):
        RefundRequestInput(
            email_address="a@example.com",
            refund_method="store_credit",
            created_at=datetime.now(timezone.utc),
        )


def test_request_refund_order_not_found():
    controller = RefundsController()
    controller.orders_service.get_order_for_refund = AsyncMock(return_value=(None, []))
    req = RefundRequestInput(
        order_number=99999,
        email_address="a@example.com",
        refund_method="store_credit",
        created_at=datetime.now(timezone.utc),
    )
    r = asyncio.run(controller.request_refund(req))
    assert r.type == HTTPStatus.NOT_FOUND.value
    assert r.errors == ["Order not found"]


def test_request_refund_shopify_errors():
    controller = RefundsController()
    controller.orders_service.get_order_for_refund = AsyncMock(
        return_value=(None, [ClientError(message="throttled")]),
    )
    req = RefundRequestInput(
        order_id=1,
        email_address="a@example.com",
        refund_method="store_credit",
        created_at=datetime.now(timezone.utc),
    )
    r = asyncio.run(controller.request_refund(req))
    assert r.type == HTTPStatus.INTERNAL_SERVER_ERROR.value
    assert r.errors == ["throttled"]
