"""Display and rendering utilities for HTTP responses and JSON.

This module contains pure UI/rendering logic for formatting and displaying content.
It handles formatting (JSON, XML, HTML, plain text), colorization, and output streams.

All rendering functions are pure UI operations - no exit logic or API interpretation.
"""

import json
import sys
import xml.dom.minidom
from datetime import datetime, date
from typing import Callable, List, Optional, Dict, Any, Sequence
import textwrap

import click_extra as click
from rich.console import Console
from rich.table import Table
from rich.theme import Theme
from rich.json import JSON
from bars_cli._core.utils.normalizers import strip_ansi

# Format detection for response bodies
def detect_http_format(text: str) -> str:
    """Simple format detection for response bodies."""
    text_lower = text.strip().lower()
    if text_lower.startswith('<?xml') or text_lower.startswith('<html'):
        return 'xml' if '<?xml' in text_lower else 'html'
    try:
        json.loads(text)
        return 'json'
    except:
        return 'text'


def _convert_pydantic_to_dict(obj: Any) -> Any:
    """Recursively convert Pydantic models to dicts.
    
    Handles Pydantic models (objects with model_dump method) and nested structures.
    
    Args:
        obj: Object that may contain Pydantic models
        
    Returns:
        Dict/list with Pydantic models converted to dicts
    """
    # Check if it's a Pydantic model (has model_dump method)
    if hasattr(obj, 'model_dump'):
        return obj.model_dump(by_alias=True, exclude_none=True)
    
    # Handle lists
    if isinstance(obj, list):
        return [_convert_pydantic_to_dict(item) for item in obj]
    
    # Handle dicts
    if isinstance(obj, dict):
        return {key: _convert_pydantic_to_dict(value) for key, value in obj.items()}
    
    # Return as-is for other types
    return obj


def _json_serialize_non_serializable(obj: Any) -> Any:
    """JSON encoder default function to serialize non-serializable types.
    
    Handles datetime and date objects by converting them to ISO format strings.
    
    Args:
        obj: Object that couldn't be serialized by default JSON encoder
        
    Returns:
        Serialized representation (ISO string for datetime/date)
        
    Raises:
        TypeError: If object type is not supported
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


# Rich Themes for different display formats
# Note: Rich has default JSON colorization (keys, strings, numbers, booleans, null)
# We can use None to get Rich's defaults, or define a custom theme to override
# JSON_THEME = None  # Use Rich's defaults
JSON_THEME = Theme({
    "json.key": "bold medium_purple",  # Override default (Rich default is bold blue)
    "json.str": "cyan",                # Override default
    "json.number": "bright_yellow",   # Override default
    "json.bool_true": "dark_sea_green4",  # Override default
    "json.bool_false": "dark_red",     # Override default
    "json.null": "dim",                # Override default
})

TABLE_THEME = Theme({
    "table.header": "bold cyan",
    "table.value": "white",
    "table.key": "bold yellow",
    "table.column.0": "cyan",      # First column
    "table.column.1": "white",     # Second column
    "table.column.2": "yellow",    # Third column
    "table.column.3": "green",     # Fourth column
})

LIST_THEME = Theme({
    "list.key": "bold cyan",
    "list.value": "white",
    "list.separator": "dim",
})

# Format-to-theme mapping
# Rich has built-in default JSON colorization, so we can use None for JSON to get defaults
# or use JSON_THEME to override with custom colors
_FORMAT_THEMES = {
    "json": JSON_THEME,  # Use custom theme, or set to None for Rich's defaults
    "table": TABLE_THEME,
    "list": LIST_THEME,
    "raw": None,  # No theme for raw output
}


def display_results_as_json(results: List[Dict], ctx: click.Context) -> None:
    """Display results as formatted JSON.
    
    Converts results (list of dicts) to JSON and displays using display_response.
    Works with both database results and HTTP responses.
    
    Args:
        results: List of dictionaries to display
        ctx: Click context for configuration
    """
    if not results:
        click.echo("[]")
        return
    
    display_response(results, display_style="formatted", ctx=ctx)




def _get_console_for_format(
    display_format: str,
    ctx: Optional[click.Context] = None,
    stream = None
) -> Console:
    """Get a Rich Console instance configured for the specified display format.
    
    Args:
        display_format: Display format - 'json', 'table', 'list', or 'raw'
        ctx: Optional Click context for color preferences
        stream: Output stream (defaults to stdout)
    
    Returns:
        Console instance with appropriate theme and settings
    """
    if stream is None:
        stream = click.get_text_stream("stdout")
    
    # Check if color is enabled
    color_enabled = True  # Default
    if ctx is None:
        try:
            ctx = click.get_current_context()
        except RuntimeError:
            ctx = None
    
    if ctx is not None and hasattr(ctx, 'color'):
        color_enabled = ctx.color
    
    # Select theme based on format
    theme = _FORMAT_THEMES.get(display_format) if color_enabled else None
    
    return Console(file=stream, theme=theme, no_color=not color_enabled)


def display_response(
    data: Any,
    *,
    display_format: str = "json",
    display_style: str = "formatted",
    ctx: Optional[click.Context] = None,
    table_columns: Optional[List[str]] = None,
    table_column_styles: Optional[Dict[str, str]] = None
) -> None:
    """Display response data with format-specific styling.
    
    Supports multiple display formats (json, table, list) with appropriate
    color themes and styling for each format type.
    
    Args:
        data: Data to display (dict, list, string, or any JSON-serializable object)
        display_format: Display format - 'json', 'table', 'list', or 'raw'
            - 'json': Pretty JSON with syntax highlighting (keys, strings, numbers, etc.)
            - 'table': Rich table with styled headers and columns
            - 'list': Key-value list with styled keys and values
            - 'raw': Plain text/minimal JSON
        display_style: Display style - 'formatted' (default) or 'raw'
        ctx: Optional Click context for color preferences
        table_columns: Optional list of column names for table format (defaults to keys from first row)
        table_column_styles: Optional dict mapping column names to Rich style strings
    
    Usage:
        # JSON format (default)
        ctx.obj['display_response'](data, display_format='json')
        
        # Table format
        ctx.obj['display_response'](data, display_format='table', table_columns=['name', 'age'])
        
        # List format (for key-value pairs)
        ctx.obj['display_response'](data, display_format='list')
    """
    if display_style == "raw" or display_format == "raw":
        # Raw output - just print as-is or minimal JSON
        if isinstance(data, str):
            click.echo(data)
        else:
            click.echo(json.dumps(data, separators=(',', ':')))
        return
    
    # Get console with appropriate theme
    console = _get_console_for_format(display_format, ctx)
    
    if display_format == "json":
        # JSON format - use Rich's JSON class for pretty-printing
        if isinstance(data, str):
            # If it's already a JSON string, use JSON constructor
            try:
                # Validate it's valid JSON first
                json.loads(data)
                json_obj = JSON(data, indent=2)
            except (json.JSONDecodeError, ValueError):
                # Not valid JSON, output as plain text
                click.echo(data)
                return
        else:
            # Convert Python objects to JSON using JSON.from_data()
            converted = _convert_pydantic_to_dict(data)
            json_obj = JSON.from_data(converted, indent=2, default=_json_serialize_non_serializable)
        
        console.print(json_obj)
        
    elif display_format == "table":
        # Table format - create Rich Table with styled columns
        if not isinstance(data, list) or not data:
            # If not a list, try to convert
            if isinstance(data, dict):
                data = [data]
            else:
                click.echo(str(data))
                return
        
        # Convert Pydantic models to dicts
        rows = [_convert_pydantic_to_dict(item) for item in data]
        
        # Determine columns
        if table_columns is None:
            if rows:
                table_columns = list(rows[0].keys())
            else:
                click.echo("[]")
                return
        
        # Create table with styled headers
        table = Table(
            show_header=True,
            header_style="table.header",
            show_lines=False
        )
        
        # Add columns with individual styling
        for i, col in enumerate(table_columns):
            # Get style for this column (from table_column_styles or default column style)
            if table_column_styles and col in table_column_styles:
                col_style = table_column_styles[col]
            else:
                # Use default column style based on position
                col_style = f"table.column.{i % 4}"  # Cycle through 4 default column styles
            
            table.add_column(col, style=col_style)
        
        # Add rows
        for row in rows:
            values = [str(row.get(col, "")) for col in table_columns]
            table.add_row(*values)
        
        console.print()
        console.print(table)
        console.print()
        
    elif display_format == "list":
        # List format - key-value pairs with styled keys and values
        from rich.text import Text
        
        if isinstance(data, dict):
            items = data.items()
        elif isinstance(data, list) and data and isinstance(data[0], dict):
            # List of dicts - flatten or show first item
            items = data[0].items()
        else:
            click.echo(str(data))
            return
        
        # Convert Pydantic models
        converted = _convert_pydantic_to_dict(dict(items))
        
        # Display as styled key-value pairs
        for key, value in converted.items():
            key_text = Text(str(key), style="list.key")
            value_text = Text(str(value), style="list.value")
            separator = Text(": ", style="list.separator")
            line = Text()
            line.append(key_text)
            line.append(separator)
            line.append(value_text)
            console.print(line)
        
    else:
        # Unknown format - fallback to plain output
        click.echo(str(data))


def print_parameter_table(
    rows: List[dict], 
    value_matches: Optional[List[dict]] = None
) -> None:
    """Print parameters in a formatted table using Rich.
    
    Args:
        rows: List of parameter dicts with keys: key, value, version, last_modified
             If value_matches is provided, these are key matches.
        value_matches: Optional list of parameter dicts that matched on value.
             If provided, rows are treated as key matches and displayed first,
             with a separator and label between sections.
    """
    # Combine all rows for width calculations
    all_rows = rows + (value_matches or [])
    if not all_rows:
        return
    
    console = Console()
    
    # Get terminal width (Rich Console automatically detects terminal size)
    # This will be updated each time the function is called, so resizing the terminal
    # and re-running the command will use the new width
    terminal_width = console.width if hasattr(console, 'width') and console.width else 120
    
    # Calculate max width for Version column (header or longest value + 2 spaces padding on each side)
    version_header_len = len("Version")
    max_version_len = max(
        version_header_len,
        max((len(str(row["version"])) for row in all_rows), default=0)
    )
    version_width = max_version_len + 4  # 2 spaces on each side
    
    # Calculate max width for LastModified column (header or longest value + 2 spaces padding on each side)
    lastmodified_header_len = len("LastModified")
    max_lastmodified_len = max(
        lastmodified_header_len,
        max((len(str(row["last_modified"])) for row in all_rows), default=0)
    )
    lastmodified_width = max_lastmodified_len + 4  # 2 spaces on each side
    
    # Calculate available width for Key and Value columns
    # Account for: Version column + LastModified column + table borders/padding (~10 chars)
    fixed_columns_width = version_width + lastmodified_width + 10
    available_width = max(50, terminal_width - fixed_columns_width)  # Minimum 50 chars for readability
    
    # Split available width between Key and Value columns (40% Key, 60% Value)
    key_width = max(20, int(available_width * 0.4))
    value_width = max(30, available_width - key_width)
    
    # Create a single table with all parameters
    # Note: Rich tables use box styling (box parameter), not the table_format preference
    # The table_format preference in settings.toml is for tabulate-style formatting.
    # Rich tables have their own box styles (ROUNDED, BOX, SIMPLE, etc.) which are
    # set via the box parameter. For now, we use default Rich table styling.
    # Future enhancement: Map table_format preference to Rich box styles if needed.
    table = Table(
        show_header=True,
        header_style="bold",
        show_lines=False,
        expand=True  # Allow table to expand to full terminal width
    )
    
    # Add columns with styling
    # Key and Value columns: dark green (#006400) - allow wrapping, no truncation, dynamic width
    # Version column: light blue (#ADD8E6) - fixed width based on content
    # LastModified column: dark blue (#2b53cc) - fixed width based on content
    # Key and Value columns expand to use available space
    table.add_column("Key", style="#006400", no_wrap=False, overflow="fold", width=key_width, min_width=20)
    table.add_column("Value", style="#006400", no_wrap=False, overflow="fold", width=value_width, min_width=30)
    table.add_column("Version", style="#ADD8E6", no_wrap=True, width=version_width, justify="right")
    table.add_column("LastModified", style="#2b53cc", no_wrap=True, width=lastmodified_width)
    
    # If value_matches is provided, we have two sections with labels
    # Only show section labels if BOTH key matches AND value matches exist
    has_sections = value_matches is not None and len(value_matches) > 0 and len(rows) > 0
    
    # Add key matches section
    if has_sections:
        # Add section label row (only if we have both sections)
        table.add_row(
            "[bold]Matched on key[/bold]",
            "",
            "",
            "",
            style="dim"
        )
        table.add_row("", "", "", "")  # Spacing after label
    
    # Add rows from key matches (always add them, with or without label)
    for i, row in enumerate(rows):
        table.add_row(
            row["key"],
            row["value"],
            row["version"],
            row["last_modified"]
        )
        
        # Add empty row for spacing between parameters (but not after the last one)
        if i < len(rows) - 1:
            table.add_row("", "", "", "")  # Empty row creates spacing
    
    # Add separator and value matches section if applicable
    if value_matches is not None and len(value_matches) > 0:
        # Only show separator and label if we have both key and value matches
        if has_sections:
            # Add horizontal separator (empty row with separator style)
            table.add_row("", "", "", "")  # Spacing before separator
            # Use a separator row that spans visually across columns
            separator_text = "─" * 80  # Long enough to span the table
            table.add_row(
                f"[dim]{separator_text}[/dim]",
                f"[dim]{separator_text}[/dim]",
                f"[dim]{separator_text}[/dim]",
                f"[dim]{separator_text}[/dim]",
            )
            table.add_row("", "", "", "")  # Spacing after separator
            
            # Add section label row
            table.add_row(
                "[bold]Matched on value[/bold]",
                "",
                "",
                "",
                style="dim"
            )
            table.add_row("", "", "", "")  # Spacing after label
        
        # Add rows from value matches (always add them, with or without label)
        for i, row in enumerate(value_matches):
            table.add_row(
                row["key"],
                row["value"],
                row["version"],
                row["last_modified"]
            )
            
            # Add empty row for spacing between parameters (but not after the last one)
            if i < len(value_matches) - 1:
                table.add_row("", "", "", "")  # Empty row creates spacing
    
    # Print table
    console.print()
    console.print(table)
    console.print()


def format_columnar_options(
    items: List[Dict[str, Any]],
    column_defs: List[Dict[str, Any]],
    ctx: Optional[click.Context] = None,
    indent: Optional[int] = 2,
    min_terminal_width: Optional[int] = 80,
    numbering_prefix_width: Optional[int] = None
) -> List[str]:
    """Format items into aligned columns with text wrapping for use in prompts.
    
    Uses Rich Table to calculate column widths, then formats each row as a string
    with proper alignment. Long text in wrap-enabled columns wraps at column start.
    
    Args:
        items: List of item dictionaries to format
        column_defs: List of column definition dicts, each with:
            - 'key': Key to extract from item dict
            - 'label': Column header/label
            - 'formatter': Function(item_value) -> styled string
            - 'width_calc': Function(item_value) -> int (display width, no ANSI)
            - 'min_width': Minimum column width (default: 0)
            - 'wrap': Whether to wrap text in this column (default: False)
            - 'justify': 'left' or 'right' (default: 'left')
        ctx: Optional Click context for terminal width
        indent: Number of spaces for left indentation (default: 2)
        min_terminal_width: Minimum terminal width to assume (default: 80)
        numbering_prefix_width: Optional width of numbering prefix (e.g., "(10) " = 5).
            If None, calculates from number of items. This ensures alignment when
            prompt adds numbering like "(1) " vs "(10) ".
        
    Returns:
        List of formatted option strings (one per item)
    """
    if not items or not column_defs:
        return []
    
    # Calculate numbering prefix width if not provided
    # Format is "  ({num}) " where num can be 1-999+
    if numbering_prefix_width is None:
        num_items = len(items)
        if num_items < 10:
            numbering_prefix_width = 5  # "  (9) "
        elif num_items < 100:
            numbering_prefix_width = 6  # "  (99) "
        else:
            numbering_prefix_width = 7  # "  (999) "
    
    # Get terminal width
    if ctx and hasattr(ctx, 'terminal_width') and ctx.terminal_width:
        term_width = max(ctx.terminal_width, min_terminal_width)
    else:
        try:
            import shutil
            term_width = max(shutil.get_terminal_size().columns, min_terminal_width)
        except Exception:
            term_width = min_terminal_width
    
    # Calculate max widths for each column (accounting for formatted output with ANSI codes)
    column_widths = []
    for col_def in column_defs:
        key = col_def['key']
        label = col_def['label']
        formatter = col_def['formatter']
        width_calc = col_def.get('width_calc', lambda x: len(str(x)))
        min_width = col_def.get('min_width', 0)
        
        # Calculate max width: need to account for formatted strings (with ANSI codes)
        # Use width_calc on raw values, but also check formatted string lengths
        max_value_width = max((width_calc(item.get(key, '')) for item in items), default=0)
        # Also check formatted string lengths (strip ANSI for width calculation)
        max_formatted_width = max(
            (len(strip_ansi(formatter(item.get(key, '')))) for item in items),
            default=0
        )
        # Calculate max width: use actual content, but ensure label fits
        # Don't force min_width if it's 0 (allows columns to be compact)
        if min_width > 0:
            max_width = max(
                len(label),
                max_value_width,
                max_formatted_width,
                min_width
            )
        else:
            # No min_width - use actual content width (but at least label width)
            max_width = max(
                len(label),
                max_value_width,
                max_formatted_width
            )
        column_widths.append(max_width)
    
    # Calculate column start positions (cumulative)
    # Account for numbering prefix width in the first column start
    # The numbering prefix is added by prompt_select_from_options as "  ({num}) "
    # So the first column should start right after the numbering prefix
    # indent is typically 0 here since prompt_select_from_options handles its own spacing
    column_starts = [0]  # Our formatted strings start at 0 (prefix added by prompt_select_from_options)
    for i, width in enumerate(column_widths[:-1]):
        # Add width + 2 spaces padding between columns
        column_starts.append(column_starts[-1] + width + 1)
    
    # For wrapping: calculate available width from the Name column start to terminal edge
    # This ensures continuation lines wrap at terminal width, not at a calculated "available" width
    # Account for the numbering prefix that will be added by prompt_select_from_options
    wrap_col_idx = None
    for i, col_def in enumerate(column_defs):
        if col_def.get('wrap', False):
            wrap_col_idx = i
            break
    # Name column start in our formatted string + numbering prefix width = actual screen position
    name_column_start_in_string = column_starts[wrap_col_idx] if wrap_col_idx is not None else column_starts[-1]
    name_column_start = name_column_start_in_string + numbering_prefix_width
    
    # Format each item
    formatted_options = []
    for item in items:
        lines = []
        # NOTE: prompt_select_from_options adds "  ({num}) " before our formatted string
        # So we start at position 0 in our string (the prefix is added externally)
        current_pos = 0  # Track current position in our formatted string
        
        # Build first line with all columns (no prefix - it's added by prompt_select_from_options)
        first_line = ''
        wrap_column_index = None
        wrap_value = None
        wrap_formatter = None
        remaining_wrapped = []
        
        for i, col_def in enumerate(column_defs):
            key = col_def['key']
            formatter = col_def['formatter']
            wrap = col_def.get('wrap', False)
            justify = col_def.get('justify', 'left')
            
            value = item.get(key, '')
            # Calculate display width of formatted output (strip ANSI codes)
            formatted_value = formatter(value)
            display_width = len(strip_ansi(formatted_value))
            
            # Pad to column start
            if current_pos < column_starts[i]:
                padding = ' ' * (column_starts[i] - current_pos)
                first_line += padding
                current_pos = column_starts[i]
            
            # Handle wrap column specially
            if wrap and i == len(column_defs) - 1:
                wrap_column_index = i
                wrap_value = value
                wrap_formatter = formatter  # Store formatter for continuation lines
                # Wrap the text (use raw value for wrapping, then format)
                # For wrapping, we need to account for the key label width in first line
                # Extract key label width from formatted output
                formatted_sample = formatter("test")
                if ":" in strip_ansi(formatted_sample):
                    # Formatter includes key label (e.g., "Name: test")
                    key_label_part = strip_ansi(formatted_sample).split(":")[0] + ": "
                    key_label_width = len(key_label_part)
                else:
                    key_label_width = 0
                
                # Calculate wrap width for continuation lines (from name column start to terminal edge)
                # This is the width available for the Name value (not including the "Name: " label)
                # The Name column starts at name_column_start_in_string in our formatted string
                # After prompt_select_from_options adds the prefix, it's at name_column_start on screen
                # For wrapping, we want to use the full terminal width from the Name column position
                # But if that's too small (< 20 chars), allow wrapping to use more space by wrapping
                # from the start of the Name column in our string (which will be at name_column_start on screen)
                continuation_wrap_width = term_width - name_column_start
                # If wrap width is too small, the Name column is too far right - use a minimum reasonable width
                # This allows names to wrap properly even when columns take up most of the terminal
                continuation_wrap_width = max(continuation_wrap_width, 30)  # Ensure reasonable minimum for readability
                
                # Calculate available width on first line (after key label)
                # current_pos is in our formatted string, so add numbering_prefix_width for screen position
                first_line_screen_pos = current_pos + numbering_prefix_width
                first_line_available = term_width - first_line_screen_pos - key_label_width
                first_line_available = max(first_line_available, 20)  # Ensure reasonable minimum
                
                # Wrap the entire value text at continuation width (consistent wrapping for all lines)
                # This ensures all continuation lines use the same width
                all_wrapped_lines = textwrap.wrap(
                    str(wrap_value),
                    width=continuation_wrap_width,
                    break_long_words=False,
                    break_on_hyphens=False
                )
                
                if all_wrapped_lines:
                    # Check if first segment fits on first line
                    if len(all_wrapped_lines[0]) <= first_line_available:
                        # First segment fits, use it as-is
                        first_wrapped = formatter(all_wrapped_lines[0])
                        first_line += first_wrapped
                        remaining_wrapped = all_wrapped_lines[1:]
                        current_pos += len(strip_ansi(first_wrapped))
                    else:
                        # First segment doesn't fit, need to wrap it for first line
                        # Wrap just the first segment at first line width
                        first_segment_wrapped = textwrap.wrap(
                            all_wrapped_lines[0],
                            width=first_line_available,
                            break_long_words=False,
                            break_on_hyphens=False
                        )
                        if first_segment_wrapped:
                            # Use first part of first segment on first line
                            first_wrapped = formatter(first_segment_wrapped[0])
                            first_line += first_wrapped
                            current_pos += len(strip_ansi(first_wrapped))
                            # Remaining: rest of first segment + all other segments
                            remaining_text = ' '.join(first_segment_wrapped[1:] + all_wrapped_lines[1:])
                            # Re-wrap remaining at continuation width
                            remaining_wrapped = textwrap.wrap(
                                remaining_text,
                                width=continuation_wrap_width,
                                break_long_words=False,
                                break_on_hyphens=False
                            ) if remaining_text.strip() else []
                        else:
                            # Empty first segment (shouldn't happen)
                            first_line += formatter('')
                            remaining_wrapped = all_wrapped_lines
                            current_pos += len(strip_ansi(formatter('')))
                else:
                    first_line += formatter('')
                    current_pos += len(strip_ansi(formatter('')))
            else:
                # Fixed-width column
                styled_value = formatter(value)
                if justify == 'right':
                    padding = ' ' * (column_widths[i] - display_width)
                    first_line += padding + styled_value
                else:
                    first_line += styled_value
                    padding = ' ' * (column_widths[i] - display_width)
                    first_line += padding
                current_pos += column_widths[i]  # Update position
        
        lines.append(first_line)
        
        # Add continuation lines for wrapped column
        if wrap_column_index is not None and remaining_wrapped and wrap_formatter:
            # Continuation lines: pad to column start (accounting for numbering prefix)
            # Use continuation_formatter if provided, otherwise use regular formatter
            continuation_formatter = column_defs[wrap_column_index].get('continuation_formatter', wrap_formatter)
            
            # Calculate wrap width for continuation lines (from column start to terminal edge)
            # This should match the width used for the initial wrap
            # Use the same calculation as above to ensure consistency
            continuation_wrap_width = term_width - name_column_start
            continuation_wrap_width = max(continuation_wrap_width, 30)  # Match the minimum from above
            
            # Process remaining wrapped text - join and re-wrap at continuation width
            # This ensures consistent wrapping across all continuation lines
            continuation_text = ' '.join(remaining_wrapped)
            if continuation_text.strip():
                continuation_lines = textwrap.wrap(
                    continuation_text,
                    width=continuation_wrap_width,
                    break_long_words=False,
                    break_on_hyphens=False
                )
            else:
                continuation_lines = []
            
            for wrapped_line in continuation_lines:
                # Continuation lines are part of our formatted string, so use string-relative position
                # (the numbering prefix is added by prompt_select_from_options, not by us)
                continuation = ' ' * name_column_start_in_string
                # Format continuation line (no key label, just value)
                continuation += continuation_formatter(wrapped_line)
                lines.append(continuation)
        
        # Join all lines for this item
        formatted_options.append('\n'.join(lines))
    
    return formatted_options


def display_columnar_table(
    items: List[Dict[str, Any]],
    column_defs: List[Dict[str, Any]],
    ctx: Optional[click.Context] = None,
    show_header: Optional[bool] = True
) -> None:
    """Display items in a Rich Table with columnar formatting.
    
    Args:
        items: List of item dictionaries to display
        column_defs: List of column definition dicts (see format_columnar_options)
        ctx: Optional Click context
        show_header: Whether to show table header (default: True)
    """
    if not items or not column_defs:
        return
    
    console = Console()
    
    # Calculate column widths
    column_widths = []
    for col_def in column_defs:
        key = col_def['key']
        label = col_def['label']
        width_calc = col_def.get('width_calc', lambda x: len(str(x)))
        min_width = col_def.get('min_width', 0)
        
        max_width = max(
            len(label),
            max((width_calc(item.get(key, '')) for item in items), default=0),
            min_width
        )
        column_widths.append(max_width)
    
    # Create Rich Table
    table = Table(
        show_header=show_header,
        header_style="bold",
        show_lines=False
    )
    
    # Add columns to table
    for i, col_def in enumerate(column_defs):
        label = col_def['label']
        style = col_def.get('style', None)
        wrap = col_def.get('wrap', False)
        justify = col_def.get('justify', 'left')
        width = column_widths[i] if not wrap else None
        
        if wrap:
            table.add_column(
                label,
                style=style,
                no_wrap=False,
                overflow="fold",
                width=width,
                justify=justify
            )
        else:
            table.add_column(
                label,
                style=style,
                no_wrap=True,
                width=width,
                justify=justify
            )
    
    # Add rows
    for item in items:
        row_values = []
        for col_def in column_defs:
            key = col_def['key']
            value = item.get(key, '')
            # For Rich Table, we pass the raw value (Rich handles styling via column style)
            # But if formatter adds markup, we can use it
            formatter = col_def.get('formatter', str)
            formatted = formatter(value)
            # Strip ANSI codes for Rich (Rich uses its own markup)
            # Or use Rich markup if formatter returns Rich markup
            row_values.append(strip_ansi(str(value)) if isinstance(formatted, str) and '\x1b' in formatted else str(value))
        table.add_row(*row_values)
    
    # Print table
    console.print()
    console.print(table)
    console.print()


# ============================================================================
# BARS CLI SPECIFIC DISPLAY FUNCTIONS (not in engine_cli)
# ============================================================================

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


def _get_box_from_string(box_style: Optional[str]) -> Optional[Any]:
    """Convert box style string to Box object.
    
    Args:
        box_style: Box style name (e.g., "SIMPLE", "ROUNDED", "HEAVY") or None
        
    Returns:
        Box object or None if box_style is None
    """
    from rich import box
    
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
    from rich import box
    
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
) -> Any:
    """Create a Rich Panel with text content.
    
    Args:
        content: Text content for the panel
        title: Optional panel title
        border_style: Border style color (default: "cyan")
        
    Returns:
        Configured Rich Panel instance
    """
    from rich.panel import Panel
    
    return Panel(content, title=title, border_style=border_style)


def create_text_panel(
    parts: Sequence[tuple[str, str | None]],
    *,
    title: Optional[str] = None,
    border_style: str = "cyan"
) -> Any:
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
    from rich.panel import Panel
    from rich.text import Text
    
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
    from rich.syntax import Syntax
    
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
