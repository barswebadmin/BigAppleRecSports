#!/usr/bin/env python3
"""
Get Order Details from Shopify - Type-Safe Version using sgqlc

This script uses sgqlc for query generation and type-safe GraphQL operations.

Usage:
    python get_order_details_pydantic.py --id gid://shopify/Order/123456789
    python get_order_details_pydantic.py --number 1234
"""

import sys
import json
import argparse
import logging
from typing import Dict, Any, List, Literal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from models.sgqlc_query import Query
from models.shopify_sgqlc_client import ShopifySGQLCClient


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
        - first: Number of results to fetch (default: 1 for single lookups)
        - json: Whether to output JSON (from --json flag)
    
    Raises:
        SystemExit: If user cancels interactive input or no identifier provided
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Get order details from Shopify")
    parser.add_argument("--id", help="Order ID (e.g., gid://shopify/Order/123456789)")
    parser.add_argument("--number", help="Order number (e.g., 1234 or #1234)")
    parser.add_argument("--json", action="store_true", default=True, help="Output raw JSON (default: True)")
    args = parser.parse_args()
    
    # Determine identifier from arguments
    if not args.id and not args.number:
        try:
            identifier = input("Enter order ID or number: ").strip()
            if not identifier:
                print("Error: Order ID or number is required", file=sys.stderr)
                sys.exit(1)
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled", file=sys.stderr)
            sys.exit(1)
        
        # Try to determine if it's an ID or number
        if identifier.startswith("gid://shopify/Order/"):
            args.id = identifier
        elif identifier.isdigit() or identifier.startswith("#"):
            args.number = identifier
        else:
            # Default to ID
            args.id = identifier
    
    # Determine identifier and query string
    if args.id:
        identifier = args.id
        if identifier.startswith("gid://shopify/Order/"):
            numeric_id = identifier.split("/")[-1]
            query_str = f"id:{numeric_id}"
        else:
            query_str = f"id:{identifier}"
        return {
            "identifier": identifier,
            "query": query_str,
            "not_found_message": f"No order found with ID: {identifier}",
            "first": 1,
            "json": args.json
        }
    elif args.number:
        identifier = args.number
        # Strip # if present
        order_num = identifier.strip().lstrip('#')
        query_str = f"name:#{order_num}"
        return {
            "identifier": identifier,
            "query": query_str,
            "not_found_message": f"No order found with number: {order_num}",
            "first": 1,
            "json": args.json
        }
    else:
        print("❌ Error: Must provide --id or --number", file=sys.stderr)
        sys.exit(1)


def get_order_by_identifier(
    query_params: Dict[str, Any],
    environment: str = "production",
    line_items_first: int = 5
) -> List[Any]:
    """
    Get an order by identifier using Shopify SGQLC client.
    
    Handles the complete flow:
    1. Builds and executes the GraphQL query
    2. Checks for GraphQL errors (exits if found)
    3. Interprets results into native objects
    4. Extracts orders from result
    5. Returns list of order objects or exits if none found
    
    Args:
        query_params: Dict from parse_identifier() with keys:
            - query: GraphQL search query string
            - first: Number of results to fetch
            - not_found_message: Error message if not found
            - identifier: Original identifier string (optional, for reference)
        environment: Environment name ("production", "staging", or "development").
            Defaults to "production".
        line_items_first: Number of line items to fetch per order (default: 5)
    
    Returns:
        List of order objects (sgqlc Type instances)
    
    Raises:
        RuntimeError: If the HTTP request fails (non-200 status or network errors)
        SystemExit: If GraphQL errors are present, results can't be interpreted, or no orders found
    """
    query_str = query_params["query"]
    first = query_params.get("first", 1)
    
    # Build query operation (domain-specific logic in models)
    op = Query.build_order_query(query_str, first=first, line_items_first=line_items_first)
    
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
    
    # Extract orders from result
    orders_connection = query_result.orders
    orders_nodes = orders_connection.nodes if orders_connection else []
    
    # Check for empty orders (exit and display JSON with message)
    if not orders_nodes:
        print("No orders found", file=sys.stderr)
        print(json.dumps(response, indent=2, default=str), file=sys.stderr)
        sys.exit(1)
    
    return orders_nodes


# ============================================================================
# Main CLI
# ============================================================================

def main() -> Literal[0, 1]:
    """Main CLI entrypoint."""
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
        # Use get_order_by_identifier helper (handles query, execution, and interpretation)
        try:
            orders = get_order_by_identifier(query_params, environment="production", line_items_first=5)
        except RuntimeError as e:
            # HTTP/network errors are raised by client
            print(f"❌ HTTP Error: {e}", file=sys.stderr)
            return 1
        
        # Convert orders to JSON and print
        orders_data = []
        for order in orders:
            orders_data.append(order.__json_data__)
        
        print(json.dumps(orders_data, indent=2, default=str))
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
