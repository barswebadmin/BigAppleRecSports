#!/usr/bin/env python3
"""
Get Customer Details from Shopify
Usage:
    python get_customer_details.py customer@example.com       # By email
    python get_customer_details.py "John Doe"                 # By first and last name
    python get_customer_details.py "f:John"                   # By first name only
    python get_customer_details.py "l:Doe"                    # By last name only
    python get_customer_details.py  # Prompts for email/ID/name
    python get_customer_details.py 123456789
    python get_customer_details.py --email customer@example.com
    python get_customer_details.py --id gid://shopify/Customer/123456789
    python get_customer_details.py customer@example.com --json
"""

import sys
import json
import argparse
from typing import Dict, Any, Optional, Literal, Tuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from shared_utils import load_environment, get_shopify_config, make_graphql_request


CUSTOMER_FIELDS = """
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
    orders(first: 5, sortKey: CREATED_AT, reverse: true) {
        edges {
            node {
                id
                name
                createdAt
            }
        }
    }
"""


IdentifierType = Literal["email", "id", "name"]


def parse_identifier(identifier: str) -> Tuple[IdentifierType, Dict[str, Any]]:
    """
    Parse identifier string and determine its type.
    
    Args:
        identifier: Input string (email, ID, or name)
        
    Returns:
        Tuple of (identifier_type, parsed_data)
        - For email: ("email", {"email": "user@example.com"})
        - For ID: ("id", {"id": "gid://shopify/Customer/123"})
        - For name: ("name", {"first_name": "John", "last_name": "Doe"})
    """
    if "@" in identifier:
        return ("email", {"email": identifier})
    
    if identifier.startswith("f:"):
        return ("name", {"first_name": identifier[2:].strip(), "last_name": None})
    
    if identifier.startswith("l:"):
        return ("name", {"first_name": None, "last_name": identifier[2:].strip()})
    
    if " " in identifier:
        parts = identifier.split(maxsplit=1)
        return ("name", {
            "first_name": parts[0],
            "last_name": parts[1] if len(parts) > 1 else None
        })
    
    if identifier.isdigit():
        return ("id", {"id": f"gid://shopify/Customer/{identifier}"})
    
    if identifier.startswith("gid://shopify/Customer/"):
        return ("id", {"id": identifier})
    
    return ("id", {"id": f"gid://shopify/Customer/{identifier}"})


def fetch_customers(
    query: str,
    variables: Dict[str, Any],
    config: Dict[str, Any],
    search_description: str
) -> Dict[str, Any]:
    """
    Execute GraphQL query and handle common error patterns.
    
    Args:
        query: GraphQL query string
        variables: Query variables
        config: Shopify API configuration
        search_description: Human-readable description of search (for error messages)
        
    Returns:
        Standardized result dict with success/message/customer(s)
    """
    payload = {"query": query, "variables": variables}
    
    try:
        data = make_graphql_request(payload, config)
        
        if "error" in data:
            return {
                "success": False,
                "message": data["error"],
                "customer": None
            }
        
        if "errors" in data:
            return {
                "success": False,
                "message": "GraphQL errors",
                "errors": data["errors"],
                "customer": None
            }
        
        return {
            "success": True,
            "data": data,
            "search_description": search_description
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "customer": None
        }


def get_customer_by_email(email: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch customer by email address."""
    query = f"""
    query getCustomer($query: String!) {{
        customers(first: 1, query: $query) {{
            edges {{
                node {{
                    {CUSTOMER_FIELDS}
                }}
            }}
        }}
    }}
    """
    
    result = fetch_customers(
        query=query,
        variables={"query": f"email:{email}"},
        config=config,
        search_description=f"email: {email}"
    )
    
    if not result["success"]:
        return result
    
    customers = result["data"].get("data", {}).get("customers", {}).get("edges", [])
    
    if not customers:
        return {
            "success": False,
            "message": f"No customer found with email: {email}",
            "customer": None
        }
    
    return {
        "success": True,
        "message": "Customer found",
        "customer": customers[0]["node"]
    }


def get_customer_by_id(customer_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch customer by ID."""
    query = f"""
    query getCustomer($id: ID!) {{
        customer(id: $id) {{
            {CUSTOMER_FIELDS}
        }}
    }}
    """
    
    result = fetch_customers(
        query=query,
        variables={"id": customer_id},
        config=config,
        search_description=f"ID: {customer_id}"
    )
    
    if not result["success"]:
        return result
    
    customer = result["data"].get("data", {}).get("customer")
    
    if not customer:
        return {
            "success": False,
            "message": f"No customer found with ID: {customer_id}",
            "customer": None
        }
    
    return {
        "success": True,
        "message": "Customer found",
        "customer": customer
    }


def get_customer_by_name(
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Fetch customers by first and/or last name."""
    if config is None:
        return {
            "success": False,
            "message": "Configuration is required",
            "customers": []
        }
    
    query = f"""
    query getCustomerByName($query: String!) {{
        customers(first: 10, query: $query) {{
            edges {{
                node {{
                    {CUSTOMER_FIELDS}
                }}
            }}
        }}
    }}
    """
    
    search_parts = []
    if first_name:
        search_parts.append(f"first_name:{first_name}")
    if last_name:
        search_parts.append(f"last_name:{last_name}")
    
    search_query = " ".join(search_parts)
    
    search_desc = []
    if first_name:
        search_desc.append(f"first name '{first_name}'")
    if last_name:
        search_desc.append(f"last name '{last_name}'")
    
    result = fetch_customers(
        query=query,
        variables={"query": search_query},
        config=config,
        search_description=" and ".join(search_desc)
    )
    
    if not result["success"]:
        return {**result, "customers": []}
    
    customers_edges = result["data"].get("data", {}).get("customers", {}).get("edges", [])
    customers = [edge["node"] for edge in customers_edges]
    
    if not customers:
        return {
            "success": False,
            "message": f"No customers found with {' and '.join(search_desc)}",
            "customers": []
        }
    
    return {
        "success": True,
        "message": f"Found {len(customers)} customer(s)",
        "customers": customers,
        "multiple": len(customers) > 1
    }


def print_customer_details(result: Dict[str, Any], json_output: bool = False) -> None:
    """Print customer details in a readable format."""
    if json_output:
        print(json.dumps(result, indent=2, default=str))
        return
    
    if not result["success"]:
        print(f"\n❌ {result['message']}")
        if "errors" in result:
            print("\nErrors:")
            print(json.dumps(result["errors"], indent=2))
        return
    
    customer = result["customer"]
    if not customer:
        print(f"\n📭 {result['message']}")
        return
    
    print("\n✅ Customer Found!")
    print("=" * 60)
    print(f"ID:            {customer.get('id', 'N/A')}")
    print(f"Name:          {customer.get('firstName', '')} {customer.get('lastName', '')}")
    print(f"Display Name:  {customer.get('displayName', 'N/A')}")
    print(f"Email:         {customer.get('email', 'N/A')}")
    print(f"Phone:         {customer.get('phone', 'N/A')}")
    print(f"State:         {customer.get('state', 'N/A')}")
    print(f"Verified:      {customer.get('verifiedEmail', 'N/A')}")
    print(f"Orders Count:  {customer.get('numberOfOrders', 'N/A')}")
    print(f"Created:       {customer.get('createdAt', 'N/A')}")
    print(f"Updated:       {customer.get('updatedAt', 'N/A')}")
    
    tags = customer.get('tags', [])
    if tags:
        print(f"\nTags ({len(tags)}):")
        for tag in tags:
            print(f"  • {tag}")
    
    default_address = customer.get('defaultAddress')
    if default_address:
        print("\nDefault Address:")
        print(f"  {default_address.get('address1', '')}")
        if default_address.get('address2'):
            print(f"  {default_address.get('address2')}")
        city = default_address.get('city', '')
        province = default_address.get('province', '')
        zip_code = default_address.get('zip', '')
        print(f"  {city}, {province} {zip_code}")
        print(f"  {default_address.get('country', '')}")
    
    orders_data = customer.get('orders', {})
    orders_edges = orders_data.get('edges', [])
    if orders_edges:
        print(f"\nRecent Orders ({len(orders_edges)}):")
        for edge in orders_edges:
            order = edge.get('node', {})
            order_name = order.get('name', 'N/A')
            order_id = order.get('id', 'N/A')
            created_at = order.get('createdAt', 'N/A')
            print(f"  • {order_name} (created: {created_at})")
            print(f"    ID: {order_id}")
    
    print("=" * 60)


def handle_multiple_results(customers: list, json_output: bool) -> int:
    """Handle selection when multiple customers are found."""
    if json_output:
        result = {
            "success": True,
            "message": f"Found {len(customers)} customers",
            "customers": customers,
            "multiple": True
        }
        print(json.dumps(result, indent=2, default=str))
        return 0
    
    print(f"\n✅ Found {len(customers)} customers:")
    print("=" * 60)
    for idx, customer in enumerate(customers, 1):
        first = customer.get('firstName', '')
        last = customer.get('lastName', '')
        email_addr = customer.get('email', 'N/A')
        print(f"{idx}. {first} {last} ({email_addr})")
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
        
        selected_result = {
            "success": True,
            "message": "Customer found",
            "customer": customers[selected_idx]
        }
        print_customer_details(selected_result, json_output=False)
        return 0
        
    except (ValueError, KeyboardInterrupt, EOFError):
        print("\n❌ Invalid input or cancelled")
        return 1


def main() -> int:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Get customer details from Shopify",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python get_customer_details.py customer@example.com              # Email (auto-detected)
  python get_customer_details.py "John Doe"                        # First and last name
  python get_customer_details.py "f:John"                          # First name only
  python get_customer_details.py "l:Doe"                           # Last name only
  python get_customer_details.py 123456789                         # Numeric ID (auto-converted to gid://)
  python get_customer_details.py gid://shopify/Customer/123456789  # Full gid format
  python get_customer_details.py customer@example.com --json       # With JSON output
  python get_customer_details.py --email customer@example.com      # Using explicit flag
  
Note: Name searches may return multiple results. You'll be prompted to select one.
        """
    )
    
    parser.add_argument(
        "identifier",
        nargs="?",
        help='Customer email, ID, or name. Name formats: "First Last", "f:First", "l:Last"'
    )
    parser.add_argument(
        "--email",
        help="Customer email address (alternative to positional arg)"
    )
    parser.add_argument(
        "--id",
        help="Customer ID (alternative to positional arg, e.g., gid://shopify/Customer/123456789)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted text"
    )
    parser.add_argument(
        "--env",
        default="production",
        choices=["production", "staging", "dev"],
        help="Environment to use (default: production)"
    )
    
    args = parser.parse_args()
    
    if not args.identifier and not args.email and not args.id:
        try:
            args.identifier = input("Enter customer email, ID, or name: ").strip()
            if not args.identifier:
                print("Error: Customer email, ID, or name is required", file=sys.stderr)
                return 1
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled", file=sys.stderr)
            return 1
    
    try:
        load_environment(args.env)
        config = get_shopify_config(args.env)
        
        if args.email:
            identifier_type, data = "email", {"email": args.email}
        elif args.id:
            identifier_type, data = "id", {"id": args.id}
        elif args.identifier:
            identifier_type, data = parse_identifier(args.identifier)
        else:
            parser.error("Must provide an identifier")
            return 1
        
        if identifier_type == "email":
            if not args.json:
                print(f"\n🔍 Searching for customer with email: {data['email']}")
            result = get_customer_by_email(data["email"], config)
            print_customer_details(result, json_output=args.json)
            return 0 if result["success"] else 1
            
        elif identifier_type == "id":
            if not args.json:
                print(f"\n🔍 Searching for customer with ID: {data['id']}")
            result = get_customer_by_id(data["id"], config)
            print_customer_details(result, json_output=args.json)
            return 0 if result["success"] else 1
            
        else:  # name
            first_name = data.get("first_name")
            last_name = data.get("last_name")
            
            search_desc = []
            if first_name:
                search_desc.append(f"first name '{first_name}'")
            if last_name:
                search_desc.append(f"last name '{last_name}'")
            
            if not args.json:
                print(f"\n🔍 Searching for customers with {' and '.join(search_desc)}")
            
            result = get_customer_by_name(
                first_name=first_name,
                last_name=last_name,
                config=config
            )
            
            if not result["success"]:
                if args.json:
                    print(json.dumps(result, indent=2, default=str))
                else:
                    print(f"\n❌ {result['message']}")
                return 1
            
            customers = result.get("customers", [])
            
            if len(customers) == 1:
                single_result = {
                    "success": True,
                    "message": "Customer found",
                    "customer": customers[0]
                }
                print_customer_details(single_result, json_output=args.json)
                return 0
            
            return handle_multiple_results(customers, args.json)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
