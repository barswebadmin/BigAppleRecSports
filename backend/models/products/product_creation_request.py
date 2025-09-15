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
from .regular_season_basic_details import (
    RegularSeasonBasicDetails,
    VALID_LOCATIONS,
    SportSubCategory,
    SocialOrAdvanced,
    LeagueAssignmentTypes,
)
from .product_creation_request_validation_error import (
    ProductCreationRequestValidationError,
)


class SportName(str, Enum):
    KICKBALL = "Kickball"
    BOWLING = "Bowling"
    PICKLEBALL = "Pickleball"
    DODGEBALL = "Dodgeball"


class OptionalLeagueInfo(BaseModel):
    socialOrAdvanced: Optional[SocialOrAdvanced] = None
    sportSubCategory: Optional[SportSubCategory] = None
    types: Optional[List[LeagueAssignmentTypes]] = None


class ImportantDates(BaseModel):
    seasonStartDate: Union[str, datetime]
    seasonEndDate: Union[str, datetime]
    vetRegistrationStartDateTime: Union[str, datetime]
    earlyRegistrationStartDateTime: Union[str, datetime]
    openRegistrationStartDateTime: Union[str, datetime]
    offDates: Optional[List[Union[str, datetime]]] = None
    newPlayerOrientationDateTime: Optional[Union[str, datetime]] = None
    scoutNightDateTime: Optional[Union[str, datetime]] = None
    openingPartyDate: Optional[Union[str, datetime]] = None
    rainDate: Optional[Union[str, datetime]] = None
    closingPartyDate: Optional[Union[str, datetime]] = None


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
    regularSeasonBasicDetails: RegularSeasonBasicDetails
    alternativeStartTime: Optional[str] = None
    alternativeEndTime: Optional[str] = None
    optionalLeagueInfo: OptionalLeagueInfo
    importantDates: ImportantDates
    inventoryInfo: InventoryInfo

    model_config = ConfigDict(use_enum_values=True)

    @model_validator(mode="after")
    def validate_sport_specific_requirements(self):
        """Validate sport-specific required fields and location constraints"""
        sport_name = self.sportName
        location = self.regularSeasonBasicDetails.location

        # Access sport-specific fields from regularSeasonBasicDetails or optionalLeagueInfo
        social_or_advanced = (
            self.regularSeasonBasicDetails.socialOrAdvanced
            or self.optionalLeagueInfo.socialOrAdvanced
        )
        sport_sub_category = (
            self.regularSeasonBasicDetails.sportSubCategory
            or self.optionalLeagueInfo.sportSubCategory
        )

        # Validate location is valid for the sport
        valid_locations = VALID_LOCATIONS.get(sport_name, [])
        if location not in valid_locations:
            raise ValueError(
                f"Location '{location}' is not valid for {sport_name}. Valid locations: {', '.join(valid_locations)}"
            )

        # Sport-specific required field validation
        if sport_name in ["Dodgeball", "Kickball"]:
            if social_or_advanced is None:
                raise ValueError(
                    f"socialOrAdvanced is required for {sport_name} (Social, Advanced, or Mixed Social/Advanced)"
                )

        if sport_name == "Dodgeball":
            if sport_sub_category is None:
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
            # Convert to our custom error class while preserving all error details
            raise ProductCreationRequestValidationError(e.errors())
