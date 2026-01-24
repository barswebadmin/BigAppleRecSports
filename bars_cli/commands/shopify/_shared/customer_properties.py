"""
Extract customer properties (birthday, pronouns) from order line items.

Moved from bars-scripts/get_bday.py and bars-scripts/get_pronouns.py
"""
import concurrent.futures
from typing import Dict, Any, List, Tuple, Optional

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.modules.integrations.shopify.services.shopify_service import ShopifyService
else:
    ShopifyService = Any


def get_order_line_item_properties(shopify_service: ShopifyService, order_id: str) -> List[Dict[str, str]]:
    """
    Fetch line item properties for a specific order.
    
    Args:
        shopify_service: ShopifyService instance
        order_id: Order ID (gid://shopify/Order/...)
        
    Returns:
        List of custom attribute dictionaries with 'key' and 'value' keys
    """
    # Use the service method which handles order ID normalization
    return shopify_service.get_order_line_item_properties(order_id)


def extract_birthday_with_name(properties: List[Dict[str, str]]) -> List[Tuple[str, str, str]]:
    """
    Extract birthdays with associated names from properties.
    
    Args:
        properties: List of custom attribute dictionaries
        
    Returns:
        List of (birthday, first_name, last_name) tuples
    """
    birthday = None
    first_name = ""
    last_name = ""
    
    for prop in properties:
        key = prop.get("key", "").lower()
        value = prop.get("value", "").strip()
        
        if "date of birth" in key and value:
            birthday = value
        elif "first name" in key and value and not first_name:
            first_name = value
        elif "last name" in key and value and not last_name:
            last_name = value
    
    if birthday:
        return [(birthday, first_name, last_name)]
    return []


def extract_pronouns_with_name(properties: List[Dict[str, str]]) -> List[Tuple[str, str, str]]:
    """
    Extract pronouns with associated names from properties.
    
    Args:
        properties: List of custom attribute dictionaries
        
    Returns:
        List of (pronouns_lowercase, first_name, last_name) tuples
    """
    pronouns = None
    first_name = ""
    last_name = ""
    
    for prop in properties:
        key = prop.get("key", "").lower()
        value = prop.get("value", "").strip()
        
        if "pronouns" in key and value:
            # Lowercase the pronouns value
            pronouns = value.lower()
        elif "first name" in key and value and not first_name:
            first_name = value
        elif "last name" in key and value and not last_name:
            last_name = value
    
    if pronouns:
        return [(pronouns, first_name, last_name)]
    return []


def get_customer_orders(customer: Any) -> List[str]:
    """
    Extract order IDs from customer data.
    
    Args:
        customer: Customer object (sgqlc Type instance)
        
    Returns:
        List of order IDs (gid://shopify/Order/...)
    """
    orders_conn = getattr(customer, 'orders', None)
    if not orders_conn:
        return []
    
    nodes = getattr(orders_conn, 'nodes', None)
    if not nodes:
        return []
    
    return [getattr(order, 'id', '') for order in nodes if getattr(order, 'id', None)]


def get_customer_orders_with_dates(customer: Any) -> List[Tuple[str, str]]:
    """
    Extract order IDs with created_at dates from customer data.
    
    Args:
        customer: Customer object (sgqlc Type instance)
        
    Returns:
        List of (order_id, created_at) tuples
    """
    orders_conn = getattr(customer, 'orders', None)
    if not orders_conn:
        return []
    
    nodes = getattr(orders_conn, 'nodes', None)
    if not nodes:
        return []
    
    return [
        (getattr(order, 'id', ''), getattr(order, 'createdAt', ''))
        for order in nodes
        if getattr(order, 'id', None) and getattr(order, 'createdAt', None)
    ]


def fetch_birthdays_with_names(
    shopify_service: ShopifyService,
    order_ids: List[str]
) -> List[Tuple[str, str, str]]:
    """
    Fetch birthdays with associated names from all orders concurrently.
    
    Args:
        shopify_service: ShopifyService instance
        order_ids: List of order IDs
        
    Returns:
        List of (birthday, first_name, last_name) tuples
    """
    birthday_records = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_order = {
            executor.submit(get_order_line_item_properties, shopify_service, order_id): order_id
            for order_id in order_ids
        }
        
        for future in concurrent.futures.as_completed(future_to_order):
            try:
                properties = future.result()
                records = extract_birthday_with_name(properties)
                birthday_records.extend(records)
            except Exception as e:
                import sys
                print(f"Error fetching order: {e}", file=sys.stderr)
    
    return birthday_records


def fetch_pronouns_with_names(
    shopify_service: ShopifyService,
    orders_with_dates: List[Tuple[str, str]]
) -> List[Tuple[str, str, str, str]]:
    """
    Fetch pronouns with associated names and dates from all orders concurrently.
    
    Args:
        shopify_service: ShopifyService instance
        orders_with_dates: List of (order_id, created_at) tuples
        
    Returns:
        List of (pronouns, first_name, last_name, created_at) tuples
    """
    pronouns_records = []
    
    # Process orders concurrently while preserving date info
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_order = {
            executor.submit(get_order_line_item_properties, shopify_service, order_id): (order_id, created_at)
            for order_id, created_at in orders_with_dates
        }
        
        for future in concurrent.futures.as_completed(future_to_order):
            order_id, created_at = future_to_order[future]
            try:
                properties = future.result()
                records = extract_pronouns_with_name(properties)
                # Add created_at to each record
                for pronouns, first_name, last_name in records:
                    pronouns_records.append((pronouns, first_name, last_name, created_at))
            except Exception as e:
                import sys
                print(f"Error fetching order {order_id}: {e}", file=sys.stderr)
    
    return pronouns_records


def process_customer_birthday(
    shopify_service: ShopifyService,
    customer: Any
) -> List[Tuple[str, str, str]]:
    """
    Process a customer and extract their birthdays from orders.
    
    Args:
        shopify_service: ShopifyService instance
        customer: Customer object (sgqlc Type instance)
        
    Returns:
        List of (birthday, first_name, last_name) tuples, sorted by birthday then name
    """
    order_ids = get_customer_orders(customer)
    
    if not order_ids:
        return []
    
    birthday_records = fetch_birthdays_with_names(shopify_service, order_ids)
    
    # Sort by birthday, then by name
    sorted_records = sorted(birthday_records, key=lambda x: (x[0], x[1], x[2]))
    
    return sorted_records


def process_customer_pronouns(
    shopify_service: ShopifyService,
    customer: Any
) -> List[Tuple[str, str, str, str]]:
    """
    Process a customer and extract their pronouns from orders.
    
    Args:
        shopify_service: ShopifyService instance
        customer: Customer object (sgqlc Type instance)
        
    Returns:
        List of (pronouns, first_name, last_name, created_at) tuples, sorted by most recent first
    """
    orders_with_dates = get_customer_orders_with_dates(customer)
    
    if not orders_with_dates:
        return []
    
    pronouns_records = fetch_pronouns_with_names(shopify_service, orders_with_dates)
    
    # Sort by created_at (most recent first), then by name
    # created_at is ISO 8601 format so string sort works correctly
    sorted_records = sorted(pronouns_records, key=lambda x: (x[3], x[1], x[2]), reverse=True)
    
    return sorted_records

