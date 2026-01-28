"""Apply discount to Shopify order command."""

import sys
import traceback
from typing import Dict, Any, Optional, List, Tuple, TYPE_CHECKING, cast

import click
from rich.console import Console

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_ORDER_IDENTIFIER
from bars_cli._core.ui.display import create_text_panel, create_info_table
from bars_cli._core.prompts import prompt_select_from_options
from bars_cli.commands.shopify._shared.shopify_formatters import (
    _format_customer_name_from_order,
    _get_product_title_from_order,
    format_order_info_for_discount,
)

if TYPE_CHECKING:
    from bars_cli.backend_services.shopify.models.sgqlc_models import Order, Customer, LineItem
else:
    Order = Any
    Customer = Any
    LineItem = Any






def prompt_discount_type() -> str:
    """Prompt user for discount type: 'fixed' or 'percentage'."""
    options_data = [
        {"value": "fixed", "display": "Fixed amount (e.g., $5.00)"},
        {"value": "percentage", "display": "Percentage (e.g., 5% for 5% off)"}
    ]
    
    # Extract display strings for the prompt
    display_options = [opt["display"] for opt in options_data]
    
    selected_display = prompt_select_from_options(
        "Select discount type",
        display_options
    )

    if selected_display is None:
        raise click.Abort()
    
    # Map back to value
    for opt in options_data:
        if opt["display"] == selected_display:
            return opt["value"]
    
    # Fallback (should not reach here)
    return options_data[0]["value"]


def prompt_fixed_amount() -> float:
    """Prompt user for fixed discount amount."""
    while True:
        try:
            response = click.prompt("Enter fixed discount amount (e.g., 5.00 for $5.00)", type=float)
            if response < 0:
                click.echo("Amount cannot be negative. Please enter a positive number.", err=True)
                continue
            return response
        except click.Abort:
            raise
        except Exception:
            click.echo("Invalid input. Please enter a valid number (e.g., 5.00).", err=True)


def prompt_percentage() -> float:
    """Prompt user for percentage discount (whole number, e.g., 5 = 5%, 100 = 100%)."""
    while True:
        try:
            response = click.prompt("Enter percentage discount (whole number, e.g., 5 for 5%, 100 for 100%)", type=float)
            if response < 0 or response > 100:
                click.echo("Percentage must be between 0 and 100. Please enter a valid percentage.", err=True)
                continue
            return response
        except click.Abort:
            raise
        except Exception:
            click.echo("Invalid input. Please enter a valid whole number (e.g., 5 for 5%).", err=True)


@click.command('apply-discount')
@handle_display_options(display=True, exit_on_error=True)
@click.option('--type', 'discount_type', type=click.Choice(['fixed', 'percentage'], case_sensitive=False), help='Discount type: fixed or percentage')
@click.option('--value', 'discount_value', type=float, help='Discount value (amount for fixed, percentage for percentage)')
@click.option('--code-desc', 'code_desc', type=str, help='Description for the discount code')
@click.option('--currency', 'currency_code', type=str, default='USD', help='Currency code (default: USD)')
@click.option('--no-prompt', is_flag=True, default=False, help='Skip prompts and use provided values')
@click.argument('identifier', type=SHOPIFY_ORDER_IDENTIFIER, required=False)
@click.pass_context
def apply_discount_cmd(
    ctx: click.Context,
    identifier: Optional[Dict[str, Any]],
    discount_type: Optional[str] = None,
    discount_value: Optional[float] = None,
    code_desc: Optional[str] = None,
    currency_code: str = 'USD',
    no_prompt: bool = False
) -> None:
    """
    Apply a discount to a Shopify order using Order Editing API.

    IDENTIFIER: Order number (1234 or #1234) or Order ID (gid://shopify/Order/123 or 123).

    Examples:
      bars shopify order apply-discount 1234
      bars shopify order apply-discount #1234 --type fixed --value 5.00
      bars shopify order apply-discount gid://shopify/Order/123456789 --type percentage --value 10
    """
    console = Console()
    # Get service from context (lazily initialized via LazyServiceProxy)
    shopify_service = ctx.meta["shopify_service"]

    if not identifier:
        raise click.ClickException("Order identifier is required.")

    try:
        # Fetch order to display info
        order_num = identifier.get('with_hash') or identifier.get('digits_only')
        order_id = identifier.get('gid')
        
        if not order_id:
            raise click.ClickException("Could not determine order GID from identifier.")
        
        console.print(f"\n[cyan]Looking up order {order_num or order_id} in {shopify_service.environment}...[/cyan]\n")
        
        # Handle special GID extraction case for apply_discount
        if order_id:
            identifier_for_fetch = {"query": f"id:{order_id}", "first": 1, "identifier": order_num or order_id}
        else:
            identifier_for_fetch = identifier
        
        orders = shopify_service.get_order_by_identifier(identifier_for_fetch, line_items_first=5)
        if not orders:
            raise click.ClickException(f"No order found with identifier: {identifier_for_fetch.get('identifier', 'N/A')}")
        order = orders[0]
        
        # Display order info using formatter
        order_info = format_order_info_for_discount(order, order_id)
        console.print(create_text_panel(order_info['header_parts'], title="Order to Apply Discount", border_style="cyan"))
        console.print(create_info_table(order_info['info_rows']))
        console.print()

        # Prompt for discount type if not provided
        if not discount_type:
            if no_prompt:
                raise click.ClickException("--type is required when --no-prompt is used")
            discount_type = prompt_discount_type()
        
        # Prompt for discount value if not provided
        if discount_value is None:
            if no_prompt:
                raise click.ClickException("--value is required when --no-prompt is used")
            if discount_type == "fixed":
                discount_value = prompt_fixed_amount()
            else:
                discount_value = prompt_percentage()

        # Confirm before applying
        if not no_prompt:
            discount_display = f"${discount_value:.2f}" if discount_type == "fixed" else f"{discount_value}%"
            confirm_input = click.prompt(
                click.style(f"Apply {discount_display} discount to this order? (yes/no)", fg="yellow"),
                type=str,
                default='no'
            ).strip().lower()
            if confirm_input not in ['yes', 'y']:
                console.print("\n[red]Discount application cancelled.[/red]\n")
                return

        console.print(f"\n[cyan]Applying {discount_type} discount of {discount_value}...[/cyan]\n")
        
        # Apply discount
        result = shopify_service.apply_discount(
            order_id=order_id,
            discount_type=discount_type,
            discount_value=discount_value,
            code_desc=code_desc,
            currency_code=currency_code
        )

        if not result.get("success"):
            errors = result.get("errors", ["Unknown error"])
            error_message = "\n".join(errors) if isinstance(errors, list) else str(errors)
            raise click.ClickException(f"[red]❌ Failed to apply discount:\n{error_message}[/red]")

        # Success
        data = result.get("data", {})
        discount_amount = data.get('discount_amount', discount_value if discount_type == "fixed" else 0.0)
        
        console.print(create_text_panel(
            [("✓ Discount Applied Successfully", "bold green")],
            title="Success",
            border_style="green"
        ))
        
        # Cast field access - at runtime, sgqlc returns actual values (str, list), not Field objects
        order_name: str = cast(str, order.name)
        
        success_rows = [
            ("Order", order_name),
            ("Discount Type", discount_type.capitalize()),
            ("Discount Value", f"${discount_amount:.2f}" if discount_type == "fixed" else f"{discount_value}%"),
            ("Discount Amount", f"${discount_amount:.2f}"),
            ("Code Description", code_desc or f"code: {discount_type}-discount"),
        ]
        console.print(create_info_table(success_rows))
        console.print("\n[dim]Note: Customer was NOT notified. Order has been updated.[/dim]\n")

    except ValueError as e:
        raise click.ClickException(f"[red]Error: {e}[/red]")
    except RuntimeError as e:
        raise click.ClickException(f"[red]API Error: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        traceback.print_exc()
        raise click.ClickException(str(e))

