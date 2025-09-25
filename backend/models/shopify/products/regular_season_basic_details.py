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
VALID_SPORT_LOCATIONS = {
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
    alternativeStartTime: Optional[str] = None
    alternativeEndTime: Optional[str] = None

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

    @field_validator(
        "sportSubCategory",
        "socialOrAdvanced",
        "alternativeStartTime",
        "alternativeEndTime",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, v):
        """Convert empty strings to None for optional fields"""
        if v == "":
            return None
        return v

    def validate_sport_specific_requirements(self, sport_name: str, optional_info=None):
        """
        Validate sport-specific required fields and location constraints

        Args:
            sport_name: The sport name for validation
            optional_info: Optional league info object for additional field sources
        """
        location = self.location

        # Access sport-specific fields from self or optional_info
        social_or_advanced = self.socialOrAdvanced
        sport_sub_category = self.sportSubCategory

        if optional_info:
            social_or_advanced = social_or_advanced or optional_info.socialOrAdvanced
            sport_sub_category = sport_sub_category or optional_info.sportSubCategory

        # Validate location is valid for the sport
        valid_locations = VALID_SPORT_LOCATIONS.get(sport_name, [])
        if location not in valid_locations:
            raise ValueError(
                f"Location '{location}' is not valid for {sport_name}. Valid locations: {', '.join(valid_locations)}"
            )

        # Sport-specific required field validation
        if sport_name in ["Dodgeball", "Kickball", "Pickleball"]:
            if social_or_advanced is None:
                raise ValueError(
                    f"socialOrAdvanced is required for {sport_name} (Social, Advanced, or Mixed Social/Advanced)"
                )

        if sport_name == "Dodgeball":
            if sport_sub_category is None:
                raise ValueError(
                    "sportSubCategory is required for Dodgeball (Big Ball, Small Ball, or Foam)"
                )
