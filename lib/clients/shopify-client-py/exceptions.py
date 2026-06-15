"""Exceptions raised by the Shopify GraphQL client wrappers.

The wrapper methods on ``ShopifyClient`` coerce any non-empty mutation
``userErrors`` into a ``ShopifyUserError``. Callers handle business failures via
``except``, not by inspecting return values.
"""

from typing import Any, Iterable, TypeVar

T = TypeVar("T")


class ShopifyUserError(Exception):
    """Raised when a Shopify mutation returns one or more userErrors.

    Attributes:
        operation: Name of the mutation, e.g. ``"adjustInventory"``.
        user_errors: The list of user-error objects from the mutation payload.
    """

    def __init__(self, operation: str, user_errors: list[Any]) -> None:
        self.operation = operation
        self.user_errors = user_errors
        super().__init__(self._format())

    def _format(self) -> str:
        parts = []
        for e in self.user_errors:
            code = getattr(e, "code", None) or "?"
            message = getattr(e, "message", "")
            field = getattr(e, "field", None) or []
            field_str = ".".join(str(f) for f in field) if field else "-"
            parts.append(f"[{code}] {message} (field={field_str})")
        return f"{self.operation}: " + "; ".join(parts)

    def has_code(self, code: str) -> bool:
        return any(getattr(e, "code", None) == code for e in self.user_errors)


def raise_if_user_errors(operation: str, result: T) -> T:
    """Postcheck for a mutation payload. Raises if ``user_errors`` is non-empty.

    Use as the final step in every ``ShopifyClient`` wrapper method::

        return raise_if_user_errors("opName", self.<codegen_method>(...))
    """
    if result is None:
        raise ShopifyUserError(operation, [_NullResultError()])
    errors: Iterable[Any] = getattr(result, "user_errors", None) or []
    errors = list(errors)
    if errors:
        raise ShopifyUserError(operation, errors)
    return result


class _NullResultError:
    """Sentinel surfaced when a mutation returns ``None`` instead of a payload."""

    code = "NULL_RESULT"
    message = "Mutation returned no payload"
    field: list[str] = []
