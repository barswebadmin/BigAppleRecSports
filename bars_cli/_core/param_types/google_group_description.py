"""Click parameter type for Google Group descriptions."""

from .base import ValidatedParamType


def _convert_google_group_description(description: str) -> str:
    """Convert and validate Google Group description.
    
    Google Groups descriptions have these constraints:
    - Maximum 300 characters
    - Can be empty (optional field)
    - Leading/trailing whitespace is trimmed
    
    Args:
        description: Raw description from user input
        
    Returns:
        Validated description string (empty string if not provided)
        
    Raises:
        ValueError: If description is too long
    """
    description = description.strip() if description else ""
    
    if len(description) > 300:
        raise ValueError(f"Description too long: {len(description)} characters (max 300)")
    
    return description


class GoogleGroupDescriptionParam(ValidatedParamType):
    """Click parameter type for Google Group descriptions."""
    
    def __init__(self):
        super().__init__(
            converter_function=_convert_google_group_description,
            prompt_text="Enter group description (optional, max 300 characters)"
        )


GOOGLE_GROUP_DESCRIPTION = GoogleGroupDescriptionParam()