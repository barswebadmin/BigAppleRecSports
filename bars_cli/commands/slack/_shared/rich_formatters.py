"""Rich-based formatters for Slack entities with common formatting patterns."""

from typing import List, Callable, Optional, Any, Dict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from bars_cli._core.ui.display import create_info_table, create_text_panel


def format_grouped_list(
    items: List[Any],
    *,
    title: str,
    group_func: Callable[[Any], str],
    format_item_func: Callable[[Any], str],
    console: Optional[Console] = None,
    empty_message: str = "No items found."
) -> None:
    """Format a list of items grouped by a function, displayed as Rich tables.
    
    Common pattern for formatting lists with grouping (e.g., active/deleted users,
    public/private channels).
    
    Args:
        items: List of items to format
        title: Main title for the output
        group_func: Function that returns group name for each item
        format_item_func: Function that formats each item as a string
        console: Optional Rich Console instance (creates new if None)
        empty_message: Message to display if items list is empty
    """
    if console is None:
        console = Console()
    
    if not items:
        console.print(f"[dim]{empty_message}[/dim]")
        return
    
    # Group items
    groups: Dict[str, List[Any]] = {}
    for item in items:
        group_name = group_func(item)
        if group_name not in groups:
            groups[group_name] = []
        groups[group_name].append(item)
    
    # Display header
    console.print(f"\n[bold cyan]{title} ({len(items)} total):[/bold cyan]\n")
    
    # Display each group
    for group_name, group_items in groups.items():
        console.print(f"[bold]{group_name}:[/bold]")
        for item in sorted(group_items, key=lambda x: format_item_func(x)):
            console.print(f"  • {format_item_func(item)}")
        console.print()


def format_key_value_details(
    data: Dict[str, Any],
    *,
    title: str,
    field_mappings: List[tuple],
    console: Optional[Console] = None,
    show_empty: bool = False
) -> None:
    """Format key-value details as a Rich info table.
    
    Common pattern for displaying entity details (e.g., user, group, channel).
    
    Args:
        data: Dictionary containing the data
        title: Title for the details section
        field_mappings: List of (display_name, data_key, formatter_func) tuples.
            formatter_func is optional and can be None for direct value access.
        console: Optional Rich Console instance (creates new if None)
        show_empty: Whether to show fields with empty/None values
    """
    if console is None:
        console = Console()
    
    rows = []
    for display_name, data_key, formatter in field_mappings:
        value = data.get(data_key) if isinstance(data, dict) else getattr(data, data_key, None)
        
        if formatter:
            value = formatter(value)
        else:
            value = value or 'N/A'
        
        if value and value != 'N/A' or show_empty:
            rows.append((display_name, value))
    
    if rows:
        table = create_info_table(rows, title=title, show_header=False)
        console.print(table)
        console.print()


def format_list_with_table(
    items: List[Any],
    *,
    title: str,
    columns: List[tuple],
    format_row_func: Callable[[Any], List[str]],
    console: Optional[Console] = None,
    empty_message: str = "No items found."
) -> None:
    """Format a list of items as a Rich table.
    
    Common pattern for displaying tabular data (e.g., line items, transactions).
    
    Args:
        items: List of items to display
        title: Table title
        columns: List of (column_name, justify) tuples (justify can be "left", "right", "center", or None)
        format_row_func: Function that takes an item and returns a list of string values for the row
        console: Optional Rich Console instance (creates new if None)
        empty_message: Message to display if items list is empty
    """
    if console is None:
        console = Console()
    
    if not items:
        console.print(f"[dim]{empty_message}[/dim]")
        return
    
    table = Table(title=title, show_header=True)
    
    for col_name, justify in columns:
        table.add_column(col_name, justify=justify)
    
    for item in items:
        row_values = format_row_func(item)
        table.add_row(*row_values)
    
    console.print(table)
    console.print()

