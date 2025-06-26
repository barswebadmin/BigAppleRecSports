from datetime import datetime
from typing import Tuple

def get_season_start_and_end(season: str, year: int) -> Tuple[str, str]:
    """
    Get start and end dates for a given season and year
    Returns dates in ISO format: YYYY-MM-DDTHH:MM:SSZ
    """
    seasons = {
        "Winter": {
            "start_month": 12, "start_day": 1, "start_year_offset": -1,  # Dec 1 (prev year)
            "end_month": 2, "end_day": 1, "end_year_offset": 0           # Feb 1 (current year)
        },
        "Spring": {
            "start_month": 3, "start_day": 1, "start_year_offset": 0,    # Mar 1
            "end_month": 5, "end_day": 31, "end_year_offset": 0          # May 31
        },
        "Summer": {
            "start_month": 5, "start_day": 15, "start_year_offset": 0,   # May 15
            "end_month": 7, "end_day": 31, "end_year_offset": 0          # Jul 31
        },
        "Fall": {
            "start_month": 8, "start_day": 15, "start_year_offset": 0,   # Aug 15
            "end_month": 10, "end_day": 1, "end_year_offset": 0          # Oct 1
        }
    }
    
    if season not in seasons:
        raise ValueError(f"Invalid season: {season}. Must be one of: {list(seasons.keys())}")
    
    season_info = seasons[season]
    
    # Calculate start date
    start_year = year + season_info["start_year_offset"]
    start_date = datetime(
        start_year,
        season_info["start_month"],
        season_info["start_day"]
    ).strftime("%Y-%m-%dT00:00:00Z")
    
    # Calculate end date
    end_year = year + season_info["end_year_offset"]
    end_date = datetime(
        end_year,
        season_info["end_month"],
        season_info["end_day"]
    ).strftime("%Y-%m-%dT00:00:00Z")
    
    return start_date, end_date 