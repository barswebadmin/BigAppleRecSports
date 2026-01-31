#!/usr/bin/env python3
"""
Fetch Shopify GraphQL Schema via Introspection

This script fetches the complete Shopify Admin API GraphQL schema
and saves it to a JSON file for use with sgqlc code generation.

Usage:
    python scripts/shopify/fetch_schema.py --store YOUR_STORE --token YOUR_TOKEN
    python scripts/shopify/fetch_schema.py --env production  # Uses .env
"""

import argparse
import json
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from sgqlc.endpoint.http import HTTPEndpoint
from sgqlc.introspection import query as introspection_query


def fetch_shopify_schema(store_id: str, access_token: str, api_version: str = "2025-01") -> dict:
    """
    Fetch Shopify GraphQL schema via introspection.
    
    Args:
        store_id: Shopify store ID (e.g., 'your-store')
        access_token: Shopify Admin API access token
        api_version: Shopify API version (default: 2025-01)
    
    Returns:
        Schema introspection result as dict
    """
    url = f"https://{store_id}.myshopify.com/admin/api/{api_version}/graphql.json"
    
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token,
    }
    
    print(f"🔍 Fetching schema from: {url}")
    print(f"📡 API Version: {api_version}")
    
    endpoint = HTTPEndpoint(url, base_headers=headers, timeout=60)
    
    try:
        # Execute introspection query
        print("⏳ Executing introspection query...")
        # introspection_query is the query string, not a function
        # It requires variables for includeDescription and includeDeprecated
        result = endpoint(introspection_query, variables={
            'includeDescription': True,
            'includeDeprecated': True
        })
        
        if 'errors' in result:
            print("❌ GraphQL errors:", file=sys.stderr)
            for error in result['errors']:
                print(f"  - {error.get('message', error)}", file=sys.stderr)
            sys.exit(1)
        
        if 'data' not in result:
            print("❌ No data in response", file=sys.stderr)
            sys.exit(1)
        
        print("✅ Schema fetched successfully")
        return result['data']
    
    except Exception as e:
        print(f"❌ Failed to fetch schema: {e}", file=sys.stderr)
        sys.exit(1)


def save_schema(schema_data: dict, output_path: Path):
    """Save schema to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(schema_data, f, indent=2)
    
    print(f"💾 Schema saved to: {output_path}")
    
    # Print stats
    schema = schema_data.get('__schema', {})
    types = schema.get('types', [])
    query_type = schema.get('queryType', {}).get('name', 'N/A')
    mutation_type = schema.get('mutationType', {}).get('name', 'N/A')
    
    print(f"\n📊 Schema Statistics:")
    print(f"  - Total types: {len(types)}")
    print(f"  - Query type: {query_type}")
    print(f"  - Mutation type: {mutation_type}")


def load_from_env(environment: str = "production") -> tuple[str, str]:
    """Load Shopify credentials from environment variables."""
    import os
    from dotenv import load_dotenv
    
    # Load .env file
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"📄 Loaded environment from: {env_path}")
    
    # Try multiple environment variable formats
    if environment.lower() in ["production", "staging"]:
        store_id = (
            os.getenv("SHOPIFY_STORE_ID") or
            os.getenv("SHOPIFY_STORE") or
            os.getenv("SHOPIFY.STORE_ID")
        )
        token = (
            os.getenv("SHOPIFY_TOKEN_ADMIN") or
            os.getenv("SHOPIFY_TOKEN") or
            os.getenv("SHOPIFY.TOKEN.ADMIN") or
            os.getenv("SHOPIFY.TOKEN.WRITE_ORDERS_READ_PRODUCTS_CUSTOMERS")
        )
    else:
        # Development
        store_id = (
            os.getenv("SHOPIFY_DEV_STORE_ID") or
            os.getenv("SHOPIFY_DEV_STORE")
        )
        token = os.getenv("SHOPIFY_DEV_TOKEN")
    
    if not store_id or not token:
        print("❌ Missing Shopify credentials in environment", file=sys.stderr)
        print("\nRequired environment variables:", file=sys.stderr)
        print("  - SHOPIFY_STORE_ID (or SHOPIFY_STORE)", file=sys.stderr)
        print("  - SHOPIFY_TOKEN_ADMIN (or SHOPIFY_TOKEN)", file=sys.stderr)
        sys.exit(1)
    
    return store_id, token


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Shopify GraphQL schema via introspection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using explicit credentials
  python scripts/shopify/fetch_schema.py --store my-store --token shpat_xxxxx
  
  # Using environment variables (from .env)
  python scripts/shopify/fetch_schema.py --env production
  python scripts/shopify/fetch_schema.py --env development
  
  # Custom output path
  python scripts/shopify/fetch_schema.py --env production --output custom_schema.json
  
  # Specific API version
  python scripts/shopify/fetch_schema.py --env production --api-version 2024-10
        """
    )
    
    parser.add_argument(
        '--store',
        help='Shopify store ID (e.g., "my-store" for my-store.myshopify.com)'
    )
    parser.add_argument(
        '--token',
        help='Shopify Admin API access token'
    )
    parser.add_argument(
        '--env',
        choices=['production', 'staging', 'development'],
        help='Load credentials from environment variables'
    )
    parser.add_argument(
        '--api-version',
        default='2025-01',
        help='Shopify API version (default: 2025-01)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('backend/modules/integrations/shopify/schema/shopify_schema.json'),
        help='Output path for schema JSON (default: backend/modules/integrations/shopify/schema/shopify_schema.json)'
    )
    
    args = parser.parse_args()
    
    # Get credentials
    if args.env:
        store_id, token = load_from_env(args.env)
    elif args.store and args.token:
        store_id = args.store
        token = args.token
    else:
        parser.error("Either --env or both --store and --token are required")
    
    # Fetch schema
    schema_data = fetch_shopify_schema(store_id, token, args.api_version)
    
    # Save to file
    save_schema(schema_data, args.output)
    
    print("\n✨ Done! You can now generate sgqlc types:")
    print(f"   sgqlc-codegen schema {args.output} backend/modules/integrations/shopify/models/sgqlc_models/shopify_schema.py")


if __name__ == "__main__":
    main()
