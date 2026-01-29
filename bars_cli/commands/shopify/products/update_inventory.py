"""Update inventory for Shopify product variants command."""

import sys
import traceback
from typing import Dict, Any, Optional, List, Tuple, TYPE_CHECKING

import click_extra as click
from rich.console import Console

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_PRODUCT_IDENTIFIER
from bars_cli.commands.shopify._shared.command_helpers import (
    extract_variants_from_product,
    process_inventory_updates,
)
from bars_cli.commands.shopify._shared.shopify_formatters import (
    format_variants_table,
    format_restock_result,
    format_restock_summary,
)

if TYPE_CHECKING:
    from bars_cli.backend_services.shopify.models.sgqlc_models import Product, ProductVariant
else:
    Product = Any
    ProductVariant = Any


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




@click.command(name='update-inventory', aliases=['update-inventory'])
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
        variants = extract_variants_from_product(product)
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
        traceback.print_exc()
        raise click.ClickException(str(e))
