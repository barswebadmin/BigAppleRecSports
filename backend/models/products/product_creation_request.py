from pydantic import (
    BaseModel,
    field_validator,
    model_validator,
    ConfigDict,
    ValidationError,
)
from typing import List, Optional, Union
from datetime import datetime
from enum import Enum


class ProductCreationRequestValidationError(Exception):
    """Custom exception for product creation request validation errors"""

    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Product creation validation failed: {', '.join(errors)}")

    def get_errors(self) -> List[str]:
        """Return list of validation error messages"""
        return self.errors


class SportName(str, Enum):
    KICKBALL = "Kickball"
    BOWLING = "Bowling"
    PICKLEBALL = "Pickleball"
    DODGEBALL = "Dodgeball"


class Division(str, Enum):
    OPEN = "Open"
    WTNB_PLUS = "WTNB+"


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


class SportSubCategory(str, Enum):
    BIG_BALL = "Big Ball"
    SMALL_BALL = "Small Ball"
    FOAM = "Foam"


class SocialOrAdvanced(str, Enum):
    SOCIAL = "Social"
    ADVANCED = "Advanced"
    MIXED = "Mixed Social/Advanced"
    COMPETITIVE_ADVANCED = "Competitive/Advanced"
    INTERMEDIATE_ADVANCED = "Intermediate/Advanced"


class LeagueTypes(str, Enum):
    DRAFT = "Draft"
    RANDOMIZED_TEAMS = "Randomized Teams"
    BUDDY_SIGNUP = "Buddy Sign-up"
    NEWBIE_SIGNUP = "Sign up with a newbie (randomized otherwise)"


# Sport-specific valid locations
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


class OptionalLeagueInfo(BaseModel):
    socialOrAdvanced: Optional[SocialOrAdvanced] = None
    sportSubCategory: Optional[SportSubCategory] = None
    types: Optional[List[LeagueTypes]] = None


class ImportantDates(BaseModel):
    seasonStartDate: Union[str, datetime]
    seasonEndDate: Union[str, datetime]
    offDates: Optional[List[Union[str, datetime]]] = None
    newPlayerOrientationDateTime: Optional[Union[str, datetime]] = None
    scoutNightDateTime: Optional[Union[str, datetime]] = None
    openingPartyDate: Optional[Union[str, datetime]] = None
    rainDate: Optional[Union[str, datetime]] = None
    closingPartyDate: Optional[Union[str, datetime]] = None
    vetRegistrationStartDateTime: Union[str, datetime]
    earlyRegistrationStartDateTime: Union[str, datetime]
    openRegistrationStartDateTime: Union[str, datetime]


class InventoryInfo(BaseModel):
    price: Union[int, float]
    totalInventory: int
    numberVetSpotsToReleaseAtGoLive: Optional[int] = None

    @field_validator("price", mode="before")
    @classmethod
    def validate_price(cls, v):
        if isinstance(v, str):
            try:
                price_val = float(v)
            except ValueError:
                raise ValueError("Price must be a valid number")
        else:
            price_val = v

        if price_val <= 0:
            raise ValueError("Price must be greater than 0")
        return price_val

    @field_validator("totalInventory", mode="before")
    @classmethod
    def validate_inventory(cls, v):
        if isinstance(v, str):
            try:
                inventory_int = int(v)
            except ValueError:
                raise ValueError("Total inventory must be a valid integer")
        else:
            inventory_int = v

        if inventory_int <= 0:
            raise ValueError("Total inventory must be greater than 0")
        return inventory_int


class ProductCreationRequest(BaseModel):
    sportName: SportName
    division: Division
    season: Season
    year: Union[str, int]
    dayOfPlay: DayOfPlay
    location: str
    leagueStartTime: str
    leagueEndTime: str
    alternativeStartTime: Optional[str] = None
    alternativeEndTime: Optional[str] = None
    optionalLeagueInfo: OptionalLeagueInfo
    importantDates: ImportantDates
    inventoryInfo: InventoryInfo

    model_config = ConfigDict(use_enum_values=True)

    @field_validator("year", mode="before")
    @classmethod
    def validate_year(cls, v):
        if isinstance(v, str):
            try:
                year_int = int(v)
            except ValueError:
                raise ValueError("Year must be a valid integer")
        else:
            year_int = v

        if year_int < 2024 or year_int > 2030:
            raise ValueError("Year must be between 2024 and 2030")
        return str(year_int)

    @field_validator("location")
    @classmethod
    def validate_location_for_sport(cls, v, info):
        """Validate location is valid for the sport"""
        # Note: This will be validated at model level where we have access to sportName
        return v

    @model_validator(mode="after")
    def validate_sport_specific_requirements(self):
        """Validate sport-specific required fields and location constraints"""
        sport_name = self.sportName
        location = self.location
        optional_info = self.optionalLeagueInfo

        # Validate location is valid for the sport
        valid_locations = VALID_LOCATIONS.get(sport_name, [])
        if location not in valid_locations:
            raise ValueError(
                f"Location '{location}' is not valid for {sport_name}. Valid locations: {', '.join(valid_locations)}"
            )

        # Sport-specific required field validation
        if sport_name in ["Dodgeball", "Kickball"]:
            if optional_info.socialOrAdvanced is None:
                raise ValueError(
                    f"socialOrAdvanced is required for {sport_name} (Social, Advanced, or Mixed Social/Advanced)"
                )

        if sport_name == "Dodgeball":
            if optional_info.sportSubCategory is None:
                raise ValueError(
                    "sportSubCategory is required for Dodgeball (Big Ball, Small Ball, or Foam)"
                )

        return self

    @classmethod
    def validate_request_data(cls, data: dict) -> "ProductCreationRequest":
        """
        Validate product creation request data and return all validation errors

        Args:
            data: Raw product data dictionary

        Returns:
            ProductCreationRequest instance if valid

        Raises:
            ProductCreationRequestValidationError: If validation fails with all error details
        """
        try:
            return cls(**data)
        except ValidationError as e:
            # Extract all error messages from Pydantic
            errors = []
            for error in e.errors():
                # Build field path
                field_path = ".".join(str(loc) for loc in error["loc"])

                # Get error message
                msg = error["msg"]

                # Format the error message
                if field_path:
                    errors.append(f"{field_path}: {msg}")
                else:
                    errors.append(msg)

            raise ProductCreationRequestValidationError(errors)
