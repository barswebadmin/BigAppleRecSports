from fastapi import APIRouter

from services.orders import handlers

router = APIRouter(prefix="/orders", tags=["orders"])

ROUTES = [
    ("GET",    "",            handlers.get_order),
    ("DELETE", "/{order_id}", handlers.cancel_order),
    ("POST",   "/webhooks",   handlers.handle_webhook),
]

for method, path, fn in ROUTES:
    router.add_api_route(path, fn, methods=[method])
