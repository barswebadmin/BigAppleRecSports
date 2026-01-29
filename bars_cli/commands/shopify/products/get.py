"""Get Shopify product details command."""

from typing import Dict, Any, Optional, List, TYPE_CHECKING

import click_extra as click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_PRODUCT_IDENTIFIER
from bars_cli._core.context import get_display_context
from bars_cli._core.ui.styling import get_console
from bars_cli.commands.shopify._shared.command_helpers import (
    handle_multiple_shopify_results,
    handle_shopify_response,
    handle_shopify_error_response,
    validate_identifier,
)
from bars_cli.commands.shopify._shared.shopify_formatters import format_error
import traceback
from bars_cli.commands.shopify._shared.shopify_formatters import (
    _format_product_option,
    format_product,
    format_product_rich,
)

if TYPE_CHECKING:
    from bars_cli.backend_services.shopify.models.sgqlc_models import Product
else:
    Product = Any


@click.command(name='get-product', aliases=['get'])
@handle_display_options(display=True, exit_on_error=True)
@click.option('--one', 'must_return_one', is_flag=True, default=False, help='Require selecting exactly one product (no "All" option)')
@click.argument('identifier', type=SHOPIFY_PRODUCT_IDENTIFIER, required=False)
@click.pass_context
def get_product_cmd(ctx: click.Context, identifier: Optional[Dict[str, Any]], must_return_one: bool = False) -> Optional[List[Any]]:
    """
    Get Shopify product details by product ID or handle.
    
    IDENTIFIER: Product ID (gid://shopify/Product/123 or 123) or product handle.
    
    Examples:
      bars shopify product get 123456789
      bars shopify product get gid://shopify/Product/123456789
      bars shopify product get 2025-fall-kickball-sunday-open-division
      bars --json shopify product get 123456789
    """
    json_output, should_display = get_display_context(ctx)
    console = get_console("formatted", ctx=ctx) if should_display and not json_output else None
    
    # Validate identifier
    validate_identifier(identifier, "product", json_output, should_display, "Product identifier is required")
    
    # After validation, identifier is guaranteed to be not None
    assert identifier is not None
    
    try:
        # Display lookup message
        if should_display and not json_output:
            lookup_value = identifier.get("identifier", "product")
            click.echo(f"🔍 Looking up: {lookup_value}", err=True)
        
        # Get Shopify service (lazily initialized on first access via LazyServiceProxy)
        shopify_service = ctx.meta["shopify_service"]
        
        def format_product_wrapper(product: Product) -> str:
            """Wrapper for format_product_rich to match expected signature."""
            if console is not None:
                format_product_rich(product, console=console, ctx=ctx)
                return ""  # Rich prints directly, return empty string for compatibility
            else:
                return format_product(product)  # Fallback to string formatter
        
        # Call service method
        try:
            entities = shopify_service.get_product_by_identifier(identifier, variants_first=5)  # type: ignore[attr-defined]
        except (RuntimeError, ValueError) as e:
            handle_shopify_error_response(e, json_output, should_display)
        
        # Route response to appropriate handler
        return handle_shopify_response(
            entities=entities,
            identifier=identifier,
            entity_name="product",
            json_output=json_output,
            should_display=should_display,
            format_func=format_product_wrapper,
            handle_multiple_func=(
                handle_multiple_shopify_results,
                {
                    "entity_name": "product",
                    "format_option_func": _format_product_option,
                    "format_func": format_product_wrapper,
                    "must_return_one": must_return_one
                }
            )
        )
        
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

