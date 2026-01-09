"""Click parameter type for BARS email identifiers."""

from .base import ValidatedParamType


def _convert_bars_email_identifier(identifier: str) -> str:
    """Convert BARS email identifier input to email format.
    
    Automatically appends @bigapplerecsports.com if not already present.
    Accepts any single string (no spaces allowed).
    
    Args:
        identifier: Raw identifier string from user input (e.g., "dodgeball" or "dodgeball@bigapplerecsports.com")
        
    Returns:
        String with the email address (guaranteed to end with @bigapplerecsports.com)
        
    Raises:
        ValueError: If identifier contains spaces or is empty
    """
    identifier = identifier.strip() if identifier else ""
    if not identifier:
        raise ValueError("Email identifier cannot be empty")
    
    # Check for spaces (only validation that should fail)
    if ' ' in identifier:
        raise ValueError(
            f"Invalid email identifier: '{identifier}'\n"
            f"   Cannot contain spaces"
        )
    
    # If already ends with @bigapplerecsports.com, return as-is
    if identifier.lower().endswith('@bigapplerecsports.com'):
        return identifier
    
    # Otherwise, append @bigapplerecsports.com
    return f"{identifier}@bigapplerecsports.com"


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

