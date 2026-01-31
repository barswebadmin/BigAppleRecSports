"""Get Shopify customer details command."""

from typing import Dict, Any, Optional, List, TYPE_CHECKING

import click_extra as click

from bars_cli._core.legacy_services import get_service
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


@click.command(name='get-customer', aliases=['get'])
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
    import sys
    import logging
    logger = logging.getLogger(__name__)
    
    from bars_cli._core.context import get_display_context
    from bars_cli.commands.shopify._shared.shopify_formatters import format_error
    import traceback
    
    print("[DEBUG] get_customer_cmd: Entry point", file=sys.stderr)
    logger.debug("get_customer_cmd: Entry point")
    
    json_output, should_display = get_display_context(ctx)
    console = get_console("formatted", ctx=ctx) if should_display and not json_output else None
    
    print(f"[DEBUG] get_customer_cmd: json_output={json_output}, should_display={should_display}", file=sys.stderr)
    logger.debug(f"get_customer_cmd: json_output={json_output}, should_display={should_display}")
    
    # Validate identifier
    print("[DEBUG] get_customer_cmd: Validating identifier", file=sys.stderr)
    logger.debug("get_customer_cmd: Validating identifier")
    validate_identifier(identifier, "customer", json_output, should_display, "Customer identifier is required")
    
    # After validation, identifier is guaranteed to be not None
    assert identifier is not None
    
    print(f"[DEBUG] get_customer_cmd: Identifier validated: {identifier}", file=sys.stderr)
    logger.debug(f"get_customer_cmd: Identifier validated: {identifier}")
    
    try:
        # Display lookup message
        if should_display and not json_output:
            lookup_value = identifier.get("identifier", "customer")
            click.echo(f"🔍 Looking up: {lookup_value}", err=True)
        
        # Get Shopify service (lazily initialized on first access via LazyServiceProxy)
        print("[DEBUG] get_customer_cmd: Getting shopify_service from context", file=sys.stderr)
        logger.debug("get_customer_cmd: Getting shopify_service from context")
        shopify_service: ShopifyService = get_service(ctx, 'shopify_service')
        print(f"[DEBUG] get_customer_cmd: shopify_service obtained: {type(shopify_service)}", file=sys.stderr)
        logger.debug(f"get_customer_cmd: shopify_service obtained: {type(shopify_service)}")
        
        # Create enhanced formatter that includes birthday and pronouns
        def format_customer_with_properties(customer: Customer) -> str:
            """Format customer with birthday and pronouns extracted from orders."""
            import concurrent.futures
            birthdays = []
            pronouns = []
            
            # Fetch birthdays and pronouns in parallel since they're independent
            print("[DEBUG] format_customer_with_properties: Starting parallel fetch of birthdays and pronouns", file=sys.stderr)
            logger.debug("format_customer_with_properties: Starting parallel fetch of birthdays and pronouns")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                birthday_future = executor.submit(process_customer_birthday, shopify_service, customer)
                pronoun_future = executor.submit(process_customer_pronouns, shopify_service, customer)
                
                # Wait for both to complete (with timeout handling)
                try:
                    birthdays = birthday_future.result(timeout=60)
                    if should_display and not json_output:
                        if birthdays:
                            print(f"[DEBUG] Found {len(birthdays)} birthday(s)", file=sys.stderr)
                        else:
                            print("[DEBUG] No birthdays found in orders", file=sys.stderr)
                except concurrent.futures.TimeoutError:
                    if should_display and not json_output:
                        print("Warning: Birthday fetch timed out after 60s", file=sys.stderr)
                except Exception as e:
                    if should_display and not json_output:
                        print(f"Warning: Could not fetch birthdays: {e}", file=sys.stderr)
                
                try:
                    pronouns = pronoun_future.result(timeout=60)
                    if should_display and not json_output:
                        if pronouns:
                            print(f"[DEBUG] Found {len(pronouns)} pronoun(s)", file=sys.stderr)
                        else:
                            print("[DEBUG] No pronouns found in orders", file=sys.stderr)
                except concurrent.futures.TimeoutError:
                    if should_display and not json_output:
                        print("Warning: Pronoun fetch timed out after 60s", file=sys.stderr)
                except Exception as e:
                    if should_display and not json_output:
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
        print(f"[DEBUG] get_customer_cmd: Calling shopify_service.get_customer_by_identifier with identifier={identifier}, orders_first=5", file=sys.stderr)
        logger.debug(f"get_customer_cmd: Calling shopify_service.get_customer_by_identifier with identifier={identifier}, orders_first=5")
        try:
            entities = shopify_service.get_customer_by_identifier(identifier, orders_first=5)
            print(f"[DEBUG] get_customer_cmd: get_customer_by_identifier returned {len(entities) if entities else 0} entities", file=sys.stderr)
            logger.debug(f"get_customer_cmd: get_customer_by_identifier returned {len(entities) if entities else 0} entities")
        except (RuntimeError, ValueError) as e:
            print(f"[DEBUG] get_customer_cmd: Exception caught: {type(e).__name__}: {e}", file=sys.stderr)
            logger.debug(f"get_customer_cmd: Exception caught: {type(e).__name__}: {e}", exc_info=True)
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

