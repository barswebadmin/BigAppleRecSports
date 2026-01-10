__version__ = "1.1.0"

import json
import traceback
from datetime import datetime
from typing import Dict, Any

from bars_common_utils.response_utils import format_response, format_error
from bars_common_utils.event_utils import validate_required_fields, parse_event_body
from bars_common_utils.request_utils import wait_until_next_minute
from bars_common_utils.shopify_utils import (
    get_inventory_item_and_quantity,
    adjust_inventory,
    update_product_title,
    get_product_tags,
    update_product_tags
)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Add inventory to a specific variant to make a product live.
    
    Expected event structure:
    {
        "productUrl": "https://09fe59-3.myshopify.com/admin/products/123456789",
        "variantGid": "gid://shopify/ProductVariant/123456789", 
        "inventoryToAdd": 10,
        "productTitle": "New Product Title" (optional)
    }
    """
    try:
        print("📦 setProductLiveByAddingInventory invoked with event:", json.dumps(event, indent=2))
        
        # Resolve required configuration
        import os
        shopify_location = os.environ.get("SHOPIFY_LOCATION_ID")
        # Token now resolved in bars_common_utils.shopify_utils via SSM; we only need location here
        print("🔑 Configuration check:")
        print(f"   SHOPIFY_LOCATION_ID exists: {bool(shopify_location)}")
        print(f"   SHOPIFY_LOCATION_ID value: {shopify_location}")
        print("   Token will be fetched from SSM: /shopify/token.admin")
        
        if not shopify_location:
            raise ValueError("SHOPIFY_LOCATION_ID environment variable is missing")

        # Parse event body if coming from API Gateway
        event_body = parse_event_body(event)
        
        # Validate required fields
        required_fields = ['productUrl', 'variantGid', 'inventoryToAdd']
        validate_required_fields(event_body, required_fields)

        product_url = event_body['productUrl']
        variant_gid = event_body['variantGid']
        inventory_to_add = event_body['inventoryToAdd']
        product_title = event_body.get('productTitle')  # Optional field
        variant_type = event_body.get('variantType', '').lower()  # Optional: for tag management

        # Validate inventoryToAdd is a positive integer
        if not isinstance(inventory_to_add, int) or inventory_to_add <= 0:
            raise ValueError("inventoryToAdd must be a positive integer")
        
        # Extract product ID from URL for potential title update
        product_id = product_url.split('/')[-1]

        # Get current inventory information for the variant
        print(f"🔍 Getting current inventory for variant: {variant_gid}")
        print(f"⏱️ Starting inventory lookup at: {datetime.now().isoformat()}")
        inventory_data = get_inventory_item_and_quantity(variant_gid)
        print(f"✅ Inventory lookup completed at: {datetime.now().isoformat()}")
        
        current_quantity = inventory_data['inventoryQuantity']
        inventory_item_id = str(inventory_data['inventoryItemId'])
        
        print(f"📊 Current inventory: {current_quantity}, Adding: {inventory_to_add}")
        
        # Add 'veteran-only' tag if first variant is veteran (before inventory adjustment)
        tags_updated = False
        if variant_type == 'vet':
            print("🏷️ First variant is veteran, adding 'veteran-only' tag")
            print(f"⏱️ Starting tag update at: {datetime.now().isoformat()}")
            try:
                current_tags = get_product_tags(product_id)
                if 'veteran-only' not in current_tags:
                    updated_tags = current_tags + ['veteran-only']
                    update_product_tags(product_id, updated_tags)
                    print(f"✅ Added 'veteran-only' tag. Updated tags: {updated_tags}")
                    tags_updated = True
                else:
                    print("ℹ️ 'veteran-only' tag already exists on product")
            except Exception as e:
                print(f"⚠️ Failed to update product tags: {e}")
                # Don't fail the entire operation if tag update fails
        
        # Wait until next minute before making inventory changes
        wait_until_next_minute()
        
        # Add the inventory FIRST
        print(f"➕ Adding {inventory_to_add} units to variant inventory")
        print(f"⏱️ Starting inventory adjustment at: {datetime.now().isoformat()}")
        adjust_inventory(inventory_item_id, inventory_to_add)
        print(f"✅ Inventory adjustment completed at: {datetime.now().isoformat()}")
        
        # Update product title AFTER inventory is successfully added
        title_updated = False
        if product_title:
            print(f"📝 Updating product title to: {product_title}")
            print(f"⏱️ Starting title update at: {datetime.now().isoformat()}")
            try:
                update_product_title(product_id, product_title)
                print(f"✅ Title update completed at: {datetime.now().isoformat()}")
                title_updated = True
            except Exception as e:
                print(f"⚠️ Failed to update product title: {e}")
                # Don't fail the entire operation if title update fails (inventory was already added)
        
        # Calculate new total
        new_total = current_quantity + inventory_to_add
        
        # Build success message
        message = f"Successfully added {inventory_to_add} units to variant"
        if title_updated:
            message += f" and updated product title to '{product_title}'"
        if tags_updated:
            message += " and added 'veteran-only' tag"
        
        return format_response(200, {
            "success": True,
            "message": message,
            "details": {
                "productUrl": product_url,
                "variantGid": variant_gid,
                "previousQuantity": current_quantity,
                "inventoryAdded": inventory_to_add,
                "newTotalQuantity": new_total,
                "inventoryItemId": inventory_item_id,
                "titleUpdated": title_updated,
                "newTitle": product_title if title_updated else None,
                "tagsUpdated": tags_updated
            }
        })

    except ValueError as e:
        # Validation errors (bad input, auth failures, etc.)
        error_msg = str(e)
        print(f"❌ Validation Error: {error_msg}")
        print("📋 Full traceback:", traceback.format_exc())
        
        if "authentication failed" in error_msg.lower() or "401" in error_msg:
            return format_error(401, f"Shopify authentication failed: {error_msg}")
        else:
            return format_error(400, f"Invalid request: {error_msg}")
    
    except Exception as e:
        # Unexpected errors
        error_msg = str(e)
        print(f"❌ Unexpected Exception: {type(e).__name__}: {error_msg}")
        print("📋 Full traceback:", traceback.format_exc())
        return format_error(500, f"Internal error: {error_msg}")
