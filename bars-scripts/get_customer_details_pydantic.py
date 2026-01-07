#!/usr/bin/env python3
"""
Get Customer Details from Shopify - Type-Safe Version using Pydantic

This is a refactored version using sgqlc for query generation and Pydantic for validation.
Shows how to incorporate Pydantic models with GraphQL queries.

Usage:
    python get_customer_details_pydantic.py customer@example.com
    python get_customer_details_pydantic.py --id gid://shopify/Customer/123456789
"""

import sys
import json
import argparse
import logging
from typing import Dict, Any, Optional, List, Literal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from models.sgqlc_query import Query
from models.shopify_sgqlc_client import ShopifySGQLCClient
from models.sgqlc_models.customer import Customer as CustomerSGQLC



# ============================================================================
# Utility Functions
# ============================================================================

def parse_identifier() -> Dict[str, Any]:
    """
    Parse CLI arguments and return dict with query and metadata.
    
    Handles all CLI argument parsing, including interactive prompt if no identifier provided.
    
    Returns:
        Dict with keys:
        - identifier: The identifier string used (for error messages)
        - query: GraphQL search query string
        - not_found_message: Error message if not found
        - first: Number of results to fetch (default: 1 for single lookups, 10 for name)
        - json: Whether to output JSON (from --json flag)
    
    Raises:
        SystemExit: If user cancels interactive input or no identifier provided
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Get customer details from Shopify")
    parser.add_argument(
        "identifier",
        nargs="?",
        help='Customer email, ID, or name. Name formats: "First Last", "f:First", "l:Last"'
    )
    parser.add_argument("--email", help="Customer email address")
    parser.add_argument("--id", help="Customer ID (e.g., gid://shopify/Customer/123456789)")
    parser.add_argument("--json", action="store_true", default=False, help="Output raw JSON (default: True)")
    args = parser.parse_args()
    
    # Determine identifier from arguments
    if not args.identifier and not args.email and not args.id:
        try:
            args.identifier = input("Enter customer email, ID, or name: ").strip()
            if not args.identifier:
                print("Error: Customer email, ID, or name is required", file=sys.stderr)
                sys.exit(1)
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled", file=sys.stderr)
            sys.exit(1)
    
    # Determine identifier from arguments
    if args.email:
        identifier = args.email
    elif args.id:
        identifier = args.id
    else:
        identifier = args.identifier
    
    # Parse identifier string to GraphQL query
    if "@" in identifier:
        return {
            "identifier": identifier,
            "query": f"email:{identifier}",
            "not_found_message": f"No customer found with email: {identifier}",
            "first": 1,
            "json": args.json
        }
    
    if identifier.startswith("f:"):
        first_name = identifier[2:].strip()
        return {
            "identifier": identifier,
            "query": f"first_name:{first_name}",
            "not_found_message": f"No customers found with first name '{first_name}'",
            "first": 10,
            "json": args.json
        }
    
    if identifier.startswith("l:"):
        last_name = identifier[2:].strip()
        return {
            "identifier": identifier,
            "query": f"last_name:{last_name}",
            "not_found_message": f"No customers found with last name '{last_name}'",
            "first": 10,
            "json": args.json
        }
    
    if " " in identifier:
        parts = identifier.split(maxsplit=1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else None
        search_parts = [f"first_name:{first_name}"]
        if last_name:
            search_parts.append(f"last_name:{last_name}")
        search_desc = [f"first name '{first_name}'"]
        if last_name:
            search_desc.append(f"last name '{last_name}'")
        return {
            "identifier": identifier,
            "query": " ".join(search_parts),
            "not_found_message": f"No customers found with {' and '.join(search_desc)}",
            "first": 10,
            "json": args.json
        }
    
    # ID lookup
    if identifier.startswith("gid://shopify/Customer/"):
        numeric_id = identifier.split("/")[-1]
        search_query = f"id:{numeric_id}"
    elif identifier.isdigit():
        search_query = f"id:{identifier}"
    else:
        search_query = f"id:{identifier}"
    
    return {
        "identifier": identifier,
        "query": search_query,
        "not_found_message": f"No customer found with ID: {identifier}",
        "first": 1
    }


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
        query_params: Dict from parse_identifier() with keys:
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
        SystemExit: If GraphQL errors are present, results can't be interpreted, or no customers found
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
        print(json.dumps(response, indent=2, default=str), file=sys.stderr)
        sys.exit(1)
    
    # Interpret results into native objects (op + data pattern)
    try:
        query_result = op + response
    except Exception as e:
        print(f"❌ Error interpreting results: {type(e).__name__}: {e}", file=sys.stderr)
        print(json.dumps(response, indent=2, default=str), file=sys.stderr)
        sys.exit(1)
    
    # Extract customers from result
    customers_connection = query_result.customers
    customers_nodes = customers_connection.nodes if customers_connection else []
    
    # Check for empty customers (exit and display JSON with message)
    if not customers_nodes:
        print("No customers found", file=sys.stderr)
        print(json.dumps(response, indent=2, default=str), file=sys.stderr)
        sys.exit(1)
    
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

def print_customer_details_typed(customer: CustomerSGQLC, json_output: bool = False) -> None:
    """Print customer details using sgqlc Type instances."""
    if json_output:
        # __json_data__ is a real attribute on sgqlc Type instances
        print(json.dumps(customer.__json_data__, indent=2, default=str))  # type: ignore[attr-defined]
        return
    
    print("\n✅ Customer Found!")
    print("=" * 60)
    print(f"ID:            {customer.id}")  # type: ignore[attr-defined]
    name_parts = [customer.firstName, customer.lastName]  # type: ignore[attr-defined]
    full_name = " ".join(str(p) for p in name_parts if p) or customer.displayName or "N/A"  # type: ignore[attr-defined]
    print(f"Name:          {full_name}")
    print(f"Display Name:  {customer.displayName or 'N/A'}")  # type: ignore[attr-defined]
    print(f"Email:         {customer.email or 'N/A'}")  # type: ignore[attr-defined]
    print(f"Phone:         {customer.phone or 'N/A'}")  # type: ignore[attr-defined]
    print(f"State:         {customer.state or 'N/A'}")  # type: ignore[attr-defined]
    print(f"Verified:      {customer.verifiedEmail}")  # type: ignore[attr-defined]
    print(f"Orders Count:  {customer.numberOfOrders or 'N/A'}")  # type: ignore[attr-defined]
    print(f"Created:       {customer.createdAt or 'N/A'}")  # type: ignore[attr-defined]
    print(f"Updated:       {customer.updatedAt or 'N/A'}")  # type: ignore[attr-defined]
    
    if customer.tags:  # type: ignore[attr-defined]
        tags_list = list(customer.tags)  # type: ignore[attr-defined]
        print(f"\nTags ({len(tags_list)}):")
        for tag in tags_list:
            print(f"  • {tag}")
    
    if customer.defaultAddress:  # type: ignore[attr-defined]
        addr = customer.defaultAddress  # type: ignore[attr-defined]
        print("\nDefault Address:")
        if addr.address1:  # type: ignore[attr-defined]
            print(f"  {addr.address1}")  # type: ignore[attr-defined]
        if addr.address2:  # type: ignore[attr-defined]
            print(f"  {addr.address2}")  # type: ignore[attr-defined]
        city_parts = [str(p) for p in [addr.city, addr.province, addr.zip] if p]  # type: ignore[attr-defined]
        if city_parts:
            print(f"  {', '.join(city_parts)}")
        if addr.country:  # type: ignore[attr-defined]
            print(f"  {addr.country}")  # type: ignore[attr-defined]
    
    # Access orders from sgqlc Connection structure
    orders_connection = customer.orders  # type: ignore[attr-defined]
    recent_orders = orders_connection.nodes if orders_connection and hasattr(orders_connection, 'nodes') else []  # type: ignore[attr-defined]
    if recent_orders:
        print(f"\nRecent Orders ({len(recent_orders)}):")
        for order in recent_orders:
            print(f"  • {order.name or 'N/A'} (created: {order.createdAt or 'N/A'})")  # type: ignore[attr-defined]
            print(f"    ID: {order.id}")  # type: ignore[attr-defined]
    
    print("=" * 60)


def handle_multiple_results_typed(customers: List[CustomerSGQLC], json_output: bool) -> Literal[0, 1]:
    """Handle selection when multiple customers are found."""
    if json_output:
        customers_data = [c.__json_data__ for c in customers]  # type: ignore[attr-defined]
        print(json.dumps(customers_data, indent=2, default=str))
        return 0
    
    print(f"\n✅ Found {len(customers)} customers:")
    print("=" * 60)
    for idx, customer in enumerate(customers, 1):
        name_parts = [customer.firstName, customer.lastName]  # type: ignore[attr-defined]
        full_name = " ".join(str(p) for p in name_parts if p) or customer.displayName or "N/A"  # type: ignore[attr-defined]
        email = customer.email or 'N/A'  # type: ignore[attr-defined]
        print(f"{idx}. {full_name} ({email})")
    print("=" * 60)
    
    try:
        selection = input("\nEnter number to view details (or press Enter to cancel): ").strip()
        if not selection:
            print("Cancelled")
            return 0
        
        selected_idx = int(selection) - 1
        if selected_idx < 0 or selected_idx >= len(customers):
            print(f"❌ Invalid selection. Please enter a number between 1 and {len(customers)}")
            return 1
        
        print_customer_details_typed(customers[selected_idx], json_output=False)
        return 0
        
    except (ValueError, KeyboardInterrupt, EOFError):
        print("\n❌ Invalid input or cancelled")
        return 1


# ============================================================================
# Main CLI
# ============================================================================

def main() -> Literal[0, 1]:
    import sys
    sys.stdout.flush()
    
    # Configure logging
    logging.basicConfig(
        level=logging.WARNING,
        format='%(levelname)s: %(message)s',
        handlers=[logging.StreamHandler(sys.stderr)]
    )
    
    # Parse CLI arguments to get query parameters (handles all argument parsing)
    query_params = parse_identifier()
    
    try:
        # Use get_customer_by_identifier helper (handles query, execution, and interpretation)
        try:
            customers = get_customer_by_identifier(query_params, environment="production", orders_first=5)
        except RuntimeError as e:
            # HTTP/network errors are raised by client
            print(f"❌ HTTP Error: {e}", file=sys.stderr)
            return 1
        
        # Handle single vs multiple results
        if not customers:
            print("No customers found", file=sys.stderr)
            return 1
        
        json_output = query_params.get("json", True)
        
        if len(customers) == 1:
            # Single customer - print directly
            print_customer_details_typed(customers[0], json_output=json_output)
            return 0
        else:
            # Multiple customers - use handler
            return handle_multiple_results_typed(customers, json_output=json_output)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
    sys.exit(main())

