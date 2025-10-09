"""
Shared product fetching utilities to prevent circular imports between services.

This module provides common product fetching functionality that can be used by
both ProductsService and OrdersService without creating circular dependencies.
"""

from typing import Dict, Any, Optional
from modules.products.models import FetchProductRequest

def fetch_product_from_shopify(request_args: FetchProductRequest) -> Dict[str, Any]:
    """
    Fetch product details with additional validation and error handling.
    
    This version provides more comprehensive error handling and validation
    suitable for service-level operations.
    
    Args:
        request_args: FetchProductRequest with product_id, product_handle
        
    Returns:
        Dict containing product data with validation status
    """
    try:
        from modules.integrations.shopify.shopify_orchestrator import ShopifyOrchestrator

        shopify = ShopifyOrchestrator()
        
        payload = build_product_fetch_request_payload(request_args)
        
        # Use send_request which returns a ShopifyResponse object
        result = shopify.fetch_product_details(request_args)
        
        if not result.success:
            return {
                "success": False,
                "message": result.message or "Failed to fetch order from Shopify"
            }
            
        # Additional validation can be added here
        order_data = result.data
        
        # Validate order exists and has required fields
        if not order_data or not order_data.get("orders", {}).get("edges"):
            return {
                "success": False,
                "message": "No order found matching the provided criteria"
            }
            
        return {
            "success": True,
            "data": order_data
        }
        
    except Exception as e:
        return {"success": False, "message": f"Error fetching order: {str(e)}"}


def fetch_recent_products_from_shopify() -> Dict[str, Any]:
    """
    Fetch recent products from Shopify
    """
    from modules.integrations.shopify.shopify_orchestrator import ShopifyOrchestrator

    shopify = ShopifyOrchestrator()
    return shopify.fetch_recent_products()
