"""
String manipulation utilities for text normalization.

For case conversion (snake_case ↔ camelCase), use Pydantic's built-in:
    from pydantic.alias_generators import to_camel, to_snake
"""
import re


def to_snake_case(text: str) -> str:
    """
    Convert string to snake_case.
    
    Removes non-alphanumeric characters, converts spaces to underscores,
    and lowercases the result.
        
    Examples:
        >>> to_snake_case("Director of Bowling")
        'director_of_bowling'
        >>> to_snake_case("Vice Commissioner")
        'vice_commissioner'
        >>> to_snake_case("  Ops Manager  ")
        'ops_manager'
    """
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', '_', text)
    return text.lower().strip('_')