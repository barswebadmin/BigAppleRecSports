#!/usr/bin/env python3
"""
Dictionary utility functions for flattening, comparing, and navigating nested structures.
"""

import json
import sys
from typing import Dict, Any, List, Optional, Union


def get_nested_value(
    data: Union[Dict[str, Any], List[Any]], 
    path: Union[str, List[Union[str, int]]]
) -> Optional[Any]:
    """Get nested value from dict or list using dot notation path or list of keys/indices.
    
    Supports both string paths (dot notation) and list paths (with string keys and int indices).
    Can navigate through both dictionaries and lists.
    
    Args:
        data: Dictionary or list to navigate
        path: Either:
            - Dot-notation string path (e.g., "request_model.field" or "subAccountTypeKey")
            - List of keys/indices (e.g., ["data", "items", 0] for dict["data"]["items"][0])
        
    Returns:
        Value at path, or None if path doesn't exist
    """
    # Normalize path to list format
    if isinstance(path, str):
        keys = path.split(".") if path else []
    else:
        keys = path if path else []
    
    # Handle empty path
    if not keys:
        return data if data is not None else None
    
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key) if key in current else None
            if current is None:
                return None
        elif isinstance(current, list) and isinstance(key, int):
            if 0 <= key < len(current):
                current = current[key]
            else:
                return None
        else:
            return None
    
    return current


def set_nested_value(data: Dict[str, Any], path: str, value: Any) -> None:
    """Set nested value in dict using dot notation path.
    
    Creates intermediate dictionaries if they don't exist.
    
    Args:
        data: Dictionary to modify
        path: Dot-notation path (e.g., "a.b.c")
        value: Value to set
    """
    keys = path.split(".")
    current = data
    for k in keys[:-1]:
        if k not in current or not isinstance(current[k], dict):
            current[k] = {}
        current = current[k]
    current[keys[-1]] = value


def flatten_dict_data(
    obj: Dict[str, Any], result: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """
    Recursively flatten a nested dictionary structure.

    Args:
        obj: The dictionary to flatten
        result: Optional result dictionary to accumulate flattened key-value pairs.
                If None, a new dict is created.

    Returns:
        Dict with all nested keys flattened to top level

    Example:
        Input: {"a": {"b": 1}, "c": 2}
        Output: {"b": 1, "c": 2}
    """
    if result is None:
        result = {}

    for key, value in obj.items():
        if isinstance(value, dict) and value is not None:
            flatten_dict_data(value, result)
        else:
            result[key] = value

    return result


def flatten_dict_data_with_prefix(
    obj: Dict[str, Any], result: Dict[str, Any] | None = None, prefix: str = ""
) -> Dict[str, Any]:
    """
    Recursively flatten a nested dictionary structure with dot notation keys.

    Args:
        obj: The dictionary to flatten
        result: Optional result dictionary to accumulate flattened key-value pairs.
                If None, a new dict is created.
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
            flatten_dict_data_with_prefix(value, result, new_key)
        else:
            result[new_key] = value

    return result


def check_dict_equivalence(obj1: Any, obj2: Any, path: str = "") -> List[str]:
    """
    Recursively compare two objects and return list of differences.
    Dict key ordering is ignored. List element ordering is compared by index.
    
    Args:
        obj1: First object to compare
        obj2: Second object to compare
        path: Current path in the object hierarchy (for error messages)
    
    Returns:
        List of difference strings. Empty list if objects are equivalent.
    """
    differences = []
    
    if type(obj1) != type(obj2):
        differences.append(f"{path}: Type mismatch - {type(obj1).__name__} vs {type(obj2).__name__}")
        return differences
    
    if isinstance(obj1, dict):
        keys1 = set(obj1.keys())
        keys2 = set(obj2.keys())
        
        missing_in_2 = keys1 - keys2
        missing_in_1 = keys2 - keys1
        
        for key in missing_in_2:
            differences.append(f"{path}.{key}: Present in obj1, missing in obj2")
        
        for key in missing_in_1:
            differences.append(f"{path}.{key}: Missing in obj1, present in obj2")
        
        for key in keys1 & keys2:
            new_path = f"{path}.{key}" if path else key
            differences.extend(check_dict_equivalence(obj1[key], obj2[key], new_path))
    
    elif isinstance(obj1, list):
        if len(obj1) != len(obj2):
            differences.append(f"{path}: List length mismatch - {len(obj1)} vs {len(obj2)}")
        
        for idx in range(min(len(obj1), len(obj2))):
            differences.extend(check_dict_equivalence(obj1[idx], obj2[idx], f"{path}[{idx}]"))
    
    else:
        if obj1 != obj2:
            differences.append(f"{path}: Value mismatch - '{obj1}' vs '{obj2}'")
    
    return differences


def main():
    """CLI tool for comparing two JSON files."""
    if len(sys.argv) < 3:
        print("Usage: python dict_utils.py file1.json file2.json")
        return 1
    
    file1_path = sys.argv[1]
    file2_path = sys.argv[2]
    
    print(f"Comparing:\n  File 1: {file1_path}\n  File 2: {file2_path}\n")
    
    with open(file1_path) as f1:
        data1 = json.load(f1)
    
    with open(file2_path) as f2:
        data2 = json.load(f2)
    
    differences = check_dict_equivalence(data1, data2)
    
    if not differences:
        print("✅ Files are identical!")
        return 0
    
    print(f"❌ Found {len(differences)} difference(s):\n")
    for diff in differences:
        print(f"  • {diff}")
    
    return 1


if __name__ == '__main__':
    sys.exit(main())

