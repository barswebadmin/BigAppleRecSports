"""Case-insensitive matching of refund request fields against Shopify order data."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from box import Box


def norm(s: str | None) -> str:
    return (s or "").strip().lower()


def norm_key(key: str | None) -> str:
    return (key or "").lower().replace("_", " ").replace("-", " ")


def match_field(
    request_value: str,
    candidates: Iterable[tuple[str, str]],
) -> tuple[bool, list[str], str | None]:
    target = norm(request_value)
    pool = list(candidates)
    values = [v for _, v in pool]
    if not target:
        return False, values, None
    for label, value in pool:
        if norm(value) == target:
            return True, values, label
    return False, values, None


def _collect_line_item_attrs(order: Box, key_substring: str) -> list[tuple[str, str]]:
    line_items = order.line_items or []
    if not line_items:
        return []
    first = line_items[0]
    attrs = getattr(first, "custom_attributes", None) or []
    needle = key_substring.lower()
    out: list[tuple[str, str]] = []
    for attr in attrs:
        val = getattr(attr, "value", None)
        if not val:
            continue
        key = getattr(attr, "key", "") or ""
        if needle in norm_key(key):
            out.append((key, val))
    return out


def candidate_emails(order: Box) -> list[tuple[str, str]]:
    pairs = _collect_line_item_attrs(order, "email address")
    if order.email:
        pairs.append(("order.email", order.email))
    cust = order.customer
    if cust is not None and cust.email:
        pairs.append(("order.customer.email", cust.email))
    return pairs


def candidate_first_names(order: Box) -> list[tuple[str, str]]:
    pairs = _collect_line_item_attrs(order, "first name")
    cust = order.customer
    if cust is not None and cust.first_name:
        pairs.append(("order.customer.first_name", cust.first_name))
    return pairs


def candidate_last_names(order: Box) -> list[tuple[str, str]]:
    pairs = _collect_line_item_attrs(order, "last name")
    cust = order.customer
    if cust is not None and cust.last_name:
        pairs.append(("order.customer.last_name", cust.last_name))
    return pairs


@dataclass
class OrderMatchResult:
    email: tuple[bool, list[str], str | None]
    first_name: tuple[bool, list[str], str | None]
    last_name: tuple[bool, list[str], str | None]

    @property
    def all_passed(self) -> bool:
        return self.email[0] and self.first_name[0] and self.last_name[0]

    def warnings(self) -> list[str]:
        out: list[str] = []
        if not self.email[0]:
            out.append(
                f"Email mismatch: request did not match any of {self.email[1] or ['(no candidates found on order)']}"
            )
        if not self.first_name[0]:
            out.append(
                "First name mismatch: request did not match any of "
                f"{self.first_name[1] or ['(no candidates found on order)']}"
            )
        if not self.last_name[0]:
            out.append(
                "Last name mismatch: request did not match any of "
                f"{self.last_name[1] or ['(no candidates found on order)']}"
            )
        return out


def validate_against_order(
    order: Box,
    *,
    email: str,
    first_name: str,
    last_name: str,
) -> OrderMatchResult:
    return OrderMatchResult(
        email=match_field(email, candidate_emails(order)),
        first_name=match_field(first_name, candidate_first_names(order)),
        last_name=match_field(last_name, candidate_last_names(order)),
    )
