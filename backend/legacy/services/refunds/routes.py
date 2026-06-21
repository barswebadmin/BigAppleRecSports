from fastapi import APIRouter

from services.refunds import handlers, service

router = APIRouter(prefix="/refunds", tags=["refunds"])

ROUTES = [
    ("POST", "/submit", service.submit),
    ("POST", "/create", service.execute_refund_create),
    ("POST", "/request", service.submit_request),
    ("POST", "/webhooks", handlers.handle_webhook),
]

for method, path, fn in ROUTES:
    router.add_api_route(path, fn, methods=[method])
