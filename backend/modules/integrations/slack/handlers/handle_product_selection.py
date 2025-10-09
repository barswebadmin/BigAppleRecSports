from typing import Dict, Any
import logging

from modules.products import ProductsService

logger = logging.getLogger("slack product selection logger")

def handle_product_selection(action: Dict[str, Any]) -> Dict[str, Any]:
    """Handle product selection from dropdown menu."""
    logger.info(f"Handling product selection: {action}")
    
    try:
        # Get the selected product ID from the action
        selected_product_id = action.get("selected_option", {}).get("value", "")
        
        if not selected_product_id:
            return {
                "response_type": "ephemeral",
                "text": "❌ No product selected"
            }
        
        # Fetch product details from Shopify
        products_service = ProductsService()
        
        # Get recent products to find the selected one
        recent_products_response = products_service.get_recent_products()
        recent_products = recent_products_response.data if recent_products_response.data else {}
        products_list = recent_products.get("products", {}).get("nodes", [])
        
        # Find the selected product
        selected_product = None
        for product in products_list:
            if product.get("id") == selected_product_id:
                selected_product = product
                break
        
        if not selected_product:
            return {
                "response_type": "ephemeral",
                "text": "❌ Product not found"
            }
        
        # Build variant information
        variants = selected_product.get("variants", {}).get("edges", [])
        variant_text = "📦 *Product Variants:*\n\n"
        
        for variant_edge in variants:
            variant = variant_edge.get("node", {})
            variant_title = variant.get("title", "Unknown Variant")
            inventory_quantity = variant.get("inventoryQuantity", 0)
            
            # Color code based on inventory
            if inventory_quantity > 0:
                status_emoji = "🟢"
            elif inventory_quantity == 0:
                status_emoji = "🟡"
            else:
                status_emoji = "🔴"
            
            variant_text += f"{status_emoji} *{variant_title}*: {inventory_quantity} units\n"
        
        return {
            "response_type": "ephemeral",
            "text": f"📦 *{selected_product.get('title', 'Unknown Product')}*",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"📦 *{selected_product.get('title', 'Unknown Product')}*\n\n{variant_text}"
                    }
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"Error handling product selection: {e}")
        return {
            "response_type": "ephemeral",
            "text": f"❌ Error loading product details: {str(e)}"
        }

