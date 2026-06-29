from typing import Any

from fastapi import Depends

from services.waitlists import service
from services.waitlists.requests import ListWaitlistQuery


async def list_entries(q: ListWaitlistQuery = Depends()) -> dict[str, Any]:
    """Materialize the `?product=X` query into `ListWaitlistQuery` and extract
    the scalar `product_id` for the service call. `signup` and `remove` route
    straight to `service.X` (no transformation needed) from `routes.py`."""
    return await service.list_for_product(q.product_id)
