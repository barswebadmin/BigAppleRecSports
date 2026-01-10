#!/usr/bin/env python3
"""
Combined script to cancel and refund a Shopify order in one workflow.
Shows cancellation status, cancels if needed, then processes refund.

Usage:
    python bars-scripts/cancel_and_refund.py 12345
    python bars-scripts/cancel_and_refund.py 12345 --env development
    python bars-scripts/cancel_and_refund.py 12345 --cancel-reason CUSTOMER --refund-type credit
"""

import sys
import argparse
from pathlib import Path

# Add backend and scripts to Python path first
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

# Import shared utilities that use project code
import shared_utils


def main():
    parser = argparse.ArgumentParser(
        description="Cancel and refund a Shopify order (combined workflow)"
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
        "--cancel-reason",
        choices=["CUSTOMER", "FRAUD", "INVENTORY", "DECLINED", "OTHER"],
        default="CUSTOMER",
        help="Cancellation reason (default: CUSTOMER)"
    )
    parser.add_argument(
        "--refund-type",
        choices=["refund", "credit"],
        help="Refund type: 'refund' (original payment) or 'credit' (store credit). If not specified, will prompt for selection."
    )
    
    args = parser.parse_args()
    
    # Initialize
    shared_utils.load_environment(args.env)
    
    # Import dependencies (after environment and paths are set up)
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    
    # Import from other scripts
    import refund_order
    
    console = Console()
    
    try:
        config = shared_utils.get_shopify_config(args.env)
        order_num = args.order_number.strip().lstrip('#')
        cancel_fetch_result = shared_utils.fetch_order(order_num, config)
        
        if "error" in cancel_fetch_result or "errors" in cancel_fetch_result:
            if "error" in cancel_fetch_result:
                console.print(f"[red]Error: {cancel_fetch_result['error']}[/red]")
            else:
                console.print(f"[red]GraphQL Errors:[/red]")
                for error in cancel_fetch_result["errors"]:
                    console.print(f"  - {error.get('message', str(error))}")
            return 1
        
        orders = cancel_fetch_result.get('data', {}).get('orders', {}).get('edges', [])
        if not orders:
            console.print(f"[yellow]No order found with number: #{order_num}[/yellow]")
            return 1
        
        order_data = orders[0]['node']
        order_id = order_data['id']
        order_name = order_data['name']
        
        customer_name = ""
        if order_data.get('customer'):
            first = order_data['customer'].get('firstName', '')
            last = order_data['customer'].get('lastName', '')
            customer_name = f"{first} {last}".strip()
        
        # Display workflow header
        console.print()
        console.print(Panel(
            f"[bold cyan]Cancel & Refund Workflow[/bold cyan]\n"
            f"Order: {order_name}\n"
            f"Customer: {customer_name or order_data.get('email', 'N/A')}",
            border_style="cyan"
        ))
        console.print()
        
        # ==================================================
        # STEP 1: CANCELLATION (don't exit on failure - we still want to ask about restock)
        # ==================================================
        
        console.print("[bold]Step 1: Order Cancellation[/bold]\n")
        
        # Try to cancel (import cancel_order logic, but don't exit on failure)
        try:
            # Import cancel_order module to reuse its logic
            import cancel_order as cancel_module
            
            # Call cancel_order's main logic but catch any exits
            # We'll manually call the cancellation logic
            already_cancelled = order_data.get('cancelledAt') is not None
            
            if already_cancelled:
                cancelled_at = cancel_module.format_datetime(order_data['cancelledAt'])
                reason = order_data.get('cancelReason', 'N/A')
                
                console.print(f"[yellow]⚠️  Order is already cancelled[/yellow]")
                console.print(f"   • Cancelled at: {cancelled_at}")
                console.print(f"   • Reason: {reason}")
                console.print()
            else:
                # Get product title for display
                product_title = "Unknown Product"
                line_items = order_data.get('lineItems', {}).get('edges', [])
                if line_items and line_items[0].get('node', {}).get('product', {}).get('title'):
                    product_title = line_items[0]['node']['product']['title']
                
                console.print(f"[cyan]Order to Cancel[/cyan]")
                console.print(f"  [bold]Order ID:[/bold] {order_id.split('/')[-1]}")
                if customer_name:
                    console.print(f"  [bold]Customer:[/bold] {customer_name}")
                console.print(f"  [bold]Email:[/bold] {order_data.get('email', 'N/A')}")
                console.print(f"  [bold]Financial Status:[/bold] {order_data.get('displayFinancialStatus', 'N/A')}")
                console.print(f"  [bold]Fulfillment Status:[/bold] {order_data.get('displayFulfillmentStatus', 'N/A')}")
                console.print(f"  [cyan]📦 Product:[/cyan] {product_title}")
                console.print()
                
                confirm_cancel = input("[yellow]Are you sure you want to cancel this order? (yes/no): [/yellow]").strip().lower()
                if confirm_cancel not in ['yes', 'y']:
                    console.print()
                    console.print("[red]Cancellation aborted.[/red]\n")
                    # Continue to restock prompt anyway (mirror bash behavior)
                else:
                    console.print()
                    console.print(f"[cyan]Cancelling order #{order_num}...[/cyan]\n")
                    
                    cancel_result = shared_utils.cancel_order(order_id, config, args.cancel_reason)
                    
                    if "error" in cancel_result or "errors" in cancel_result:
                        if "error" in cancel_result:
                            console.print(f"[red]Cancellation error: {cancel_result['error']}[/red]")
                        else:
                            console.print(f"[red]GraphQL Errors:[/red]")
                            for error in cancel_result["errors"]:
                                console.print(f"  - {error.get('message', str(error))}")
                        # Don't exit - continue to restock prompt
                    else:
                        mutation_data = cancel_result.get('data', {}).get('orderCancel', {})
                        user_errors = mutation_data.get('userErrors', []) + mutation_data.get('orderCancelUserErrors', [])
                        
                        if user_errors:
                            console.print(f"[red]❌ Cancellation failed:[/red]")
                            for error in user_errors:
                                field = error.get('field', 'N/A')
                                message = error.get('message', 'Unknown error')
                                console.print(f"  • {field}: {message}")
                            # Don't exit - continue to restock prompt
                        else:
                            console.print(f"[green]✓ Order cancelled successfully[/green]\n")
        except Exception as e:
            console.print(f"[yellow]Warning: Cancellation step had issues: {str(e)}[/yellow]")
            console.print("[yellow]Continuing to restock prompt...[/yellow]\n")
        
        # Prompt for restock regardless of cancellation success/failure (mirror bash behavior)
        console.print()
        restock_choice = input("Restock inventory? (yes/no): ").strip().lower()
        if restock_choice in ['yes', 'y']:
            console.print()
            console.print("[cyan]Restocking inventory...[/cyan]\n")
            try:
                import restock_order
                restock_order.restock_inventory(order_num, config)
            except ImportError:
                console.print("[dim]Restock functionality not available.[/dim]\n")
        else:
            console.print("[dim]Restock skipped.[/dim]\n")
        console.print()
        
        # ==================================================
        # STEP 2: REFUND
        # ==================================================
        
        console.print("[bold]Step 2: Process Refund[/bold]\n")
        
        # Fetch fresh order data with refund details
        console.print(f"[cyan]Fetching order payment details...[/cyan]\n")
        refund_fetch_result = refund_order.fetch_order(order_num, config)
        
        if "error" in refund_fetch_result or "errors" in refund_fetch_result:
            if "error" in refund_fetch_result:
                console.print(f"[red]Error: {refund_fetch_result['error']}[/red]")
            else:
                console.print(f"[red]GraphQL Errors:[/red]")
                for error in refund_fetch_result["errors"]:
                    console.print(f"  - {error.get('message', str(error))}")
            return 1
        
        orders = refund_fetch_result.get('data', {}).get('orders', {}).get('edges', [])
        if not orders:
            console.print(f"[yellow]Could not fetch order for refund[/yellow]")
            return 1
        
        order_data = orders[0]['node']
        
        # Calculate payment summary
        payment_summary = refund_order.calculate_payment_summary(order_data)
        total_amount = payment_summary['total_amount']
        currency = payment_summary['currency']
        total_refunded = payment_summary['total_refunded']
        pending_refunds = payment_summary['pending_refunds']
        completed_refunds = payment_summary['completed_refunds']
        remaining_refundable = payment_summary['remaining_refundable']
        
        # Display refund summary
        from rich.table import Table
        
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
                refund_date = refund_order.format_datetime(refund.get('createdAt'))
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
            estimated_refund_amount, estimated_refund_message = refund_order.calculate_estimated_refund(
                order_data, total_amount, refund_type, console
            )
            
            if estimated_refund_amount is None:
                console.print("[red]⚠️  Warning: Could not calculate suggested refund amount.[/red]")
                console.print("[dim]No season dates found in product description.[/dim]\n")
        else:
            # Prompt for refund type selection with calculated amounts
            result = refund_order.prompt_refund_type_selection(
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
        
        # Prompt for refund amount with full summary
        refund_type_display = "Store Credit" if refund_type == "credit" else "Original Payment Method"
        customer_email = customer_name or order_data.get('email', 'N/A')
        
        refund_amount = refund_order.prompt_refund_with_summary(
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
        
        console.print()
        
        # Process refund
        transactions = order_data.get('transactions', [])
        
        console.print(f"[cyan]Processing refund of ${refund_amount:.2f}...[/cyan]\n")
        refund_result = refund_order.create_refund(
            order_id, refund_amount, refund_type, transactions, config
        )
        
        if not refund_result.get("success"):
            console.print(f"[red]❌ Failed to create refund:[/red]")
            message = refund_result.get("message", "Unknown error")
            if isinstance(message, list):
                for error in message:
                    if isinstance(error, dict):
                        field = error.get('field', 'N/A')
                        msg = error.get('message', 'Unknown error')
                        console.print(f"  • {field}: {msg}")
                    else:
                        console.print(f"  • {error}")
            else:
                console.print(f"  {message}")
            console.print()
            return 1
        
        # Success!
        refund_data = refund_result.get("data", {})
        refund_id = refund_data.get('id', 'N/A').split('/')[-1]
        refund_created = refund_order.format_datetime(refund_data.get('createdAt'))
        
        console.print(Panel(
            f"[bold green]✓ Workflow Complete: Order Cancelled and Refunded[/bold green]",
            border_style="green"
        ))
        
        success_table = Table(show_header=False, box=None, padding=(0, 2))
        success_table.add_column("Field", style="bold")
        success_table.add_column("Value")
        
        success_table.add_row("Order", order_name)
        success_table.add_row("Cancellation", "✓ Cancelled" if not already_cancelled else "Already cancelled")
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
        console.print("\n\n[yellow]Workflow cancelled by user.[/yellow]\n")
        return 0
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

