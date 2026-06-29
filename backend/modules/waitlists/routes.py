from fastapi import APIRouter

from services.waitlists import handlers, service

router = APIRouter(prefix="/waitlists", tags=["waitlists"])

ROUTES = [
    ("POST",   "",             service.signup),
    ("GET",    "",             handlers.list_entries),
    ("DELETE", "/{entry_id}",  service.remove),
]

for method, path, fn in ROUTES:
    router.add_api_route(path, fn, methods=[method])
