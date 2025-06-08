from datetime import datetime, timedelta
import json

def get_discount_dates_and_prices(season_start_date, off_dates_comma_separated, sport_start_time, price):
    print("📍 Entered get_discount_dates_and_prices()")
    print(f"🔎 Inputs:\n- season_start_date: {season_start_date}\n- off_dates_comma_separated: {off_dates_comma_separated}\n- sport_start_time: {sport_start_time}\n- price: {price}")

    try:
        # Convert season start date and time into a datetime object
        month, day, year = map(int, season_start_date.strip().split('/'))
        if year < 100:
            year += 2000
        season_date = datetime(year, month, day)
        print(f"✅ Parsed season start date: {season_date}")
    except Exception as e:
        error_message = f"❌ Failed to parse season_start_date '{season_start_date}': {e}"
        print(error_message)
        raise ValueError(error_message)

    try:
        # Parse the start time into hours and minutes
        sport_start_time_parsed = datetime.strptime(sport_start_time.strip(), "%I:%M %p").time()
        print(f"✅ Parsed sport start time: {sport_start_time_parsed}")
    except Exception as e:
        error_message = f"❌ Failed to parse sport_start_time '{sport_start_time}': {e}"
        print(error_message)
        raise ValueError(error_message)

    season_start = datetime.combine(season_date, sport_start_time_parsed)
    print(f"✅ Combined season start datetime: {season_start}")

    # Generate 4 week-based timestamps
    week_dates = [season_start]
    for i in range(1, 4):
        week_date = week_dates[i - 1] + timedelta(days=7)
        week_dates.append(week_date)
    print(f"📅 Initial week_dates: {[d.isoformat() for d in week_dates]}")

    # Safely parse off dates
    off_dates = []
    if off_dates_comma_separated and off_dates_comma_separated.strip():
        try:
            for date_str in off_dates_comma_separated.split(','):
                date_str = date_str.strip()
                if not date_str:
                    continue
                m, d, y = map(int, date_str.split('/'))
                if y < 100:
                    y += 2000
                off_date = datetime(y, m, d, sport_start_time_parsed.hour, sport_start_time_parsed.minute)
                off_dates.append(off_date)
            print(f"📅 Parsed off dates: {[d.isoformat() for d in off_dates]}")
        except Exception as e:
            error_message = f"❌ Failed to parse offDatesCommaSeparated '{off_dates_comma_separated}': {e}"
            print(error_message)
            raise ValueError(error_message)
    else:
        print("ℹ️ No off dates provided.")

    # Shift weeks if an off-date matches a week
    try:
        for off_date in sorted(off_dates):
            for i in range(len(week_dates)):
                if week_dates[i].date() == off_date.date():
                    print(f"🔄 Matching off-date {off_date.date()} found at week {i+1}, shifting future dates")
                    for j in range(i, len(week_dates)):
                        week_dates[j] += timedelta(days=7)
                    break
    except Exception as e:
        error_message = f"❌ Failed while adjusting for off dates: {e}"
        print(error_message)
        raise ValueError(error_message)

    # Define discount tiers
    discount_percents = [0.85, 0.75, 0.65, 0.55]

    discount_schedule = []
    try:
        for i in range(4):
            discount_price = round(price * discount_percents[i], 2)
            discount_schedule.append({
                "timestamp": week_dates[i].isoformat(),
                "updated_price": discount_price
            })
        print(f"📈 Final discount schedule: {json.dumps(discount_schedule, indent=2)}")
    except Exception as e:
        error_message = f"❌ Failed to build discount schedule: {e}"
        print(error_message)
        raise ValueError(error_message)

    print("✅ Exiting get_discount_dates_and_prices() successfully")
    return discount_schedule