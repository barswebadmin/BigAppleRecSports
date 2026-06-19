"""Domain view over Shopify order fetch results."""

from dataclasses import dataclass
from decimal import Decimal
from functools import cached_property
from typing import Any

from registrations.refunds import SeasonDates
from shopify_client.generated.find_orders import (
    FindOrdersOrdersNodes,
    FindOrdersOrdersNodesLineItemsNodes,
    FindOrdersOrdersNodesLineItemsNodesProduct,
)

from models._text import norm_key

SPORTS = (
    "dodgeball",
    "kickball",
    "pickleball",
    "bowling",
    "basketball",
    "volleyball",
    "soccer",
    "softball",
)
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
SEASONS = ("spring", "summer", "fall", "winter")
# Order matters: "wtnb+" must match before "wtnb".
DIVISIONS = ("wtnb+", "wtnb", "open")


def _enum_value(v: object) -> str | None:
    if v is None:
        return None
    return getattr(v, "value", None) or str(v)


def _money(amount_str: str | None) -> float:
    return float(Decimal(amount_str)) if amount_str else 0.0


def _find_in_tokens(needles: tuple[str, ...], tokens: list[str]) -> str | None:
    for needle in needles:
        if needle in tokens:
            return needle
    return None


def _division_tokens(tokens: list[str]) -> list[str]:
    expanded: list[str] = []
    for token in tokens:
        expanded.append(token)
        if token.endswith("div") and len(token) > 3:
            expanded.append(token[:-3])
    return expanded


def _parse_league_from_handle(handle: str) -> League:
    tokens = [t.strip().lower() for t in handle.split("-") if t.strip()]
    div_pool = _division_tokens(tokens)
    sport = _find_in_tokens(SPORTS, tokens)
    day = _find_in_tokens(DAYS, tokens)
    season = _find_in_tokens(SEASONS, tokens)
    division = _find_in_tokens(DIVISIONS, div_pool)
    return League(
        sport=sport.title() if sport else None,
        season=season,
        day=day.title() if day else None,
        division=division,
    )


@dataclass(frozen=True)
class League:
    sport: str | None
    season: str | None
    day: str | None
    division: str | None


@dataclass(frozen=True)
class RefundTransaction:
    id: str
    kind: str
    status: str
    gateway: str | None
    parent_id: str | None


@dataclass(frozen=True)
class ShopifyCustomer:
    email: str | None
    first_name: str | None
    last_name: str | None


@dataclass(frozen=True)
class ShopifyProduct:
    id: str
    title: str
    handle: str
    description_html: str | None

    @cached_property
    def league(self) -> League:
        return _parse_league_from_handle(self.handle)

    @cached_property
    def season_dates(self) -> SeasonDates:
        return SeasonDates.from_html(self.description_html or "")

    @classmethod
    def from_codegen(
        cls,
        node: FindOrdersOrdersNodesLineItemsNodesProduct | None,
    ) -> ShopifyProduct | None:
        if node is None:
            return None
        return cls(
            id=node.id,
            title=node.title,
            handle=node.handle,
            description_html=str(node.description_html) if node.description_html is not None else None,
        )


@dataclass(frozen=True)
class ShopifyOrder:
    name: str
    id: str
    email: str | None
    customer: ShopifyCustomer | None
    cancelled_at: Any
    order_total: float
    total_refunded: float
    refundable_balance: float
    currency_code: str | None
    transactions: list[RefundTransaction]
    product: ShopifyProduct | None
    _line_item_nodes: list[FindOrdersOrdersNodesLineItemsNodes]

    @property
    def is_cancelled(self) -> bool:
        return self.cancelled_at is not None

    @classmethod
    def from_codegen(cls, node: FindOrdersOrdersNodes) -> ShopifyOrder:
        order_total = _money(node.total_price_set.shop_money.amount if node.total_price_set else None)
        total_refunded = sum(
            (_money(r.total_refunded_set.shop_money.amount) for r in node.refunds if r.total_refunded_set),
            0.0,
        )
        currency_code = _enum_value(node.total_price_set.shop_money.currency_code if node.total_price_set else None)
        customer = None
        if node.customer is not None:
            customer = ShopifyCustomer(
                email=node.customer.email,
                first_name=node.customer.first_name,
                last_name=node.customer.last_name,
            )
        line_item_nodes = node.line_items.nodes
        first_item = line_item_nodes[0] if line_item_nodes else None
        return cls(
            name=node.name,
            id=node.id,
            email=node.email,
            customer=customer,
            cancelled_at=node.cancelled_at,
            order_total=order_total,
            total_refunded=total_refunded,
            refundable_balance=max(0.0, order_total - total_refunded),
            currency_code=currency_code,
            transactions=[
                RefundTransaction(
                    id=t.id,
                    kind=_enum_value(t.kind) or "",
                    status=_enum_value(t.status) or "",
                    gateway=t.gateway,
                    parent_id=t.parent_transaction.id if t.parent_transaction else None,
                )
                for t in node.transactions
            ],
            product=ShopifyProduct.from_codegen(first_item.product if first_item else None),
            _line_item_nodes=line_item_nodes,
        )

    def _first_line_item(self) -> FindOrdersOrdersNodesLineItemsNodes | None:
        return self._line_item_nodes[0] if self._line_item_nodes else None

    def _collect_attrs_containing(self, key_substring: str) -> list[tuple[str, str]]:
        line_item = self._first_line_item()
        if line_item is None:
            return []
        needle = key_substring.lower()
        out: list[tuple[str, str]] = []
        for attr in line_item.custom_attributes:
            if not attr.value:
                continue
            if needle in norm_key(attr.key):
                out.append((attr.key, attr.value))
        return out

    def candidate_emails(self) -> list[tuple[str, str]]:
        pairs = self._collect_attrs_containing("email address")
        if self.email:
            pairs.append(("order.email", self.email))
        if self.customer and self.customer.email:
            pairs.append(("order.customer.email", self.customer.email))
        return pairs

    def candidate_first_names(self) -> list[tuple[str, str]]:
        pairs = self._collect_attrs_containing("first name")
        if self.customer and self.customer.first_name:
            pairs.append(("order.customer.firstName", self.customer.first_name))
        return pairs

    def candidate_last_names(self) -> list[tuple[str, str]]:
        pairs = self._collect_attrs_containing("last name")
        if self.customer and self.customer.last_name:
            pairs.append(("order.customer.lastName", self.customer.last_name))
        return pairs
