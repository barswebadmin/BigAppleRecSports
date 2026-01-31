"""Cancel Shopify order command."""

import sys
from typing import Dict, Any, Optional, List, Tuple, TYPE_CHECKING, cast

import click_extra as click
from rich.console import Console

from bars_cli._core.context import get_display_context
from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_ORDER_IDENTIFIER
from bars_cli._core.prompts import prompt_confirmation
from bars_cli.commands.shopify._shared.shopify_formatters import (
    extract_connection_nodes,
    format_cancellation_error,
    format_cancellation_success,
    format_variants_table,
)
from bars_cli.commands.shopify.orders.refund import refund_order_cmd
from bars_cli.commands.shopify._shared.command_helpers import (
    extract_variant_id_from_line_items,
    handle_shopify_error_response,
    process_inventory_updates,
)

if TYPE_CHECKING:
    from bars_cli.backend_services.shopify.models.sgqlc_models import Order, LineItem
else:
    Order = Any
    LineItem = Any


def _handle_cancellation_stage(
    identifier: Dict[str, Any],
    ctx: click.Context,
    reason: str,
    confirm: bool,
    console: Console
) -> Tuple[Dict[str, Any], str, str, str]:
    """Handle cancellation stage: fetch order, check status, cancel if needed.
    
    Returns:
        Tuple of (order_dict, order_id, order_name, customer_name)
    """
    from bars_cli._core.context import get_http_client
    
    # Get HTTP client
    client = get_http_client(ctx)
    
    # Extract identifier info
    identifier_value = identifier.get("identifier", "")
    identifier_type = identifier.get("type", "")
    
    # Display lookup message
    order_num = identifier_value.strip().lstrip('#')
    console.print(f"\n[cyan]Looking up order #{order_num}...[/cyan]\n")
    
    # Build API endpoint with reason=cancel parameter
    if identifier_type == "order_number":
        endpoint = f'http://localhost:8000/orders?number={identifier_value}&reason=cancel'
    else:  # order_id
        endpoint = f'http://localhost:8000/orders?id={identifier_value}&reason=cancel'
    
    # Make the API request
    response = client.get(endpoint)
    
    # Handle response based on status code
    if response.status_code == 404:
        # Order not found
        error_msg = f"Order not found: {identifier_value}"
        console.print(f"[red]❌ {error_msg}[/red]\n")
        raise click.ClickException(error_msg)
    
    elif response.status_code == 202:
        # Order already canceled - extract enriched data and display warning
        try:
            response_data = response.json()
            data = response_data.get('data', {})
            message = response_data.get('message', 'Order already canceled')
            
            # Extract nested order data from enriched response
            order_data = data.get('order', {})
            cancellation_status = data.get('cancellation_status', {})
            payment_summary = data.get('payment_summary', {})
            
            # Format and display the order with enriched data
            _format_order_for_cancel_enriched(order_data, cancellation_status, payment_summary, console, already_canceled=True)
            
            # Extract order info for return
            order_id = order_data.get('id', '')
            order_name = order_data.get('name', f"#{order_num}")
            customer = order_data.get('customer', {})
            customer_name = f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip() if customer else "Unknown"
            
            # Warn but allow continuation
            console.print(f"\n[yellow]⚠️  {message}[/yellow]")
            
            # Prompt whether to continue
            if not confirm:
                if not prompt_confirmation("Order is already canceled. Continue to refund stage?", default=True):
                    console.print()
                    console.print("[red]Cancellation workflow aborted.[/red]\n")
                    raise click.ClickException("Workflow aborted by user")
                console.print()
            
            return order_data, order_id, order_name, customer_name
            
        except (ValueError, KeyError) as e:
            console.print(f"[red]Error parsing response: {e}[/red]\n")
            raise click.ClickException("Failed to parse API response")
    
    elif response.status_code == 200:
        # Order is eligible for cancellation
        try:
            response_data = response.json()
            data = response_data.get('data', {})
            
            if not data:
                error_msg = f"No order data returned for identifier: {identifier_value}"
                console.print(f"[red]❌ {error_msg}[/red]\n")
                raise click.ClickException(error_msg)
            
            # Extract nested order data from enriched response
            order_data = data.get('order', {})
            cancellation_status = data.get('cancellation_status', {})
            payment_summary = data.get('payment_summary', {})
            
            # Format and display the order with enriched data
            _format_order_for_cancel_enriched(order_data, cancellation_status, payment_summary, console, already_canceled=False)
            
            # Extract order info
            order_id = order_data.get('id', '')
            order_name = order_data.get('name', f"#{order_num}")
            customer = order_data.get('customer', {})
            customer_name = f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip() if customer else "Unknown"
            
            # Confirmation prompt
            if not confirm:
                if not prompt_confirmation("Are you sure you want to cancel this order?", default=True):
                    console.print()
                    console.print("[red]Cancellation aborted.[/red]\n")
                    raise click.ClickException("Cancellation aborted by user")
                console.print()
            
            # Now actually cancel the order using DELETE request
            console.print(f"[cyan]Cancelling order #{order_num}...[/cyan]\n")
            
            # Build DELETE endpoint
            delete_endpoint = f'http://localhost:8000/orders/{order_id}?reason={reason}'
            
            # Make DELETE request
            delete_response = client.delete(delete_endpoint)
            
            # Handle DELETE response
            if delete_response.status_code == 200:
                delete_data = delete_response.json()
                job_data = delete_data.get('data', {})
                job_id = job_data.get('id', 'N/A')
                job_done = job_data.get('done', False)
                
                format_cancellation_success(order_num, job_id, job_done, reason, console)
                
                return order_data, order_id, order_name, customer_name
            
            elif delete_response.status_code == 422:
                # Shopify returned user errors
                try:
                    error_response = delete_response.json()
                    if isinstance(error_response, dict) and 'detail' in error_response:
                        detail = error_response['detail']
                        if isinstance(detail, dict):
                            error_msg = detail.get('message', 'Cancellation failed')
                        else:
                            error_msg = str(detail)
                    else:
                        error_msg = error_response.get('message', 'Cancellation failed')
                except:
                    error_msg = "Cancellation failed"
                
                format_cancellation_error(error_msg, console)
                raise click.ClickException(error_msg)
            
            else:
                # Unexpected error
                error_msg = f"DELETE request failed with status {delete_response.status_code}"
                try:
                    error_response = delete_response.json()
                    if isinstance(error_response, dict):
                        if 'message' in error_response:
                            error_msg = f"API Error: {error_response['message']}"
                        elif 'detail' in error_response:
                            error_msg = f"API Error: {error_response['detail']}"
                except:
                    pass
                
                format_cancellation_error(error_msg, console)
                raise click.ClickException(error_msg)
            
        except (ValueError, KeyError) as e:
            console.print(f"[red]Error parsing response: {e}[/red]\n")
            raise click.ClickException("Failed to parse API response")
    
    else:
        # Unexpected status code
        error_msg = f"API request failed with status {response.status_code}"
        try:
            error_response = response.json()
            if isinstance(error_response, dict):
                if 'message' in error_response:
                    error_msg = f"API Error: {error_response['message']}"
                elif 'detail' in error_response:
                    error_msg = f"API Error: {error_response['detail']}"
        except:
            pass
        
        console.print(f"[red]❌ {error_msg}[/red]\n")
        raise click.ClickException(error_msg)




def _format_order_for_cancel_enriched(
    order: dict,
    cancellation_status: dict,
    payment_summary: dict,
    console: Console,
    already_canceled: bool = False
) -> None:
    """Format order data with enriched cancellation and payment info for display.
    
    Args:
        order: Order data dict from API
        cancellation_status: Cancellation status dict with is_canceled, canceled_at, etc.
        payment_summary: Payment summary dict with total_amount, refunded, remaining, etc.
        console: Rich console for output
        already_canceled: Whether order is already canceled
    """
    if already_canceled:
        console.print("\n[yellow]⚠️  Order Already Canceled[/yellow]")
    else:
        console.print("\n[green]✅ Order Found - Eligible for Cancellation[/green]")
    
    console.print("=" * 60)
    
    # Display order number
    order_name = order.get('name', 'N/A')
    console.print(f"{'Order':<20} {order_name}")
    
    # Display customer info
    customer = order.get('customer', {})
    if customer:
        if customer.get('firstName') or customer.get('lastName'):
            name = f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip()
            console.print(f"{'Customer':<20} {name}")
        if customer.get('email'):
            console.print(f"{'Email':<20} {customer['email']}")
    
    # Display payment summary
    currency = payment_summary.get('currency', 'USD')
    total_amount = payment_summary.get('total_amount', 0.0)
    total_refunded = payment_summary.get('total_refunded', 0.0)
    remaining_refundable = payment_summary.get('remaining_refundable', 0.0)
    
    console.print(f"\n{'Payment Summary:':<20}")
    console.print(f"  {'Total Paid':<18} ${total_amount:.2f} {currency}")
    console.print(f"  {'Total Refunded':<18} ${total_refunded:.2f} {currency}")
    console.print(f"  {'Remaining Refundable':<18} ${remaining_refundable:.2f} {currency}")
    
    # Display cancellation status
    console.print(f"\n{'Cancellation Status:':<20}")
    if cancellation_status.get('is_canceled'):
        canceled_at = cancellation_status.get('canceled_at', 'N/A')
        cancel_reason = cancellation_status.get('cancel_reason', 'N/A')
        console.print(f"  {'Status':<18} [yellow]Canceled[/yellow]")
        console.print(f"  {'Canceled At':<18} {canceled_at}")
        console.print(f"  {'Reason':<18} {cancel_reason}")
    else:
        console.print(f"  {'Status':<18} [green]Active (Eligible for Cancellation)[/green]")
    
    console.print("=" * 60)
    console.print()


def _format_order_for_cancel(order: dict, console: Console, already_canceled: bool = False) -> None:
    """Format order data for cancellation display.
    
    Args:
        order: Order data dict from API
        console: Rich console for output
        already_canceled: Whether order is already canceled
    """
    if already_canceled:
        console.print("\n[yellow]⚠️  Order Already Canceled[/yellow]")
    else:
        console.print("\n[green]✅ Order Found - Eligible for Cancellation[/green]")
    
    console.print("=" * 60)
    
    # Display order number as hyperlink (if available)
    if order.get('order_number_link'):
        console.print(f"{'Order':<20} {order['order_number_link']}")
    else:
        console.print(f"{'Order':<20} #{order.get('number', 'N/A')}")
    
    # Display product as hyperlink
    if order.get('product_link'):
        console.print(f"{'Product':<20} {order['product_link']}")
    elif order.get('product_title'):
        console.print(f"{'Product':<20} {order['product_title']}")
    
    # Display order email
    order_email = order.get('form_email')
    if order_email and order_email != 'N/A':
        console.print(f"{'Order Email':<20} {order_email}")
    else:
        console.print(f"{'Order Email':<20} Not collected in form")
    
    console.print(f"{'Amount Paid':<20} ${order.get('amount_paid', '0.00')}")
    
    if order.get('createdAt'):
        console.print(f"{'Created At':<20} {order['createdAt']}")
    
    # Cancellation status
    console.print(f"{'Cancellation Status':<20} {order.get('cancellation_status', 'N/A')}")
    
    # Refund status
    console.print(f"{'Refund Status':<20} {order.get('refund_status', 'N/A (Not Refunded)')}")
    
    # Customer info
    if order.get('customer'):
        customer = order['customer']
        console.print(f"\n{'Customer:':<20}")
        if customer.get('firstName') or customer.get('lastName'):
            name = f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip()
            console.print(f"  {'Name':<18} {name}")
        if customer.get('email'):
            console.print(f"  {'Email':<18} {customer['email']}")
    
    console.print("=" * 60)
    console.print()


def _handle_refund_stage(
    ctx: click.Context,
    identifier: Dict[str, Any],
    console: Console
) -> None:
    """Handle refund stage: invoke refund command.
    
    Always prompts for refund, even if order was already cancelled.
    """
    console.print()
    console.print("[cyan]━━━ Refund Stage ━━━[/cyan]\n")
    
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


def _handle_restock_stage(
    identifier: Dict[str, Any],
    shopify_service: Any,
    console: Console
) -> None:
    """Handle restock stage: prompt for single variant and process immediately.
    
    Always prompts for restock, regardless of cancel/refund outcome.
    Processes immediately when variant number is entered (no "done" prompt).
    """
    console.print()
    console.print("[cyan]━━━ Restock Stage ━━━[/cyan]\n")
    
    try:
        # Fetch order again to get line items
        orders_restock: List[Order] = shopify_service.get_order_by_identifier(identifier, line_items_first=5)
        if not orders_restock:
            console.print("[yellow]⚠️  Could not fetch order for restock.[/yellow]\n")
            return
        
        order_restock: Order = orders_restock[0]
        
        # Get line items
        line_items = extract_connection_nodes(getattr(order_restock, 'lineItems', None))
        if not line_items:
            console.print("[dim]No line items found to restock.[/dim]\n")
            return
        
        # Get variant ID from first line item
        variant_id = extract_variant_id_from_line_items(line_items) if line_items else None
        if not variant_id:
            console.print("[dim]No variants found to restock.[/dim]\n")
            return
        
        # Get all variants for the product
        try:
            variants = shopify_service.get_product_variants_for_restock(variant_id)
            if not variants:
                console.print("[yellow]No variants found for this product.[/yellow]\n")
                return
        except ValueError as e:
            console.print(f"[yellow]⚠️  Error fetching variants: {str(e)}[/yellow]\n")
            return
        
        # Display variants table
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
    
    except Exception as e:
        # Log error but don't fail the entire command
        console.print(f"[yellow]⚠️  Restock stage encountered an error: {str(e)}[/yellow]\n")





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
    json_output, should_display = get_display_context(ctx)
    
    # Get service from context (lazily initialized via LazyServiceProxy)
    shopify_service = ctx.meta["shopify_service"]
    
    # Validate identifier
    if not identifier:
        click.echo("❌ Order identifier is required", err=True)
        raise click.ClickException("Order identifier is required")
    
    try:
        # Stage 1: Cancel
        order_data, order_id, order_name, customer_name = _handle_cancellation_stage(
            identifier, ctx, reason, confirm, console
        )
        
        # Stage 2: Refund
        _handle_refund_stage(ctx, identifier, console)
        
        # Stage 3: Restock
        shopify_service = ctx.meta["shopify_service"]
        _handle_restock_stage(identifier, shopify_service, console)
        
        return {
            "success": True,
            "order_name": order_name,
            "message": "Order cancellation workflow completed"
        }
        
    except (RuntimeError, ValueError) as e:
        handle_shopify_error_response(e, json_output, should_display)
        raise
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Cancellation cancelled by user.[/yellow]\n")
        sys.exit(0)
    except Exception as e:
        if json_output:
            from bars_cli._core.utils.json_output import output_json_error
            output_json_error(str(e))
        else:
            console.print(f"[red]Unexpected error: {str(e)}[/red]")
            import traceback
            traceback.print_exc()
        raise click.ClickException(str(e))

