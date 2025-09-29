"""
Shared order fetching utilities to prevent circular imports between services.

This module provides common order fetching functionality that can be used by
both OrdersService and RefundsService without creating circular dependencies.
"""

from typing import Dict, Any, Optional
from backend.modules.integrations.shopify.models.requests import FetchOrderRequest
from backend.modules.integrations.shopify import ShopifyClient
from backend.modules.integrations.shopify.builders import build_order_fetch_request_payload


def fetch_order_from_shopify(request_args: FetchOrderRequest, client: Optional[ShopifyClient] = None) -> Dict[str, Any]:
    """
    Fetch order details from Shopify using FetchOrderRequest.
    
    This is a shared utility function that can be used by any service
    that needs to fetch order data from Shopify.
    
    Args:
        request_args: FetchOrderRequest with order_id, order_number, or email
        
    Returns:
        Dict containing order data or error information
        
    Raises:
        Exception: If the Shopify request fails
    """
    try:
        if client is None:
            client = ShopifyClient()
        payload = build_order_fetch_request_payload(request_args)
        response = client.send_request(payload)
        
        if response.success and response.data:
            return {"success": True, "data": response.data}
        else:
            return {
                "success": False, 
                "message": response.message or "Failed to fetch order from Shopify"
            }
            
    except Exception as e:
        return {"success": False, "message": str(e)}


def fetch_order_details_with_validation(request_args: FetchOrderRequest, client: Optional[ShopifyClient] = None) -> Dict[str, Any]:
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
        result = fetch_order_from_shopify(request_args, client)
        
        if not result["success"]:
            return result
            
        # Additional validation can be added here
        order_data = result["data"]
        
        # Validate order exists and has required fields
        if not order_data or not order_data.get("orders", {}).get("edges"):
            return {
                "success": False,
                "message": "No order found matching the provided criteria"
            }
            
        return result
        
    except Exception as e:
        return {"success": False, "message": f"Error fetching order: {str(e)}"}
