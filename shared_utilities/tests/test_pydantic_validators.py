"""
Tests for Pydantic-based Validators

Tests to verify the new Pydantic-based validation system works correctly.
"""

import pytest
from pydantic import ValidationError

from shared_utilities.validators import validators


class TestPydanticEmailValidation:
    """Test email validation using regex pattern."""

    def test_valid_email_strict_mode(self):
        """Test valid email in strict mode returns the email."""
        result = validators.validate('user@example.com', 'email')
        assert result == 'user@example.com'

    def test_valid_email_non_strict_mode(self):
        """Test valid email in non-strict mode returns True."""
        result = validators.validate('user@example.com', 'email', strict=False)
        assert result is True

    def test_invalid_email_strict_mode(self):
        """Test invalid email in strict mode raises ValueError."""
        with pytest.raises(ValueError, match="Invalid email format"):
            validators.validate('invalid-email', 'email')

    def test_invalid_email_non_strict_mode(self):
        """Test invalid email in non-strict mode returns False."""
        result = validators.validate('invalid-email', 'email', strict=False)
        assert result is False

    def test_empty_email_allow_empty_true(self):
        """Test empty email with allow_empty=True returns None."""
        result = validators.validate('', 'email', allow_empty=True)
        assert result is None
        
        result = validators.validate(None, 'email', allow_empty=True)
        assert result is None

    def test_empty_email_allow_empty_false_strict(self):
        """Test empty email with allow_empty=False in strict mode raises ValueError."""
        with pytest.raises(ValueError, match="Email is required"):
            validators.validate('', 'email', allow_empty=False)

    def test_empty_email_allow_empty_false_non_strict(self):
        """Test empty email with allow_empty=False in non-strict mode returns False."""
        result = validators.validate('', 'email', allow_empty=False, strict=False)
        assert result is False


class TestPydanticUrlValidation:
    """Test URL validation using Pydantic HttpUrl."""

    def test_valid_url_strict_mode(self):
        """Test valid URL in strict mode returns the URL."""
        result = validators.validate('https://example.com', 'url')
        assert result == 'https://example.com/'  # Pydantic normalizes URLs

    def test_valid_url_non_strict_mode(self):
        """Test valid URL in non-strict mode returns True."""
        result = validators.validate('https://example.com', 'url', strict=False)
        assert result is True

    def test_invalid_url_strict_mode(self):
        """Test invalid URL in strict mode raises ValueError."""
        with pytest.raises(ValueError, match="Invalid URL format"):
            validators.validate('not-a-url', 'url')

    def test_invalid_url_non_strict_mode(self):
        """Test invalid URL in non-strict mode returns False."""
        result = validators.validate('not-a-url', 'url', strict=False)
        assert result is False

    def test_https_requirement(self):
        """Test HTTPS requirement option."""
        # HTTP URL should fail with require_https=True
        with pytest.raises(ValueError, match="HTTPS URL required"):
            validators.validate('http://example.com', 'url', require_https=True)
        
        # HTTPS URL should pass
        result = validators.validate('https://example.com', 'url', require_https=True)
        assert result == 'https://example.com/'

    def test_https_requirement_non_strict(self):
        """Test HTTPS requirement in non-strict mode."""
        result = validators.validate('http://example.com', 'url', require_https=True, strict=False)
        assert result is False
        
        result = validators.validate('https://example.com', 'url', require_https=True, strict=False)
        assert result is True


class TestPydanticNumericValidation:
    """Test numeric validation using Pydantic numeric types."""

    def test_valid_number_strict_mode(self):
        """Test valid number in strict mode returns the number."""
        result = validators.validate('42', 'numeric')
        assert result == 42
        
        result = validators.validate('3.14', 'numeric')
        assert result == 3.14

    def test_valid_number_non_strict_mode(self):
        """Test valid number in non-strict mode returns True."""
        result = validators.validate('42', 'numeric', strict=False)
        assert result is True

    def test_invalid_number_strict_mode(self):
        """Test invalid number in strict mode raises ValueError."""
        with pytest.raises(ValueError):
            validators.validate('not-a-number', 'numeric')

    def test_invalid_number_non_strict_mode(self):
        """Test invalid number in non-strict mode returns False."""
        result = validators.validate('not-a-number', 'numeric', strict=False)
        assert result is False

    def test_integer_only_validation(self):
        """Test integer-only validation."""
        result = validators.validate('42', 'numeric', integer_only=True)
        assert result == 42
        assert isinstance(result, int)
        
        # Float should fail with integer_only=True
        with pytest.raises(ValueError):
            validators.validate('3.14', 'numeric', integer_only=True)

    def test_min_max_constraints(self):
        """Test min/max value constraints."""
        # Valid range
        result = validators.validate('25', 'numeric', min_value=18, max_value=65)
        assert result == 25
        
        # Below minimum
        with pytest.raises(ValueError, match="Must be at least 18"):
            validators.validate('15', 'numeric', min_value=18)
        
        # Above maximum
        with pytest.raises(ValueError, match="Must be at most 65"):
            validators.validate('70', 'numeric', max_value=65)


class TestPydanticEnumValidation:
    """Test enum validation with Pydantic-style validation."""

    def test_valid_enum_case_sensitive(self):
        """Test valid enum value with case-sensitive matching."""
        result = validators.validate('premium', 'enum', 
                                   allowed_values=['basic', 'premium'], 
                                   case_sensitive=True)
        assert result == 'premium'

    def test_valid_enum_case_insensitive(self):
        """Test valid enum value with case-insensitive matching."""
        result = validators.validate('PREMIUM', 'enum', 
                                   allowed_values=['basic', 'premium'], 
                                   case_sensitive=False)
        assert result == 'premium'  # Returns properly cased version

    def test_invalid_enum_strict_mode(self):
        """Test invalid enum value in strict mode raises ValueError."""
        with pytest.raises(ValueError, match="Must be one of: basic, premium"):
            validators.validate('invalid', 'enum', allowed_values=['basic', 'premium'])

    def test_invalid_enum_non_strict_mode(self):
        """Test invalid enum value in non-strict mode returns False."""
        result = validators.validate('invalid', 'enum', 
                                   allowed_values=['basic', 'premium'], 
                                   strict=False)
        assert result is False

    def test_missing_allowed_values(self):
        """Test enum validation without allowed_values."""
        with pytest.raises(ValueError, match="allowed_values must be provided"):
            validators.validate('value', 'enum')
        
        result = validators.validate('value', 'enum', strict=False)
        assert result is False


class TestPydanticValidationIntegration:
    """Test integration with Pydantic models."""

    def test_pydantic_model_integration(self):
        """Test that validators work well with Pydantic models."""
        from pydantic import BaseModel, field_validator
        
        class UserModel(BaseModel):
            email: str
            age: int
            website: str = None
            
            @field_validator('email')
            @classmethod
            def validate_email(cls, v):
                return validators.validate(v, 'email', strict=True, allow_empty=False)
            
            @field_validator('age')
            @classmethod
            def validate_age(cls, v):
                return validators.validate(v, 'numeric', strict=True, 
                                         min_value=0, max_value=150, integer_only=True)
            
            @field_validator('website')
            @classmethod
            def validate_website(cls, v):
                return validators.validate(v, 'url', strict=True, allow_empty=True)
        
        # Valid model
        user = UserModel(email='user@example.com', age=25, website='https://example.com')
        assert user.email == 'user@example.com'
        assert user.age == 25
        assert user.website == 'https://example.com/'
        
        # Invalid email should raise ValidationError
        with pytest.raises(ValidationError):
            UserModel(email='invalid-email', age=25)
        
        # Invalid age should raise ValidationError
        with pytest.raises(ValidationError):
            UserModel(email='user@example.com', age=200)


class TestValidatorRegistration:
    """Test validator registration system."""

    def test_unknown_validation_type_strict(self):
        """Test unknown validation type in strict mode raises ValueError."""
        with pytest.raises(ValueError, match="Validation type 'unknown' not implemented"):
            validators.validate('value', 'unknown')

    def test_unknown_validation_type_non_strict(self):
        """Test unknown validation type in non-strict mode returns False."""
        result = validators.validate('value', 'unknown', strict=False)
        assert result is False

    def test_custom_validator_registration(self):
        """Test registering a custom validator."""
        @validators.register('test_custom')
        def validate_test_custom(input_value, **options):
            strict = options.get('strict', True)
            allow_empty = options.get('allow_empty', False)
            
            if input_value is None or input_value == '':
                if allow_empty:
                    return None
                if strict:
                    raise ValueError("Test value is required")
                return False
            
            if input_value == 'valid':
                return 'VALID' if strict else True
            
            if strict:
                raise ValueError("Must be 'valid'")
            return False
        
        # Test the custom validator
        result = validators.validate('valid', 'test_custom')
        assert result == 'VALID'
        
        result = validators.validate('valid', 'test_custom', strict=False)
        assert result is True
        
        with pytest.raises(ValueError, match="Must be 'valid'"):
            validators.validate('invalid', 'test_custom')
        
        result = validators.validate('invalid', 'test_custom', strict=False)
        assert result is False