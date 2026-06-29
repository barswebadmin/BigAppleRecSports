"""
Extract customer properties (birthday, pronouns) from order line item properties.

Pure data extraction utilities - no service calls, no dependencies.
These functions work on already-extracted property dictionaries.
"""
from typing import Dict, List, Tuple


def extract_birthday_with_name(properties: List[Dict[str, str]]) -> List[Tuple[str, str, str]]:
    """
    Extract birthdays with associated names from properties.
    
    Args:
        properties: List of custom attribute dictionaries with 'key' and 'value' keys
        
    Returns:
        List of (birthday, first_name, last_name) tuples
    """
    birthday = None
    first_name = ""
    last_name = ""
    
    for prop in properties:
        key = prop.get("key", "").lower()
        value = prop.get("value", "").strip()
        
        if "date of birth" in key and value:
            birthday = value
        elif "first name" in key and value and not first_name:
            first_name = value
        elif "last name" in key and value and not last_name:
            last_name = value
    
    if birthday:
        return [(birthday, first_name, last_name)]
    return []


def extract_pronouns_with_name(properties: List[Dict[str, str]]) -> List[Tuple[str, str, str]]:
    """
    Extract pronouns with associated names from properties.
    
    Args:
        properties: List of custom attribute dictionaries with 'key' and 'value' keys
        
    Returns:
        List of (pronouns_lowercase, first_name, last_name) tuples
    """
    pronouns = None
    first_name = ""
    last_name = ""
    
    for prop in properties:
        key = prop.get("key", "").lower()
        value = prop.get("value", "").strip()
        
        if "pronouns" in key and value:
            # Lowercase the pronouns value
            pronouns = value.lower()
        elif "first name" in key and value and not first_name:
            first_name = value
        elif "last name" in key and value and not last_name:
            last_name = value
    
    if pronouns:
        return [(pronouns, first_name, last_name)]
    return []
