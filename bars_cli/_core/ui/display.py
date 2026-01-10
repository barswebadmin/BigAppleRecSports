"""Display utilities for formatted CLI output."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

import click
from rich import box
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
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


def format_datetime(dt_str: Optional[str]) -> str:
    """Format ISO datetime string to readable format.
    
    Args:
        dt_str: ISO datetime string (e.g., "2025-01-15T10:30:00Z")
        
    Returns:
        Formatted datetime string (e.g., "2025-01-15 10:30 AM UTC") or "N/A" if invalid
    """
    if not dt_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %I:%M %p %Z")
    except (ValueError, AttributeError):
        return dt_str


def _get_box_from_string(box_style: Optional[str]) -> Optional[box.Box]:
    """Convert box style string to Box object.
    
    Args:
        box_style: Box style name (e.g., "SIMPLE", "ROUNDED", "HEAVY") or None
        
    Returns:
        Box object or None if box_style is None
    """
    if box_style is None:
        return None
    
    # Convert to uppercase to match Rich constants
    box_name = box_style.upper()
    
    # Map common box style names to Rich Box constants
    box_mapping = {
        "SIMPLE": box.SIMPLE,
        "ROUNDED": box.ROUNDED,
        "HEAVY": box.HEAVY,
        "HEAVY_HEAD": box.HEAVY_HEAD,
        "HEAVY_EDGE": box.HEAVY_EDGE,
        "SIMPLE_HEAD": box.SIMPLE_HEAD,
        "SIMPLE_HEAVY": box.SIMPLE_HEAVY,
        "MINIMAL": box.MINIMAL,
        "MINIMAL_HEAVY_HEAD": box.MINIMAL_HEAVY_HEAD,
        "SQUARE": box.SQUARE,
        "SQUARE_DOUBLE_HEAD": box.SQUARE_DOUBLE_HEAD,
        "ASCII": box.ASCII,
        "ASCII2": box.ASCII2,
        "ASCII_DOUBLE_HEAD": box.ASCII_DOUBLE_HEAD,
    }
    
    # Try direct lookup first
    if box_name in box_mapping:
        return box_mapping[box_name]
    
    # Try getattr as fallback (for any other box constants)
    try:
        return getattr(box, box_name, None)
    except AttributeError:
        return None


def create_info_table(
    rows: list[tuple[str, str]],
    *,
    title: Optional[str] = None,
    show_header: bool = False,
    field_style: str = "bold",
    value_style: Optional[str] = None,
    box_style: Optional[str] = None,
    padding: tuple[int, int] = (0, 2)
) -> Table:
    """Create a Rich table for key-value information display.
    
    Args:
        rows: List of (field, value) tuples where both are strings
        title: Optional table title
        show_header: Whether to show column headers
        field_style: Style for field column (default: "bold")
        value_style: Optional style for value column
        box_style: Optional box style string (e.g., "SIMPLE", "ROUNDED", "HEAVY") or None for no box
        padding: Tuple of (vertical, horizontal) padding
        
    Returns:
        Configured Rich Table instance
    """
    box_obj = _get_box_from_string(box_style)
    
    table = Table(
        show_header=show_header,
        title=title,
        box=box_obj,
        padding=padding
    )
    
    table.add_column("Field", style=field_style)
    table.add_column("Value", style=value_style)
    
    for field, value in rows:
        table.add_row(str(field), str(value))
    
    return table


def create_panel(
    content: str,
    *,
    title: Optional[str] = None,
    border_style: str = "cyan"
) -> Panel:
    """Create a Rich Panel with text content.
    
    Args:
        content: Text content for the panel
        title: Optional panel title
        border_style: Border style color (default: "cyan")
        
    Returns:
        Configured Rich Panel instance
    """
    return Panel(content, title=title, border_style=border_style)


def create_text_panel(
    parts: Sequence[tuple[str, str | None]],
    *,
    title: Optional[str] = None,
    border_style: str = "cyan"
) -> Panel:
    """Create a Rich Panel with styled text parts.
    
    Args:
        parts: List of (text, style) tuples where style is optional
        title: Optional panel title
        border_style: Border style color (default: "cyan")
        
    Returns:
        Configured Rich Panel instance
        
    Example:
        parts = [
            ("Order #", "bold cyan"),
            ("1234", "cyan"),
            (" [CANCELLED]", "bold red")
        ]
        create_text_panel(parts, title="Order Details")
    """
    combined_text = Text()
    for text_str, style_str in parts:
        combined_text.append(text_str, style=style_str)
    return Panel(combined_text, title=title, border_style=border_style)


def display_json_syntax(
    data: Any,
    *,
    title: Optional[str] = None,
    theme: str = "monokai",
    line_numbers: bool = False,
    stream = None
) -> None:
    """Display JSON data with syntax highlighting using Rich Syntax.
    
    Args:
        data: Data to display (dict, list, or JSON string)
        title: Optional title above the syntax block
        theme: Syntax theme (default: "monokai")
        line_numbers: Whether to show line numbers
        stream: Output stream (defaults to stdout)
    """
    if stream is None:
        stream = click.get_text_stream("stdout")
    
    console = Console(file=stream)
    
    if isinstance(data, str):
        json_str = data
    else:
        json_str = json.dumps(data, indent=2)
    
    syntax = Syntax(json_str, "json", theme=theme, line_numbers=line_numbers)
    
    if title:
        console.print(f"[bold cyan]{title}[/bold cyan]")
    console.print(syntax)

