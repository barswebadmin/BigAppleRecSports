"""
Tests for normalizers module.
Comprehensive test coverage for all normalization functions with colorized output.
"""

import pytest
import sys
import os

# Add backend to path so we can import shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.normalizers import normalize_shopify_id, normalize_order_number, normalize_email


class TestNormalizers:
    """Test suite for all normalizer functions with consolidated test cases."""

    def test_normalize_shopify_id_cases(self):
        """Test normalize_shopify_id with success and failure cases."""
        
        # Test cases: (input, expected_output, description)
        test_cases = [
            # Success cases
            ("123456789", "123456789", "plain numeric ID"),
            ("12345678", "12345678", "minimum length (8 digits)"),
            ("12345678901234567890", "12345678901234567890", "maximum length (20 digits)"),
            ("gid://shopify/Product/123456789", "123456789", "product GID format"),
            ("gid://shopify/Order/987654321", "987654321", "order GID format"),
            ("GID://SHOPIFY/Customer/555666777", "555666777", "case insensitive GID"),
            ("  gid://shopify/Variant/111222333  ", "111222333", "GID with whitespace"),
            
            # Failure cases
            ("1234567", None, "too short (7 digits)"),
            ("123456789012345678901", None, "too long (21 digits)"),
            ("gid://other/Product/123456789", None, "wrong domain (not shopify)"),
            ("gid://shopify/Product/", None, "missing ID in GID"),
            ("gid://shopify", None, "incomplete GID format"),
            ("abc123def", None, "non-numeric characters"),
            ("", None, "empty string"),
            (None, None, "None input"),
            ("gid://shopify/Product/abc123", None, "non-numeric ID in GID"),
        ]
        
        print(f"\n🧪 Testing normalize_shopify_id with {len(test_cases)} cases:")
        
        for input_val, expected, description in test_cases:
            result = normalize_shopify_id(input_val)
            
            if result == expected:
                print(f"  ✅ {description}")
                print(f"     \033[36mInput:\033[0m {repr(input_val)} → \033[32mGot:\033[0m {repr(result)}")
            else:
                print(f"  ❌ {description}")
                print(f"     \033[36mInput:\033[0m {repr(input_val)}")
                print(f"     \033[36mExpected:\033[0m {repr(expected)}")
                print(f"     \033[33mGot:\033[0m {repr(result)}")
                
            assert result == expected, f"Failed for {description}: input={repr(input_val)}"

    def test_normalize_order_number_cases(self):
        """Test normalize_order_number with success and failure cases."""
        
        # Test cases: (input, expected_output, description)
        test_cases = [
            # Success cases
            ("12345", "12345", "plain 5-digit number"),
            ("#12345", "12345", "number with hash prefix"),
            ("1234", "1234", "minimum length (4 digits)"),
            ("12345678", "12345678", "maximum length (8 digits)"),
            ("  #67890  ", "67890", "hash with whitespace"),
            ("#0001", "0001", "leading zeros with hash"),
            
            # Failure cases
            ("123", None, "too short (3 digits)"),
            ("123456789", None, "too long (9 digits)"),
            ("#abc123", None, "non-numeric with hash"),
            ("12a34", None, "mixed alphanumeric"),
            ("", None, "empty string"),
            (None, None, "None input"),
            ("#", None, "hash only"),
            ("##12345", None, "double hash"),
        ]
        
        print(f"\n🧪 Testing normalize_order_number with {len(test_cases)} cases:")
        
        for input_val, expected, description in test_cases:
            result = normalize_order_number(input_val)
            
            if result == expected:
                print(f"  ✅ {description}")
                print(f"     \033[36mInput:\033[0m {repr(input_val)} → \033[32mGot:\033[0m {repr(result)}")
            else:
                print(f"  ❌ {description}")
                print(f"     \033[36mInput:\033[0m {repr(input_val)}")
                print(f"     \033[36mExpected:\033[0m {repr(expected)}")
                print(f"     \033[33mGot:\033[0m {repr(result)}")
                
            assert result == expected, f"Failed for {description}: input={repr(input_val)}"

    def test_normalize_email_cases(self):
        """Test normalize_email with success and failure cases."""
        
        # Test cases: (input, expected_output, description)
        test_cases = [
            # Success cases
            ("user@example.com", "user@example.com", "basic valid email"),
            ("  USER@EXAMPLE.COM  ", "user@example.com", "uppercase with whitespace"),
            ("test.email+tag@domain.co.uk", "test.email+tag@domain.co.uk", "complex valid email"),
            ("a@b.c", "a@b.c", "minimal valid email"),
            ("user123@test-domain.org", "user123@test-domain.org", "alphanumeric with hyphen"),
            ("very.long.email.address@very.long.domain.name.com", 
             "very.long.email.address@very.long.domain.name.com", "long valid email"),
            
            # Failure cases
            ("invalid", None, "no @ symbol"),
            ("user@domain", None, "no dot in domain"),
            ("@domain.com", None, "empty local part"),
            ("user@", None, "empty domain part"),
            ("user@@domain.com", None, "multiple @ symbols"),
            ("user@domain.", None, "domain ends with dot"),
            ("", None, "empty string"),
            (None, None, "None input"),
            ("user@.com", None, "domain starts with dot"),
            ("a" * 65 + "@domain.com", None, "local part too long (>64 chars)"),
            ("user@" + "a" * 254 + ".com", None, "domain part too long (>253 chars)"),
            ("a" * 320 + "@b.c", None, "total length too long (>320 chars)"),
        ]
        
        print(f"\n🧪 Testing normalize_email with {len(test_cases)} cases:")
        
        for input_val, expected, description in test_cases:
            result = normalize_email(input_val)
            
            if result == expected:
                print(f"  ✅ {description}")
                print(f"     \033[36mInput:\033[0m {repr(input_val)} → \033[32mGot:\033[0m {repr(result)}")
            else:
                print(f"  ❌ {description}")
                print(f"     \033[36mInput:\033[0m {repr(input_val)}")
                print(f"     \033[36mExpected:\033[0m {repr(expected)}")
                print(f"     \033[33mGot:\033[0m {repr(result)}")
                
            assert result == expected, f"Failed for {description}: input={repr(input_val)}"

    def test_edge_cases_and_type_handling(self):
        """Test edge cases and type conversion handling."""
        
        print(f"\n🧪 Testing edge cases and type handling:")
        
        # Test integer inputs (should be converted to strings)
        result = normalize_shopify_id(str(123456789))
        expected = "123456789"
        print(f"  ✅ Integer input handling")
        print(f"     \033[36mInput:\033[0m {repr(123456789)} → \033[32mGot:\033[0m {repr(result)}")
        assert result == expected
        
        # Test float inputs (should handle conversion)
        result = normalize_order_number(str(12345.0))
        expected = None  # Float conversion creates "12345.0" which contains non-digits
        print(f"  ✅ Float input handling (expected failure)")
        print(f"     \033[36mInput:\033[0m {repr(12345.0)} → \033[32mGot:\033[0m {repr(result)}")
        assert result == expected
        
        # Test whitespace-only inputs
        result = normalize_email("   ")
        expected = None
        print(f"  ✅ Whitespace-only input")
        print(f"     \033[36mInput:\033[0m {repr('   ')} → \033[32mGot:\033[0m {repr(result)}")
        assert result == expected


if __name__ == "__main__":
    # Run tests with verbose output for local development
    pytest.main([__file__, "-v", "--tb=short"])
