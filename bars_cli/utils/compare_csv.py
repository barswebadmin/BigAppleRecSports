"""Compare CSV files command.

This is a general utility command, not Shopify-specific.
Compares two CSV files and shows differences.

BACKEND SERVICE STATUS:
- ❌ MISSING: CSV comparison logic - Needs to be created (or use existing library)
- ✅ EXISTS: bars-scripts/compare_csv.py - Has reference implementation
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
    
    console = Console()
    json_output, should_display = get_display_context(ctx)
    
    # PSEUDOCODE:
    # 1. Read both CSV files
    # 2. Parse CSV data (handle headers, rows)
    # 3. Compare files:
    #    - If --key-column: Match rows by key column value
    #    - Otherwise: Compare row-by-row
    #    - Ignore columns specified in --ignore-columns
    # 4. Identify differences:
    #    - Rows only in file1 (removed)
    #    - Rows only in file2 (added)
    #    - Rows in both but with different values (modified)
    #    - Rows in both with same values (unchanged)
    # 5. Display results:
    #    - Summary statistics
    #    - Table showing differences
    #    - Highlight changed cells
    
    console.print(f"[yellow]⚠️  TODO: Implement CSV comparison logic[/yellow]")
    console.print(f"  Would read: {file1} and {file2}")
    if key_column:
        console.print(f"  Would use key column: {key_column}")
    if ignore_columns:
        console.print(f"  Would ignore columns: {', '.join(ignore_columns)}")
    console.print(f"  Would compare rows and show differences")
    
    console.print("\n[green]✅ CSV comparison complete (skeleton implementation)[/green]\n")
