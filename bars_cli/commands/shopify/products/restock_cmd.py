"""Restock inventory for a Shopify order command."""

import sys
from typing import Dict, Any, Optional, List, Tuple, TypedDict
from datetime import datetime

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_ORDER_IDENTIFIER
from bars_cli.commands.shopify._shared.command_helpers import get_shopify_service


class InventoryAdjustmentRequest(TypedDict):
    """Request structure for inventory adjustment."""
    inventory_item_id: str
    location_id: str
    delta: int
    reason: str
    name: str
    reference_uri: Optional[str]


def _format_customer_name(order: Any) -> str:
    """Format customer name from order."""
    customer = getattr(order, 'customer', None)  # type: ignore[attr-defined]
    if not customer:
        return "N/A"
    
    if hasattr(customer, 'displayName') and customer.displayName:  # type: ignore[attr-defined]
        return customer.displayName  # type: ignore[attr-defined]
    
    first = getattr(customer, 'firstName', None)  # type: ignore[attr-defined]
    last = getattr(customer, 'lastName', None)  # type: ignore[attr-defined]
    if first or last:
        return f"{first or ''} {last or ''}".strip()
    
    return "N/A"


def _get_product_id_from_variant(variant_id: str, shopify_service: Any) -> Optional[str]:
    """Get product ID from variant ID."""
    from backend.modules.integrations.shopify.models.sgqlc_models.sgqlc_query import Query
    
    # Build query to get product from variant
    op = Query.build_variant_query(variant_id)
    
    try:
        response = shopify_service.client.execute(op)
        
        if response.get('errors'):
            return None
        
        query_result = op + response
        variant = getattr(query_result, 'productVariant', None)  # type: ignore[attr-defined]
        if variant:
            product = getattr(variant, 'product', None)  # type: ignore[attr-defined]
            if product:
                return getattr(product, 'id', None)  # type: ignore[attr-defined]
    except Exception:
        return None
    
    return None


def _fetch_all_product_variants(product_id: str, shopify_service: Any) -> List[Dict[str, Any]]:
    """Fetch all variants for a product."""
    from backend.modules.integrations.shopify.models.sgqlc_models.sgqlc_query import Query
    
    op = Query.build_product_query(f"id:{product_id}", first=1, variants_first=100)
    
    try:
        response = shopify_service.client.execute(op)
        
        if response.get('errors'):
            return []
        
        query_result = op + response
        products_conn = query_result.products  # type: ignore[attr-defined]
        if not products_conn or not products_conn.nodes:
            return []
        
        product = products_conn.nodes[0]
        variants_conn = getattr(product, 'variants', None)  # type: ignore[attr-defined]
        if not variants_conn:
            return []
        
        variants = []
        nodes = getattr(variants_conn, 'nodes', None)  # type: ignore[attr-defined]
        if nodes:
            for variant in nodes:
                variant_data = variant.__json_data__ if hasattr(variant, '__json_data__') else {}
                inventory_item = getattr(variant, 'inventoryItem', None)  # type: ignore[attr-defined]
                inventory_item_id = None
                if inventory_item:
                    inventory_item_id = getattr(inventory_item, 'id', None)  # type: ignore[attr-defined]
                
                variants.append({
                    'id': getattr(variant, 'id', None),  # type: ignore[attr-defined]
                    'title': getattr(variant, 'title', 'Unknown'),  # type: ignore[attr-defined]
                    'inventory_quantity': getattr(variant, 'inventoryQuantity', None),  # type: ignore[attr-defined]
                    'inventory_item_id': inventory_item_id
                })
        
        return variants
    except Exception:
        return []


def _get_first_location_id(shopify_service: Any) -> Optional[str]:
    """Get the first available location ID."""
    from backend.modules.integrations.shopify.models.sgqlc_models.sgqlc_query import Query
    
    op = Query.build_location_query(first=1)
    
    try:
        response = shopify_service.client.execute(op)
        
        if response.get('errors'):
            return None
        
        query_result = op + response
        locations_conn = getattr(query_result, 'locations', None)  # type: ignore[attr-defined]
        if locations_conn:
            nodes = getattr(locations_conn, 'nodes', None)  # type: ignore[attr-defined]
            if nodes and len(nodes) > 0:
                location = nodes[0]
                return getattr(location, 'id', None)  # type: ignore[attr-defined]
    except Exception:
        pass
    
    return None


def _prompt_restock_selection(
    line_items: List[Any],
    shopify_service: Any,
    console: Console
) -> List[Tuple[str, str, int]]:
    """
    Display product variants and prompt user for restock selection.
    
    Returns:
        List of tuples: (variant_id, inventory_item_id, quantity_to_restock)
    """
    if not line_items:
        return []
    
    console.print("\n[bold]📦 Product Variants - Inventory Status[/bold]\n")
    
    # Extract variant from first line item
    first_item = line_items[0]
    variant = getattr(first_item, 'variant', None)  # type: ignore[attr-defined]
    if not variant:
        console.print("[dim]No variants found to restock.[/dim]\n")
        return []
    
    variant_id = getattr(variant, 'id', None)  # type: ignore[attr-defined]
    if not variant_id:
        console.print("[dim]No variant ID found.[/dim]\n")
        return []
    
    # Get product ID from variant
    product_id = _get_product_id_from_variant(variant_id, shopify_service)
    if not product_id:
        console.print("[red]Could not find product ID.[/red]")
        return []
    
    # Fetch all variants for the product
    all_variants = _fetch_all_product_variants(product_id, shopify_service)
    
    if not all_variants:
        console.print("[yellow]No variants found for this product.[/yellow]")
        return []
    
    # Display variants table
    variants_table = Table(title="Available Variants", show_header=True)
    variants_table.add_column("#", justify="center")
    variants_table.add_column("Variant Name")
    variants_table.add_column("Current Inventory", justify="right")
    
    for i, variant_data in enumerate(all_variants, 1):
        inv_qty = variant_data.get('inventory_quantity', 0)
        variants_table.add_row(
            str(i),
            variant_data.get('title', 'Unknown'),
            str(inv_qty) if inv_qty is not None else "N/A"
        )
    
    console.print(variants_table)
    console.print()
    
    # Prompt for selection
    restock_list = []
    
    while True:
        selection = input("Enter variant number to restock (or 'done' to finish): ").strip().lower()
        
        if selection == 'done':
            break
        
        try:
            variant_index = int(selection) - 1
            if 0 <= variant_index < len(all_variants):
                selected_variant = all_variants[variant_index]
                
                # Default quantity to 1 (matching restock_order.py behavior)
                quantity = 1
                inventory_item_id = selected_variant.get('inventory_item_id')
                if inventory_item_id:
                    restock_list.append((selected_variant['id'], inventory_item_id, quantity))
                    console.print(f"[green]✓ Added {quantity} unit for {selected_variant['title']}[/green]")
                else:
                    console.print("[red]Error: No inventory item ID found for this variant.[/red]")
            else:
                console.print(f"[red]Invalid selection. Enter a number between 1 and {len(all_variants)}.[/red]")
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
) -> None:
    """
    Restock inventory for a Shopify order.
    
    Fetches order line items, displays available variants, and prompts for selection.
    Then adjusts inventory for selected variants.
    
    IDENTIFIER: Order number (1234 or #1234) or Order ID (gid://shopify/Order/123 or 123).
    
    Examples:
      bars shopify product restock 1234
      bars shopify product restock #1234
      bars shopify product restock gid://shopify/Order/123456789
    """
    console = Console()
    
    # Get service from context
    shopify_service = get_shopify_service(ctx, "order")
    
    # Validate identifier
    if not identifier:
        click.echo("❌ Order identifier is required", err=True)
        raise click.ClickException("Order identifier is required")
    
    try:
        # Fetch order
        order_num = identifier.get("identifier", "").strip().lstrip('#')
        console.print(f"\n[cyan]Fetching order details for #{order_num}...[/cyan]\n")
        
        orders = shopify_service.get_order_by_identifier(identifier, line_items_first=50)
        if not orders:
            click.echo("❌ No order found", err=True)
            raise click.ClickException(f"No order found with identifier: {identifier.get('identifier', 'N/A')}")
        
        order = orders[0]
        order_name = getattr(order, 'name', 'N/A')  # type: ignore[attr-defined]
        
        # Get line items
        line_items_conn = getattr(order, 'lineItems', None)  # type: ignore[attr-defined]
        if not line_items_conn:
            console.print("[yellow]No line items found.[/yellow]\n")
            return
        
        nodes = getattr(line_items_conn, 'nodes', None)  # type: ignore[attr-defined]
        if not nodes:
            console.print("[yellow]No line items found to restock.[/yellow]\n")
            return
        
        line_items = list(nodes)
        
        # Prompt for restock selection
        restock_list = _prompt_restock_selection(line_items, shopify_service, console)
        
        if not restock_list:
            console.print("[dim]No inventory changes made.[/dim]\n")
            return
        
        # Get location ID
        location_id = _get_first_location_id(shopify_service)
        if not location_id:
            console.print("[red]Error: No locations found. Cannot restock inventory.[/red]\n")
            raise click.ClickException("No locations found")
        
        # Process restocking
        console.print("[cyan]Processing inventory adjustments...[/cyan]\n")
        
        success_count = 0
        failure_count = 0
        
        for variant_id, inventory_item_id, quantity in restock_list:
            # Build request
            request: InventoryAdjustmentRequest = {
                "inventory_item_id": inventory_item_id,
                "location_id": location_id,
                "delta": quantity,
                "reason": "correction",
                "name": "available",
                "reference_uri": f"logistics://cli-restock/{datetime.utcnow().isoformat()}"
            }
            
            result = shopify_service.adjust_inventory(request)
            
            if result.get("success"):
                console.print(f"  [green]✓ Restocked +{quantity} units[/green]")
                success_count += 1
            else:
                error_msg = result.get("message") or result.get("error", "Unknown error")
                console.print(f"  [red]✗ Restock failed: {error_msg}[/red]")
                failure_count += 1
        
        console.print()
        
        # Summary
        if success_count > 0:
            console.print(f"[green]✓ Successfully restocked {success_count} variant(s)[/green]")
        if failure_count > 0:
            console.print(f"[yellow]⚠️  Failed to restock {failure_count} variant(s)[/yellow]")
        
        console.print()
        
        if failure_count > 0:
            raise click.ClickException(f"Failed to restock {failure_count} variant(s)")
        
    except (RuntimeError, ValueError) as e:
        error_msg = str(e)
        click.echo(f"❌ Error: {error_msg}", err=True)
        raise click.ClickException(error_msg)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Restock cancelled by user.[/yellow]\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        raise click.ClickException(str(e))

