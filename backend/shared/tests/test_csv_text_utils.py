"""
Tests for shared CSV text utilities.

Tests: clean_unicode_control_chars, to_snake_case, find_column
"""
import pytest
from shared.csv import clean_unicode_control_chars, to_snake_case, find_column


class TestCleanUnicodeControlChars:
    """Test Unicode control character cleaning."""
    
    @pytest.mark.parametrize("input_text,expected_output", [
        ("Hello\u200bWorld", "HelloWorld"),
        ("Test\u0000Text", "TestText"),
        ("Normal Text", "Normal Text"),
        ("Multiple\u200b\u200c\u200dSpaces", "MultipleSpaces"),
        ("", ""),
        ("Clean\u202aRTL\u202eText", "CleanRTLText"),
    ])
    def test_clean_unicode_control_chars(self, input_text, expected_output):
        """Test cleaning of various Unicode control characters."""
        assert clean_unicode_control_chars(input_text) == expected_output


class TestToSnakeCase:
    """Test snake_case conversion."""
    
    @pytest.mark.parametrize("input_text,expected_output", [
        ("Director of Bowling", "director_of_bowling"),
        ("Vice Commissioner", "vice_commissioner"),
        ("  Ops Manager  ", "ops_manager"),
        ("UPPERCASE TEXT", "uppercase_text"),
        ("Mixed-Case_Text", "mixedcase_text"),
        ("Special!@#Characters", "specialcharacters"),
        ("", ""),
        ("Single", "single"),
    ])
    def test_to_snake_case(self, input_text, expected_output):
        """Test conversion to snake_case."""
        assert to_snake_case(input_text) == expected_output


class TestFindColumn:
    """Test column finding by keywords."""
    
    def test_find_column_exact_match(self):
        """Test finding column with exact keyword match."""
        header_row = ["Name", "Email", "Phone"]
        assert find_column(header_row, ["email"]) == 1
    
    def test_find_column_partial_match(self):
        """Test finding column with partial keyword match."""
        header_row = ["Position", "BARS Email", "Personal Email"]
        assert find_column(header_row, ["bars email"]) == 1
    
    def test_find_column_case_insensitive(self):
        """Test case-insensitive matching."""
        header_row = ["NAME", "EMAIL", "PHONE"]
        assert find_column(header_row, ["name"]) == 0
        assert find_column(header_row, ["email"]) == 1
    
    def test_find_column_multiple_keywords(self):
        """Test matching against multiple keywords."""
        header_row = ["Full Name", "E-Mail Address", "Phone Number"]
        assert find_column(header_row, ["email", "e-mail"]) == 1
    
    def test_find_column_not_found(self):
        """Test when no matching column is found."""
        header_row = ["Name", "Title", "Department"]
        assert find_column(header_row, ["email"]) is None
    
    def test_find_column_empty_header(self):
        """Test with empty header row."""
        assert find_column([], ["email"]) is None
    
    def test_find_column_empty_keywords(self):
        """Test with empty keywords list."""
        header_row = ["Name", "Email"]
        assert find_column(header_row, []) is None
    
    def test_find_column_first_match(self):
        """Test that first matching column is returned."""
        header_row = ["Personal Email", "BARS Email", "Work Email"]
        assert find_column(header_row, ["email"]) == 0

