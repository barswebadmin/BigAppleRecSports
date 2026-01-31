"""Get orders for a product command."""

from typing import Dict, Any, Optional, List, TYPE_CHECKING, cast
from datetime import datetime
from dateutil.relativedelta import relativedelta
import traceback

import click_extra as click
from rich.console import Console

from bars_cli._core.context import get_display_context
from bars_cli._core.legacy_services import get_service
from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_PRODUCT_IDENTIFIER
from bars_cli.backend_services.shared.csv.csv_io import write_csv_file
from bars_cli.commands.shopify._shared.command_helpers import (
    handle_shopify_error_response,
    handle_shopify_response,
    validate_identifier,
    write_csv_dict_to_stdout,
)
from bars_cli.commands.shopify._shared.shopify_formatters import (
    format_error,
    display_orders_table,
    extract_id_short,
)
from bars_cli._core.prompts import prompt_select_from_options

if TYPE_CHECKING:
    from bars_cli.backend_services.shopify.models.sgqlc_models import Product, Order
else:
    Product = Any
    Order = Any



@click.command(name='product-orders', aliases=['orders', 'get-orders'])
@handle_display_options(display=True, exit_on_error=True)
@click.option('--csv', is_flag=True, default=False, help='Output as CSV format matching Shopify export (skip prompt)')
@click.option('--csv-file', type=click.Path(), help='Write CSV to file instead of stdout (skip prompt)')
@click.argument('identifier', type=SHOPIFY_PRODUCT_IDENTIFIER, required=False)
@click.pass_context
def product_orders_cmd(
    ctx: click.Context,
    identifier: Optional[Dict[str, Any]],
    csv: bool = False,
    csv_file: Optional[str] = None
) -> Optional[List[Any]]:
    """
    Get all orders containing a specific product (automatic pagination within 4-month window).
    
    IDENTIFIER: Product ID (gid://shopify/Product/123 or 123) or product handle.
    
    Examples:
      bars shopify product orders 123456789
      bars shopify product orders gid://shopify/Product/123456789
      bars shopify product orders 2025-fall-kickball-sunday-open-division
      bars shopify product orders 123456789 --csv
      bars shopify product orders 123456789 --csv-file orders.csv
    """
    json_output, should_display = get_display_context(ctx)
    console = Console()
    
    # Validate identifier
    validate_identifier(identifier, "product", json_output, should_display, "Product identifier is required")
    
    # After validation, identifier is guaranteed to be not None
    assert identifier is not None
    
    try:
        # Display lookup message
        if should_display and not json_output:
            lookup_value = identifier.get("identifier", "product")
            click.echo(f"🔍 Looking up orders for product: {lookup_value}", err=True)
        
        # Get Shopify service (lazily initialized on first access via LazyServiceProxy)
        shopify_service = get_service(ctx, 'shopify_service')
        
        # Fetch product (service handles all identifier formats)
        try:
            products = shopify_service.get_product_by_identifier(identifier, variants_first=1)  # type: ignore[attr-defined]
        except (RuntimeError, ValueError) as e:
            handle_shopify_error_response(e, json_output, should_display)
        
        if not products:
            raise click.ClickException(f"No product found with identifier: {identifier.get('identifier', 'N/A')}")
        
        product = products[0]
        product_id = extract_id_short(cast(str, product.id))
        
        # Get product creation date and calculate 4-month window
        product_created_at_str = cast(str, product.createdAt)
        product_created_at = datetime.fromisoformat(product_created_at_str.replace('Z', '+00:00'))
        end_date = product_created_at + relativedelta(months=4)
        
        # Format dates for Shopify query (YYYY-MM-DD format)
        start_date_str = product_created_at.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # Prompt for output format if not specified via flags
        output_to_csv = csv or csv_file is not None
        if not output_to_csv and should_display and not json_output:
            output_options = [
                {"value": "terminal", "display": "Display in terminal (formatted table)"},
                {"value": "csv_file", "display": "Export to CSV file"},
                {"value": "csv_stdout", "display": "Print CSV to stdout"}
            ]
            selected = prompt_select_from_options(
                "How would you like to view the results?",
                output_options
            )

            if selected is None:
                raise click.Abort()

            if selected == "csv_file":  # Export to CSV file
                csv_file = click.prompt("Enter CSV file path", type=str)
                output_to_csv = True
            elif selected == "csv_stdout":  # Print CSV to stdout
                csv = True
                output_to_csv = True
            # else: Display in terminal (default)
        
        # Fetch all orders with automatic pagination (within 4-month window)
        # Date filtering: only orders from product creation date to 4 months later
        try:
            all_orders = []
            cursor = None
            page_size = 250  # Use larger page size for efficiency (matching bars-scripts)
            page_num = 1
            
            if should_display and not json_output:
                console.print(f"[cyan]Fetching all orders from {start_date_str} to {end_date_str} (automatic pagination)...[/cyan]\n")
            
            while True:
                page_orders, next_cursor = shopify_service.get_orders_by_product(  # type: ignore[attr-defined]
                    product_id=product_id,
                    first=page_size,
                    after=cursor,
                    line_items_first=5,
                    created_at_min=start_date_str,
                    created_at_max=end_date_str
                )
                all_orders.extend(page_orders)
                
                if should_display and not json_output:
                    click.echo(f"Page {page_num}: Found {len(page_orders)} order(s) (total: {len(all_orders)})", err=True)
                
                if not next_cursor:
                    break
                cursor = next_cursor
                page_num += 1
            
            orders = all_orders
            
            if should_display and not json_output:
                console.print(f"[green]Fetched {len(orders)} total order(s) across {page_num} page(s)[/green]\n")
        except (RuntimeError, ValueError) as e:
            handle_shopify_error_response(e, json_output, should_display)
        
        # Handle empty results
        if not orders:
            if should_display:
                if json_output:
                    from bars_cli._core.utils.json_output import output_json_list
                    output_json_list([])
                else:
                    console.print(f"[yellow]No orders found for product ID: {product_id}[/yellow]\n")
            return []
        
        # Handle CSV output
        if output_to_csv:
            order_dicts = [shopify_service.order_to_csv_dict(order) for order in orders]
            if csv_file:
                write_csv_file(order_dicts, file_path=csv_file)
                click.echo(f"CSV written to {csv_file}", err=True)
            else:
                write_csv_dict_to_stdout(order_dicts)
            return orders
        
        # Handle JSON output
        if json_output:
            from bars_cli._core.utils.json_output import output_json_list
            output_json_list(orders)
            return orders
        
        # Handle formatted display
        if should_display:
            display_orders_table(orders, shopify_service, console)
        
        return orders
        
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
