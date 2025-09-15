"""
Products Service for validating and processing product creation requests
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
import dateutil.parser
from models.products.create_product_request import CreateProductRequest
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class ProductsService:
    """Service for handling product creation and validation"""

    # Required fields that must be present and non-empty
    REQUIRED_FIELDS = [
        "sportName",
        "dayOfPlay",
        "division",
        "season",
        "year",
        "location",
        "leagueStartTime",
        "leagueEndTime",
    ]

    # Required nested fields
    REQUIRED_NESTED_FIELDS = {
        "importantDates": [
            "seasonStartDate",
            "seasonEndDate",
            "vetRegistrationStartDateTime",
            "earlyRegistrationStartDateTime",
            "openRegistrationStartDateTime",
        ],
        "inventoryInfo": ["price", "totalInventory"],
        "optionalLeagueInfo": [],  # This object must exist but fields are optional
    }

    @classmethod
    def is_valid_product_request_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate product request data structure and types

        Args:
            data: Raw product data dictionary from request

        Returns:
            Dict with 'valid' boolean and 'errors' list
        """
        errors = []

        try:
            # Check for missing top-level required fields
            missing_fields = []
            for field in cls.REQUIRED_FIELDS:
                if field not in data or data[field] is None or data[field] == "":
                    missing_fields.append(field)

            if missing_fields:
                errors.append(f"Missing required fields: {', '.join(missing_fields)}")

            # Check for missing nested objects and their required fields
            for (
                nested_obj,
                required_nested_fields,
            ) in cls.REQUIRED_NESTED_FIELDS.items():
                if nested_obj not in data or data[nested_obj] is None:
                    errors.append(f"Missing required nested object: {nested_obj}")
                    continue

                nested_data = data[nested_obj]
                if not isinstance(nested_data, dict):
                    errors.append(f"{nested_obj} must be an object")
                    continue

                # Check required fields within nested object
                missing_nested = []
                for nested_field in required_nested_fields:
                    if (
                        nested_field not in nested_data
                        or nested_data[nested_field] is None
                        or nested_data[nested_field] == ""
                    ):
                        missing_nested.append(f"{nested_obj}.{nested_field}")

                if missing_nested:
                    errors.append(
                        f"Missing required nested fields: {', '.join(missing_nested)}"
                    )

            # Validate specific field types and values
            type_errors = cls._validate_field_types(data)
            errors.extend(type_errors)

            # Validate enum values
            enum_errors = cls._validate_enum_values(data)
            errors.extend(enum_errors)

            # Validate date formats
            date_errors = cls._validate_date_fields(data)
            errors.extend(date_errors)

            # Try to create Pydantic model for full validation
            try:
                CreateProductRequest(**data)
            except ValidationError as e:
                pydantic_errors = []
                for error in e.errors():
                    field_path = ".".join(str(loc) for loc in error["loc"])
                    pydantic_errors.append(f"{field_path}: {error['msg']}")
                errors.extend(pydantic_errors)

        except Exception as e:
            logger.error(f"Unexpected error during validation: {e}")
            errors.append(f"Validation error: {str(e)}")

        return {"valid": len(errors) == 0, "errors": errors}

    @classmethod
    def _validate_field_types(cls, data: Dict[str, Any]) -> List[str]:
        """Validate field types match expected types"""
        errors = []

        # String fields
        string_fields = [
            "sportName",
            "dayOfPlay",
            "division",
            "season",
            "location",
            "leagueStartTime",
            "leagueEndTime",
        ]
        for field in string_fields:
            if field in data and data[field] is not None:
                if not isinstance(data[field], str):
                    errors.append(f"{field} must be a string")

        # Year validation (string or int, convertible to int)
        if "year" in data and data["year"] is not None:
            try:
                year_val = int(data["year"])
                if year_val < 2024 or year_val > 2030:
                    errors.append("Year must be between 2024 and 2030")
            except (ValueError, TypeError):
                errors.append("Year must be a valid integer")

        # Price validation
        if "inventoryInfo" in data and isinstance(data["inventoryInfo"], dict):
            if "price" in data["inventoryInfo"]:
                try:
                    price_val = float(data["inventoryInfo"]["price"])
                    if price_val <= 0:
                        errors.append("Price must be greater than 0")
                except (ValueError, TypeError):
                    errors.append("Price must be a valid number")

        # Total inventory validation
        if "inventoryInfo" in data and isinstance(data["inventoryInfo"], dict):
            if "totalInventory" in data["inventoryInfo"]:
                try:
                    inventory_val = int(data["inventoryInfo"]["totalInventory"])
                    if inventory_val <= 0:
                        errors.append("Total inventory must be greater than 0")
                except (ValueError, TypeError):
                    errors.append("Total inventory must be a valid integer")

        return errors

    @classmethod
    def _validate_enum_values(cls, data: Dict[str, Any]) -> List[str]:
        """Validate enum field values"""
        errors = []

        # Valid enum values (should match GAS project validation)
        valid_sports = ["Kickball", "Bowling", "Pickleball", "Dodgeball"]
        valid_divisions = ["Open", "WTNB+", "Social", "Advanced"]
        valid_seasons = ["Spring", "Summer", "Fall", "Winter"]
        valid_days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        # Validate sportName
        if "sportName" in data and data["sportName"] not in valid_sports:
            errors.append(f"Invalid sportName: must be one of {valid_sports}")

        # Validate division
        if "division" in data and data["division"] not in valid_divisions:
            errors.append(f"Invalid division: must be one of {valid_divisions}")

        # Validate season
        if "season" in data and data["season"] not in valid_seasons:
            errors.append(f"Invalid season: must be one of {valid_seasons}")

        # Validate dayOfPlay
        if "dayOfPlay" in data and data["dayOfPlay"] not in valid_days:
            errors.append(f"Invalid dayOfPlay: must be one of {valid_days}")

        return errors

    @classmethod
    def _validate_date_fields(cls, data: Dict[str, Any]) -> List[str]:
        """Validate date fields can be parsed"""
        errors = []

        if "importantDates" not in data or not isinstance(data["importantDates"], dict):
            return errors

        date_fields = [
            "seasonStartDate",
            "seasonEndDate",
            "vetRegistrationStartDateTime",
            "earlyRegistrationStartDateTime",
            "openRegistrationStartDateTime",
            "newPlayerOrientationDateTime",
            "scoutNightDateTime",
            "openingPartyDate",
            "rainDate",
            "closingPartyDate",
        ]

        for field in date_fields:
            if field in data["importantDates"]:
                value = data["importantDates"][field]
                if value is not None and value != "TBD":
                    try:
                        if isinstance(value, str):
                            dateutil.parser.parse(value)
                        elif not isinstance(value, datetime):
                            errors.append(
                                f"{field} must be a valid date string or datetime object"
                            )
                    except (ValueError, TypeError):
                        errors.append(f"{field} must be a valid date format")

        # Validate offDates array
        if "offDates" in data["importantDates"]:
            off_dates = data["importantDates"]["offDates"]
            if off_dates is not None:
                if not isinstance(off_dates, list):
                    errors.append("offDates must be an array")
                else:
                    for i, date_val in enumerate(off_dates):
                        if date_val is not None:
                            try:
                                if isinstance(date_val, str):
                                    dateutil.parser.parse(date_val)
                                elif not isinstance(date_val, datetime):
                                    errors.append(
                                        f"offDates[{i}] must be a valid date string or datetime object"
                                    )
                            except (ValueError, TypeError):
                                errors.append(
                                    f"offDates[{i}] must be a valid date format"
                                )

        return errors
