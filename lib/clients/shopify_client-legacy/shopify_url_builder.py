"""
Shopify Admin URL Builder

Utility for constructing Shopify admin URLs for various resources.
"""

import os
from typing import Optional


def get_shopify_store_id() -> str:
    """Get Shopify store ID from environment."""
    return os.getenv("SHOPIFY_STORE_ID", "09fe59-3")


def extract_shopify_id(gid_or_id: str) -> str:
    """
    Extract numeric ID from Shopify GID or return as-is if already numeric.
    
    Args:
        gid_or_id: Either a GID (gid://shopify/Resource/123) or numeric ID (123)
    
    Returns:
        Numeric ID string
    
    Examples:
        >>> extract_shopify_id("gid://shopify/Order/6069195636830")
        '6069195636830'
        
        >>> extract_shopify_id("6069195636830")
        '6069195636830'
    """
    if gid_or_id.startswith("gid://shopify/"):
        return gid_or_id.split("/")[-1]
    return gid_or_id


def build_shopify_admin_url(
    resource_type: str,
    resource_id: str,
    store_id: Optional[str] = None
) -> str:
    """
    Build Shopify admin URL for a resource.
    
    Args:
        resource_type: Type of resource (e.g., "orders", "products", "customers")
        resource_id: Numeric ID of the resource (with or without gid prefix)
        store_id: Optional store ID (defaults to environment variable)
    
    Returns:
        Full Shopify admin URL
    
    Examples:
        >>> build_shopify_admin_url("orders", "6069195636830")
        'https://admin.shopify.com/store/09fe59-3/orders/6069195636830'
        
        >>> build_shopify_admin_url("products", "gid://shopify/Product/7350462185566")
        'https://admin.shopify.com/store/09fe59-3/products/7350462185566'
    """
    if not store_id:
        store_id = get_shopify_store_id()
    
    # Extract numeric ID from gid if provided
    resource_id = extract_shopify_id(resource_id)
    
    return f"https://admin.shopify.com/store/{store_id}/{resource_type}/{resource_id}"
