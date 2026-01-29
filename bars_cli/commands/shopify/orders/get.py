"""Get Shopify order command."""

from typing import Dict, Any, Optional, List, TYPE_CHECKING

import click_extra as click
from rich.console import Console

from bars_cli._core.context import get_display_context, get_service
from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_ORDER_IDENTIFIER
from bars_cli._core.ui.styling import get_console
from bars_cli.backend_services.shared.csv.csv_io import write_csv_file
from bars_cli.commands.shopify._shared.command_helpers import (
    handle_multiple_shopify_results,
    handle_shopify_response,
    handle_shopify_error_response,
    validate_identifier,
    write_csv_dict_to_stdout,
)
from bars_cli.commands.shopify._shared.shopify_formatters import (
    _format_order_option,
    format_order_rich,
)

if TYPE_CHECKING:
    from bars_cli.backend_services.shopify.models.sgqlc_models import Order
else:
    Order = Any


def display_order(
    order: Order,
    shopify_service: Any,
    csv: bool,
    csv_file: Optional[str],
    show_properties: bool,
    console: Console
) -> str:
    """Display order using formatters directly.
    
    Returns empty string since Rich prints directly.
    """
    if csv or csv_file:
        order_dict = shopify_service.order_to_csv_dict(order)
        if csv_file:
            write_csv_file([order_dict], file_path=csv_file)
            click.echo(f"CSV written to {csv_file}", err=True)
        else:
            write_csv_dict_to_stdout([order_dict])
    else:
        # Calculate total paid and format it
        payment_summary = shopify_service.calculate_payment_summary(order)
        total_amount = payment_summary.get('total_amount', 0.0)
        currency = payment_summary.get('currency', 'USD')
        total_paid = f"${total_amount:.2f} {currency}" if total_amount > 0 else "N/A"
        
        format_order_rich(order, console=console, show_properties=show_properties, total_paid=total_paid)
    return ""  # Rich prints directly, return empty string for compatibility




@click.command('get')
@handle_display_options(display=True, exit_on_error=True)
@click.option('--one', 'must_return_one', is_flag=True, default=False, help='Require selecting exactly one order (no "All" option)')
@click.option('-P', '--show-properties', 'show_properties', is_flag=True, default=False, help='Show line item custom attributes')
@click.option('--csv', is_flag=True, default=False, help='Output as CSV format matching Shopify export')
@click.option('--csv-file', type=click.Path(), help='Write CSV to file instead of stdout')
@click.argument('identifier', type=SHOPIFY_ORDER_IDENTIFIER, required=False)
@click.pass_context
def get_order_cmd(
    ctx: click.Context,
    identifier: Optional[Dict[str, Any]],
    must_return_one: bool = False,
    show_properties: bool = False,
    csv: bool = False,
    csv_file: Optional[str] = None
) -> Optional[List[Any]]:
    """
    Get Shopify order details by order number or ID.
    
    IDENTIFIER: Order number (1234 or #1234) or Order ID (gid://shopify/Order/123 or 123).
    
    Examples:
      bars shopify order get 1234
      bars shopify order get #1234
      bars shopify order get gid://shopify/Order/123456789
      bars shopify order get 123456789
      bars --json shopify order get 1234
      bars shopify order get 1234 --show-properties
      bars shopify order get 1234 --csv
    """
    json_output, should_display = get_display_context(ctx)
    console = get_console("formatted", ctx=ctx) if should_display and not json_output else Console()
    
    # Validate identifier
    validate_identifier(identifier, "order", json_output, should_display, "Order identifier is required")
    
    # After validation, identifier is guaranteed to be not None
    assert identifier is not None
    
    try:
        # Display lookup message
        if should_display and not json_output:
            lookup_value = identifier.get("identifier", "order")
            click.echo(f"🔍 Looking up: {lookup_value}", err=True)
        
        # Get Shopify service (lazily initialized on first access via LazyServiceProxy)
        shopify_service = get_service(ctx, 'shopify_service')
        
        def format_order_wrapper(order: Order) -> str:
            """Wrapper for display_order to match expected signature."""
            return display_order(order, shopify_service, csv, csv_file, show_properties, console)
        
        # Call service method
        try:
            entities = shopify_service.get_order_by_identifier(identifier, line_items_first=5)  # type: ignore[attr-defined]
        except (RuntimeError, ValueError) as e:
            handle_shopify_error_response(e, json_output, should_display)
        
        # Route response to appropriate handler
        return handle_shopify_response(
            entities=entities,
            identifier=identifier,
            entity_name="order",
            json_output=json_output,
            should_display=should_display,
            format_func=format_order_wrapper,
            handle_multiple_func=(
                handle_multiple_shopify_results,
                {
                    "entity_name": "order",
                    "format_option_func": _format_order_option,
                    "format_func": format_order_wrapper,
                    "must_return_one": must_return_one
                }
            )
        )
        
    except click.ClickException:
        # Re-raise Click exceptions - decorator will handle exit
        raise
    except Exception as e:
        from bars_cli.commands.shopify._shared.shopify_formatters import format_error
        import traceback
        error_type = type(e).__name__
        error_msg = str(e)
        format_error(error_msg, error_type=error_type, json_output=json_output, should_display=should_display)
        if should_display and not json_output:
            click.echo(traceback.format_exc(), err=True)
        raise click.ClickException(error_msg)

