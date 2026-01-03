#!/usr/bin/env python3
"""
Fetch Shopify page or theme template content.

Usage:
    shopify-get-page contact
    shopify-get-page --theme 134424232030 --asset templates/page.about-us-2.json
    shopify-get-page --page contact --output json
"""

import sys
import json
import argparse
import requests
from typing import Optional, Dict, Any
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from config import config


def fetch_page(page_handle: str, output_format: str = "text") -> Optional[Dict[str, Any]]:
    """
    Fetch a Shopify page by handle.
    
    Args:
        page_handle: The page handle (e.g., "contact", "about")
        output_format: Output format ("text", "json", "html")
    
    Returns:
        Page data dictionary or None if not found
    """
    store_url = f"https://{config.Shopify.store_id}.myshopify.com"
    api_url = f"{store_url}/admin/api/2024-10/pages.json"
    
    headers = {
        "X-Shopify-Access-Token": config.Shopify.token,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
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
        return None


def fetch_theme_asset(theme_id: str, asset_key: str, output_format: str = "text") -> Optional[str]:
    """
    Fetch a theme asset (template, section, snippet).
    
    Args:
        theme_id: The theme ID
        asset_key: The asset key (e.g., "templates/page.about-us-2.json")
        output_format: Output format ("text", "json")
    
    Returns:
        Asset content or None if not found
    """
    store_url = f"https://{config.Shopify.store_id}.myshopify.com"
    api_url = f"{store_url}/admin/api/2024-10/themes/{theme_id}/assets.json"
    
    headers = {
        "X-Shopify-Access-Token": config.Shopify.token,
        "Content-Type": "application/json"
    }
    
    params = {"asset[key]": asset_key}
    
    try:
        response = requests.get(api_url, headers=headers, params=params, timeout=10)
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
        return None


def list_theme_assets(theme_id: str, filter_pattern: Optional[str] = None):
    """
    List all assets in a theme.
    
    Args:
        theme_id: The theme ID
        filter_pattern: Optional pattern to filter assets (e.g., "template", "about")
    """
    store_url = f"https://{config.Shopify.store_id}.myshopify.com"
    api_url = f"{store_url}/admin/api/2024-10/themes/{theme_id}/assets.json"
    
    headers = {
        "X-Shopify-Access-Token": config.Shopify.token,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
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
    
    args = parser.parse_args()
    
    # Determine what to fetch
    if args.theme and args.list:
        list_theme_assets(args.theme, args.filter)
    elif args.theme and args.asset:
        fetch_theme_asset(args.theme, args.asset, args.output)
    elif args.page or args.page_handle:
        page_handle = args.page or args.page_handle
        fetch_page(page_handle, args.output)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

