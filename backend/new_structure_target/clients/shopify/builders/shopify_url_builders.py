from config import config
import logging

logger = logging.getLogger(__name__)

def normalize_order_number(order_number: str) -> str:
    """Normalize order number"""
    return order_number if order_number.startswith("#") else f"#{order_number}"

def build_order_url(order_id: str) -> str:
    """Create Shopify admin order URL for Slack"""
    order_id_str = str(order_id)
    order_id_digits = order_id_str.split("/")[-1] if "/" in order_id_str else order_id_str
    return f"{config.Shopify.admin_url}/orders/{order_id_digits}" if order_id_digits != "Unknown" else f"{config.Shopify.admin_url}/orders"

def build_product_url(product_id: str) -> str:
    """Create Shopify admin product URL for Slack"""
    product_id_str = str(product_id)
    product_id_digits = (
        product_id_str.split("/")[-1] if "/" in product_id_str else product_id_str
    )
    logger.info(f"🔗 DEBUG SHOPIFY_URL_BUILDERS: Product ID Digits: {product_id_digits}, admin_url: {config.Shopify.admin_url}")
    return f"{config.Shopify.admin_url}/products/{product_id_digits}" if product_id_digits != "Unknown" else f"{config.Shopify.admin_url}/products"

def build_customer_url(customer_id: str) -> str:
    """Create Shopify admin customer URL for Slack"""
    customer_id_str = str(customer_id)
    customer_id_digits = (
        customer_id_str.split("/")[-1] if "/" in customer_id_str else customer_id_str
    )
    return f"{config.Shopify.admin_url}/customers/{customer_id_digits}" if customer_id_digits != "Unknown" else f"{config.Shopify.admin_url}/customers"