"""Cancel Shopify order command."""

import sys
from typing import Dict, Any, Optional, List, TYPE_CHECKING

import click
from rich.console import Console

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_ORDER_IDENTIFIER
from bars_cli._core.prompts import prompt_confirmation
from bars_cli.commands.shopify._shared.shopify_formatters import (
    _format_customer_name_from_order,
    _get_product_title_from_order,
    format_already_cancelled_order,
    format_order_to_cancel,
    format_cancellation_error,
    format_cancellation_success,
)

if TYPE_CHECKING:
    from bars_cli.backend_services.shopify.models.sgqlc_models import Order
else:
    Order = Any





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
) -> Optional[Dict[str, Any]]:
    """
    Cancel a Shopify order by order number or ID.
    
    This command runs in three stages:
    1. Cancel: Cancels the order (if not already cancelled)
    2. Refund: Prompts for refund (even if order was already cancelled)
    3. Restock: Prompts for inventory restock (regardless of cancel/refund outcome)
    
    IDENTIFIER: Order number (1234 or #1234) or Order ID (gid://shopify/Order/123 or 123).
    
    Examples:
      bars shopify order cancel 1234
      bars shopify order cancel #1234 --reason FRAUD
      bars shopify order cancel 1234 --confirm
    """
    console = Console()
    
    # Get service from context (lazily initialized via LazyServiceProxy)
    shopify_service = ctx.meta["shopify_service"]
    
    # Validate identifier
    if not identifier:
        click.echo("❌ Order identifier is required", err=True)
        raise click.ClickException("Order identifier is required")
    
    try:
        # ========================================================================
        # STAGE 1: CANCEL
        # ========================================================================
        order_num = identifier.get("identifier", "").strip().lstrip('#')
        console.print(f"\n[cyan]Looking up order #{order_num}...[/cyan]\n")
        
        orders: List[Order] = shopify_service.get_order_by_identifier(identifier, line_items_first=1)
        if not orders:
            click.echo("❌ No order found", err=True)
            raise click.ClickException(f"No order found with identifier: {identifier.get('identifier', 'N/A')}")
        
        order: Order = orders[0]
        order_id: str = order.id if hasattr(order, 'id') else ''
        order_name: str = order.name if hasattr(order, 'name') else 'N/A'
        
        # Get customer name and product title
        customer_name = _format_customer_name_from_order(order)
        product_title = _get_product_title_from_order(order)
        
        # Check if already cancelled
        cancelled_at = order.cancelledAt if hasattr(order, 'cancelledAt') else None
        order_already_cancelled = bool(cancelled_at)
        
        if order_already_cancelled:
            format_already_cancelled_order(order, order_name, customer_name, console)
        else:
        # Display order info before cancelling
            format_order_to_cancel(order, order_name, order_id, customer_name, product_title, console)
        
        # Confirmation
        if not confirm:
            if not prompt_confirmation("Are you sure you want to cancel this order?", default=True):
                console.print()
                console.print("[red]Cancellation aborted.[/red]\n")
                return {"success": False, "message": "Cancellation aborted by user"}
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
            format_cancellation_error(error_msg, console)
            raise click.ClickException(error_msg if isinstance(error_msg, str) else "; ".join(error_msg))
        
        # Success!
        job_data = cancel_result.get("data", {})
        job_id = job_data.get("id", "N/A")
        job_done = job_data.get("done", False)
        
        format_cancellation_success(order_num, job_id, job_done, reason, console)
        
        # ========================================================================
        # STAGE 2: REFUND (always prompt, even if already cancelled)
        # ========================================================================
        console.print()
        console.print("[cyan]━━━ Refund Stage ━━━[/cyan]\n")
        
        # Import refund command function
        from bars_cli.commands.shopify.orders.refund import refund_order_cmd
        
        # Invoke refund command using Click's invoke method
        try:
            ctx.invoke(refund_order_cmd, identifier=identifier, refund_type=None)
        except click.ClickException:
            # User cancelled refund or error occurred - continue to restock stage
            pass
        except SystemExit:
            # User interrupted - exit gracefully
            raise
        except Exception as e:
            # Log error but continue to restock stage
            console.print(f"[yellow]⚠️  Refund stage encountered an error: {str(e)}[/yellow]\n")
        
        # ========================================================================
        # STAGE 3: RESTOCK (always prompt, regardless of cancel/refund outcome)
        # ========================================================================
        console.print()
        console.print("[cyan]━━━ Restock Stage ━━━[/cyan]\n")
        
        # Inline restock logic - process immediately when variant number entered
        try:
            # Fetch order again to get line items
            orders_restock: List[Order] = shopify_service.get_order_by_identifier(identifier, line_items_first=50)
            if not orders_restock:
                console.print("[yellow]⚠️  Could not fetch order for restock.[/yellow]\n")
            else:
                order_restock: Order = orders_restock[0]
                
                # Get line items
                line_items_conn = order_restock.lineItems if hasattr(order_restock, 'lineItems') else None
                if line_items_conn:
                    nodes = getattr(line_items_conn, 'nodes', None)  # type: ignore[attr-defined]
                    if nodes:
                        line_items = list(nodes)
                        
                        # Get variant ID from first line item
                        from bars_cli.commands.shopify.orders.restock import _get_variant_id_from_line_items
                        variant_id = _get_variant_id_from_line_items(line_items)
                        
                        if variant_id:
                            # Get all variants for the product
                            try:
                                variants = shopify_service.get_product_variants_for_restock(variant_id)
                                if variants:
                                    # Display variants table
                                    from bars_cli.commands.shopify._shared.shopify_formatters import format_variants_table
                                    console.print("\n[bold]📦 Product Variants - Inventory Status[/bold]\n")
                                    format_variants_table(variants, console)
                                    
                                    # Prompt for single variant selection (process immediately)
                                    while True:
                                        selection = input("\nEnter variant number to restock (or press ENTER to skip): ").strip()
                                        
                                        if not selection:
                                            # Empty input - skip restock
                                            console.print("[dim]Restock skipped.[/dim]\n")
                                            break
                                        
                                        try:
                                            variant_index = int(selection) - 1
                                            if 0 <= variant_index < len(variants):
                                                selected_variant = variants[variant_index]
                                                inventory_item_id = selected_variant.get('inventory_item_id')
                                                
                                                if inventory_item_id:
                                                    # Process immediately - no "done" prompt
                                                    from bars_cli.commands.shopify.products.update_inventory import process_inventory_updates
                                                    restock_list = [(selected_variant['id'], inventory_item_id, 1)]
                                                    process_inventory_updates(shopify_service, variants, restock_list, console)
                                                    break
                                                else:
                                                    console.print("[red]Error: No inventory item ID found for this variant.[/red]")
                                                    break
                                            else:
                                                console.print(f"[red]Invalid selection. Enter a number between 1 and {len(variants)}, or press ENTER to skip.[/red]")
                                        except ValueError:
                                            console.print("[red]Invalid input. Enter a number or press ENTER to skip.[/red]")
                                else:
                                    console.print("[yellow]No variants found for this product.[/yellow]\n")
                            except ValueError as e:
                                console.print(f"[yellow]⚠️  Error fetching variants: {str(e)}[/yellow]\n")
                        else:
                            console.print("[dim]No variants found to restock.[/dim]\n")
                    else:
                        console.print("[dim]No line items found to restock.[/dim]\n")
                else:
                    console.print("[dim]No line items found to restock.[/dim]\n")
        except Exception as e:
            # Log error but don't fail the entire command
            console.print(f"[yellow]⚠️  Restock stage encountered an error: {str(e)}[/yellow]\n")
        
            console.print()
        
        # Return success result
        return {
            "success": True,
            "order_name": order_name if 'order_name' in locals() else 'N/A',
            "message": "Order cancellation workflow completed"
        }
        
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

