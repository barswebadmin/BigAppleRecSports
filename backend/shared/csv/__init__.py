"""
CSV processing utilities.

Provides reusable utilities for CSV parsing, validation, and error reporting.
"""
from shared.csv.column_index_to_letter import column_index_to_letter
from shared.csv.cell_reference import cell_reference
from shared.csv.parse_csv_text import parse_csv_text
from shared.csv.clean_text import clean_unicode_control_chars
from shared.csv.column_finder import find_column
from shared.csv.compare import (
    read_csv_file,
    extract_order_id,
    normalize_header,
    normalize_phone_number,
    normalize_value,
    build_keyed_dict,
    compare_csvs,
    format_differences,
)

__all__ = [
    "column_index_to_letter",
    "cell_reference",
    "parse_csv_text",
    "clean_unicode_control_chars",
    "find_column",
    "read_csv_file",
    "extract_order_id",
    "normalize_header",
    "normalize_phone_number",
    "normalize_value",
    "build_keyed_dict",
    "compare_csvs",
    "format_differences",
]
