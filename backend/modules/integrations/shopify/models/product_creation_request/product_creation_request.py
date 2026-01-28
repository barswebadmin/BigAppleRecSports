from pydantic import (
    BaseModel,
    model_validator,
    ConfigDict,
    ValidationError,
)
from enum import Enum
from typing import List, Optional, Union

from .regular_season_basic_details import RegularSeasonBasicDetails
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
    tags: Optional[List[str]] = None

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

class ProductCreationRequestValidationError(Exception):
    """Custom exception for product creation request validation errors

    Uses Pydantic's ValidationError structure while extending Exception for simplicity.
    Provides field_name attribute and maintains full error details.
    """

    def __init__(self, errors: list[dict]):
        """
        Initialize with standard Pydantic error format

        Args:
            errors: list of pydantic error dictionaries
        """
        self._errors = errors

        # Add field_name attribute for the first error (primary error)
        if errors:
            first_error = errors[0]
            self.field_name = ".".join(str(loc) for loc in first_error.get("loc", []))
        else:
            self.field_name = "unknown"

        # Create error message for exception
        error_messages: list[str] = self.get_errors(formatted=True)  # type: ignore
        message = f"Product validation failed: {', '.join(error_messages)}"
        super().__init__(message)

    def get_errors(self, formatted: bool = True) -> Union[list[str], list[dict]]:
        """
        Get validation errors - either formatted messages or raw Pydantic error dictionaries

        Args:
            formatted: If True, return formatted "field_name: message" strings.
                      If False, return raw Pydantic error dictionaries.

        Returns:
            list of formatted error messages or raw error dictionaries
        """
        if formatted:
            return [
                f"{'.'.join(str(loc) for loc in error.get('loc', []))}: {error.get('msg', 'Validation failed')}"
                for error in self._errors
            ]
        else:
            return self._errors