"""
All HTTP routes for the backend API.

Each route is a thin stub that delegates to a controller/service.
Domain exceptions bubble up and are handled by the global exception
handler registered in main.py (see core/api_errors.py).
"""

from fastapi import APIRouter, Response
from modules.orders.controllers.orders_controller import router as orders_router
from modules.refunds.controllers.refunds_controller import router as refunds_router

router = APIRouter()


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
# Stage 5 — orders router lives in modules.orders.controllers.orders_controller.
# The inline stubs (`@orders.get`, `@orders.patch`, `@orders.delete`) that
# previously lived here have been removed. The new controller owns
# DELETE /orders/{order_id}; GET / PATCH placeholders are not re-added
# because no current consumer relies on them.


# ── Refunds ──────────────────────────────────────────────────────────────────
# Stage 2 — refunds router lives in modules.refunds.controllers.refunds_controller.
# The inline stubs that previously lived here have been removed.


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


# ── Health ───────────────────────────────────────────────────────────────────

@router.get("/health")
async def health():
    return {"status": "healthy"}


# ── Aggregate ────────────────────────────────────────────────────────────────

router.include_router(products)
router.include_router(orders_router)
router.include_router(refunds_router)
router.include_router(waitlists)
