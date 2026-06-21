"""Money helpers used by the refund-cancel workflow.

Per design § 2.d (Stage 2 Commit 2.2 — D19):

  ``Money``, ``format_money``, and ``to_decimal`` consolidate into this
  module so any caller (``EstimateService``, the Stage 5 execute path,
  future workflows) imports them from one place.

Drift note (Stage 2 inventory): no prior ``format_money`` / ``to_decimal``
implementations existed in the backend. The only ``Money`` types in the tree
were Shopify schema GraphQL types unrelated to a money-formatting utility.
The implementations below are minimal, USD-only, and dependency-free.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


def to_decimal(value: Any) -> Decimal:
    """Defensive coercion of arbitrary inputs (str, int, float, Decimal,
    None) to `Decimal`.

    Correctness properties:
      - ``to_decimal(None)`` returns ``Decimal("0")``.
      - ``to_decimal("")`` returns ``Decimal("0")``.
      - ``to_decimal(<malformed string>)`` returns ``Decimal("0")``
        (does not raise).
      - For numeric inputs, the conversion preserves exact decimal value
        (floats are stringified first to avoid binary-float artifacts —
        ``Decimal(0.1)`` would otherwise yield
        ``0.1000000000000000055511151231257827021181583404541015625``).
    """
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def format_money(amount: Any, currency: str = "USD") -> str:
    """Format a numeric amount as a money string.

    USD-only by design (BARS does not run multi-currency). Returns the
    canonical form ``"$<amount>"`` for USD, falling back to
    ``"<amount> <currency>"`` for other codes so non-USD values are
    visibly distinct.

    Correctness properties:
      - ``format_money(None)``  → ``"$0.00"``.
      - ``format_money("0")``   → ``"$0.00"``.
      - Always exactly two decimal places.
      - Negative amounts render as ``"-$X.YY"`` (sign before symbol).
    """
    decimal_amount = to_decimal(amount)
    quantized = decimal_amount.quantize(Decimal("0.01"))
    code = (currency or "USD").upper()
    if code == "USD":
        sign = "-" if quantized < 0 else ""
        magnitude = abs(quantized)
        return f"{sign}${magnitude:.2f}"
    return f"{quantized:.2f} {code}"


@dataclass(frozen=True)
class Money:
    """Lightweight (amount, currency) value type.

    Used for places where the bare ``Decimal`` is too anemic to carry the
    currency code. Frozen + hashable so it can be used as a dict key /
    cache token.

    Correctness properties:
      - ``Money(amount, currency)`` always stores ``amount`` as a
        ``Decimal`` (any ``Any``-typed input is coerced via
        :func:`to_decimal`).
      - Currency defaults to USD.
      - ``str(Money(...))`` delegates to :func:`format_money` for
        consistency.
    """

    amount: Decimal
    currency: str = "USD"

    @classmethod
    def of(cls, amount: Any, currency: str = "USD") -> "Money":
        """Smart constructor that runs :func:`to_decimal` on ``amount``."""
        return cls(amount=to_decimal(amount), currency=(currency or "USD").upper())

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return format_money(self.amount, self.currency)
