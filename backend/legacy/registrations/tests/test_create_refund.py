import asyncio
from http import HTTPStatus
from unittest.mock import AsyncMock

from clients.shopify.models.base import ClientError
from controllers.refunds_controller import RefundsController
from models.refunds import RefundCreateInput


def test_create_refund_order_not_found():
    controller = RefundsController()
    controller.orders_service.get_order_for_refund = AsyncMock(return_value=(None, []))
    req = RefundCreateInput(
        order_id=1,
        amount=10.0,
        refund_method="store_credit",
        should_notify=True,
    )
    r = asyncio.run(controller.create_refund(req))
    assert r.type == HTTPStatus.NOT_FOUND.value
    assert r.errors == ["Order not found"]


def test_create_refund_shopify_fetch_errors():
    controller = RefundsController()
    controller.orders_service.get_order_for_refund = AsyncMock(
        return_value=(None, [ClientError(message="boom")]),
    )
    req = RefundCreateInput(
        order_id=1,
        amount=10.0,
        refund_method="store_credit",
        should_notify=True,
    )
    r = asyncio.run(controller.create_refund(req))
    assert r.type == HTTPStatus.INTERNAL_SERVER_ERROR.value
    assert r.errors == ["boom"]


def test_create_refund_success_uses_fetched_order_gid():
    controller = RefundsController()

    class _Order:
        id = "gid://shopify/Order/99"

    captured: list[RefundCreateInput] = []

    async def capture_refund(body: RefundCreateInput):
        captured.append(body)
        return {"id": "gid://shopify/Refund/1"}, []

    controller.orders_service.get_order_for_refund = AsyncMock(
        return_value=(_Order(), []),
    )
    controller.service.refund_shopify_order = AsyncMock(side_effect=capture_refund)

    req = RefundCreateInput(
        order_id=1,
        amount=10.0,
        refund_method="store_credit",
        should_notify=True,
    )
    r = asyncio.run(controller.create_refund(req))
    assert r.type == HTTPStatus.CREATED.value
    assert r.data == {"id": "gid://shopify/Refund/1"}
    assert len(captured) == 1
    assert captured[0].order_id == "gid://shopify/Order/99"
    assert captured[0].amount == 10.0
