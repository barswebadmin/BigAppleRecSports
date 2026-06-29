"""Refunds domain service. Flat module-level async functions, no class."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import ClassVar, Self
from uuid import uuid4
from zoneinfo import ZoneInfo

from core.clients import shopify
from lib.clients.shopify.generated.enums import OrderTransactionKind, OrderTransactionStatus
from lib.clients.shopify.generated.fragments import Order, OrderRefunds
from lib.clients.shopify.generated.input_types import (
    MoneyInput,
    OrderTransactionInput,
    RefundInput,
    RefundMethodInput,
    StoreCreditRefundInput,
)
from lib.clients.shopify.generated.products_get import ProductsGetProductsNodes
from lib.clients.shopify.generated.refund_create import RefundCreate
from lib.clients.shopify.exceptions import ShopifyUserError
from modules.refunds.refunds_models import (
    RefundApproval,
    RefundBaseModel,
    RefundMethod,
    RefundRequest,
)


# Legacy ``orders_service.submit_refund_request`` additionally computed:
#     total_refunded = sum(r.total_refunded_set.shop_money.amount for r in order.refunds)
#     refundable_balance = max(0, order_total - total_refunded)
# Not migrated — the new validate gate raises on any existing refund, so past
# the gate both values are known: total_refunded == 0, refundable_balance ==
# order_total.
class ExistingRefundsSummary(RefundBaseModel):
    """Existing refunds on an order, split by status. Internal to validation."""

    pending_refunds: list[OrderRefunds]
    completed_refunds: list[OrderRefunds]

    @classmethod
    def from_order(cls, order: Order) -> Self:
        completed: list[OrderRefunds] = []
        pending: list[OrderRefunds] = []
        for refund in order.refunds:
            if Decimal(refund.total_refunded_set.shop_money.amount) > 0:
                completed.append(refund)
                continue
            pending_txn = next(
                (t for t in refund.transactions.nodes
                 if t.kind == OrderTransactionKind.REFUND
                 and t.status == OrderTransactionStatus.PENDING),
                None,
            )
            if pending_txn is None:
                continue
            pending.append(refund)
        return cls(pending_refunds=pending, completed_refunds=completed)


def group_by_value(items: list[tuple[str, str]]) -> dict[str, list[str]]:
    """Group descriptor→value pairs by normalized value (strip+casefold)."""
    mapping: dict[str, list[str]] = {}
    for descriptor, value in items:
        mapping.setdefault(value.strip().casefold(), []).append(descriptor)
    return mapping


async def evaluate_refund_request(
    order: Order,
    request_details: RefundRequest,
) -> RefundBreakdown:
    """Evaluate eligibility + estimate for a refund request against an order."""

    email_addresses = group_by_value([
        ("from refund request", request_details.email),
        ("customer email", order.email),
        ("order form email", next(
            a.value for a in order.line_items.nodes[0].custom_attributes
            if "email address" in a.key.casefold()
        )),
    ])
    existing_refunds = any(t.kind == OrderTransactionKind.REFUND for t in order.transactions)

    if len(email_addresses) > 1 or order.cancelled_at or existing_refunds:
        raise ValueError("invalid")

    product_id = int(order.line_items.nodes[0].product.id.split("/")[-1])
    product = (await shopify.products_get(query=f"id:{product_id}", first=1)).products.nodes[0]
    return RefundBreakdown.estimate(order, request_details, product)


# async def get_refunds(order_id: int) -> Order:
#     """Return the order including its refunds."""
#     return await orders_service.get_order(order_id)


async def refund_order(
        order_id: int,
        refund_details: RefundApproval,
        validated: bool = False,

    ) -> RefundCreate:
    """Execute a refund against the order via Shopify."""

    if not validated:
        evaluation = evaluate_refund_request(order_id)
        if not evaluation.is_valid:
            raise "FIGURE IT OUT LATER"

    refund_input = to_mutation(
        order_id,
        refund_details.amount,
        refund_details.refund_method,
        refund_details.should_notify,
        refund_details.note,
        refund_details.parent_transaction_id,
    )

    result = await shopify.refund_create(input=refund_input, idempotency_key=str(uuid4()))
    user_errors = result.refund_create.user_errors if result.refund_create else []
    if user_errors:
        raise ShopifyUserError(
            "refundCreate",
            [{"message": err.message, "field": err.field} for err in user_errors],
        )
    return result


def to_mutation(
    order_id: int,
    amount: Decimal,
    refund_method: RefundMethod,
    should_notify: bool,
    note: str,
    parent_transaction_id: str | None = None,
) -> RefundInput:
    """Build a single-amount ``RefundInput`` discriminated by ``refund_method``."""
    order_gid = f"gid://shopify/Order/{order_id}"

    refund_base = RefundInput(order_id=order_gid, note=note, notify=should_notify)

    if refund_method == "original_payment":
        refund_base.transactions = [
            OrderTransactionInput(
                order_id=order_gid,
                amount=amount,
                kind="REFUND",
                gateway="shopify_payments",
                parent_id=parent_transaction_id,
            ),
        ]
    if refund_method == "store_credit":
        refund_base.refund_methods = [
            RefundMethodInput(
                store_credit_refund=StoreCreditRefundInput(
                    amount=MoneyInput(amount=amount, currency_code="USD"),
                ),
            ),
        ]
    return refund_base


# ── Refund-estimate engine ───────────────────────────────────────────────────


class RefundBreakdown(RefundBaseModel):
    """Refund estimate for one request: tier resolved from submission timing
    against the product's ``important_dates`` week cutoffs (midnight ET,
    inclusive boundary), and both method amounts computed from amount paid.
    ``tier`` is ``None`` past the week 5 cutoff (no refund eligible).
    """

    TIER_PERCENTAGES: ClassVar[dict[str, tuple[int, int]]] = {
        "more_than_2_weeks_before_week_1": (95, 100),
        "week1": (90, 95),
        "week2": (80, 85),
        "week3": (70, 75),
        "week4": (60, 65),
        "week5": (50, 55),
    }

    refund_method: RefundMethod
    created_at: datetime
    amount_paid: Decimal
    tier: str | None
    order_id: str
    product_id: str
    parent_transaction_id: str | None
    original_payment_amount: Decimal
    store_credit_amount: Decimal

    @classmethod
    def estimate(
        cls,
        order: Order,
        request_details: RefundRequest,
        product: ProductsGetProductsNodes,
    ) -> Self:
        et = ZoneInfo("America/New_York")
        fields = {f.key: f.value for f in product.important_dates.reference.fields}
        weeks = {
            "week1": datetime.combine(date.fromisoformat(fields["week1"]), time(0), tzinfo=et),
            "week2": datetime.combine(date.fromisoformat(fields["week2"]), time(0), tzinfo=et),
            "week3": datetime.combine(date.fromisoformat(fields["week3"]), time(0), tzinfo=et),
            "week4": datetime.combine(date.fromisoformat(fields["week4"]), time(0), tzinfo=et),
            "week5": datetime.combine(date.fromisoformat(fields["week5"]), time(0), tzinfo=et),
        }
        cutoffs = {"more_than_2_weeks_before_week_1": weeks["week1"] - timedelta(days=14), **weeks}
        tier = next(
            (name for name, cutoff in cutoffs.items() if request_details.created_at <= cutoff),
            None,
        )
        original_pct, credit_pct = cls.TIER_PERCENTAGES.get(tier, (0, 0))
        paid = Decimal(order.total_price_set.shop_money.amount)
        capture_txn = next(
            (t for t in order.transactions
             if t.kind in (OrderTransactionKind.CAPTURE, OrderTransactionKind.SALE)
             and t.status == OrderTransactionStatus.SUCCESS),
            None,
        )
        parent_transaction_id = (
            (capture_txn.parent_transaction.id if capture_txn.parent_transaction else capture_txn.id)
            if capture_txn else None
        )
        return cls(
            refund_method=request_details.refund_method,
            created_at=request_details.created_at,
            amount_paid=paid,
            tier=tier,
            order_id=order.id,
            product_id=product.id,
            parent_transaction_id=parent_transaction_id,
            original_payment_amount=paid * original_pct / 100,
            store_credit_amount=paid * credit_pct / 100,
        )
