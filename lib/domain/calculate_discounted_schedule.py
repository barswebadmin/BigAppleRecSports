"""Calculate a schedule of discounted prices across season weeks."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional


def calculate_discounted_schedule(
    season_start_date: datetime,
    off_dates: List[datetime],
    base_price: float,
    discount_tiers: Optional[List[float]] = None,
) -> List[Dict]:
    """
    Calculate a schedule of discounted prices with dates.

    Skips off-date weeks by shifting subsequent weeks forward by 7 days.
    """
    if discount_tiers is None:
        discount_tiers = [0.85, 0.75, 0.65, 0.55]

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
