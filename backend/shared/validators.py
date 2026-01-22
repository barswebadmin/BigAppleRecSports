import re
from dataclasses import dataclass
from typing import Optional, TypedDict, Dict, List, Callable, Any
from pydantic.alias_generators import to_camel as snake_to_camel


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
    def success(cls, input_after_validation: Any = None) -> "ValidationResult":
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


def validate_email_format(email: Optional[str]) -> ValidationResult:
    """
    Pragmatic email validation:
    - local part allows common RFC 5322 safe chars
    - domain has at least one dot and valid labels
    """
    if email is None:
        return ValidationResult.failure("Email is required")
    pattern = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}$")
    if pattern.match(email) is None:
        return ValidationResult.failure("Invalid email format")
    return ValidationResult.success()


def validate_shopify_order_number_format(order_number: Optional[str]) -> ValidationResult:
    """
    Validate a Shopify order number: optional leading '#', followed by at least 4 digits.
    """
    if order_number is None:
        return ValidationResult.failure("Order number is required")
    if re.match(r'^#?\d{4,}$', order_number) is None:
        return ValidationResult.failure("Invalid order number format")
    return ValidationResult.success()


def validate_shopify_order_id_format(order_id: Optional[str]) -> ValidationResult:
    """
    Validate a Shopify order ID: optional leading "gid://shopify/Order/" followed by 10-15 digits.
    """
    if order_id is None:
        return ValidationResult.failure("Order ID was not provided")
    # Accept either numeric id or full gid form
    if re.match(r'^\d{10,15}$', order_id) is None and re.match(r'^gid://shopify/Order/\d{10,15}$', order_id) is None:
        return ValidationResult.failure("Invalid order ID format")
    return ValidationResult.success()


def validate_shopify_product_id_format(product_id: Optional[str]) -> ValidationResult:
    """
    Validate a Shopify product ID: allow numeric or full GID (gid://shopify/Product/{digits}).
    """
    if product_id is None:
        return ValidationResult.failure("Product ID was not provided")
    if re.match(r'^\d{8,20}$', product_id) is None and re.match(r'^gid://shopify/Product/\d{8,20}$', product_id) is None:
        return ValidationResult.failure("Invalid product ID format")
    return ValidationResult.success()


def validate_shopify_customer_id_format(customer_id: Optional[str]) -> ValidationResult:
    """
    Validate a Shopify customer ID: allow numeric or full GID (gid://shopify/Customer/{digits}).
    """
    if customer_id is None:
        return ValidationResult.failure("Customer ID was not provided")
    if re.match(r'^\d{8,20}$', customer_id) is None and re.match(r'^gid://shopify/Customer/\d{8,20}$', customer_id) is None:
        return ValidationResult.failure("Invalid customer ID format")
    return ValidationResult.success()


def validate_shopify_transaction_id_format(transaction_id: Optional[str]) -> ValidationResult:
    """
    Validate a Shopify transaction ID: allow numeric or full GID (gid://shopify/Transaction/{digits}).
    """
    if transaction_id is None:
        return ValidationResult.failure("Transaction ID was not provided")
    if re.match(r'^\d{8,20}$', transaction_id) is None and re.match(r'^gid://shopify/Transaction/\d{8,20}$', transaction_id) is None:
        return ValidationResult.failure("Invalid transaction ID format")
    return ValidationResult.success()


def validate_shopify_variant_id_format(variant_id: Optional[str]) -> ValidationResult:
    """
    Validate a Shopify variant ID: allow numeric or full GID (gid://shopify/ProductVariant/{digits}).
    """
    if variant_id is None:
        return ValidationResult.failure("Variant ID was not provided")
    if re.match(r'^\d{8,20}$', variant_id) is None and re.match(r'^gid://shopify/ProductVariant/\d{8,20}$', variant_id) is None:
        return ValidationResult.failure("Invalid variant ID format")
    return ValidationResult.success()


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
                "email": validate_email_format,
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


