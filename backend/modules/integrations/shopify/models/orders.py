from __future__ import annotations
from pydantic import Field
from typing import Optional, Dict, Any
from shared.model_config import ApiModel


class Money(ApiModel):
    amount: str
    currency_code: str


class TotalPriceSet(ApiModel):
    shop_money: Money


class MoneySet(ApiModel):
    presentment_money: Money
    shop_money: Money


class ParentTransaction(ApiModel):
    id: Optional[str] = None


class Transaction(ApiModel):
    id: str
    kind: Optional[str] = None
    gateway: Optional[str] = None
    parent_transaction: Optional[ParentTransaction] = None


class CustomerRef(ApiModel):
    id: Optional[str] = None
    email: Optional[str] = None


class RefundStaffMember(ApiModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class Refund(ApiModel):
    created_at: Optional[str] = None
    staff_member: Optional[RefundStaffMember] = None
    total_refunded_set: Optional[MoneySet] = None


class Order(ApiModel):
    id: str
    name: str
    email: Optional[str] = None
    total_price_set: Optional[TotalPriceSet] = None
    total_capturable_set: Optional[Dict[str, Any]] = None
    customer: Optional[CustomerRef] = None
    transactions: Optional[list[Transaction]] = None
    refunds: Optional[list[Refund]] = None
    cancelled_at: Optional[str] = None


