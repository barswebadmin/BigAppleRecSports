#!/usr/bin/env python3
"""
Fetch all non-canceled orders for a specific product and output as CSV.

Usage:
    python bars-scripts/product_orders.py 1234567890
    python bars-scripts/product_orders.py 1234567890 --csv-file output.csv
    python bars-scripts/product_orders.py 1234567890 --env development
"""

import sys
import argparse
import csv
import json
from typing import Dict, Any, List, Optional

# Import shared utilities
import shared_utils

# Import CSV functions from get_order_details
# Import as module to avoid circular dependencies
import get_order_details


def wrap_product_id(product_id: str) -> str:
    """Wrap product ID with Shopify GID format."""
    product_id = product_id.strip()
    if product_id.startswith('gid://shopify/Product/'):
        return product_id
    return f"gid://shopify/Product/{product_id}"


def fetch_orders_by_product(
    product_id: str,
    config: Dict[str, Any],
    cursor: Optional[str] = None
) -> Dict[str, Any]:
    """Fetch orders for a product with pagination support."""
    product_gid = wrap_product_id(product_id)
    
    # Query to fetch orders with the same fields as fetch_order_with_metadata
    query = """
    query FetchOrdersByProduct($q: String!, $cursor: String) {
        orders(first: 250, query: $q, after: $cursor) {
            pageInfo {
                hasNextPage
                endCursor
            }
            edges {
                node {
                    id
                    name
                    email
                    createdAt
                    updatedAt
                    phone
                    displayFinancialStatus
                    displayFulfillmentStatus
                    subtotalLineItemsQuantity
                    totalPriceSet {
                        shopMoney {
                            amount
                            currencyCode
                        }
                    }
                    discountApplications(first: 10) {
                        edges {
                            node {
                                ... on DiscountCodeApplication {
                                    code
                                }
                                ... on ScriptDiscountApplication {
                                    title
                                }
                                ... on AutomaticDiscountApplication {
                                    title
                                }
                            }
                        }
                    }
                    billingAddress {
                        firstName
                        lastName
                        address1
                        city
                        zip
                        country
                        phone
                    }
                    customer {
                        id
                        email
                        firstName
                        lastName
                    }
                    cancelledAt
                    cancelReason
                    refunds {
                        id
                        createdAt
                        totalRefundedSet {
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                    }
                    lineItems(first: 50) {
                        edges {
                            node {
                                id
                                name
                                title
                                quantity
                                customAttributes {
                                    key
                                    value
                                }
                                product {
                                    """ + shared_utils.get_product_fields() + """
                                }
                                variant {
                                    id
                                    title
                                    price
                                    sku
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    # Query string: product_id uses numeric ID, not GID
    # Extract numeric ID from GID if needed
    numeric_id = product_id
    if product_id.startswith('gid://shopify/Product/'):
        numeric_id = product_id.replace('gid://shopify/Product/', '')
    
    # Query string: product_id (include canceled orders to show cancellation status)
    query_string = f"product_id:{numeric_id}"
    
    payload = {
        "query": query,
        "variables": {
            "q": query_string,
            "cursor": cursor
        }
    }
    
    return shared_utils.make_graphql_request(payload, config)


def extract_order_id_digits(order_gid: str) -> str:
    """Extract numeric order ID from GID."""
    if order_gid.startswith('gid://shopify/Order/'):
        return order_gid.replace('gid://shopify/Order/', '')
    return order_gid


def find_email_in_custom_attributes(line_items: List[Dict[str, Any]]) -> str:
    """Find email in first line item's custom attributes."""
    if not line_items:
        return ''
    
    first_item = line_items[0].get('node', {})
    custom_attrs = first_item.get('customAttributes', [])
    
    for attr in custom_attrs:
        key = attr.get('key', '').lower()
        if 'email' in key:
            return attr.get('value', '')
    
    return ''


def format_discounts(discount_apps: Dict[str, Any]) -> str:
    """Format discount applications as a string."""
    if not discount_apps:
        return ''
    
    discounts = []
    edges = discount_apps.get('edges', [])
    
    for edge in edges:
        node = edge.get('node', {})
        if 'code' in node:
            discounts.append(node.get('code', ''))
        elif 'title' in node:
            discounts.append(node.get('title', ''))
    
    return ', '.join(discounts) if discounts else ''


def calculate_total_refunded(refunds: List[Dict[str, Any]]) -> str:
    """Calculate total refunded amount from all refunds."""
    if not refunds:
        return '0.00'
    
    total = 0.0
    for refund in refunds:
        total_refunded_set = refund.get('totalRefundedSet', {})
        shop_money = total_refunded_set.get('shopMoney', {})
        amount_str = shop_money.get('amount', '0')
        try:
            total += float(amount_str)
        except (ValueError, TypeError):
            continue
    
    return f"{total:.2f}"


def order_to_dates_csv_row(order: Dict[str, Any], shop: str = "09fe59-3") -> List[str]:
    """Convert order data to dates CSV row format."""
    order_id = extract_order_id_digits(order.get('id', ''))
    order_url = f"https://admin.shopify.com/store/{shop}/orders/{order_id}"
    
    # Get email from line items custom attributes
    line_items = order.get('lineItems', {}).get('edges', [])
    email = find_email_in_custom_attributes(line_items)
    
    # Get descriptionHtml from first line item's product
    description_html = ''
    if line_items:
        first_line_item = line_items[0].get('node', {})
        product = first_line_item.get('product', {})
        description_html = product.get('descriptionHtml', '')
    
    # Get order status (financial status)
    order_status = order.get('displayFinancialStatus', '')
    
    # Get total paid
    total_paid = ''
    total_price_set = order.get('totalPriceSet', {}).get('shopMoney', {})
    if total_price_set:
        total_paid = total_price_set.get('amount', '')
    
    # Get discounts
    discounts = format_discounts(order.get('discountApplications', {}))
    
    # Check if order is canceled
    is_canceled = 'true' if order.get('cancelledAt') else 'false'
    
    # Calculate total refunded amount
    refunds = order.get('refunds', [])
    total_refunded = calculate_total_refunded(refunds)
    
    return [
        order.get('name', ''),  # orderName
        order_id,  # orderId
        order_url,  # orderUrl
        order.get('createdAt', ''),  # createdAt
        email,  # email from lineItems[0].customAttributes
        order_status,  # order status
        total_paid,  # total paid
        discounts,  # any discounts
        description_html,  # descriptionHtml
        is_canceled,  # isCanceled
        total_refunded  # totalRefunded
    ]


def get_dates_csv_headers() -> List[str]:
    """Get CSV headers for dates format."""
    return [
        'orderName',
        'orderId',
        'orderUrl',
        'createdAt',
        'email',
        'orderStatus',
        'totalPaid',
        'discounts',
        'descriptionHtml',
        'isCanceled',
        'totalRefunded'
    ]


def fetch_all_orders_by_product(
    product_id: str,
    config: Dict[str, Any],
    debug: bool = False
) -> List[Dict[str, Any]]:
    """Fetch all orders for a product with pagination (including canceled orders)."""
    all_orders = []
    cursor = None
    page_num = 1
    
    while True:
        result = fetch_orders_by_product(product_id, config, cursor)
        
        if debug:
            print(f"Page {page_num} query result keys: {list(result.keys())}", file=sys.stderr)
            if 'data' in result:
                orders_data = result.get('data', {}).get('orders', {})
                edges = orders_data.get('edges', [])
                print(f"Page {page_num} found {len(edges)} order(s)", file=sys.stderr)
        
        # Check for errors
        if "error" in result:
            print(f"Error: {result['error']}", file=sys.stderr)
            break
        
        if "errors" in result:
            print("GraphQL Errors:", file=sys.stderr)
            for error in result["errors"]:
                print(f"  - {error.get('message', str(error))}", file=sys.stderr)
            if debug:
                print(f"Full error response: {json.dumps(result, indent=2)}", file=sys.stderr)
            break
        
        # Extract orders
        orders_data = result.get('data', {}).get('orders', {})
        if not orders_data:
            if debug:
                print(f"No 'orders' in data. Response keys: {list(result.get('data', {}).keys())}", file=sys.stderr)
            break
        
        edges = orders_data.get('edges', [])
        
        if debug and page_num == 1:
            # Show first query string for debugging
            numeric_id = product_id
            if product_id.startswith('gid://shopify/Product/'):
                numeric_id = product_id.replace('gid://shopify/Product/', '')
            query_string = f"product_id:{numeric_id}"
            print(f"Query string: {query_string}", file=sys.stderr)
        
        # Include all orders (including canceled ones to show cancellation status)
        for edge in edges:
            order = edge['node']
            # Debug logging for descriptionHtml in first order
            if debug and page_num == 1 and len(all_orders) == 0:
                line_items = order.get('lineItems', {}).get('edges', [])
                if line_items:
                    first_line_item = line_items[0].get('node', {})
                    product = first_line_item.get('product', {})
                    print(f"DEBUG: First order {order.get('name', 'N/A')} - Product keys: {list(product.keys())}", file=sys.stderr)
                    print(f"DEBUG: First order {order.get('name', 'N/A')} - descriptionHtml in product: {'descriptionHtml' in product}", file=sys.stderr)
                    if 'descriptionHtml' in product:
                        desc_len = len(product.get('descriptionHtml', ''))
                        print(f"DEBUG: First order {order.get('name', 'N/A')} - descriptionHtml length: {desc_len}", file=sys.stderr)
            all_orders.append(order)
        
        # Check pagination
        page_info = orders_data.get('pageInfo', {})
        has_next_page = page_info.get('hasNextPage', False)
        
        if not has_next_page:
            break
        
        cursor = page_info.get('endCursor')
        if not cursor:
            break
        
        page_num += 1
    
    return all_orders


def main():
    parser = argparse.ArgumentParser(
        description="Fetch all non-canceled orders for a product and output as CSV"
    )
    parser.add_argument(
        "product_id",
        help="Product ID (numeric or GID format)"
    )
    parser.add_argument(
        "--env",
        choices=["development", "staging", "production"],
        default="production",
        help="Environment to use (default: production)"
    )
    parser.add_argument(
        "--csv-datachamp",
        type=str,
        help="Write CSV to file (datachamp format) instead of stdout"
    )
    parser.add_argument(
        "--csv-dates",
        type=str,
        help="Write CSV to file (dates format) instead of stdout"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of CSV"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show debug information"
    )
    
    args = parser.parse_args()
    
    # Initialize
    shared_utils.load_environment(args.env)
    
    try:
        # Get config
        config = shared_utils.get_shopify_config(args.env)
        
        # Fetch all orders
        product_gid = wrap_product_id(args.product_id)
        print(f"Fetching orders for product {product_gid} from {args.env}...", file=sys.stderr)
        
        orders = fetch_all_orders_by_product(args.product_id, config, debug=args.debug)
        
        if not orders:
            print("No orders found for this product.", file=sys.stderr)
            return 1
        
        print(f"Found {len(orders)} order(s)", file=sys.stderr)
        
        # Output JSON or CSV
        if args.json:
            # Output raw JSON
            print(json.dumps(orders, indent=2))
        elif args.csv_dates:
            # Output dates CSV format
            headers = get_dates_csv_headers()
            with open(args.csv_dates, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for order in orders:
                    row = order_to_dates_csv_row(order)
                    writer.writerow(row)
            print(f"CSV written to {args.csv_dates}", file=sys.stderr)
        elif args.csv_datachamp:
            # Output datachamp CSV format
            headers = get_order_details.get_csv_headers()
            with open(args.csv_datachamp, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for order in orders:
                    row = get_order_details.order_to_csv_row(order)
                    writer.writerow(row)
            print(f"CSV written to {args.csv_datachamp}", file=sys.stderr)
        else:
            # Output datachamp CSV format to stdout
            headers = get_order_details.get_csv_headers()
            writer = csv.writer(sys.stdout)
            writer.writerow(headers)
            for order in orders:
                row = get_order_details.order_to_csv_row(order)
                writer.writerow(row)
        
        return 0
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

