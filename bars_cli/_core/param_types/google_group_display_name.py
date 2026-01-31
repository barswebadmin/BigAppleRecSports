"""Click parameter type for Google Group display names."""

from .base import ValidatedParamType


def _convert_google_group_display_name(name: str) -> str:
    """Convert and validate Google Group display name.
    
    Google Groups display names have these constraints:
    - Must be 1-75 characters
    - Cannot be empty or just whitespace
    
    Args:
        name: Raw display name from user input
        
    Returns:
        Validated display name string
        
    Raises:
        ValueError: If name is invalid
    """
    name = name.strip() if name else ""
    if not name:
        raise ValueError("Display name cannot be empty")
    
    if len(name) > 75:
        raise ValueError(f"Display name too long: {len(name)} characters (max 75)")
    
    return name


class GoogleGroupDisplayNameParam(ValidatedParamType):
    """Click parameter type for Google Group display names."""
    
    def __init__(self):
        super().__init__(
            converter_function=_convert_google_group_display_name,
            prompt_text="Enter group display name (1-75 characters)"
        )


GOOGLE_GROUP_DISPLAY_NAME = GoogleGroupDisplayNameParam()