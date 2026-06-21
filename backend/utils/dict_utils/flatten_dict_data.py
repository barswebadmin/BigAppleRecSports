"""Recursively flatten nested dictionary structures with dot notation keys."""

import json
from typing import Any, Dict, Optional


def flatten_dict_data(
    obj: Dict[str, Any], result: Optional[Dict[str, Any]] = None, prefix: str = ""
) -> Dict[str, Any]:
    """
    Recursively flatten a nested dictionary structure with dot notation keys.
    Lists are JSON-encoded for CSV compatibility.

    Args:
        obj: The dictionary to flatten
        result: The result dictionary to accumulate flattened key-value pairs (optional)
        prefix: The current key prefix for nested structures (optional, defaults to "")

    Returns:
        Dict with all nested keys flattened using dot notation

    Example:
        Input: {"a": {"b": 1}, "c": [2, 3]}
        Output: {"a.b": 1, "c": "[2, 3]"}
    """
    if result is None:
        result = {}

    for key, value in obj.items():
        new_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict) and value is not None:
            flatten_dict_data(value, result, new_key)
        elif isinstance(value, list):
            if not value:
                result[new_key] = ""
            elif all(isinstance(item, (str, int, float, bool, type(None))) for item in value):
                result[new_key] = json.dumps(value)
            else:
                result[new_key] = json.dumps(value, default=str)
        else:
            result[new_key] = value

    return result
