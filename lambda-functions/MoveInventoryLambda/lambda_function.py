__version__ = "1.1.0"

import json
import traceback
from datetime import datetime
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
      - Veteran ➡ Early (calculates deltaToMove)
      - Early/Vet ➡ Open (consolidates inventory)
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

        # 🧠 Case 1: Veteran ➡ Early logic
        if source_type == 'veteran' and dest_type == 'early':
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

        # 🧠 Case 2: Consolidate from veteran+early ➡ open
        if dest_type == 'open':
            product_id = event['productUrl'].split('/')[-1]
            result = get_product_variants(product_id)
            variants = result['product']['variants']['nodes']

            move_variants = []
            total_delta = 0

            for v in variants:
                title = v['title'].lower()
                if 'early' in title or 'veteran' in title:
                    qty = v['inventoryQuantity']
                    if qty != 0:
                        item_id = str(v['inventoryItem']['id'])
                        print(f"🔁 Queuing {qty} from '{title}'")
                        move_variants.append((item_id, qty))
                        total_delta += qty

            if total_delta == 0:
                raise ValueError("No inventory found to move from early/veteran variants.")

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
                    "from": "early+vet",
                    "to": f"{dest_name} ({dest_gid})",
                    "amountMoved": total_delta
                }
            })
        
        # 🧠 Case 3: Manually move between specific variants:
        if source_type == "custom" and dest_type == "custom":
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
        raise ValueError(f"Unsupported source→destination move: {source_type} → {dest_type}")

    except Exception as e:
        print("❌ Exception occurred:", traceback.format_exc())
        return format_error(500, str(e))