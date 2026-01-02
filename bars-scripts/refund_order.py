#!/usr/bin/env python3
"""
Refund order utilities for cancel_and_refund script.
"""

import sys
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path

# Add backend to Python path for date_utils import
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Add shared-utilities to Python path for retry_api_request
shared_utilities_path = Path(__file__).parent.parent / "shared-utilities" / "src"
if str(shared_utilities_path) not in sys.path:
    sys.path.insert(0, str(shared_utilities_path))

# Import shared utilities that use project code
import shared_utils


def fetch_order(order_number: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch order with product description for refund calculation."""
    order_num = order_number.strip().lstrip('#')
    
    query = """
    query FetchOrderForRefund($q: String!) {
        orders(first: 1, query: $q) {
            edges {
                node {
                    id
                    name
                    email
                    totalPriceSet {
                        shopMoney {
                            amount
                            currencyCode
                        }
                    }
                    customer {
                        firstName
                        lastName
                        email
                    }
                    refunds {
                        id
                        createdAt
                        totalRefundedSet {
                            shopMoney {
                                amount
                            }
                        }
                        transactions(first: 10) {
                            edges {
                                node {
                                    id
                                    kind
                                    status
                                    amount
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
                                title
                                quantity
                                product {
                                    id
                                    title
                                    descriptionHtml
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
    
    import os
    import requests
    
    ssl_cert_file = os.getenv('SSL_CERT_FILE', '/opt/homebrew/etc/openssl@3/cert.pem')
    verify_ssl = ssl_cert_file if os.path.exists(ssl_cert_file) else True
    
    try:
        response = requests.post(
            config["graphql_url"],
            json=payload,
            headers=config["headers"],
            timeout=30,
            verify=verify_ssl
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def create_refund(
    order_id: str, refund_amount: float, refund_type: str, transactions: list, config: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a refund using Shopify's refundCreate mutation."""
    return shared_utils.create_refund(order_id, refund_amount, refund_type, transactions, config)


def format_datetime(dt_str: Optional[str]) -> str:
    """Format datetime string for display."""
    if not dt_str:
        return "N/A"
    
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, AttributeError):
        return dt_str


def calculate_payment_summary(order_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate payment summary from order data."""
    total_price_data = order_data.get('totalPriceSet', {}).get('shopMoney', {})
    total_amount = float(total_price_data.get('amount', 0))
    currency = total_price_data.get('currencyCode', 'USD')
    
    refunds = order_data.get('refunds', [])
    total_refunded = 0.0
    pending_refunds = 0.0
    completed_refunds = 0.0
    
    for refund in refunds:
        refund_total = float(refund.get('totalRefundedSet', {}).get('shopMoney', {}).get('amount', 0))
        
        if refund_total == 0:
            refund_transactions = refund.get('transactions', {}).get('edges', [])
            for trans_edge in refund_transactions:
                trans = trans_edge['node']
                if trans.get('kind') == 'REFUND':
                    trans_amount = float(trans.get('amount', 0))
                    if trans.get('status') == 'PENDING':
                        pending_refunds += trans_amount
                    refund_total += trans_amount
                    break
        else:
            completed_refunds += refund_total
        
        total_refunded += refund_total
    
    remaining_refundable = total_amount - total_refunded
    
    return {
        'total_amount': total_amount,
        'currency': currency,
        'total_refunded': total_refunded,
        'pending_refunds': pending_refunds,
        'completed_refunds': completed_refunds,
        'remaining_refundable': remaining_refundable
    }


def parse_submitted_at_timestamp(timestamp_input: str, console) -> Optional[datetime]:
    """Parse submitted_at timestamp from user input."""
    if not timestamp_input:
        submitted_at = datetime.now(timezone.utc)
        console.print(f"[dim]Using current time: {submitted_at.strftime('%m/%d/%Y %H:%M:%S')} UTC[/dim]\n")
        return submitted_at
    
    try:
        # Parse timestamp: "10/23/2025 15:08:40"
        try:
            dt = datetime.strptime(timestamp_input, "%m/%d/%Y %H:%M:%S")
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            # Try alternative format
            try:
                dt = datetime.strptime(timestamp_input, "%m/%d/%Y %H:%M")
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                console.print("[red]Invalid timestamp format. Use MM/DD/YYYY HH:MM:SS[/red]")
                return None
    except Exception as e:
        console.print(f"[red]Error parsing timestamp: {str(e)}[/red]")
        return None


def calculate_estimated_refund(
    order_data: Dict[str, Any],
    total_amount: float,
    refund_type: str,
    console,
    submitted_at: Optional[datetime] = None
) -> Tuple[Optional[float], Optional[str]]:
    """Calculate estimated refund amount based on season dates."""
    from shared.date_utils import extract_season_dates, calculate_refund_amount
    
    line_items = order_data.get('lineItems', {}).get('edges', [])
    if not line_items:
        return None, None
    
    first_item = line_items[0].get('node', {})
    product = first_item.get('product', {})
    product_description = product.get('descriptionHtml', '')
    
    if not product_description:
        return None, None
    
    season_start_date_str, off_dates_str = extract_season_dates(product_description)
    
    if not season_start_date_str:
        return None, None
    
    if submitted_at is None:
        console.print("[cyan]Refund Calculation[/cyan]")
        console.print(f"Season start date found: {season_start_date_str}")
        if off_dates_str:
            console.print(f"Off dates: {off_dates_str}")
        else:
            console.print("[yellow]⚠️  No off dates detected in product description[/yellow]")
        console.print()
        
        while True:
            timestamp_input = input(
                "Enter submitted_at timestamp (format: MM/DD/YYYY HH:MM:SS, or press ENTER to use current time): "
            ).strip()
            
            submitted_at = parse_submitted_at_timestamp(timestamp_input, console)
            if submitted_at is None:
                continue
            break
    
    estimated_refund_amount, estimated_refund_message = calculate_refund_amount(
        season_start_date_str=season_start_date_str,
        off_dates_str=off_dates_str,
        total_amount_paid=total_amount,
        refund_type=refund_type,
        request_submitted_at=submitted_at
    )
    
    return estimated_refund_amount, estimated_refund_message


def prompt_refund_type_selection(
    order_data: Dict[str, Any],
    total_amount: float,
    remaining_refundable: float,
    currency: str,
    console
) -> Tuple[Optional[str], Optional[float], Optional[str], Optional[datetime]]:
    """
    Calculate refund amounts for both types and prompt user to select.
    
    Returns:
        Tuple of (refund_type, estimated_amount, estimated_message, submitted_at)
    """
    from shared.date_utils import extract_season_dates
    from rich.table import Table
    
    line_items = order_data.get('lineItems', {}).get('edges', [])
    if not line_items:
        return None, None, None, None
    
    first_item = line_items[0].get('node', {})
    product = first_item.get('product', {})
    product_description = product.get('descriptionHtml', '')
    
    if not product_description:
        return None, None, None, None
    
    season_start_date_str, off_dates_str = extract_season_dates(product_description)
    
    if not season_start_date_str:
        return None, None, None, None
    
    console.print("[cyan]Refund Calculation[/cyan]")
    console.print(f"Season start date found: {season_start_date_str}")
    if off_dates_str:
        console.print(f"Off dates: {off_dates_str}")
    else:
        console.print("[yellow]⚠️ No off dates detected in product description[/yellow]")
    console.print()
    
    # Get submitted_at timestamp once
    submitted_at = None
    while True:
        timestamp_input = input(
            "Enter submitted_at timestamp (format: MM/DD/YYYY HH:MM:SS, or press ENTER to use current time): "
        ).strip()
        
        submitted_at = parse_submitted_at_timestamp(timestamp_input, console)
        if submitted_at is None:
            continue
        break
    
    # Calculate for both refund types (using shared calculation logic)
    from shared.date_utils import calculate_refund_amount
    
    refund_amount, refund_message = calculate_refund_amount(
        season_start_date_str=season_start_date_str,
        off_dates_str=off_dates_str,
        total_amount_paid=total_amount,
        refund_type="refund",
        request_submitted_at=submitted_at
    )
    
    credit_amount, credit_message = calculate_refund_amount(
        season_start_date_str=season_start_date_str,
        off_dates_str=off_dates_str,
        total_amount_paid=total_amount,
        refund_type="credit",
        request_submitted_at=submitted_at
    )
    
    # Display both options
    console.print()
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
    
    # Prompt for selection
    while True:
        selection = input("Select refund type: (o) Original Payment, (s) Store Credit: ").strip().lower()
        
        if selection in ['o', 'original', 'original payment']:
            refund_type = "refund"
            estimated_amount = refund_amount
            estimated_message = refund_message
            break
        elif selection in ['s', 'store', 'store credit', 'credit']:
            refund_type = "credit"
            estimated_amount = credit_amount
            estimated_message = credit_message
            break
        else:
            console.print("[red]Invalid selection. Please enter 'o' for Original Payment or 's' for Store Credit.[/red]")
            continue
    
    return refund_type, estimated_amount, estimated_message, submitted_at


def prompt_refund_with_summary(
    remaining_refundable: float,
    estimated_refund_amount: Optional[float],
    estimated_refund_message: Optional[str],
    refund_type_display: str,
    customer_email: str,
    currency: str,
    console
) -> Optional[float]:
    """
    Prompt user for refund with full summary displayed.
    
    Returns:
        Refund amount if confirmed/entered, None if skipped
    """
    # Display full refund summary
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
    
    while True:
        if estimated_refund_amount is not None:
            prompt_text = (
                f"Type 'yes' or press ENTER to confirm refunding ${estimated_refund_amount:.2f}, "
                f"or enter a different amount: "
            )
        else:
            prompt_text = f"Enter refund amount (without $), or press ENTER to exit: "
        
        refund_amount_input = input(prompt_text).strip()
        
        # Empty input
        if not refund_amount_input:
            if estimated_refund_amount is not None:
                # User confirmed suggested amount by pressing ENTER
                if estimated_refund_amount > remaining_refundable:
                    console.print(f"[red]Suggested amount ${estimated_refund_amount:.2f} exceeds maximum refundable ${remaining_refundable:.2f}[/red]")
                    continue
                return estimated_refund_amount
            else:
                # No suggested amount, user skipped
                return None
        
        # Check if user typed 'yes' to confirm suggested amount
        if refund_amount_input.lower() in ['yes', 'y']:
            if estimated_refund_amount is not None:
                if estimated_refund_amount > remaining_refundable:
                    console.print(f"[red]Suggested amount ${estimated_refund_amount:.2f} exceeds maximum refundable ${remaining_refundable:.2f}[/red]")
                    continue
                return estimated_refund_amount
            else:
                console.print("[red]No suggested amount available. Please enter an amount.[/red]")
                continue
        
        # User entered a number - custom amount, proceed immediately
        try:
            refund_amount = float(refund_amount_input)
            
            if refund_amount <= 0:
                console.print("[red]Refund amount must be greater than 0.[/red]")
                continue
            
            if refund_amount > remaining_refundable:
                console.print(f"[red]Refund amount cannot exceed ${remaining_refundable:.2f}[/red]")
                continue
            
            return refund_amount
            
        except ValueError:
            console.print("[red]Invalid input. Enter a number, 'yes', or press ENTER.[/red]")




def main():
    """Standalone refund script entry point."""
    import argparse
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    
    parser = argparse.ArgumentParser(
        description="Refund a Shopify order"
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
        "--refund-type",
        choices=["refund", "credit"],
        help="Refund type: 'refund' (original payment) or 'credit' (store credit). If not specified, will prompt for selection."
    )
    
    args = parser.parse_args()
    
    console = Console()
    
    try:
        # Setup
        shared_utils.load_environment(args.env)
        config = shared_utils.get_shopify_config(args.env)
        order_num = args.order_number.strip().lstrip('#')
        
        # Fetch order
        console.print(f"\n[cyan]Fetching order details for #{order_num}...[/cyan]\n")
        fetch_result = fetch_order(order_num, config)
        
        if "error" in fetch_result or "errors" in fetch_result:
            if "error" in fetch_result:
                console.print(f"[red]Error: {fetch_result['error']}[/red]")
            else:
                console.print(f"[red]GraphQL Errors:[/red]")
                for error in fetch_result["errors"]:
                    console.print(f"  - {error.get('message', str(error))}")
            return 1
        
        orders = fetch_result.get('data', {}).get('orders', {}).get('edges', [])
        if not orders:
            console.print(f"[yellow]No order found with number: #{order_num}[/yellow]")
            return 1
        
        order_data = orders[0]['node']
        order_id = order_data['id']
        order_name = order_data['name']
        
        # Get customer name
        customer_name = ""
        if order_data.get('customer'):
            first = order_data['customer'].get('firstName', '')
            last = order_data['customer'].get('lastName', '')
            customer_name = f"{first} {last}".strip()
        
        # Display header
        console.print(Panel(
            f"[bold cyan]Refund Order[/bold cyan]\n"
            f"Order: {order_name}\n"
            f"Customer: {customer_name or order_data.get('email', 'N/A')}",
            border_style="cyan"
        ))
        console.print()
        
        # Calculate payment summary
        payment_summary = calculate_payment_summary(order_data)
        total_amount = payment_summary['total_amount']
        currency = payment_summary['currency']
        total_refunded = payment_summary['total_refunded']
        pending_refunds = payment_summary['pending_refunds']
        completed_refunds = payment_summary['completed_refunds']
        remaining_refundable = payment_summary['remaining_refundable']
        
        # Display payment summary
        payment_table = Table(title="💰 Payment Summary", show_header=False, box=None, padding=(0, 2))
        payment_table.add_column("Field", style="bold green")
        payment_table.add_column("Amount", style="green", justify="right")
        
        payment_table.add_row("Total Paid", f"${total_amount:.2f} {currency}")
        payment_table.add_row("Total Refunded", f"${total_refunded:.2f} {currency}")
        if pending_refunds > 0:
            payment_table.add_row("  - Pending", f"${pending_refunds:.2f} {currency}", style="yellow")
            payment_table.add_row("  - Completed", f"${completed_refunds:.2f} {currency}")
        payment_table.add_row("Remaining Refundable", f"${remaining_refundable:.2f} {currency}")
        
        console.print(payment_table)
        console.print()
        
        # Check if refund is possible
        if remaining_refundable <= 0:
            if total_amount == 0:
                console.print("[red]❌ No payment found. Order total is $0.00 - nothing to refund.[/red]\n")
            else:
                console.print("[red]❌ No refundable amount remaining. Order is fully refunded.[/red]\n")
            return 0
        
        # Show existing refunds
        refunds = order_data.get('refunds', [])
        if refunds:
            refunds_table = Table(title=f"📋 Existing Refunds ({len(refunds)} total)", show_header=True)
            refunds_table.add_column("Date", style="dim")
            refunds_table.add_column("Amount", justify="right")
            refunds_table.add_column("Status")
            
            for refund in refunds:
                refund_amount = float(refund.get('totalRefundedSet', {}).get('shopMoney', {}).get('amount', '0'))
                refund_date = format_datetime(refund.get('createdAt'))
                refund_status = "Completed"
                status_style = "green"
                
                if refund_amount == 0:
                    refund_transactions = refund.get('transactions', {}).get('edges', [])
                    for trans_edge in refund_transactions:
                        trans = trans_edge['node']
                        if trans.get('kind') == 'REFUND':
                            refund_amount = float(trans.get('amount', 0))
                            if trans.get('status') == 'PENDING':
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
        
        # Determine refund type and calculate amounts
        if args.refund_type:
            # Use provided refund type
            refund_type = args.refund_type
            estimated_refund_amount, estimated_refund_message = calculate_estimated_refund(
                order_data, total_amount, refund_type, console
            )
            
            if estimated_refund_amount is None:
                console.print("[red]⚠️  Warning: Could not calculate suggested refund amount.[/red]")
                console.print("[dim]No season dates found in product description.[/dim]\n")
        else:
            # Prompt for refund type selection with calculated amounts
            result = prompt_refund_type_selection(
                order_data, total_amount, remaining_refundable, currency, console
            )
            
            if result[0] is None:
                console.print("[red]⚠️  Warning: Could not calculate suggested refund amounts.[/red]")
                console.print("[dim]No season dates found in product description.[/dim]\n")
                refund_type = None
                estimated_refund_amount = None
                estimated_refund_message = None
            else:
                refund_type, estimated_refund_amount, estimated_refund_message, _ = result
        
        # Prompt for refund amount with summary
        refund_type_display = "Store Credit" if refund_type == "credit" else "Original Payment Method"
        customer_email = customer_name or order_data.get('email', 'N/A')
        
        refund_amount = prompt_refund_with_summary(
            remaining_refundable,
            estimated_refund_amount,
            estimated_refund_message,
            refund_type_display,
            customer_email,
            currency,
            console
        )
        
        if refund_amount is None:
            console.print("\n[yellow]Refund skipped. Workflow complete.[/yellow]\n")
            return 0
        
        if refund_type is None:
            # If no refund type was selected, prompt for it now
            while True:
                selection = input("Select refund type: (o) Original Payment, (s) Store Credit: ").strip().lower()
                if selection in ['o', 'original', 'original payment']:
                    refund_type = "refund"
                    break
                elif selection in ['s', 'store', 'store credit', 'credit']:
                    refund_type = "credit"
                    break
                else:
                    console.print("[red]Invalid selection. Please enter 'o' for Original Payment or 's' for Store Credit.[/red]")
        
        console.print()
        
        # Process refund
        transactions = order_data.get('transactions', [])
        
        console.print(f"[cyan]Processing refund of ${refund_amount:.2f}...[/cyan]\n")
        refund_result = create_refund(
            order_id, refund_amount, refund_type, transactions, config
        )
        
        if not refund_result.get("success"):
            console.print(f"[red]❌ Failed to create refund:[/red]")
            message = refund_result.get("message", refund_result.get("error", "Unknown error"))
            if isinstance(message, list):
                for error in message:
                    console.print(f"  • {error}")
            elif isinstance(message, str):
                console.print(f"  {message}")
            else:
                console.print(f"  {str(message)}")
            console.print()
            return 1
        
        # Success!
        refund_data = refund_result.get("data", {})
        refund_id = refund_data.get('id', 'N/A').split('/')[-1]
        refund_created = format_datetime(refund_data.get('createdAt'))
        
        console.print(Panel(
            f"[bold green]✓ Refund Processed Successfully[/bold green]",
            border_style="green"
        ))
        
        success_table = Table(show_header=False, box=None, padding=(0, 2))
        success_table.add_column("Field", style="bold")
        success_table.add_column("Value")
        
        success_table.add_row("Order", order_name)
        success_table.add_row("Refund ID", refund_id)
        success_table.add_row("Amount Refunded", f"${refund_amount:.2f} {currency}")
        success_table.add_row("Refund Type", refund_type_display)
        success_table.add_row("Created At", refund_created)
        success_table.add_row("Customer Notified", "✓ YES - Email sent")
        
        console.print(success_table)
        console.print()
        
        console.print(f"[dim]Customer has been notified via email about the refund.[/dim]\n")
        
        return 0
        
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Refund cancelled by user.[/yellow]\n")
        return 0
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

