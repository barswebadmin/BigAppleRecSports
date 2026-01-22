"""Update inventory for Shopify product variants command."""

import sys
from typing import Dict, Any, Optional, List, Tuple

import click
from rich.console import Console

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_PRODUCT_IDENTIFIER
from bars_cli.commands.shopify._shared.shopify_formatters import (
    format_variants_table,
    format_restock_result,
    format_restock_summary,
)


def process_inventory_updates(
    shopify_service: Any,
    variants: List[Dict[str, Any]],
    update_list: List[Tuple[str, str, int]],
    console: Console
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
    """
    if not update_list:
        console.print("[dim]No inventory changes made.[/dim]\n")
        return []
    
    # Get location ID using service method
    location_id = shopify_service.get_first_location_id()
    if not location_id:
        console.print("[red]Error: No locations found. Cannot update inventory.[/red]\n")
        raise click.ClickException("No locations found")
    
    # Process inventory updates using service method
    console.print("[cyan]Processing inventory adjustments...[/cyan]\n")
    
    success_count = 0
    failure_count = 0
    results = []  # Collect all results for return
    
    for variant_id, inventory_item_id, delta in update_list:
        result = shopify_service.update_inventory(
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


def _prompt_inventory_selection(
    variants: List[Dict[str, Any]],
    console: Console
) -> List[Tuple[str, str, int]]:
    """
    Prompt user for inventory update selection from available variants.
    
    Args:
        variants: List of variant dicts with keys: id, title, inventory_quantity, inventory_item_id
        console: Console for output
    
    Returns:
        List of tuples: (variant_id, inventory_item_id, delta)
        delta can be positive (increase) or negative (decrease)
    """
    if not variants:
        console.print("[yellow]No variants found for this product.[/yellow]")
        return []
    
    console.print("\n[bold]📦 Product Variants - Inventory Status[/bold]\n")
    
    # Display variants table
    format_variants_table(variants, console)
    
    # Prompt for selection
    update_list = []
    
    while True:
        selection = input("Enter variant number to update (or 'done' to finish): ").strip().lower()
        
        if selection == 'done':
            break
        
        try:
            variant_index = int(selection) - 1
            if 0 <= variant_index < len(variants):
                selected_variant = variants[variant_index]
                
                # Prompt for delta (can be positive or negative)
                while True:
                    delta_input = input(f"Enter quantity change for {selected_variant['title']} (positive to increase, negative to decrease, or 'cancel'): ").strip()
                    
                    if delta_input.lower() == 'cancel':
                        break
                    
                    try:
                        delta = int(delta_input)
                        inventory_item_id = selected_variant.get('inventory_item_id')
                        if inventory_item_id:
                            # Don't print success until mutation succeeds - process_inventory_updates handles that
                            update_list.append((selected_variant['id'], inventory_item_id, delta))
                            break
                        else:
                            console.print("[red]Error: No inventory item ID found for this variant.[/red]")
                            break
                    except ValueError:
                        console.print("[red]Invalid input. Enter a number, or 'cancel'.[/red]")
            else:
                console.print(f"[red]Invalid selection. Enter a number between 1 and {len(variants)}.[/red]")
        except ValueError:
            console.print("[red]Invalid input. Enter a number or 'done'.[/red]")
    
    return update_list


@click.command('update-inventory')
@handle_display_options(display=True, exit_on_error=True)
@click.argument('identifier', type=SHOPIFY_PRODUCT_IDENTIFIER, required=False)
@click.pass_context
def update_inventory_cmd(
    ctx: click.Context,
    identifier: Optional[Dict[str, Any]]
) -> None:
    """
    Update inventory for Shopify product variants.
    
    Fetches product variants, displays inventory status, and prompts for selection.
    Then adjusts inventory for selected variants (can increase or decrease).
    
    IDENTIFIER: Product ID (gid://shopify/Product/123 or 123) or product handle.
    
    Examples:
      bars shopify product update-inventory 123456789
      bars shopify product update-inventory gid://shopify/Product/123456789
      bars shopify product update-inventory product-handle
    """
    console = Console()
    
    # Get service from context (lazily initialized via LazyServiceProxy)
    shopify_service = ctx.meta["shopify_service"]
    
    # Validate identifier
    if not identifier:
        click.echo("❌ Product identifier is required", err=True)
        raise click.ClickException("Product identifier is required")
    
    try:
        # Fetch product to get variants
        query_str = identifier.get("query", "")
        console.print(f"\n[cyan]Fetching product variants...[/cyan]\n")
        
        products = shopify_service.get_product_by_identifier(
            identifier,
            variants_first=10
        )
        
        if not products:
            click.echo("❌ No product found", err=True)
            raise click.ClickException(f"No product found with identifier: {identifier.get('identifier', 'N/A')}")
        
        product = products[0]
        
        # Get variants from product
        variants_conn = getattr(product, 'variants', None)
        if not variants_conn:
            console.print("[yellow]No variants found for this product.[/yellow]")
            return
        
        nodes = getattr(variants_conn, 'nodes', None)
        if not nodes:
            console.print("[yellow]No variants found for this product.[/yellow]")
            return
        
        # Build variants list
        variants = []
        for variant in nodes:
            inventory_item = getattr(variant, 'inventoryItem', None)
            inventory_item_id = None
            if inventory_item:
                inventory_item_id = getattr(inventory_item, 'id', None)
            
            variants.append({
                'id': getattr(variant, 'id', None),
                'title': getattr(variant, 'title', 'Unknown'),
                'inventory_quantity': getattr(variant, 'inventoryQuantity', None),
                'inventory_item_id': inventory_item_id
            })
        
        if not variants:
            console.print("[yellow]No variants found for this product.[/yellow]")
            return
        
        # Prompt for inventory update selection
        update_list = _prompt_inventory_selection(variants, console)
        
        # Process inventory updates using shared function
        process_inventory_updates(shopify_service, variants, update_list, console)
        
    except (RuntimeError, ValueError) as e:
        error_msg = str(e)
        click.echo(f"❌ Error: {error_msg}", err=True)
        raise click.ClickException(error_msg)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Inventory update cancelled by user.[/yellow]\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        raise click.ClickException(str(e))
