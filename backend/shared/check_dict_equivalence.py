#!/usr/bin/env python3
"""
Check equivalence of two dictionary structures and identify differences.
"""
import json
import sys
from typing import Any, List


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
        # Check for missing keys
        keys1 = set(obj1.keys())
        keys2 = set(obj2.keys())
        
        missing_in_2 = keys1 - keys2
        missing_in_1 = keys2 - keys1
        
        for key in missing_in_2:
            differences.append(f"{path}.{key}: Present in obj1, missing in obj2")
        
        for key in missing_in_1:
            differences.append(f"{path}.{key}: Missing in obj1, present in obj2")
        
        # Compare common keys
        for key in keys1 & keys2:
            new_path = f"{path}.{key}" if path else key
            differences.extend(check_dict_equivalence(obj1[key], obj2[key], new_path))
    
    elif isinstance(obj1, list):
        if len(obj1) != len(obj2):
            differences.append(f"{path}: List length mismatch - {len(obj1)} vs {len(obj2)}")
        
        for idx in range(min(len(obj1), len(obj2))):
            differences.extend(check_dict_equivalence(obj1[idx], obj2[idx], f"{path}[{idx}]"))
    
    else:
        # Primitive types
        if obj1 != obj2:
            differences.append(f"{path}: Value mismatch - '{obj1}' vs '{obj2}'")
    
    return differences


def main():
    if len(sys.argv) < 3:
        print("Usage: python check_dict_equivalence.py file1.json file2.json")
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

