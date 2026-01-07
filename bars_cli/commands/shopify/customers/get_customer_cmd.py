"""Get Shopify customer details command."""
import json
import sys
from typing import Dict, Any, Optional, List

import click

from bars_cli._core.param_types import SHOPIFY_CUSTOMER_IDENTIFIER
from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli.models.shopify.sgqlc_query import Query
from bars_cli.clients.shopify_sgqlc_client import ShopifySGQLCClient
from bars_cli.models.shopify.customer import Customer as CustomerSGQLC



def get_customer_by_identifier(
    query_params: Dict[str, Any],
    environment: str = "production",
    orders_first: int = 5
) -> List[Any]:
    """
    Get a customer by identifier using Shopify SGQLC client.
    
    Handles the complete flow:
    1. Builds and executes the GraphQL query
    2. Checks for GraphQL errors (exits if found)
    3. Interprets results into native objects
    4. Extracts customers from result
    5. Returns list of customer objects or exits if none found
    
    Args:
        query_params: Dict from SHOPIFY_CUSTOMER_IDENTIFIER with keys:
            - query: GraphQL search query string
            - first: Number of results to fetch
            - not_found_message: Error message if not found
            - identifier: Original identifier string (optional, for reference)
        environment: Environment name ("production", "staging", or "development").
            Defaults to "production".
        orders_first: Number of orders to fetch per customer (default: 5)
    
    Returns:
        List of customer objects (sgqlc Type instances)
    
    Raises:
        RuntimeError: If the HTTP request fails (non-200 status or network errors)
        click.ClickException: If GraphQL errors are present, results can't be interpreted, or no customers found
    """
    query_str = query_params["query"]
    first = query_params.get("first", 1)
    
    # Build query operation (domain-specific logic in models)
    op = Query.build_customer_query(query_str, first=first, orders_first=orders_first)
    
    # Execute with generic client (handles environment/config loading internally)
    client = ShopifySGQLCClient(environment=environment)
    response = client.execute(op)
    
    # Check for GraphQL errors
    if response.get('errors'):
        error_msg = f"GraphQL errors: {json.dumps(response.get('errors'), indent=2)}"
        raise click.ClickException(error_msg)
    
    # Interpret results into native objects (op + data pattern)
    try:
        query_result = op + response
    except Exception as e:
        error_msg = f"Error interpreting results: {type(e).__name__}: {e}\n{json.dumps(response, indent=2, default=str)}"
        raise click.ClickException(error_msg)
    
    # Extract customers from result
    customers_connection = query_result.customers
    customers_nodes = customers_connection.nodes if customers_connection else []
    
    # Check for empty customers
    if not customers_nodes:
        not_found_msg = query_params.get('not_found_message', 'No customers found')
        raise click.ClickException(f"{not_found_msg}\n{json.dumps(response, indent=2, default=str)}")
    
    return customers_nodes



# TODO: Either refactor to use sgqlc/ShopifySGQLCClient or delete if not needed
# def get_all_customers_paginated(
#     config: Dict[str, Any],
#     query: Optional[str] = None,
#     page_size: int = 250
# ) -> List[Customer]:
#     """
#     Fetch all customers using cursor-based pagination.
#     
#     Useful for large result sets that need to be fetched in chunks.
#     
#     Args:
#         config: Shopify API configuration
#         query: Optional search query (e.g., "email:test@example.com")
#         page_size: Number of customers per page (default: 250, max recommended: 250)
#         
#     Returns:
#         List of all Customer objects
#         
#     Example:
#         ```python
#         # Get all customers
#         all_customers = get_all_customers_paginated(config)
#         
#         # Get all customers matching a query
#         all_test_customers = get_all_customers_paginated(
#             config, 
#             query="email:*@test.com"
#         )
#         ```
#     """
#     all_customers: List[Customer] = []
#     cursor: Optional[str] = None
#     page_num = 1
#     
#     base_query = """
#     query getCustomers($query: String, $after: String, $first: Int!) {
#         customers(first: $first, query: $query, after: $after) {
#             edges {
#                 cursor
#                 node {
#                     id
#                     firstName
#                     lastName
#                     email
#                     displayName
#                     phone
#                     tags
#                     numberOfOrders
#                     createdAt
#                     updatedAt
#                     state
#                     verifiedEmail
#                     addresses {
#                         address1
#                         address2
#                         city
#                         province
#                         zip
#                         country
#                     }
#                     defaultAddress {
#                         address1
#                         address2
#                         city
#                         province
#                         zip
#                         country
#                     }
#                 }
#             }
#             pageInfo {
#                 hasNextPage
#                 hasPreviousPage
#                 startCursor
#                 endCursor
#             }
#         }
#     }
#     """
#     
#     while True:
#         payload = {
#             "query": base_query,
#             "variables": {
#                 "query": query,
#                 "after": cursor,
#                 "first": page_size
#             }
#         }
#         
#         try:
#             response = make_graphql_request(payload, config)
#             
#             if "error" in response or "errors" in response:
#                 error_msg = response.get("error") or response.get("errors", [])
#                 raise Exception(f"GraphQL error on page {page_num}: {error_msg}")
#             
#             customers_data = response.get("data", {}).get("customers", {})
#             
#             # Use Customers list model - automatically handles Connection structure resolution
#             if customers_data:
#                 if Customers is None:
#                     raise Exception("Customers list model not available")
#                 page_customers = Customers(customers_data)
#                 all_customers.extend(page_customers)
#             
#             page_info_data = customers_data.get("pageInfo", {}) if isinstance(customers_data, dict) else {}
#             
#             has_next = page_info_data.get("hasNextPage", False)
#             cursor = page_info_data.get("endCursor")
#             
#             if not has_next or not cursor:
#                 break
#             
#             page_num += 1
#             
#         except Exception as e:
#             raise Exception(f"Error fetching page {page_num}: {str(e)}")
#     
#     return all_customers


# ============================================================================
# Display Functions (Now Type-Safe)
# ============================================================================

def format_customer(customer: CustomerSGQLC) -> str:
    """Format customer data for display."""
    output = []
    output.append("\n✅ Customer Found!")
    output.append("=" * 60)
    output.append(f"ID:            {customer.id}")  # type: ignore[attr-defined]
    name_parts = [customer.firstName, customer.lastName]  # type: ignore[attr-defined]
    full_name = " ".join(str(p) for p in name_parts if p) or customer.displayName or "N/A"  # type: ignore[attr-defined]
    output.append(f"Name:          {full_name}")
    output.append(f"Display Name:  {customer.displayName or 'N/A'}")  # type: ignore[attr-defined]
    output.append(f"Email:         {customer.email or 'N/A'}")  # type: ignore[attr-defined]
    output.append(f"Phone:         {customer.phone or 'N/A'}")  # type: ignore[attr-defined]
    output.append(f"State:         {customer.state or 'N/A'}")  # type: ignore[attr-defined]
    output.append(f"Verified:      {customer.verifiedEmail}")  # type: ignore[attr-defined]
    output.append(f"Orders Count:  {customer.numberOfOrders or 'N/A'}")  # type: ignore[attr-defined]
    output.append(f"Created:       {customer.createdAt or 'N/A'}")  # type: ignore[attr-defined]
    output.append(f"Updated:       {customer.updatedAt or 'N/A'}")  # type: ignore[attr-defined]
    
    if customer.tags:  # type: ignore[attr-defined]
        tags_list = list(customer.tags)  # type: ignore[attr-defined]
        output.append(f"\nTags ({len(tags_list)}):")
        for tag in tags_list:
            output.append(f"  • {tag}")
    
    if customer.defaultAddress:  # type: ignore[attr-defined]
        addr = customer.defaultAddress  # type: ignore[attr-defined]
        output.append("\nDefault Address:")
        if addr.address1:  # type: ignore[attr-defined]
            output.append(f"  {addr.address1}")  # type: ignore[attr-defined]
        if addr.address2:  # type: ignore[attr-defined]
            output.append(f"  {addr.address2}")  # type: ignore[attr-defined]
        city_parts = [str(p) for p in [addr.city, addr.province, addr.zip] if p]  # type: ignore[attr-defined]
        if city_parts:
            output.append(f"  {', '.join(city_parts)}")
        if addr.country:  # type: ignore[attr-defined]
            output.append(f"  {addr.country}")  # type: ignore[attr-defined]
    
    # Access orders from sgqlc Connection structure
    orders_connection = customer.orders  # type: ignore[attr-defined]
    recent_orders = orders_connection.nodes if orders_connection and hasattr(orders_connection, 'nodes') else []  # type: ignore[attr-defined]
    if recent_orders:
        output.append(f"\nRecent Orders ({len(recent_orders)}):")
        for order in recent_orders:
            output.append(f"  • {order.name or 'N/A'} (created: {order.createdAt or 'N/A'})")  # type: ignore[attr-defined]
            output.append(f"    ID: {order.id}")  # type: ignore[attr-defined]
    
    output.append("=" * 60)
    return '\n'.join(output)


def handle_multiple_results(customers: List[CustomerSGQLC], json_output: bool, should_display: bool) -> Optional[CustomerSGQLC]:
    """Handle selection when multiple customers are found.
    
    Returns:
        Selected customer object, or None if cancelled
    """
    if json_output:
        customers_data = [c.__json_data__ for c in customers]  # type: ignore[attr-defined]
        if should_display:
            click.echo(json.dumps(customers_data, indent=2, default=str))
        return None
    
    if should_display:
        click.echo(f"\n✅ Found {len(customers)} customers:")
        click.echo("=" * 60)
        for idx, customer in enumerate(customers, 1):
            name_parts = [customer.firstName, customer.lastName]  # type: ignore[attr-defined]
            full_name = " ".join(str(p) for p in name_parts if p) or customer.displayName or "N/A"  # type: ignore[attr-defined]
            email = customer.email or 'N/A'  # type: ignore[attr-defined]
            click.echo(f"{idx}. {full_name} ({email})")
        click.echo("=" * 60)
    
    try:
        selection = click.prompt("\nEnter number to view details (or press Enter to cancel)", default="", show_default=False)
        if not selection:
            if should_display:
                click.echo("Cancelled")
            return None
        
        selected_idx = int(selection) - 1
        if selected_idx < 0 or selected_idx >= len(customers):
            if should_display:
                click.echo(f"❌ Invalid selection. Please enter a number between 1 and {len(customers)}", err=True)
            raise ValueError(f"Invalid selection: {selection}")
        
        return customers[selected_idx]
        
    except (ValueError, KeyboardInterrupt, EOFError) as e:
        if should_display:
            click.echo("\n❌ Invalid input or cancelled", err=True)
        raise click.ClickException(str(e))


@click.command('get')
@handle_display_options(display=True, exit_on_error=True)
@click.argument('identifier', type=SHOPIFY_CUSTOMER_IDENTIFIER, required=False)
@click.pass_context
def get_customer_cmd(ctx: click.Context, identifier: Optional[Dict[str, Any]]) -> Optional[List[CustomerSGQLC]]:
    """
    Get Shopify customer details by email, ID, or name.
    
    IDENTIFIER: Customer email, ID (gid://shopify/Customer/123 or 123), or name.
    Name formats: "First Last", "f:First", "l:Last" (with or without # prefix).
    
    Examples:
      bars shopify customer get customer@example.com
      bars shopify customer get gid://shopify/Customer/123456789
      bars shopify customer get 123456789
      bars shopify customer get "John Doe"
      bars shopify customer get f:John
      bars --json shopify customer get customer@example.com
    """
    json_output = ctx.obj.get('json_output', False) if ctx.obj else False
    display_override = ctx.obj.get('display_override', True) if ctx.obj else True
    should_display = display_override if display_override is not None else True
    environment = ctx.obj.get('environment', 'production') if ctx.obj else 'production'
    
    if not identifier:
        error_msg = "Customer identifier is required"
        if should_display:
            if json_output:
                click.echo(json.dumps({"error": error_msg}, indent=2))
            else:
                click.echo(f"❌ {error_msg}", err=True)
        raise click.ClickException(error_msg)
    
    try:
        if should_display and not json_output:
            lookup_value = identifier.get("identifier", "customer")
            click.echo(f"🔍 Looking up: {lookup_value}", err=True)
        
        # Get customers using helper function
        try:
            customers = get_customer_by_identifier(
                identifier,
                environment=environment,
                orders_first=5
            )
        except RuntimeError as e:
            error_msg = f"HTTP Error: {str(e)}"
            if should_display:
                if json_output:
                    click.echo(json.dumps({"error": error_msg}, indent=2))
                else:
                    click.echo(f"❌ {error_msg}", err=True)
            raise click.ClickException(error_msg)
        
        if not customers:
            error_msg = identifier.get('not_found_message', 'No customers found')
            if should_display:
                if json_output:
                    click.echo(json.dumps({"error": error_msg}, indent=2))
                else:
                    click.echo(f"❌ {error_msg}", err=True)
            raise click.ClickException(error_msg)
        
        # Handle single vs multiple results
        if len(customers) == 1:
            customer = customers[0]
            if should_display:
                if json_output:
                    click.echo(json.dumps(customer.__json_data__, indent=2, default=str))  # type: ignore[attr-defined]
                else:
                    click.echo(format_customer(customer))
            return customers
        else:
            # Multiple customers - use handler
            selected_customer = handle_multiple_results(customers, json_output, should_display)
            if selected_customer:
                if should_display and not json_output:
                    click.echo(format_customer(selected_customer))
                elif should_display and json_output:
                    click.echo(json.dumps(selected_customer.__json_data__, indent=2, default=str))  # type: ignore[attr-defined]
                return [selected_customer]
            return customers
        
    except click.ClickException:
        # Re-raise Click exceptions - decorator will handle exit
        raise
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        if should_display:
            if json_output:
                click.echo(json.dumps({"error": error_msg, "type": error_type}, indent=2))
            else:
                click.echo(f"❌ Unexpected error ({error_type}): {error_msg}", err=True)
                import traceback
                click.echo(traceback.format_exc(), err=True)
        raise click.ClickException(error_msg)

