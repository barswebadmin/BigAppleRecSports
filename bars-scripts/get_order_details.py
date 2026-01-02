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
from datetime import datetime
from typing import Dict, Any, Optional

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
    
    query = """
    query FetchOrderWithMetadata($q: String!) {
        orders(first: 1, query: $q) {
            edges {
                node {
                    id
                    name
                    email
                    createdAt
                    displayFinancialStatus
                    displayFulfillmentStatus
                    totalPriceSet {
                        shopMoney {
                            amount
                            currencyCode
                        }
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
                                customAttributes {
                                    key
                                    value
                                }
                                product {
                                    title
                                }
                                variant {
                                    id
                                    title
                                    price
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
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
        if args.json:
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

