"""Get Shopify customer details command."""

from typing import Dict, Any, Optional, List, TYPE_CHECKING

import click

from bars_cli._core.context import get_service
from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_CUSTOMER_IDENTIFIER
from bars_cli._core.ui.styling import get_console
from bars_cli.backend_services.shopify.services.shopify_service import ShopifyService
from bars_cli.commands.shopify._shared.command_helpers import (
    handle_multiple_shopify_results,
    handle_shopify_response,
    handle_shopify_error_response,
    validate_identifier,
)
from bars_cli.commands.shopify._shared.customer_properties import (
    process_customer_birthday,
    process_customer_pronouns,
)
from bars_cli.commands.shopify._shared.shopify_formatters import (
    _format_customer_option,
    format_customer,
    format_customer_rich,
)

if TYPE_CHECKING:
    from bars_cli.backend_services.shopify.models.sgqlc_models import Customer
else:
    Customer = Any


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
    from bars_cli._core.context import get_display_context
    from bars_cli.commands.shopify._shared.shopify_formatters import format_error
    import traceback
    
    json_output, should_display = get_display_context(ctx)
    console = get_console("formatted", ctx=ctx) if should_display and not json_output else None
    
    # Validate identifier
    validate_identifier(identifier, "customer", json_output, should_display, "Customer identifier is required")
    
    # After validation, identifier is guaranteed to be not None
    assert identifier is not None
    
    try:
        # Display lookup message
        if should_display and not json_output:
            lookup_value = identifier.get("identifier", "customer")
            click.echo(f"🔍 Looking up: {lookup_value}", err=True)
        
        # Get Shopify service (lazily initialized on first access via LazyServiceProxy)
        shopify_service: ShopifyService = get_service(ctx, 'shopify_service')
        
        # Create enhanced formatter that includes birthday and pronouns
        def format_customer_with_properties(customer: Customer) -> str:
            """Format customer with birthday and pronouns extracted from orders."""
            birthdays = []
            pronouns = []
            
            try:
                birthdays = process_customer_birthday(shopify_service, customer)  # type: ignore[arg-type]
                if should_display and not json_output:
                    import sys
                    if birthdays:
                        print(f"[DEBUG] Found {len(birthdays)} birthday(s)", file=sys.stderr)
                    else:
                        print("[DEBUG] No birthdays found in orders", file=sys.stderr)
            except Exception as e:
                if should_display and not json_output:
                    import sys
                    print(f"Warning: Could not fetch birthdays: {e}", file=sys.stderr)
            
            try:
                pronouns = process_customer_pronouns(shopify_service, customer)  # type: ignore[arg-type]
                if should_display and not json_output:
                    import sys
                    if pronouns:
                        print(f"[DEBUG] Found {len(pronouns)} pronoun(s)", file=sys.stderr)
                    else:
                        print("[DEBUG] No pronouns found in orders", file=sys.stderr)
            except Exception as e:
                if should_display and not json_output:
                    import sys
                    print(f"Warning: Could not fetch pronouns: {e}", file=sys.stderr)
            
            if console is not None:
                format_customer_rich(
                    customer,
                    console=console,
                    ctx=ctx,
                    birthdays=birthdays if birthdays else None,
                    pronouns=pronouns if pronouns else None
                )
                return ""  # Rich prints directly, return empty string for compatibility
            else:
                return format_customer(customer, birthdays=birthdays if birthdays else None, pronouns=pronouns if pronouns else None)
        
        # Call service method
        try:
            entities = shopify_service.get_customer_by_identifier(identifier, orders_first=5)
        except (RuntimeError, ValueError) as e:
            handle_shopify_error_response(e, json_output, should_display)
        
        # Route response to appropriate handler
        return handle_shopify_response(
            entities=entities,
            identifier=identifier,
            entity_name="customer",
            json_output=json_output,
            should_display=should_display,
            format_func=format_customer_with_properties,
            handle_multiple_func=(
                handle_multiple_shopify_results,
                {
                    "entity_name": "customer",
                    "format_option_func": _format_customer_option,
                    "format_func": format_customer_with_properties,
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

