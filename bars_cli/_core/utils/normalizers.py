"""Normalization utilities for identifiers and values."""

import re
from typing import Any, Callable, Optional, Union
from uuid import UUID
import logging

# ANSI escape sequence pattern for removing all ANSI codes
_ANSI_ESCAPE_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def normalize_phone_number(phone: str) -> Optional[str]:
    """Normalize phone number to digits only.
    
    Strips all non-digit characters (removes dashes, spaces, parentheses, etc.)
    to get just the digits. Returns None if the result is empty or invalid.
    
    Args:
        phone: Phone number string (may contain formatting)
        
    Returns:
        Phone number as digits-only string, or None if empty/invalid
    """
    if not phone:
        return None
    # Strip all non-digit characters
    digits_only = re.sub(r'[^\d]', '', phone)
    # Return None if no digits found
    if not digits_only:
        return None
    return digits_only


def normalize_ssn(ssn_to_validate: str, include_hyphens = True) -> Optional[str]:
    """Normalize SSN to format XXX-XX-XXXX.
    
    Formats 9 digits as XXX-XX-XXXX (with hyphens).
    If already formatted, validates and returns as-is.
    
    Args:
        ssn: SSN string (may be 9 digits or already formatted)
        
    Returns:
        SSN in format XXX-XX-XXXX
    """
    if not ssn_to_validate or not isinstance(ssn_to_validate,str) or not ssn_to_validate.strip():
        return None
    
    # Strip all non-digit characters
    digits_only = re.sub(r'[^\d]', '', ssn_to_validate)
    
    # Must be exactly 9 digits
    if len(digits_only) != 9:
        return None
    
    # Format as XXX-XX-XXXX
    return f"{digits_only[0:3]}-{digits_only[3:5]}-{digits_only[5:9]}" if include_hyphens else digits_only


def normalize_uuid(uuid_to_validate: str) -> Optional[str]:
    """Normalize UUID string by adding hyphens if missing.
    
    Converts UUIDs without hyphens (32 hex chars) to standard format (36 chars with hyphens).
    UUIDs that already have hyphens are returned as-is.
    Leading and trailing whitespace is automatically stripped.
    
    Args:
        uuid_to_validate: UUID as str or type UUID, (with or without hyphens)
        
    Returns:
        Normalized UUID string with hyphens, or None if invalid
        
    Examples:
        >>> normalize_uuid("550e8400-e29b-41d4-a716-446655440000")
        '550e8400-e29b-41d4-a716-446655440000'
        >>> normalize_uuid("550e8400e29b41d4a716446655440000")
        '550e8400-e29b-41d4-a716-446655440000'
    """
    if not uuid_to_validate:
        return None
    try:
        return str(UUID(uuid_to_validate.strip()))
    except ValueError as e:
        logging.debug(f"\n{uuid_to_validate} could not be parsed as UUID")
        return None


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text.
    
    Args:
        text: Text that may contain ANSI escape sequences
        
    Returns:
        Text with ANSI escape sequences removed
    """
    return _ANSI_ESCAPE_PATTERN.sub('', text)


def normalize_string(
    input_str: str,
    transformations: Union[dict[str, Any], list[str]]
) -> Optional[str]:
    """Normalize string by applying transformations sequentially.
    
    Args:
        input_str: Input string to normalize
        transformations: 
            Either a dict mapping transformation names to args,
            or a list of transformation names to apply in order.
            
            Supported transformation names:
            - "strip": Strip whitespace
            - "lower": Convert to lowercase
            - "upper": Convert to uppercase
            - "strip_ansi": Remove ANSI escape sequences
            
    Returns:
        Normalized string, or None if input is empty or whitespace-only
    """
    # Return None if empty or whitespace-only
    if not input_str or not input_str.strip():
        return None
    
    # Transformation function registry
    _transformations: dict[str, Callable[[str], str]] = {
        "strip": lambda s: s.strip(),
        "lower": lambda s: s.lower(),
        "upper": lambda s: s.upper(),
        "strip_ansi": strip_ansi,
    }
    
    result = input_str
    
    # Handle list format
    if isinstance(transformations, list):
        for transform_name in transformations:
            if transform_name in _transformations:
                result = _transformations[transform_name](result)
            else:
                raise ValueError(f"Unknown transformation: {transform_name}")
        # Check if result is empty/whitespace after transformations
        if not result or not result.strip():
            return None
        return result
    
    # Handle dict format
    if isinstance(transformations, dict):
        for transform_name, transform_arg in transformations.items():
            if transform_name not in _transformations:
                raise ValueError(f"Unknown transformation: {transform_name}")
            
            # If arg is False, skip this transformation
            if transform_arg is False:
                continue
            
            # Apply transformation
            result = _transformations[transform_name](result)
        # Check if result is empty/whitespace after transformations
        if not result or not result.strip():
            return None
        return result
    
    raise TypeError("transformations must be a dict or list")


def snake_to_camel(snake_str: str) -> Optional[str]:
    """Convert snake_case string to camelCase.
    
    Uses normalize_string to strip whitespace and handle edge cases.
    
    Args:
        snake_str: String in snake_case format (e.g., "employment_status")
        
    Returns:
        String in camelCase format (e.g., "employmentStatus"), or None if empty/whitespace
    """
    # Normalize input (strip whitespace)
    normalized = normalize_string(snake_str, ["strip"])
    
    # Return None if empty or whitespace-only
    if not normalized:
        return None
    
    components = [c for c in normalized.split('_') if c]
    if not components:
        return None
    
    # First component stays lowercase, rest are capitalized
    return components[0] + ''.join(word.capitalize() for word in components[1:])


def camel_to_snake(camel_str: str) -> Optional[str]:
    """Convert camelCase string to snake_case.
    
    Args:
        camel_str: String in camelCase format
        
    Returns:
        String in snake_case format, or None if empty/whitespace
    """
    # Normalize input (strip whitespace)
    normalized = normalize_string(camel_str, ["strip"])
    
    # Return None if empty or whitespace-only
    if not normalized:
        return None
    
    # Insert underscore before uppercase letters (except the first one)
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', normalized)
    result = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
    
    # Apply lowercase transformation
    return normalize_string(result, ["lower"])


def _detect_whitespace(text: str) -> tuple[int, int]:
    """Detect leading and trailing spaces in text.
    
    Args:
        text: Input text to analyze
        
    Returns:
        Tuple of (num_leading_spaces, num_trailing_spaces)
    """
    num_leading_spaces = len(text) - len(text.lstrip(' '))
    num_trailing_spaces = len(text) - len(text.rstrip(' '))
    return (num_leading_spaces, num_trailing_spaces)


def replace_whitespace_with_char(text: str, replacement: str = '_') -> str:
    """Replace leading and trailing spaces with a replacement character.
    
    Leading and trailing spaces are replaced with the specified character to make them visible.
    Internal spaces are left unchanged.
    
    Args:
        text: Input text that may have leading/trailing spaces
        replacement: Character to replace spaces with (default: '_')
        
    Returns:
        Text with leading and trailing spaces replaced with the replacement character
        
    Raises:
        ValueError: If input contains only spaces (not empty string)
    """
    # Handle empty string - return as-is
    if not text:
        return text
    
    num_leading, num_trailing = _detect_whitespace(text)
    
    # Check if input contains only spaces
    stripped = text.lstrip(' ').rstrip(' ')
    if not stripped:
        raise ValueError('only spaces detected in input')
    
    # Strip leading and trailing spaces
    result = stripped
    
    # Replace with replacement character
    if num_leading > 0:
        result = replacement * num_leading + result
    if num_trailing > 0:
        result = result + replacement * num_trailing
    
    return result

