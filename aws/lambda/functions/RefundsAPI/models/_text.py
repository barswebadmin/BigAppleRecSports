"""Shared text normalization for request↔order matching."""

from collections.abc import Iterable


def norm(s: str | None) -> str:
    return (s or "").strip().lower()


def norm_key(key: str | None) -> str:
    """Lowercase, then collapse ``_``/``-`` to spaces so e.g.
    ``"preferred_first_name"`` and ``"Preferred First Name"`` are equivalent."""
    return (key or "").lower().replace("_", " ").replace("-", " ")


def match_field(request_value: str, candidates: Iterable[tuple[str, str]]) -> tuple[bool, list[str], str | None]:
    """Case-insensitive, whitespace-trimmed match against any ``(label, value)`` candidate.

    Returns ``(matched, candidate_values, matched_against_label)``.
    """
    target = norm(request_value)
    pool = list(candidates)
    values = [v for _, v in pool]
    if not target:
        return False, values, None
    for label, value in pool:
        if norm(value) == target:
            return True, values, label
    return False, values, None
