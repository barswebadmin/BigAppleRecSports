"""Compare CSV files command.

This is a general utility command, not Shopify-specific.
Compares two CSV files and shows differences.

BACKEND SERVICE STATUS:
- ✅ EXISTS: backend/shared/csv/compare.py - Has comparison logic
- ✅ EXISTS: Python csv module - Standard library for CSV parsing

CLI RESPONSIBILITIES:
- Accept two CSV file paths
- Display comparison results (differences, matches)
- Support output formats (formatted table, JSON)
- Show summary statistics

BACKEND RESPONSIBILITIES:
- Parse both CSV files
- Compare rows/columns
- Identify differences (added, removed, modified rows)
- Return structured comparison results
- This is a general utility, not Shopify-specific
"""
from typing import Optional

import click
from rich.console import Console

from bars_cli._core.decorators.handle_display_options import handle_display_options


@click.command('compare-csv')
@handle_display_options(display=True, exit_on_error=True)
@click.argument('file1', type=click.Path(exists=True))
@click.argument('file2', type=click.Path(exists=True))
@click.option('--key-column', type=str, help='Column name to use as key for comparison')
@click.option('--ignore-columns', type=str, multiple=True, help='Column names to ignore in comparison')
@click.pass_context
def compare_csv_cmd(
    ctx: click.Context,
    file1: str,
    file2: str,
    key_column: Optional[str] = None,
    ignore_columns: Optional[tuple] = None
) -> None:
    """
    Compare two CSV files and show differences.
    
    FILE1: Path to first CSV file
    FILE2: Path to second CSV file
    
    Examples:
      bars utils compare-csv file1.csv file2.csv
      bars utils compare-csv file1.csv file2.csv --key-column order_number
      bars utils compare-csv file1.csv file2.csv --ignore-columns timestamp notes
      bars --json utils compare-csv file1.csv file2.csv
    """
    from bars_cli._core.context import get_display_context
    from bars_cli.backend_services.shared.csv.compare import compare_csvs, format_differences
    
    console = Console()
    json_output, should_display = get_display_context(ctx)
    
    try:
        # Call backend comparison logic
        result = compare_csvs(file1, file2)
        
        # Format and display results
        if json_output:
            # Return JSON output
            import json
            console.print(json.dumps(result, indent=2, default=str))
        else:
            # Use format_differences for formatted output
            formatted_output = format_differences(result, json_output=False)
            console.print(formatted_output)
        
    except Exception as e:
        console.print(f"[red]Error comparing CSV files: {e}[/red]")
        raise click.Abort()
