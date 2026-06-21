"""Date helpers used by the refund-cancel workflow.

Per design § 2.d (Stage 2 Commit 2.1 — D20):

  ``parse_season_start_date``, ``parse_off_dates``, and ``weeks_into_season``
  consolidate into this module so any caller (``EstimateService``, the
  Stage 5 execute path, future workflows) imports them from one place.

Drift note (Stage 2 inventory): the design table cited
``backend/legacy/shared/date_utils.py`` as the source of these three helpers.
That file does NOT actually contain functions named
``parse_season_start_date`` / ``parse_off_dates`` / ``weeks_into_season`` —
the analogous logic is folded inline into ``extract_season_dates`` and
``calculate_refund_amount`` (already superseded by ``refund_calculator.py``).
The implementations below mirror the canonical estimator's parsing rules
(``backend/modules/refunds/refund_calculator.py``: ``parse_date_mdy`` /
``parse_csv_dates``) so behavior is consistent with the canonical estimator.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Iterable

_BARS_TZ = timezone.utc
"""Season cutoffs live at UTC 07:00 by BARS convention. See
``refund_calculator.parse_date_mdy``."""


def parse_season_start_date(date_str: str | None) -> date | None:
    """Parse a ``M/D/YY`` or ``M/D/YYYY`` string into a `date`.

    Correctness properties:
      - ``parse_season_start_date(None)`` returns ``None``.
      - ``parse_season_start_date("")`` returns ``None``.
      - On a malformed token (non-numeric, missing separator, out-of-range
        month/day), returns ``None`` rather than raising.
      - Two-digit years are normalized to ``2000 + year`` (e.g. ``25`` →
        ``2025``).
      - Whitespace at either end is stripped.

    Returned dates are calendar dates (no time component) — pair with
    :func:`weeks_into_season` for ladder math.
    """
    if not date_str:
        return None
    token = date_str.strip()
    if not token or "/" not in token:
        return None
    try:
        month_s, day_s, year_s = token.split("/")
        month, day, year = int(month_s), int(day_s), int(year_s)
    except (ValueError, AttributeError):
        return None
    if year < 100:
        year += 2000
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_off_dates(off_dates_str: str | None) -> list[date]:
    """Parse a comma-separated list of ``M/D/YY`` dates into a sorted
    ``list[date]``.

    Correctness properties:
      - ``parse_off_dates(None)`` returns ``[]``.
      - ``parse_off_dates("")`` returns ``[]``.
      - Malformed individual entries are silently skipped (matches the
        canonical estimator's tolerance for partial-data product
        descriptions).
      - The result is sorted ascending — callers can rely on this when
        iterating to apply week-shifts.
      - Surrounding whitespace on each entry is stripped.
    """
    if not off_dates_str:
        return []
    out: list[date] = []
    for part in off_dates_str.split(","):
        parsed = parse_season_start_date(part)
        if parsed is not None:
            out.append(parsed)
    return sorted(out)


def weeks_into_season(
    now: datetime,
    season_start: date,
    off_dates: Iterable[date] | None = None,
) -> int:
    """Number of full weeks ``now`` is into the season starting at
    ``season_start``, accounting for ``off_dates`` that push the schedule
    forward by one week each.

    Correctness properties:
      - When ``now`` falls before ``season_start``, the function returns ``0``
        (never negative) — the "before week 1" tier is the caller's concern.
      - Each off-date that coincides with a scheduled week shifts that week
        and every subsequent week forward by 7 days, mirroring
        ``WeekSchedule.build`` in ``refund_calculator.py``.
      - The result is unbounded above; callers cap at 5 (or 6 for short
        seasons) when applying tier ladders.

    The ``now`` argument may be naive or aware; naive datetimes are coerced
    to UTC. ``season_start`` is a calendar date; it is expanded internally
    to UTC 07:00 to align with BARS season cutoffs.
    """
    if now.tzinfo is None:
        now = now.replace(tzinfo=_BARS_TZ)

    # Anchor the season start at UTC 07:00 (BARS convention — see
    # `refund_calculator.parse_date_mdy`).
    week_anchor = datetime(
        season_start.year,
        season_start.month,
        season_start.day,
        7,
        0,
        0,
        tzinfo=_BARS_TZ,
    )

    if now < week_anchor:
        return 0

    # Each off-date that lands on or before `now`'s position in the
    # schedule effectively pushes the schedule out by 7 days. We sum those
    # shifts and subtract from the elapsed delta.
    sorted_offs = sorted(off_dates or [])
    elapsed = now - week_anchor
    cursor = week_anchor
    extra_days = 0
    for off in sorted_offs:
        # Advance cursor weekly until we land on or pass the off-date or
        # exceed `now`. This mirrors the schedule-shift loop in
        # `WeekSchedule.build`.
        while cursor.date() < off and cursor <= now:
            cursor += timedelta(days=7)
        if cursor.date() == off and cursor <= now:
            extra_days += 7
            cursor += timedelta(days=7)

    weeks = (elapsed.days - extra_days) // 7
    return max(weeks, 0)
