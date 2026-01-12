"""Get Shopify customer details command."""
import json
import sys
import traceback
from typing import Dict, Any, Optional, List

import click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_CUSTOMER_IDENTIFIER
from bars_cli.commands.shopify._shared.shopify_formatters import _format_customer_option, format_customer
from bars_cli.commands.shopify._shared.command_helpers import handle_multiple_shopify_results
from bars_cli.commands.shopify._shared.command_helpers import handle_shopify_get_command
from bars_cli.backend_services.shopify.services.shopify_service import ShopifyService


@click.command('get')
@handle_display_options(display=True, exit_on_error=True)
@click.option('--one', 'must_return_one', is_flag=True, default=False, help='Require selecting exactly one customer (no "All" option)')
@click.argument('identifier', type=SHOPIFY_CUSTOMER_IDENTIFIER, required=False)
@click.pass_context
def get_customer_cmd(ctx: click.Context, identifier: Optional[Dict[str, Any]], must_return_one: bool = False) -> Optional[List[Any]]:
    """
    Get Shopify customer details by email, ID, or name.
    
    IDENTIFIER: Customer email, ID (gid://shopify/Customer/123 or 123), or name.
    Name formats: "First Last", "f:First", "l:Last" (with or without # prefix).
    
    Examples:
      bars shopify customer get customer@example.com
      bars shopify customer get gid://shopify/Customer/123456789
      bars shopify customer get 123456789
      bars shopify customer get "John Doe"
      bars shopify customer get f:John
      bars --json shopify customer get customer@example.com
    """
    
    shopify_service: ShopifyService = ctx.meta['shopify_service']
    
    return handle_shopify_get_command(
        ctx=ctx,
        identifier=identifier,
        service_method=shopify_service.get_customer_by_identifier,
        entity_name="customer",
        format_func=format_customer,
        handle_multiple_func=(
            handle_multiple_shopify_results,
            {
                "entity_name": "customer",
                "format_option_func": _format_customer_option,
                "must_return_one": must_return_one
            }
        ),
        service_method_kwargs={"orders_first": 5},
        identifier_required_msg="Customer identifier is required"
    )

