"""Discount schedule and amount calculations."""

from datetime import datetime, time, timedelta

DEFAULT_DISCOUNT_TIERS: list[float] = [0.85, 0.75, 0.65, 0.55]


def _parse_date(date_str: str, default_century: int = 2000) -> datetime:
    """Parse MM/DD/YY or MM/DD/YYYY."""
    try:
        month, day, year = map(int, date_str.strip().split("/"))
        if year < 100:
            year += default_century
        return datetime(year, month, day)
    except Exception as exc:
        raise ValueError(
            f"Invalid date format. Expected MM/DD/YY or MM/DD/YYYY, got: {date_str}"
        ) from exc


def _parse_time(time_str: str) -> time:
    """Parse HH:MM AM/PM."""
    try:
        return datetime.strptime(time_str.strip(), "%I:%M %p").time()
    except Exception as exc:
        raise ValueError(
            f"Invalid time format. Expected HH:MM AM/PM, got: {time_str}"
        ) from exc


def _parse_off_dates(dates_str: str | None, sport_time: time) -> list[datetime]:
    """Parse comma-separated off dates (YYYY-MM-DD or MM/DD/YY) with sport time."""
    off_dates: list[datetime] = []
    if not dates_str or not dates_str.strip():
        return off_dates
    for date_str in dates_str.split(","):
        date_str = date_str.strip()
        if not date_str:
            continue
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            parsed_date = _parse_date(date_str).date()
        off_dates.append(datetime.combine(parsed_date, sport_time))
    return off_dates


def calculate_discount_amount(
    discount_type: str,
    discount_value: float,
    unit_price: float,
) -> float:
    """Return the discount amount for a line item.

    For ``discount_type == "fixed"``, ``discount_value`` is the dollar amount.
    Otherwise ``discount_value`` is a percentage of ``unit_price``.
    """
    if discount_type == "fixed":
        return discount_value
    return (discount_value / 100.0) * unit_price


def calculate_discounted_schedule(
    season_start_date: datetime,
    off_dates: list[datetime],
    base_price: float,
    discount_tiers: list[float] | None = None,
) -> list[dict]:
    """Build a schedule of discounted prices across season weeks.

    Skips off-date weeks by shifting subsequent weeks forward by 7 days.
    Default tiers: 85%, 75%, 65%, 55% of ``base_price``.
    """
    if discount_tiers is None:
        discount_tiers = list(DEFAULT_DISCOUNT_TIERS)

    week_dates = [season_start_date]
    for i in range(1, len(discount_tiers)):
        week_dates.append(week_dates[i - 1] + timedelta(days=7))

    for off_date in sorted(off_dates):
        for i, week_date in enumerate(week_dates):
            if week_date.date() == off_date.date():
                for j in range(i, len(week_dates)):
                    week_dates[j] += timedelta(days=7)
                break

    return [
        {"timestamp": date.isoformat(), "updated_price": round(base_price * multiplier, 2)}
        for date, multiplier in zip(week_dates, discount_tiers)
    ]


def get_discount_dates_and_prices(
    season_start_date: str,
    off_dates_comma_separated: str | None,
    sport_start_time: str,
    price: float,
) -> list[dict]:
    """Calculate a schedule of discounted prices based on season dates."""
    try:
        try:
            season_date = datetime.strptime(season_start_date, "%Y-%m-%d").date()
        except ValueError:
            season_date = _parse_date(season_start_date).date()

        sport_start_time_parsed = _parse_time(sport_start_time)
        season_start = datetime.combine(season_date, sport_start_time_parsed)
        off_dates = _parse_off_dates(off_dates_comma_separated, sport_start_time_parsed)

        return calculate_discounted_schedule(
            season_start_date=season_start,
            off_dates=off_dates,
            base_price=price,
        )
    except ValueError as e:
        raise ValueError(str(e)) from e
    except Exception as e:
        raise ValueError(f"Unexpected error: {e}") from e
