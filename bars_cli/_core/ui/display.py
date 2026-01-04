"""Display utilities for formatted CLI output."""

import json
from typing import Any, Dict, List, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.theme import Theme


# Custom JSON theme for rich Console
JSON_THEME = Theme({
    "json.key": "bold medium_purple",
    "json.str": "cyan",
    "json.number": "bright_yellow",
    "json.bool_true": "dark_sea_green4",
    "json.bool_false": "dark_red",
    "json.null": "dim",
})


def display_json(
    data: Any,
    *,
    indent: bool = True,
    use_color: bool = True,
    stream = None
) -> None:
    """Display JSON data with syntax highlighting.
    
    Args:
        data: Data to display (dict, list, or JSON string)
        indent: Whether to pretty-print with indentation
        use_color: Whether to use color syntax highlighting
        stream: Output stream (defaults to stdout)
    """
    if stream is None:
        stream = click.get_text_stream("stdout")
    
    # Convert to JSON string if needed
    if isinstance(data, str):
        json_str = data
        # Validate it's valid JSON
        try:
            json.loads(json_str)
        except json.JSONDecodeError:
            # Not valid JSON, output as plain text
            stream.write(data)
            return
    else:
        json_str = json.dumps(data)
    
    # Display with Rich if color enabled
    if use_color:
        try:
            console = Console(file=stream, theme=JSON_THEME)
            if indent:
                console.print_json(json=json_str, indent=2)
            else:
                console.print_json(json=json_str, indent=None)
            return
        except Exception:
            pass  # Fall through to plain JSON
    
    # Fallback to plain JSON
    if isinstance(data, str):
        try:
            obj = json.loads(data)
            if indent:
                stream.write(json.dumps(obj, indent=2))
            else:
                stream.write(json.dumps(obj, separators=(",", ":")))
        except json.JSONDecodeError:
            stream.write(data)
    else:
        if indent:
            stream.write(json.dumps(data, indent=2))
        else:
            stream.write(json.dumps(data, separators=(",", ":")))


def display_table(
    rows: List[Dict[str, Any]],
    *,
    columns: Optional[List[str]] = None,
    show_header: bool = True,
    title: Optional[str] = None,
    stream = None
) -> None:
    """Display data as a formatted table using Rich.
    
    Args:
        rows: List of dictionaries containing row data
        columns: List of column names to display (defaults to keys from first row)
        show_header: Whether to show column headers
        title: Optional table title
        stream: Output stream (defaults to stdout)
    
    Example:
        rows = [
            {"name": "John", "age": 30, "city": "NYC"},
            {"name": "Jane", "age": 25, "city": "LA"},
        ]
        display_table(rows, columns=["name", "age"])
    """
    if not rows:
        return
    
    if stream is None:
        stream = click.get_text_stream("stdout")
    
    console = Console(file=stream)
    
    # Auto-detect columns from first row if not provided
    if columns is None:
        columns = list(rows[0].keys())
    
    # Create Rich table
    table = Table(
        show_header=show_header,
        header_style="bold cyan",
        title=title,
        title_style="bold magenta"
    )
    
    # Add columns
    for col in columns:
        table.add_column(col, overflow="fold")
    
    # Add rows
    for row in rows:
        values = [str(row.get(col, "")) for col in columns]
        table.add_row(*values)
    
    # Print table
    console.print(table)


def display_key_value_pairs(
    pairs: Dict[str, Any],
    *,
    key_color: str = "cyan",
    value_color: Optional[str] = None,
    stream = None
) -> None:
    """Display key-value pairs in a formatted list.
    
    Args:
        pairs: Dictionary of key-value pairs
        key_color: Color for keys (default: cyan)
        value_color: Color for values (default: None)
        stream: Output stream (defaults to stdout)
    
    Example:
        pairs = {"Name": "John Doe", "Email": "john@example.com"}
        display_key_value_pairs(pairs)
    """
    if stream is None:
        stream = click.get_text_stream("stdout")
    
    max_key_length = max(len(str(k)) for k in pairs.keys()) if pairs else 0
    
    for key, value in pairs.items():
        key_str = click.style(f"{key:>{max_key_length}}", fg=key_color, bold=True)
        if value_color:
            value_str = click.style(str(value), fg=value_color)
        else:
            value_str = str(value)
        stream.write(f"{key_str}: {value_str}\n")

