"""Restock inventory for a Shopify order command."""

import json
import sys
import traceback
from typing import Dict, Any, Optional, List, Tuple, TYPE_CHECKING, cast

import click
from rich.console import Console

from bars_cli._core.context import get_display_context
from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_ORDER_IDENTIFIER
from bars_cli.commands.shopify._shared.command_helpers import (
    extract_variant_id_from_line_items,
)
from bars_cli.commands.shopify._shared.shopify_formatters import (
    _get_line_items,
    format_variants_table,
    format_restock_result,
    format_restock_summary,
)
from bars_cli.commands.shopify._shared.command_helpers import process_inventory_updates

if TYPE_CHECKING:
    from bars_cli.backend_services.shopify.models.sgqlc_models import Order, LineItem, ProductVariant
else:
    Order = Any
    LineItem = Any
    ProductVariant = Any




def _prompt_restock_selection(
    variants: List[Dict[str, Any]],
    console: Console
) -> List[Tuple[str, str, int]]:
    """Prompt user for restock selection.
    
    Returns:
        List of tuples (variant_id, inventory_item_id, delta)
    """
    restock_list = []
    console.print("\n[bold]📦 Product Variants - Inventory Status[/bold]\n")
    format_variants_table(variants, console)
    
    while True:
        selection = input("Enter variant number to restock (or 'done' to finish): ").strip().lower()
        
        if selection == 'done':
            break
        
        try:
            variant_index = int(selection) - 1
            if 0 <= variant_index < len(variants):
                selected_variant = variants[variant_index]
                inventory_item_id = selected_variant.get('inventory_item_id')
                if inventory_item_id:
                    # Default to +1 for restock - don't print success until mutation succeeds
                    restock_list.append((selected_variant['id'], inventory_item_id, 1))
                else:
                    console.print("[red]Error: No inventory item ID found for this variant.[/red]")
            else:
                console.print(f"[red]Invalid selection. Enter a number between 1 and {len(variants)}.[/red]")
        except ValueError:
            console.print("[red]Invalid input. Enter a number or 'done'.[/red]")
    
    return restock_list




@click.command('restock')
@handle_display_options(display=True, exit_on_error=True)
@click.argument('identifier', type=SHOPIFY_ORDER_IDENTIFIER, required=False)
@click.pass_context
def restock_cmd(
    ctx: click.Context,
    identifier: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Restock inventory for a Shopify order.
    
    Fetches order line items, displays available variants, and prompts for selection.
    Then adjusts inventory for selected variants.
    
    IDENTIFIER: Order number (1234 or #1234) or Order ID (gid://shopify/Order/123 or 123).
    
    Examples:
      bars shopify orders restock 1234
      bars shopify orders restock #1234
      bars shopify orders restock gid://shopify/Order/123456789
    """
    console = Console()
    json_output, should_display = get_display_context(ctx)
    
    # Get service from context (lazily initialized via LazyServiceProxy)
    shopify_service = ctx.meta["shopify_service"]
    
    # Validate identifier
    if not identifier:
        click.echo("❌ Order identifier is required", err=True)
        raise click.ClickException("Order identifier is required")
    
    try:
        # Fetch order
        order_num = identifier.get("identifier", "").strip().lstrip('#')
        console.print(f"\n[cyan]Fetching order details for #{order_num}...[/cyan]\n")
        
        orders = shopify_service.get_order_by_identifier(identifier, line_items_first=5)
        if not orders:
            raise click.ClickException(f"No order found with identifier: {identifier.get('identifier', 'N/A')}")
        order = orders[0]
        order_name = cast(str, order.name)
        
        # Get line items
        line_items = _get_line_items(order)
        if not line_items:
            console.print("[yellow]No line items found.[/yellow]\n")
            return
        
        # Get variant ID from first line item
        variant_id = extract_variant_id_from_line_items(line_items)
        if not variant_id:
            console.print("[dim]No variants found to restock.[/dim]\n")
            return
        
        # Get all variants for the product using service method
        try:
            variants = shopify_service.get_product_variants_for_restock(variant_id)
            if not variants:
                console.print("[yellow]No variants found for this product.[/yellow]")
                return
        except ValueError as e:
            error_msg = str(e)
            console.print(f"[red]❌ Error fetching variants:[/red]")
            console.print(f"[red]{error_msg}[/red]\n")
            raise click.ClickException(error_msg)
        
        # Prompt for restock selection (defaults to +1 for restock)
        restock_list = _prompt_restock_selection(variants, console)
        
        # If no variants selected, exit successfully
        if not restock_list:
            console.print("[dim]No inventory changes made.[/dim]\n")
            return {
                "success": True,
                "order_name": order_name,
                "restocked_variants": 0,
                "message": "No variants selected for restock"
            }
        
        # Process inventory updates using shared function
        results = process_inventory_updates(shopify_service, variants, restock_list, console)
        
        # Handle JSON output
        if json_output:
            # Collect raw responses from all results
            raw_responses = [r.get("raw_response", r.get("data", {})) for r in results]
            click.echo(json.dumps(raw_responses if len(raw_responses) > 1 else (raw_responses[0] if raw_responses else {}), indent=2, default=str))
            return raw_responses[0] if raw_responses else {}
        
        # Return success result
        return {
            "success": True,
            "order_name": order_name,
            "restocked_variants": len(restock_list),
            "message": f"Successfully restocked {len(restock_list)} variant(s)",
            "results": results
        }
        
    except (RuntimeError, ValueError) as e:
        error_msg = str(e)
        click.echo(f"❌ Error: {error_msg}", err=True)
        raise click.ClickException(error_msg)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Restock cancelled by user.[/yellow]\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        traceback.print_exc()
        raise click.ClickException(str(e))

