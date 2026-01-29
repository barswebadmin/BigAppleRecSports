"""JSON output utilities for CLI commands.

Provides generic helpers for outputting data as JSON across all domains.
Handles sgqlc objects, Pydantic models, and plain Python objects.
"""

import json
from typing import Any, List, Optional, Dict


def to_json_data(item: Any) -> Any:
    """Convert an item to JSON-serializable data.
    
    Handles:
    - sgqlc Type objects (uses __json_data__ attribute)
    - Pydantic models (uses model_dump() or dict())
    - Plain dicts/lists/primitives
    
    Args:
        item: Item to convert (any type)
        
    Returns:
        JSON-serializable data (dict, list, or primitive)
    """
    # Handle sgqlc Type objects
    if hasattr(item, '__json_data__'):
        return item.__json_data__  # type: ignore[attr-defined]
    
    # Handle Pydantic models
    if hasattr(item, 'model_dump'):
        return item.model_dump()  # type: ignore[attr-defined]
    if hasattr(item, 'dict'):
        return item.dict()  # type: ignore[attr-defined]
    
    # Handle dicts, lists, and primitives (already JSON-serializable)
    if isinstance(item, (dict, list, str, int, float, bool, type(None))):
        return item
    
    # Fallback: convert to string representation
    return str(item)


def output_json(
    data: Any,
    *,
    indent: int = 2,
    default: Any = str
) -> None:
    """Output data as formatted JSON.
    
    Args:
        data: Data to output (will be converted to JSON-serializable format)
        indent: Number of spaces for indentation (default: 2)
        default: Function to handle non-serializable objects (default: str)
    """
    import click_extra as click
    
    # Convert to JSON-serializable format
    json_data = to_json_data(data)
    
    # Output as JSON
    click.echo(json.dumps(json_data, indent=indent, default=default))


def output_json_item(item: Any, *, indent: int = 2) -> None:
    """Output a single item as JSON.
    
    Convenience wrapper for output_json() for single items.
    
    Args:
        item: Single item to output
        indent: Number of spaces for indentation (default: 2)
    """
    output_json(item, indent=indent)


def output_json_list(items: List[Any], *, indent: int = 2) -> None:
    """Output a list of items as JSON.
    
    Convenience wrapper for output_json() for lists.
    
    Args:
        items: List of items to output
        indent: Number of spaces for indentation (default: 2)
    """
    json_data = [to_json_data(item) for item in items]
    output_json(json_data, indent=indent)


def output_json_error(
    error_msg: str,
    *,
    error_type: Optional[str] = None,
    error_data: Optional[Dict[str, Any]] = None,
    indent: int = 2
) -> None:
    """Output an error as JSON.
    
    Args:
        error_msg: Error message text
        error_type: Optional error type name
        error_data: Optional additional error data
        indent: Number of spaces for indentation (default: 2)
    """
    error_output: Dict[str, Any] = {"error": error_msg}
    
    if error_type:
        error_output["type"] = error_type
    
    if error_data:
        error_output.update(error_data)
    
    output_json(error_output, indent=indent)

