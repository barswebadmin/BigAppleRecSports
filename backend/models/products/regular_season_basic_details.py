"""
Regular Season Basic Details model for product creation
"""

from pydantic import BaseModel, field_validator
from typing import List, Optional, Union
from enum import Enum


class Season(str, Enum):
    SPRING = "Spring"
    SUMMER = "Summer"
    FALL = "Fall"
    WINTER = "Winter"


class DayOfPlay(str, Enum):
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"


class Division(str, Enum):
    OPEN = "Open"
    WTNB_PLUS = "WTNB+"


class SportSubCategory(str, Enum):
    BIG_BALL = "Big Ball"
    SMALL_BALL = "Small Ball"
    FOAM = "Foam"


class SocialOrAdvanced(str, Enum):
    SOCIAL = "Social"
    ADVANCED = "Advanced"
    MIXED_SOCIAL_ADVANCED = "Mixed Social/Advanced"
    COMPETITIVE_ADVANCED = "Competitive/Advanced"
    INTERMEDIATE_ADVANCED = "Intermediate/Advanced"


class LeagueAssignmentTypes(str, Enum):
    DRAFT = "Draft"
    RANDOMIZED_TEAMS = "Randomized Teams"
    BUDDY_SIGNUP = "Buddy Sign-up"
    NEWBIE_SIGNUP = "Sign up with a newbie (randomized otherwise)"


# Valid locations by sport
VALID_LOCATIONS = {
    "Dodgeball": [
        "Elliott Center (26th St & 9th Ave)",
        "PS3 Charrette School (Grove St & Hudson St)",
        "Village Community School (10th St & Greenwich St)",
        "Hartley House (46th St & 9th Ave)",
        "Dewitt Clinton Park (52nd St & 11th Ave)",
    ],
    "Kickball": [
        "Gansevoort Peninsula Athletic Park, Pier 53 (Gansevoort St & 11th)",
        "Chelsea Park (27th St & 9th Ave)",
        "Dewitt Clinton Park (52nd St & 11th Ave)",
    ],
    "Pickleball": [
        "Gotham Pickleball (46th and Vernon in LIC)",
        "Pickle1 (7 Hanover Square in LIC)",
    ],
    "Bowling": [
        "Frames Bowling Lounge (40th St and 9th Ave)",
        "Bowlero Chelsea Piers (60 Chelsea Piers)",
    ],
}


class RegularSeasonBasicDetails(BaseModel):
    """Basic details for regular season leagues"""

    model_config = {"str_strip_whitespace": True}

    # Basic league information
    year: Union[str, int]
    season: Season
    dayOfPlay: DayOfPlay
    division: Division
    location: str

    # League assignment and categorization
    leagueAssignmentTypes: Optional[List[LeagueAssignmentTypes]] = None
    sportSubCategory: Optional[SportSubCategory] = None
    socialOrAdvanced: Optional[SocialOrAdvanced] = None

    # League timing
    leagueStartTime: str
    leagueEndTime: str

    @field_validator("year")
    @classmethod
    def validate_year(cls, v):
        """Validate year is between 2024 and 2030"""
        if isinstance(v, str):
            try:
                year_int = int(v)
            except ValueError:
                raise ValueError("Year must be a valid integer")
        else:
            year_int = v

        if year_int < 2024 or year_int > 2030:
            raise ValueError("Year must be between 2024 and 2030")
        return year_int
