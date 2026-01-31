"""
Orders API Router

Handles order operations across the system.
Currently delegates to Shopify service, will migrate to dedicated orders service.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import ValidationError

from modules.integrations.shopify.controllers.api_controller import ShopifyAPIController
from modules.integrations.shopify.models.requests import ShopifyOrderIdentifierRequest
from shared.api_models import SuccessResponse, ValidationAPIError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])

# TODO: Migrate to OrdersController when orders service is implemented
_shopify_controller = ShopifyAPIController()

# =============================================================================
# ORDERS
# =============================================================================

@router.get("", response_model=SuccessResponse)
async def get_order(
    number: Optional[str] = Query(
        None,
        description="Order number (5 digits, e.g., 12345)",
        min_length=5,
        max_length=5
    ),
    id: Optional[str] = Query(
        None,
        description="Order ID (11-16 digits)",
        min_length=11,
        max_length=16
    ),
    reason: Optional[str] = Query(
        None,
        description="Operation reason: 'cancel' to validate cancellation eligibility, 'refund' to get refund calculations"
    ),
    submitted_at: Optional[str] = Query(
        None,
        description="ISO 8601 datetime string for refund calculation (e.g., '2025-01-30T15:08:40Z'). Defaults to current time if not provided."
    )
):
    """
    Get order details by order number or ID.
    
    Query Parameters (provide ONE identifier):
    - number: Order number (5 digits, e.g., 12345)
    - id: Order ID (11-16 digits, e.g., 1234567890)
    - reason: Optional operation reason:
        - 'cancel': Validates cancellation eligibility, returns cancellation status and payment summary
        - 'refund': Returns refund calculations for both refund types, cancellation status, and payment summary
    - submitted_at: Optional ISO 8601 datetime for refund calculation (only used with reason='refund')
    
    Returns order data with line items, customer info, and payment summary.
    
    If reason='cancel', returns enriched data:
    - 200: Order is eligible for cancellation
    - 202: Order already canceled (warning)
    - 404: Order not found
    
    If reason='refund', returns enriched data with refund calculations:
    - 200: Order has refundable amount
    - 202: No refundable amount remaining (warning)
    - 404: Order not found
    
    Raises:
    - 400: Invalid parameters or missing both number and id
    - 404: Order not found
    - 500: Server error
    
    TODO: Migrate to OrdersService when implemented
    """
    # Validate that exactly one parameter is provided
    if not number and not id:
        raise HTTPException(
            status_code=400,
            detail="Must provide either 'number' or 'id' query parameter"
        )
    
    if number and id:
        raise HTTPException(
            status_code=400,
            detail="Cannot provide both 'number' and 'id' query parameters"
        )
    
    # Determine which identifier was provided
    if number:
        identifier = number
        identifier_type = "order_number"
    else:
        identifier = id
        identifier_type = "order_id"
    
    try:
        # Validate identifier format using Pydantic model
        try:
            identifier_request = ShopifyOrderIdentifierRequest(identifier=identifier)
            parsed = identifier_request.parse()
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ValidationAPIError as e:
            raise HTTPException(status_code=400, detail=e.message)
        
        # Route based on reason parameter
        if reason and reason.lower() == 'cancel':
            # Validate cancellation eligibility with enriched data
            result = await _shopify_controller.validate_order_cancellation(identifier, submitted_at)
        elif reason and reason.lower() == 'refund':
            # Get refund calculations with enriched data
            result = await _shopify_controller.validate_order_refund(identifier, submitted_at)
        elif reason:
            # Unexpected reason value - log warning and proceed with standard retrieval
            logger.warning(f"Unexpected 'reason' parameter value: '{reason}'. Expected 'cancel' or 'refund'. Ignoring and proceeding with standard order retrieval.")
            result = await _shopify_controller.get_order(identifier)
        else:
            # Standard order retrieval (no reason provided)
            result = await _shopify_controller.get_order(identifier)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{order_id}", response_model=SuccessResponse)
async def cancel_order(
    order_id: str,
    reason: Optional[str] = Query(default="CUSTOMER", description="Cancellation reason"),
    notify_customer: bool = Query(default=False, description="Whether to notify customer"),
    refund: bool = Query(default=False, description="Whether to refund"),
    restock: bool = Query(default=False, description="Whether to restock"),
    staff_note: Optional[str] = Query(default=None, description="Staff note")
):
    """
    Cancel an order by ID.
    
    Path Parameters:
    - order_id: Full Shopify order ID (e.g., gid://shopify/Order/1234567890)
    
    Query Parameters:
    - reason: Cancellation reason (CUSTOMER, FRAUD, INVENTORY, DECLINED, OTHER)
    - notify_customer: Whether to notify the customer (default: False)
    - refund: Whether to automatically refund (default: False)
    - restock: Whether to restock inventory (default: False)
    - staff_note: Optional staff note
    
    Returns success response with job data if successful.
    
    Raises:
    - 422: Shopify returned user errors (e.g., order already canceled)
    - 500: Server error
    
    TODO: Migrate to OrdersService when implemented
    """
    try:
        result = await _shopify_controller.cancel_order(
            order_id=order_id,
            reason=reason,
            notify_customer=notify_customer,
            refund=refund,
            restock=restock,
            staff_note=staff_note
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
