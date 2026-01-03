"""
Text transformation utilities for CSV processing.

Provides common text transformations like snake_case conversion.
"""
import re


def to_snake_case(text: str) -> str:
    """
    Convert string to snake_case.
    
    Removes non-alphanumeric characters, converts spaces to underscores,
    and lowercases the result.
    
    Args:
        text: Input text to convert
        
    Returns:
        snake_case version of the input text
        
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

