"""Get Shopify customer details command."""
import json
import sys
import traceback
from typing import Dict, Any, Optional, List, TYPE_CHECKING, TypedDict, Callable

import click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_CUSTOMER_IDENTIFIER
import sys
sys.path.insert(0, 'backend')
from modules.integrations.shopify.models.sgqlc_models import Customer as CustomerSGQLC

if TYPE_CHECKING:
    from sgqlc.types import Type as SGQLCType
    CustomerSGQLCType = SGQLCType
else:
    CustomerSGQLCType = Any



# ============================================================================
# Display Functions (Now Type-Safe)
# ============================================================================

class CustomerDisplayField(TypedDict):
    """Type definition for customer display field configuration."""
    field_name: str
    display_label: str
    default: Optional[str]
    formatter: Optional[Callable[[Any], str]]


def _format_customer_name(customer: Any) -> str:
    """Format customer full name from firstName, lastName, or displayName."""
    name_parts = [customer.firstName, customer.lastName]  # type: ignore[attr-defined]
    full_name = " ".join(str(p) for p in name_parts if p) or customer.displayName or "N/A"  # type: ignore[attr-defined]
    return full_name


customer_display_fields: List[CustomerDisplayField] = [
    {"field_name": "id", "display_label": "ID", "default": None, "formatter": None},
    {"field_name": "name", "display_label": "Name", "default": None, "formatter": _format_customer_name},
    {"field_name": "displayName", "display_label": "Display Name", "default": "N/A", "formatter": None},
    {"field_name": "email", "display_label": "Email", "default": "N/A", "formatter": None},
    {"field_name": "phone", "display_label": "Phone", "default": "N/A", "formatter": None},
    {"field_name": "state", "display_label": "State", "default": "N/A", "formatter": None},
    {"field_name": "verifiedEmail", "display_label": "Verified", "default": None, "formatter": None},
    {"field_name": "numberOfOrders", "display_label": "Orders Count", "default": "N/A", "formatter": None},
    {"field_name": "createdAt", "display_label": "Created", "default": "N/A", "formatter": None},
    {"field_name": "updatedAt", "display_label": "Updated", "default": "N/A", "formatter": None},
]


def format_customer(customer: Any) -> str:
    """Format customer data for display."""
    output = []
    output.append("\n✅ Customer Found!")
    output.append("=" * 60)
    
    for field_config in customer_display_fields:
        field_name = field_config["field_name"]
        display_label = field_config["display_label"]
        default = field_config["default"]
        formatter = field_config["formatter"]
        
        if formatter:
            value = formatter(customer)
        else:
            value = getattr(customer, field_name, None)  # type: ignore[attr-defined]
            if value is None:
                value = default
            else:
                value = str(value)
        
        output.append(f"{display_label:<15} {value}")
    
    if customer.tags:  # type: ignore[attr-defined]
        tags_list = list(customer.tags)  # type: ignore[attr-defined]
        output.append(f"\nTags ({len(tags_list)}):")
        for tag in tags_list:
            output.append(f"  • {tag}")
    
    if customer.defaultAddress:  # type: ignore[attr-defined]
        addr = customer.defaultAddress  # type: ignore[attr-defined]
        output.append("\nDefault Address:")
        if addr.address1:  # type: ignore[attr-defined]
            output.append(f"  {addr.address1}")  # type: ignore[attr-defined]
        if addr.address2:  # type: ignore[attr-defined]
            output.append(f"  {addr.address2}")  # type: ignore[attr-defined]
        city_parts = [str(p) for p in [addr.city, addr.province, addr.zip] if p]  # type: ignore[attr-defined]
        if city_parts:
            output.append(f"  {', '.join(city_parts)}")
        if addr.country:  # type: ignore[attr-defined]
            output.append(f"  {addr.country}")  # type: ignore[attr-defined]
    
    # Access orders from sgqlc Connection structure
    orders_connection = customer.orders  # type: ignore[attr-defined]
    recent_orders = orders_connection.nodes if orders_connection and hasattr(orders_connection, 'nodes') else []  # type: ignore[attr-defined]
    if recent_orders:
        output.append(f"\nRecent Orders ({len(recent_orders)}):")
        for order in recent_orders:
            output.append(f"  • {order.name or 'N/A'} (created: {order.createdAt or 'N/A'})")  # type: ignore[attr-defined]
            output.append(f"    ID: {order.id}")  # type: ignore[attr-defined]
    
    output.append("=" * 60)
    return '\n'.join(output)


def _format_customer_option(customer: Any) -> str:
    """Format customer for display in selection options."""
    name_parts = [customer.firstName, customer.lastName]  # type: ignore[attr-defined]
    full_name = " ".join(str(p) for p in name_parts if p) or customer.displayName or "N/A"  # type: ignore[attr-defined]
    email = customer.email or 'N/A'  # type: ignore[attr-defined]
    return f"{full_name} ({email})"


def handle_multiple_results(customers: List[Any], json_output: bool, should_display: bool, must_return_one: bool = False) -> Optional[Any]:
    """Handle selection when multiple customers are found.
    
    Args:
        customers: List of customer objects
        json_output: Whether to output JSON format
        should_display: Whether to display output
        must_return_one: If True, requires selecting exactly one customer (no "All" option)
        
    Returns:
        Selected customer object, list of all customers if "All" selected, or None if cancelled
    """
    from bars_cli.commands.shopify._shared.command_helpers import handle_multiple_shopify_results
    return handle_multiple_shopify_results(
        items=customers,
        json_output=json_output,
        should_display=should_display,
        format_option_func=_format_customer_option,
        entity_name="customer",
        must_return_one=must_return_one
    )


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
    from bars_cli.commands.shopify._shared.command_helpers import handle_shopify_get_command
    
    # Service is guaranteed to be available (initialized in shopify group)
    shopify_service = ctx.meta.get('shopify_service')
    
    def handle_multiple_wrapper(items, json_out, should_disp):
        return handle_multiple_results(items, json_out, should_disp, must_return_one=must_return_one)
    
    return handle_shopify_get_command(
        ctx=ctx,
        identifier=identifier,
        service_method=shopify_service.get_customer_by_identifier,  # type: ignore[attr-defined]
        entity_name="customer",
        format_func=format_customer,
        handle_multiple_func=handle_multiple_wrapper,
        service_method_kwargs={"orders_first": 5},
        identifier_required_msg="Customer identifier is required"
    )

