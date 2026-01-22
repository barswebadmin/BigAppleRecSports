"""Get Shopify product details command."""
from typing import Dict, Any, Optional, List, TYPE_CHECKING

import click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_PRODUCT_IDENTIFIER
from bars_cli.backend_services.shopify.models.sgqlc_models import Product
from bars_cli.commands.shopify._shared.shopify_formatters import format_product, _format_product_option
from bars_cli.commands.shopify._shared.command_helpers import handle_multiple_shopify_results

if TYPE_CHECKING:
    from sgqlc.types import Type as SGQLCType
    ProductSGQLCType = SGQLCType
else:
    ProductSGQLCType = Any


@click.command('get')
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
    from bars_cli.commands.shopify._shared.command_helpers import handle_shopify_get_command
    
    # Service is lazily initialized on first access via LazyServiceProxy
    # ctx.meta["shopify_service"] contains a proxy that creates the service on first attribute access
    shopify_service = ctx.meta["shopify_service"]
    
    return handle_shopify_get_command(
        ctx=ctx,
        identifier=identifier,
        service_method=shopify_service.get_product_by_identifier,  # type: ignore[attr-defined]
        entity_name="product",
        format_func=format_product,
        handle_multiple_func=(
            handle_multiple_shopify_results,
            {
                "entity_name": "product",
                "format_option_func": _format_product_option,
                "must_return_one": must_return_one
            }
        ),
        service_method_kwargs={"variants_first": 5},
        identifier_required_msg="Product identifier is required"
    )

