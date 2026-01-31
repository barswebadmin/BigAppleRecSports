"""
Shared helpers for Shopify CLI commands.

Provides generic command handlers to reduce duplication across customer, order, and other Shopify commands.
"""

import csv
import sys
from typing import Dict, Any, Optional, List, Callable, Tuple, TYPE_CHECKING

import click_extra as click

from bars_cli._core.prompts import prompt_select_from_options
from bars_cli._core.utils import strip_ansi
from bars_cli._core.utils.json_output import (
    output_json_item,
    output_json_list,
)
from .shopify_formatters import format_error, _format_customer_name_from_order

if TYPE_CHECKING:
    from bars_cli.backend_services.shopify.models.sgqlc_models import (
        Order,
        Customer,
        LineItem,
        Product,
        ProductVariant,
        InventoryItem,
    )
else:
    Order = Any
    Customer = Any
    LineItem = Any
    Product = Any
    ProductVariant = Any
    InventoryItem = Any


# Removed ALL_SENTINEL - use display_all=True in prompt_select_from_options instead


def handle_shopify_error_response(
    error: Exception,
    json_output: bool,
    should_display: bool
) -> None:
    """Handle error response from Shopify service method call.
    
    Args:
        error: Exception raised from service method (RuntimeError or ValueError)
        json_output: Whether to output JSON format
        should_display: Whether to display output
        
    Raises:
        click.ClickException: Always raises with formatted error message
    """
    error_msg = str(error)
    
    # If error already contains formatted GraphQL errors, display as-is to avoid duplication
    if "GraphQL query failed" in error_msg:
        if should_display:
            # Remove duplicate "GraphQL query failed" prefixes
            lines = error_msg.split('\n')
            seen_prefixes = set()
            unique_lines = []
            for line in lines:
                if line.startswith("GraphQL query failed"):
                    if "GraphQL query failed" not in seen_prefixes:
                        unique_lines.append(line)
                        seen_prefixes.add("GraphQL query failed")
                else:
                    unique_lines.append(line)
            error_msg = '\n'.join(unique_lines)
            
            if json_output:
                from bars_cli._core.utils.json_output import output_json_error
                output_json_error(error_msg)
            else:
                click.echo(error_msg, err=True)
    else:
        format_error(error_msg, json_output=json_output, should_display=should_display)
    
    raise click.ClickException(error_msg)


def handle_empty_shopify_results(
    identifier: Dict[str, Any],
    entity_name: str,
    json_output: bool,
    should_display: bool
) -> None:
    """Handle empty results from Shopify service method call.
    
    Args:
        identifier: Identifier dict from parameter type converter
        entity_name: Entity name for messages (e.g., "customer", "order")
        json_output: Whether to output JSON format
        should_display: Whether to display output
        
    Raises:
        click.ClickException: Always raises with "not found" error message
    """
    error_msg = identifier.get('not_found_message', f'No {entity_name}s found')
    format_error(error_msg, json_output=json_output, should_display=should_display)
    raise click.ClickException(error_msg)


def validate_identifier(
    identifier: Optional[Dict[str, Any]],
    entity_name: str,
    json_output: bool,
    should_display: bool,
    identifier_required_msg: Optional[str] = None
) -> None:
    """Validate that identifier is provided.
    
    Args:
        identifier: Identifier dict from parameter type converter
        entity_name: Entity name for messages (e.g., "customer", "order")
        json_output: Whether to output JSON format
        should_display: Whether to display output
        identifier_required_msg: Custom message when identifier is missing
        
    Raises:
        click.ClickException: Always raises if identifier is missing
    """
    if not identifier:
        error_msg = identifier_required_msg or f"{entity_name.capitalize()} identifier is required"
        format_error(error_msg, json_output=json_output, should_display=should_display)
        raise click.ClickException(error_msg)


def handle_single_shopify_result(
    entity: Any,
    json_output: bool,
    should_display: bool,
    format_func: Callable[[Any], str]
) -> List[Any]:
    """Handle display of a single Shopify entity result.
    
    Args:
        entity: Single entity object
        json_output: Whether to output JSON format
        should_display: Whether to display output
        format_func: Function to format entity for display
        
    Returns:
        List containing the single entity
    """
    if should_display:
        if json_output:
            output_json_item(entity)
        else:
            click.echo(format_func(entity))
    return [entity]


def handle_shopify_response(
    entities: List[Any],
    identifier: Dict[str, Any],
    entity_name: str,
    json_output: bool,
    should_display: bool,
    format_func: Callable[[Any], str],
    handle_multiple_func: Optional[Tuple[Callable[..., Optional[List[Any]]], Dict[str, Any]]] = None
) -> Optional[List[Any]]:
    """Route Shopify service response to appropriate handler.
    
    Routes to:
    - handle_empty_shopify_results: if entities list is empty
    - handle_single_shopify_result: if entities list has 1 item
    - handle_multiple_shopify_results: if entities list has 2+ items
    
    Args:
        entities: List of entity objects returned from service method
        identifier: Identifier dict from parameter type converter
        entity_name: Entity name for messages (e.g., "customer", "order")
        json_output: Whether to output JSON format
        should_display: Whether to display output
        format_func: Function to format single entity for display
        handle_multiple_func: Optional tuple of (callable, kwargs_dict) to handle multiple results.
                            If provided, will be called as: func(items, json_output, should_display, **kwargs)
        
    Returns:
        List of entity objects, or None if cancelled/error
        
    Raises:
        click.ClickException: For empty results (via handle_empty_shopify_results)
    """
    # Check for empty results
    if not entities:
        handle_empty_shopify_results(identifier, entity_name, json_output, should_display)
    
    # Route based on result count
    if len(entities) == 1:
        # Single result: display immediately
        return handle_single_shopify_result(
            entity=entities[0],
            json_output=json_output,
            should_display=should_display,
            format_func=format_func
        )
    else:
        # Multiple results: prompt for selection
        if handle_multiple_func:
            func, kwargs = handle_multiple_func
            # Add format_func to kwargs if not already present
            if 'format_func' not in kwargs:
                kwargs['format_func'] = format_func
            selected_result = func(entities, json_output, should_display, **kwargs)
            return selected_result
        else:
            # Default: just return all entities
            if should_display:
                if json_output:
                    output_json_list(entities)
                else:
                    for item in entities:
                        click.echo(format_func(item))
            return entities


def handle_multiple_shopify_results(
    items: List[Any],
    json_output: bool,
    should_display: bool,
    format_option_func: Callable[[Any], str],
    format_func: Callable[[Any], str],
    entity_name: str,
    must_return_one: bool = False
) -> Optional[List[Any]]:
    """Handle user selection and display when multiple Shopify entities are found.
    
    This function should only be called when there are multiple items.
    It prompts the user to select one item or "All", displays the selection, and returns it.
    
    Args:
        items: List of entity objects (customers, orders, etc.) - must have 2+ items
        json_output: Whether to output JSON format
        should_display: Whether to display output
        format_option_func: Function to format each item for display in options list
        format_func: Function to format selected item(s) for display
        entity_name: Entity name for messages (e.g., "customer", "order")
        must_return_one: If True, requires selecting exactly one item (no "All" option)
        
    Returns:
        List containing selected item if one selected, list of all items if "All" selected,
        or None if cancelled/exit
    """
    if json_output:
        if should_display:
            output_json_list(items)
        return None
    
    if not should_display:
        return None
    
    # Format options for selection
    options = []
    item_map = {}
    for i, item in enumerate(items):
        display_text = format_option_func(item)
        item_key = f"item_{i}"
        options.append({"value": item_key, "display": display_text})
        item_map[item_key] = item

    # Use prompt_select_from_options for selection
    selected_option = prompt_select_from_options(
        display_text=f"Select {entity_name.capitalize()} ({len(items)} found)",
        options=options,
        display_all=not must_return_one
    )

    # Handle exit/cancellation
    if selected_option is None:
        return None

    # Handle "All" selection
    if selected_option == "All":
        # Display all items
        if should_display:
            if json_output:
                output_json_list(items)
            else:
                for item in items:
                    click.echo(format_func(item))
        return items

    # Find the selected item using the item_map
    selected_item = item_map.get(selected_option)
    if selected_item is None:
        return None

    # Display selected item using single result handler
    return handle_single_shopify_result(
        entity=selected_item,
        json_output=json_output,
        should_display=should_display,
        format_func=format_func
    )


# ============================================================================
# ENTITY DATA EXTRACTION HELPERS
# ============================================================================

def extract_variants_from_product(product: Product) -> List[Dict[str, Any]]:
    """Extract variants from product with inventory info.
    
    Args:
        product: Product object
        
    Returns:
        List of variant dicts with keys: id, title, inventory_quantity, inventory_item_id
    """
    from typing import cast
    
    variants_conn = getattr(product, 'variants', None)
    if not variants_conn:
        return []
    
    nodes = getattr(variants_conn, 'nodes', None)
    if not nodes:
        return []
    
    # Cast to list - at runtime, sgqlc returns actual list, not Field objects
    variant_nodes = cast(List[ProductVariant], list(nodes))
    
    # Build variants list
    variants = []
    for variant in variant_nodes:
        inventory_item = getattr(variant, 'inventoryItem', None)
        inventory_item_id = None
        if inventory_item:
            # Cast field access - at runtime, sgqlc returns actual values (str), not Field objects
            inventory_item_id = cast(Optional[str], getattr(inventory_item, 'id', None))
        
        # Cast field access - at runtime, sgqlc returns actual values (str, int), not Field objects
        variant_id = cast(Optional[str], getattr(variant, 'id', None))
        variant_title = cast(str, getattr(variant, 'title', 'Unknown'))
        variant_inventory = cast(Optional[int], getattr(variant, 'inventoryQuantity', None))
        
        variants.append({
            'id': variant_id,
            'title': variant_title,
            'inventory_quantity': variant_inventory,
            'inventory_item_id': inventory_item_id
        })
    
    return variants


def extract_variant_id_from_line_items(line_items: List[LineItem]) -> Optional[str]:
    """Extract variant ID from first line item.
    
    Args:
        line_items: List of LineItem objects
        
    Returns:
        Variant ID string or None if not found
    """
    from typing import cast
    
    if not line_items:
        return None
    
    first_item = line_items[0]
    variant = getattr(first_item, 'variant', None)
    if not variant:
        return None
    
    # Cast field access - at runtime, sgqlc returns actual values (str), not Field objects
    variant_id = getattr(variant, 'id', None)
    return cast(Optional[str], variant_id)


# ============================================================================
# CSV UTILITIES
# ============================================================================

def write_csv_dict_to_stdout(data: List[Dict[str, str]]) -> None:
    """Write CSV dictionary data to stdout.
    
    Args:
        data: List of dictionaries to write as CSV rows
    """
    if not data:
        return
    
    fieldnames = sorted(set().union(*(d.keys() for d in data)))
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)


def process_inventory_updates(
    shopify_service: Any,
    variants: List[Dict[str, Any]],
    update_list: List[Tuple[str, str, int]],
    console: Any
) -> List[Dict[str, Any]]:
    """
    Process inventory updates for a list of variants.
    
    This is the shared logic for updating inventory that can be used by both
    the update-inventory command and the restock command.
    
    Args:
        shopify_service: ShopifyService instance
        variants: List of variant dicts (for reference)
        update_list: List of tuples (variant_id, inventory_item_id, delta)
        console: Console for output
        
    Returns:
        List of result dictionaries from update_inventory calls
    """
    from rich.console import Console
    from bars_cli.commands.shopify._shared.shopify_formatters import (
        format_restock_result,
        format_restock_summary,
    )
    
    if not isinstance(console, Console):
        console = Console()
    
    if not update_list:
        console.print("[dim]No inventory changes made.[/dim]\n")
        return []
    
    # Get location ID using service method
    location_id = shopify_service.get_first_location_id()  # type: ignore[attr-defined]
    if not location_id:
        console.print("[red]Error: No locations found. Cannot update inventory.[/red]\n")
        raise click.ClickException("No locations found")
    
    # Process inventory updates using service method
    console.print("[cyan]Processing inventory adjustments...[/cyan]\n")
    
    success_count = 0
    failure_count = 0
    results = []  # Collect all results for return
    
    for variant_id, inventory_item_id, delta in update_list:
        result = shopify_service.update_inventory(  # type: ignore[attr-defined]
            inventory_item_id=inventory_item_id,
            location_id=location_id,
            delta=delta
        )
        
        results.append(result)  # Collect result
        
        success = result.get("success", False)
        error_msg = None if success else (result.get("message") or result.get("error", "Unknown error"))
        
        format_restock_result(abs(delta), success, error_msg, console)
        
        if success:
            success_count += 1
        else:
            failure_count += 1
    
    console.print()
    
    # Summary
    format_restock_summary(success_count, failure_count, console)
    
    if failure_count > 0:
        raise click.ClickException(f"Failed to update {failure_count} variant(s)")
    
    return results  # Return all results
