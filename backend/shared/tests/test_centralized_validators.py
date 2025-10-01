"""
Tests for centralized multi-field validation functionality.
"""

import pytest
from ../../../shared.validators import (
    validate_multiple_fields,
    validate_email_format,
    validate_shopify_order_number_format,
)


class TestCentralizedValidation:
    """Test the centralized multi-field validator"""
    
    def test_all_valid_fields(self):
        """Test that valid data passes validation"""
        data = {"email": "test@example.com", "order_number": "#1234"}
        field_validators = {
            "email": validate_email_format,
            "order_number": validate_shopify_order_number_format,
        }
        
        result = validate_multiple_fields(data, field_validators)
        
        assert result["success"] is True
        assert result["errors"] == []
    
    def test_all_invalid_fields_collected(self):
        """Test that all invalid fields are reported together"""
        data = {"email": "bad-email", "order_number": "123"}
        field_validators = {
            "email": validate_email_format,
            "order_number": validate_shopify_order_number_format,
        }
        
        result = validate_multiple_fields(data, field_validators)
        
        assert result["success"] is False
        assert len(result["errors"]) == 2
        assert any("email:" in error and "Invalid email format" in error for error in result["errors"])
        assert any("order_number:" in error and "Invalid order number format" in error for error in result["errors"])
    
    def test_type_errors_collected(self):
        """Test that type errors are collected for all fields"""
        data = {"email": 123, "order_number": 456}
        field_validators = {
            "email": validate_email_format,
            "order_number": validate_shopify_order_number_format,
        }
        
        result = validate_multiple_fields(data, field_validators)
        
        assert result["success"] is False
        assert len(result["errors"]) == 2
        assert any("email: Must be a string, got int" in error for error in result["errors"])
        assert any("order_number: Must be a string, got int" in error for error in result["errors"])
    
    def test_mixed_errors_collected(self):
        """Test that both type and format errors are collected"""
        data = {"email": 123, "order_number": "bad"}
        field_validators = {
            "email": validate_email_format,
            "order_number": validate_shopify_order_number_format,
        }
        
        result = validate_multiple_fields(data, field_validators)
        
        assert result["success"] is False
        assert len(result["errors"]) == 2
        assert any("email: Must be a string, got int" in error for error in result["errors"])
        assert any("order_number:" in error and "Invalid order number format" in error for error in result["errors"])
    
    def test_single_field_validation(self):
        """Test validation with only one field"""
        data = {"email": "test@example.com"}
        field_validators = {
            "email": validate_email_format,
        }
        
        result = validate_multiple_fields(data, field_validators)
        
        assert result["success"] is True
        assert result["errors"] == []
    
    def test_missing_field_validation(self):
        """Test validation when field is missing (None)"""
        data = {}  # No fields provided
        field_validators = {
            "email": validate_email_format,
            "order_number": validate_shopify_order_number_format,
        }
        
        result = validate_multiple_fields(data, field_validators)
        
        assert result["success"] is False
        assert len(result["errors"]) == 2
        assert any("email:" in error and "Email was not provided" in error for error in result["errors"])
        assert any("order_number:" in error and "Order number was not provided" in error for error in result["errors"])
