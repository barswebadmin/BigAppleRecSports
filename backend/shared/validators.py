import re
from dataclasses import dataclass
from typing import Optional, TypedDict, Dict, List, Callable, Any
from pydantic.alias_generators import to_camel as snake_to_camel

from validator_collection import is_email


@dataclass(frozen=True)
class ValidationResult:
    """
    Validation result with optional value transformation.
    
    Supports both:
    1. Simple pass/fail validation (backend validators)
    2. Validation + transformation (CLI parameter types)
    """
    input_after_validation: Optional[Any]
    error_message: Optional[str] = None
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed (compatible with engine_cli API)."""
        return self.error_message is None
    
    # Backwards compatibility for dict-like access
    def get(self, key: str, default=None):
        """Dict-like .get() for backwards compatibility."""
        if key == "success":
            return self.error_message is None
        elif key == "message":
            return self.error_message
        return default
    
    def __getitem__(self, key: str):
        """Dict-like subscript access for backwards compatibility."""
        if key == "success":
            return self.error_message is None
        elif key == "message":
            return self.error_message
        raise KeyError(f"Key '{key}' not found")
    
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


class MultiFieldValidationResult(TypedDict, total=True):
    success: bool
    errors: List[str]


def validate_email(email: Optional[str]) -> ValidationResult:
    """
    Pragmatic email validation:
    - local part allows common RFC 5322 safe chars
    - domain has at least one dot and valid labels
    """
    if email is None:
        return ValidationResult.failure("Email is required")
    if not is_email(email.strip()):
        return ValidationResult.failure("Invalid email format")
    return ValidationResult.success(input_after_validation=email.strip())


def validate(
    input: Any,
    validation_config: Dict[str, Any]
) -> ValidationResult:
    """Validate input based on validation configuration (compatible with engine_cli API).
    
    Args:
        input: Value to validate
        validation_config: Dict containing validation_type and other options
        
    Returns:
        ValidationResult indicating success or failure with error message
        
    Example:
        result = validate("leadership", {
            "validation_type": "enum",
            "allowed_values": ["Leadership", "Refunds"],
            "case_sensitive": False
        })
        if result.is_valid:
            print("Valid!")
    """
    validation_type = validation_config.get("validation_type")
    
    if not validation_type:
        return ValidationResult.failure("validation_config must contain 'validation_type'")
    
    # Handle enum validation (most common case)
    if validation_type == "enum":
        allowed_values = validation_config.get("allowed_values", [])
        case_sensitive = validation_config.get("case_sensitive", False)
        if not allowed_values:
            return ValidationResult.failure("validation_config must contain 'allowed_values' list for enum validation")
        return validate_enum(str(input), allowed_values, case_sensitive)
    
    # For other validation types, return failure (not implemented in bars_cli yet)
    return ValidationResult.failure(f"Validation type '{validation_type}' not yet implemented in bars_cli")


def validate_enum(value: str, allowed_values: list[str], case_sensitive: bool = False) -> ValidationResult:
    """
    Validate that value is in allowed_values with optional case-insensitive matching.
    
    Args:
        value: The value to validate
        allowed_values: List of allowed values
        case_sensitive: If True, match exactly. If False, match case-insensitively
        
    Returns:
        ValidationResult with the properly cased value on success
        
    Example:
        result = validate_enum("leadership", ["Leadership", "Refunds"], case_sensitive=False)
        # Returns ValidationResult.success("Leadership")
    """
    if not case_sensitive:
        value_lower = value.lower()
        if value_lower in [v.lower() for v in allowed_values]:
            # Return properly cased version
            for allowed in allowed_values:
                if allowed.lower() == value_lower:
                    return ValidationResult.success(allowed)
    else:
        if value in allowed_values:
            return ValidationResult.success(value)
    
    return ValidationResult.failure(f"Must be one of: {', '.join(allowed_values)}")


def validate_multiple_fields(
    data: Dict[str, Any], 
    field_validators: Dict[str, Callable[[Any], ValidationResult]]
) -> MultiFieldValidationResult:
    """
    Validate multiple fields and collect all validation errors.
    
    This centralized validator ensures all field errors are reported together,
    even when inputs are not the expected types. Supports both snake_case and
    camelCase field names (e.g., order_number and orderNumber).
    
    Args:
        data: Dictionary containing field values to validate
        field_validators: Dictionary mapping field names to their validator functions
        
    Returns:
        MultiFieldValidationResult with success status and list of errors
        
    Example:
        result = validate_multiple_fields(
            {"email": "bad", "order_number": "123"}, 
            {
                "email": validate_email,
                "order_number": validate_shopify_order_number_format
            }
        )
        if not result["success"]:
            raise ValueError("; ".join(result["errors"]))
    """
    errors = []
    
    for field_name, validator_func in field_validators.items():
        # Try snake_case first, then camelCase
        field_value = data.get(field_name)
        if field_value is None:
            camel_name = snake_to_camel(field_name)
            field_value = data.get(camel_name)
        
        try:
            # Check if field requires string type (most validators do)
            if field_value is not None and not isinstance(field_value, str):
                errors.append(f"{field_name}: Must be a string, got {type(field_value).__name__}")
            else:
                # Run the validator function
                result = validator_func(field_value)
                if not result.get("success"):
                    message = result.get("message") or f"Invalid {field_name} format"
                    errors.append(f"{field_name}: {message}")
        except Exception as e:
            errors.append(f"{field_name}: Validation error - {str(e)}")
    
    return {
        "success": len(errors) == 0,
        "errors": errors
    }


