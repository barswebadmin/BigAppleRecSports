"""
Enhanced Validators class with Pydantic-based validation.

This module provides a centralized validation system that leverages Pydantic's
native validation capabilities for robust, type-safe validation. It can return either:
- Validated values (strict=True, default)
- Boolean results (strict=False)
- None for empty values when allowed

The Validators class uses a decorator pattern for registering validation functions
and integrates with Pydantic's validation system for consistent behavior.
"""

import re
from typing import Any, Union
from enum import Enum
from pydantic import BaseModel, ValidationError, field_validator
from pydantic.networks import HttpUrl

try:
    from decorator import decorator
except ImportError:
    # Fallback if decorator library is not available
    def decorator(wrapper):
        def decorator_wrapper(func):
            return wrapper(func)
        return decorator_wrapper


class ValidationTypeEnum(str, Enum):
    """Supported validation types."""
    EMAIL = "email"
    ENUM = "enum"
    NUMERIC = "numeric"
    URL = "url"
    PHONE = "phone"


class Validators:
    """A class for handling different types of validation using Pydantic and dispatch pattern."""
    
    def __init__(self, **config):
        self.cfg = config
        self._registry = {}
    
    def validate(self, input_value: Any, validation_type: str, **options) -> Union[Any, bool, None]:
        """
        Validate input based on validation type using Pydantic validation.
        
        Args:
            input_value: Value to validate
            validation_type: Type of validation to perform
            **options: Additional options including:
                - strict (bool): If True, returns validated value or raises exception.
                                If False, returns boolean. Default: True
                - allow_empty (bool): If True, allows empty/None values. Default: False
                - Other validation-specific options
        
        Returns:
            - If strict=True: Validated value or raises ValueError
            - If strict=False: Boolean (True/False)
            - If allow_empty=True and value is empty: None
        """
        if validation_type not in self._registry:
            if options.get('strict', True):
                raise ValueError(f"Validation type '{validation_type}' not implemented")
            return False
        
        validator_func = self._registry[validation_type]
        return validator_func(input_value, **options)
    
    def register(self, validation_type: str):
        """Register a validation function for a specific type."""
        def register_decorator(func):
            self._registry[validation_type] = func
            return func
        return register_decorator


# Create a global instance
validators = Validators()


# Pydantic models for validation
class UrlValidationModel(BaseModel):
    """Pydantic model for URL validation."""
    url: HttpUrl


class NumericValidationModel(BaseModel):
    """Pydantic model for numeric validation with constraints."""
    value: Union[int, float]
    
    @field_validator('value')
    @classmethod
    def validate_numeric_constraints(cls, v, info):
        """Apply min/max constraints if provided."""
        if hasattr(info, 'context') and info.context:
            min_value = info.context.get('min_value')
            max_value = info.context.get('max_value')
            
            if min_value is not None and v < min_value:
                raise ValueError(f"Must be at least {min_value}")
            
            if max_value is not None and v > max_value:
                raise ValueError(f"Must be at most {max_value}")
        
        return v


class IntegerValidationModel(BaseModel):
    """Pydantic model for integer-only validation."""
    value: int
    
    @field_validator('value')
    @classmethod
    def validate_integer_constraints(cls, v, info):
        """Apply min/max constraints if provided."""
        if hasattr(info, 'context') and info.context:
            min_value = info.context.get('min_value')
            max_value = info.context.get('max_value')
            
            if min_value is not None and v < min_value:
                raise ValueError(f"Must be at least {min_value}")
            
            if max_value is not None and v > max_value:
                raise ValueError(f"Must be at most {max_value}")
        
        return v


def _handle_empty_value(input_value: Any, allow_empty: bool, strict: bool, field_name: str = "Value"):
    """
    Handle empty values consistently across all validators.
    
    Returns:
        - None if allow_empty=True and value is empty
        - Raises ValueError if strict=True and value is empty but not allowed
        - Returns False if strict=False and value is empty but not allowed
        - Returns the input_value if it's not empty
        - Returns 'continue' string to indicate validation should continue
    """
    if input_value is None or (isinstance(input_value, str) and input_value.strip() == ""):
        if allow_empty:
            return None
        if strict:
            raise ValueError(f"{field_name} is required")
        return False
    return 'continue'


# Email validation using regex
@validators.register('email')
def validate_email(input_value: Any, **options):
    """
    Email validation using regex pattern.
    
    Options:
        strict (bool): If True, returns validated email or raises ValueError. 
                      If False, returns boolean. Default: True
        allow_empty (bool): If True, allows empty/None values. Default: False
    
    Returns:
        - strict=True: Validated email string or raises ValueError
        - strict=False: Boolean
        - allow_empty=True and empty: None
    """
    strict = options.get('strict', True)
    allow_empty = options.get('allow_empty', False)
    
    # Handle empty values
    empty_result = _handle_empty_value(input_value, allow_empty, strict, "Email")
    if empty_result != 'continue':
        return empty_result
    
    # Simple but effective email regex pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    try:
        email_str = str(input_value).strip()
        if re.match(email_pattern, email_str):
            return email_str if strict else True
        else:
            if strict:
                raise ValueError(f"Invalid email format: {email_str}")
            return False
    except Exception as e:
        if strict:
            raise ValueError(f"Invalid email format: {str(e)}") from e
        return False


# Enum validation using Pydantic Enum
@validators.register('enum')
def validate_enum(input_value: Any, **options):
    """
    Validate that value is in allowed_values using Pydantic Enum validation.
    
    Options:
        strict (bool): If True, returns validated value or raises ValueError.
                      If False, returns boolean. Default: True
        allow_empty (bool): If True, allows empty/None values. Default: False
        allowed_values: List of allowed values
        case_sensitive: If True, match exactly. If False, match case-insensitively (default: False)
    
    Returns:
        - strict=True: Properly cased value from allowed_values or raises ValueError
        - strict=False: Boolean
        - allow_empty=True and empty: None
    """
    strict = options.get('strict', True)
    allow_empty = options.get('allow_empty', False)
    allowed_values = options.get("allowed_values", [])
    case_sensitive = options.get("case_sensitive", False)
    
    # Handle empty values
    empty_result = _handle_empty_value(input_value, allow_empty, strict, "Value")
    if empty_result != 'continue':
        return empty_result
    
    if not allowed_values:
        if strict:
            raise ValueError("allowed_values must be provided for enum validation")
        return False
    
    # Create a dynamic Pydantic Enum class
    try:
        # Convert to string for comparison
        value = str(input_value)
        
        if not case_sensitive:
            # Case-insensitive matching
            value_lower = value.lower()
            for allowed in allowed_values:
                if str(allowed).lower() == value_lower:
                    return str(allowed) if strict else True
        else:
            # Case-sensitive matching
            if value in [str(v) for v in allowed_values]:
                return value if strict else True
        
        # Value not found in allowed values
        if strict:
            raise ValueError(f"Must be one of: {', '.join(str(v) for v in allowed_values)}")
        return False
        
    except (ValueError, TypeError) as e:
        if strict:
            raise ValueError(f"Enum validation error: {str(e)}") from e
        return False


# Numeric validation using Pydantic numeric types
@validators.register('numeric')
def validate_numeric(input_value: Any, **options):
    """
    Validate that value is numeric using Pydantic's numeric validation.
    
    Options:
        strict (bool): If True, returns validated number or raises ValueError.
                      If False, returns boolean. Default: True
        allow_empty (bool): If True, allows empty/None values. Default: False
        min_value: Minimum allowed value (optional)
        max_value: Maximum allowed value (optional)
        integer_only: If True, only allow integers (default: False)
    
    Returns:
        - strict=True: Validated number (int/float) or raises ValueError
        - strict=False: Boolean
        - allow_empty=True and empty: None
    """
    strict = options.get('strict', True)
    allow_empty = options.get('allow_empty', False)
    integer_only = options.get("integer_only", False)
    
    # Handle empty values
    empty_result = _handle_empty_value(input_value, allow_empty, strict, "Numeric value")
    if empty_result != 'continue':
        return empty_result
    
    try:
        # Create validation context for constraints
        context = {
            'min_value': options.get('min_value'),
            'max_value': options.get('max_value')
        }
        
        # Use appropriate Pydantic model based on integer_only
        if integer_only:
            model = IntegerValidationModel.model_validate(
                {'value': input_value}, 
                context=context
            )
        else:
            model = NumericValidationModel.model_validate(
                {'value': input_value}, 
                context=context
            )
        
        return model.value if strict else True
        
    except ValidationError as e:
        if strict:
            # Extract the first error message for cleaner output
            error_msg = e.errors()[0]['msg'] if e.errors() else "Invalid numeric value"
            raise ValueError(error_msg) from e
        return False


# URL validation using Pydantic HttpUrl
@validators.register('url')
def validate_url(input_value: Any, **options):
    """
    URL validation using Pydantic's HttpUrl validation.
    
    Options:
        strict (bool): If True, returns validated URL or raises ValueError.
                      If False, returns boolean. Default: True
        allow_empty (bool): If True, allows empty/None values. Default: False
        require_https (bool): If True, only allow HTTPS URLs. Default: False
    
    Returns:
        - strict=True: Validated URL string or raises ValueError
        - strict=False: Boolean
        - allow_empty=True and empty: None
    """
    strict = options.get('strict', True)
    allow_empty = options.get('allow_empty', False)
    require_https = options.get('require_https', False)
    
    # Handle empty values
    empty_result = _handle_empty_value(input_value, allow_empty, strict, "URL")
    if empty_result != 'continue':
        return empty_result
    
    try:
        # Use Pydantic's HttpUrl validation
        model = UrlValidationModel(url=input_value)
        validated_url = str(model.url)
        
        if require_https and not validated_url.startswith('https://'):
            if strict:
                raise ValueError("HTTPS URL required")
            return False
        
        return validated_url if strict else True
        
    except ValidationError as e:
        if strict:
            # Extract the first error message for cleaner output
            error_msg = e.errors()[0]['msg'] if e.errors() else "Invalid URL format"
            raise ValueError(f"Invalid URL format: {error_msg}") from e
        return False


# ============================================================================
# USAGE EXAMPLES AND DOCUMENTATION
# ============================================================================

"""
USAGE EXAMPLES WITH PYDANTIC VALIDATION:

1. STRICT MODE (DEFAULT) - Returns validated values or raises exceptions:
   
   # Email validation using regex
   email = validators.validate('user@example.com', 'email')  # Returns: 'user@example.com'
   email = validators.validate('invalid', 'email')  # Raises: ValueError("Invalid email format...")
   
   # Enum validation with case-insensitive matching
   category = validators.validate('PREMIUM', 'enum', 
                                 allowed_values=['basic', 'premium'], 
                                 case_sensitive=False)  # Returns: 'premium'
   
   # Numeric validation with Pydantic constraints
   age = validators.validate('25', 'numeric', min_value=18, max_value=120)  # Returns: 25
   price = validators.validate('19.99', 'numeric', min_value=0)  # Returns: 19.99
   count = validators.validate('5', 'numeric', integer_only=True)  # Returns: 5

2. NON-STRICT MODE - Returns booleans:
   
   # Fast boolean checks using Pydantic validation
   is_valid_email = validators.validate('user@example.com', 'email', strict=False)  # Returns: True
   is_valid_url = validators.validate('https://example.com', 'url', strict=False)  # Returns: True
   is_valid_number = validators.validate('abc', 'numeric', strict=False)  # Returns: False

3. ALLOW EMPTY - Handles optional fields:
   
   # Optional fields with Pydantic validation
   email = validators.validate('', 'email', allow_empty=True)  # Returns: None
   email = validators.validate('user@example.com', 'email', allow_empty=True)  # Returns: 'user@example.com'
   url = validators.validate(None, 'url', allow_empty=True)  # Returns: None

4. PYDANTIC MODEL INTEGRATION:
   
   from pydantic import BaseModel, field_validator
   
   class UserModel(BaseModel):
       email: str
       website: Optional[str] = None
       age: int
       
       @field_validator('email')
       @classmethod
       def validate_email(cls, v):
           return validators.validate(v, 'email', strict=True, allow_empty=False)
       
       @field_validator('website')
       @classmethod
       def validate_website(cls, v):
           return validators.validate(v, 'url', strict=True, allow_empty=True, require_https=True)
       
       @field_validator('age')
       @classmethod
       def validate_age(cls, v):
           return validators.validate(v, 'numeric', strict=True, min_value=0, max_value=150, integer_only=True)

5. ADVANCED VALIDATION WITH PYDANTIC FEATURES:
   
   # URL validation with HTTPS requirement
   secure_url = validators.validate('https://example.com', 'url', require_https=True)
   
   # Integer-only numeric validation
   user_id = validators.validate('123', 'numeric', integer_only=True, min_value=1)
   
   # Case-insensitive enum validation
   status = validators.validate('ACTIVE', 'enum', 
                               allowed_values=['active', 'inactive'], 
                               case_sensitive=False)  # Returns: 'active'

BENEFITS OF PYDANTIC INTEGRATION:
- Consistent validation behavior across the application
- Better error messages from Pydantic's validation system
- Type safety and IDE support
- Automatic serialization/deserialization
- Integration with FastAPI for automatic API documentation
- Extensible validation with custom Pydantic models
"""