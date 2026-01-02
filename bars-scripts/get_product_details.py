#!/usr/bin/env python3
"""
Standalone script to fetch product details from Shopify by product ID or name.
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, Any

# Add backend to Python path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Import shared utilities that use project code
import shared_utils


console = Console()


def fetch_product_by_id(product_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch product by ID."""
    product_gid = f"gid://shopify/Product/{product_id}"
    
    query = """
    query GetProductById($id: ID!) {
        product(id: $id) {
            id
            title
            handle
            status
            description
            variants(first: 100) {
                edges {
                    node {
                        id
                        title
                        displayName
                        price
                        inventoryQuantity
                        inventoryItem {
                            id
                        }
                    }
                }
            }
        }
    }
    """
    
    payload = {
        "query": query,
        "variables": {"id": product_gid}
    }
    
    import os
    import requests
    
    ssl_cert_file = os.getenv('SSL_CERT_FILE', '/opt/homebrew/etc/openssl@3/cert.pem')
    verify_ssl = ssl_cert_file if os.path.exists(ssl_cert_file) else True
    
    try:
        response = requests.post(
            config["graphql_url"],
            json=payload,
            headers=config["headers"],
            timeout=30,
            verify=verify_ssl
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="Fetch product details from Shopify by ID or name"
    )
    parser.add_argument(
        "identifier",
        help="Product ID (numeric) or product name (text)"
    )
    parser.add_argument(
        "--env",
        choices=["development", "staging", "production"],
        default="production",
        help="Environment to use (default: production)"
    )
    
    args = parser.parse_args()
    
    try:
        # Setup
        shared_utils.load_environment(args.env)
        config = shared_utils.get_shopify_config(args.env)
        
        identifier = args.identifier.strip()
        
        # Check if identifier is numeric
        if identifier.isdigit():
            # Fetch by ID
            console.print(f"\n[cyan]Fetching product by ID: {identifier}...[/cyan]\n")
            result = fetch_product_by_id(identifier, config)
            
            if "error" in result:
                console.print(f"[red]Error: {result['error']}[/red]")
                return 1
            
            if "errors" in result:
                console.print(f"[red]GraphQL Errors:[/red]")
                for error in result["errors"]:
                    console.print(f"  - {error.get('message', str(error))}")
                return 1
            
            product = result.get('data', {}).get('product')
            if not product:
                console.print(f"[yellow]No product found with ID: {identifier}[/yellow]")
                return 1
            
            # Display product
            console.print(Panel(
                f"[bold cyan]Product Details[/bold cyan]\n"
                f"Title: {product.get('title', 'N/A')}\n"
                f"Status: {product.get('status', 'N/A')}\n"
                f"Handle: {product.get('handle', 'N/A')}",
                border_style="cyan"
            ))
            console.print()
            
            # Display variants
            variants = product.get('variants', {}).get('edges', [])
            if variants:
                variants_table = Table(title="Variants", show_header=True)
                variants_table.add_column("Variant")
                variants_table.add_column("Price", justify="right")
                variants_table.add_column("Inventory", justify="right")
                
                for edge in variants:
                    variant = edge['node']
                    variants_table.add_row(
                        variant.get('title', 'N/A'),
                        f"${float(variant.get('price', 0)):.2f}",
                        str(variant.get('inventoryQuantity', 0))
                    )
                
                console.print(variants_table)
                console.print()
        else:
            console.print(f"[yellow]Product name search not yet implemented. Please use numeric product ID.[/yellow]")
            return 1
        
        return 0
        
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Cancelled by user.[/yellow]\n")
        return 0
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

