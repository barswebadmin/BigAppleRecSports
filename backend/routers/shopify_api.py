"""
Shopify API Router

Provides RESTful API endpoints for Shopify operations including orders, products, and customers.
This router delegates to the ShopifyAPIController for business logic and maintains consistency
with existing CLI command functionality.
"""

from typing import Dict, Any
import logging

from backend.modules.integrations.shopify.controllers.api_controller import ShopifyAPIController
from backend.modules.integrations.shopify.models import (
    OrderResponse,
    OrderListResponse,
    OrderCancelRequest,
    OrderRefundRequest,
    OrderDiscountRequest,
    ProductResponse,
    ProductListResponse,
    CustomerResponse,
    CustomerListResponse
)
from backend.shared.api_models import (
    SuccessResponse,
    PaginationParams,
    FilterParams,
    SortParams,
    ExceptionMapper
)

logger = logging.getLogger(__name__)

# Note: FastAPI imports removed for now due to missing dependency
# This will be added back when FastAPI is available in the environment

controller = ShopifyAPIController()


# ============================================================================
# ORDER ENDPOINTS
# ============================================================================

async def list_orders(
    pagination: PaginationParams,
    filters: FilterParams,
    sort: SortParams
) -> OrderListResponse:
    """
    List Shopify orders with pagination and filtering.

    This endpoint provides the same functionality as the CLI command:
    `bars shopify orders list`
    """
    try:
        return await controller.list_orders(
            limit=pagination.limit,
            offset=pagination.offset,
            start_date=filters.start_date,
            end_date=filters.end_date,
            status=filters.status,
            sort_by=sort.sort_by,
            sort_order=sort.sort_order
        )
    except Exception as e:
        api_error = ExceptionMapper.map_exception_to_api_error(e)
        # For now, just re-raise the original exception since FastAPI is not available
        raise e


async def get_order(identifier: str) -> OrderResponse:
    """
    Get a specific Shopify order by identifier.

    This endpoint provides the same functionality as the CLI command:
    `bars shopify order get {identifier}`
    """
    try:
        return await controller.get_order(identifier=identifier)
    except Exception as e:
        api_error = ExceptionMapper.map_exception_to_api_error(e)
        # For now, just re-raise the original exception since FastAPI is not available
        raise e


# ============================================================================
# HEALTH CHECK
# ============================================================================

async def health_check() -> Dict[str, Any]:
    """Health check endpoint for the Shopify API service."""
    return {
        "status": "healthy",
        "service": "shopify-api",
        "timestamp": controller.format_success_response({})["timestamp"]
    }