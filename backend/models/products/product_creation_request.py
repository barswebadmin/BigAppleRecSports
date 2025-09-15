from pydantic import (
    BaseModel,
    model_validator,
    ConfigDict,
    ValidationError,
)
from enum import Enum
from .regular_season_basic_details import RegularSeasonBasicDetails
from .product_creation_request_validation_error import (
    ProductCreationRequestValidationError,
)
from .inventory_info import InventoryInfo
from .important_dates import ImportantDates
from .optional_league_info import OptionalLeagueInfo


class SportName(str, Enum):
    KICKBALL = "Kickball"
    BOWLING = "Bowling"
    PICKLEBALL = "Pickleball"
    DODGEBALL = "Dodgeball"


class ProductCreationRequest(BaseModel):
    sportName: SportName
    regularSeasonBasicDetails: RegularSeasonBasicDetails
    optionalLeagueInfo: OptionalLeagueInfo
    importantDates: ImportantDates
    inventoryInfo: InventoryInfo

    model_config = ConfigDict(use_enum_values=True)

    @model_validator(mode="after")
    def validate_sport_specific_requirements(self):
        """Validate sport-specific required fields and location constraints"""
        # Delegate validation to the RegularSeasonBasicDetails method
        self.regularSeasonBasicDetails.validate_sport_specific_requirements(
            sport_name=self.sportName, optional_info=self.optionalLeagueInfo
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
            raise ProductCreationRequestValidationError(
                [dict(error) for error in e.errors()]
            )
