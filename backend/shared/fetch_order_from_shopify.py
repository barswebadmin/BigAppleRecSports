"""
Shared order fetching utilities to prevent circular imports between services.

This module provides common order fetching functionality that can be used by
both OrdersService and RefundsService without creating circular dependencies.
"""

from typing import Dict, Any, Optional
from modules.orders.models import FetchOrderRequest
from modules.integrations.shopify import ShopifyClient
from modules.integrations.shopify.builders import build_order_fetch_request_payload


def fetch_order_from_shopify(request_args: FetchOrderRequest) -> Dict[str, Any]:
    """
    Fetch order details with additional validation and error handling.
    
    This version provides more comprehensive error handling and validation
    suitable for service-level operations.
    
    Args:
        request_args: FetchOrderRequest with order_id, order_number, or email
        
    Returns:
        Dict containing order data with validation status
    """
    try:
        shopify_client = ShopifyClient()
        
        payload = build_order_fetch_request_payload(request_args)
        
        # Use send_request which returns a ShopifyResponse object
        result = shopify_client.send_request(payload)
        
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
