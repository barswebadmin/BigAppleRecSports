#!/usr/bin/env python3
"""CLI tool for comparing two JSON files."""

import json
import sys

from .check_dict_equivalence import check_dict_equivalence


def main():
    """CLI tool for comparing two JSON files."""
    if len(sys.argv) < 3:
        print("Usage: python -m shared_utilities.dict_utils file1.json file2.json")
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
