"""Utility modules for BARS CLI."""

from .normalizers import (
    normalize_phone_number,
    normalize_ssn,
    normalize_uuid,
    strip_ansi,
    normalize_string,
    snake_to_camel,
    camel_to_snake,
)

from .json_output import (
    to_json_data,
    output_json,
    output_json_item,
    output_json_list,
    output_json_error,
)

__all__ = [
    "normalize_phone_number",
    "normalize_ssn",
    "normalize_uuid",
    "strip_ansi",
    "normalize_string",
    "snake_to_camel",
    "camel_to_snake",
    "to_json_data",
    "output_json",
    "output_json_item",
    "output_json_list",
    "output_json_error",
]

