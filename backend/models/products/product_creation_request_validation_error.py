"""
Custom validation error class for product creation requests
"""

from typing import List


class ProductCreationRequestValidationError(Exception):
    """Custom exception for product creation request validation errors

    Uses Pydantic's ValidationError structure while extending Exception for simplicity.
    Provides field_name attribute and maintains full error details.
    """

    def __init__(self, errors: List[dict]):
        """
        Initialize with standard Pydantic error format

        Args:
            errors: List of pydantic error dictionaries
        """
        self._errors = errors

        # Add field_name attribute for the first error (primary error)
        if errors:
            first_error = errors[0]
            self.field_name = ".".join(str(loc) for loc in first_error.get("loc", []))
        else:
            self.field_name = "unknown"

        # Create error message for exception
        error_messages = self.get_errors()
        message = f"Product validation failed: {', '.join(error_messages)}"
        super().__init__(message)

    def errors(self) -> List[dict]:
        """
        Return the original Pydantic error dictionaries

        Returns:
            List of pydantic error dictionaries
        """
        return self._errors

    def get_errors(self) -> List[str]:
        """
        Get list of error messages for backward compatibility

        Returns:
            List of formatted error messages
        """
        return [
            f"{'.'.join(str(loc) for loc in error.get('loc', []))}: {error.get('msg', 'Validation failed')}"
            for error in self._errors
        ]
