from pydantic import BaseModel


class GetOrderQuery(BaseModel):
    id_or_number: str


class CancelOrderRequest(BaseModel):
    reason: str = "CUSTOMER"
    notify_customer: bool = False
    restock: bool = False
    staff_note: str | None = None
