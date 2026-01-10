#!/usr/bin/env python3
"""
Standalone script to cancel a Shopify order by order number.
Checks if already cancelled and displays cancellation date.
Does not notify customer or restock inventory.

Usage:
    python scripts/cancel_order.py 12345
    python scripts/cancel_order.py 12345 --env development
    python scripts/cancel_order.py 12345 --reason CUSTOMER
"""

import sys
import argparse
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

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


def main():
    parser = argparse.ArgumentParser(
        description="Cancel a Shopify order by order number (no notification, no restock)"
    )
    parser.add_argument(
        "order_number",
        help="5-digit order number (with or without # prefix)"
    )
    parser.add_argument(
        "--env",
        choices=["development", "staging", "production"],
        default="production",
        help="Environment to use (default: production)"
    )
    parser.add_argument(
        "--reason",
        choices=["CUSTOMER", "FRAUD", "INVENTORY", "DECLINED", "OTHER"],
        default="CUSTOMER",
        help="Cancellation reason (default: CUSTOMER)"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    args = parser.parse_args()
    
    # Initialize
    shared_utils.load_environment(args.env)
    console = Console()
    
    try:
        # Get config
        config = shared_utils.get_shopify_config(args.env)
        order_num = args.order_number.strip().lstrip('#')
        
        # Fetch order first
        console.print(f"\n[cyan]Looking up order #{order_num} in {args.env}...[/cyan]\n")
        fetch_result = shared_utils.fetch_order(order_num, config)
        
        # Check for errors
        if "error" in fetch_result:
            console.print(f"[red]Error fetching order: {fetch_result['error']}[/red]")
            return 1
        
        if "errors" in fetch_result:
            console.print(f"[red]GraphQL Errors:[/red]")
            for error in fetch_result["errors"]:
                console.print(f"  - {error.get('message', str(error))}")
            return 1
        
        # Extract order data
        orders = fetch_result.get('data', {}).get('orders', {}).get('edges', [])
        
        if not orders:
            console.print(f"[yellow]No order found with number: #{order_num}[/yellow]")
            return 1
        
        order_data = orders[0]['node']
        order_id = order_data['id']
        customer_name = ""
        if order_data.get('customer'):
            first = order_data['customer'].get('firstName', '')
            last = order_data['customer'].get('lastName', '')
            customer_name = f"{first} {last}".strip()
        
        # Get product title from first line item
        product_title = "Unknown Product"
        line_items = order_data.get('lineItems', {}).get('edges', [])
        if line_items and line_items[0].get('node', {}).get('product', {}).get('title'):
            product_title = line_items[0]['node']['product']['title']
        
        # Check if already cancelled
        if order_data.get('cancelledAt'):
            cancelled_at = format_datetime(order_data['cancelledAt'])
            reason = order_data.get('cancelReason', 'N/A')
            
            header = Text()
            header.append(f"Order #{order_data['name']} ", style="bold yellow")
            header.append("[ALREADY CANCELLED]", style="bold red")
            
            console.print(Panel(header, title="Cancellation Status", border_style="red"))
            console.print(f"  [bold]Cancelled At:[/bold] {cancelled_at}")
            console.print(f"  [bold]Reason:[/bold] {reason}")
            if customer_name:
                console.print(f"  [bold]Customer:[/bold] {customer_name}")
            console.print(f"  [bold]Email:[/bold] {order_data.get('email', 'N/A')}")
            console.print()
            console.print("[yellow]This order is already cancelled. No action taken.[/yellow]\n")
            
            # Prompt for restock even if already cancelled (mirror bash behavior)
            restock_choice = input("Restock inventory? (yes/no): ").strip().lower()
            if restock_choice in ['yes', 'y']:
                console.print()
                console.print("[cyan]Restocking inventory...[/cyan]\n")
                try:
                    import restock_order
                    restock_order.restock_inventory(order_num, config)
                except ImportError:
                    console.print("[dim]Restock functionality not available.[/dim]\n")
            console.print()
            return 0
        
        # Display order info before cancelling
        header = Text()
        header.append(f"Order #{order_data['name']}", style="bold cyan")
        
        console.print(Panel(header, title="Order to Cancel", border_style="cyan"))
        console.print(f"  [bold]Order ID:[/bold] {order_id.split('/')[-1]}")
        if customer_name:
            console.print(f"  [bold]Customer:[/bold] {customer_name}")
        console.print(f"  [bold]Email:[/bold] {order_data.get('email', 'N/A')}")
        console.print(f"  [bold]Financial Status:[/bold] {order_data.get('displayFinancialStatus', 'N/A')}")
        console.print(f"  [bold]Fulfillment Status:[/bold] {order_data.get('displayFulfillmentStatus', 'N/A')}")
        console.print(f"  [cyan]📦 Product:[/cyan] {product_title}")
        console.print()
        
        # Confirmation (always required, mirror bash behavior)
        confirm = input("[yellow]Are you sure you want to cancel this order? (yes/no): [/yellow]").strip().lower()
        if confirm not in ['yes', 'y']:
            console.print()
            console.print("[red]Cancellation aborted.[/red]\n")
            return 0
        console.print()
        
        # Cancel the order
        console.print(f"[cyan]Cancelling order #{order_num}...[/cyan]\n")
        cancel_result = shared_utils.cancel_order(order_id, config, args.reason)
        
        # Check for errors
        if "error" in cancel_result:
            console.print(f"[red]Error cancelling order: {cancel_result['error']}[/red]")
            return 1
        
        if "errors" in cancel_result:
            console.print(f"[red]GraphQL Errors:[/red]")
            for error in cancel_result["errors"]:
                console.print(f"  - {error.get('message', str(error))}")
            return 1
        
        # Check mutation result
        mutation_data = cancel_result.get('data', {}).get('orderCancel', {})
        
        user_errors = mutation_data.get('userErrors', []) + mutation_data.get('orderCancelUserErrors', [])
        if user_errors:
            console.print(f"[red]❌ Failed to cancel order:[/red]")
            for error in user_errors:
                field = error.get('field', 'N/A')
                message = error.get('message', 'Unknown error')
                console.print(f"  • {field}: {message}")
            console.print()
            return 1
        
        # Success!
        job_info = mutation_data.get('job', {})
        job_id = job_info.get('id', 'N/A')
        job_done = job_info.get('done', False)
        
        console.print(Panel(
            f"[bold green]✓ Order #{order_num} successfully cancelled[/bold green]",
            border_style="green"
        ))
        console.print(f"  [bold]Cancellation Job ID:[/bold] {job_id}")
        console.print(f"  [bold]Job Status:[/bold] {'Completed' if job_done else 'In Progress'}")
        console.print(f"  [bold]Reason:[/bold] {args.reason}")
        console.print()
        console.print("[dim]Note: Customer was NOT notified and inventory was NOT restocked.[/dim]")
        console.print("[dim]If a refund is needed, it must be processed separately.[/dim]\n")
        
        # Prompt for restock
        restock_choice = input("Restock inventory? (yes/no): ").strip().lower()
        if restock_choice in ['yes', 'y']:
            console.print()
            console.print("[cyan]Restocking inventory...[/cyan]\n")
            # Call restock (import here to avoid circular dependency)
            try:
                import restock_order
                restock_order.restock_inventory(order_num, config)
            except ImportError:
                console.print("[dim]Restock functionality not available.[/dim]\n")
        
        return 0
        
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

