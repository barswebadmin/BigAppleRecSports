"""Get Shopify order details command."""
import json
import sys
import traceback
from typing import Dict, Any, Optional, List, TYPE_CHECKING, TypedDict, Callable

import click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_ORDER_IDENTIFIER
import sys
sys.path.insert(0, 'backend')
from modules.integrations.shopify.models.sgqlc_models import Order as OrderSGQLC

if TYPE_CHECKING:
    from sgqlc.types import Type as SGQLCType
    OrderSGQLCType = SGQLCType
else:
    OrderSGQLCType = Any


# ============================================================================
# Display Functions (Now Type-Safe)
# ============================================================================

class OrderDisplayField(TypedDict):
    """Type definition for order display field configuration."""
    field_name: str
    display_label: str
    default: Optional[str]
    formatter: Optional[Callable[[Any], str]]


def _format_order_total(order: Any) -> str:
    """Format order total from totalPriceSet."""
    if hasattr(order, 'totalPriceSet') and order.totalPriceSet:  # type: ignore[attr-defined]
        if hasattr(order.totalPriceSet, 'shopMoney') and order.totalPriceSet.shopMoney:  # type: ignore[attr-defined]
            amount = order.totalPriceSet.shopMoney.amount  # type: ignore[attr-defined]
            currency = order.totalPriceSet.shopMoney.currencyCode  # type: ignore[attr-defined]
            return f"{currency} {amount}" if currency else str(amount)
    return "N/A"


def _format_customer_name(order: Any) -> str:
    """Format customer name from order customer connection."""
    if hasattr(order, 'customer') and order.customer:  # type: ignore[attr-defined]
        customer_conn = order.customer  # type: ignore[attr-defined]
        if hasattr(customer_conn, 'nodes') and customer_conn.nodes:  # type: ignore[attr-defined]
            customer = customer_conn.nodes[0]  # type: ignore[attr-defined]
            if hasattr(customer, 'displayName') and customer.displayName:  # type: ignore[attr-defined]
                return customer.displayName  # type: ignore[attr-defined]
            name_parts = []
            if hasattr(customer, 'firstName') and customer.firstName:  # type: ignore[attr-defined]
                name_parts.append(customer.firstName)  # type: ignore[attr-defined]
            if hasattr(customer, 'lastName') and customer.lastName:  # type: ignore[attr-defined]
                name_parts.append(customer.lastName)  # type: ignore[attr-defined]
            if name_parts:
                return " ".join(name_parts)
    return "N/A"


order_display_fields: List[OrderDisplayField] = [
    {"field_name": "id", "display_label": "ID", "default": None, "formatter": None},
    {"field_name": "name", "display_label": "Order Number", "default": "N/A", "formatter": None},
    {"field_name": "email", "display_label": "Email", "default": "N/A", "formatter": None},
    {"field_name": "phone", "display_label": "Phone", "default": "N/A", "formatter": None},
    {"field_name": "createdAt", "display_label": "Created", "default": "N/A", "formatter": None},
    {"field_name": "totalPriceSet", "display_label": "Total", "default": "N/A", "formatter": _format_order_total},
    {"field_name": "customer", "display_label": "Customer", "default": "N/A", "formatter": _format_customer_name},
]


def format_order(order: Any) -> str:
    """Format order data for display."""
    output = []
    output.append("\n✅ Order Found!")
    output.append("=" * 60)
    
    for field_config in order_display_fields:
        field_name = field_config["field_name"]
        display_label = field_config["display_label"]
        default = field_config["default"]
        formatter = field_config["formatter"]
        
        if formatter:
            value = formatter(order)
        else:
            value = getattr(order, field_name, None)  # type: ignore[attr-defined]
            if value is None:
                value = default
            else:
                value = str(value)
        
        output.append(f"{display_label:<15} {value}")
    
    # Display line items
    if hasattr(order, 'lineItems') and order.lineItems:  # type: ignore[attr-defined]
        line_items_conn = order.lineItems  # type: ignore[attr-defined]
        line_items = line_items_conn.nodes if hasattr(line_items_conn, 'nodes') else []  # type: ignore[attr-defined]
        if line_items:
            output.append(f"\nLine Items ({len(line_items)}):")
            for item in line_items:
                name = getattr(item, 'name', 'N/A')  # type: ignore[attr-defined]
                quantity = getattr(item, 'quantity', 'N/A')  # type: ignore[attr-defined]
                output.append(f"  • {name} (qty: {quantity})")
    
    # Display transactions
    if hasattr(order, 'transactions') and order.transactions:  # type: ignore[attr-defined]
        transactions = list(order.transactions)  # type: ignore[attr-defined]
        if transactions:
            output.append(f"\nTransactions ({len(transactions)}):")
            for txn in transactions:
                kind = getattr(txn, 'kind', 'N/A')  # type: ignore[attr-defined]
                status = getattr(txn, 'status', 'N/A')  # type: ignore[attr-defined]
                amount = getattr(txn, 'amount', 'N/A')  # type: ignore[attr-defined]
                output.append(f"  • {kind} - {status} - {amount}")
    
    # Display refunds
    if hasattr(order, 'refunds') and order.refunds:  # type: ignore[attr-defined]
        refunds = list(order.refunds)  # type: ignore[attr-defined]
        if refunds:
            output.append(f"\nRefunds ({len(refunds)}):")
            for refund in refunds:
                refund_id = getattr(refund, 'id', 'N/A')  # type: ignore[attr-defined]
                note = getattr(refund, 'note', 'N/A')  # type: ignore[attr-defined]
                output.append(f"  • {refund_id} - {note}")
    
    output.append("=" * 60)
    return '\n'.join(output)


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
@click.argument('identifier', type=SHOPIFY_ORDER_IDENTIFIER, required=False)
@click.pass_context
def get_order_cmd(ctx: click.Context, identifier: Optional[Dict[str, Any]], must_return_one: bool = False) -> Optional[List[Any]]:
    """
    Get Shopify order details by order number or ID.
    
    IDENTIFIER: Order number (1234 or #1234) or Order ID (gid://shopify/Order/123 or 123).
    
    Examples:
      bars shopify order get 1234
      bars shopify order get #1234
      bars shopify order get gid://shopify/Order/123456789
      bars shopify order get 123456789
      bars --json shopify order get 1234
    """
    from bars_cli.commands.shopify._shared.command_helpers import handle_shopify_get_command
    
    # Service is guaranteed to be available (initialized in shopify group)
    shopify_service = ctx.meta.get('shopify_service')
    
    def handle_multiple_wrapper(items, json_out, should_disp):
        return handle_multiple_results(items, json_out, should_disp, must_return_one=must_return_one)
    
    return handle_shopify_get_command(
        ctx=ctx,
        identifier=identifier,
        service_method=shopify_service.get_order_by_identifier,  # type: ignore[attr-defined]
        entity_name="order",
        format_func=format_order,
        handle_multiple_func=handle_multiple_wrapper,
        service_method_kwargs={"line_items_first": 5},
        identifier_required_msg="Order identifier is required"
    )

