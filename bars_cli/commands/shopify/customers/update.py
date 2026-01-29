"""Update Shopify customer identifier (email or phone) command."""

import traceback
from typing import Dict, Any, Optional, Tuple, TYPE_CHECKING, cast

import click_extra as click
from rich.console import Console

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_CUSTOMER_IDENTIFIER
from bars_cli._core.ui.display import create_text_panel, create_info_table
from bars_cli.commands.shopify._shared.shopify_formatters import (
    _format_customer_name,
    format_customer_info_for_update,
)

if TYPE_CHECKING:
    from bars_cli.backend_services.shopify.models.sgqlc_models import Customer
else:
    Customer = Any




def _display_customer_info(
    customer: Customer,
    customer_id: str,
    email: Optional[str],
    phone: Optional[str],
    console: Console
) -> None:
    """Display customer information before updating."""
    # Cast field access - at runtime, sgqlc returns actual values (str), not Field objects
    customer_name = _format_customer_name(customer)
    current_email: str = cast(str, getattr(customer, 'email', 'N/A'))
    current_phone: str = cast(str, getattr(customer, 'phone', 'N/A'))
    
    header_parts = [
        (f"Customer: {customer_name}", "bold cyan")
    ]
    console.print(create_text_panel(header_parts, title="Update Customer Identifier", border_style="cyan"))
    
    info_rows = [
        ("Customer ID", customer_id.split('/')[-1]),
        ("Current Email", current_email),
        ("Current Phone", current_phone),
    ]
    console.print(create_info_table(info_rows))
    console.print()
    
    # Show what will be updated
    update_rows = []
    if email:
        update_rows.append(("New Email", email))
    if phone:
        update_rows.append(("New Phone", phone))
    
    if update_rows:
        console.print(create_info_table(update_rows, title="Updates to Apply", field_style="bold yellow"))
        console.print()


@click.command(name='update-customer', aliases=['update'])
@handle_display_options(display=True, exit_on_error=True)
@click.option('--email', type=str, help='New email address')
@click.option('--phone', type=str, help='New phone number')
@click.argument('identifier', type=SHOPIFY_CUSTOMER_IDENTIFIER, required=False)
@click.pass_context
def update_customer_cmd(
    ctx: click.Context,
    identifier: Optional[Dict[str, Any]],
    email: Optional[str] = None,
    phone: Optional[str] = None
) -> None:
    """
    Update a customer's identifier (email or phone) in Shopify.

    IDENTIFIER: Customer email, ID (gid://shopify/Customer/123 or 123), or name.

    Examples:
      bars shopify customer update customer@example.com --email new@example.com
      bars shopify customer update gid://shopify/Customer/123456789 --phone "+1234567890"
      bars shopify customer update 123456789 --email new@example.com --phone "+1234567890"
    """
    console = Console()
    # Get service from context (lazily initialized via LazyServiceProxy)
    shopify_service = ctx.meta["shopify_service"]

    if not identifier:
        raise click.ClickException("Customer identifier is required.")

    if not email and not phone:
        raise click.ClickException("Must provide at least one of --email or --phone")

    try:
        # Fetch customer
        identifier_str = identifier.get('with_hash') or identifier.get('digits_only') or identifier.get('email') or identifier.get('identifier', 'N/A')
        console.print(f"\n[cyan]Looking up customer {identifier_str} in {shopify_service.environment}...[/cyan]\n")
        
        customers = shopify_service.get_customer_by_identifier(identifier, orders_first=1)
        if not customers:
            raise click.ClickException(f"[yellow]No customer found with identifier: {identifier_str}[/yellow]")
        
        customer = customers[0]
        customer_id: str = cast(str, customer.id)
        
        # Display customer info using formatter
        customer_info = format_customer_info_for_update(customer, customer_id, email, phone)
        console.print(create_text_panel(customer_info['header_parts'], title="Update Customer Identifier", border_style="cyan"))
        console.print(create_info_table(customer_info['info_rows']))
        console.print()
        if customer_info['update_rows']:
            console.print(create_info_table(customer_info['update_rows'], title="Updates to Apply", field_style="bold yellow"))
        console.print()

        # Confirm before updating
        confirm_input = click.prompt(
            click.style("Confirm update? (yes/no)", fg="yellow"),
            type=str,
            default='no'
        ).strip().lower()
        if confirm_input not in ['yes', 'y']:
            console.print("\n[red]Update cancelled.[/red]\n")
            return

        console.print("\n[cyan]Updating customer identifier...[/cyan]\n")
        
        # Update customer
        result = shopify_service.update_identifier(
            customer_id=customer_id,
            email=email,
            phone=phone
        )

        if not result.get("success"):
            errors = result.get("errors", ["Unknown error"])
            error_message = "\n".join(errors) if isinstance(errors, list) else str(errors)
            raise click.ClickException(f"[red]❌ Failed to update customer:\n{error_message}[/red]")

        # Success
        data = result.get("data", {})
        
        console.print(create_text_panel(
            [("✓ Customer Updated Successfully", "bold green")],
            title="Success",
            border_style="green"
        ))
        
        success_rows = [
            ("Customer ID", data.get('id', 'N/A').split('/')[-1] if data.get('id') else 'N/A'),
        ]
        if data.get('email'):
            success_rows.append(("Email", data['email']))
        if data.get('phone'):
            success_rows.append(("Phone", data['phone']))
        if data.get('firstName') or data.get('lastName'):
            name = f"{data.get('firstName', '')} {data.get('lastName', '')}".strip()
            if name:
                success_rows.append(("Name", name))
        
        console.print(create_info_table(success_rows))
        console.print("\n[dim]Customer identifier has been updated.[/dim]\n")
        
    except ValueError as e:
        raise click.ClickException(f"[red]Error: {e}[/red]")
    except RuntimeError as e:
        raise click.ClickException(f"[red]API Error: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        traceback.print_exc()
        raise click.ClickException(str(e))

