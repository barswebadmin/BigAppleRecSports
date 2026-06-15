"""Compare a refund-request payload to a fetched Shopify order.

Three checks, all soft (produce warnings, never raise):

  1. Email — fuzzy. We look at *every* line-item custom attribute whose key
     contains the words "email address" (case-insensitive substring), plus the
     order's billing email and the linked customer's email. The request email
     matches if it equals any of those, comparing case-insensitively and
     ignoring surrounding whitespace.

  2. First name — line-item custom attribute whose key contains "first name"
     (any of "First Name", "Preferred First Name", "preferred_first_name", ...).
     Falls back to the linked customer's ``firstName``.

  3. Last name — same pattern as first name.

Why fuzzy on the attribute key: registration forms over the years have used a
mix of labels ("Best Contact Email Address", "Email Address", "Player Email
Address"). Doing exact-string matching breaks whenever a form changes. The
predictable invariant is the substring "email address" / "first name" / "last
name" — that's what we anchor on.

Returns a structured ``ValidationResult`` so downstream code can decide what to
warn vs. block on. Nothing here is fatal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Protocol


# --- Order-shape Protocols ---------------------------------------------------
# We don't import the codegen'd FindOrdersOrdersNodes type here — it would
# couple this module to a specific Shopify schema revision. Instead we declare
# the minimal duck-typed interface we need. Codegen types satisfy this.

class _Attr(Protocol):
    key: str
    value: str | None


class _LineItem(Protocol):
    @property
    def custom_attributes(self) -> list[_Attr]: ...


class _Customer(Protocol):
    email: str | None
    first_name: str | None
    last_name: str | None


class _LineItemsConnection(Protocol):
    @property
    def nodes(self) -> list[_LineItem]: ...


class OrderLike(Protocol):
    """Subset of the order shape needed for validation."""
    email: str | None
    customer: _Customer | None
    line_items: _LineItemsConnection


# --- Result ------------------------------------------------------------------


@dataclass
class FieldMatch:
    """Result of comparing one request field to candidates pulled from the order.

    ``matched_against`` carries the value(s) we actually matched on, so the
    caller can show "your input X matched line-item attribute 'Best Contact
    Email Address' = X" in a Slack message.
    """
    matched: bool
    request_value: str
    candidates: list[str] = field(default_factory=list)
    matched_against: str | None = None


@dataclass
class ValidationResult:
    email: FieldMatch
    first_name: FieldMatch
    last_name: FieldMatch

    @property
    def all_passed(self) -> bool:
        return self.email.matched and self.first_name.matched and self.last_name.matched

    @property
    def warnings(self) -> list[str]:
        """Human-readable warnings for each failed check — empty when ``all_passed``."""
        out: list[str] = []
        if not self.email.matched:
            out.append(
                f"Email mismatch: request '{self.email.request_value}' did not match "
                f"any of {self.email.candidates or ['(no candidates found on order)']}"
            )
        if not self.first_name.matched:
            out.append(
                f"First name mismatch: request '{self.first_name.request_value}' did not match "
                f"any of {self.first_name.candidates or ['(no candidates found on order)']}"
            )
        if not self.last_name.matched:
            out.append(
                f"Last name mismatch: request '{self.last_name.request_value}' did not match "
                f"any of {self.last_name.candidates or ['(no candidates found on order)']}"
            )
        return out


# --- Internals ---------------------------------------------------------------


def _norm(s: str | None) -> str:
    """Lowercase + strip surrounding whitespace, ``None`` becomes ``''``."""
    return (s or "").strip().lower()


def _first_line_item(order: OrderLike) -> _LineItem | None:
    nodes = order.line_items.nodes
    return nodes[0] if nodes else None


def _norm_key(key: str | None) -> str:
    """Normalize a custom-attribute key for fuzzy matching.

    Lowercases, then collapses ``_`` and ``-`` into spaces so e.g.
    ``"preferred_first_name"`` and ``"Preferred First Name"`` are equivalent.
    GAS / Shopify form-processor variants use either convention; the substring
    "first name" matches both after this normalization.
    """
    return (key or "").lower().replace("_", " ").replace("-", " ")


def _collect_attrs_containing(
    line_item: _LineItem | None,
    key_substring: str,
) -> list[tuple[str, str]]:
    """All ``(label, value)`` pairs from this line item whose attribute key contains
    ``key_substring`` (case-insensitive, ``_``/``-`` treated as space). Empty values are skipped.

    The returned ``label`` is the attribute's key *as-typed* (preserving casing /
    separators) so diagnostic messages quote the actual field name.
    """
    if line_item is None:
        return []
    needle = key_substring.lower()
    out: list[tuple[str, str]] = []
    for attr in line_item.custom_attributes:
        if not attr.value:
            continue
        if needle in _norm_key(attr.key):
            out.append((attr.key, attr.value))
    return out


def _match(request_value: str, candidates: Iterable[tuple[str, str]]) -> FieldMatch:
    """Case-insensitive, whitespace-trimmed match of ``request_value`` against any candidate.

    ``candidates`` is an iterable of ``(label, value)`` pairs — the label is what
    the matching candidate's source was (e.g. "Best Contact Email Address",
    "order.customer.email") for diagnostic purposes.
    """
    target = _norm(request_value)
    pool = list(candidates)
    if not target:
        return FieldMatch(matched=False, request_value=request_value, candidates=[v for _, v in pool])
    for label, value in pool:
        if _norm(value) == target:
            return FieldMatch(
                matched=True,
                request_value=request_value,
                candidates=[v for _, v in pool],
                matched_against=label,
            )
    return FieldMatch(matched=False, request_value=request_value, candidates=[v for _, v in pool])


# --- Public surface ----------------------------------------------------------


def email_candidates(order: OrderLike) -> list[tuple[str, str]]:
    """All emails the request email might legitimately match.

    Pulls in:
      - any line-item custom attribute whose key contains "email address"
        (case-insensitive). The "Best Contact Email Address" form field is the
        canonical example; "Player Email Address" / "Backup Email Address" /
        future variants are caught the same way.
      - order.email (the billing email at checkout)
      - order.customer.email (the linked customer record, may differ from billing)
    """
    items = _first_line_item(order)
    pairs = _collect_attrs_containing(items, "email address")
    if order.email:
        pairs.append(("order.email", order.email))
    if order.customer and order.customer.email:
        pairs.append(("order.customer.email", order.customer.email))
    return pairs


def first_name_candidates(order: OrderLike) -> list[tuple[str, str]]:
    items = _first_line_item(order)
    pairs = _collect_attrs_containing(items, "first name")
    if order.customer and order.customer.first_name:
        pairs.append(("order.customer.firstName", order.customer.first_name))
    return pairs


def last_name_candidates(order: OrderLike) -> list[tuple[str, str]]:
    items = _first_line_item(order)
    pairs = _collect_attrs_containing(items, "last name")
    if order.customer and order.customer.last_name:
        pairs.append(("order.customer.lastName", order.customer.last_name))
    return pairs


def validate_request_against_order(
    *,
    request_email: str,
    request_first_name: str,
    request_last_name: str,
    order: OrderLike,
) -> ValidationResult:
    """Run all three checks and return a structured result.

    The caller decides how to surface failures (block, warn, log) — this
    function never raises on a mismatch.
    """
    return ValidationResult(
        email=_match(request_email, email_candidates(order)),
        first_name=_match(request_first_name, first_name_candidates(order)),
        last_name=_match(request_last_name, last_name_candidates(order)),
    )
