"""All HTTP routes for the backend API.

Routes are thin wrappers around module-level dependencies + the Shopify
client. Cross-cutting concerns (auth, error mapping) are handled by the
exception handler in ``main.py`` (see ``core/api_errors.py``).
"""


from typing import Annotated

from fastapi import APIRouter, Response, Path, Body, Query, Depends, HTTPException

from modules.orders import (
    CancelOrderRequest,
    Order,
    OrderCancel,
    cancel_order,
    find_orders,
    get_order,
)
from modules.refunds.refunds_models import (
    RefundApproval,
    RefundRequest,
)
from modules.refunds import refunds_service
from modules.refunds.refunds_service import RefundBreakdown
from lib.clients.shopify.generated.refund_create import RefundCreate

router_main = APIRouter()

# products = APIRouter(prefix="/products", tags=["products"])


# @products.post("/create")
# async def create_product():
#     return Response(status_code=204)


# @products.patch("/update")
# async def update_product():
#     return Response(status_code=204)


# @products.delete("/delete")
# async def delete_product():
#     return Response(status_code=204)


# @products.post("/schedules/create")
# async def create_product_schedule():
#     return Response(status_code=204)


# @products.patch("/schedules/update")
# async def update_product_schedule():
#     return Response(status_code=204)


# @products.delete("/schedules/delete")
# async def delete_product_schedule():
#     return Response(status_code=204)


# ── Orders ───────────────────────────────────────────────────────────────────

async def existing_order(order_number: int) -> Order:
    """Resolve an Order by its customer-facing order number.

    Raises 404 unless the lookup returns exactly one order.
    """
    orders = await find_orders(order_number)
    if len(orders) != 1:
        raise HTTPException(
            status_code=404,
            detail=f"Expected 1 order for number {order_number}, found {len(orders)}",
        )
    return orders[0]


orders = APIRouter(prefix="/orders", tags=["orders"])


@orders.get("/{order_id}", response_model=Order)
async def read_order(order_id: Annotated[int, Path(title="The ID of the item to get", min_length=8)]):
    return await get_order(order_id)

@orders.get("/", response_model=Order)
async def list_orders(order_number: Annotated[int | str | None, Query(alias="number")]):
    return await find_orders(order_number)


@orders.delete("/{order_id}", response_model=OrderCancel)
async def delete_order(
    order_id: Annotated[int, Path(title="Shopify order ID", ge=1)],
    request_body: Annotated[CancelOrderRequest, Body()],
):
    return await cancel_order(order_id, request_body)


# @orders.post("/{order_id}/refund", response_model=RefundCreate)
# async def refund_order(
#     order_id: Annotated[int, Path(title="Shopify order ID", ge=1)],
#     body: Annotated[RefundApproval, Body()],
# ) -> RefundCreate:
#     return await refunds_service.refund_order(order_id, body)


# ── Refunds ──────────────────────────────────────────────────────────────────

refunds = APIRouter(prefix="/refunds", tags=["refunds"])


# @refunds.get("/{order_id}", response_model=Order)
# async def get_refunds(
#     order_id: Annotated[int, Path(title="Shopify order ID", ge=1)],
# ) -> Order:
#     return await refunds_service.get_refunds(order_id)


@refunds.post("/{order_number}/validate", response_model=RefundBreakdown)
async def validate_refund_request(
    order: Annotated[Order, Depends(existing_order)],
    request_body: Annotated[RefundRequest, Body()],
) -> RefundBreakdown:
    return await refunds_service.evaluate_refund_request(
        order,
        request_body,
    )


@refunds.post("/{order_id}/approve", response_model=RefundCreate)
async def approve_refund_request(
    order_id: Annotated[int, Path(title="Shopify order ID", ge=1)],
    request_body: Annotated[RefundApproval, Body()],
) -> RefundCreate:
    return await refunds_service.refund_order(order_id, request_body, validated=True)


# @refunds.patch("/update")
# async def update_refund_request() -> Response:
#     return Response(status_code=204)


# @refunds.post("/deny")
# async def deny_refund_request() -> Response:
#     return Response(status_code=204)


# @refunds.delete("/{refund_id}")
# async def cancel_refund_request(refund_id: str) -> Response:
#     return Response(status_code=204)


# ── Waitlists ────────────────────────────────────────────────────────────────

# waitlists = APIRouter(prefix="/waitlists", tags=["waitlists"])


# @waitlists.post("/submit")
# async def submit_waitlist_entry():
#     return Response(status_code=204)


# @waitlists.patch("/update")
# async def update_waitlist_entry():
#     return Response(status_code=204)


# @waitlists.post("/admit")
# async def admit_waitlist_entry():
#     return Response(status_code=204)


# @waitlists.delete("/remove")
# async def remove_waitlist_entry():
#     return Response(status_code=204)


# ── Aggregate ────────────────────────────────────────────────────────────────

# router_main.include_router(products)
router_main.include_router(orders)
router_main.include_router(refunds)
# router_main.include_router(waitlists)
