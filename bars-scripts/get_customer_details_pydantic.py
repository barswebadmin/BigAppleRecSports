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
import warnings
import logging
from typing import Dict, Any, Optional, List, Literal, Tuple
from pathlib import Path

# Suppress Pydantic serializer warnings for Connection -> List resolution
# This is expected behavior - connections are resolved to lists in model_post_init
warnings.filterwarnings('ignore', category=UserWarning, module='pydantic')

from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent))
from shared_utils import (
    make_graphql_request,
    query_with_pydantic_model
)
from models import (
    Customer,
    Customers,
    Order,
    ShopifyResponse,
)
from models.sgqlc_query import Query
from models.shopify_sgqlc_client import ShopifySGQLCClient



# ============================================================================
# Constants
# ============================================================================

CUSTOMER_QUERY_FIELDS = """
    id
    firstName
    lastName
    email
    displayName
    phone
    tags
    numberOfOrders
    createdAt
    updatedAt
    state
    verifiedEmail
    defaultAddress {
        address1
        address2
        city
        province
        zip
        country
    }
    orders(first: 5, sortKey: CREATED_AT, reverse: true) {
        edges {
            cursor
            node {
                id
                name
                createdAt
            }
        }
        pageInfo {
            hasNextPage
            hasPreviousPage
            startCursor
            endCursor
        }
    }
"""


# ============================================================================
# Utility Functions
# ============================================================================

def handle_graphql_response(
    response: Dict[str, Any],
    not_found_message: str
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Handle GraphQL response and extract data or error message.
    
    Args:
        response: Raw GraphQL response dict
        not_found_message: Message to return if no data found
        
    Returns:
        Tuple of (customers_data dict, error_message str)
        Returns (None, error_message) on error
        Returns (customers_data, None) on success
    """
    if "error" in response:
        return None, response["error"]
    
    if "errors" in response:
        return None, "GraphQL errors"
    
    customers_data = response.get("data", {}).get("customers", {})
    # Support both nodes (simplified) and edges (legacy)
    nodes = customers_data.get("nodes", [])
    edges = customers_data.get("edges", [])
    
    if not nodes and not edges:
        return None, not_found_message
    
    return customers_data, None


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
    parser.add_argument("--json", action="store_true", default=True, help="Output raw JSON (default: True)")
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


def update_customer_identifier(
    customer_id: str,
    new_email: Optional[str] = None,
    new_phone: Optional[str] = None,
    environment: str = "production"
) -> ShopifyResponse:
    """
    Update a customer's identifier (email or phone) using sgqlc Operation.
    
    First validates the customer exists, then updates it.
    
    Args:
        customer_id: Customer ID (gid://shopify/Customer/...)
        new_email: New email address (optional)
        new_phone: New phone number (optional)
        environment: Environment name ("production", "staging", or "development").
            Defaults to "production".
        
    Returns:
        ShopifyResponse with mutation result
        
    Raises:
        ValueError: If customer not found or no update fields provided
    """
    # First, get the customer to validate it exists
    # Create query params dict for get_customer_by_identifier
    query_params = {
        "identifier": customer_id,
        "query": f"id:{customer_id.split('/')[-1]}" if customer_id.startswith("gid://shopify/Customer/") else f"id:{customer_id}",
        "not_found_message": f"Customer not found: {customer_id}",
        "first": 1
    }
    # get_customer_by_identifier will exit if there are GraphQL errors or no customers found
    # If we get here, the customer exists
    _ = get_customer_by_identifier(query_params, environment=environment)
    
    # Build mutation using Customer model's class method
    mutation, variables = Customer.build_update_mutation(
        customer_id,
        new_email=new_email,
        new_phone=new_phone
    )
    
    payload = {
        "query": str(mutation),
        "variables": variables
    }
    
    # Get config from client for make_graphql_request (legacy function)
    from models.shopify_sgqlc_client import ShopifySGQLCClient
    client = ShopifySGQLCClient(environment=environment)
    shopify_response = make_graphql_request(payload, client.config)
    return shopify_response




def get_all_customers_paginated(
    config: Dict[str, Any],
    query: Optional[str] = None,
    page_size: int = 250
) -> List[Customer]:
    """
    Fetch all customers using cursor-based pagination.
    
    Useful for large result sets that need to be fetched in chunks.
    
    Args:
        config: Shopify API configuration
        query: Optional search query (e.g., "email:test@example.com")
        page_size: Number of customers per page (default: 250, max recommended: 250)
        
    Returns:
        List of all Customer objects
        
    Example:
        ```python
        # Get all customers
        all_customers = get_all_customers_paginated(config)
        
        # Get all customers matching a query
        all_test_customers = get_all_customers_paginated(
            config, 
            query="email:*@test.com"
        )
        ```
    """
    all_customers: List[Customer] = []
    cursor: Optional[str] = None
    page_num = 1
    
    base_query = """
    query getCustomers($query: String, $after: String, $first: Int!) {
        customers(first: $first, query: $query, after: $after) {
            edges {
                cursor
                node {
                    id
                    firstName
                    lastName
                    email
                    displayName
                    phone
                    tags
                    numberOfOrders
                    createdAt
                    updatedAt
                    state
                    verifiedEmail
                    addresses {
                        address1
                        address2
                        city
                        province
                        zip
                        country
                    }
                    defaultAddress {
                        address1
                        address2
                        city
                        province
                        zip
                        country
                    }
                }
            }
            pageInfo {
                hasNextPage
                hasPreviousPage
                startCursor
                endCursor
            }
        }
    }
    """
    
    while True:
        payload = {
            "query": base_query,
            "variables": {
                "query": query,
                "after": cursor,
                "first": page_size
            }
        }
        
        try:
            response = make_graphql_request(payload, config)
            
            if "error" in response or "errors" in response:
                error_msg = response.get("error") or response.get("errors", [])
                raise Exception(f"GraphQL error on page {page_num}: {error_msg}")
            
            customers_data = response.get("data", {}).get("customers", {})
            
            # Use Customers list model - automatically handles Connection structure resolution
            if customers_data:
                if Customers is None:
                    raise Exception("Customers list model not available")
                page_customers = Customers(customers_data)
                all_customers.extend(page_customers)
            
            page_info_data = customers_data.get("pageInfo", {}) if isinstance(customers_data, dict) else {}
            
            has_next = page_info_data.get("hasNextPage", False)
            cursor = page_info_data.get("endCursor")
            
            if not has_next or not cursor:
                break
            
            page_num += 1
            
        except Exception as e:
            raise Exception(f"Error fetching page {page_num}: {str(e)}")
    
    return all_customers


# ============================================================================
# Display Functions (Now Type-Safe)
# ============================================================================

# TODO: Re-enable formatted printing when needed
# def print_customer_details_typed(customer: Customer, json_output: bool = False) -> None:
#     """Print customer details using typed models."""
#     if json_output:
#         print(json.dumps(customer.model_dump(mode='python'), indent=2, default=str))
#         return
#     
#     print("\n✅ Customer Found!")
#     print("=" * 60)
#     print(f"ID:            {customer.id}")
#     name_parts = [customer.firstName, customer.lastName]
#     full_name = " ".join(p for p in name_parts if p) or customer.displayName or "N/A"
#     print(f"Name:          {full_name}")
#     print(f"Display Name:  {customer.displayName or 'N/A'}")
#     print(f"Email:         {customer.email or 'N/A'}")
#     print(f"Phone:         {customer.phone or 'N/A'}")
#     print(f"State:         {customer.state or 'N/A'}")
#     print(f"Verified:      {customer.verifiedEmail}")
#     print(f"Orders Count:  {customer.numberOfOrders or 'N/A'}")
#     print(f"Created:       {customer.createdAt or 'N/A'}")
#     print(f"Updated:       {customer.updatedAt or 'N/A'}")
#     
#     if customer.tags:
#         print(f"\nTags ({len(customer.tags)}):")
#         for tag in customer.tags:
#             print(f"  • {tag}")
#     
#     if customer.defaultAddress:
#         addr = customer.defaultAddress
#         print("\nDefault Address:")
#         if addr.address1:
#             print(f"  {addr.address1}")
#         if addr.address2:
#             print(f"  {addr.address2}")
#         city_parts = [p for p in [addr.city, addr.province, addr.zip] if p]
#         if city_parts:
#             print(f"  {', '.join(city_parts)}")
#         if addr.country:
#             print(f"  {addr.country}")
#     
#     recent_orders = customer.recent_orders
#     if recent_orders:
#         print(f"\nRecent Orders ({len(recent_orders)}):")
#         for order in recent_orders:
#             print(f"  • {order.name or 'N/A'} (created: {order.createdAt or 'N/A'})")
#             print(f"    ID: {order.id}")
#     
#     print("=" * 60)


# def handle_multiple_results_typed(customers: List[Customer], json_output: bool) -> Literal[0, 1]:
#     """Handle selection when multiple customers are found."""
#     if json_output:
#         customers_data = [c.model_dump(mode='python') for c in customers]
#         print(json.dumps(customers_data, indent=2, default=str))
#         return 0
#     
#     print(f"\n✅ Found {len(customers)} customers:")
#     print("=" * 60)
#     for idx, customer in enumerate(customers, 1):
#         name_parts = [customer.firstName, customer.lastName]
#         full_name = " ".join(p for p in name_parts if p) or customer.displayName or "N/A"
#         print(f"{idx}. {full_name} ({customer.email or 'N/A'})")
#     print("=" * 60)
#     
#     try:
#         selection = input("\nEnter number to view details (or press Enter to cancel): ").strip()
#         if not selection:
#             print("Cancelled")
#             return 0
#         
#         selected_idx = int(selection) - 1
#         if selected_idx < 0 or selected_idx >= len(customers):
#             print(f"❌ Invalid selection. Please enter a number between 1 and {len(customers)}")
#             return 1
#         
#         print_customer_details_typed(customers[selected_idx], json_output=False)
#         return 0
#         
#     except (ValueError, KeyboardInterrupt, EOFError):
#         print("\n❌ Invalid input or cancelled")
#         return 1


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
    logger = logging.getLogger(__name__)
    
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
        
        # Convert customers to JSON and print
        customers_data = []
        for customer in customers:
            customers_data.append(customer.__json_data__)
        
        print(json.dumps(customers_data, indent=2, default=str))
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

#     """Main CLI entrypoint."""
#     parser = argparse.ArgumentParser(
#         description="Get customer details from Shopify (Type-Safe Version)",
#         formatter_class=argparse.RawDescriptionHelpFormatter
#     )
    
#     parser.add_argument(
#         "identifier",
#         nargs="?",
#         help='Customer email, ID, or name. Name formats: "First Last", "f:First", "l:Last"'
#     )
#     parser.add_argument("--email", help="Customer email address")
#     parser.add_argument("--id", help="Customer ID (e.g., gid://shopify/Customer/123456789)")
#     parser.add_argument("--json", action="store_true", default=True, help="Output raw JSON (default: True)")
#     parser.add_argument(
#         "--env",
#         default="production",
#         choices=["production", "staging", "dev"],
#         help="Environment to use (default: production)"
#     )
    
#     args = parser.parse_args()
    
#     if not args.identifier and not args.email and not args.id:
#         try:
#             args.identifier = input("Enter customer email, ID, or name: ").strip()
#             if not args.identifier:
#                 print("Error: Customer email, ID, or name is required", file=sys.stderr)
#                 return 1
#         except (KeyboardInterrupt, EOFError):
#             print("\nCancelled", file=sys.stderr)
#             return 1
    
#     try:
#         load_environment(args.env)
#         config = get_shopify_config(args.env)
        
#         # Parse identifier into query params
#         if args.email:
#             query_params = {
#                 "query": f"email:{args.email}",
#                 "not_found_message": f"No customer found with email: {args.email}",
#                 "first": 1
#             }
#             if not args.json:
#                 print(f"\n🔍 Searching for customer with email: {args.email}")
#         elif args.id:
#             if args.id.startswith("gid://shopify/Customer/"):
#                 numeric_id = args.id.split("/")[-1]
#                 search_query = f"id:{numeric_id}"
#             else:
#                 search_query = f"id:{args.id}"
#             query_params = {
#                 "query": search_query,
#                 "not_found_message": f"No customer found with ID: {args.id}",
#                 "first": 1
#             }
#             if not args.json:
#                 print(f"\n🔍 Searching for customer with ID: {args.id}")
#         elif args.identifier:
#             query_params = parse_identifier(args.identifier)
#             if not args.json:
#                 # Extract search description from query
#                 query = query_params["query"]
#                 if query.startswith("email:"):
#                     print(f"\n🔍 Searching for customer with email: {query[6:]}")
#                 elif query.startswith("id:"):
#                     print(f"\n🔍 Searching for customer with ID: {query[3:]}")
#                 else:
#                     print(f"\n🔍 Searching for customers with query: {query}")
#         else:
#             parser.error("Must provide an identifier")
#             return 1
        
#         result = get_customer_by_identifier(
#             args.identifier or args.email or args.id,
#             config
#         )
        
#         if not result.success:
#             print(json.dumps(result.model_dump(), indent=2, default=str))
#             return 1
        
#         # Print result as JSON (all customers, single or multiple)
#         print(json.dumps(result.model_dump(), indent=2, default=str))
#         # Check if results are empty for proper exit code
#         connection = result.get_connection("customers")
#         if not connection or (not connection.get("nodes") and not connection.get("edges")):
#             return 1
#         return 0
        
#         # TODO: Re-enable formatted printing and multiple results handling when needed
#         # # Extract Connection from GraphQL response structure
#         # connection = result.get_connection("customers")
#         # if not connection or not connection.get("edges"):
#         #     print(f"\n📭 No customers found")
#         #     return 1
#         # 
#         # # Convert Connection to list of Customer models
#         # if Customers is None:
#         #     print("❌ Customers list model not available")
#         #     return 1
#         # 
#         # customers = Customers.from_connection(connection)
#         # 
#         # if not customers:
#         #     print(f"\n📭 {query_params.get('not_found_message', 'No customers found')}")
#         #     return 1
#         # 
#         # # Handle single vs multiple results
#         # if len(customers) == 1:
#         #     print_customer_details_typed(customers[0], json_output=False)
#         #     return 0
#         # 
#         # # Multiple results - commented out, now just print all as JSON above
#         # # return handle_multiple_results_typed(customers, args.json)
        
#     except Exception as e:
#         print(f"\n❌ Error: {e}")
#         import traceback
#         traceback.print_exc()
#         return 1


if __name__ == "__main__":
    sys.exit(main())

