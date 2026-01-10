"""CSV formatter for Shopify orders matching Shopify export format."""

from typing import Dict, Any, List
from bars_cli._core.ui.csv_export import (
    format_date_for_csv,
    get_custom_attribute_value
)


def get_csv_headers() -> List[str]:
    """Get CSV headers matching the Shopify export format."""
    return [
        'Order Number',
        'Email',
        'Updated at',
        'Fully paid',
        'Fulfillment status',
        'Current subtotal quantity',
        'Discount code',
        'Line items: Name',
        'Total price',
        'Line items: SKU',
        'Line items: Vendor',
        'Line items: Product description HTML',
        'Line items: Title',
        'Line items: Variant title',
        'Billing address: First name',
        'Billing address: Last name',
        'Billing address: Address first line',
        'Billing address: City',
        'Billing address: Zip',
        'Billing address: Country',
        'Phone',
        'Line items: Custom attributes _Form Fields',
        'Line items: Custom attributes Are you interested in being a captain?',
        'Line items: Custom attributes Are you interested in reffing?',
        'Line items: Custom attributes Best Contact Email Address',
        'Line items: Custom attributes Best Contact Number (Cell Phone Number Preferred)',
        'Line items: Custom attributes Date of Birth',
        'Line items: Custom attributes Emergency Contact Name',
        'Line items: Custom attributes Emergency Contact Phone Number',
        'Line items: Custom attributes Gender Identity ',
        'Line items: Custom attributes Have you ever played any sport(s) with B.A.R.S. before?',
        "Line items: Custom attributes Have you played the sport you're registering for with B.A.R.S?",
        'Line items: Custom attributes If you chose "Two or More Races", please identify those races.',
        'Line items: Custom attributes Last Name',
        'Line items: Custom attributes Please select the one that best applies: Which racial categories best describe you?',
        'Line items: Custom attributes Preferred First Name',
        'Line items: Custom attributes Pronouns',
        'Line items: Custom attributes Shirt Size',
        'Line items: Custom attributes What is your self rated skill ranking?',
        'Line items: Custom attributes: Best Contact Phone Number (Cell Phone Number Preferred)',
        'isCanceled',
        'totalRefunded',
    ]


def order_to_csv_row(order_data: Dict[str, Any]) -> List[str]:
    """Convert order data to CSV row matching the Shopify export format.
    
    Args:
        order_data: Order dictionary (from __json_data__ or similar)
        
    Returns:
        List of string values for CSV row
    """
    # Get first line item (assuming one line item per order for this use case)
    line_items = order_data.get('lineItems', {})
    if isinstance(line_items, dict):
        edges = line_items.get('edges', [])
        line_item = edges[0]['node'] if edges else {}
    else:
        # Handle Connection format with nodes
        nodes = getattr(line_items, 'nodes', []) if hasattr(line_items, 'nodes') else []
        if nodes:
            line_item = nodes[0].__json_data__ if hasattr(nodes[0], '__json_data__') else {}
        else:
            line_item = {}
    
    # Get discount code
    discount_apps = order_data.get('discountApplications', {})
    discount_code = ''
    if isinstance(discount_apps, dict):
        edges = discount_apps.get('edges', [])
        for edge in edges:
            node = edge.get('node', {})
            if 'code' in node:
                discount_code = node.get('code', '')
                break
            if not discount_code and 'title' in node:
                discount_code = node.get('title', '')
    else:
        # Handle Connection format
        nodes = getattr(discount_apps, 'nodes', []) if hasattr(discount_apps, 'nodes') else []
        for node in nodes:
            node_data = node.__json_data__ if hasattr(node, '__json_data__') else {}
            if 'code' in node_data:
                discount_code = node_data.get('code', '')
                break
            if not discount_code and 'title' in node_data:
                discount_code = node_data.get('title', '')
    
    # Get billing address
    billing = order_data.get('billingAddress', {}) or {}
    if hasattr(billing, '__json_data__'):
        billing = billing.__json_data__
    
    # Format updatedAt date (M/D/YYYY format)
    updated_at = format_date_for_csv(order_data.get('updatedAt'))
    
    # Fully paid (true if financial status is PAID)
    fully_paid = str(order_data.get('displayFinancialStatus', '') == 'PAID').lower()
    
    # Phone - prefer billing address phone, fallback to order phone
    phone = billing.get('phone') or order_data.get('phone') or ''
    
    # Get line item data (handle both dict and object formats)
    if isinstance(line_item, dict):
        line_item_data = line_item
    else:
        line_item_data = line_item.__json_data__ if hasattr(line_item, '__json_data__') else {}
    
    variant = line_item_data.get('variant', {})
    if hasattr(variant, '__json_data__'):
        variant = variant.__json_data__
    
    product = line_item_data.get('product', {})
    if hasattr(product, '__json_data__'):
        product = product.__json_data__
    
    # Build CSV row matching the exact column order
    row = [
        order_data.get('name', ''),  # Order Number
        order_data.get('email', ''),  # Email
        updated_at,  # Updated at
        fully_paid,  # Fully paid
        order_data.get('displayFulfillmentStatus', ''),  # Fulfillment status
        str(order_data.get('subtotalLineItemsQuantity', 0)),  # Current subtotal quantity
        discount_code,  # Discount code
        line_item_data.get('name', ''),  # Line items: Name
        order_data.get('totalPriceSet', {}).get('shopMoney', {}).get('amount', ''),  # Total price
        variant.get('sku', '') if isinstance(variant, dict) else getattr(variant, 'sku', ''),  # Line items: SKU
        product.get('vendor', '') if isinstance(product, dict) else getattr(product, 'vendor', ''),  # Line items: Vendor
        product.get('descriptionHtml', '') if isinstance(product, dict) else getattr(product, 'descriptionHtml', ''),  # Line items: Product description HTML
        line_item_data.get('title', ''),  # Line items: Title
    ]
    
    row.extend([
        variant.get('title', '') if isinstance(variant, dict) else getattr(variant, 'title', ''),  # Line items: Variant title
        billing.get('firstName', ''),  # Billing address: First name
        billing.get('lastName', ''),  # Billing address: Last name
        billing.get('address1', ''),  # Billing address: Address first line
        billing.get('city', ''),  # Billing address: City
        billing.get('zip', ''),  # Billing address: Zip
        billing.get('country', ''),  # Billing address: Country
        phone,  # Phone
        get_custom_attribute_value(line_item_data, '_Form Fields'),  # Line items: Custom attributes _Form Fields
        get_custom_attribute_value(line_item_data, 'Are you interested in being a captain?'),  # Line items: Custom attributes Are you interested in being a captain?
        get_custom_attribute_value(line_item_data, 'Are you interested in reffing?'),  # Line items: Custom attributes Are you interested in reffing?
        get_custom_attribute_value(line_item_data, 'Best Contact Email Address'),  # Line items: Custom attributes Best Contact Email Address
        get_custom_attribute_value(line_item_data, 'Best Contact Number (Cell Phone Number Preferred)'),  # Line items: Custom attributes Best Contact Number (Cell Phone Number Preferred)
        get_custom_attribute_value(line_item_data, 'Date of Birth'),  # Line items: Custom attributes Date of Birth
        get_custom_attribute_value(line_item_data, 'Emergency Contact Name'),  # Line items: Custom attributes Emergency Contact Name
        get_custom_attribute_value(line_item_data, 'Emergency Contact Phone Number'),  # Line items: Custom attributes Emergency Contact Phone Number
        get_custom_attribute_value(line_item_data, 'Gender Identity '),  # Line items: Custom attributes Gender Identity (note the trailing space)
        get_custom_attribute_value(line_item_data, 'Have you ever played any sport(s) with B.A.R.S. before?'),  # Line items: Custom attributes Have you ever played any sport(s) with B.A.R.S. before?
        get_custom_attribute_value(line_item_data, "Have you played the sport you're registering for with B.A.R.S?"),  # Line items: Custom attributes Have you played the sport you're registering for with B.A.R.S?
        get_custom_attribute_value(line_item_data, 'If you chose "Two or More Races", please identify those races.'),  # Line items: Custom attributes If you chose "Two or More Races", please identify those races.
        get_custom_attribute_value(line_item_data, 'Last Name'),  # Line items: Custom attributes Last Name
        get_custom_attribute_value(line_item_data, 'Please select the one that best applies: Which racial categories best describe you?'),  # Line items: Custom attributes Please select the one that best applies: Which racial categories best describe you?
        get_custom_attribute_value(line_item_data, 'Preferred First Name'),  # Line items: Custom attributes Preferred First Name
        get_custom_attribute_value(line_item_data, 'Pronouns'),  # Line items: Custom attributes Pronouns
        get_custom_attribute_value(line_item_data, 'Shirt Size'),  # Line items: Custom attributes Shirt Size
        get_custom_attribute_value(line_item_data, 'What is your self rated skill ranking?'),  # Line items: Custom attributes What is your self rated skill ranking?
        get_custom_attribute_value(line_item_data, 'Best Contact Phone Number (Cell Phone Number Preferred)'),  # Line items: Custom attributes: Best Contact Phone Number (Cell Phone Number Preferred)
    ])
    
    # Check if order is canceled
    is_canceled = 'true' if order_data.get('cancelledAt') else 'false'
    
    # Calculate total refunded amount
    refunds = order_data.get('refunds', [])
    total_refunded = '0.00'
    if refunds:
        total = 0.0
        for refund in refunds:
            refund_data = refund.__json_data__ if hasattr(refund, '__json_data__') else refund
            total_refunded_set = refund_data.get('totalRefundedSet', {})
            shop_money = total_refunded_set.get('shopMoney', {})
            amount_str = shop_money.get('amount', '0')
            try:
                total += float(amount_str)
            except (ValueError, TypeError):
                continue
        total_refunded = f"{total:.2f}"
    
    row.extend([is_canceled, total_refunded])
    
    return row

