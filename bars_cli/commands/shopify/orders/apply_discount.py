"""Apply discount to Shopify order command."""

import sys
import time
import traceback
from typing import Dict, Any, Optional, List, TYPE_CHECKING

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_ORDER_IDENTIFIER
from bars_cli._core.ui.display import create_text_panel, create_info_table
from bars_cli._core.prompts import prompt_select_from_options

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

    order_num = identifier.get('with_hash') or identifier.get('digits_only')
    order_id = identifier.get('gid')

    if not order_id:
        raise click.ClickException("Could not determine order GID from identifier.")

    console.print(f"\n[cyan]Looking up order {order_num or order_id} in {shopify_service.environment}...[/cyan]\n")

    try:
        # Fetch order to display info
        orders: List[Order] = shopify_service.get_order_by_identifier(
            {"query": f"id:{order_id}", "first": 1, "identifier": order_num or order_id},
            line_items_first=1
        )
        if not orders:
            raise click.ClickException(f"[yellow]No order found with identifier: {order_num or order_id}[/yellow]")
        order: Order = orders[0]

        customer_name = ""
        if hasattr(order, 'customer') and order.customer:
            customer = order.customer
            if hasattr(customer, 'displayName') and customer.displayName:
                customer_name = customer.displayName
            else:
                first = customer.firstName if hasattr(customer, 'firstName') else ''
                last = customer.lastName if hasattr(customer, 'lastName') else ''
                customer_name = f"{first} {last}".strip()

        product_title = "Unknown Product"
        line_items_conn = order.lineItems if hasattr(order, 'lineItems') else None
        if line_items_conn and hasattr(line_items_conn, 'nodes') and line_items_conn.nodes:
            first_line_item = line_items_conn.nodes[0]
            product = first_line_item.product if hasattr(first_line_item, 'product') else None
            if product and hasattr(product, 'title') and product.title:
                product_title = product.title

        # Display order info
        header_parts = [
            (f"Order #{order.name if hasattr(order, 'name') else 'N/A'}", "bold cyan")
        ]
        console.print(create_text_panel(header_parts, title="Order to Apply Discount", border_style="cyan"))
        
        info_rows = [
            ("Order ID", order_id.split('/')[-1] if '/' in order_id else order_id),
        ]
        if customer_name:
            info_rows.append(("Customer", customer_name))
        info_rows.append(("Email", order.email if hasattr(order, 'email') else 'N/A'))
        info_rows.append(("Financial Status", order.displayFinancialStatus if hasattr(order, 'displayFinancialStatus') else 'N/A'))
        info_rows.append(("📦 Product", product_title))
        console.print(create_info_table(info_rows))
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
        
        success_rows = [
            ("Order", order.name if hasattr(order, 'name') else 'N/A'),
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
        click.echo(f"[red]Unexpected error: {str(e)}[/red]", err=True)
        traceback.print_exc()
        raise click.ClickException(str(e))

