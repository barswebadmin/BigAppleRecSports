from pydantic import BaseModel, field_validator, ConfigDict
from typing import List, Optional, Union
from datetime import datetime
from enum import Enum


class SportName(str, Enum):
    KICKBALL = "Kickball"
    BOWLING = "Bowling"
    PICKLEBALL = "Pickleball"
    DODGEBALL = "Dodgeball"


class Division(str, Enum):
    OPEN = "Open"
    WTNB_PLUS = "WTNB+"
    SOCIAL = "Social"
    ADVANCED = "Advanced"


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


class OptionalLeagueInfo(BaseModel):
    socialOrAdvanced: Optional[str] = None
    sportSubCategory: Optional[str] = None
    types: Optional[List[str]] = None


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


class CreateProductRequest(BaseModel):
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
