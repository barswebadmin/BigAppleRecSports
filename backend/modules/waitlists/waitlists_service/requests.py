from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class WaitlistSignupRequest(BaseModel):
    """Body for `POST /waitlists`. Identifies the product the user wants to
    join and the customer fields needed to notify them when a spot opens."""

    product_id: str = Field(min_length=1)
    email: EmailStr
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    phone: Optional[str] = None


class ListWaitlistQuery(BaseModel):
    """Query model for `GET /waitlists?product=X`. The query-string key is
    `product`; the field's `alias` exposes it as such while keeping a
    snake_case attribute name internally."""

    product_id: str = Field(alias="product", min_length=1)
