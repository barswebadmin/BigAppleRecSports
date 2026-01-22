"""Update Shopify customer identifier (email or phone) command."""

import sys
import traceback
from typing import Dict, Any, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_CUSTOMER_IDENTIFIER
from bars_cli._core.ui.display import create_text_panel, create_info_table


@click.command('update')
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

    customer_id = identifier.get('gid')
    identifier_str = identifier.get('with_hash') or identifier.get('digits_only') or identifier.get('email') or identifier.get('identifier', 'N/A')

    if not customer_id:
        # Need to fetch customer first to get the ID
        console.print(f"\n[cyan]Looking up customer {identifier_str} in {shopify_service.environment}...[/cyan]\n")
        
        try:
            customers = shopify_service.get_customer_by_identifier(
                identifier,
                orders_first=1
            )
            if not customers:
                raise click.ClickException(f"[yellow]No customer found with identifier: {identifier_str}[/yellow]")
            customer = customers[0]
            customer_id = getattr(customer, 'id', None)
            
            if not customer_id:
                raise click.ClickException("Could not determine customer ID from fetched customer")
        except ValueError as e:
            raise click.ClickException(f"[red]Error: {e}[/red]")
    else:
        # Display customer info before updating
        console.print(f"\n[cyan]Looking up customer {identifier_str} in {shopify_service.environment}...[/cyan]\n")
        
        try:
            customers = shopify_service.get_customer_by_identifier(
                {"query": f"id:{customer_id.split('/')[-1]}", "first": 1, "identifier": identifier_str},
                orders_first=1
            )
            if not customers:
                raise click.ClickException(f"[yellow]No customer found with identifier: {identifier_str}[/yellow]")
            customer = customers[0]
        except ValueError as e:
            raise click.ClickException(f"[red]Error: {e}[/red]")

    # Display current customer info
    customer_name = ""
    if hasattr(customer, 'displayName') and getattr(customer, 'displayName', None):
        customer_name = getattr(customer, 'displayName')
    else:
        first = getattr(customer, 'firstName', '')
        last = getattr(customer, 'lastName', '')
        customer_name = f"{first} {last}".strip() or "N/A"

    header_parts = [
        (f"Customer: {customer_name}", "bold cyan")
    ]
    console.print(create_text_panel(header_parts, title="Update Customer Identifier", border_style="cyan"))
    
    info_rows = [
        ("Customer ID", customer_id.split('/')[-1]),
        ("Current Email", getattr(customer, 'email', 'N/A')),
        ("Current Phone", getattr(customer, 'phone', 'N/A')),
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

