#!/usr/bin/env python3
"""
Compare two CSV files and report differences.

Usage:
    python bars-scripts/compare_csv.py file1.csv file2.csv
    python bars-scripts/compare_csv.py file1.csv file2.csv --json
"""

import sys
import argparse
import csv
import json
import html
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict


def read_csv_file(filepath: str) -> Tuple[List[str], List[List[str]]]:
    """Read CSV file and return headers and rows."""
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader, [])
        rows = list(reader)
    return headers, rows


def extract_order_id(order_number: str) -> str:
    """Extract numerical ID from order number (strip leading #)."""
    if not order_number:
        return ''
    return order_number.strip().lstrip('#').strip()


def normalize_header(header: str) -> str:
    """Normalize header by decoding HTML entities for comparison."""
    if not header:
        return ''
    # Decode HTML entities (e.g., &#39; -> ', &quot; -> ")
    return html.unescape(header.strip())


def normalize_phone_number(phone: str) -> str:
    """Normalize phone number for comparison: strip leading 1, remove spaces and special chars."""
    if not phone:
        return ''
    
    # Remove all non-digit characters
    digits_only = ''.join(c for c in phone if c.isdigit())
    
    # Strip leading 1 (US country code)
    if digits_only.startswith('1') and len(digits_only) == 11:
        digits_only = digits_only[1:]
    
    return digits_only


def normalize_value(value: str, column_name: str) -> str:
    """Normalize value for comparison, handling special cases per column."""
    # Normalize header name for comparison (handle HTML entities)
    normalized_column_name = normalize_header(column_name)
    
    # Case-insensitive check for Total Price
    if normalized_column_name.lower() == 'total price':
        # For Total Price: cast to float, treat null/empty as 0, compare numerically
        value = value.strip() if value else ''
        
        # Treat empty, null, none as 0
        if not value or value.lower() in ('null', 'none'):
            return '0.00'
        
        # Remove currency symbols and whitespace
        cleaned = value.replace('$', '').replace(',', '').strip()
        
        # Try to parse as float
        try:
            float_val = float(cleaned)
            # Return normalized string representation (consistent decimal places)
            return f"{float_val:.2f}"
        except (ValueError, TypeError):
            # If parsing fails, return original (will be flagged as different)
            return value
    
    # Phone number columns
    if (normalized_column_name == 'Phone' or 
        normalized_column_name == 'Line items: Custom attributes Best Contact Number (Cell Phone Number Preferred)'):
        return normalize_phone_number(value)
    
    return value.strip() if value else ''


def build_keyed_dict(headers: List[str], rows: List[List[str]], key_column: str = 'Order Number', header_normalization_map: Optional[Dict[str, str]] = None) -> Tuple[Dict[str, Dict[str, str]], List[str]]:
    """Build a dictionary keyed by order ID from CSV data.
    
    Args:
        headers: List of header strings
        rows: List of row data
        key_column: Name of the column to use as key (will be normalized for lookup)
        header_normalization_map: Optional mapping from normalized header to original header
    """
    keyed_dict = {}
    missing_key_rows = []
    
    # Normalize headers for lookup
    normalized_headers = [normalize_header(h) for h in headers]
    normalized_key_column = normalize_header(key_column)
    
    # Find key column index using normalized headers
    try:
        key_col_idx = normalized_headers.index(normalized_key_column)
    except ValueError:
        # Try case-insensitive search
        key_col_idx = None
        for i, h in enumerate(normalized_headers):
            if h.lower() == normalized_key_column.lower():
                key_col_idx = i
                break
        
        if key_col_idx is None:
            raise ValueError(f"Key column '{key_column}' (normalized: '{normalized_key_column}') not found in headers: {headers}")
    
    for row_idx, row in enumerate(rows):
        # Pad row to match headers length
        while len(row) < len(headers):
            row.append('')
        
        # Extract order ID
        order_number = row[key_col_idx].strip() if key_col_idx < len(row) else ''
        order_id = extract_order_id(order_number)
        
        if not order_id:
            missing_key_rows.append(f"Row {row_idx + 2}")  # +2 because row 0 is header, and we're 1-indexed
            continue
        
        # Build row object (dict keyed by normalized header names for consistent comparison)
        row_obj = {}
        for col_idx, header in enumerate(headers):
            value = row[col_idx].strip() if col_idx < len(row) else ''
            # Use normalized header as key for consistent comparison across files
            normalized_header = normalized_headers[col_idx]
            row_obj[normalized_header] = value
        
        keyed_dict[order_id] = row_obj
    
    return keyed_dict, missing_key_rows


def compare_csvs(file1: str, file2: str) -> Dict[str, Any]:
    """Compare two CSV files by order ID and return detailed differences."""
    headers1, rows1 = read_csv_file(file1)
    headers2, rows2 = read_csv_file(file2)
    
    # Normalize headers (strip whitespace)
    headers1 = [h.strip() for h in headers1]
    headers2 = [h.strip() for h in headers2]
    
    # Create normalized header mappings for comparison
    normalized_headers1 = [normalize_header(h) for h in headers1]
    normalized_headers2 = [normalize_header(h) for h in headers2]
    
    # Create mapping from normalized to original headers (for display)
    # Use the first occurrence if there are duplicates
    norm_to_orig1 = {norm: orig for orig, norm in zip(headers1, normalized_headers1)}
    norm_to_orig2 = {norm: orig for orig, norm in zip(headers2, normalized_headers2)}
    
    # Compare headers using normalized versions
    header_differences = []
    normalized_headers1_set = set(normalized_headers1)
    normalized_headers2_set = set(normalized_headers2)
    
    # Headers only in file1 (using normalized comparison)
    only_in_file1_norm = normalized_headers1_set - normalized_headers2_set
    for norm_header in sorted(only_in_file1_norm):
        orig_header = norm_to_orig1.get(norm_header, norm_header)
        header_differences.append({
            'type': 'header',
            'column_name': orig_header,
            'file1_value': orig_header,
            'file2_value': '<missing>'
        })
    
    # Headers only in file2 (using normalized comparison)
    only_in_file2_norm = normalized_headers2_set - normalized_headers1_set
    for norm_header in sorted(only_in_file2_norm):
        orig_header = norm_to_orig2.get(norm_header, norm_header)
        header_differences.append({
            'type': 'header',
            'column_name': orig_header,
            'file1_value': '<missing>',
            'file2_value': orig_header
        })
    
    # Build keyed dictionaries (will use normalized headers internally)
    try:
        dict1, missing_keys1 = build_keyed_dict(headers1, rows1)
        dict2, missing_keys2 = build_keyed_dict(headers2, rows2)
    except ValueError as e:
        return {
            'error': str(e),
            'file1': file1,
            'file2': file2,
            'total_differences': 0,
            'header_differences': header_differences,
            'row_breakdown': {},
            'column_breakdown': {},
            'differences': []
        }
    
    # Find all order IDs
    all_ids = set(dict1.keys()) | set(dict2.keys())
    
    # Compare row objects
    differences = []
    total_differences = 0
    row_differences = defaultdict(int)  # order_id -> count
    col_differences = defaultdict(int)  # col_name -> count (using normalized headers)
    
    # All normalized headers (union of both) - use normalized for comparison
    all_normalized_headers = sorted(normalized_headers1_set | normalized_headers2_set)
    
    for order_id in sorted(all_ids):
        row1 = dict1.get(order_id)
        row2 = dict2.get(order_id)
        
        if row1 is None:
            # Order only in file2
            differences.append({
                'type': 'missing_order',
                'order_id': order_id,
                'column_name': None,
                'file1_value': '<missing>',
                'file2_value': f"Order #{order_id} present"
            })
            total_differences += 1
            row_differences[order_id] = len(all_normalized_headers)
            continue
        
        if row2 is None:
            # Order only in file1
            differences.append({
                'type': 'missing_order',
                'order_id': order_id,
                'column_name': None,
                'file1_value': f"Order #{order_id} present",
                'file2_value': '<missing>'
            })
            total_differences += 1
            row_differences[order_id] = len(all_normalized_headers)
            continue
        
        # Compare row objects field by field using normalized headers
        row_diff_count = 0
        for norm_header in all_normalized_headers:
            # Skip "Updated at" column - ignore differences
            if norm_header.lower() == 'updated at':
                continue
            
            val1_raw = row1.get(norm_header, '')
            val2_raw = row2.get(norm_header, '')
            
            # Normalize values for comparison (use normalized header name)
            val1_normalized = normalize_value(val1_raw, norm_header)
            val2_normalized = normalize_value(val2_raw, norm_header)
            
            if val1_normalized != val2_normalized:
                # Get original header name for display (prefer file1, fallback to file2, then normalized)
                display_header = norm_to_orig1.get(norm_header) or norm_to_orig2.get(norm_header) or norm_header
                
                differences.append({
                    'type': 'cell',
                    'order_id': order_id,
                    'column_name': display_header,
                    'file1_value': val1_raw,
                    'file2_value': val2_raw
                })
                total_differences += 1
                row_diff_count += 1
                # Use display header (original) for column breakdown
                col_differences[display_header] += 1
        
        if row_diff_count > 0:
            row_differences[order_id] = row_diff_count
    
    return {
        'total_differences': total_differences,
        'file1': file1,
        'file2': file2,
        'file1_rows': len(rows1),
        'file2_rows': len(rows2),
        'file1_orders': len(dict1),
        'file2_orders': len(dict2),
        'file1_missing_keys': missing_keys1,
        'file2_missing_keys': missing_keys2,
        'header_differences': header_differences,
        'row_breakdown': dict(row_differences),
        'column_breakdown': dict(col_differences),
        'differences': differences
    }


def format_differences(result: Dict[str, Any], json_output: bool = False) -> str:
    """Format differences for display."""
    if json_output:
        return json.dumps(result, indent=2)
    
    output = []
    output.append("=" * 80)
    output.append("CSV Comparison Report")
    output.append("=" * 80)
    output.append(f"\nFile 1: {result['file1']}")
    output.append(f"  Rows: {result['file1_rows']}, Orders: {result.get('file1_orders', 'N/A')}")
    output.append(f"\nFile 2: {result['file2']}")
    output.append(f"  Rows: {result['file2_rows']}, Orders: {result.get('file2_orders', 'N/A')}")
    
    # Missing keys warning
    if result.get('file1_missing_keys'):
        output.append(f"\n⚠️  File 1 rows missing Order Number: {', '.join(result['file1_missing_keys'])}")
    if result.get('file2_missing_keys'):
        output.append(f"⚠️  File 2 rows missing Order Number: {', '.join(result['file2_missing_keys'])}")
    
    output.append("\n" + "=" * 80)
    
    # Header differences
    if result.get('header_differences'):
        output.append(f"\n📋 Header Differences: {len(result['header_differences'])}")
        output.append("-" * 80)
        for diff in result['header_differences']:
            output.append(f"  Column '{diff['column_name']}':")
            output.append(f"    File 1: {diff['file1_value']}")
            output.append(f"    File 2: {diff['file2_value']}")
        output.append("")
    
    # Total differences
    output.append(f"\n📊 Total Differences: {result['total_differences']}")
    output.append("")
    
    # Row breakdown (by order ID)
    if result['row_breakdown']:
        output.append("📋 Differences by Order ID:")
        output.append("-" * 80)
        for order_id in sorted(result['row_breakdown'].keys(), key=lambda x: int(x) if x.isdigit() else 0):
            count = result['row_breakdown'][order_id]
            output.append(f"  Order #{order_id}: {count} difference(s)")
        output.append("")
    
    # Column breakdown
    if result['column_breakdown']:
        output.append("📊 Differences by Column:")
        output.append("-" * 80)
        for col_name in sorted(result['column_breakdown'].keys(), key=lambda x: result['column_breakdown'][x], reverse=True):
            count = result['column_breakdown'][col_name]
            output.append(f"  {col_name}: {count} difference(s)")
        output.append("")
    
    # Detailed differences - sort by column (most changes first), then by order ID
    if result['differences']:
        output.append("🔍 Detailed Differences (Cell by Cell):")
        output.append("-" * 80)
        
        # Sort differences: first by column change count (descending), then by order ID
        column_counts = result['column_breakdown']
        sorted_differences = sorted(
            result['differences'],
            key=lambda d: (
                -column_counts.get(d.get('column_name', ''), 0),  # Negative for descending
                int(d.get('order_id', '0')) if d.get('order_id', '').isdigit() else 0
            )
        )
        
        for diff in sorted_differences:
            if diff['type'] == 'header':
                output.append(f"\nHeader - {diff['column_name']}:")
            elif diff['type'] == 'missing_order':
                output.append(f"\nOrder #{diff['order_id']} - Missing in one file:")
            else:
                output.append(f"\nOrder #{diff['order_id']}, Column '{diff['column_name']}':")
            
            output.append(f"  File 1: {repr(diff['file1_value'])}")
            output.append(f"  File 2: {repr(diff['file2_value'])}")
    
    return '\n'.join(output)


def main():
    parser = argparse.ArgumentParser(
        description="Compare two CSV files and report differences"
    )
    parser.add_argument(
        "file1",
        help="First CSV file to compare"
    )
    parser.add_argument(
        "file2",
        help="Second CSV file to compare"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    
    args = parser.parse_args()
    
    try:
        result = compare_csvs(args.file1, args.file2)
        output = format_differences(result, json_output=args.json)
        print(output)
        
        # Exit with error code if differences found
        if result['total_differences'] > 0:
            return 1
        return 0
        
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

