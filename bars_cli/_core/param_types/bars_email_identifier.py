"""Click parameter type for BARS email identifiers."""

import re
from typing import Dict, Any

from .base import ValidatedParamType


def _convert_bars_email_identifier(identifier: str) -> Dict[str, Any]:
    """Convert BARS email identifier input to dict format.
    
    Validates that the email address ends with @bigapplerecsports.com.
    
    Args:
        identifier: Raw identifier string from user input
        
    Returns:
        Dict with key: "email"
        
    Raises:
        ValueError: If identifier format is invalid or doesn't end with @bigapplerecsports.com
    """
    identifier = identifier.strip() if identifier else ""
    if not identifier:
        raise ValueError("Email identifier cannot be empty")
    
    # Basic email format validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, identifier):
        raise ValueError(
            f"Invalid email format: '{identifier}'\n"
            f"   Must be a valid email address ending with @bigapplerecsports.com"
        )
    
    # Check domain
    if not identifier.lower().endswith('@bigapplerecsports.com'):
        raise ValueError(
            f"Invalid email domain: '{identifier}'\n"
            f"   Must end with @bigapplerecsports.com"
        )
    
    return {"email": identifier}


class BarsEmailIdentifierParam(ValidatedParamType):
    """Click parameter type for BARS email identifiers.
    
    Validates that the email address ends with @bigapplerecsports.com.
    """
    
    def __init__(self):
        super().__init__(
            converter_function=_convert_bars_email_identifier,
            prompt_text="Enter email address (@bigapplerecsports.com)"
        )


BARS_EMAIL_IDENTIFIER = BarsEmailIdentifierParam()

