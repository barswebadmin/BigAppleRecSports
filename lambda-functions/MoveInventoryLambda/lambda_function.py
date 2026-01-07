__version__ = "1.2.0"

import json
import traceback
from typing import Dict, Any

from bars_common_utils.response_utils import format_response, format_error
from bars_common_utils.event_utils import validate_required_fields
from bars_common_utils.request_utils import wait_until_next_minute
from bars_common_utils.shopify_utils import (
    get_inventory_item_and_quantity,
    adjust_inventory,
    get_product_variants
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

            return format_response(200, {
                "success": True,
                "message": f"Moved all {source_qty} units from {source_name} to {dest_name}",
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
                # Exclude destination variant (open) and source variant to avoid double-moving
                if variant_gid == dest_gid or variant_gid == source_gid:
                    continue
                
                # Move inventory from any variant that has inventory > 0
                qty = v['inventoryQuantity']
                if qty != 0:
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

            return format_response(200, {
                "success": True,
                "message": f"Moved {total_delta} units into {dest_name}",
                "details": {
                    "from": "all non-open variants",
                    "to": f"{dest_name} ({dest_gid})",
                    "amountMoved": total_delta
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

            return format_response(200, {
                "success": True,
                "message": f"Moved all {source_qty} units from {source_name} to {dest_name}",
                "details": {
                    "from": f"{source_name} ({source_gid})",
                    "to": f"{dest_name} ({dest_gid})",
                    "amountMoved": source_qty
                }
            })

        # ❌ Catch-all for unhandled types
        else:
            raise ValueError(f"Unsupported source→destination move: {source_type} → {dest_type}")

    except Exception as e:
        print("❌ Exception occurred:", traceback.format_exc())
        return format_error(500, str(e))