from __future__ import annotations

from typing import Annotated

from conf import config
from controllers.orders_controller import OrdersController
from controllers.refunds_controller import RefundsController
from fastapi import APIRouter, Depends, HTTPException, Response, Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from models.orders import OrderRequest, OrdersListResponse
from models.query_params import QueryParam
from models.refunds import RefundCreateInput, RefundRequestInput
from service_errors import ServiceErrors

orders_controller = OrdersController()
refunds_controller = RefundsController()


async def verify_bearer(
    credentials: HTTPAuthorizationCredentials | None = Security(HTTPBearer(auto_error=False)),
) -> None:
    if credentials is None or credentials.credentials != config.api_bearer_token:
        raise HTTPException(status_code=401, detail="Invalid bearer token")


# Health stays public: the GAS refund form pings it without credentials
reg_router = APIRouter(prefix="/registrations")


@reg_router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


orders_router = APIRouter(
    prefix="/orders",
    tags=["orders"],
    dependencies=[Depends(verify_bearer)],
)


@orders_router.get("/orders", tags=["orders"], response_model=None)
async def get_orders(
    params: Annotated[OrderRequest, Depends(QueryParam(OrderRequest).depends())],
) -> OrdersListResponse | Response:
    orders, errors = await orders_controller.get_orders(params)
    if errors:
        raise ServiceErrors(errors)
    if len(orders) == 0:
        return Response(status_code=204)

    return OrdersListResponse(orders=orders)


@orders_router.patch("/{order_id}", tags=["orders"])
async def update_order(order_id: str) -> dict:
    return await orders_controller.update_order(order_id)


@orders_router.delete("/{order_id}", tags=["orders"])
async def delete_order(order_id: str) -> dict:
    return await orders_controller.delete_order(order_id)


@orders_router.post("/request-refund", tags=["refunds"])
async def request_refund(body: RefundRequestInput) -> JSONResponse:
    return (await refunds_controller.request_refund(body)).to_http_response()


@orders_router.post("/{order_id}/refunds", tags=["refunds"])
async def create_refund(order_id: str, body: RefundCreateInput) -> JSONResponse:
    req = body.model_copy(update={"order_id": order_id})
    return (await refunds_controller.create_refund(req)).to_http_response()
