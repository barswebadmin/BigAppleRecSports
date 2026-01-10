#!/usr/bin/env python3
"""
Fetch Shopify page or theme template content.

Usage:
    shopify-get-page contact
    shopify-get-page --theme 134424232030 --asset templates/page.about-us-2.json
    shopify-get-page --page contact --output json
"""

import os
import sys
import json
import argparse
import requests
from typing import Optional, Dict, Any
from pathlib import Path

# Add bars-scripts to path for shared utilities
sys.path.insert(0, str(Path(__file__).parent))

from shared_utils import load_environment, get_shopify_config


def get_ssl_verification():
    """Get SSL verification setting (same as shared_utils pattern)."""
    ssl_cert_file = os.getenv('SSL_CERT_FILE', '/opt/homebrew/etc/openssl@3/cert.pem')
    return ssl_cert_file if os.path.exists(ssl_cert_file) else True


def fetch_page(page_handle: str, output_format: str = "text", environment: str = "production") -> Optional[Dict[str, Any]]:
    """
    Fetch a Shopify page by handle.
    
    Args:
        page_handle: The page handle (e.g., "contact", "about")
        output_format: Output format ("text", "json", "html")
        environment: Environment to use (production, staging, dev)
    
    Returns:
        Page data dictionary or None if not found
    """
    load_environment(environment)
    shopify_config = get_shopify_config(environment)
    
    store_url = f"https://{shopify_config['store_id']}.myshopify.com"
    api_url = f"{store_url}/admin/api/2024-10/pages.json"
    
    headers = {
        "X-Shopify-Access-Token": shopify_config['token'],
        "Content-Type": "application/json"
    }
    
    verify_ssl = get_ssl_verification()
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10, verify=verify_ssl)
        response.raise_for_status()
        
        pages_data = response.json()
        pages = pages_data.get("pages", [])
        
        # Find page by handle
        page = next((p for p in pages if p.get("handle") == page_handle), None)
        
        if not page:
            print(f"❌ Page '{page_handle}' not found", file=sys.stderr)
            print(f"\nAvailable pages:", file=sys.stderr)
            for p in pages:
                print(f"  - {p.get('handle')} (ID: {p.get('id')})", file=sys.stderr)
            return None
        
        if output_format == "json":
            print(json.dumps(page, indent=2))
        elif output_format == "html":
            print(page.get("body_html", ""))
        else:
            print(f"📄 Page: {page.get('title')}")
            print(f"🔗 Handle: {page.get('handle')}")
            print(f"🆔 ID: {page.get('id')}")
            print(f"📝 Template: {page.get('template_suffix', 'default')}")
            print(f"\n{'='*80}")
            print(page.get("body_html", ""))
            print(f"{'='*80}")
        
        return page
        
    except requests.RequestException as e:
        print(f"❌ Error fetching page: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"\n📋 API Response:", file=sys.stderr)
                print(json.dumps(error_data, indent=2), file=sys.stderr)
            except (ValueError, AttributeError):
                print(f"\n📋 Response Text: {e.response.text}", file=sys.stderr)
        return None


def fetch_theme_asset(theme_id: str, asset_key: str, output_format: str = "text", environment: str = "production") -> Optional[str]:
    """
    Fetch a theme asset (template, section, snippet).
    
    Args:
        theme_id: The theme ID
        asset_key: The asset key (e.g., "templates/page.about-us-2.json")
        output_format: Output format ("text", "json")
        environment: Environment to use (production, staging, dev)
    
    Returns:
        Asset content or None if not found
    """
    load_environment(environment)
    shopify_config = get_shopify_config(environment)
    
    store_url = f"https://{shopify_config['store_id']}.myshopify.com"
    api_url = f"{store_url}/admin/api/2024-10/themes/{theme_id}/assets.json"
    
    headers = {
        "X-Shopify-Access-Token": shopify_config['token'],
        "Content-Type": "application/json"
    }
    
    params = {"asset[key]": asset_key}
    verify_ssl = get_ssl_verification()
    
    try:
        response = requests.get(api_url, headers=headers, params=params, timeout=10, verify=verify_ssl)
        response.raise_for_status()
        
        asset_data = response.json()
        asset = asset_data.get("asset")
        
        if not asset:
            print(f"❌ Asset '{asset_key}' not found in theme {theme_id}", file=sys.stderr)
            return None
        
        content = asset.get("value") or asset.get("attachment")
        
        if output_format == "json":
            if asset_key.endswith(".json"):
                try:
                    parsed = json.loads(content)
                    print(json.dumps(parsed, indent=2))
                except json.JSONDecodeError:
                    print(content)
            else:
                print(json.dumps(asset, indent=2))
        else:
            print(f"🎨 Theme: {theme_id}")
            print(f"📄 Asset: {asset_key}")
            print(f"📦 Size: {asset.get('size', 'unknown')} bytes")
            print(f"\n{'='*80}")
            print(content)
            print(f"{'='*80}")
        
        return content
        
    except requests.RequestException as e:
        print(f"❌ Error fetching theme asset: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"\n📋 API Response:", file=sys.stderr)
                print(json.dumps(error_data, indent=2), file=sys.stderr)
            except (ValueError, AttributeError):
                print(f"\n📋 Response Text: {e.response.text}", file=sys.stderr)
        return None


def list_theme_assets(theme_id: str, filter_pattern: Optional[str] = None, environment: str = "production"):
    """
    List all assets in a theme.
    
    Args:
        theme_id: The theme ID
        filter_pattern: Optional pattern to filter assets (e.g., "template", "about")
        environment: Environment to use (production, staging, dev)
    """
    load_environment(environment)
    shopify_config = get_shopify_config(environment)
    
    store_url = f"https://{shopify_config['store_id']}.myshopify.com"
    api_url = f"{store_url}/admin/api/2024-10/themes/{theme_id}/assets.json"
    
    headers = {
        "X-Shopify-Access-Token": shopify_config['token'],
        "Content-Type": "application/json"
    }
    
    verify_ssl = get_ssl_verification()
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10, verify=verify_ssl)
        response.raise_for_status()
        
        assets_data = response.json()
        assets = assets_data.get("assets", [])
        
        if filter_pattern:
            assets = [a for a in assets if filter_pattern.lower() in a.get("key", "").lower()]
        
        print(f"📦 Theme {theme_id} Assets ({len(assets)} total):\n")
        
        # Group by type
        templates = [a for a in assets if a.get("key", "").startswith("templates/")]
        sections = [a for a in assets if a.get("key", "").startswith("sections/")]
        snippets = [a for a in assets if a.get("key", "").startswith("snippets/")]
        
        if templates:
            print("📝 Templates:")
            for asset in sorted(templates, key=lambda a: a.get("key", "")):
                print(f"  - {asset.get('key')}")
        
        if sections:
            print("\n📐 Sections:")
            for asset in sorted(sections, key=lambda a: a.get("key", "")):
                print(f"  - {asset.get('key')}")
        
        if snippets:
            print("\n✂️  Snippets:")
            for asset in sorted(snippets, key=lambda a: a.get("key", "")):
                print(f"  - {asset.get('key')}")
        
    except requests.RequestException as e:
        print(f"❌ Error listing theme assets: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"\n📋 API Response:", file=sys.stderr)
                print(json.dumps(error_data, indent=2), file=sys.stderr)
            except (ValueError, AttributeError):
                print(f"\n📋 Response Text: {e.response.text}", file=sys.stderr)


def extract_leadership_positions(theme_id: str, asset_key: str = "templates/page.template-about-us-2.json", environment: str = "production", raw: bool = False):
    """
    Extract leadership position titles from the About Us page template.
    
    Args:
        theme_id: The Shopify theme ID
        asset_key: The template asset key (defaults to About Us template)
        environment: Environment to use (production, staging, dev)
        raw: If True, print raw API response instead of extracted positions
    """
    load_environment(environment)
    shopify_config = get_shopify_config(environment)
    
    store_url = f"https://{shopify_config['store_id']}.myshopify.com"
    api_url = f"{store_url}/admin/api/2024-10/themes/{theme_id}/assets.json"
    
    headers = {
        "X-Shopify-Access-Token": shopify_config['token'],
        "Content-Type": "application/json"
    }
    params = {"asset[key]": asset_key}
    
    verify_ssl = get_ssl_verification()
    
    try:
        response = requests.get(api_url, headers=headers, params=params, verify=verify_ssl, timeout=10)
        response.raise_for_status()
        
        asset = response.json().get('asset', {})
        content = asset.get('value', '')
        
        if not content:
            print(f"❌ Asset '{asset_key}' has no content", file=sys.stderr)
            return
        
        template_data = json.loads(content)
        
        # If raw mode, just print the pretty JSON and exit
        if raw:
            print(f"📄 Raw API Response for: {asset_key}\n")
            print(f"{'='*80}\n")
            print(json.dumps(template_data, indent=2))
            print(f"\n{'='*80}")
            return
        
        # Otherwise, extract and display positions
        print(f"🎯 Extracting leadership positions from: {asset_key}\n")
        print(f"{'='*80}\n")
        
        positions = []
        
        if 'sections' in template_data:
            for section_id, section_data in template_data['sections'].items():
                if 'blocks' in section_data:
                    for block_id, block_data in section_data['blocks'].items():
                        if block_data.get('type') == 'Text':
                            settings = block_data.get('settings', {})
                            name = settings.get('text', '').strip()
                            position = settings.get('description', '').strip()
                            
                            if position and name:
                                positions.append((name, position))
        
        if positions:
            unique_positions = sorted(set([p[1] for p in positions]), key=lambda x: x.lower())
            
            print(f"📊 Found {len(positions)} total leadership entries")
            print(f"📊 Found {len(unique_positions)} unique position titles\n")
            print(f"{'='*80}\n")
            
            for idx, position in enumerate(unique_positions, 1):
                print(f"{idx:3}. {position}")
            
            print(f"\n{'='*80}")
        else:
            print(f"⚠️  No leadership positions found in template", file=sys.stderr)
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error fetching theme asset: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                print("\n📋 API Response:", file=sys.stderr)
                print(json.dumps(error_details, indent=2), file=sys.stderr)
            except json.JSONDecodeError:
                print(f"\n📋 Raw API Response: {e.response.text}", file=sys.stderr)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing template JSON: {e}", file=sys.stderr)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Shopify page or theme template content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch contact page
  shopify-get-page contact
  
  # Fetch page as JSON
  shopify-get-page --page contact --output json
  
  # Fetch theme template
  shopify-get-page --theme 134424232030 --asset templates/page.about-us-2.json
  
  # List all theme assets
  shopify-get-page --theme 134424232030 --list
  
  # List theme assets matching pattern
  shopify-get-page --theme 134424232030 --list --filter about
  
  # Extract leadership position titles from About Us page
  shopify-get-page --extract-positions
  shopify-get-page --extract-positions --theme 134424232030
  
  # Show raw API response (for debugging/analysis)
  shopify-get-page --extract-positions-raw
  shopify-get-page --extract-positions-raw > about_page_raw.json
"""
    )
    
    parser.add_argument(
        "page_handle",
        nargs="?",
        help="Page handle (e.g., 'contact', 'about')"
    )
    parser.add_argument(
        "--page",
        help="Page handle (alternative to positional arg)"
    )
    parser.add_argument(
        "--theme",
        help="Theme ID (e.g., 134424232030)"
    )
    parser.add_argument(
        "--asset",
        help="Theme asset key (e.g., 'templates/page.about-us-2.json')"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all assets in theme"
    )
    parser.add_argument(
        "--filter",
        help="Filter pattern for listing assets"
    )
    parser.add_argument(
        "--output",
        choices=["text", "json", "html"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--env",
        "--environment",
        choices=["production", "staging", "dev"],
        default="production",
        help="Environment (default: production)"
    )
    parser.add_argument(
        "--extract-positions",
        action="store_true",
        help="Extract leadership position titles from About Us template"
    )
    parser.add_argument(
        "--extract-positions-raw",
        action="store_true",
        help="Print raw API response (pretty JSON) instead of extracted positions"
    )
    
    args = parser.parse_args()
    
    # Determine what to fetch
    if args.extract_positions or args.extract_positions_raw:
        # Default to production theme if not specified
        theme_id = args.theme or "134424232030"
        asset_key = args.asset or "templates/page.template-about-us-2.json"
        extract_leadership_positions(theme_id, asset_key, args.env, raw=args.extract_positions_raw)
    elif args.theme and args.list:
        list_theme_assets(args.theme, args.filter, args.env)
    elif args.theme and args.asset:
        fetch_theme_asset(args.theme, args.asset, args.output, args.env)
    elif args.page or args.page_handle:
        page_handle = args.page or args.page_handle
        fetch_page(page_handle, args.output, args.env)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

