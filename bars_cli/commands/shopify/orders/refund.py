"""Refund Shopify order command."""

import sys
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_ORDER_IDENTIFIER
from bars_cli._core.ui.display import format_datetime, create_info_table


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
    """Format datetime string for display."""
    return format_datetime(dt_str)


def parse_submitted_at_timestamp(timestamp_input: str, console: Console) -> Optional[datetime]:
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


def calculate_payment_summary(order: Any) -> Dict[str, Any]:
    """Calculate payment summary from order."""
    total_price_set = getattr(order, 'totalPriceSet', None)  # type: ignore[attr-defined]
    if total_price_set:
        shop_money = getattr(total_price_set, 'shopMoney', None)  # type: ignore[attr-defined]
        if shop_money:
            amount_str = getattr(shop_money, 'amount', '0')  # type: ignore[attr-defined]
            currency = getattr(shop_money, 'currencyCode', 'USD')  # type: ignore[attr-defined]
            try:
                total_amount = float(amount_str)
            except (ValueError, TypeError):
                total_amount = 0.0
        else:
            total_amount = 0.0
            currency = 'USD'
    else:
        total_amount = 0.0
        currency = 'USD'
    
    refunds = _get_refunds(order)
    total_refunded = 0.0
    pending_refunds = 0.0
    completed_refunds = 0.0
    
    for refund in refunds:
        refund_data = refund.__json_data__ if hasattr(refund, '__json_data__') else {}
        total_refunded_set = refund_data.get('totalRefundedSet', {})
        shop_money = total_refunded_set.get('shopMoney', {})
        refund_total = float(shop_money.get('amount', 0))
        
        if refund_total == 0:
            # Check transactions for pending refunds
            refund_transactions_conn = getattr(refund, 'transactions', None)  # type: ignore[attr-defined]
            if refund_transactions_conn:
                nodes = getattr(refund_transactions_conn, 'nodes', None)  # type: ignore[attr-defined]
                if nodes:
                    for trans in nodes:
                        trans_data = trans.__json_data__ if hasattr(trans, '__json_data__') else {}
                        if trans_data.get('kind') == 'REFUND':
                            trans_amount = float(trans_data.get('amount', 0))
                            if trans_data.get('status') == 'PENDING':
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


def _get_refunds(order: Any) -> list:
    """Extract refunds from order."""
    refunds = getattr(order, 'refunds', None)  # type: ignore[attr-defined]
    if refunds:
        return list(refunds)
    return []


def calculate_estimated_refund(
    order: Any,
    total_amount: float,
    refund_type: str,
    console: Console,
    submitted_at: Optional[datetime] = None
) -> Tuple[Optional[float], Optional[str]]:
    """Calculate estimated refund amount based on season dates."""
    from backend.shared.date_utils import extract_season_dates, calculate_refund_amount
    
    line_items_conn = getattr(order, 'lineItems', None)  # type: ignore[attr-defined]
    if not line_items_conn:
        return None, None
    
    nodes = getattr(line_items_conn, 'nodes', None)  # type: ignore[attr-defined]
    if not nodes or len(nodes) == 0:
        return None, None
    
    first_item = nodes[0]
    product = getattr(first_item, 'product', None)  # type: ignore[attr-defined]
    if not product:
        return None, None
    
    product_data = product.__json_data__ if hasattr(product, '__json_data__') else {}
    product_description = product_data.get('descriptionHtml', '')
    
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
    order: Any,
    total_amount: float,
    remaining_refundable: float,
    currency: str,
    console: Console
) -> Tuple[Optional[str], Optional[float], Optional[str], Optional[datetime]]:
    """Calculate refund amounts for both types and prompt user to select."""
    from backend.shared.date_utils import extract_season_dates, calculate_refund_amount
    
    line_items_conn = getattr(order, 'lineItems', None)  # type: ignore[attr-defined]
    if not line_items_conn:
        return None, None, None, None
    
    nodes = getattr(line_items_conn, 'nodes', None)  # type: ignore[attr-defined]
    if not nodes or len(nodes) == 0:
        return None, None, None, None
    
    first_item = nodes[0]
    product = getattr(first_item, 'product', None)  # type: ignore[attr-defined]
    if not product:
        return None, None, None, None
    
    product_data = product.__json_data__ if hasattr(product, '__json_data__') else {}
    product_description = product_data.get('descriptionHtml', '')
    
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
    
    # Calculate for both refund types
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
    console: Console
) -> Optional[float]:
    """Prompt user for refund with full summary displayed."""
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
                "or enter a different amount: "
            )
        else:
            prompt_text = "Enter refund amount (without $), or press ENTER to exit: "
        
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


@click.command('refund')
@handle_display_options(display=True, exit_on_error=True)
@click.option('--refund-type', type=click.Choice(['refund', 'credit'], case_sensitive=False), help='Refund type: refund (original payment) or credit (store credit). If not specified, will prompt for selection.')
@click.argument('identifier', type=SHOPIFY_ORDER_IDENTIFIER, required=False)
@click.pass_context
def refund_order_cmd(
    ctx: click.Context,
    identifier: Optional[Dict[str, Any]],
    refund_type: Optional[str] = None
) -> None:
    """
    Refund a Shopify order by order number or ID.
    
    Calculates refund amounts based on season dates and prompts for confirmation.
    
    IDENTIFIER: Order number (1234 or #1234) or Order ID (gid://shopify/Order/123 or 123).
    
    Examples:
      bars shopify order refund 1234
      bars shopify order refund #1234 --refund-type credit
      bars shopify order refund 1234 --refund-type refund
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
        # Fetch order
        order_num = identifier.get("identifier", "").strip().lstrip('#')
        console.print(f"\n[cyan]Fetching order details for #{order_num}...[/cyan]\n")
        
        orders = shopify_service.get_order_by_identifier(identifier, line_items_first=50)
        if not orders:
            click.echo("❌ No order found", err=True)
            raise click.ClickException(f"No order found with identifier: {identifier.get('identifier', 'N/A')}")
        
        order = orders[0]
        order_id = getattr(order, 'id', '')  # type: ignore[attr-defined]
        order_name = getattr(order, 'name', 'N/A')  # type: ignore[attr-defined]
        
        # Get customer name
        customer_name = _format_customer_name(order)
        customer_email = customer_name if customer_name != "N/A" else getattr(order, 'email', 'N/A')  # type: ignore[attr-defined]
        
        # Display header
        console.print(Panel(
            "[bold cyan]Refund Order[/bold cyan]\n"
            f"Order: {order_name}\n"
            f"Customer: {customer_name or getattr(order, 'email', 'N/A')}",  # type: ignore[attr-defined]
            border_style="cyan"
        ))
        console.print()
        
        # Calculate payment summary
        payment_summary = calculate_payment_summary(order)
        total_amount = payment_summary['total_amount']
        currency = payment_summary['currency']
        total_refunded = payment_summary['total_refunded']
        pending_refunds = payment_summary['pending_refunds']
        completed_refunds = payment_summary['completed_refunds']
        remaining_refundable = payment_summary['remaining_refundable']
        
        # Display payment summary
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
        
        # Check if refund is possible
        if remaining_refundable <= 0:
            if total_amount == 0:
                console.print("[red]❌ No payment found. Order total is $0.00 - nothing to refund.[/red]\n")
            else:
                console.print("[red]❌ No refundable amount remaining. Order is fully refunded.[/red]\n")
            return
        
        # Show existing refunds
        refunds = _get_refunds(order)
        if refunds:
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
        
        # Determine refund type and calculate amounts
        if refund_type:
            # Use provided refund type
            estimated_refund_amount, estimated_refund_message = calculate_estimated_refund(
                order, total_amount, refund_type, console
            )
            
            if estimated_refund_amount is None:
                console.print("[red]⚠️  Warning: Could not calculate suggested refund amount.[/red]")
                console.print("[dim]No season dates found in product description.[/dim]\n")
        else:
            # Prompt for refund type selection with calculated amounts
            result = prompt_refund_type_selection(
                order, total_amount, remaining_refundable, currency, console
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
            return
        
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
        transactions = list(getattr(order, 'transactions', []))  # type: ignore[attr-defined]
        
        console.print(f"[cyan]Processing refund of ${refund_amount:.2f}...[/cyan]\n")
        refund_result = shopify_service.create_refund(
            order_id=order_id,
            refund_amount=refund_amount,
            refund_type=refund_type,
            transactions=transactions,
            notify=True
        )
        
        if not refund_result.get("success"):
            error_msg = refund_result.get("message", refund_result.get("error", "Unknown error"))
            console.print("[red]❌ Failed to create refund:[/red]")
            if isinstance(error_msg, list):
                for error in error_msg:
                    console.print(f"  • {error}")
            elif isinstance(error_msg, str):
                console.print(f"  {error_msg}")
            else:
                console.print(f"  {str(error_msg)}")
            console.print()
            raise click.ClickException(error_msg if isinstance(error_msg, str) else "; ".join(error_msg))
        
        # Success!
        refund_data = refund_result.get("data", {})
        refund_id = refund_data.get('id', 'N/A')
        if isinstance(refund_id, str) and '/' in refund_id:
            refund_id = refund_id.split('/')[-1]
        refund_created = format_datetime_display(refund_data.get('createdAt'))
        
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
        
    except (RuntimeError, ValueError) as e:
        error_msg = str(e)
        click.echo(f"❌ Error: {error_msg}", err=True)
        raise click.ClickException(error_msg)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Refund cancelled by user.[/yellow]\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        raise click.ClickException(str(e))

