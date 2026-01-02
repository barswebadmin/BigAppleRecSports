"""
Shared inventory utilities for order management scripts.
"""

import os
import requests
from typing import Dict, Any, List, Optional, Tuple
from rich.console import Console
from rich.table import Table


def fetch_order_line_items(order_number: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch order line items with variant details."""
    order_num = order_number.strip().lstrip('#')
    
    query = """
    query FetchOrderLineItems($q: String!) {
        orders(first: 1, query: $q) {
            edges {
                node {
                    id
                    name
                    lineItems(first: 50) {
                        edges {
                            node {
                                id
                                name
                                title
                                quantity
                                variant {
                                    id
                                    title
                                    displayName
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    payload = {
        "query": query,
        "variables": {"q": f"name:#{order_num}"}
    }
    
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


def fetch_all_product_variants(product_id: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch all variants for a product."""
    query = """
    query GetProductVariants($productId: ID!) {
        product(id: $productId) {
            id
            title
            variants(first: 100) {
                edges {
                    node {
                        id
                        title
                        displayName
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
        "variables": {"productId": product_id}
    }
    
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
        result = response.json()
        
        if "errors" in result:
            return []
        
        product_data = result.get('data', {}).get('product', {})
        variants_edges = product_data.get('variants', {}).get('edges', [])
        
        variants = []
        for edge in variants_edges:
            node = edge.get('node', {})
            variants.append({
                'id': node.get('id'),
                'title': node.get('title') or node.get('displayName', 'Unknown'),
                'inventory_quantity': node.get('inventoryQuantity'),
                'inventory_item_id': node.get('inventoryItem', {}).get('id')
            })
        
        return variants
        
    except requests.exceptions.RequestException as e:
        return []


def get_inventory_item_id(variant_id: str, config: Dict[str, Any]) -> Optional[str]:
    """Get inventory item ID for a variant."""
    query = """
    query GetInventoryItemId($variantId: ID!) {
        productVariant(id: $variantId) {
            inventoryItem {
                id
            }
        }
    }
    """
    
    payload = {
        "query": query,
        "variables": {"variantId": variant_id}
    }
    
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
        result = response.json()
        
        if "errors" in result:
            return None
        
        variant_data = result.get('data', {}).get('productVariant', {})
        inventory_item = variant_data.get('inventoryItem', {})
        return inventory_item.get('id')
        
    except requests.exceptions.RequestException:
        return None


def update_variant_inventory(
    variant_id: str,
    inventory_item_id: str,
    quantity: int,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Update inventory for a variant."""
    # Get location ID (using first available location)
    location_query = """
    query {
        locations(first: 1) {
            edges {
                node {
                    id
                }
            }
        }
    }
    """
    
    ssl_cert_file = os.getenv('SSL_CERT_FILE', '/opt/homebrew/etc/openssl@3/cert.pem')
    verify_ssl = ssl_cert_file if os.path.exists(ssl_cert_file) else True
    
    try:
        response = requests.post(
            config["graphql_url"],
            json={"query": location_query},
            headers=config["headers"],
            timeout=30,
            verify=verify_ssl
        )
        response.raise_for_status()
        location_result = response.json()
        
        locations = location_result.get('data', {}).get('locations', {}).get('edges', [])
        if not locations:
            return {"success": False, "error": "No locations found"}
        
        location_id = locations[0]['node']['id']
        
        # Update inventory
        mutation = """
        mutation InventoryAdjustQuantities($input: InventoryAdjustQuantitiesInput!) {
            inventoryAdjustQuantities(input: $input) {
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        payload = {
            "query": mutation,
            "variables": {
                "input": {
                    "reason": "correction",
                    "name": "available",
                    "changes": [
                        {
                            "delta": quantity,
                            "inventoryItemId": inventory_item_id,
                            "locationId": location_id
                        }
                    ]
                }
            }
        }
        
        response = requests.post(
            config["graphql_url"],
            json=payload,
            headers=config["headers"],
            timeout=30,
            verify=verify_ssl
        )
        response.raise_for_status()
        result = response.json()
        
        if "errors" in result:
            return {"success": False, "errors": result["errors"]}
        
        mutation_data = result.get('data', {}).get('inventoryAdjustQuantities', {})
        user_errors = mutation_data.get('userErrors', [])
        
        if user_errors:
            return {"success": False, "errors": user_errors}
        
        return {"success": True, "data": mutation_data}
        
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


def prompt_restock_selection(
    line_items: List[Dict[str, Any]],
    config: Dict[str, Any],
    console: Console
) -> List[Tuple[str, str, int]]:
    """
    Display product variants and prompt user for restock selection.
    
    Returns:
        List of tuples: (variant_id, inventory_item_id, quantity_to_restock)
    """
    if not line_items:
        return []
    
    console.print("\n[bold]📦 Product Variants - Inventory Status[/bold]\n")
    
    # Extract product ID from first line item
    first_item = line_items[0]
    variant = first_item.get('variant', {})
    if not variant or not variant.get('id'):
        console.print("[dim]No variants found to restock.[/dim]\n")
        return []
    
    variant_id = variant['id']
    
    # Get product ID from variant
    product_query = """
    query GetProductFromVariant($variantId: ID!) {
        productVariant(id: $variantId) {
            product {
                id
            }
        }
    }
    """
    
    payload = {"query": product_query, "variables": {"variantId": variant_id}}
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
        result = response.json()
        
        if "errors" in result:
            console.print("[red]Error fetching product information.[/red]")
            return []
        
        variant_data = result.get('data', {}).get('productVariant', {})
        product = variant_data.get('product', {})
        product_id = product.get('id')
        
        if not product_id:
            console.print("[red]Could not find product ID.[/red]")
            return []
        
        # Fetch all variants for the product
        all_variants = fetch_all_product_variants(product_id, config)
        
        if not all_variants:
            console.print("[yellow]No variants found for this product.[/yellow]")
            return []
        
        # Display variants table
        variants_table = Table(title="Available Variants", show_header=True)
        variants_table.add_column("#", justify="center")
        variants_table.add_column("Variant Name")
        variants_table.add_column("Current Inventory", justify="right")
        
        for i, variant in enumerate(all_variants, 1):
            inv_qty = variant.get('inventory_quantity', 0)
            variants_table.add_row(
                str(i),
                variant.get('title', 'Unknown'),
                str(inv_qty) if inv_qty is not None else "N/A"
            )
        
        console.print(variants_table)
        console.print()
        
        # Prompt for selection
        restock_list = []
        
        while True:
            selection = input("Enter variant number to restock (or 'done' to finish): ").strip().lower()
            
            if selection == 'done':
                break
            
            try:
                variant_index = int(selection) - 1
                if 0 <= variant_index < len(all_variants):
                    selected_variant = all_variants[variant_index]
                    
                    # Prompt for quantity (commented out - defaulting to 1)
                    # quantity_input = input(f"Enter quantity to restock for '{selected_variant['title']}': ").strip()
                    # try:
                    #     quantity = int(quantity_input)
                    #     if quantity > 0:
                    #         inventory_item_id = selected_variant.get('inventory_item_id')
                    #         if inventory_item_id:
                    #             restock_list.append((selected_variant['id'], inventory_item_id, quantity))
                    #             console.print(f"[green]✓ Added {quantity} units for {selected_variant['title']}[/green]")
                    #         else:
                    #             console.print("[red]Error: No inventory item ID found for this variant.[/red]")
                    #     else:
                    #         console.print("[red]Quantity must be greater than 0.[/red]")
                    # except ValueError:
                    #     console.print("[red]Invalid quantity. Please enter a number.[/red]")
                    
                    quantity = 1
                    inventory_item_id = selected_variant.get('inventory_item_id')
                    if inventory_item_id:
                        restock_list.append((selected_variant['id'], inventory_item_id, quantity))
                        console.print(f"[green]✓ Added {quantity} unit for {selected_variant['title']}[/green]")
                    else:
                        console.print("[red]Error: No inventory item ID found for this variant.[/red]")
                else:
                    console.print(f"[red]Invalid selection. Enter a number between 1 and {len(all_variants)}.[/red]")
            except ValueError:
                console.print("[red]Invalid input. Enter a number or 'done'.[/red]")
        
        return restock_list
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        return []

