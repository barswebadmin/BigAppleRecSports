"""
Custom validation error class for product creation requests
"""

from typing import List
from enum import Enum


class InvalidationReason(str, Enum):
    """Enum for validation failure reasons based on Pydantic error types"""

    MISSING = "Missing"
    INVALID_DATA_TYPE = "InvalidDataType"
    INVALID_VALUE = "InvalidValue"


class ProductCreationRequestValidationError(Exception):
    """Custom exception for product creation request validation errors

    Provides structured error information with field names and invalidation reasons.
    """

    def __init__(self, errors: List[dict]):
        """
        Initialize with standard Pydantic error format

        Args:
            errors: List of pydantic error dictionaries
        """
        self._errors = errors

        # Add custom attributes for the first error (primary error)
        if errors:
            first_error = errors[0]
            self.field_name = ".".join(str(loc) for loc in first_error.get("loc", []))
            self.invalidation_reason = self._determine_invalidation_reason(first_error)
        else:
            self.field_name = "unknown"
            self.invalidation_reason = InvalidationReason.INVALID_VALUE

        # Create error message for exception
        error_messages = self.get_errors()
        message = f"Product validation failed: {', '.join(error_messages)}"
        super().__init__(message)

    def _determine_invalidation_reason(self, error: dict) -> InvalidationReason:
        """
        Determine invalidation reason from Pydantic error type

        Args:
            error: Pydantic error dictionary

        Returns:
            InvalidationReason enum value
        """
        error_type = error.get("type", "")
        error_msg = error.get("msg", "").lower()

        # Missing/required field errors
        if "missing" in error_type or "required" in error_msg:
            return InvalidationReason.MISSING

        # Data type errors
        if any(
            x in error_type
            for x in [
                "type",
                "_type",
                "int_",
                "str_",
                "float_",
                "bool_",
                "list_",
                "dict_",
            ]
        ):
            return InvalidationReason.INVALID_DATA_TYPE

        # Everything else is invalid value
        return InvalidationReason.INVALID_VALUE

    def get_error_details(self) -> List[dict]:
        """
        Get detailed error information for all validation errors

        Returns:
            List of dictionaries with field name, reason, and message for each error
        """
        details = []

        for error in self._errors:
            field_name = ".".join(str(loc) for loc in error.get("loc", []))
            reason = self._determine_invalidation_reason(error)

            details.append(
                {
                    "field_name": field_name,
                    "invalidation_reason": reason.value,
                    "message": error.get("msg", "Validation failed"),
                }
            )

        return details

    def get_errors(self) -> List[str]:
        """
        Get list of error messages for backward compatibility

        Returns:
            List of formatted error messages
        """
        return [
            f"{detail['field_name']}: {detail['message']}"
            for detail in self.get_error_details()
        ]
