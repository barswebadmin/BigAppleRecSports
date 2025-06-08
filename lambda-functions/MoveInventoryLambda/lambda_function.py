__version__ = "1.1.0"

import json
import traceback
from datetime import datetime

from bars_common_utils.response_utils import format_response, format_error
from bars_common_utils.event_utils import validate_required_fields
from bars_common_utils.request_utils import wait_until_next_minute
from bars_common_utils.shopify_utils import (
    get_inventory_item_and_quantity,
    adjust_inventory,
    get_product_variants
)

def lambda_handler(event, context):
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
        source_gid = source['gid']
        dest_gid = dest['gid']
        source_type = source.get('type', '').lower()
        dest_type = dest.get('type', '').lower()

        # 🧠 Case 1: Veteran ➡ Early logic
        if source_type == 'veteran' and dest_type == 'early':
            validate_required_fields(event, ['totalInventory', 'numEligibleVeterans'])

            total_inventory = event['totalInventory']
            num_vets = event['numEligibleVeterans']

            source_data = get_inventory_item_and_quantity(source_gid)
            dest_data = get_inventory_item_and_quantity(dest_gid)

            source_qty = source_data['inventoryQuantity']
            source_id = source_data['inventoryItemId']
            dest_id = dest_data['inventoryItemId']

            num_orders = total_inventory - source_qty
            remaining_non_vet_spots = source_qty - (num_vets - num_orders)
            delta_to_move = min(remaining_non_vet_spots, source_qty)

            print(f"📊 Calculated deltaToMove: {delta_to_move}")
            if delta_to_move <= 0:
                raise ValueError(f"Delta to move is not positive: {delta_to_move}")

            wait_until_next_minute()
            adjust_inventory(source_id, -delta_to_move)
            adjust_inventory(dest_id, delta_to_move)

            return format_response(200, {
                "success": True,
                "message": f"Moved {delta_to_move} units from veteran to early",
                "details": {
                    "from": source_gid,
                    "to": dest_gid,
                    "amountMoved": delta_to_move
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
                        item_id = v['inventoryItem']['id']
                        print(f"🔁 Queuing {qty} from '{title}'")
                        move_variants.append((item_id, qty))
                        total_delta += qty

            if total_delta == 0:
                raise ValueError("No inventory found to move from early/veteran variants.")

            dest_data = get_inventory_item_and_quantity(dest_gid)
            dest_id = dest_data['inventoryItemId']

            wait_until_next_minute()
            for item_id, qty in move_variants:
                adjust_inventory(item_id, -qty)
            adjust_inventory(dest_id, total_delta)

            return format_response(200, {
                "success": True,
                "message": f"Moved {total_delta} units into open variant",
                "details": {
                    "from": "early+vet",
                    "to": dest_gid,
                    "amountMoved": total_delta
                }
            })

        # ❌ Catch-all for unhandled types
        raise ValueError(f"Unsupported source→destination move: {source_type} → {dest_type}")

    except Exception as e:
        print("❌ Exception occurred:", traceback.format_exc())
        return format_error(500, str(e))