from datetime import datetime
from bars_common_utils.date_utils import parse_date, parse_time, parse_off_dates, calculate_discounted_schedule, parse_iso_datetime

def get_discount_dates_and_prices(season_start_date, off_dates_comma_separated, sport_start_time, price):
    """
    Calculate a schedule of discounted prices based on season dates
    """
    print("📍 Entered get_discount_dates_and_prices()")
    print(f"🔎 Inputs:\n- season_start_date: {season_start_date}\n- off_dates_comma_separated: {off_dates_comma_separated}\n- sport_start_time: {sport_start_time}\n- price: {price}")

    try:
        # Parse season start date - handle both YYYY-MM-DD and MM/DD/YY formats
        try:
            # Try YYYY-MM-DD format first (what backend sends)
            season_date = datetime.strptime(season_start_date, "%Y-%m-%d").date()
            print(f"✅ Parsed season start date (YYYY-MM-DD): {season_date}")
        except ValueError:
            # Fallback to MM/DD/YY format
            season_date = parse_date(season_start_date)
            print(f"✅ Parsed season start date (MM/DD/YY): {season_date}")

        # Parse sport start time
        sport_start_time_parsed = parse_time(sport_start_time)
        print(f"✅ Parsed sport start time: {sport_start_time_parsed}")

        # Combine date and time
        season_start_date = datetime.combine(season_date, sport_start_time_parsed)
        print(f"✅ Combined season start datetime: {season_start_date}")

        # Parse off dates
        off_dates = parse_off_dates(off_dates_comma_separated, sport_start_time_parsed)
        if off_dates:
            print(f"📅 Parsed off dates: {[d.isoformat() for d in off_dates]}")
        else:
            print("ℹ️ No off dates provided.")

        # Calculate discount schedule
        discount_schedule = calculate_discounted_schedule(
            season_start_date=season_start_date,
            off_dates=off_dates,
            base_price=price
        )
        print(f"📈 Final discount schedule: {discount_schedule}")

        print("✅ Exiting get_discount_dates_and_prices() successfully")
        return discount_schedule

    except ValueError as e:
        error_message = f"❌ {str(e)}"
        print(error_message)
        raise ValueError(error_message)
    except Exception as e:
        error_message = f"❌ Unexpected error: {str(e)}"
        print(error_message)
        raise ValueError(error_message)