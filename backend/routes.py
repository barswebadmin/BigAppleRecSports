"""
All HTTP routes for the backend API.

Each route is a thin stub that delegates to a controller/service.
Domain exceptions bubble up and are handled by the global exception
handler registered in main.py (see core/api_errors.py).
"""

from fastapi import APIRouter, HTTPException, Response

from core.clients import shopify

# from services.refunds import handlers as refunds_handlers
# from services.refunds import service as refunds_service


router_main = APIRouter()


# ── Products ─────────────────────────────────────────────────────────────────

products = APIRouter(prefix="/products", tags=["products"])


@products.post("/create")
async def create_product():
    return Response(status_code=204)


@products.patch("/update")
async def update_product():
    return Response(status_code=204)


@products.delete("/delete")
async def delete_product():
    return Response(status_code=204)


@products.post("/schedules/create")
async def create_product_schedule():
    return Response(status_code=204)


@products.patch("/schedules/update")
async def update_product_schedule():
    return Response(status_code=204)


@products.delete("/schedules/delete")
async def delete_product_schedule():
    return Response(status_code=204)


# ── Orders ───────────────────────────────────────────────────────────────────

orders = APIRouter(prefix="/orders", tags=["orders"])


@orders.get("/{order_identifier}")
async def get_order(order_identifier: str):
    """Fetch a single order by numeric ID (Shopify search syntax: ``id:<n>``)."""
    result = await shopify.orders_get(query=f"id:{order_identifier}", first=1)
    if not result.orders.nodes:
        raise HTTPException(status_code=404, detail=f"Order not found: {order_identifier}")
    return result.orders.nodes[0]


# @orders.delete("/{order_id}")
# async def cancel_order(order_id: str, body: CancelOrderRequest):
#     ...


# @orders.post("/webhooks")
# async def handle_order_webhook(req: Request):
#     ...


# ── Refunds ──────────────────────────────────────────────────────────────────
# Refunds service still uses the legacy shopify_client.shop_client + box import
# paths. Re-enable once it's migrated to the typed ShopifyClient.

# refunds = APIRouter(prefix="/refunds", tags=["refunds"])
#
# REFUND_ROUTES = [
#     ("POST", "/submit", refunds_service.submit),
#     ("POST", "/create", refunds_service.execute_refund_create),
#     ("POST", "/request", refunds_service.submit_request),
#     ("POST", "/webhooks", refunds_handlers.handle_webhook),
# ]
# for method, path, fn in REFUND_ROUTES:
#     refunds.add_api_route(path, fn, methods=[method])


# ── Waitlists ────────────────────────────────────────────────────────────────

waitlists = APIRouter(prefix="/waitlists", tags=["waitlists"])


@waitlists.post("/submit")
async def submit_waitlist_entry():
    return Response(status_code=204)


@waitlists.patch("/update")
async def update_waitlist_entry():
    return Response(status_code=204)


@waitlists.post("/admit")
async def admit_waitlist_entry():
    return Response(status_code=204)


@waitlists.delete("/remove")
async def remove_waitlist_entry():
    return Response(status_code=204)


# ── Aggregate ────────────────────────────────────────────────────────────────

router_main.include_router(products)
router_main.include_router(orders)
# router_main.include_router(refunds)
router_main.include_router(waitlists)
