"""Cancel and refund order command (combined workflow).

This command combines order cancellation and refund processing into a single workflow.
It first cancels the order, then prompts for restock, then processes the refund.

BACKEND SERVICE STATUS:
- ✅ EXISTS: shopify_service.cancel_order() - Cancels order with options
- ✅ EXISTS: shopify_service.create_refund() - Creates refund (needs verification)
- ⚠️  NEEDS: Combined workflow logic (cancel → restock prompt → refund)

CLI RESPONSIBILITIES:
- Orchestrate the workflow (cancel → restock prompt → refund)
- Display order info before cancellation
- Prompt for restock after cancellation (always, even if already cancelled)
- Prompt for refund amount and type
- Display progress and results

BACKEND RESPONSIBILITIES:
- Execute cancel_order mutation
- Execute refundCreate mutation
- Handle error responses
- Return structured success/error responses
"""
import sys
from typing import Dict, Any, Optional

import click
from rich.console import Console
from rich.panel import Panel

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_ORDER_IDENTIFIER
from bars_cli.commands.shopify._shared.command_helpers import get_shopify_service


@click.command('cancel-and-refund')
@handle_display_options(display=True, exit_on_error=True)
@click.option('--cancel-reason', type=click.Choice(['CUSTOMER', 'FRAUD', 'INVENTORY', 'DECLINED', 'OTHER'], case_sensitive=False), default='CUSTOMER', help='Cancellation reason')
@click.option('--refund-type', type=click.Choice(['refund', 'credit'], case_sensitive=False), help='Refund type (prompts if not provided)')
@click.option('--confirm', is_flag=True, default=False, help='Skip confirmation prompts')
@click.argument('identifier', type=SHOPIFY_ORDER_IDENTIFIER, required=False)
@click.pass_context
def cancel_and_refund_cmd(
    ctx: click.Context,
    identifier: Optional[Dict[str, Any]],
    cancel_reason: str = 'CUSTOMER',
    refund_type: Optional[str] = None,
    confirm: bool = False
) -> None:
    """
    Cancel an order and process a refund in a single workflow.
    
    Workflow:
    1. Cancel order (with confirmation unless --confirm)
    2. Prompt for restock (always, regardless of cancellation success)
    3. Process refund (with calculation and type selection)
    
    IDENTIFIER: Order number (1234 or #1234) or Order ID (gid://shopify/Order/123 or 123).
    
    Examples:
      bars shopify order cancel-and-refund 1234
      bars shopify order cancel-and-refund #1234 --cancel-reason FRAUD
      bars shopify order cancel-and-refund 1234 --refund-type credit
    """
    console = Console()
    shopify_service = get_shopify_service(ctx, "order")
    
    # Validate identifier
    if not identifier:
        click.echo("❌ Order identifier is required", err=True)
        raise click.ClickException("Order identifier is required")
    
    try:
        # STEP 1: Get order details
        order_num = identifier.get("identifier", "").strip().lstrip('#')
        console.print(f"\n[cyan]Looking up order #{order_num}...[/cyan]\n")
        
        orders = shopify_service.get_order_by_identifier(identifier, line_items_first=1)
        if not orders:
            click.echo("❌ No order found", err=True)
            raise click.ClickException(f"No order found with identifier: {identifier.get('identifier', 'N/A')}")
        
        order = orders[0]
        order_id = getattr(order, 'id', '')  # type: ignore[attr-defined]
        
        # STEP 2: Cancel order (reuse cancel_order_cmd logic)
        # PSEUDOCODE:
        # - Display order info
        # - Check if already cancelled
        # - Prompt for confirmation (unless --confirm)
        # - Call shopify_service.cancel_order(order_id, reason=cancel_reason, ...)
        # - Display cancellation result
        # - Continue even if cancellation was aborted or already cancelled
        
        console.print("[yellow]⚠️  Cancel order step - TODO: Implement cancellation logic[/yellow]")
        console.print(f"  Would call: shopify_service.cancel_order(order_id='{order_id}', reason='{cancel_reason}')")
        
        # STEP 3: Always prompt for restock (even if already cancelled)
        # PSEUDOCODE:
        # - Prompt: "Restock inventory? (yes/no): "
        # - If yes, call restock functionality (may need to be implemented)
        # - Display restock result
        
        if not confirm:
            restock_choice = input("\nRestock inventory? (yes/no): ").strip().lower()
            if restock_choice in ['yes', 'y']:
                console.print("[yellow]⚠️  Restock step - TODO: Implement restock logic[/yellow]")
                # Would call: shopify_service.restock_order(order_id, variant_quantities)
        
        # STEP 4: Process refund (reuse refund_order_cmd logic)
        # PSEUDOCODE:
        # - Calculate refund amount based on order submission timestamp
        # - Display refund calculation details
        # - Show both original payment and store credit options
        # - Prompt for refund type if not provided via --refund-type
        # - Prompt for refund amount (default to calculated amount)
        # - Call shopify_service.create_refund(order_id, amount, refund_type, notify=True)
        # - Display refund result
        
        console.print("\n[yellow]⚠️  Refund step - TODO: Implement refund logic[/yellow]")
        console.print(f"  Would call: shopify_service.create_refund(order_id='{order_id}', amount=<calculated>, refund_type='{refund_type or 'refund'}')")
        
        console.print("\n[green]✅ Combined workflow complete (skeleton implementation)[/green]\n")
        
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Operation cancelled by user.[/yellow]\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise click.ClickException(str(e))
