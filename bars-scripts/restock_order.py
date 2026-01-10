#!/usr/bin/env python3
"""
Standalone script to restock inventory for a Shopify order or product.
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, Any

# Add backend to Python path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from rich.console import Console

import inventory_utils


console = Console()


def restock_inventory(order_num: str, config: Dict[str, Any]) -> int:
    """
    Restock inventory for an order or product.
    Note: This function does not prompt for confirmation. It should be called
    from cancel_order.py which handles the prompt.
    Returns 0 if restock completed/skipped, 1 on error.
    """
    console.print()
    
    # Fetch order line items
    try:
        line_items_result = inventory_utils.fetch_order_line_items(order_num, config)
        
        if "error" in line_items_result or "errors" in line_items_result:
            console.print("[red]Error fetching line items for restocking.[/red]")
            return 1
        
        orders_data = line_items_result.get('data', {}).get('orders', {}).get('edges', [])
        if not orders_data:
            console.print("[yellow]No line items found.[/yellow]")
            return 1
        
        line_items_edges = orders_data[0]['node'].get('lineItems', {}).get('edges', [])
        line_items = [edge['node'] for edge in line_items_edges]
        
        if not line_items:
            console.print("[yellow]No line items found to restock.[/yellow]")
            return 0
        
        # Prompt for restock selection
        restock_list = inventory_utils.prompt_restock_selection(line_items, config, console)
        
        if not restock_list:
            console.print("[dim]No inventory changes made.[/dim]\n")
            return 0
        
        # Process restocking
        console.print("[cyan]Processing inventory adjustments...[/cyan]\n")
        
        success_count = 0
        failure_count = 0
        
        for variant_id, inventory_item_id, quantity in restock_list:
            result = inventory_utils.update_variant_inventory(
                variant_id, inventory_item_id, quantity, config
            )
            
            if result.get("success"):
                console.print(f"  [green]✓ Restocked +{quantity} units[/green]")
                success_count += 1
            else:
                error_msg = result.get("error") or result.get("errors", "Unknown error")
                console.print(f"  [red]✗ Restock failed: {error_msg}[/red]")
                failure_count += 1
        
        console.print()
        
        # Summary
        if success_count > 0:
            console.print(f"[green]✓ Successfully restocked {success_count} variant(s)[/green]")
        if failure_count > 0:
            console.print(f"[yellow]⚠️  Failed to restock {failure_count} variant(s)[/yellow]")
        
        console.print()
        
        return 0 if failure_count == 0 else 1
        
    except ImportError:
        console.print("[red]Error: inventory_utils module not found.[/red]")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Restock inventory for a Shopify order"
    )
    parser.add_argument(
        "order_number",
        help="5-digit order number (with or without # prefix)"
    )
    parser.add_argument(
        "--env",
        choices=["development", "staging", "production"],
        default="production",
        help="Environment to use (default: production)"
    )
    
    args = parser.parse_args()
    
    try:
        # Setup - use shared_utils to avoid circular dependency
        import shared_utils
        shared_utils.load_environment(args.env)
        config = shared_utils.get_shopify_config(args.env)
        
        # Clean order number
        order_num = args.order_number.strip().lstrip('#')
        
        # Execute restock (no prompt - should be called from cancel_order.py)
        return restock_inventory(order_num, config)
        
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Restock cancelled by user.[/yellow]\n")
        return 0
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

