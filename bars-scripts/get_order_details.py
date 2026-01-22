#!/usr/bin/env python3
"""
Standalone script to fetch order details from Shopify by order number.
Displays order information including cancellation status and refunds.

Usage:
    python scripts/get_order_details.py 12345
    python scripts/get_order_details.py  # Prompts for order number
    python scripts/get_order_details.py 12345 --json
    python scripts/get_order_details.py 12345 -P  # Show line item properties
    python scripts/get_order_details.py 12345 --env development
"""

import sys
import json
import argparse
import csv
import html
from datetime import datetime
from typing import Dict, Any, Optional, List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax

# Import shared utilities that use project code
import shared_utils


def format_datetime(dt_str: Optional[str]) -> str:
    """Format ISO datetime string to readable format."""
    if not dt_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %I:%M %p %Z")
    except:
        return dt_str


def fetch_order_with_metadata(order_number: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch order details including metadata fields."""
    order_num = order_number.strip().lstrip('#')
    
    # Query moved to bottom - see ALREADY MIGRATED section
    query = _FETCH_ORDER_WITH_METADATA_QUERY
    
    payload = {
        "query": query,
        "variables": {"q": f"name:#{order_num}"}
    }
    
    return shared_utils.make_graphql_request(payload, config)


def display_order_rich(order_data: Dict[str, Any], console: Console, show_properties: bool = False):
    """Display order details in a rich formatted output."""
    order = order_data
    
    # Order Header
    header = Text()
    header.append(f"Order #{order['name']}", style="bold cyan")
    if order.get('cancelledAt'):
        header.append(" [CANCELLED]", style="bold red")
    
    console.print(Panel(header, title="Order Details", border_style="cyan"))
    
    # Basic Info Table
    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_column("Field", style="bold")
    info_table.add_column("Value")
    
    info_table.add_row("Order ID", order['id'].split('/')[-1])
    info_table.add_row("Order Number", order['name'])
    info_table.add_row("Email", order.get('email', 'N/A'))
    info_table.add_row("Created At", format_datetime(order.get('createdAt')))
    
    customer = order.get('customer', {})
    if customer:
        customer_name = f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip()
        info_table.add_row("Customer", customer_name or 'N/A')
    
    total = order.get('totalPriceSet', {}).get('shopMoney', {})
    if total:
        amount = total.get('amount', '0')
        currency = total.get('currencyCode', 'USD')
        info_table.add_row("Total Price", f"${float(amount):.2f} {currency}")
    
    info_table.add_row("Financial Status", order.get('displayFinancialStatus', 'N/A'))
    info_table.add_row("Fulfillment Status", order.get('displayFulfillmentStatus', 'N/A'))
    
    console.print(info_table)
    console.print()
    
    # Cancellation Status
    if order.get('cancelledAt'):
        cancel_table = Table(title="❌ Cancellation Details", show_header=False, box=None, padding=(0, 2))
        cancel_table.add_column("Field", style="bold red")
        cancel_table.add_column("Value", style="red")
        
        cancel_table.add_row("Cancelled At", format_datetime(order['cancelledAt']))
        cancel_table.add_row("Reason", order.get('cancelReason', 'N/A'))
        
        console.print(cancel_table)
        console.print()
    
    # Line Items
    line_items = order.get('lineItems', {}).get('edges', [])
    if line_items:
        items_table = Table(title="📦 Line Items", show_header=True)
        items_table.add_column("Quantity", justify="center")
        items_table.add_column("Item")
        items_table.add_column("Variant")
        items_table.add_column("Price", justify="right")
        
        for edge in line_items:
            item = edge['node']
            variant = item.get('variant', {})
            items_table.add_row(
                str(item.get('quantity', 0)),
                item.get('title', 'N/A'),
                variant.get('title', 'N/A'),
                f"${float(variant.get('price', 0)):.2f}"
            )
        
        console.print(items_table)
        console.print()
        
        # Display properties if requested
        if show_properties:
            has_any_properties = False
            properties_data = []
            
            for idx, edge in enumerate(line_items, 1):
                item = edge['node']
                custom_attrs = item.get('customAttributes', [])
                
                if custom_attrs:
                    has_any_properties = True
                    properties_data.append({
                        "line_item_id": item.get('id', 'N/A').split('/')[-1],
                        "line_item_name": item.get('name', 'N/A'),
                        "properties": custom_attrs
                    })
            
            if has_any_properties:
                console.print("[bold cyan]Line Item Properties:[/bold cyan]")
                json_str = json.dumps(properties_data, indent=2)
                syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
                console.print(syntax)
                console.print()
            else:
                console.print("[dim]No properties found on line items.[/dim]\n")
    
    # Refunds
    refunds = order.get('refunds', [])
    if refunds:
        console.print(Panel(f"💰 Refunds ({len(refunds)} total)", style="yellow"))
        
        for idx, refund in enumerate(refunds, 1):
            refund_table = Table(show_header=False, box=None, padding=(0, 2))
            refund_table.add_column("Field", style="bold yellow")
            refund_table.add_column("Value")
            
            refund_id = refund['id'].split('/')[-1]
            refund_table.add_row("Refund ID", refund_id)
            refund_table.add_row("Created At", format_datetime(refund.get('createdAt')))
            
            total_refunded = refund.get('totalRefundedSet', {}).get('shopMoney', {})
            if total_refunded:
                amount = total_refunded.get('amount', '0')
                currency = total_refunded.get('currencyCode', 'USD')
                refund_table.add_row("Amount", f"${float(amount):.2f} {currency}")
            
            if refund.get('note'):
                refund_table.add_row("Note", refund['note'])
            
            console.print(f"\n[bold]Refund #{idx}[/bold]")
            console.print(refund_table)
            
            # Refund line items
            refund_items = refund.get('refundLineItems', {}).get('edges', [])
            if refund_items:
                items_table = Table(show_header=True, title="Refunded Items", box=None)
                items_table.add_column("Quantity", justify="center")
                items_table.add_column("Item")
                items_table.add_column("Restock Type")
                
                for item_edge in refund_items:
                    item = item_edge['node']
                    line_item = item.get('lineItem', {})
                    items_table.add_row(
                        str(item.get('quantity', 0)),
                        line_item.get('title', 'N/A'),
                        item.get('restockType', 'N/A')
                    )
                
                console.print(items_table)
            
            # Transactions
            transactions = refund.get('transactions', {}).get('edges', [])
            if transactions:
                trans_table = Table(show_header=True, title="Transactions", box=None)
                trans_table.add_column("Kind")
                trans_table.add_column("Status")
                trans_table.add_column("Amount", justify="right")
                trans_table.add_column("Gateway")
                
                for trans_edge in transactions:
                    trans = trans_edge['node']
                    trans_table.add_row(
                        trans.get('kind', 'N/A'),
                        trans.get('status', 'N/A'),
                        f"${float(trans.get('amount', 0)):.2f}",
                        trans.get('gateway', 'N/A')
                    )
                
                console.print(trans_table)
        
        console.print()
    else:
        console.print("[dim]No refunds found for this order.[/dim]\n")


def order_to_csv_row(order_data: Dict[str, Any]) -> List[str]:
    """Convert order data to CSV row matching the Shopify export format."""
    order = order_data
    
    # Helper to get custom attribute value
    def get_custom_attr(line_item, key: str) -> str:
        attrs = line_item.get('customAttributes', [])
        # Decode HTML entities in the search key for matching
        key_decoded = html.unescape(key)
        for attr in attrs:
            attr_key = attr.get('key', '')
            # Decode HTML entities in the attribute key for comparison
            attr_key_decoded = html.unescape(attr_key)
            if attr_key_decoded == key_decoded:
                return attr.get('value', '')
        return ''
    
    # Get first line item (assuming one line item per order for this use case)
    line_items = order.get('lineItems', {}).get('edges', [])
    line_item = line_items[0]['node'] if line_items else {}
    
    # Get discount code
    discount_apps = order.get('discountApplications', {}).get('edges', [])
    discount_code = ''
    if discount_apps:
        # Try to get code from DiscountCodeApplication
        for edge in discount_apps:
            node = edge.get('node', {})
            if 'code' in node:
                discount_code = node.get('code', '')
                break
            # Fallback to title for other discount types
            if not discount_code and 'title' in node:
                discount_code = node.get('title', '')
    
    # Get billing address
    billing = order.get('billingAddress', {}) or {}
    
    # Format updatedAt date (9/11/2025 format)
    updated_at = ''
    if order.get('updatedAt'):
        try:
            dt = datetime.fromisoformat(order['updatedAt'].replace('Z', '+00:00'))
            # Format without leading zeros: 9/11/2025
            month = str(dt.month)
            day = str(dt.day)
            year = str(dt.year)
            updated_at = f"{month}/{day}/{year}"
        except:
            updated_at = order.get('updatedAt', '')
    
    # Fully paid (true if financial status is PAID)
    fully_paid = str(order.get('displayFinancialStatus', '') == 'PAID').lower()
    
    # Phone - prefer billing address phone, fallback to order phone
    phone = billing.get('phone') or order.get('phone') or ''
    
    # Build CSV row matching the exact column order from the sample CSV
    row = [
        order.get('name', ''),  # Order Number
        order.get('email', ''),  # Email
        updated_at,  # Updated at
        fully_paid,  # Fully paid
        order.get('displayFulfillmentStatus', ''),  # Fulfillment status
        str(order.get('subtotalLineItemsQuantity', 0)),  # Current subtotal quantity
        discount_code,  # Discount code
        line_item.get('name', ''),  # Line items: Name
        order.get('totalPriceSet', {}).get('shopMoney', {}).get('amount', ''),  # Total price
        line_item.get('variant', {}).get('sku', ''),  # Line items: SKU
        line_item.get('product', {}).get('vendor', ''),  # Line items: Vendor
        line_item.get('product', {}).get('descriptionHtml', ''),  # Line items: Product description HTML
        line_item.get('title', ''),  # Line items: Title
    ]
    
    row.extend([
        line_item.get('variant', {}).get('title', ''),  # Line items: Variant title
        billing.get('firstName', ''),  # Billing address: First name
        billing.get('lastName', ''),  # Billing address: Last name
        billing.get('address1', ''),  # Billing address: Address first line
        billing.get('city', ''),  # Billing address: City
        billing.get('zip', ''),  # Billing address: Zip
        billing.get('country', ''),  # Billing address: Country
        phone,  # Phone
        get_custom_attr(line_item, '_Form Fields'),  # Line items: Custom attributes _Form Fields
        get_custom_attr(line_item, 'Are you interested in being a captain?'),  # Line items: Custom attributes Are you interested in being a captain?
        get_custom_attr(line_item, 'Are you interested in reffing?'),  # Line items: Custom attributes Are you interested in reffing?
        get_custom_attr(line_item, 'Best Contact Email Address'),  # Line items: Custom attributes Best Contact Email Address
        get_custom_attr(line_item, 'Best Contact Number (Cell Phone Number Preferred)'),  # Line items: Custom attributes Best Contact Number (Cell Phone Number Preferred)
        get_custom_attr(line_item, 'Date of Birth'),  # Line items: Custom attributes Date of Birth
        get_custom_attr(line_item, 'Emergency Contact Name'),  # Line items: Custom attributes Emergency Contact Name
        get_custom_attr(line_item, 'Emergency Contact Phone Number'),  # Line items: Custom attributes Emergency Contact Phone Number
        get_custom_attr(line_item, 'Gender Identity '),  # Line items: Custom attributes Gender Identity (note the trailing space)
        get_custom_attr(line_item, 'Have you ever played any sport(s) with B.A.R.S. before?'),  # Line items: Custom attributes Have you ever played any sport(s) with B.A.R.S. before?
        get_custom_attr(line_item, "Have you played the sport you're registering for with B.A.R.S?"),  # Line items: Custom attributes Have you played the sport you're registering for with B.A.R.S?
        get_custom_attr(line_item, 'If you chose "Two or More Races", please identify those races.'),  # Line items: Custom attributes If you chose "Two or More Races", please identify those races.
        get_custom_attr(line_item, 'Last Name'),  # Line items: Custom attributes Last Name
        get_custom_attr(line_item, 'Please select the one that best applies: Which racial categories best describe you?'),  # Line items: Custom attributes Please select the one that best applies: Which racial categories best describe you?
        get_custom_attr(line_item, 'Preferred First Name'),  # Line items: Custom attributes Preferred First Name
        get_custom_attr(line_item, 'Pronouns'),  # Line items: Custom attributes Pronouns
        get_custom_attr(line_item, 'Shirt Size'),  # Line items: Custom attributes Shirt Size
        get_custom_attr(line_item, 'What is your self rated skill ranking?'),  # Line items: Custom attributes What is your self rated skill ranking?
        get_custom_attr(line_item, 'Best Contact Phone Number (Cell Phone Number Preferred)'),  # Line items: Custom attributes: Best Contact Phone Number (Cell Phone Number Preferred)
    ])
    
    # Check if order is canceled
    is_canceled = 'true' if order.get('cancelledAt') else 'false'
    
    # Calculate total refunded amount
    refunds = order.get('refunds', [])
    total_refunded = '0.00'
    if refunds:
        total = 0.0
        for refund in refunds:
            total_refunded_set = refund.get('totalRefundedSet', {})
            shop_money = total_refunded_set.get('shopMoney', {})
            amount_str = shop_money.get('amount', '0')
            try:
                total += float(amount_str)
            except (ValueError, TypeError):
                continue
        total_refunded = f"{total:.2f}"
    
    row.extend([is_canceled, total_refunded])
    
    return row


def get_csv_headers() -> List[str]:
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


def output_csv(order_data: Dict[str, Any], output_file: Optional[str] = None):
    """Output order data as CSV."""
    headers = get_csv_headers()
    row = order_to_csv_row(order_data)
    
    if output_file:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerow(row)
        print(f"CSV written to {output_file}")
    else:
        writer = csv.writer(sys.stdout)
        writer.writerow(headers)
        writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch order details from Shopify by order number"
    )
    parser.add_argument(
        "order_number",
        nargs="?",
        help="5-digit order number (with or without # prefix)"
    )
    parser.add_argument(
        "--env",
        choices=["development", "staging", "production"],
        default="production",
        help="Environment to use (default: production)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted display"
    )
    parser.add_argument(
        "-P", "--show-properties",
        action="store_true",
        dest="show_properties",
        help="Show line item properties as JSON"
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Output as CSV format matching Shopify export"
    )
    parser.add_argument(
        "--csv-file",
        type=str,
        help="Write CSV to file instead of stdout"
    )
    
    args = parser.parse_args()
    
    # Prompt for order number if not provided
    order_number = args.order_number
    if not order_number:
        try:
            order_number = input("Enter order number: ").strip()
            if not order_number:
                print("Error: Order number is required", file=sys.stderr)
                return 1
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled", file=sys.stderr)
            return 1
    
    # Initialize
    shared_utils.load_environment(args.env)
    console = Console()
    
    try:
        # Get config
        config = shared_utils.get_shopify_config(args.env)
        
        # Fetch order (with metadata if requested)
        console.print(f"\n[cyan]Fetching order #{order_number.lstrip('#')} from {args.env}...[/cyan]\n")
        result = fetch_order_with_metadata(order_number, config)
        
        # Check for errors
        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            return 1
        
        if "errors" in result:
            console.print(f"[red]GraphQL Errors:[/red]")
            for error in result["errors"]:
                console.print(f"  - {error.get('message', str(error))}")
            return 1
        
        # Extract order data
        orders = result.get('data', {}).get('orders', {}).get('edges', [])
        
        if not orders:
            console.print(f"[yellow]No order found with number: {order_number}[/yellow]")
            return 1
        
        order_data = orders[0]['node']
        
        # Output
        if args.csv or args.csv_file:
            output_csv(order_data, output_file=args.csv_file)
        elif args.json:
            print(json.dumps(order_data, indent=2))
        else:
            display_order_rich(order_data, console, show_properties=args.show_properties)
        
        return 0
        
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())


# ============================================================================
# ALREADY MIGRATED - GraphQL Query Structures
# ============================================================================
# These query structures have been migrated to sgqlc models.
# They are kept here for reference only and should not be used in new code.

_FETCH_ORDER_WITH_METADATA_QUERY = """
    query FetchOrderWithMetadata($q: String!) {
        orders(first: 1, query: $q) {
            edges {
                node {
                    id
                    name
                    email
                    createdAt
                    updatedAt
                    phone
                    displayFinancialStatus
                    displayFulfillmentStatus
                    subtotalLineItemsQuantity
                    totalPriceSet {
                        shopMoney {
                            amount
                            currencyCode
                        }
                    }
                    discountApplications(first: 10) {
                        edges {
                            node {
                                ... on DiscountCodeApplication {
                                    code
                                }
                                ... on ScriptDiscountApplication {
                                    title
                                }
                                ... on AutomaticDiscountApplication {
                                    title
                                }
                            }
                        }
                    }
                    billingAddress {
                        firstName
                        lastName
                        address1
                        city
                        zip
                        country
                        phone
                    }
                    customer {
                        id
                        email
                        firstName
                        lastName
                    }
                    cancelledAt
                    cancelReason
                    refunds {
                        id
                        createdAt
                        note
                        totalRefundedSet {
                            presentmentMoney {
                                amount
                                currencyCode
                            }
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                        refundLineItems(first: 50) {
                            edges {
                                node {
                                    quantity
                                    restockType
                                    lineItem {
                                        id
                                        name
                                        title
                                    }
                                }
                            }
                        }
                        transactions(first: 10) {
                            edges {
                                node {
                                    id
                                    kind
                                    status
                                    amount
                                    gateway
                                    createdAt
                                }
                            }
                        }
                    }
                    transactions {
                        id
                        kind
                        gateway
                        status
                        amount
                        parentTransaction {
                            id
                        }
                    }
                    lineItems(first: 50) {
                        edges {
                            node {
                                id
                                name
                                title
                                quantity
                                fulfillableQuantity
                                fulfillmentStatus
                                originalUnitPriceSet {
                                    shopMoney {
                                        amount
                                        currencyCode
                                    }
                                }
                                discountedUnitPriceSet {
                                    shopMoney {
                                        amount
                                        currencyCode
                                    }
                                }
                                originalTotalSet {
                                    shopMoney {
                                        amount
                                        currencyCode
                                    }
                                }
                                discountedTotalSet {
                                    shopMoney {
                                        amount
                                        currencyCode
                                    }
                                }
                                customAttributes {
                                    key
                                    value
                                }
                                product {
                                    """ + shared_utils.get_product_fields() + """
                                }
                                variant {
                                    id
                                    title
                                    price
                                    sku
                                }
                            }
                        }
                    }
                }
            }
        }
    }
"""

