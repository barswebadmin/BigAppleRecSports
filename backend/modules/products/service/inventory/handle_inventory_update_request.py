from typing import Dict, Any
import json
import logging

from modules.products import ProductsService
from modules.integrations.slack import SlackOrchestrator

products = ProductsService()
slack = SlackOrchestrator()

logger = logging.getLogger("slack inventory update logger")

def handle_inventory_update(data: Dict[str, Any]) -> Dict[str, Any]:
    text = data.get("text", "").strip() if data.get("text", "") else ""
    user = data.get("user", {})
    channel = data.get("channel", {})
    response_url = data.get("response_url", "")
    trigger_id = data.get("trigger_id", "")

    response = products.get_recent_products()
    data = response.data if response.data else {}
    recent_products = data.get("products", {}).get("nodes", [])
    
    
    # print("=" * 80)
    
    # # Extract products from the response data
    if response.success:
        
        # Create options for the select menu
        product_options = []
        for product in recent_products:
            product_title = product.get("title", "Unknown Product")
            product_id = product.get("id", "")
            product_options.append({
                "text": {
                    "type": "plain_text",
                    "text": product_title
                },
                "value": product_id
            })
        print("📦 RECENT PRODUCTS DATA:")
        print(json.dumps(product_options, indent=2))
        
        # Create the response with InputBlock and select menu
        return {
            "response_type": "ephemeral",
            "text": f"🔧 *Update Product Inventory*",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🔧 *Update Product Inventory*\n\nTriggered by <@{user.get('id', '')}>\n\nSelect a product to view its inventory:"
                    }
                },
                {
                    "type": "input",
                    "block_id": "product_selector",
                    "element": {
                        "type": "static_select",
                        "action_id": "select_product",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Choose a product..."
                        },
                        "options": product_options
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Product"
                    }
                }
            ]
        }
    else:
        print("❌ Error getting recent products")
        print(json.dumps(response.data, indent=2))
    
   