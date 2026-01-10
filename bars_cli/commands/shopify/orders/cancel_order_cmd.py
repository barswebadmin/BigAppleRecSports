"""Cancel Shopify order command."""

import sys
from typing import Dict, Any, Optional
from datetime import datetime

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_ORDER_IDENTIFIER
from bars_cli._core.ui.display import format_datetime, create_text_panel


def _format_customer_name(order: Any) -> str:
    """Format customer name from order."""
    customer = getattr(order, 'customer', None)  # type: ignore[attr-defined]
    if not customer:
        return "N/A"
    
    if hasattr(customer, 'displayName') and customer.displayName:  # type: ignore[attr-defined]
        return customer.displayName  # type: ignore[attr-defined]
    
    first = getattr(customer, 'firstName', None)  # type: ignore[attr-defined]
    last = getattr(customer, 'lastName', None)  # type: ignore[attr-defined]
    if first or last:
        return f"{first or ''} {last or ''}".strip()
    
    return "N/A"


def format_datetime_display(dt_str: Optional[str]) -> str:
    """Format ISO datetime string to readable format."""
    return format_datetime(dt_str)


@click.command('cancel')
@handle_display_options(display=True, exit_on_error=True)
@click.option('--reason', type=click.Choice(['CUSTOMER', 'FRAUD', 'INVENTORY', 'DECLINED', 'OTHER'], case_sensitive=False), default='CUSTOMER', help='Cancellation reason')
@click.option('--confirm', is_flag=True, default=False, help='Skip confirmation prompt')
@click.argument('identifier', type=SHOPIFY_ORDER_IDENTIFIER, required=False)
@click.pass_context
def cancel_order_cmd(
    ctx: click.Context,
    identifier: Optional[Dict[str, Any]],
    reason: str = 'CUSTOMER',
    confirm: bool = False
) -> None:
    """
    Cancel a Shopify order by order number or ID.
    
    Does not notify customer or restock inventory by default.
    
    IDENTIFIER: Order number (1234 or #1234) or Order ID (gid://shopify/Order/123 or 123).
    
    Examples:
      bars shopify order cancel 1234
      bars shopify order cancel #1234 --reason FRAUD
      bars shopify order cancel 1234 --confirm
    """
    from bars_cli.commands.shopify._shared.command_helpers import get_shopify_service
    
    console = Console()
    
    # Get service from context
    shopify_service = get_shopify_service(ctx, "order")
    
    # Validate identifier
    if not identifier:
        click.echo("❌ Order identifier is required", err=True)
        raise click.ClickException("Order identifier is required")
    
    try:
        # Fetch order first
        order_num = identifier.get("identifier", "").strip().lstrip('#')
        console.print(f"\n[cyan]Looking up order #{order_num}...[/cyan]\n")
        
        orders = shopify_service.get_order_by_identifier(identifier, line_items_first=1)
        if not orders:
            click.echo("❌ No order found", err=True)
            raise click.ClickException(f"No order found with identifier: {identifier.get('identifier', 'N/A')}")
        
        order = orders[0]
        order_id = getattr(order, 'id', '')  # type: ignore[attr-defined]
        order_name = getattr(order, 'name', 'N/A')  # type: ignore[attr-defined]
        
        # Get customer name
        customer_name = _format_customer_name(order)
        
        # Get product title from first line item
        product_title = "Unknown Product"
        line_items_conn = getattr(order, 'lineItems', None)  # type: ignore[attr-defined]
        if line_items_conn:
            nodes = getattr(line_items_conn, 'nodes', None)  # type: ignore[attr-defined]
            if nodes and len(nodes) > 0:
                first_item = nodes[0]
                product = getattr(first_item, 'product', None)  # type: ignore[attr-defined]
                if product:
                    product_title = getattr(product, 'title', 'Unknown Product')  # type: ignore[attr-defined]
        
        # Check if already cancelled
        cancelled_at = getattr(order, 'cancelledAt', None)  # type: ignore[attr-defined]
        if cancelled_at:
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
            
            # Prompt for restock even if already cancelled
            restock_choice = input("Restock inventory? (yes/no): ").strip().lower()
            if restock_choice in ['yes', 'y']:
                console.print()
                console.print("[cyan]Restocking inventory...[/cyan]\n")
                # TODO: Implement restock functionality
                console.print("[dim]Restock functionality not yet implemented in CLI.[/dim]\n")
            console.print()
            return
        
        # Display order info before cancelling
        header_parts = [(f"Order #{order_name}", "bold cyan")]
        panel = create_text_panel(header_parts, title="Order to Cancel", border_style="cyan")
        console.print(panel)
        
        order_id_short = order_id.split('/')[-1] if '/' in order_id else order_id
        console.print(f"  [bold]Order ID:[/bold] {order_id_short}")
        if customer_name and customer_name != "N/A":
            console.print(f"  [bold]Customer:[/bold] {customer_name}")
        console.print(f"  [bold]Email:[/bold] {getattr(order, 'email', 'N/A')}")  # type: ignore[attr-defined]
        console.print(f"  [bold]Financial Status:[/bold] {getattr(order, 'displayFinancialStatus', 'N/A')}")  # type: ignore[attr-defined]
        console.print(f"  [bold]Fulfillment Status:[/bold] {getattr(order, 'displayFulfillmentStatus', 'N/A')}")  # type: ignore[attr-defined]
        console.print(f"  [cyan]📦 Product:[/cyan] {product_title}")
        console.print()
        
        # Confirmation
        if not confirm:
            confirm_input = input("[yellow]Are you sure you want to cancel this order? (yes/no): [/yellow]").strip().lower()
            if confirm_input not in ['yes', 'y']:
                console.print()
                console.print("[red]Cancellation aborted.[/red]\n")
                return
            console.print()
        
        # Cancel the order
        console.print(f"[cyan]Cancelling order #{order_num}...[/cyan]\n")
        cancel_result = shopify_service.cancel_order(
            order_id=order_id,
            reason=reason,
            notify_customer=False,
            refund=False,
            restock=False,
            staff_note="Cancelled via CLI"
        )
        
        # Check for errors
        if not cancel_result.get("success"):
            error_msg = cancel_result.get("message", "Unknown error")
            if isinstance(error_msg, list):
                console.print("[red]❌ Failed to cancel order:[/red]")
                for err in error_msg:
                    console.print(f"  • {err}")
            else:
                console.print(f"[red]❌ Failed to cancel order: {error_msg}[/red]")
            console.print()
            raise click.ClickException(error_msg if isinstance(error_msg, str) else "; ".join(error_msg))
        
        # Success!
        job_data = cancel_result.get("data", {})
        job_id = job_data.get("id", "N/A")
        job_done = job_data.get("done", False)
        
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
        
        # Prompt for restock
        restock_choice = input("Restock inventory? (yes/no): ").strip().lower()
        if restock_choice in ['yes', 'y']:
            console.print()
            console.print("[cyan]Restocking inventory...[/cyan]\n")
            # TODO: Implement restock functionality
            console.print("[dim]Restock functionality not yet implemented in CLI.[/dim]\n")
        
    except (RuntimeError, ValueError) as e:
        error_msg = str(e)
        click.echo(f"❌ Error: {error_msg}", err=True)
        raise click.ClickException(error_msg)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Cancellation cancelled by user.[/yellow]\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        raise click.ClickException(str(e))

