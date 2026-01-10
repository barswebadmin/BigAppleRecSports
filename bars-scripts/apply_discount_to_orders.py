#!/usr/bin/env python3
"""
Batch apply a fixed amount or percentage discount to Shopify orders via Order Editing:
1) orderEditBegin
2) fetch CalculatedLineItem (first line)
3) orderEditAddLineItemDiscount
4) orderEditCommit

Configure the order IDs in ORDER_IDS below. Processes in batches of 10.
Prompts for discount type (fixed 'f' or percentage 'p') and discount value.
"""

import os
import json
import time
import requests
import sys
from typing import Optional, List, Dict, Any
from pathlib import Path

# Add bars-scripts to path for refund_order import
sys.path.insert(0, str(Path(__file__).parent))

# Import refund utilities
import refund_order

# ====== CONFIG ======
SHOP = os.getenv("SHOPIFY_SHOP", "09fe59-3")            # e.g. 09fe59-3
API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2025-07")
ACCESS_TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN")         # export SHOPIFY_ADMIN_TOKEN=shpat_...
CURRENCY_ENUM = os.getenv("DISCOUNT_CURRENCY", "USD")   # GraphQL enum (no quotes in mutation): USD, CAD, …

# <<< EDIT THIS LIST >>>
ORDER_IDS: List[int] = [
    6039629594718,
    6055356334174
]

BATCH_SIZE = 10
SLEEP_BETWEEN_CALLS_SEC = 0.05   # tiny delay to be gentle on API
# =====================

BASE_URL = f"https://{SHOP}.myshopify.com/admin/api/{API_VERSION}/graphql.json"
SESSION = requests.Session()
SESSION.headers.update({"Content-Type": "application/json", "X-Shopify-Access-Token": ACCESS_TOKEN or ""})


def prompt_discount_type() -> str:
    """Prompt user for discount type: 'f' for fixed, 'p' for percentage."""
    while True:
        response = input("Discount type - Fixed amount (f) or Percentage (p): ").strip().lower()
        if response in ('f', 'p'):
            return response
        print("Invalid input. Please enter 'f' for fixed amount or 'p' for percentage.")


def prompt_fixed_amount() -> float:
    """Prompt user for fixed discount amount."""
    while True:
        try:
            response = input("Enter fixed discount amount (e.g., 5.00 for $5.00): ").strip()
            amount = float(response)
            if amount < 0:
                print("Amount cannot be negative. Please enter a positive number.")
                continue
            return amount
        except ValueError:
            print("Invalid input. Please enter a valid number (e.g., 5.00).")


def prompt_percentage() -> float:
    """Prompt user for percentage discount (whole number, e.g., 5 = 5%, 100 = 100%)."""
    while True:
        try:
            response = input("Enter percentage discount (whole number, e.g., 5 for 5%, 100 for 100%): ").strip()
            percentage = float(response)
            if percentage < 0 or percentage > 100:
                print("Percentage must be between 0 and 100. Please enter a valid percentage.")
                continue
            return percentage
        except ValueError:
            print("Invalid input. Please enter a valid whole number (e.g., 5 for 5%).")


def gql(query: str, variables: Optional[dict] = None) -> dict:
    payload: Dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables  # type: ignore[assignment]
    r = SESSION.post(BASE_URL, data=json.dumps(payload), timeout=30)
    try:
        data = r.json()
    except Exception:
        raise RuntimeError(f"Non-JSON response {r.status_code}: {r.text[:300]}")
    if "errors" in data and data["errors"]:
        raise RuntimeError(json.dumps(data["errors"]))
    return data["data"]


def order_edit_begin(order_gid: str) -> str:
    q = f'''
    mutation {{
      orderEditBegin(id: "{order_gid}") {{
        calculatedOrder {{ id }}
        userErrors {{ field message }}
      }}
    }}
    '''
    d = gql(q)["orderEditBegin"]
    errs = d.get("userErrors") or []
    if errs:
        raise RuntimeError(f"{errs}")
    return d["calculatedOrder"]["id"]


def get_first_calculated_line_item(calc_order_gid: str) -> tuple:
    """Get first calculated line item ID and its original unit price. Returns (line_item_id, unit_price)."""
    q = f'''
    {{
      node(id: "{calc_order_gid}") {{
        ... on CalculatedOrder {{
          lineItems(first: 50) {{
            edges {{
              node {{
                id
                title
                originalUnitPriceSet {{
                  shopMoney {{
                    amount
                    currencyCode
                  }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    '''
    d = gql(q)
    edges = d["node"]["lineItems"]["edges"]
    if not edges:
        raise RuntimeError("No calculated line items on CalculatedOrder")
    line_item = edges[0]["node"]
    line_item_id = line_item["id"]
    unit_price = float(line_item["originalUnitPriceSet"]["shopMoney"]["amount"])
    return line_item_id, unit_price


def add_fixed_discount(calc_order_gid: str, calc_line_item_gid: str, amount: str, code_desc: str):
    """Add a fixed amount discount."""
    q = f'''
    mutation {{
      orderEditAddLineItemDiscount(
        id: "{calc_order_gid}",
        lineItemId: "{calc_line_item_gid}",
        discount: {{
          description: "{code_desc}",
          fixedValue: {{ amount: "{amount}", currencyCode: {CURRENCY_ENUM} }}
        }}
      ) {{
        userErrors {{ field message }}
      }}
    }}
    '''
    d = gql(q)["orderEditAddLineItemDiscount"]
    errs = d.get("userErrors") or []
    if errs:
        raise RuntimeError(f"{errs}")


def add_percentage_discount(calc_order_gid: str, calc_line_item_gid: str, percentage: float, code_desc: str, unit_price: float):
    """Add a percentage discount by calculating the fixed amount and applying it.
    
    Since Shopify's OrderEditAppliedDiscountInput only supports fixedValue,
    we calculate the discount amount from the percentage and apply it as a fixed discount.
    """
    # Calculate discount amount from percentage (e.g., 5% of $100 = $5.00)
    discount_amount = (percentage / 100.0) * unit_price
    
    # Apply as fixed discount
    q = f'''
    mutation {{
      orderEditAddLineItemDiscount(
        id: "{calc_order_gid}",
        lineItemId: "{calc_line_item_gid}",
        discount: {{
          description: "{code_desc}",
          fixedValue: {{ amount: "{discount_amount:.2f}", currencyCode: {CURRENCY_ENUM} }}
        }}
      ) {{
        userErrors {{ field message }}
      }}
    }}
    '''
    d = gql(q)["orderEditAddLineItemDiscount"]
    errs = d.get("userErrors") or []
    if errs:
        raise RuntimeError(f"{errs}")


def order_edit_commit(calc_order_gid: str, discount_type: str, discount_value: float, code_desc: str):
    """Commit the order edit with appropriate staff note."""
    if discount_type == 'f':
        note = f"Applied ${discount_value:.2f} discount via {code_desc}"
    else:
        note = f"Applied {discount_value}% discount via {code_desc}"
    
    q = f'''
    mutation {{
      orderEditCommit(
        id: "{calc_order_gid}",
        notifyCustomer: false,
        staffNote: "{note}"
      ) {{
        userErrors {{ field message }}
      }}
    }}
    '''
    d = gql(q)["orderEditCommit"]
    errs = d.get("userErrors") or []
    if errs:
        raise RuntimeError(f"{errs}")


def get_order_refund_info(order_number: str) -> Dict[str, Any]:
    """Fetch order information including refunds and total paid."""
    # Setup config for refund_order
    shared_utils_path = Path(__file__).parent
    sys.path.insert(0, str(shared_utils_path))
    import shared_utils
    
    # Load environment and get config
    shared_utils.load_environment(os.getenv("ENVIRONMENT", "production"))
    config = shared_utils.get_shopify_config(os.getenv("ENVIRONMENT", "production"))
    
    # Fetch order
    fetch_result = refund_order.fetch_order(order_number, config)
    
    if "error" in fetch_result or "errors" in fetch_result:
        return {"error": fetch_result.get("error", fetch_result.get("errors", "Unknown error"))}
    
    orders = fetch_result.get('data', {}).get('orders', {}).get('edges', [])
    if not orders:
        return {"error": f"No order found with number: #{order_number}"}
    
    order_data = orders[0]['node']
    payment_summary = refund_order.calculate_payment_summary(order_data)
    
    return {
        "order_data": order_data,
        "order_id": order_data['id'],
        "order_name": order_data['name'],
        "payment_summary": payment_summary,
        "refunds": order_data.get('refunds', []),
        "transactions": order_data.get('transactions', [])
    }


def calculate_net_refund_due(discount_amount: float, order_refund_info: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate net refund due after discount, accounting for existing refunds.
    
    Compares total_paid against what they should have paid (original_total - discount_amount).
    """
    payment_summary = order_refund_info.get("payment_summary", {})
    total_refunded = payment_summary.get("total_refunded", 0.0)
    total_paid = payment_summary.get("total_amount", 0.0)
    
    # Get original order total (before discount was applied)
    order_data = order_refund_info.get("order_data", {})
    original_total = float(order_data.get("totalPriceSet", {}).get("shopMoney", {}).get("amount", 0.0))
    
    # Calculate what they should have paid after discount
    should_have_paid = original_total - discount_amount
    
    # Calculate refund due: if they paid more than they should have
    if total_paid > should_have_paid:
        # Refund the difference, minus any already refunded
        net_refund_due = (total_paid - should_have_paid) - total_refunded
        net_refund_due = max(0.0, net_refund_due)  # Can't be negative
    else:
        # They paid the correct amount or less, no refund due
        net_refund_due = 0.0
    
    return {
        "discount_amount": discount_amount,
        "original_total": original_total,
        "should_have_paid": should_have_paid,
        "total_refunded": total_refunded,
        "net_refund_due": net_refund_due,
        "total_paid": total_paid,
        "remaining_refundable": payment_summary.get("remaining_refundable", 0.0)
    }


def apply_discount_to_order(
    numeric_order_id: int,
    discount_type: str,
    discount_value: float,
    code_desc: str,
    prompt_for_refund: bool = True
) -> Dict[str, str]:
    """Returns dict with keys: order_id, status ('ok'|'error'), step, error, refund_info"""
    out = {"order_id": str(numeric_order_id), "status": "ok", "step": "done", "error": "", "refund_info": {}}
    order_gid = f"gid://shopify/Order/{numeric_order_id}"

    try:
        out["step"] = "begin"
        calc_id = order_edit_begin(order_gid)
        time.sleep(SLEEP_BETWEEN_CALLS_SEC)

        out["step"] = "fetch_line"
        calc_line_id, unit_price = get_first_calculated_line_item(calc_id)
        time.sleep(SLEEP_BETWEEN_CALLS_SEC)

        out["step"] = "addDiscount"
        if discount_type == 'f':
            discount_amount = discount_value
            add_fixed_discount(calc_id, calc_line_id, f"{discount_value:.2f}", code_desc)
        else:
            discount_amount = (discount_value / 100.0) * unit_price
            add_percentage_discount(calc_id, calc_line_id, discount_value, code_desc, unit_price)
        time.sleep(SLEEP_BETWEEN_CALLS_SEC)

        out["step"] = "commit"
        order_edit_commit(calc_id, discount_type, discount_value, code_desc)
        out["step"] = "done"
        
        # Wait 3 seconds after discount is applied
        print(f"Waiting 3 seconds for order to update...", flush=True)
        time.sleep(3)
        
        # Check refund status and prompt if needed
        if prompt_for_refund:
            try:
                order_number = f"{numeric_order_id}"
                order_refund_info = get_order_refund_info(order_number)
                
                if "error" in order_refund_info:
                    out["refund_info"] = {"error": order_refund_info["error"]}
                    print(f"⚠️  Warning: Could not fetch order refund info: {order_refund_info['error']}", flush=True)
                else:
                    net_refund = calculate_net_refund_due(discount_amount, order_refund_info)
                    out["refund_info"] = net_refund
                    
                    # Display refund information
                    print(f"\n💰 Refund Analysis for Order #{order_number}:")
                    print(f"   Original Order Total: ${net_refund['original_total']:.2f}")
                    print(f"   Discount Applied: ${discount_amount:.2f}")
                    print(f"   Should Have Paid: ${net_refund['should_have_paid']:.2f}")
                    print(f"   Total Actually Paid: ${net_refund['total_paid']:.2f}")
                    print(f"   Total Already Refunded: ${net_refund['total_refunded']:.2f}")
                    print(f"   Net Refund Due: ${net_refund['net_refund_due']:.2f}")
                    print(f"   Remaining Refundable: ${net_refund['remaining_refundable']:.2f}")
                    
                    # Check if refund is due (they paid more than they should have)
                    if net_refund['net_refund_due'] > 0:
                        # Prompt user for confirmation
                        while True:
                            response = input(f"\nRefund ${net_refund['net_refund_due']:.2f} to customer? (y/n): ").strip().lower()
                            if response in ('y', 'yes'):
                                # Process refund using refund_order logic
                                try:
                                    # Setup config
                                    shared_utils_path = Path(__file__).parent
                                    sys.path.insert(0, str(shared_utils_path))
                                    import shared_utils
                                    
                                    shared_utils.load_environment(os.getenv("ENVIRONMENT", "production"))
                                    config = shared_utils.get_shopify_config(os.getenv("ENVIRONMENT", "production"))
                                    
                                    # Create refund (default to "refund" type - original payment method)
                                    refund_result = refund_order.create_refund(
                                        order_refund_info["order_id"],
                                        net_refund['net_refund_due'],
                                        "refund",  # Use original payment method
                                        order_refund_info["transactions"],
                                        config
                                    )
                                    
                                    if refund_result.get("success"):
                                        refund_data = refund_result.get("data", {})
                                        refund_id = refund_data.get('id', 'N/A').split('/')[-1]
                                        print(f"✅ Refund processed successfully! Refund ID: {refund_id}")
                                        out["refund_info"]["refund_processed"] = True
                                        out["refund_info"]["refund_id"] = refund_id
                                    else:
                                        error_msg = refund_result.get("message", refund_result.get("error", "Unknown error"))
                                        print(f"❌ Failed to process refund: {error_msg}")
                                        out["refund_info"]["refund_processed"] = False
                                        out["refund_info"]["refund_error"] = error_msg
                                
                                except Exception as refund_error:
                                    print(f"❌ Error processing refund: {str(refund_error)}")
                                    out["refund_info"]["refund_processed"] = False
                                    out["refund_info"]["refund_error"] = str(refund_error)
                                
                                break
                            elif response in ('n', 'no'):
                                print("Refund skipped.")
                                out["refund_info"]["refund_processed"] = False
                                out["refund_info"]["refund_skipped"] = True
                                break
                            else:
                                print("Invalid input. Please enter 'y' for yes or 'n' for no.")
                    elif net_refund['net_refund_due'] <= 0:
                        print(f"\nℹ️  No refund due (discount amount already refunded or no discount).")
                        out["refund_info"]["refund_skipped"] = True
                        out["refund_info"]["reason"] = "No refund due"
            
            except Exception as refund_check_error:
                print(f"⚠️  Warning: Error checking refund status: {str(refund_check_error)}", flush=True)
                out["refund_info"] = {"error": str(refund_check_error)}
        
        return out

    except Exception as e:
        out["status"] = "error"
        out["error"] = str(e)
        return out


def batched(iterable: List[int], size: int) -> List[List[int]]:
    return [iterable[i:i+size] for i in range(0, len(iterable), size)]


def main():
    if not ACCESS_TOKEN:
        print("ERROR: set SHOPIFY_ADMIN_TOKEN (export SHOPIFY_ADMIN_TOKEN=shpat_...)", flush=True)
        raise SystemExit(1)
    if not ORDER_IDS:
        print("ERROR: populate ORDER_IDS at the top of this script.", flush=True)
        raise SystemExit(2)

    # Prompt for discount type
    discount_type = prompt_discount_type()
    
    # Prompt for discount value
    if discount_type == 'f':
        discount_value = prompt_fixed_amount()
        code_desc = f"code: fixed-discount-${discount_value:.2f}"
    else:
        discount_value = prompt_percentage()
        code_desc = f"code: percentage-discount-{discount_value}%"

    successes: List[str] = []
    failures: List[Dict[str, str]] = []

    for chunk in batched(ORDER_IDS, BATCH_SIZE):
        for oid in chunk:
            res = apply_discount_to_order(oid, discount_type, discount_value, code_desc)
            if res["status"] == "ok":
                successes.append(res["order_id"])
            else:
                failures.append({"order_id": res["order_id"], "failed_step": res["step"], "error": res["error"]})
        # optional gentle pause between batches
        time.sleep(0.2)

    if not failures:
        # all good — print only successes
        print(json.dumps({"success": successes}, indent=2))
    else:
        print(json.dumps({"success": successes, "failures": failures}, indent=2))


if __name__ == "__main__":
    main()
