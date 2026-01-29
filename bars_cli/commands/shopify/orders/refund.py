"""Refund Shopify order command."""

import json
import sys
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List, TYPE_CHECKING, cast

import click_extra as click
from rich.console import Console

from bars_cli._core.context import get_display_context
from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_ORDER_IDENTIFIER
from bars_cli._core.utils.json_output import output_json_error
from bars_cli.commands.shopify._shared.shopify_formatters import (
    _format_customer_name_from_order,
    _get_refunds,
    format_datetime_display,
    format_payment_summary,
    format_existing_refunds_table,
    format_refund_options_table,
    format_refund_summary,
    format_refund_header,
    format_refund_success,
    format_season_info,
)

if TYPE_CHECKING:
    from bars_cli.backend_services.shopify.models.sgqlc_models import Order, Refund, Transaction, LineItem, Product
else:
    Order = Any
    Refund = Any
    Transaction = Any
    LineItem = Any
    Product = Any


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








def prompt_refund_type_selection(
    order: Order,
    total_amount: float,
    shopify_service: Any,
    currency: str,
    console: Console,
    submitted_at: Optional[datetime] = None
) -> Tuple[Optional[str], Optional[float], Optional[str], Optional[datetime]]:
    """Calculate refund amounts for both types and prompt user to select.
    
    Args:
        order: Order object
        total_amount: Total amount paid
        shopify_service: ShopifyService instance
        currency: Currency code
        console: Console for output
        submitted_at: Optional pre-provided timestamp (from CLI option)
    
    Returns:
        Tuple of (refund_type, estimated_amount, estimated_message, submitted_at)
    """
    season_start_date_str, off_dates_str = shopify_service.extract_season_info_from_order(order)
    
    if not season_start_date_str:
        return None, None, None, None
    
    # Display season info using formatter
    season_info_lines = format_season_info(season_start_date_str, off_dates_str)
    for line in season_info_lines:
        console.print(line)
    
    submitted_at = _prompt_submitted_at_timestamp(console, submitted_at)
    if submitted_at is None:
        return None, None, None, None
    
    # Calculate for both refund types using service
    refund_amount, refund_message = shopify_service.calculate_estimated_refund(
        order=order,
        total_amount=total_amount,
        refund_type="refund",
        submitted_at=submitted_at
    )
    
    credit_amount, credit_message = shopify_service.calculate_estimated_refund(
        order=order,
        total_amount=total_amount,
        refund_type="credit",
        submitted_at=submitted_at
    )
    
    # Display both options using formatter
    format_refund_options_table(refund_amount, refund_message, credit_amount, credit_message, currency, console)
    
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




def _validate_refundable_amount(
    payment_summary: Dict[str, Any],
    console: Console
) -> Optional[Dict[str, Any]]:
    """Validate that order has refundable amount.
    
    Returns:
        Payment summary dict if refundable, None otherwise
    """
    total_amount = payment_summary['total_amount']
    remaining_refundable = payment_summary['remaining_refundable']
    
    if remaining_refundable <= 0:
        if total_amount == 0:
            console.print("[red]❌ No payment found. Order total is $0.00 - nothing to refund.[/red]\n")
        else:
            console.print("[red]❌ No refundable amount remaining. Order is fully refunded.[/red]\n")
        return None
    
    return payment_summary


def _display_season_info(
    season_start_date_str: Optional[str],
    off_dates_str: Optional[str],
    console: Console
) -> None:
    """Display season information for refund calculation."""
    console.print("[cyan]Refund Calculation[/cyan]")
    console.print(f"Season start date found: {season_start_date_str}")
    if off_dates_str:
        console.print(f"Off dates: {off_dates_str}")
    else:
        console.print("[yellow]⚠️  No off dates detected in product description[/yellow]")
    console.print()


def _prompt_submitted_at_timestamp(
    console: Console,
    submitted_at: Optional[datetime] = None
) -> Optional[datetime]:
    """Prompt for submitted_at timestamp if not provided.
    
    Returns:
        datetime object or None if user cancels
    """
    if submitted_at is not None:
        return submitted_at
    
    while True:
        timestamp_input = input(
            "Enter submitted_at timestamp (format: MM/DD/YYYY HH:MM:SS, or press ENTER to use current time): "
        ).strip()
        
        submitted_at = parse_submitted_at_timestamp(timestamp_input, console)
        if submitted_at is None:
            continue
        break
    
    return submitted_at


def _prompt_refund_type_simple(console: Console) -> str:
    """Prompt user to select refund type (refund or credit).
    
    Returns:
        "refund" or "credit"
    """
    while True:
        selection = input("Select refund type: (o) Original Payment, (s) Store Credit: ").strip().lower()
        if selection in ['o', 'original', 'original payment']:
            return "refund"
        elif selection in ['s', 'store', 'store credit', 'credit']:
            return "credit"
        else:
            console.print("[red]Invalid selection. Please enter 'o' for Original Payment or 's' for Store Credit.[/red]")


def _handle_refund_with_type_provided(
    order: Order,
    refund_type: str,
    total_amount: float,
    shopify_service: Any,
    console: Console,
    submitted_at_datetime: Optional[datetime] = None
) -> Tuple[Optional[float], Optional[str], Optional[datetime]]:
    """Handle refund calculation when refund type is provided via CLI option.
    
    Returns:
        Tuple of (estimated_amount, estimated_message, submitted_at_datetime)
    """
    season_start_date_str, off_dates_str = shopify_service.extract_season_info_from_order(order)
    
    if not season_start_date_str:
        console.print("[yellow]⚠️  Warning: Could not calculate suggested refund amounts.[/yellow]")
        console.print("[dim]No season dates found in product description.[/dim]\n")
        return None, None, submitted_at_datetime
    
    # Display season info using formatter
    season_info_lines = format_season_info(season_start_date_str, off_dates_str)
    for line in season_info_lines:
        console.print(line)
    
    submitted_at_datetime = _prompt_submitted_at_timestamp(console, submitted_at_datetime)
    if submitted_at_datetime is None:
        return None, None, None
    
    estimated_refund_amount, estimated_refund_message = shopify_service.calculate_estimated_refund(
        order=order,
        total_amount=total_amount,
        refund_type=refund_type,
        submitted_at=submitted_at_datetime
    )
    
    return estimated_refund_amount, estimated_refund_message, submitted_at_datetime


def _handle_refund_error(
    refund_result: Dict[str, Any],
    json_output: bool,
    console: Console
) -> None:
    """Handle refund creation error and display appropriate message."""
    error_msg = refund_result.get("message", refund_result.get("error", "Unknown error"))
    
    if json_output:
        output_json_error(error_msg if isinstance(error_msg, str) else "; ".join(error_msg))
    else:
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


def _handle_refund_success(
    refund_result: Dict[str, Any],
    order_name: str,
    refund_amount: float,
    refund_type_display: str,
    currency: str,
    json_output: bool,
    console: Console
) -> Dict[str, Any]:
    """Handle successful refund creation and return result."""
    if json_output:
        raw_response = refund_result.get("raw_response")
        if raw_response:
            click.echo(json.dumps(raw_response, indent=2, default=str))
            return raw_response
        else:
            refund_data = refund_result.get("data", {})
            click.echo(json.dumps(refund_data, indent=2, default=str))
            return refund_data
    else:
        refund_data = refund_result.get("data", {})
        refund_id = refund_data.get('id', 'N/A')
        if isinstance(refund_id, str) and '/' in refund_id:
            refund_id = refund_id.split('/')[-1]
        refund_created = format_datetime_display(refund_data.get('createdAt'))
        
        format_refund_success(
            order_name=order_name,
            refund_id=refund_id,
            refund_amount=refund_amount,
            refund_type_display=refund_type_display,
            refund_created=refund_created,
            currency=currency,
            console=console
        )
        
        return {
            "success": True,
            "order_name": order_name,
            "refund_id": refund_id,
            "refund_amount": refund_amount,
            "refund_type": refund_type_display,
            "refund_created": refund_created,
            "currency": currency
        }


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
    # Display full refund summary using formatter
    format_refund_summary(
        estimated_refund_amount,
        estimated_refund_message,
        refund_type_display,
        customer_email,
        remaining_refundable,
        currency,
        console
    )
    
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
@click.option('--submitted-at', type=str, help='Submission timestamp in format MM/DD/YYYY HH:MM:SS. If not provided, will prompt for it (or use current time if ENTER pressed).')
@click.argument('identifier', type=SHOPIFY_ORDER_IDENTIFIER, required=False)
@click.pass_context
def refund_order_cmd(
    ctx: click.Context,
    identifier: Optional[Dict[str, Any]],
    refund_type: Optional[str] = None,
    submitted_at: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Refund a Shopify order by order number or ID.
    
    Calculates refund amounts based on season dates and prompts for confirmation.
    
    IDENTIFIER: Order number (1234 or #1234) or Order ID (gid://shopify/Order/123 or 123).
    
    Examples:
      bars shopify order refund 1234
      bars shopify order refund #1234 --refund-type credit
      bars shopify order refund 1234 --refund-type refund
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
        # Fetch order
        order_num = identifier.get("identifier", "").strip().lstrip('#')
        console.print(f"\n[cyan]Fetching order details for #{order_num}...[/cyan]\n")
        
        orders = shopify_service.get_order_by_identifier(identifier, line_items_first=5)
        if not orders:
            raise click.ClickException(f"No order found with identifier: {identifier.get('identifier', 'N/A')}")
        order = orders[0]
        order_id: str = cast(str, order.id)
        order_name: str = cast(str, order.name)
        customer_name = _format_customer_name_from_order(order)
        customer_email: str = cast(str, order.email)
        
        format_refund_header(order_name, customer_name, customer_email, console)
        
        payment_summary = shopify_service.calculate_payment_summary(order)
        format_payment_summary(payment_summary, console)
        
        validated_summary = _validate_refundable_amount(payment_summary, console)
        if validated_summary is None:
            return
        
        total_amount = validated_summary['total_amount']
        currency = validated_summary['currency']
        remaining_refundable = validated_summary['remaining_refundable']
        
        # Show existing refunds using formatter
        refunds = _get_refunds(order)
        if refunds:
            format_existing_refunds_table(refunds, console)
        
        # Determine refund type and calculate amounts
        submitted_at_datetime: Optional[datetime] = None
        
        # Parse submitted_at if provided via CLI option
        if submitted_at:
            submitted_at_datetime = parse_submitted_at_timestamp(submitted_at, console)
            if submitted_at_datetime is None:
                raise click.ClickException("Invalid --submitted-at format. Use MM/DD/YYYY HH:MM:SS")
        
        if refund_type:
            estimated_refund_amount, estimated_refund_message, submitted_at_datetime = _handle_refund_with_type_provided(
                order, refund_type, total_amount, shopify_service, console, submitted_at_datetime
            )
        else:
            # Prompt for refund type selection with calculated amounts
            # If submitted_at was provided via CLI, pass it to the prompt function
            result = prompt_refund_type_selection(
                order, total_amount, shopify_service, currency, console, submitted_at=submitted_at_datetime
            )
            
            if result[0] is None:
                console.print("[yellow]⚠️  Warning: Could not calculate suggested refund amounts.[/yellow]")
                console.print("[dim]No season dates found in product description.[/dim]\n")
                refund_type = None
                estimated_refund_amount = None
                estimated_refund_message = None
                submitted_at_datetime = None
            else:
                refund_type, estimated_refund_amount, estimated_refund_message, submitted_at_datetime = result
        
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
            refund_type = _prompt_refund_type_simple(console)
        
        console.print()
        
        # Cast field access - at runtime, sgqlc returns actual values (str, list), not Field objects
        transactions = list(cast(list, order.transactions))
        
        console.print(f"[cyan]Processing refund of ${refund_amount:.2f}...[/cyan]\n")
        refund_result = shopify_service.create_refund(
            order_id=order_id,
            refund_amount=refund_amount,
            refund_type=refund_type,
            transactions=transactions,
            currency=currency,
            notify=True
        )
        
        if not refund_result.get("success"):
            _handle_refund_error(refund_result, json_output, console)
        
        return _handle_refund_success(
            refund_result, order_name, refund_amount, refund_type_display, currency, json_output, console
        )
        
    except (RuntimeError, ValueError) as e:
        error_msg = str(e)
        click.echo(f"❌ Error: {error_msg}", err=True)
        raise click.ClickException(error_msg)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Refund cancelled by user.[/yellow]\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        traceback.print_exc()
        raise click.ClickException(str(e))

