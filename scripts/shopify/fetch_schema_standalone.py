#!/usr/bin/env python3
"""
Standalone Shopify GraphQL Schema Fetcher

Fetches Shopify schema without requiring backend imports.
Just needs sgqlc installed: pip install sgqlc

Usage:
    python scripts/shopify/fetch_schema_standalone.py YOUR_STORE YOUR_TOKEN
    
Example:
    python scripts/shopify/fetch_schema_standalone.py my-store shpat_xxxxxxxxxxxxx
"""

import json
import sys
from pathlib import Path

try:
    from sgqlc.endpoint.http import HTTPEndpoint
    from sgqlc.introspection import query
except ImportError:
    print("❌ sgqlc not installed. Install with: pip install sgqlc", file=sys.stderr)
    sys.exit(1)


def fetch_schema(store_id: str, access_token: str, api_version: str = "2025-01"):
    """Fetch Shopify GraphQL schema via introspection."""
    
    url = f"https://{store_id}.myshopify.com/admin/api/{api_version}/graphql.json"
    
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token,
    }
    
    print(f"🔍 Fetching schema from: {url}")
    print(f"📡 API Version: {api_version}")
    
    endpoint = HTTPEndpoint(url, base_headers=headers, timeout=60)
    
    try:
        print("⏳ Executing introspection query...")
        # query is the introspection query string, not a function
        # It requires variables for includeDescription and includeDeprecated
        result = endpoint(query, variables={
            'includeDescription': True,
            'includeDeprecated': True
        })
        
        if 'errors' in result:
            print("❌ GraphQL errors:", file=sys.stderr)
            for error in result['errors']:
                print(f"  - {error.get('message', error)}", file=sys.stderr)
            return None
        
        if 'data' not in result:
            print("❌ No data in response", file=sys.stderr)
            return None
        
        print("✅ Schema fetched successfully")
        return result['data']
    
    except Exception as e:
        print(f"❌ Failed to fetch schema: {e}", file=sys.stderr)
        return None


def main():
    if len(sys.argv) < 3:
        print("Usage: python fetch_schema_standalone.py STORE_ID ACCESS_TOKEN [API_VERSION]")
        print("\nExample:")
        print("  python fetch_schema_standalone.py my-store shpat_xxxxx")
        print("  python fetch_schema_standalone.py my-store shpat_xxxxx 2024-10")
        sys.exit(1)
    
    store_id = sys.argv[1]
    access_token = sys.argv[2]
    api_version = sys.argv[3] if len(sys.argv) > 3 else "2025-01"
    
    # Fetch schema
    schema_data = fetch_schema(store_id, access_token, api_version)
    
    if not schema_data:
        sys.exit(1)
    
    # Save to file
    output_path = Path("shopify_schema.json")
    with open(output_path, 'w') as f:
        json.dump(schema_data, f, indent=2)
    
    print(f"\n💾 Schema saved to: {output_path}")
    
    # Print stats
    schema = schema_data.get('__schema', {})
    types = schema.get('types', [])
    query_type = schema.get('queryType', {}).get('name', 'N/A')
    mutation_type = schema.get('mutationType', {}).get('name', 'N/A')
    
    print(f"\n📊 Schema Statistics:")
    print(f"  - Total types: {len(types)}")
    print(f"  - Query type: {query_type}")
    print(f"  - Mutation type: {mutation_type}")
    
    print("\n✨ Next steps:")
    print("  1. Generate sgqlc types:")
    print(f"     sgqlc-codegen schema {output_path} shopify_schema.py")
    print("\n  2. Or use with graphql-codegen for TypeScript:")
    print(f"     # Add {output_path} to your codegen.yml schema")


if __name__ == "__main__":
    main()
