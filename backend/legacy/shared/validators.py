"""
Backend validators module.

Provides ValidationResult class and email validation for backend code.
Uses shared_utilities.validators for the actual validation logic.
"""
from dataclasses import dataclass
from typing import Optional, Any

from shared_utilities.validators import validators


@dataclass(frozen=True)
class ValidationResult:
    """
    Validation result with optional value transformation.
    
    Used by backend code for validation that needs both success/failure
    status and transformed values.
    """
    input_after_validation: Optional[Any]
    error_message: Optional[str] = None
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return self.error_message is None
    
    @classmethod
    def success(cls, input_after_validation: Any) -> "ValidationResult":
        """Create a successful validation result."""
        return cls(input_after_validation=input_after_validation, error_message=None)
    
    @classmethod
    def failure(cls, error_message: str) -> "ValidationResult":
        """Create a failed validation result."""
        if not error_message or not error_message.strip():
            raise ValueError("error_message must be a non-empty string for failure")
        return cls(input_after_validation=None, error_message=error_message)


def validate_email_with_results(email: Optional[str]) -> ValidationResult:
    """
    Validate email format and return ValidationResult.
    
    Used by backend Pydantic models for email validation.
    """
    try:
        validated_email = validators.validate(email, 'email', strict=True, allow_empty=False)
        return ValidationResult.success(validated_email)
    except ValueError as e:
        return ValidationResult.failure(str(e))
