"""
Tests for CSV utilities.

Tests generic, business-agnostic utilities for Excel-style column references.
"""
import pytest
from shared.csv import column_index_to_letter, cell_reference


class TestColumnIndexToLetter:
    """Test Excel-style column letter conversion."""
    
    @pytest.mark.parametrize("col_idx,expected", [
        (0, "A"),
        (1, "B"),
        (12, "M"),
        (25, "Z"),
        (26, "AA"),
        (27, "AB"),
        (51, "AZ"),
        (52, "BA"),
        (701, "ZZ"),
        (702, "AAA"),
        (703, "AAB"),
    ])
    def test_column_index_to_letter(self, col_idx, expected):
        """Test conversion of various column indices to Excel-style letters."""
        assert column_index_to_letter(col_idx) == expected
    
    def test_first_column(self):
        """First column (index 0) should be 'A'."""
        assert column_index_to_letter(0) == "A"
    
    def test_last_single_letter(self):
        """Last single-letter column (index 25) should be 'Z'."""
        assert column_index_to_letter(25) == "Z"
    
    def test_first_double_letter(self):
        """First double-letter column (index 26) should be 'AA'."""
        assert column_index_to_letter(26) == "AA"


class TestCellReference:
    """Test Excel-style cell reference generation."""
    
    @pytest.mark.parametrize("row,col_idx,expected", [
        (1, 0, "A1"),
        (5, 0, "A5"),
        (10, 1, "B10"),
        (10, 26, "AA10"),
        (100, 27, "AB100"),
        (50, 702, "AAA50"),
        (9999, 0, "A9999"),
        (1000, 701, "ZZ1000"),
    ])
    def test_cell_reference(self, row, col_idx, expected):
        """Test cell reference generation for various row/column combinations."""
        assert cell_reference(row, col_idx) == expected
    
    def test_typical_csv_error_reporting(self):
        """Test typical use case: reporting CSV error at row 5, column B."""
        assert cell_reference(5, 1) == "B5"
    
    def test_first_cell(self):
        """First cell should be A1."""
        assert cell_reference(1, 0) == "A1"

