"""Get Shopify order details command.

# ============================================================================
# MISSING FUNCTIONALITY FROM get_order_details_pydantic.py
# ============================================================================
# 
# The following features from get_order_details_pydantic.py are not yet
# implemented in this CLI command:
#
# 1. JSON OUTPUT DEFAULT BEHAVIOR
#    - get_order_details_pydantic.py: --json flag defaults to True
#    - CLI: --json flag is opt-in (requires explicit flag)
#    - Impact: Pydantic script outputs raw JSON by default, CLI outputs Rich formatted
#
# 2. ENVIRONMENT SELECTION
#    - get_order_details_pydantic.py: get_order_by_identifier() accepts environment parameter
#      (defaults to "production", but can be "staging" or "development")
#    - CLI: Uses context-based service initialization (environment may be set globally)
#    - Impact: Cannot easily switch environments per-command in CLI
#    - TODO: Add --env flag to allow environment selection per command
#
# 3. INTERACTIVE PROMPT WHEN IDENTIFIER MISSING
#    - get_order_details_pydantic.py: Prompts user for identifier if --id/--number not provided
#    - CLI: Uses Click's required=False, but may not prompt interactively
#    - Impact: Different UX - pydantic script always prompts, CLI may error
#    - TODO: Ensure Click parameter type handles interactive prompting
#
# 4. SEPARATE --id AND --number FLAGS
#    - get_order_details_pydantic.py: Has separate --id and --number flags
#    - CLI: Uses unified identifier argument with SHOPIFY_ORDER_IDENTIFIER type
#    - Impact: Different CLI interface (unified vs separate flags)
#    - Note: Unified approach is likely better UX, but different from original
#
# 5. LOGGING CONFIGURATION
#    - get_order_details_pydantic.py: Configures logging (WARNING level, stderr handler)
#    - CLI: Uses default logging configuration
#    - Impact: May have different log output behavior
#    - TODO: Consider adding logging configuration if needed
#
# 6. DIRECT JSON OUTPUT FORMAT
#    - get_order_details_pydantic.py: Outputs order.__json_data__ directly as JSON array
#    - CLI: Uses Rich formatting by default, JSON via --json flag
#    - Impact: Different output format (pydantic script always JSON array, CLI can be formatted)
#    - Note: CLI approach is more flexible with Rich formatting
#
# ============================================================================
# ADDITIONAL FEATURES IN CLI (NOT IN get_order_details_pydantic.py)
# ============================================================================
#
# The CLI has these additional features not present in get_order_details_pydantic.py:
#
# - Rich formatted display (tables, panels, colors)
# - CSV export (--csv, --csv-file flags)
# - Line item properties display (--show-properties flag)
# - Multiple results handling with selection (--one flag)
# - Service abstraction (uses ShopifyService instead of direct client calls)
#
# ============================================================================
"""
import json
import sys
from typing import Dict, Any, Optional, List, TYPE_CHECKING

import click
from rich.console import Console

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_ORDER_IDENTIFIER
from bars_cli.commands.shopify.orders.order_formatters import format_order_rich

if TYPE_CHECKING:
    from sgqlc.types import Type as SGQLCType
    OrderSGQLCType = SGQLCType
else:
    OrderSGQLCType = Any


def format_order(order: Any, show_properties: bool = False) -> None:
    """Format order data for display using Rich.
    
    Args:
        order: Order object (sgqlc Type instance)
        show_properties: Whether to show line item custom attributes
    """
    console = Console()
    format_order_rich(order, console=console, show_properties=show_properties)


def _format_order_option(order: Any) -> str:
    """Format order for display in selection options."""
    order_name = getattr(order, 'name', 'N/A')  # type: ignore[attr-defined]
    order_email = getattr(order, 'email', 'N/A')  # type: ignore[attr-defined]
    return f"{order_name} ({order_email})"


def handle_multiple_results(orders: List[Any], json_output: bool, should_display: bool, must_return_one: bool = False) -> Optional[Any]:
    """Handle selection when multiple orders are found.
    
    Args:
        orders: List of order objects
        json_output: Whether to output JSON format
        should_display: Whether to display output
        must_return_one: If True, requires selecting exactly one order (no "All" option)
        
    Returns:
        Selected order object, list of all orders if "All" selected, or None if cancelled
    """
    from bars_cli.commands.shopify._shared.command_helpers import handle_multiple_shopify_results
    return handle_multiple_shopify_results(
        items=orders,
        json_output=json_output,
        should_display=should_display,
        format_option_func=_format_order_option,
        entity_name="order",
        must_return_one=must_return_one
    )


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
    from bars_cli.commands.shopify._shared.command_helpers import handle_shopify_get_command
    from bars_cli._core.context import get_display_context
    
    # Service is guaranteed to be available (initialized in shopify group)
    shopify_service = ctx.meta.get('shopify_service')
    
    json_output, should_display = get_display_context(ctx)
    
    def format_order_wrapper(order: Any) -> str:
        """Wrapper to pass show_properties to format_order.
        
        Returns empty string since Rich prints directly.
        """
        if csv or csv_file:
            _output_order_csv(order, csv_file)
        else:
            format_order(order, show_properties=show_properties)
        return ""  # Rich prints directly, return empty string for compatibility
    
    return handle_shopify_get_command(
        ctx=ctx,
        identifier=identifier,
        service_method=shopify_service.get_order_by_identifier,  # type: ignore[attr-defined]
        entity_name="order",
        format_func=format_order_wrapper,
        handle_multiple_func=(handle_multiple_results, {"must_return_one": must_return_one}),
        service_method_kwargs={"line_items_first": 5},
        identifier_required_msg="Order identifier is required"
    )


def _output_order_csv(order: Any, csv_file: Optional[str] = None) -> None:
    """Output order as CSV."""
    from bars_cli._core.ui.csv_export import write_csv_to_file, write_csv_to_stdout
    from bars_cli.commands.shopify.orders.csv_formatter import order_to_csv_row, get_csv_headers
    
    # Convert order to dict format for CSV
    order_dict = order.__json_data__ if hasattr(order, '__json_data__') else {}
    
    headers = get_csv_headers()
    row = order_to_csv_row(order_dict)
    
    if csv_file:
        write_csv_to_file(headers, [row], csv_file)
        click.echo(f"CSV written to {csv_file}", err=True)
    else:
        write_csv_to_stdout(headers, [row])

