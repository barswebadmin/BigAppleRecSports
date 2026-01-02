#!/usr/bin/env python3
"""
Get Date of Birth from customer's recent orders.
Searches line item properties for "Date of Birth" field and extracts name from form.

Usage:
    python get_bday.py customer@example.com      # By email
    python get_bday.py "John Doe"                # By name
    python get_bday.py "f:John"                  # By first name
    python get_bday.py 123456789                 # By ID
    python get_bday.py  # Prompts for email/name/ID
    python get_bday.py customer@example.com --env development

Note: Name is extracted from "First Name" and "Last Name" properties in the order form,
not from the customer profile, so it reflects what the customer entered during registration.
"""

import sys
import argparse
from typing import Dict, Any, List, Set
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


def get_order_line_item_properties(order_id: str, config: Dict[str, Any]) -> List[Dict[str, str]]:
    """Fetch line item properties for a specific order."""
    query = """
    query getOrder($id: ID!) {
        order(id: $id) {
            id
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


def extract_birthday_with_name(properties: List[Dict[str, str]]) -> List[tuple]:
    """
    Extract birthdays with associated names from properties.
    Returns list of (birthday, first_name, last_name) tuples.
    """
    birthday = None
    first_name = ""
    last_name = ""
    
    for prop in properties:
        key = prop.get("key", "").lower()
        value = prop.get("value", "").strip()
        
        if "date of birth" in key and value:
            birthday = value
        elif "first name" in key and value and not first_name:
            first_name = value
        elif "last name" in key and value and not last_name:
            last_name = value
    
    if birthday:
        return [(birthday, first_name, last_name)]
    return []


def get_customer_orders(customer: Dict[str, Any]) -> List[str]:
    """Extract order IDs from customer data."""
    order_edges = customer.get("orders", {}).get("edges", [])
    return [edge["node"]["id"] for edge in order_edges]


def fetch_birthdays_with_names(order_ids: List[str], config: Dict[str, Any]) -> List[tuple]:
    """
    Fetch birthdays with associated names from all orders concurrently.
    Returns list of (birthday, first_name, last_name) tuples.
    """
    birthday_records = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_order = {
            executor.submit(get_order_line_item_properties, order_id, config): order_id
            for order_id in order_ids
        }
        
        for future in concurrent.futures.as_completed(future_to_order):
            try:
                properties = future.result()
                records = extract_birthday_with_name(properties)
                birthday_records.extend(records)
            except Exception as e:
                print(f"Error fetching order: {e}", file=sys.stderr)
    
    return birthday_records


def process_customer_birthday(customer: Dict[str, Any], config: Dict[str, Any]) -> int:
    """Process a single customer and display their birthday."""
    order_ids = get_customer_orders(customer)
    
    if not order_ids:
        email = customer.get("email", "unknown")
        print(f"No orders found for customer: {email}", file=sys.stderr)
        return 1
    
    birthday_records = fetch_birthdays_with_names(order_ids, config)
    
    if not birthday_records:
        email = customer.get("email", "unknown")
        print(f"No Date of Birth found in recent orders for: {email}", file=sys.stderr)
        return 1
    
    # Sort by birthday, then by name
    sorted_records = sorted(birthday_records, key=lambda x: (x[0], x[1], x[2]))
    
    for birthday, first_name, last_name in sorted_records:
        full_name = f"{first_name} {last_name}".strip()
        if full_name:
            print(f"{birthday} - {full_name}")
        else:
            print(birthday)
    
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
        selection = input("\nEnter number to view birthday (or press Enter to cancel): ").strip()
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
        description="Get Date of Birth from customer's recent orders",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python get_bday.py customer@example.com    # By email
  python get_bday.py "John Doe"             # By first and last name
  python get_bday.py "f:John"               # By first name only
  python get_bday.py "l:Doe"                # By last name only
  python get_bday.py 123456789              # By customer ID
  
Note: Name searches may return multiple results. You'll be prompted to select one.
        """
    )
    parser.add_argument(
        "identifier",
        nargs="?",
        help='Customer email, ID, or name. Name formats: "First Last", "f:First", "l:Last"'
    )
    parser.add_argument(
        "--env",
        choices=["development", "staging", "production"],
        default="production",
        help="Environment (default: production)"
    )
    
    args = parser.parse_args()
    
    if not args.identifier:
        try:
            args.identifier = input("Enter customer email, ID, or name: ").strip()
            if not args.identifier:
                print("Error: Customer email, ID, or name is required", file=sys.stderr)
                return 1
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled", file=sys.stderr)
            return 1
    
    load_environment(args.env)
    config = get_shopify_config(args.env)
    
    identifier_type, data = parse_identifier(args.identifier)
    
    try:
        if identifier_type == "email":
            result = get_customer_by_email(data["email"], config)
            
            if not result["success"]:
                print(f"Error: {result['message']}", file=sys.stderr)
                return 1
            
            customer = result["customer"]
            
        elif identifier_type == "id":
            result = get_customer_by_id(data["id"], config)
            
            if not result["success"]:
                print(f"Error: {result['message']}", file=sys.stderr)
                return 1
            
            customer = result["customer"]
            
        else:  # name
            result = get_customer_by_name(
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
                config=config
            )
            
            if not result["success"]:
                print(f"Error: {result['message']}", file=sys.stderr)
                return 1
            
            customers = result.get("customers", [])
            
            if len(customers) == 1:
                customer = customers[0]
            else:
                customer = select_customer_from_multiple(customers)
        
        return process_customer_birthday(customer, config)
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
