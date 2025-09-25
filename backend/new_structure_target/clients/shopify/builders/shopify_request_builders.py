from config import config
from typing import Dict, Any

shopify_token = config.Shopify.token
shopify_graphql_url = config.Shopify.graphql_url
shopify_rest_url = config.Shopify.rest_url

def build_shopify_request_headers(token: str = shopify_token) -> Dict[str, str]:
    """Build default Shopify request headers"""
    return {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": token
    }

def build_shopify_get_product_details_request(payload: Dict[str, str], token: str = shopify_token) -> Dict[str, Any]:
    """Build default Shopify request"""
    if not payload:
        raise ValueError("Payload is required")
    return {
        "url": shopify_graphql_url,
        "method": "POST",
        "headers": build_shopify_request_headers(token),
        "payload": payload
    }