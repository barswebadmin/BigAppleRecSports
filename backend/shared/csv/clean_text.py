"""
Text cleaning utilities for CSV processing.

Removes invisible Unicode control characters and normalizes text.
"""
import re


def clean_unicode_control_chars(text: str) -> str:
    """
    Remove invisible Unicode control characters.
    
    Removes:
    - C0 controls (0x00-0x1F)
    - DEL (0x7F)
    - C1 controls (0x80-0x9F)
    - Zero-width spaces (0x200B-0x200F)
    - Directional formatting (0x202A-0x202E)
    
    Args:
        text: Input text that may contain Unicode control characters
        
    Returns:
        Cleaned text with control characters removed
        
    Examples:
        >>> clean_unicode_control_chars("Hello\u200bWorld")
        'HelloWorld'
        >>> clean_unicode_control_chars("Test\u0000Text")
        'TestText'
    """
    return re.sub(r'[\u0000-\u001f\u007f-\u009f\u200b-\u200f\u202a-\u202e]', '', text)

