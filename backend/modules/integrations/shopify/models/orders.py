from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from backend.shared.model_config import BaseModelConfig


class Money(BaseModel):
    model_config = BaseModelConfig
    amount: str
    currency_code: str


class TotalPriceSet(BaseModel):
    model_config = BaseModelConfig
    shop_money: Money


class MoneySet(BaseModel):
    model_config = BaseModelConfig
    presentment_money: Money
    shop_money: Money


class ParentTransaction(BaseModel):
    model_config = BaseModelConfig
    id: Optional[str] = None


class Transaction(BaseModel):
    model_config = BaseModelConfig
    id: str
    kind: Optional[str] = None
    gateway: Optional[str] = None
    parent_transaction: Optional[ParentTransaction] = None


class CustomerRef(BaseModel):
    model_config = BaseModelConfig
    id: Optional[str] = None
    email: Optional[str] = None


class RefundStaffMember(BaseModel):
    model_config = BaseModelConfig
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class Refund(BaseModel):
    model_config = BaseModelConfig
    created_at: Optional[str] = None
    staff_member: Optional[RefundStaffMember] = None
    total_refunded_set: Optional[MoneySet] = None


class Order(BaseModel):
    model_config = BaseModelConfig
    id: str
    name: str
    email: Optional[str] = None
    total_price_set: Optional[TotalPriceSet] = None
    total_capturable_set: Optional[Dict[str, Any]] = None
    customer: Optional[CustomerRef] = None
    transactions: Optional[List[Transaction]] = None
    refunds: Optional[List[Refund]] = None
    cancelled_at: Optional[str] = None


