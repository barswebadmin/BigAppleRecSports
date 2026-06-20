from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class GetOrderQuery(BaseModel):
    number: Optional[str] = Field(None, min_length=5, max_length=5)
    id: Optional[str] = Field(None, min_length=11, max_length=16)
    reason: Optional[Literal["cancel"]] = None

    @model_validator(mode="after")
    def exactly_one_identifier(self) -> "GetOrderQuery":
        if not self.number and not self.id:
            raise ValueError("Must provide 'number' or 'id'")
        if self.number and self.id:
            raise ValueError("Provide only one of 'number' or 'id'")
        return self


class CancelOrderRequest(BaseModel):
    reason: str = "CUSTOMER"
    notify_customer: bool = False
    restock: bool = False
    staff_note: Optional[str] = None
