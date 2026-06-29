# from __future__ import annotations

# from fastapi import Query
# from models.types import (
#     Day,
#     Division,
#     EndDate,
#     OrderId,
#     OrderNumber,
#     ProductHandle,
#     ProductId,
#     Season,
#     Sport,
#     StartDate,
#     Year,
# )
# from pydantic import BaseModel


# class OrderQueryParams(BaseModel):
#     order_id: OrderId | None = Query(None)
#     order_number: OrderNumber | None = Query(None)
#     product_id: ProductId | None = Query(None)
#     handle: ProductHandle | None = Query(None)
#     start_date: StartDate | None = Query(None)
#     end_date: EndDate | None = Query(None)
#     season: Season | None = Query(None)
#     year: Year | None = Query(None)
#     sport: Sport | None = Query(None)
#     day: Day | None = Query(None)
#     division: Division | None = Query(None)
#     dev_func: str | None = Query(None)
