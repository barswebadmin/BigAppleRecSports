#!/usr/bin/env python3
"""
Get Pronouns from customer's recent orders.
Searches line item properties for "Pronouns" field and extracts name from form.
Orders are processed from most recent to oldest (by created_at).

Usage:
    python get_pronouns.py customer@example.com      # By email
    python get_pronouns.py "John Doe"                # By name
    python get_pronouns.py "f:John"                  # By first name
    python get_pronouns.py 123456789                 # By ID
    python get_pronouns.py  # Prompts for email/name/ID
    python get_pronouns.py customer@example.com --env development

Note: Name is extracted from "First Name" and "Last Name" properties in the order form,
not from the customer profile, so it reflects what the customer entered during registration.
Pronouns are lowercased automatically.
"""

import sys
import argparse
from typing import Dict, Any, List, Tuple
from pathlib import Path
import concurrent.futures

sys.path.insert(0, str(Path(__file__).parent))
from shared_utils import load_environment, get_shopify_config, make_graphql_request
from get_customer_details import (
    parse_identifier,
    get_customer_by_email,
    get_customer_by_id,
    get_customer_by_name
)


def get_customer_orders_with_dates(customer: Dict[str, Any]) -> List[Tuple[str, str]]:
    """
    Extract order IDs with created_at dates from customer data.
    Returns list of (order_id, created_at) tuples.
    """
    order_edges = customer.get("orders", {}).get("edges", [])
    return [
        (edge["node"]["id"], edge["node"].get("createdAt", ""))
        for edge in order_edges
    ]


def get_order_line_item_properties(order_id: str, config: Dict[str, Any]) -> List[Dict[str, str]]:
    """Fetch line item properties for a specific order."""
    # Query moved to bottom - see ALREADY MIGRATED section
    query = _GET_ORDER_QUERY
    
    payload = {
        "query": query,
        "variables": {"id": order_id}
    }
    
    result = make_graphql_request(payload, config)
    properties = []
    
    if "data" in result and result["data"].get("order"):
        order = result["data"]["order"]
        line_items = order.get("lineItems", {}).get("edges", [])
        
        for edge in line_items:
            node = edge.get("node", {})
            custom_attrs = node.get("customAttributes", [])
            properties.extend(custom_attrs)
    
    return properties


def extract_pronouns_with_name(properties: List[Dict[str, str]]) -> List[Tuple[str, str, str]]:
    """
    Extract pronouns with associated names from properties.
    Returns list of (pronouns_lowercase, first_name, last_name) tuples.
    """
    pronouns = None
    first_name = ""
    last_name = ""
    
    for prop in properties:
        key = prop.get("key", "").lower()
        value = prop.get("value", "").strip()
        
        if "pronouns" in key and value:
            # Lowercase the pronouns value as requested
            pronouns = value.lower()
        elif "first name" in key and value and not first_name:
            first_name = value
        elif "last name" in key and value and not last_name:
            last_name = value
    
    if pronouns:
        return [(pronouns, first_name, last_name)]
    return []


def fetch_pronouns_with_names(orders_with_dates: List[Tuple[str, str]], config: Dict[str, Any]) -> List[Tuple[str, str, str, str]]:
    """
    Fetch pronouns with associated names and dates from all orders concurrently.
    Returns list of (pronouns, first_name, last_name, created_at) tuples.
    Orders are already sorted by most recent first.
    """
    pronouns_records = []
    
    # Process orders concurrently while preserving date info
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_order = {
            executor.submit(get_order_line_item_properties, order_id, config): (order_id, created_at)
            for order_id, created_at in orders_with_dates
        }
        
        for future in concurrent.futures.as_completed(future_to_order):
            order_id, created_at = future_to_order[future]
            try:
                properties = future.result()
                records = extract_pronouns_with_name(properties)
                # Add created_at to each record
                for pronouns, first_name, last_name in records:
                    pronouns_records.append((pronouns, first_name, last_name, created_at))
            except Exception as e:
                print(f"Error fetching order {order_id}: {e}", file=sys.stderr)
    
    return pronouns_records


def process_customer_pronouns(customer: Dict[str, Any], config: Dict[str, Any]) -> int:
    """Process a single customer and display their pronouns."""
    orders_with_dates = get_customer_orders_with_dates(customer)
    
    if not orders_with_dates:
        email = customer.get("email", "unknown")
        print(f"No orders found for customer: {email}", file=sys.stderr)
        return 1
    
    pronouns_records = fetch_pronouns_with_names(orders_with_dates, config)
    
    if not pronouns_records:
        email = customer.get("email", "unknown")
        print(f"No Pronouns found in recent orders for: {email}", file=sys.stderr)
        return 1
    
    # Sort by created_at (most recent first), then by name
    # created_at is ISO 8601 format so string sort works correctly
    sorted_records = sorted(pronouns_records, key=lambda x: (x[3], x[1], x[2]), reverse=True)
    
    # Display results
    for pronouns, first_name, last_name, created_at in sorted_records:
        full_name = f"{first_name} {last_name}".strip()
        if full_name:
            print(f"{pronouns} - {full_name} (order: {created_at})")
        else:
            print(f"{pronouns} (order: {created_at})")
    
    return 0


def select_customer_from_multiple(customers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Prompt user to select a customer when multiple matches are found."""
    print(f"\n✅ Found {len(customers)} customers:")
    print("=" * 60)
    
    for idx, customer in enumerate(customers, 1):
        first = customer.get('firstName', '')
        last = customer.get('lastName', '')
        email = customer.get('email', 'N/A')
        print(f"{idx}. {first} {last} ({email})")
    
    print("=" * 60)
    
    try:
        selection = input("\nEnter number to view pronouns (or press Enter to cancel): ").strip()
        if not selection:
            print("Cancelled", file=sys.stderr)
            sys.exit(0)
        
        selected_idx = int(selection) - 1
        if selected_idx < 0 or selected_idx >= len(customers):
            print(f"❌ Invalid selection. Please enter a number between 1 and {len(customers)}", file=sys.stderr)
            sys.exit(1)
        
        return customers[selected_idx]
        
    except (ValueError, KeyboardInterrupt, EOFError):
        print("\n❌ Invalid input or cancelled", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Get Pronouns from customer's recent orders",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python get_pronouns.py customer@example.com    # By email
  python get_pronouns.py "John Doe"             # By first and last name
  python get_pronouns.py "f:John"               # By first name only
  python get_pronouns.py "l:Doe"                # By last name only
  python get_pronouns.py 123456789              # By customer ID
  python get_pronouns.py                        # Interactive prompt

Output shows pronouns (lowercased) with name and order date (most recent first).
"""
    )
    
    parser.add_argument(
        "identifier",
        nargs="?",
        help="Customer email, name (quoted), first name (f:Name), last name (l:Name), or ID"
    )
    parser.add_argument(
        "--env",
        "--environment",
        choices=["production", "staging", "development", "dev"],
        default="production",
        help="Environment (default: production)"
    )
    
    args = parser.parse_args()
    
    # Load environment and config
    environment = "development" if args.env == "dev" else args.env
    load_environment(environment)
    config = get_shopify_config(environment)
    
    # Get identifier
    identifier = args.identifier
    if not identifier:
        identifier = input("Enter customer email, name, or ID: ").strip()
        if not identifier:
            print("❌ No identifier provided", file=sys.stderr)
            sys.exit(1)
    
    # Parse identifier
    identifier_type, identifier_data = parse_identifier(identifier)
    
    # Fetch customer(s)
    if identifier_type == "email":
        result = get_customer_by_email(identifier_data["email"], config)
        if not result["success"]:
            print(f"❌ {result['message']}", file=sys.stderr)
            sys.exit(1)
        customer = result["customer"]
        exit_code = process_customer_pronouns(customer, config)
        sys.exit(exit_code)
    
    elif identifier_type == "id":
        result = get_customer_by_id(identifier_data["id"], config)
        if not result["success"]:
            print(f"❌ {result['message']}", file=sys.stderr)
            sys.exit(1)
        customer = result["customer"]
        exit_code = process_customer_pronouns(customer, config)
        sys.exit(exit_code)
    
    elif identifier_type in ["name", "first_name", "last_name"]:
        result = get_customer_by_name(
            identifier_data.get("first_name"),
            identifier_data.get("last_name"),
            config
        )
        if not result["success"]:
            print(f"❌ {result['message']}", file=sys.stderr)
            sys.exit(1)
        
        customers = result["customers"]
        if not customers:
            print(f"❌ No customers found matching: {identifier_data}", file=sys.stderr)
            sys.exit(1)
        
        if len(customers) == 1:
            exit_code = process_customer_pronouns(customers[0], config)
            sys.exit(exit_code)
        else:
            customer = select_customer_from_multiple(customers)
            exit_code = process_customer_pronouns(customer, config)
            sys.exit(exit_code)
    
    else:
        print(f"❌ Unknown identifier type: {identifier_type}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


# ============================================================================
# ALREADY MIGRATED - GraphQL Query Structures
# ============================================================================
# These query structures have been migrated to sgqlc models.
# They are kept here for reference only and should not be used in new code.

_GET_ORDER_QUERY = """
    query getOrder($id: ID!) {
        order(id: $id) {
            id
            createdAt
            lineItems(first: 50) {
                edges {
                    node {
                        customAttributes {
                            key
                            value
                        }
                    }
                }
            }
        }
    }
"""

