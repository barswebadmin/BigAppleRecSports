#!/usr/bin/env python3
"""
Fetch Filtered Shopify GraphQL Schema - Exclude-Only Strategy

This script fetches the Shopify schema and excludes types you don't need.
Everything is included by default, then excluded types are removed.

Usage:
    python scripts/shopify/fetch_schema_filtered.py --env production
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Set, Dict, Any

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from sgqlc.endpoint.http import HTTPEndpoint
from sgqlc.introspection import query as introspection_query


# EXCLUDE-ONLY STRATEGY: Everything is included by default, then these are removed
EXCLUDE_TYPES = {
    # App development (but keep DiscountApplication!)
    'AppInstallation', 'AppSubscription', 'AppPurchase',
    'AppCredit', 'AppUsageRecord', 'AppRevenueAttribution', 
    'AppCatalog', 'AppConnection', 'AppEdge',
    'AppFeedback', 'AppPurchaseOneTime', 'AppPurchaseStatus',
    'AppRecurringPricing', 'AppUsagePricing',
    'WebhookSubscription',
    
    # Abandoned checkouts
    'AbandonedCheckout', 'Abandonment', 'CheckoutProfile',
    
    # Blog/CMS
    'Blog', 'Article', 'Comment', 'Page', 'OnlineStorePage',
    
    # Gift cards
    'GiftCard',
    
    # Markets & Internationalization (all customers in NY)
    'Market', 'MarketLocalization', 'MarketRegion', 'MarketCatalog',
    'MarketingActivity', 'MarketingEngagement', 'MarketingEvent',
    
    # B2B / Companies
    'CompanyLocation', 'CompanyContact', 'Company',
    
    # Shopify Functions & Extensions
    'Function', 'ShopifyFunction', 'Validation',
    
    # Disputes & Chargebacks
    'ShopifyPaymentsDispute', 'ShopifyPaymentsDisputeEvidence',
    
    # Bulk operations
    'BulkOperation', 'BulkMutation',
    
    # Themes & Storefront customization
    'OnlineStoreTheme', 'ShopLocale', 'ThemeFile',
    
    # Subscriptions & Selling Plans (if you don't use subscriptions)
    'SellingPlan', 'SubscriptionContract', 'SubscriptionBilling',
    
    # Metaobjects (if you don't use them)
    'Metaobject', 'MetaobjectDefinition',
    
    # Misc admin
    'Domain', 'ShopFeatures', 'ShopPlan', 'SavedSearch',
    'ScriptTag', 'ShopResourceLimits', 'Translation',
    'PrivateMetafield', 'Channel', 'Publication', 'ResourcePublication',
    
    # Delivery customization (if you use standard shipping)
    'DeliveryCustomization', 'DeliveryProfile',
    
    # Payment customization
    'PaymentCustomization',
}


def should_keep_type(type_name: str) -> bool:
    """
    Determine if a type should be kept in the filtered schema.
    
    EXCLUDE-ONLY STRATEGY: Keep everything except excluded patterns.
    
    Args:
        type_name: Name of the type
    
    Returns:
        True if type should be kept, False otherwise
    """
    # Always keep built-in types
    if type_name.startswith('__'):
        return True
    
    # Check if it matches any exclusion pattern
    for exclude_pattern in EXCLUDE_TYPES:
        if exclude_pattern in type_name:
            return False
    
    # Default: keep everything else
    return True


def collect_referenced_types(schema: Dict[str, Any], kept_types: Set[str]) -> Set[str]:
    """
    Collect all types referenced by kept types (recursive dependency resolution).
    
    Args:
        schema: The schema dict
        kept_types: Set of type names to keep
    
    Returns:
        Set of all type names including dependencies
    """
    all_types = {t['name']: t for t in schema['types']}
    referenced = set(kept_types)
    to_process = list(kept_types)
    
    while to_process:
        type_name = to_process.pop()
        if type_name not in all_types:
            continue
        
        type_def = all_types[type_name]
        
        # Check fields
        for field in type_def.get('fields', []) or []:
            field_type = extract_type_name(field['type'])
            if field_type and field_type not in referenced:
                referenced.add(field_type)
                to_process.append(field_type)
            
            # Check field arguments
            for arg in field.get('args', []) or []:
                arg_type = extract_type_name(arg['type'])
                if arg_type and arg_type not in referenced:
                    referenced.add(arg_type)
                    to_process.append(arg_type)
        
        # Check input fields
        for field in type_def.get('inputFields', []) or []:
            field_type = extract_type_name(field['type'])
            if field_type and field_type not in referenced:
                referenced.add(field_type)
                to_process.append(field_type)
        
        # Check interfaces
        for interface in type_def.get('interfaces', []) or []:
            interface_name = interface.get('name')
            if interface_name and interface_name not in referenced:
                referenced.add(interface_name)
                to_process.append(interface_name)
        
        # Check possible types (for unions)
        for possible_type in type_def.get('possibleTypes', []) or []:
            possible_name = possible_type.get('name')
            if possible_name and possible_name not in referenced:
                referenced.add(possible_name)
                to_process.append(possible_name)
    
    return referenced


def extract_type_name(type_ref: Dict[str, Any]) -> str:
    """Extract the actual type name from a type reference (unwrapping NON_NULL and LIST)."""
    if type_ref['kind'] in ['NON_NULL', 'LIST']:
        return extract_type_name(type_ref['ofType'])
    return type_ref.get('name')


def filter_fields(type_def: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter fields from a type definition to remove references to excluded types.
    
    Args:
        type_def: Type definition dict
    
    Returns:
        Type definition with filtered fields
    """
    if not type_def.get('fields'):
        return type_def
    
    # Filter out fields that reference excluded types
    filtered_fields = []
    for field in type_def['fields']:
        field_type_name = extract_type_name(field['type'])
        if should_keep_type(field_type_name):
            filtered_fields.append(field)
    
    return {
        **type_def,
        'fields': filtered_fields
    }


def filter_schema(schema_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter schema to exclude specified types.
    
    Args:
        schema_data: Full schema introspection result
    
    Returns:
        Filtered schema
    """
    schema = schema_data['__schema']
    
    # Step 1: Filter fields from Query and Mutation types first
    # This prevents excluded types from being pulled back in via dependencies
    filtered_types_initial = []
    for type_def in schema['types']:
        type_name = type_def['name']
        
        # For Query and Mutation, filter their fields
        if type_name in ['QueryRoot', 'Mutation', 'Subscription']:
            filtered_types_initial.append(filter_fields(type_def))
        else:
            filtered_types_initial.append(type_def)
    
    # Step 2: Identify types to keep (everything except excluded)
    kept_types = set()
    excluded_count = 0
    
    for type_def in filtered_types_initial:
        type_name = type_def['name']
        
        if should_keep_type(type_name):
            kept_types.add(type_name)
        else:
            excluded_count += 1
    
    print(f"📋 Types after exclusion: {len(kept_types)}")
    print(f"🗑️  Excluded types: {excluded_count}")
    
    # Step 3: Collect all referenced types (dependencies)
    # Use filtered types so we don't pull in excluded types via Query/Mutation fields
    temp_schema = {'types': filtered_types_initial}
    all_kept_types = collect_referenced_types(temp_schema, kept_types)
    
    print(f"📦 Total types (with dependencies): {len(all_kept_types)}")
    
    # Step 4: Filter types
    filtered_types = [
        t for t in filtered_types_initial
        if t['name'] in all_kept_types
    ]
    
    # Step 5: Create filtered schema
    filtered_schema = {
        '__schema': {
            **schema,
            'types': filtered_types
        }
    }
    
    return filtered_schema


def fetch_shopify_schema(store_id: str, access_token: str, api_version: str = "2025-01") -> dict:
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
    
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"📄 Loaded environment from: {env_path}")
    
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
        store_id = (
            os.getenv("SHOPIFY_DEV_STORE_ID") or
            os.getenv("SHOPIFY_DEV_STORE")
        )
        token = os.getenv("SHOPIFY_DEV_TOKEN")
    
    if not store_id or not token:
        print("❌ Missing Shopify credentials in environment", file=sys.stderr)
        sys.exit(1)
    
    return store_id, token


def main():
    parser = argparse.ArgumentParser(
        description="Fetch filtered Shopify GraphQL schema (exclude-only strategy)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch filtered schema from production
  python scripts/shopify/fetch_schema_filtered.py --env production
  
  # Custom output path
  python scripts/shopify/fetch_schema_filtered.py --env production --output custom_schema.json
  
  # After fetching, generate Python types:
  sgqlc-codegen schema shopify_schema_filtered.json shopify_schema.py
  
Customization:
  Edit EXCLUDE_TYPES in this script to control what gets excluded.
  Everything else is included by default.
        """
    )
    
    parser.add_argument(
        '--env',
        choices=['production', 'staging', 'development'],
        default='production',
        help='Environment to load credentials from (default: production)'
    )
    parser.add_argument(
        '--api-version',
        default='2025-01',
        help='Shopify API version (default: 2025-01)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('shopify_schema_filtered.json'),
        help='Output path for filtered schema JSON (default: shopify_schema_filtered.json)'
    )
    
    args = parser.parse_args()
    
    # Get credentials
    store_id, token = load_from_env(args.env)
    
    # Fetch full schema
    schema_data = fetch_shopify_schema(store_id, token, args.api_version)
    
    # Filter schema
    print("\n🔧 Filtering schema (exclude-only strategy)...")
    filtered_schema = filter_schema(schema_data)
    
    # Save to file
    save_schema(filtered_schema, args.output)
    
    print("\n✨ Done! Next steps:")
    print(f"   1. Generate Python types:")
    print(f"      sgqlc-codegen schema {args.output} shopify_schema.py")
    print(f"   2. Review the generated file - it should be much smaller!")
    print(f"   3. Edit EXCLUDE_TYPES in this script to adjust what's excluded")


if __name__ == "__main__":
    main()
