#!/usr/bin/env python3
"""
Update Customer Identifier (Email or Phone) in Shopify

This script updates a customer's email or phone number in Shopify.
It first validates that the customer exists before attempting the update.

Usage:
    python update_customer_identifier.py --id gid://shopify/Customer/123456789 --email new@example.com
    python update_customer_identifier.py --id gid://shopify/Customer/123456789 --phone "+1234567890"
"""

import sys
import json
import argparse
from typing import Optional
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from models import Customer, ShopifyResponse
from models.shopify_sgqlc_client import ShopifySGQLCClient
from shared_utils import make_graphql_request
from get_customer_details_pydantic import get_customer_by_identifier


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
    client = ShopifySGQLCClient(environment=environment)
    shopify_response = make_graphql_request(payload, client.config)
    return shopify_response


def main() -> int:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Update customer identifier (email or phone) in Shopify"
    )
    parser.add_argument(
        "--id",
        required=True,
        help="Customer ID (e.g., gid://shopify/Customer/123456789)"
    )
    parser.add_argument(
        "--email",
        help="New email address"
    )
    parser.add_argument(
        "--phone",
        help="New phone number"
    )
    parser.add_argument(
        "--env",
        default="production",
        choices=["production", "staging", "dev"],
        help="Environment to use (default: production)"
    )
    
    args = parser.parse_args()
    
    if not args.email and not args.phone:
        parser.error("Must provide at least one of --email or --phone")
        return 1
    
    try:
        response = update_customer_identifier(
            customer_id=args.id,
            new_email=args.email,
            new_phone=args.phone,
            environment=args.env
        )
        
        print(json.dumps(response.model_dump(), indent=2, default=str))
        
        if not response.success:
            return 1
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

