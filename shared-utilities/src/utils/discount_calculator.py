"""
Discount Calculator Utilities
Based on calculate_refund_amount but without penalties - focused on discounts
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def create_discount_amount(
    season_start_date_str: str,
    off_dates_str: Optional[str],
    total_amount_paid: float,
    request_submitted_at: Optional[datetime] = None,
) -> Tuple[float, str]:
    """
    Calculate discount amount based on timing and season dates

    Discount tiers without penalties:
    - Before week 1: No discount (0%)
    - After week 1 starts: 15% discount
    - After week 2 starts: 25% discount
    - After week 3 starts: 35% discount
    - After week 4 starts: 45% discount
    - After week 5 starts: 55% discount

    Args:
        season_start_date_str: Season start date in MM/DD/YY format
        off_dates_str: Comma-separated off dates in MM/DD/YY format
        total_amount_paid: Original amount paid
        request_submitted_at: When the request was submitted (defaults to now)

    Returns:
        Tuple of (discount_amount, description_text)
    """
    try:
        if not season_start_date_str or not total_amount_paid:
            return (
                0,
                "Error calculating discount - please check season dates and amount",
            )

        if total_amount_paid == 0:
            return 0, "Discount Amount: $0 (No payment was made for this order)"

        # Ensure request_submitted_at is timezone-aware
        if request_submitted_at is None:
            request_submitted_at = datetime.now(timezone.utc)
        elif request_submitted_at.tzinfo is None:
            # If naive, assume it's UTC
            request_submitted_at = request_submitted_at.replace(tzinfo=timezone.utc)

        # Parse season start date and make it timezone-aware (UTC)
        month, day, year = map(int, season_start_date_str.split("/"))
        normalized_year = year if year >= 100 else 2000 + year
        season_start_date = datetime(
            normalized_year, month, day, 7, 0, 0, tzinfo=timezone.utc
        )

        # Create week dates (5 weeks starting from season start) - all timezone-aware
        week_dates = [season_start_date]
        for i in range(1, 5):
            next_week_timestamp = week_dates[i - 1].timestamp() + (7 * 24 * 60 * 60)
            next_week = datetime.fromtimestamp(next_week_timestamp, tz=timezone.utc)
            week_dates.append(next_week)

        # Parse off dates and adjust week dates
        if off_dates_str:
            off_dates = []
            for date_str in off_dates_str.split(","):
                date_str = date_str.strip()
                if date_str and "/" in date_str:
                    try:
                        m, d, y = map(int, date_str.split("/"))
                        normalized_year = y if y >= 100 else 2000 + y
                        off_date = datetime(
                            normalized_year, m, d, 7, 0, 0, tzinfo=timezone.utc
                        )
                        off_dates.append(off_date)
                    except ValueError:
                        continue

            # Adjust week dates by shifting subsequent weeks for each off date
            for off_date in sorted(off_dates):
                for i in range(len(week_dates)):
                    if week_dates[i] == off_date:
                        # Shift all subsequent weeks by 7 days
                        for j in range(i, len(week_dates)):
                            shift_timestamp = week_dates[j].timestamp() + (
                                7 * 24 * 60 * 60
                            )
                            week_dates[j] = datetime.fromtimestamp(
                                shift_timestamp, tz=timezone.utc
                            )
                        break

        # Define discount tiers (without penalties)
        # Index 0: Before week 1 (no discount)
        # Index 1: After week 1 starts (15% discount)
        # Index 2: After week 2 starts (25% discount)
        # Index 3: After week 3 starts (35% discount)
        # Index 4: After week 4 starts (45% discount)
        # Index 5: After week 5 starts (55% discount)
        discount_percentages = [0, 15, 25, 35, 45, 55]

        discount_percentage = 0
        week_index = 0

        logger.info(f"Season Start Date (UTC @ 7am): {season_start_date.isoformat()}")
        logger.info(f"Request Submitted At (UTC): {request_submitted_at.isoformat()}")

        # Find appropriate discount tier
        # Check if request is before season starts
        if request_submitted_at < week_dates[0]:
            discount_percentage = discount_percentages[0]  # 0% discount
            week_index = 0
        else:
            # Find which week has started
            for i in range(len(week_dates)):
                week_date = week_dates[i]
                logger.info(
                    f"Checking against week {i+1}: {week_date.isoformat()}. Request after this week started? {request_submitted_at >= week_date}"
                )

                # If this is the last week or request is before the next week
                if i == len(week_dates) - 1 or request_submitted_at < week_dates[i + 1]:
                    if request_submitted_at >= week_date:
                        # Request is after this week started
                        week_index = (
                            i + 1
                        )  # +1 because we want discount after week starts
                        if week_index < len(discount_percentages):
                            discount_percentage = discount_percentages[week_index]
                        else:
                            # After week 5
                            discount_percentage = discount_percentages[-1]  # 55%
                    break

        discount_amount = (discount_percentage / 100) * total_amount_paid

        # Generate timing description
        if week_index == 0:
            timing_description = "before the season started"
        elif week_index == 1:
            timing_description = "after week 1 started"
        elif week_index == 2:
            timing_description = "after week 2 started"
        elif week_index == 3:
            timing_description = "after week 3 started"
        elif week_index == 4:
            timing_description = "after week 4 started"
        else:
            timing_description = "after week 5 started"

        if discount_percentage == 0:
            discount_text = f"*Discount Amount:* $0.00\n(This request was submitted {timing_description}. No discount applied.)"
        else:
            discount_text = f"*Discount Amount:* ${discount_amount:.2f}\n(This request was submitted {timing_description}. {discount_percentage}% discount applied.)"

        return discount_amount, discount_text

    except Exception as e:
        logger.error(f"Error calculating discount amount: {str(e)}")
        return 0, f"Error calculating discount amount: {str(e)}"


def calculate_discounted_price(
    original_price: float,
    season_start_date_str: str,
    off_dates_str: Optional[str] = None,
    request_submitted_at: Optional[datetime] = None,
) -> Tuple[float, float, str]:
    """
    Calculate the final discounted price

    Args:
        original_price: Original price
        season_start_date_str: Season start date in MM/DD/YY format
        off_dates_str: Comma-separated off dates in MM/DD/YY format
        request_submitted_at: When the request was submitted

    Returns:
        Tuple of (final_price, discount_amount, description_text)
    """
    discount_amount, discount_text = create_discount_amount(
        season_start_date_str, off_dates_str, original_price, request_submitted_at
    )

    final_price = original_price - discount_amount

    return final_price, discount_amount, discount_text


def get_discount_percentage_for_week(week_number: int) -> int:
    """
    Get the discount percentage for a specific week

    Args:
        week_number: Week number (0 = before season, 1-5 = weeks 1-5)

    Returns:
        Discount percentage
    """
    discount_map = {
        0: 0,  # Before season starts
        1: 15,  # After week 1 starts
        2: 25,  # After week 2 starts
        3: 35,  # After week 3 starts
        4: 45,  # After week 4 starts
        5: 55,  # After week 5 starts (and beyond)
    }

    return discount_map.get(week_number, 55)  # Default to max discount


def is_discount_eligible(
    season_start_date_str: str,
    request_submitted_at: Optional[datetime] = None,
) -> bool:
    """
    Check if a request is eligible for any discount

    Args:
        season_start_date_str: Season start date in MM/DD/YY format
        request_submitted_at: When the request was submitted

    Returns:
        True if eligible for discount, False otherwise
    """
    try:
        discount_amount, _ = create_discount_amount(
            season_start_date_str,
            None,  # No off dates needed for simple eligibility check
            100,  # Use $100 as test amount
            request_submitted_at,
        )
        return discount_amount > 0
    except Exception:
        return False


def get_next_discount_tier_info(
    season_start_date_str: str,
    off_dates_str: Optional[str] = None,
    current_time: Optional[datetime] = None,
) -> Tuple[Optional[datetime], int]:
    """
    Get information about the next discount tier

    Args:
        season_start_date_str: Season start date in MM/DD/YY format
        off_dates_str: Comma-separated off dates in MM/DD/YY format
        current_time: Current time (defaults to now)

    Returns:
        Tuple of (next_tier_date, next_discount_percentage) or (None, 0) if no more tiers
    """
    try:
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        elif current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        # Parse season start date
        month, day, year = map(int, season_start_date_str.split("/"))
        normalized_year = year if year >= 100 else 2000 + year
        season_start_date = datetime(
            normalized_year, month, day, 7, 0, 0, tzinfo=timezone.utc
        )

        # Create week dates
        week_dates = [season_start_date]
        for i in range(1, 5):
            next_week_timestamp = week_dates[i - 1].timestamp() + (7 * 24 * 60 * 60)
            next_week = datetime.fromtimestamp(next_week_timestamp, tz=timezone.utc)
            week_dates.append(next_week)

        # Adjust for off dates (same logic as create_discount_amount)
        if off_dates_str:
            off_dates = []
            for date_str in off_dates_str.split(","):
                date_str = date_str.strip()
                if date_str and "/" in date_str:
                    try:
                        m, d, y = map(int, date_str.split("/"))
                        normalized_year = y if y >= 100 else 2000 + y
                        off_date = datetime(
                            normalized_year, m, d, 7, 0, 0, tzinfo=timezone.utc
                        )
                        off_dates.append(off_date)
                    except ValueError:
                        continue

            # Adjust week dates
            for off_date in sorted(off_dates):
                for i in range(len(week_dates)):
                    if week_dates[i] == off_date:
                        for j in range(i, len(week_dates)):
                            shift_timestamp = week_dates[j].timestamp() + (
                                7 * 24 * 60 * 60
                            )
                            week_dates[j] = datetime.fromtimestamp(
                                shift_timestamp, tz=timezone.utc
                            )
                        break

        discount_percentages = [0, 15, 25, 35, 45, 55]

        # Find the next tier
        for i, week_date in enumerate(week_dates):
            if current_time < week_date:
                discount_index = i + 1  # Discount applies after week starts
                if discount_index < len(discount_percentages):
                    return week_date, discount_percentages[discount_index]

        return None, 0  # No more tiers

    except Exception as e:
        logger.error(f"Error getting next discount tier info: {str(e)}")
        return None, 0
