"""Shopify formatters organized by domain.

All formatting code for Shopify commands is consolidated here for easy refactoring.
Organized by domain: Customers, Products, Orders (Rich & CSV), and shared utilities.
"""

from __future__ import annotations
import html
from datetime import datetime
from typing import TypedDict, Optional, Any, Callable, List, Dict, Union

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from bars_cli.backend_services.shopify.models.sgqlc_models import (
    Customer,
    Product,
    Order,
    LineItem,
    Refund,
    RefundLineItem,
    RefundTransaction,
    Transaction,
    DiscountApplication,
    CustomAttribute,
)
from bars_cli._core.ui.display import format_datetime, create_info_table, create_text_panel, display_json_syntax
from bars_cli._core.utils.json_output import output_json_error


# ============================================================================
# CSV FORMATTING UTILITIES
# ============================================================================

def format_date_for_csv(dt_str: Optional[str]) -> str:
    """Format ISO datetime string to CSV date format (M/D/YYYY).
    
    Args:
        dt_str: ISO datetime string (e.g., "2025-01-15T10:30:00Z")
        
    Returns:
        Formatted date string (e.g., "1/15/2025") or empty string if invalid
    """
    if not dt_str:
        return ''
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return f"{dt.month}/{dt.day}/{dt.year}"
    except (ValueError, AttributeError):
        return dt_str if dt_str else ''


def get_custom_attribute_value(line_item: Dict[str, Any], key: str) -> str:
    """Get custom attribute value from line item by key.
    
    Handles HTML entity decoding for key matching.
    
    Args:
        line_item: Line item dictionary with customAttributes
        key: Attribute key to search for
        
    Returns:
        Attribute value or empty string if not found
    """
    attrs = line_item.get('customAttributes', [])
    if not attrs:
        return ''
    
    key_decoded = html.unescape(key)
    for attr in attrs:
        attr_key = attr.get('key', '')
        attr_key_decoded = html.unescape(attr_key)
        if attr_key_decoded == key_decoded:
            return attr.get('value', '')
    return ''


# ============================================================================
# SHARED UTILITIES
# ============================================================================

def format_error(
    error_msg: str,
    error_type: Optional[str] = None,
    json_output: bool = False,
    should_display: bool = True
) -> None:
    """Format and display error message.
    
    Args:
        error_msg: Error message text
        error_type: Optional error type name
        json_output: Whether to output JSON format
        should_display: Whether to display the error
    """
    if not should_display:
        return
    
    if json_output:
        output_json_error(error_msg, error_type=error_type)
    else:
        if error_type:
            click.echo(f"❌ Unexpected error ({error_type}): {error_msg}", err=True)
        else:
            click.echo(f"❌ {error_msg}", err=True)


def format_datetime_display(dt_str: Optional[str]) -> str:
    """Format datetime string for display."""
    return format_datetime(dt_str)


def _format_customer_name_from_order(order: Order) -> str:
    """Format customer name from order customer.
    
    Handles both direct Customer objects and Connection structures.
    """
    customer = getattr(order, 'customer', None)  # type: ignore[attr-defined]
    if not customer:
        return "N/A"
    
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


# ============================================================================
# CUSTOMER FORMATTING
# ============================================================================

class CustomerDisplayField(TypedDict):
    """Type definition for customer display field configuration."""
    field_name: str
    display_label: str
    default: Optional[str]
    formatter: Optional[Callable[[Any], str]]


def _format_customer_option(customer: Customer) -> str:
    """Format customer for display in selection options."""
    name_parts = [customer.firstName, customer.lastName]  # type: ignore[attr-defined]
    full_name = " ".join(str(p) for p in name_parts if p) or customer.displayName or "N/A"  # type: ignore[attr-defined]
    email = customer.email or 'N/A'  # type: ignore[attr-defined]
    return f"{full_name} ({email})"


def _format_customer_name(customer: Customer) -> str:
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
    {"field_name": "verifiedEmail", "display_label": "Verified", "default": "N/A", "formatter": None},
    {"field_name": "numberOfOrders", "display_label": "Orders Count", "default": "N/A", "formatter": None},
    {"field_name": "createdAt", "display_label": "Created", "default": "N/A", "formatter": None},
    {"field_name": "updatedAt", "display_label": "Updated", "default": "N/A", "formatter": None},
]


def format_customer(customer: Customer) -> str:
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


# ============================================================================
# PRODUCT FORMATTING
# ============================================================================

class ProductDisplayField(TypedDict):
    """Type definition for product display field configuration."""
    field_name: str
    display_label: str
    default: Optional[str]
    formatter: Optional[Callable[[Any], str]]


product_display_fields: List[ProductDisplayField] = [
    {"field_name": "id", "display_label": "ID", "default": None, "formatter": None},
    {"field_name": "title", "display_label": "Title", "default": "N/A", "formatter": None},
    {"field_name": "handle", "display_label": "Handle", "default": "N/A", "formatter": None},
    {"field_name": "productType", "display_label": "Type", "default": "N/A", "formatter": None},
    {"field_name": "vendor", "display_label": "Vendor", "default": "N/A", "formatter": None},
    {"field_name": "status", "display_label": "Status", "default": "N/A", "formatter": None},
    {"field_name": "createdAt", "display_label": "Created", "default": "N/A", "formatter": None},
    {"field_name": "updatedAt", "display_label": "Updated", "default": "N/A", "formatter": None},
]


def format_product(product: Product) -> str:
    """Format product data for display."""
    output = []
    output.append("\n✅ Product Found!")
    output.append("=" * 60)
    
    for field_config in product_display_fields:
        field_name = field_config["field_name"]
        display_label = field_config["display_label"]
        default = field_config["default"]
        formatter = field_config["formatter"]
        
        if formatter:
            value = formatter(product)
        else:
            value = getattr(product, field_name, None)  # type: ignore[attr-defined]
            if value is None:
                value = default
            else:
                value = str(value)
        
        output.append(f"{display_label:<15} {value}")
    
    # Display tags
    if hasattr(product, 'tags') and product.tags:  # type: ignore[attr-defined]
        tags_list = list(product.tags)  # type: ignore[attr-defined]
        if tags_list:
            output.append(f"\nTags ({len(tags_list)}):")
            for tag in tags_list:
                output.append(f"  • {tag}")
    
    # Display variants
    if hasattr(product, 'variants') and product.variants:  # type: ignore[attr-defined]
        variants_conn = product.variants  # type: ignore[attr-defined]
        variants = variants_conn.nodes if hasattr(variants_conn, 'nodes') else []  # type: ignore[attr-defined]
        if variants:
            output.append(f"\nVariants ({len(variants)}):")
            for variant in variants:
                title = getattr(variant, 'title', 'N/A')  # type: ignore[attr-defined]
                price = getattr(variant, 'price', 'N/A')  # type: ignore[attr-defined]
                inventory = getattr(variant, 'inventoryQuantity', 'N/A')  # type: ignore[attr-defined]
                output.append(f"  • {title} - ${price} (qty: {inventory})")
    
    output.append("=" * 60)
    return '\n'.join(output)


def _format_product_option(product: Product) -> str:
    """Format product for display in selection options."""
    title = getattr(product, 'title', 'N/A')  # type: ignore[attr-defined]
    handle = getattr(product, 'handle', 'N/A')  # type: ignore[attr-defined]
    return f"{title} ({handle})"


# ============================================================================
# ORDER FORMATTING - RICH DISPLAY
# ============================================================================

def format_order_rich(
    order: Order,
    *,
    console: Optional[Console] = None,
    show_properties: bool = False,
    total_paid: Optional[str] = None
) -> None:
    """Display order details in a rich formatted output.
    
    Args:
        order: Order object (sgqlc Type instance)
        console: Optional Rich Console instance (creates new if None)
        show_properties: Whether to show line item custom attributes
        total_paid: Formatted total paid string (e.g., "$115.00 USD") - calculated by command
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
    customer_name = _format_customer_name_from_order(order)
    info_rows.append(("Customer", customer_name))
    
    # Total paid (formatted string passed from command)
    info_rows.append(("Total Paid", total_paid or "N/A"))
    
    # Financial and fulfillment status
    info_rows.append(("Financial Status", getattr(order, 'displayFinancialStatus', 'N/A')))  # type: ignore[attr-defined]
    info_rows.append(("Fulfillment Status", getattr(order, 'displayFulfillmentStatus', 'N/A')))  # type: ignore[attr-defined]
    
    info_table = create_info_table(info_rows, show_header=False)
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
            box_style=None,
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




def _get_line_items(order: Order) -> List[LineItem]:
    """Extract line items from order."""
    line_items_conn = getattr(order, 'lineItems', None)  # type: ignore[attr-defined]
    if line_items_conn:
        nodes = getattr(line_items_conn, 'nodes', None)  # type: ignore[attr-defined]
        if nodes:
            return list(nodes)
    return []


def _get_refunds(order: Order) -> List[Refund]:
    """Extract refunds from order."""
    refunds = getattr(order, 'refunds', None)  # type: ignore[attr-defined]
    if refunds:
        return list(refunds)
    return []


def _display_line_item_properties(line_items: List[LineItem], console: Console) -> None:
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


def _display_refund_details(refund: Refund, idx: int, console: Console) -> None:
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
        box_style=None,
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


def _get_refund_line_items(refund: Refund) -> List[RefundLineItem]:
    """Extract refund line items from refund."""
    refund_line_items_conn = getattr(refund, 'refundLineItems', None)  # type: ignore[attr-defined]
    if refund_line_items_conn:
        nodes = getattr(refund_line_items_conn, 'nodes', None)  # type: ignore[attr-defined]
        if nodes:
            return list(nodes)
    return []


def _get_refund_transactions(refund: Refund) -> List[RefundTransaction]:
    """Extract refund transactions from refund."""
    refund_transactions_conn = getattr(refund, 'transactions', None)  # type: ignore[attr-defined]
    if refund_transactions_conn:
        nodes = getattr(refund_transactions_conn, 'nodes', None)  # type: ignore[attr-defined]
        if nodes:
            return list(nodes)
    return []


def _format_order_option(order: Order) -> str:
    """Format order for display in selection options."""
    order_name = getattr(order, 'name', 'N/A')  # type: ignore[attr-defined]
    order_email = getattr(order, 'email', 'N/A')  # type: ignore[attr-defined]
    return f"{order_name} ({order_email})"


def _get_product_title_from_order(order: Order) -> str:
    """Extract product title from first line item in order."""
    product_title = "Unknown Product"
    line_items_conn = getattr(order, 'lineItems', None)  # type: ignore[attr-defined]
    if line_items_conn:
        nodes = getattr(line_items_conn, 'nodes', None)  # type: ignore[attr-defined]
        if nodes and len(nodes) > 0:
            first_item = nodes[0]
            product = getattr(first_item, 'product', None)  # type: ignore[attr-defined]
            if product:
                product_title = getattr(product, 'title', 'Unknown Product')  # type: ignore[attr-defined]
    return product_title


def _extract_numeric_id_from_gid(gid: str) -> Optional[str]:
    """Extract numeric ID from Shopify GID format (e.g., gid://shopify/Order/123456789 -> 123456789)."""
    if not gid:
        return None
    if '/' in gid:
        return gid.split('/')[-1]
    return gid if gid.isdigit() else None


def _get_product_id_from_order(order: Order) -> Optional[str]:
    """Extract product ID from first line item in order."""
    line_items_conn = getattr(order, 'lineItems', None)  # type: ignore[attr-defined]
    if line_items_conn:
        nodes = getattr(line_items_conn, 'nodes', None)  # type: ignore[attr-defined]
        if nodes and len(nodes) > 0:
            first_item = nodes[0]
            product = getattr(first_item, 'product', None)  # type: ignore[attr-defined]
            if product:
                product_id = getattr(product, 'id', None)  # type: ignore[attr-defined]
                if product_id:
                    return _extract_numeric_id_from_gid(product_id)
    return None


def format_already_cancelled_order(
    order: Order,
    order_name: str,
    customer_name: str,
    console: Console
) -> None:
    """Display already cancelled order information."""
    cancelled_at = getattr(order, 'cancelledAt', None)  # type: ignore[attr-defined]
    cancel_reason = getattr(order, 'cancelReason', 'N/A')  # type: ignore[attr-defined]
    
    header_parts = [
        (f"Order #{order_name} ", "bold yellow"),
        ("[ALREADY CANCELLED]", "bold red")
    ]
    panel = create_text_panel(header_parts, title="Cancellation Status", border_style="red")
    console.print(panel)
    
    console.print(f"  [bold]Cancelled At:[/bold] {format_datetime_display(cancelled_at)}")
    console.print(f"  [bold]Reason:[/bold] {cancel_reason}")
    if customer_name and customer_name != "N/A":
        console.print(f"  [bold]Customer:[/bold] {customer_name}")
    console.print(f"  [bold]Email:[/bold] {getattr(order, 'email', 'N/A')}")  # type: ignore[attr-defined]
    console.print()
    console.print("[yellow]This order is already cancelled. No action taken.[/yellow]\n")


def format_order_to_cancel(
    order: Order,
    order_name: str,
    order_id: str,
    customer_name: str,
    product_title: str,
    console: Console
) -> None:
    """Display order information before cancelling."""
    header_parts = [(f"Order #{order_name}", "bold cyan")]
    panel = create_text_panel(header_parts, title="Order to Cancel", border_style="cyan")
    console.print(panel)
    
    # Extract numeric IDs for URLs
    order_id_numeric = _extract_numeric_id_from_gid(order_id)
    product_id_numeric = _get_product_id_from_order(order)
    
    order_id_short = order_id.split('/')[-1] if '/' in order_id else order_id
    console.print(f"  [bold]Order ID:[/bold] {order_id_short}")
    
    # Add order URL
    if order_id_numeric:
        order_url = f"https://admin.shopify.com/store/09fe59-3/orders/{order_id_numeric}"
        console.print(f"  [bold]Order URL:[/bold] [link={order_url}]{order_url}[/link]")
    
    if customer_name and customer_name != "N/A":
        console.print(f"  [bold]Customer:[/bold] {customer_name}")
    console.print(f"  [bold]Email:[/bold] {getattr(order, 'email', 'N/A')}")  # type: ignore[attr-defined]
    console.print(f"  [bold]Financial Status:[/bold] {getattr(order, 'displayFinancialStatus', 'N/A')}")  # type: ignore[attr-defined]
    console.print(f"  [bold]Fulfillment Status:[/bold] {getattr(order, 'displayFulfillmentStatus', 'N/A')}")  # type: ignore[attr-defined]
    
    # Add product with clickable link
    if product_id_numeric:
        product_url = f"https://admin.shopify.com/store/09fe59-3/products/{product_id_numeric}"
        console.print(f"  [cyan]📦 Product:[/cyan] [link={product_url}]{product_title}[/link]")
    else:
        console.print(f"  [cyan]📦 Product:[/cyan] {product_title}")
    
    console.print()


def format_cancellation_error(
    error_msg: Union[str, List[str]],
    console: Console
) -> None:
    """Display cancellation error message."""
    if isinstance(error_msg, list):
        console.print("[red]❌ Failed to cancel order:[/red]")
        for err in error_msg:
            console.print(f"  • {err}")
    else:
        console.print(f"[red]❌ Failed to cancel order: {error_msg}[/red]")
    console.print()


def format_cancellation_success(
    order_num: str,
    job_id: str,
    job_done: bool,
    reason: str,
    console: Console
) -> None:
    """Display successful cancellation information."""
    console.print(Panel(
        f"[bold green]✓ Order #{order_num} successfully cancelled[/bold green]",
        border_style="green"
    ))
    console.print(f"  [bold]Cancellation Job ID:[/bold] {job_id}")
    console.print(f"  [bold]Job Status:[/bold] {'Completed' if job_done else 'In Progress'}")
    console.print(f"  [bold]Reason:[/bold] {reason}")
    console.print()
    console.print("[dim]Note: Customer was NOT notified and inventory was NOT restocked.[/dim]")
    console.print("[dim]If a refund is needed, it must be processed separately.[/dim]\n")


def format_variants_table(
    variants: List[Dict[str, Any]],
    console: Console
) -> None:
    """Display product variants table for restock selection."""
    variants_table = Table(title="Available Variants", show_header=True)
    variants_table.add_column("#", justify="center")
    variants_table.add_column("Variant Name")
    variants_table.add_column("Current Inventory", justify="right")
    
    for i, variant_data in enumerate(variants, 1):
        inv_qty = variant_data.get('inventory_quantity', 0)
        variants_table.add_row(
            str(i),
            variant_data.get('title', 'Unknown'),
            str(inv_qty) if inv_qty is not None else "N/A"
        )
    
    console.print(variants_table)
    console.print()


def format_restock_result(
    quantity: int,
    success: bool,
    error_msg: Optional[str] = None,
    console: Optional[Console] = None
) -> None:
    """Display individual restock result."""
    if console is None:
        console = Console()
    
    if success:
        console.print(f"  [green]✓ Restocked +{quantity} units[/green]")
    else:
        error = error_msg or "Unknown error"
        console.print(f"  [red]✗ Restock failed: {error}[/red]")


def format_restock_summary(
    success_count: int,
    failure_count: int,
    console: Console
) -> None:
    """Display restock operation summary."""
    if success_count > 0:
        console.print(f"[green]✓ Successfully restocked {success_count} variant(s)[/green]")
    if failure_count > 0:
        console.print(f"[yellow]⚠️  Failed to restock {failure_count} variant(s)[/yellow]")
    console.print()


# ============================================================================
# REFUND FORMATTING
# ============================================================================

def format_payment_summary(
    payment_summary: Dict[str, Any],
    console: Console
) -> None:
    """Display payment summary table."""
    total_amount = payment_summary['total_amount']
    currency = payment_summary['currency']
    total_refunded = payment_summary['total_refunded']
    pending_refunds = payment_summary['pending_refunds']
    completed_refunds = payment_summary['completed_refunds']
    remaining_refundable = payment_summary['remaining_refundable']
    
    payment_rows = [
        ("Total Paid", f"${total_amount:.2f} {currency}"),
        ("Total Refunded", f"${total_refunded:.2f} {currency}")
    ]
    if pending_refunds > 0:
        payment_rows.append(("  - Pending", f"${pending_refunds:.2f} {currency}"))
        payment_rows.append(("  - Completed", f"${completed_refunds:.2f} {currency}"))
    payment_rows.append(("Remaining Refundable", f"${remaining_refundable:.2f} {currency}"))
    
    payment_table = create_info_table(
        payment_rows,
        title="💰 Payment Summary"
    )
    console.print(payment_table)
    console.print()


def format_existing_refunds_table(
    refunds: List[Refund],
    console: Console
) -> None:
    """Display existing refunds table."""
    if not refunds:
        return
    
    refunds_table = Table(title=f"📋 Existing Refunds ({len(refunds)} total)", show_header=True)
    refunds_table.add_column("Date", style="dim")
    refunds_table.add_column("Amount", justify="right")
    refunds_table.add_column("Status")
    
    for refund in refunds:
        refund_data = refund.__json_data__ if hasattr(refund, '__json_data__') else {}
        refund_amount = float(refund_data.get('totalRefundedSet', {}).get('shopMoney', {}).get('amount', '0'))
        refund_date = format_datetime_display(refund_data.get('createdAt'))
        refund_status = "Completed"
        status_style = "green"
        
        if refund_amount == 0:
            refund_transactions_conn = getattr(refund, 'transactions', None)  # type: ignore[attr-defined]
            if refund_transactions_conn:
                nodes = getattr(refund_transactions_conn, 'nodes', None)  # type: ignore[attr-defined]
                if nodes:
                    for trans in nodes:
                        trans_data = trans.__json_data__ if hasattr(trans, '__json_data__') else {}
                        if trans_data.get('kind') == 'REFUND':
                            refund_amount = float(trans_data.get('amount', 0))
                            if trans_data.get('status') == 'PENDING':
                                refund_status = "Pending"
                                status_style = "yellow"
                            break
        
        refunds_table.add_row(
            refund_date,
            f"${refund_amount:.2f}",
            f"[{status_style}]{refund_status}[/{status_style}]"
        )
    
    console.print(refunds_table)
    console.print()


def format_refund_options_table(
    refund_amount: Optional[float],
    refund_message: Optional[str],
    credit_amount: Optional[float],
    credit_message: Optional[str],
    currency: str,
    console: Console
) -> None:
    """Display refund type options table."""
    options_table = Table(title="💰 Refund Options", show_header=True, box=None)
    options_table.add_column("Option", style="bold")
    options_table.add_column("Type", style="cyan")
    options_table.add_column("Amount", justify="right", style="green")
    options_table.add_column("Details", style="dim")
    
    if refund_amount is not None:
        refund_details = refund_message.split('(')[1].rstrip(')') if refund_message and '(' in refund_message else "Calculated"
        options_table.add_row(
            "[bold](o)[/bold] Original Payment",
            "Original Payment Method",
            f"${refund_amount:.2f} {currency}",
            refund_details
        )
    else:
        options_table.add_row(
            "[bold](o)[/bold] Original Payment",
            "Original Payment Method",
            "[yellow]Not available[/yellow]",
            "No calculation available"
        )
    
    if credit_amount is not None:
        credit_details = credit_message.split('(')[1].rstrip(')') if credit_message and '(' in credit_message else "Calculated"
        options_table.add_row(
            "[bold](s)[/bold] Store Credit",
            "Store Credit",
            f"${credit_amount:.2f} {currency}",
            credit_details
        )
    else:
        options_table.add_row(
            "[bold](s)[/bold] Store Credit",
            "Store Credit",
            "[yellow]Not available[/yellow]",
            "No calculation available"
        )
    
    console.print(options_table)
    console.print()


def format_refund_summary(
    estimated_refund_amount: Optional[float],
    estimated_refund_message: Optional[str],
    refund_type_display: str,
    customer_email: str,
    remaining_refundable: float,
    currency: str,
    console: Console
) -> None:
    """Display refund summary before confirmation."""
    console.print("[yellow]⚠️  Refund Summary:[/yellow]")
    
    if estimated_refund_amount is not None:
        console.print(f"   • Estimated Refund Due: [bold green]${estimated_refund_amount:.2f} {currency}[/bold green]")
        if estimated_refund_message:
            # Extract just the calculation details from the message
            console.print(f"   • Calculation: [dim]{estimated_refund_message.split('(')[1].rstrip(')') if '(' in estimated_refund_message else ''}[/dim]")
    else:
        console.print("   • Estimated Refund Due: [yellow]Not available[/yellow]")
    
    console.print(f"   • Type: [bold]{refund_type_display}[/bold]")
    console.print(f"   • Customer: [bold]{customer_email}[/bold]")
    console.print("   • Customer notification: [bold]YES - Email will be sent[/bold]")
    console.print(f"   • Maximum refundable: [bold]${remaining_refundable:.2f} {currency}[/bold]")
    console.print()


def format_refund_header(
    order_name: str,
    customer_name: str,
    customer_email: str,
    console: Console
) -> None:
    """Display refund order header."""
    console.print(Panel(
        "[bold cyan]Refund Order[/bold cyan]\n"
        f"Order: {order_name}\n"
        f"Customer: {customer_name or customer_email}",
        border_style="cyan"
    ))
    console.print()


def format_refund_success(
    order_name: str,
    refund_id: str,
    refund_amount: float,
    refund_type_display: str,
    refund_created: str,
    currency: str,
    console: Console
) -> None:
    """Display successful refund information."""
    console.print(Panel(
        "[bold green]✓ Refund Processed Successfully[/bold green]",
        border_style="green"
    ))
    
    success_rows = [
        ("Order", order_name),
        ("Refund ID", refund_id),
        ("Amount Refunded", f"${refund_amount:.2f} {currency}"),
        ("Refund Type", refund_type_display),
        ("Created At", refund_created),
        ("Customer Notified", "✓ YES - Email sent")
    ]
    
    success_table = create_info_table(success_rows)
    console.print(success_table)
    console.print()
    console.print("[dim]Customer has been notified via email about the refund.[/dim]\n")


# ============================================================================
# ORDER FORMATTING - CSV EXPORT
# ============================================================================

def get_order_csv_headers() -> List[str]:
    """Get CSV headers matching the Shopify export format."""
    return [
        'Order Number',
        'Email',
        'Updated at',
        'Fully paid',
        'Fulfillment status',
        'Current subtotal quantity',
        'Discount code',
        'Line items: Name',
        'Total price',
        'Line items: SKU',
        'Line items: Vendor',
        'Line items: Product description HTML',
        'Line items: Title',
        'Line items: Variant title',
        'Billing address: First name',
        'Billing address: Last name',
        'Billing address: Address first line',
        'Billing address: City',
        'Billing address: Zip',
        'Billing address: Country',
        'Phone',
        'Line items: Custom attributes _Form Fields',
        'Line items: Custom attributes Are you interested in being a captain?',
        'Line items: Custom attributes Are you interested in reffing?',
        'Line items: Custom attributes Best Contact Email Address',
        'Line items: Custom attributes Best Contact Number (Cell Phone Number Preferred)',
        'Line items: Custom attributes Date of Birth',
        'Line items: Custom attributes Emergency Contact Name',
        'Line items: Custom attributes Emergency Contact Phone Number',
        'Line items: Custom attributes Gender Identity ',
        'Line items: Custom attributes Have you ever played any sport(s) with B.A.R.S. before?',
        "Line items: Custom attributes Have you played the sport you're registering for with B.A.R.S?",
        'Line items: Custom attributes If you chose "Two or More Races", please identify those races.',
        'Line items: Custom attributes Last Name',
        'Line items: Custom attributes Please select the one that best applies: Which racial categories best describe you?',
        'Line items: Custom attributes Preferred First Name',
        'Line items: Custom attributes Pronouns',
        'Line items: Custom attributes Shirt Size',
        'Line items: Custom attributes What is your self rated skill ranking?',
        'Line items: Custom attributes: Best Contact Phone Number (Cell Phone Number Preferred)',
        'isCanceled',
        'totalRefunded',
    ]


def order_to_csv_row(order_data: Dict[str, Any]) -> List[str]:
    """Convert order data to CSV row matching the Shopify export format.
    
    Args:
        order_data: Order dictionary (from __json_data__ or similar)
        
    Returns:
        List of string values for CSV row
    """
    # Get first line item (assuming one line item per order for this use case)
    line_items = order_data.get('lineItems', {})
    if isinstance(line_items, dict):
        edges = line_items.get('edges', [])
        line_item = edges[0]['node'] if edges else {}
    else:
        # Handle Connection format with nodes
        nodes = getattr(line_items, 'nodes', []) if hasattr(line_items, 'nodes') else []
        if nodes:
            line_item = nodes[0].__json_data__ if hasattr(nodes[0], '__json_data__') else {}
        else:
            line_item = {}
    
    # Get discount code
    discount_apps = order_data.get('discountApplications', {})
    discount_code = ''
    if isinstance(discount_apps, dict):
        edges = discount_apps.get('edges', [])
        for edge in edges:
            node = edge.get('node', {})
            if 'code' in node:
                discount_code = node.get('code', '')
                break
            if not discount_code and 'title' in node:
                discount_code = node.get('title', '')
    else:
        # Handle Connection format
        nodes = getattr(discount_apps, 'nodes', []) if hasattr(discount_apps, 'nodes') else []
        for node in nodes:
            node_data = node.__json_data__ if hasattr(node, '__json_data__') else {}
            if 'code' in node_data:
                discount_code = node_data.get('code', '')
                break
            if not discount_code and 'title' in node_data:
                discount_code = node_data.get('title', '')
    
    # Get billing address
    billing = order_data.get('billingAddress', {}) or {}
    if hasattr(billing, '__json_data__'):
        billing = billing.__json_data__
    
    # Format updatedAt date (M/D/YYYY format)
    updated_at = format_date_for_csv(order_data.get('updatedAt'))
    
    # Fully paid (true if financial status is PAID)
    fully_paid = str(order_data.get('displayFinancialStatus', '') == 'PAID').lower()
    
    # Phone - prefer billing address phone, fallback to order phone
    phone = billing.get('phone') or order_data.get('phone') or ''
    
    # Get line item data (handle both dict and object formats)
    if isinstance(line_item, dict):
        line_item_data = line_item
    else:
        line_item_data = line_item.__json_data__ if hasattr(line_item, '__json_data__') else {}
    
    variant = line_item_data.get('variant', {})
    if hasattr(variant, '__json_data__'):
        variant = variant.__json_data__
    
    product = line_item_data.get('product', {})
    if hasattr(product, '__json_data__'):
        product = product.__json_data__
    
    # Build CSV row matching the exact column order
    row = [
        order_data.get('name', ''),  # Order Number
        order_data.get('email', ''),  # Email
        updated_at,  # Updated at
        fully_paid,  # Fully paid
        order_data.get('displayFulfillmentStatus', ''),  # Fulfillment status
        str(order_data.get('subtotalLineItemsQuantity', 0)),  # Current subtotal quantity
        discount_code,  # Discount code
        line_item_data.get('name', ''),  # Line items: Name
        order_data.get('totalPriceSet', {}).get('shopMoney', {}).get('amount', ''),  # Total price
        variant.get('sku', '') if isinstance(variant, dict) else getattr(variant, 'sku', ''),  # Line items: SKU
        product.get('vendor', '') if isinstance(product, dict) else getattr(product, 'vendor', ''),  # Line items: Vendor
        product.get('descriptionHtml', '') if isinstance(product, dict) else getattr(product, 'descriptionHtml', ''),  # Line items: Product description HTML
        line_item_data.get('title', ''),  # Line items: Title
    ]
    
    row.extend([
        variant.get('title', '') if isinstance(variant, dict) else getattr(variant, 'title', ''),  # Line items: Variant title
        billing.get('firstName', ''),  # Billing address: First name
        billing.get('lastName', ''),  # Billing address: Last name
        billing.get('address1', ''),  # Billing address: Address first line
        billing.get('city', ''),  # Billing address: City
        billing.get('zip', ''),  # Billing address: Zip
        billing.get('country', ''),  # Billing address: Country
        phone,  # Phone
        get_custom_attribute_value(line_item_data, '_Form Fields'),  # Line items: Custom attributes _Form Fields
        get_custom_attribute_value(line_item_data, 'Are you interested in being a captain?'),  # Line items: Custom attributes Are you interested in being a captain?
        get_custom_attribute_value(line_item_data, 'Are you interested in reffing?'),  # Line items: Custom attributes Are you interested in reffing?
        get_custom_attribute_value(line_item_data, 'Best Contact Email Address'),  # Line items: Custom attributes Best Contact Email Address
        get_custom_attribute_value(line_item_data, 'Best Contact Number (Cell Phone Number Preferred)'),  # Line items: Custom attributes Best Contact Number (Cell Phone Number Preferred)
        get_custom_attribute_value(line_item_data, 'Date of Birth'),  # Line items: Custom attributes Date of Birth
        get_custom_attribute_value(line_item_data, 'Emergency Contact Name'),  # Line items: Custom attributes Emergency Contact Name
        get_custom_attribute_value(line_item_data, 'Emergency Contact Phone Number'),  # Line items: Custom attributes Emergency Contact Phone Number
        get_custom_attribute_value(line_item_data, 'Gender Identity '),  # Line items: Custom attributes Gender Identity (note the trailing space)
        get_custom_attribute_value(line_item_data, 'Have you ever played any sport(s) with B.A.R.S. before?'),  # Line items: Custom attributes Have you ever played any sport(s) with B.A.R.S. before?
        get_custom_attribute_value(line_item_data, "Have you played the sport you're registering for with B.A.R.S?"),  # Line items: Custom attributes Have you played the sport you're registering for with B.A.R.S?
        get_custom_attribute_value(line_item_data, 'If you chose "Two or More Races", please identify those races.'),  # Line items: Custom attributes If you chose "Two or More Races", please identify those races.
        get_custom_attribute_value(line_item_data, 'Last Name'),  # Line items: Custom attributes Last Name
        get_custom_attribute_value(line_item_data, 'Please select the one that best applies: Which racial categories best describe you?'),  # Line items: Custom attributes Please select the one that best applies: Which racial categories best describe you?
        get_custom_attribute_value(line_item_data, 'Preferred First Name'),  # Line items: Custom attributes Preferred First Name
        get_custom_attribute_value(line_item_data, 'Pronouns'),  # Line items: Custom attributes Pronouns
        get_custom_attribute_value(line_item_data, 'Shirt Size'),  # Line items: Custom attributes Shirt Size
        get_custom_attribute_value(line_item_data, 'What is your self rated skill ranking?'),  # Line items: Custom attributes What is your self rated skill ranking?
        get_custom_attribute_value(line_item_data, 'Best Contact Phone Number (Cell Phone Number Preferred)'),  # Line items: Custom attributes: Best Contact Phone Number (Cell Phone Number Preferred)
    ])
    
    # Check if order is canceled
    is_canceled = 'true' if order_data.get('cancelledAt') else 'false'
    
    # Calculate total refunded amount
    refunds = order_data.get('refunds', [])
    total_refunded = '0.00'
    if refunds:
        total = 0.0
        for refund in refunds:
            refund_data = refund.__json_data__ if hasattr(refund, '__json_data__') else refund
            total_refunded_set = refund_data.get('totalRefundedSet', {})
            shop_money = total_refunded_set.get('shopMoney', {})
            amount_str = shop_money.get('amount', '0')
            try:
                total += float(amount_str)
            except (ValueError, TypeError):
                continue
        total_refunded = f"{total:.2f}"
    
    row.extend([is_canceled, total_refunded])
    
    return row
