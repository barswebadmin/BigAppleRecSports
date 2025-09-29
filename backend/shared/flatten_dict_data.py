"""
Utility function to flatten nested dictionary data
Mirrors the flattenProductData_ function from GAS project
"""

from typing import Dict, Any


def flatten_dict_data(
    obj: Dict[str, Any], result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Recursively flatten a nested dictionary structure

    Args:
        obj: The dictionary to flatten
        result: The result dictionary to accumulate flattened key-value pairs

    Returns:
        Dict with all nested keys flattened to top level

    Example:
        Input: {"a": {"b": 1}, "c": 2}
        Output: {"a.b": 1, "c": 2}
    """
    if result is None:
        result = {}

    for key, value in obj.items():
        if isinstance(value, dict) and value is not None:
            # Recursively flatten nested dictionaries
            flatten_dict_data(value, result)
        else:
            # Add non-dict values directly to result
            result[key] = value

    return result


def flatten_dict_data_with_prefix(
    obj: Dict[str, Any], result: Dict[str, Any], prefix: str = ""
) -> Dict[str, Any]:
    """
    Recursively flatten a nested dictionary structure with dot notation keys

    Args:
        obj: The dictionary to flatten
        result: The result dictionary to accumulate flattened key-value pairs
        prefix: The current key prefix for nested structures

    Returns:
        Dict with all nested keys flattened using dot notation

    Example:
        Input: {"a": {"b": 1}, "c": 2}
        Output: {"a.b": 1, "c": 2}
    """
    if result is None:
        result = {}

    for key, value in obj.items():
        new_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict) and value is not None:
            # Recursively flatten nested dictionaries
            flatten_dict_data_with_prefix(value, result, new_key)
        else:
            # Add non-dict values with the constructed key
            result[new_key] = value

    return result


