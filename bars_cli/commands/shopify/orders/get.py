"""Get Shopify order command - HTTP client version."""

import json
from typing import Dict, Any, Optional

import click_extra as click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_ORDER_IDENTIFIER
from bars_cli._core.utils.json_output import output_json_item, output_json_error
from bars_cli._core.context import get_http_client


@click.command('get')
@handle_display_options(display=True, exit_on_error=True)
@click.argument('identifier', type=SHOPIFY_ORDER_IDENTIFIER, required=False)
@click.pass_context
def get_order_cmd(
    ctx: click.Context,
    identifier: Optional[Dict[str, Any]] = None
) -> Optional[dict]:
    """
    Get Shopify order details by order number or ID.
    
    IDENTIFIER: Order number (1234 or #1234) or Order ID (gid://shopify/Order/123 or 123).
    
    Examples:
      bars shopify order get 1234
      bars shopify order get #1234
      bars shopify order get gid://shopify/Order/123456789
      bars --json shopify order get 1234
    """
    json_output = ctx.obj.get('json_output', False)
    should_display = ctx.obj.get('should_display', True)

    # Prompt for identifier if not provided
    if not identifier:
        identifier_str = click.prompt('Order identifier (number or ID)')
        identifier = SHOPIFY_ORDER_IDENTIFIER.convert(identifier_str, None, ctx)

    # Get HTTP client from context (BARS API base URL)
    client = get_http_client(ctx)

    try:
        # Extract identifier string and type from dict
        identifier_value = identifier.get("identifier", "")
        identifier_type = identifier.get("type", "")
        
        # Display lookup message
        if should_display and not json_output:
            # Show user-friendly format with # for order numbers
            display_value = f"#{identifier_value}" if identifier_type == "order_number" else identifier_value
            click.echo(f"🔍 Looking up order: {display_value}", err=True)

        # Build API endpoint with appropriate query parameter based on type
        if identifier_type == "order_number":
            endpoint = f'http://localhost:8000/orders?number={identifier_value}'
        else:  # order_id
            endpoint = f'http://localhost:8000/orders?id={identifier_value}'

        # Make the API request
        response = client.get(endpoint)

        # Handle successful response
        if response.status_code == 200:
            response_data = response.json()

            # Extract order data from response
            if 'data' in response_data:
                order_data = response_data['data']
                
                if not order_data:
                    error_msg = f"No order found for identifier: {identifier_value}"
                    if json_output:
                        output_json_error(error_msg)
                    else:
                        click.echo(f"❌ {error_msg}", err=True)
                    raise click.ClickException(error_msg)

                # Display result
                if should_display:
                    if json_output:
                        output_json_item(order_data)
                    else:
                        _format_order(order_data)

                return order_data

            error_msg = "Invalid response format from API"
            if json_output:
                output_json_error(error_msg)
            else:
                click.echo(f"❌ {error_msg}", err=True)
            raise click.ClickException(error_msg)

        # Handle error response
        if response.status_code == 404:
            error_msg = f"Order not found: {identifier_value}"
            if json_output:
                output_json_error(error_msg, error_type="NotFound")
            else:
                click.echo(f"❌ {error_msg}", err=True)
            raise click.ClickException(error_msg)

        error_msg = _extract_error_message(response)
        if json_output:
            output_json_error(error_msg, error_type="APIError")
        else:
            click.echo(f"❌ {error_msg}", err=True)
            click.echo(f"Status Code: {response.status_code}", err=True)
        raise click.ClickException(error_msg)

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)

        if json_output:
            output_json_error(error_msg, error_type=error_type)
        else:
            click.echo(f"❌ Unexpected error ({error_type}): {error_msg}", err=True)

        raise click.ClickException(error_msg) from e


def _format_order(order: dict) -> None:
    """Format order data for display.
    
    Args:
        order: Order data dict from API with computed fields
    """
    output = []
    output.append("\n✅ Order Found!")
    output.append("=" * 60)
    
    # Display order number as hyperlink (if terminal supports it)
    if order.get('order_number_link'):
        output.append(f"{'Order':<20} {order['order_number_link']}")
    else:
        output.append(f"{'Order':<20} #{order.get('number', 'N/A')}")
    
    # Display product as hyperlink
    if order.get('product_link'):
        output.append(f"{'Product':<20} {order['product_link']}")
    elif order.get('product_title'):
        output.append(f"{'Product':<20} {order['product_title']}")
    
    # Display order email with fallback
    order_email = order.get('form_email')
    if order_email and order_email != 'N/A':
        output.append(f"{'Order Email':<20} {order_email}")
    else:
        output.append(f"{'Order Email':<20} Not collected in form")
    
    output.append(f"{'Amount Paid':<20} ${order.get('amount_paid', '0.00')}")
    
    if order.get('createdAt'):
        output.append(f"{'Created At':<20} {order['createdAt']}")
    
    # Cancellation status
    output.append(f"{'Cancellation Status':<20} {order.get('cancellation_status', 'N/A')}")
    
    # Refund status
    output.append(f"{'Refund Status':<20} {order.get('refund_status', 'N/A (Not Refunded)')}")
    
    # Customer info
    if order.get('customer'):
        customer = order['customer']
        output.append(f"\n{'Customer:':<20}")
        if customer.get('first_name') or customer.get('last_name'):
            name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
            output.append(f"  {'Name':<18} {name}")
        if customer.get('email'):
            output.append(f"  {'Email':<18} {customer['email']}")
    
    output.append("=" * 60)
    click.echo('\n'.join(output))


def _extract_error_message(response) -> str:
    """Extract error message from API response."""
    error_msg = f"API request failed with status {response.status_code}"
    try:
        error_response = response.json()
        if isinstance(error_response, dict):
            if 'message' in error_response:
                error_msg = f"API Error: {error_response['message']}"
            elif 'error' in error_response:
                error_msg = f"API Error: {error_response['error']}"
            elif 'detail' in error_response:
                if isinstance(error_response['detail'], str):
                    error_msg = f"API Error: {error_response['detail']}"
    except json.JSONDecodeError:
        pass
    return error_msg
