"""
Shared helpers for Shopify CLI commands.

Provides generic command handlers to reduce duplication across customer, order, and other Shopify commands.
"""

import json
import traceback
from typing import Dict, Any, Optional, List, Callable

import click

from bars_cli._core.prompts import prompt_select_from_options, EXIT_SENTINEL
from bars_cli._core.utils import strip_ansi
from bars_cli._core.utils.json_output import (
    to_json_data,
    output_json_item,
    output_json_list,
    output_json_error,
)


ALL_SENTINEL = "__ALL__"


def get_shopify_service(ctx: click.Context, entity_name: str = "entity"):
    """Get Shopify service from context or raise error.
    
    Args:
        ctx: Click context object
        entity_name: Name of entity for error messages (e.g., "customer", "order")
        
    Returns:
        ShopifyService instance
        
    Raises:
        click.ClickException: If service is not available
    """
    shopify_service = ctx.meta.get('shopify_service')
    if not shopify_service:
        error_msg = ctx.meta.get('shopify_service_error', 'Shopify service not available')
        raise click.ClickException(error_msg)
    return shopify_service


def format_error(
    error_msg: str,
    error_type: Optional[str] = None,
    json_output: bool = False,
    should_display: bool = True
) -> None:
    """Format and display error message.
    
    Args:
        error_msg: Error message text
        error_type: Optional error type name
        json_output: Whether to output JSON format
        should_display: Whether to display the error
    """
    if not should_display:
        return
    
    if json_output:
        output_json_error(error_msg, error_type=error_type)
    else:
        if error_type:
            click.echo(f"❌ Unexpected error ({error_type}): {error_msg}", err=True)
        else:
            click.echo(f"❌ {error_msg}", err=True)


def handle_multiple_shopify_results(
    items: List[Any],
    json_output: bool,
    should_display: bool,
    format_option_func: Callable[[Any], str],
    entity_name: str,
    must_return_one: bool = False
) -> Optional[Any]:
    """Handle selection when multiple Shopify entities are found.
    
    Args:
        items: List of entity objects (customers, orders, etc.)
        json_output: Whether to output JSON format
        should_display: Whether to display output
        format_option_func: Function to format each item for display in options list
        entity_name: Entity name for messages (e.g., "customer", "order")
        must_return_one: If True, requires selecting exactly one item (no "All" option)
        
    Returns:
        Selected entity object if one selected, list of all entities if "All" selected,
        or None if cancelled/exit
    """
    if json_output:
        if should_display:
            output_json_list(items)
        return None
    
    if not should_display:
        return None
    
    # Format options for selection
    options = [format_option_func(item) for item in items]
    
    # Add "All" option if not must_return_one (before Exit, which is added by prompt_select_from_options)
    if not must_return_one:
        all_option = click.style("All", fg="green", bold=True)
        options.append(all_option)
    
    # Use prompt_select_from_options for selection (it automatically adds "Exit" at the end)
    selected_option = prompt_select_from_options(
        display_text=f"Select {entity_name.capitalize()} ({len(items)} found)",
        options=options,
        autocomplete=True
    )
    
    # Handle exit/cancellation
    if selected_option == EXIT_SENTINEL:
        return None
    
    # Handle "All" selection
    # Strip ANSI codes for comparison (prompt_select_from_options may return with or without ANSI)
    selected_clean = strip_ansi(selected_option).strip().lower()
    
    # Check if "All" was selected
    if selected_clean == "all":
        return items  # Return all items as a list
    
    # Find the item that matches the selected option
    # Remove "All" from options list for indexing (if it was added)
    item_options = options[:-1] if not must_return_one and len(options) > len(items) else options
    
    # Try to find exact match first
    try:
        selected_idx = item_options.index(selected_option)
        return items[selected_idx]
    except ValueError:
        # Fallback: try to find by matching stripped text (in case of ANSI code differences)
        for i, opt in enumerate(item_options):
            opt_clean = strip_ansi(opt).strip()
            if opt_clean == selected_clean:
                return items[i]
        # If still not found, return None
        return None


def handle_shopify_get_command(
    ctx: click.Context,
    identifier: Optional[Dict[str, Any]],
    service_method: Callable[..., List[Any]],
    entity_name: str,
    format_func: Callable[[Any], str],
    handle_multiple_func: Callable[[List[Any], bool, bool], Optional[Any]],
    service_method_kwargs: Optional[Dict[str, Any]] = None,
    identifier_required_msg: Optional[str] = None
) -> Optional[List[Any]]:
    """Generic handler for Shopify GET commands (customer, order, etc.).
    
    Handles the complete flow:
    1. Extract display context
    2. Validate identifier
    3. Get Shopify service
    4. Call service method
    5. Handle errors
    6. Handle single vs multiple results
    7. Output JSON or formatted display
    
    Args:
        ctx: Click context object
        identifier: Identifier dict from parameter type converter
        service_method: Service method to call (e.g., shopify_service.get_customer_by_identifier)
        entity_name: Entity name for messages (e.g., "customer", "order")
        format_func: Function to format single entity for display (e.g., format_customer)
        handle_multiple_func: Function to handle multiple results (e.g., handle_multiple_results)
        service_method_kwargs: Optional kwargs to pass to service_method
        identifier_required_msg: Custom message when identifier is missing
        
    Returns:
        List of entity objects, or None if cancelled/error
        
    Raises:
        click.ClickException: For all errors (decorator handles exit)
    """
    ctx.ensure_object(dict)
    json_output = ctx.obj.get('json_output', False)
    should_display = ctx.obj.get('should_display', True)
    
    # Validate identifier
    if not identifier:
        error_msg = identifier_required_msg or f"{entity_name.capitalize()} identifier is required"
        format_error(error_msg, json_output=json_output, should_display=should_display)
        raise click.ClickException(error_msg)
    
    try:
        # Display lookup message
        if should_display and not json_output:
            lookup_value = identifier.get("identifier", entity_name)
            click.echo(f"🔍 Looking up: {lookup_value}", err=True)
        
        # Get Shopify service (guaranteed to be available from shopify group initialization)
        shopify_service = ctx.meta.get('shopify_service')
        if not shopify_service:
            # This should never happen if shopify group initialized correctly
            error_msg = f"Shopify service not available. This is a bug - service should be initialized in shopify group."
            format_error(error_msg, json_output=json_output, should_display=should_display)
            raise click.ClickException(error_msg)
        
        # Call service method
        try:
            if service_method_kwargs:
                entities = service_method(identifier, **service_method_kwargs)
            else:
                entities = service_method(identifier)
        except (RuntimeError, ValueError) as e:
            error_msg = str(e)
            format_error(error_msg, json_output=json_output, should_display=should_display)
            raise click.ClickException(error_msg)
        
        # Check for empty results
        if not entities:
            error_msg = identifier.get('not_found_message', f'No {entity_name}s found')
            format_error(error_msg, json_output=json_output, should_display=should_display)
            raise click.ClickException(error_msg)
        
        # Handle single vs multiple results
        if len(entities) == 1:
            entity = entities[0]
            if should_display:
                if json_output:
                    output_json_item(entity)
                else:
                    click.echo(format_func(entity))
            return entities
        else:
            # Multiple entities - use handler
            selected_result = handle_multiple_func(entities, json_output, should_display)
            if selected_result:
                # Check if "All" was selected (returns list) or single item selected
                if isinstance(selected_result, list):
                    # "All" was selected - display all items
                    if should_display:
                        if json_output:
                            output_json_list(selected_result)
                        else:
                            for item in selected_result:
                                click.echo(format_func(item))
                    return selected_result
                else:
                    # Single item selected
                    if should_display:
                        if json_output:
                            output_json_item(selected_result)
                        else:
                            click.echo(format_func(selected_result))
                    return [selected_result]
            return entities
        
    except click.ClickException:
        # Re-raise Click exceptions - decorator will handle exit
        raise
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        format_error(error_msg, error_type=error_type, json_output=json_output, should_display=should_display)
        if should_display and not json_output:
            click.echo(traceback.format_exc(), err=True)
        raise click.ClickException(error_msg)

