__version__ = "1.4.0"

import json
import traceback
from typing import Dict, Any

from bars_common_utils.response_utils import format_response, format_error
from bars_common_utils.event_utils import validate_required_fields
from bars_common_utils.request_utils import wait_until_next_minute
from bars_common_utils.shopify_utils import (
    get_inventory_item_and_quantity,
    adjust_inventory,
    get_product_variants,
    get_product_tags,
    update_product_tags
)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Move inventory between variants based on the type of transfer.
    Supports:
      - Any variant type ➡ Any variant type (moves all inventory)
      - Any variant ➡ Open (consolidates inventory from all non-open variants)
    
    Uses variant GIDs only for validation - does not parse variant titles.
    """
    try:
        print("📦 MoveInventoryLambda invoked with event:", json.dumps(event, indent=2))

        required_fields = ['scheduleName', 'productUrl', 'sourceVariant', 'destinationVariant']
        validate_required_fields(event, required_fields)

        source = event['sourceVariant']
        dest = event['destinationVariant']
        source_name = source['name']
        dest_name = dest['name']
        source_gid = source['gid']
        dest_gid = dest['gid']
        source_type = source.get('type', '').lower()
        dest_type = dest.get('type', '').lower()
        num_eligible_veterans = event.get('numEligibleVeterans', 0)
        
        product_id = event['productUrl'].split('/')[-1]
        tags_updated = False
        
        if dest_type in ['vet', 'early', 'wtnb', 'bipoc']:
            # 🧠 Case 1: reg1 ➡ reg2 logic (move all inventory from source to destination)
            source_data = get_inventory_item_and_quantity(source_gid)
            dest_data = get_inventory_item_and_quantity(dest_gid)

            source_qty = source_data['inventoryQuantity']
            source_id = str(source_data['inventoryItemId'])
            dest_id = str(dest_data['inventoryItemId'])

            print(f"📊 Moving ALL inventory from {source_name} → {dest_name}: {source_qty} units")
            if source_qty <= 0:
                raise ValueError(f"No inventory to move from {source_name}.")

            wait_until_next_minute()
            adjust_inventory(source_id, -source_qty)
            adjust_inventory(dest_id, source_qty)
            
            # Remove 'veteran-only' tag if source variant was veteran and now has 0 inventory
            if source_type == 'vet':
                # Check if veteran variant still has inventory after the move
                source_data_after = get_inventory_item_and_quantity(source_gid)
                remaining_qty = source_data_after['inventoryQuantity']
                print(f"🔍 Veteran variant inventory after move: {remaining_qty}")
                
                if remaining_qty == 0:
                    print("🏷️ Veteran variant has 0 inventory, removing 'veteran-only' tag")
                    try:
                        current_tags = get_product_tags(product_id)
                        if 'veteran-only' in current_tags:
                            updated_tags = [tag for tag in current_tags if tag != 'veteran-only']
                            update_product_tags(product_id, updated_tags)
                            print(f"✅ Removed 'veteran-only' tag. Updated tags: {updated_tags}")
                            tags_updated = True
                        else:
                            print("ℹ️ 'veteran-only' tag not found on product")
                    except Exception as e:
                        print(f"⚠️ Failed to update product tags: {e}")
                        # Don't fail the entire operation if tag update fails
                else:
                    print(f"ℹ️ Veteran variant still has {remaining_qty} inventory, keeping 'veteran-only' tag")

            return format_response(200, {
                "success": True,
                "message": f"Moved all {source_qty} units from {source_name} to {dest_name}" + (" and removed 'veteran-only' tag" if tags_updated else ""),
                "details": {
                    "from": f"{source_name} ({source_gid})",
                    "to": f"{dest_name} ({dest_gid})",
                    "amountMoved": source_qty
                }
            })
            
        elif dest_type == 'open':
            # 🧠 Case 2: Consolidate from all non-open variants ➡ open
            # Uses variant GIDs only - no title validation
            product_id = event['productUrl'].split('/')[-1]
            result = get_product_variants(product_id)
            variants = result['product']['variants']['nodes']

            move_variants = []
            total_delta = 0

            for v in variants:
                variant_gid = v['id']
                # Exclude only the destination variant (open) - include source variant
                if variant_gid == dest_gid:
                    continue
                
                # Move inventory from any variant that has inventory > 0
                qty = v['inventoryQuantity']
                if qty > 0:
                    item_id = str(v['inventoryItem']['id'])
                    variant_title = v.get('title', 'Unknown')
                    print(f"🔁 Queuing {qty} from variant {variant_gid} ({variant_title})")
                    move_variants.append((item_id, qty))
                    total_delta += qty

            if total_delta == 0:
                raise ValueError("No inventory found to move from other variants.")

            dest_data = get_inventory_item_and_quantity(dest_gid)
            dest_id = str(dest_data['inventoryItemId'])

            wait_until_next_minute()
            for item_id, qty in move_variants:
                adjust_inventory(item_id, -qty)
            adjust_inventory(dest_id, total_delta)
            
            # Check if any veteran variant has 0 inventory after consolidation
            # Find veteran variant by checking all variants for 'veteran' in title
            veteran_variant_gid = None
            for v in variants:
                variant_title = v.get('title', '').lower()
                if 'veteran' in variant_title:
                    veteran_variant_gid = v['id']
                    break
            
            if veteran_variant_gid:
                veteran_data_after = get_inventory_item_and_quantity(veteran_variant_gid)
                remaining_qty = veteran_data_after['inventoryQuantity']
                print(f"🔍 Veteran variant inventory after consolidation: {remaining_qty}")
                
                if remaining_qty == 0:
                    print("🏷️ Veteran variant has 0 inventory, removing 'veteran-only' tag")
                    try:
                        current_tags = get_product_tags(product_id)
                        if 'veteran-only' in current_tags:
                            updated_tags = [tag for tag in current_tags if tag != 'veteran-only']
                            update_product_tags(product_id, updated_tags)
                            print(f"✅ Removed 'veteran-only' tag. Updated tags: {updated_tags}")
                            tags_updated = True
                        else:
                            print("ℹ️ 'veteran-only' tag not found on product")
                    except Exception as e:
                        print(f"⚠️ Failed to update product tags: {e}")
                        # Don't fail the entire operation if tag update fails
                else:
                    print(f"ℹ️ Veteran variant still has {remaining_qty} inventory, keeping 'veteran-only' tag")

            message = f"Moved {total_delta} units into {dest_name}"
            if tags_updated:
                message += " and removed 'veteran-only' tag"
            
            return format_response(200, {
                "success": True,
                "message": message,
                "details": {
                    "from": "all non-open variants",
                    "to": f"{dest_name} ({dest_gid})",
                    "amountMoved": total_delta,
                    "tagsUpdated": tags_updated
                }
            })
        
        elif source_type == "custom" and dest_type == "custom":
            # 🧠 Case 3: Manually move between specific variants
            source_data = get_inventory_item_and_quantity(source_gid)
            dest_data = get_inventory_item_and_quantity(dest_gid)

            source_qty = source_data['inventoryQuantity']
            source_id = str(source_data['inventoryItemId'])
            dest_id = str(dest_data['inventoryItemId'])

            print(f"📊 Moving ALL {source_qty} inventory units from {source_name} → {dest_name}")
            if source_qty <= 0:
                raise ValueError(f"No inventory to move from {source_name} variant.")

            wait_until_next_minute()
            adjust_inventory(source_id, -source_qty)
            adjust_inventory(dest_id, source_qty)

            message = f"Moved all {source_qty} units from {source_name} to {dest_name}"
            if tags_updated:
                message += " and removed 'veteran-only' tag"
            
            return format_response(200, {
                "success": True,
                "message": message,
                "details": {
                    "from": f"{source_name} ({source_gid})",
                    "to": f"{dest_name} ({dest_gid})",
                    "amountMoved": source_qty,
                    "tagsUpdated": tags_updated
                }
            })

        # ❌ Catch-all for unhandled types
        else:
            raise ValueError(f"Unsupported source→destination move: {source_type} → {dest_type}")

    except Exception as e:
        print("❌ Exception occurred:", traceback.format_exc())
        return format_error(500, str(e))
