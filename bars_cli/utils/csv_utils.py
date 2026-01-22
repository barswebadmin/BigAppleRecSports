"""CSV reading and writing utilities (I/O only, no formatting)."""

import csv
from typing import Any, Dict, List, Optional, Tuple

import click

from bars_cli.commands.shopify._shared.shopify_formatters import (
    get_order_csv_headers,
    order_to_csv_row,
)


def read_csv_file(file_path: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Read CSV file and return headers and rows.
    
    Args:
        file_path: Path to CSV file
    
    Returns:
        Tuple of (headers, rows)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = list(reader.fieldnames or [])
        rows = list(reader)
    
    return headers, rows


def write_csv_to_file(
    headers: List[str],
    rows: List[List[str]],
    file_path: str
) -> None:
    """Write CSV data to a file.
    
    Args:
        headers: List of column header names
        rows: List of row data (each row is a list of strings)
        file_path: Path to output file
    """
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def write_csv_to_stdout(
    headers: List[str],
    rows: List[List[str]]
) -> None:
    """Write CSV data to stdout.
    
    Args:
        headers: List of column header names
        rows: List of row data (each row is a list of strings)
    """
    writer = csv.writer(click.get_text_stream("stdout"))
    writer.writerow(headers)
    writer.writerows(rows)


def write_results_csv(results: List[Dict[str, Any]], output_path: str) -> None:
    """
    Write analysis results to CSV file.
    
    Args:
        results: List of analysis result dictionaries
        output_path: Path to output CSV file
    """
    if not results:
        click.echo("No results to write", err=True)
        return
    
    # Get all unique keys from results
    fieldnames = set()
    for result in results:
        fieldnames.update(result.keys())
    
    fieldnames = sorted(fieldnames)
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def output_order_csv(order: Any, csv_file: Optional[str] = None) -> None:
    """Output order as CSV.
    
    Args:
        order: Order object (sgqlc Type instance)
        csv_file: Optional path to output file (if None, writes to stdout)
    """
    # Convert order to dict format for CSV
    order_dict = order.__json_data__ if hasattr(order, '__json_data__') else {}
    
    headers = get_order_csv_headers()
    row = order_to_csv_row(order_dict)
    
    if csv_file:
        write_csv_to_file(headers, [row], csv_file)
        click.echo(f"CSV written to {csv_file}", err=True)
    else:
        write_csv_to_stdout(headers, [row])
