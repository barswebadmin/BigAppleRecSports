"""Rich formatters for Shopify orders."""

from typing import Any, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
import json

from bars_cli._core.ui.display import format_datetime, create_info_table, create_text_panel, display_json_syntax


def format_order_rich(
    order: Any,
    *,
    console: Optional[Console] = None,
    show_properties: bool = False
) -> None:
    """Display order details in a rich formatted output.
    
    Args:
        order: Order object (sgqlc Type instance)
        console: Optional Rich Console instance (creates new if None)
        show_properties: Whether to show line item custom attributes
    """
    if console is None:
        console = Console()
    
    # Order Header
    header_parts = [
        (f"Order #{getattr(order, 'name', 'N/A')}", "bold cyan")
    ]
    if hasattr(order, 'cancelledAt') and getattr(order, 'cancelledAt', None):  # type: ignore[attr-defined]
        header_parts.append((" [CANCELLED]", "bold red"))
    
    panel = create_text_panel(header_parts, title="Order Details", border_style="cyan")
    console.print(panel)
    
    # Basic Info Table
    info_rows = []
    
    order_id = getattr(order, 'id', 'N/A')  # type: ignore[attr-defined]
    if isinstance(order_id, str) and '/' in order_id:
        order_id = order_id.split('/')[-1]
    info_rows.append(("Order ID", order_id))
    info_rows.append(("Order Number", getattr(order, 'name', 'N/A')))  # type: ignore[attr-defined]
    info_rows.append(("Email", getattr(order, 'email', 'N/A')))  # type: ignore[attr-defined]
    info_rows.append(("Created At", format_datetime(getattr(order, 'createdAt', None))))  # type: ignore[attr-defined]
    
    # Customer name
    customer_name = _format_customer_name(order)
    info_rows.append(("Customer", customer_name))
    
    # Total price
    total_price = _format_order_total(order)
    info_rows.append(("Total Price", total_price))
    
    # Financial and fulfillment status
    info_rows.append(("Financial Status", getattr(order, 'displayFinancialStatus', 'N/A')))  # type: ignore[attr-defined]
    info_rows.append(("Fulfillment Status", getattr(order, 'displayFulfillmentStatus', 'N/A')))  # type: ignore[attr-defined]
    
    info_table = create_info_table(info_rows, show_header=False, box=None, padding=(0, 2))
    console.print(info_table)
    console.print()
    
    # Cancellation Status
    cancelled_at = getattr(order, 'cancelledAt', None)  # type: ignore[attr-defined]
    if cancelled_at:
        cancel_rows = [
            ("Cancelled At", format_datetime(cancelled_at)),
            ("Reason", getattr(order, 'cancelReason', 'N/A'))  # type: ignore[attr-defined]
        ]
        cancel_table = create_info_table(
            cancel_rows,
            title="❌ Cancellation Details",
            show_header=False,
            box=None,
            padding=(0, 2),
            field_style="bold red",
            value_style="red"
        )
        console.print(cancel_table)
        console.print()
    
    # Line Items
    line_items = _get_line_items(order)
    if line_items:
        items_table = Table(title="📦 Line Items", show_header=True)
        items_table.add_column("Quantity", justify="center")
        items_table.add_column("Item")
        items_table.add_column("Variant")
        items_table.add_column("Price", justify="right")
        
        for item in line_items:
            variant = getattr(item, 'variant', None)  # type: ignore[attr-defined]
            variant_title = getattr(variant, 'title', 'N/A') if variant else 'N/A'  # type: ignore[attr-defined]
            variant_price = getattr(variant, 'price', '0') if variant else '0'  # type: ignore[attr-defined]
            
            items_table.add_row(
                str(getattr(item, 'quantity', 0)),  # type: ignore[attr-defined]
                getattr(item, 'title', 'N/A'),  # type: ignore[attr-defined]
                variant_title,
                f"${float(variant_price):.2f}" if variant_price != '0' else "N/A"
            )
        
        console.print(items_table)
        console.print()
        
        # Display properties if requested
        if show_properties:
            _display_line_item_properties(line_items, console)
    
    # Refunds
    refunds = _get_refunds(order)
    if refunds:
        console.print(Panel(f"💰 Refunds ({len(refunds)} total)", style="yellow"))
        
        for idx, refund in enumerate(refunds, 1):
            _display_refund_details(refund, idx, console)
        
        console.print()
    else:
        console.print("[dim]No refunds found for this order.[/dim]\n")


def _format_order_total(order: Any) -> str:
    """Format order total from totalPriceSet."""
    total_price_set = getattr(order, 'totalPriceSet', None)  # type: ignore[attr-defined]
    if total_price_set:
        shop_money = getattr(total_price_set, 'shopMoney', None)  # type: ignore[attr-defined]
        if shop_money:
            amount = getattr(shop_money, 'amount', '0')  # type: ignore[attr-defined]
            currency = getattr(shop_money, 'currencyCode', 'USD')  # type: ignore[attr-defined]
            try:
                return f"${float(amount):.2f} {currency}"
            except (ValueError, TypeError):
                return f"{amount} {currency}" if currency else str(amount)
    return "N/A"


def _format_customer_name(order: Any) -> str:
    """Format customer name from order customer."""
    customer = getattr(order, 'customer', None)  # type: ignore[attr-defined]
    if customer:
        # Customer can be a direct Customer object or a Connection
        if hasattr(customer, 'nodes') and customer.nodes:  # type: ignore[attr-defined]
            # It's a Connection
            customer_node = customer.nodes[0]  # type: ignore[attr-defined]
        else:
            # It's a direct Customer object
            customer_node = customer
        
        display_name = getattr(customer_node, 'displayName', None)  # type: ignore[attr-defined]
        if display_name:
            return display_name
        
        first_name = getattr(customer_node, 'firstName', None)  # type: ignore[attr-defined]
        last_name = getattr(customer_node, 'lastName', None)  # type: ignore[attr-defined]
        name_parts = [p for p in [first_name, last_name] if p]
        if name_parts:
            return " ".join(name_parts)
    return "N/A"


def _get_line_items(order: Any) -> List[Any]:
    """Extract line items from order."""
    line_items_conn = getattr(order, 'lineItems', None)  # type: ignore[attr-defined]
    if line_items_conn:
        nodes = getattr(line_items_conn, 'nodes', None)  # type: ignore[attr-defined]
        if nodes:
            return list(nodes)
    return []


def _get_refunds(order: Any) -> List[Any]:
    """Extract refunds from order."""
    refunds = getattr(order, 'refunds', None)  # type: ignore[attr-defined]
    if refunds:
        return list(refunds)
    return []


def _display_line_item_properties(line_items: List[Any], console: Console) -> None:
    """Display custom attributes for line items."""
    has_any_properties = False
    properties_data = []
    
    for item in line_items:
        custom_attrs = getattr(item, 'customAttributes', None)  # type: ignore[attr-defined]
        if custom_attrs:
            has_any_properties = True
            item_id = getattr(item, 'id', 'N/A')  # type: ignore[attr-defined]
            if isinstance(item_id, str) and '/' in item_id:
                item_id = item_id.split('/')[-1]
            
            # Convert customAttributes to dict format
            attrs_list = []
            if hasattr(custom_attrs, '__iter__'):
                for attr in custom_attrs:
                    if hasattr(attr, 'key') and hasattr(attr, 'value'):
                        attrs_list.append({
                            "key": getattr(attr, 'key', ''),
                            "value": getattr(attr, 'value', '')
                        })
            
            properties_data.append({
                "line_item_id": item_id,
                "line_item_name": getattr(item, 'name', 'N/A'),  # type: ignore[attr-defined]
                "properties": attrs_list
            })
    
    if has_any_properties:
        display_json_syntax(properties_data, title="Line Item Properties")
        console.print()
    else:
        console.print("[dim]No properties found on line items.[/dim]\n")


def _display_refund_details(refund: Any, idx: int, console: Console) -> None:
    """Display detailed refund information."""
    refund_rows = []
    
    refund_id = getattr(refund, 'id', 'N/A')  # type: ignore[attr-defined]
    if isinstance(refund_id, str) and '/' in refund_id:
        refund_id = refund_id.split('/')[-1]
    
    refund_rows.append(("Refund ID", refund_id))
    refund_rows.append(("Created At", format_datetime(getattr(refund, 'createdAt', None))))  # type: ignore[attr-defined]
    
    # Total refunded amount
    total_refunded_set = getattr(refund, 'totalRefundedSet', None)  # type: ignore[attr-defined]
    if total_refunded_set:
        shop_money = getattr(total_refunded_set, 'shopMoney', None)  # type: ignore[attr-defined]
        if shop_money:
            amount = getattr(shop_money, 'amount', '0')  # type: ignore[attr-defined]
            currency = getattr(shop_money, 'currencyCode', 'USD')  # type: ignore[attr-defined]
            try:
                refund_rows.append(("Amount", f"${float(amount):.2f} {currency}"))
            except (ValueError, TypeError):
                refund_rows.append(("Amount", f"{amount} {currency}"))
    
    note = getattr(refund, 'note', None)  # type: ignore[attr-defined]
    if note:
        refund_rows.append(("Note", note))
    
    refund_table = create_info_table(
        refund_rows,
        show_header=False,
        box=None,
        padding=(0, 2),
        field_style="bold yellow"
    )
    
    console.print(f"\n[bold]Refund #{idx}[/bold]")
    console.print(refund_table)
    
    # Refund line items
    refund_line_items = _get_refund_line_items(refund)
    if refund_line_items:
        items_table = Table(title="Refunded Items", show_header=True, box=None)
        items_table.add_column("Quantity", justify="center")
        items_table.add_column("Item")
        items_table.add_column("Restock Type")
        
        for refund_item in refund_line_items:
            line_item = getattr(refund_item, 'lineItem', None)  # type: ignore[attr-defined]
            line_item_title = getattr(line_item, 'title', 'N/A') if line_item else 'N/A'  # type: ignore[attr-defined]
            
            items_table.add_row(
                str(getattr(refund_item, 'quantity', 0)),  # type: ignore[attr-defined]
                line_item_title,
                getattr(refund_item, 'restockType', 'N/A')  # type: ignore[attr-defined]
            )
        
        console.print(items_table)
    
    # Refund transactions
    refund_transactions = _get_refund_transactions(refund)
    if refund_transactions:
        trans_table = Table(title="Transactions", show_header=True, box=None)
        trans_table.add_column("Kind")
        trans_table.add_column("Status")
        trans_table.add_column("Amount", justify="right")
        trans_table.add_column("Gateway")
        
        for trans in refund_transactions:
            amount = getattr(trans, 'amount', '0')  # type: ignore[attr-defined]
            try:
                amount_str = f"${float(amount):.2f}"
            except (ValueError, TypeError):
                amount_str = str(amount)
            
            trans_table.add_row(
                getattr(trans, 'kind', 'N/A'),  # type: ignore[attr-defined]
                getattr(trans, 'status', 'N/A'),  # type: ignore[attr-defined]
                amount_str,
                getattr(trans, 'gateway', 'N/A')  # type: ignore[attr-defined]
            )
        
        console.print(trans_table)


def _get_refund_line_items(refund: Any) -> List[Any]:
    """Extract refund line items from refund."""
    refund_line_items_conn = getattr(refund, 'refundLineItems', None)  # type: ignore[attr-defined]
    if refund_line_items_conn:
        nodes = getattr(refund_line_items_conn, 'nodes', None)  # type: ignore[attr-defined]
        if nodes:
            return list(nodes)
    return []


def _get_refund_transactions(refund: Any) -> List[Any]:
    """Extract refund transactions from refund."""
    refund_transactions_conn = getattr(refund, 'transactions', None)  # type: ignore[attr-defined]
    if refund_transactions_conn:
        nodes = getattr(refund_transactions_conn, 'nodes', None)  # type: ignore[attr-defined]
        if nodes:
            return list(nodes)
    return []

