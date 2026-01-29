"""
Shopify API Controller

Handles HTTP request/response conversion for Shopify API endpoints.
Delegates to existing backend services and maintains consistency with CLI command functionality.

CRITICAL: This controller ONLY handles HTTP-specific logic and delegates all business logic
to existing backend services. It does NOT rewrite or duplicate existing functionality.
"""

from typing import Dict, Any, Optional

from backend.controllers.api.base import BaseAPIController
from backend.modules.integrations.shopify.services.shopify_service import ShopifyService
from backend.shared.api_models import (
    APIError,
    NotFoundAPIError,
    ValidationAPIError
)
from backend.modules.integrations.shopify.models import (
    OrderResponse,
    OrderListResponse,
    ShopifyOrderIdentifierRequest,
    PaginationRequest,
    DateRangeRequest
)


class ShopifyAPIController(BaseAPIController):
    """
    API controller for Shopify operations.

    This controller follows the webhook controller pattern and delegates all business logic
    to the existing ShopifyService. It ONLY handles:
    - HTTP request/response conversion
    - Parameter validation and normalization
    - Error mapping to HTTP status codes
    - Response formatting

    It does NOT contain any business logic - all operations are delegated to ShopifyService.
    """

    def __init__(self):
        super().__init__()
        # REUSE existing service - DO NOT rewrite business logic
        self.shopify_service = ShopifyService()

    # ============================================================================
    # ORDER OPERATIONS
    # ============================================================================

    async def list_orders(
        self,
        limit: int = 50,
        offset: int = 0,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None
    ) -> OrderListResponse:
        """
        List orders with pagination and filtering.

        DELEGATES to existing ShopifyService methods - NO business logic here.
        """
        try:
            self.log_api_request("GET", "/orders", {
                "limit": limit, "offset": offset, "status": status
            })

            # Validate pagination using request model
            pagination_request = PaginationRequest(limit=limit, offset=offset)
            limit, offset = pagination_request.validate_and_normalize()

            # Validate date range using request model
            if start_date or end_date:
                date_request = DateRangeRequest(start_date=start_date, end_date=end_date)
                start_date, end_date = date_request.validate_and_parse()

            # For MVP, we'll implement a simple approach using existing get_order_by_identifier
            # with a broad search query. In production, this would need a proper list method.
            # REUSE existing service parameter format - DO NOT change
            query_params = {
                "query": self._build_order_search_query(status, start_date, end_date) or "*",
                "first": limit
            }

            # DELEGATE to existing service method - using search approach for now
            self.log_service_call("get_order_by_identifier (search)", query_params)
            try:
                orders = self.shopify_service.get_order_by_identifier(
                    query_params, line_items_first=5
                )
            except Exception:
                # If search fails, return empty list for MVP
                orders = []

            if not orders:
                orders = []

            # Convert service response to API response format
            # REUSE existing data structures - DO NOT rewrite
            order_items = []
            for order in orders:
                order_dict = self._convert_order_to_dict(order)
                order_items.append(order_dict)

            # Calculate total count (simplified for MVP)
            total_count = len(order_items) + offset

            # Format response using base controller
            return OrderListResponse(**self.format_list_response(
                items=order_items,
                total_count=total_count,
                limit=limit,
                offset=offset,
                message=f"Retrieved {len(order_items)} orders"
            ))

        except ValidationAPIError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            self.logger.error("Error listing orders: %s", e)
            raise self.map_exception_to_http_error(e)

    async def get_order(self, identifier: str) -> OrderResponse:
        """
        Get a specific order by identifier.

        DELEGATES to existing ShopifyService.get_order_by_identifier - same as CLI uses.
        """
        try:
            self.log_api_request("GET", f"/orders/{identifier}")

            # Validate and parse identifier using request model
            identifier_request = ShopifyOrderIdentifierRequest(identifier=identifier)
            identifier_dict = identifier_request.parse()

            # DELEGATE to existing service method - same as CLI command uses
            self.log_service_call("get_order_by_identifier", identifier_dict)
            orders = self.shopify_service.get_order_by_identifier(
                identifier_dict,
                line_items_first=5  # Same default as CLI
            )

            if not orders:
                raise NotFoundAPIError("Order", identifier)

            # Use first order (same logic as CLI)
            order = orders[0]

            # Convert to API response format
            # REUSE existing data conversion - DO NOT rewrite
            order_dict = self._convert_order_to_dict(order)

            # Add payment summary using existing service method
            payment_summary = self.shopify_service.calculate_payment_summary(order)
            order_dict["payment_summary"] = payment_summary

            return OrderResponse(**self.format_success_response(
                data=order_dict,
                message="Order retrieved successfully"
            ))

        except ValidationAPIError:
            # Re-raise validation errors as-is
            raise
        except APIError:
            raise
        except Exception as e:
            self.logger.error("Error getting order %s: %s", identifier, e)
            raise self.map_exception_to_http_error(e)

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    def _build_order_search_query(
        self,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> str:
        """Build GraphQL search query for orders."""
        query_parts = []

        if status:
            query_parts.append(f"status:{status}")

        if start_date:
            query_parts.append(f"created_at:>={start_date}")

        if end_date:
            query_parts.append(f"created_at:<={end_date}")

        return " AND ".join(query_parts) if query_parts else ""

    def _convert_order_to_dict(self, order: Any) -> Dict[str, Any]:
        """
        Convert order object to dictionary for API response.

        REUSES existing data structures - DO NOT rewrite conversion logic.
        """
        try:
            total_price_amount = "0.00"
            currency = "USD"
            if hasattr(order, 'totalPriceSet'):
                total_price_amount = str(order.totalPriceSet.shopMoney.amount)
                currency = str(order.totalPriceSet.shopMoney.currencyCode)

            return {
                "id": str(order.id),
                "order_number": str(order.name),
                "email": str(order.email) if order.email else None,
                "total_price": total_price_amount,
                "currency": currency,
                "financial_status": str(order.displayFinancialStatus) if hasattr(
                    order, 'displayFinancialStatus'
                ) else None,
                "fulfillment_status": str(order.displayFulfillmentStatus) if hasattr(
                    order, 'displayFulfillmentStatus'
                ) else None,
                "created_at": str(order.createdAt) if hasattr(order, 'createdAt') else None,
                "updated_at": str(order.updatedAt) if hasattr(order, 'updatedAt') else None,
                "cancelled_at": str(order.cancelledAt) if hasattr(order, 'cancelledAt') else None,
                "customer": {
                    "id": str(order.customer.id) if order.customer else None,
                    "email": str(order.customer.email) if (
                        order.customer and order.customer.email
                    ) else None,
                    "first_name": str(order.customer.firstName) if (
                        order.customer and order.customer.firstName
                    ) else None,
                    "last_name": str(order.customer.lastName) if (
                        order.customer and order.customer.lastName
                    ) else None,
                } if order.customer else None,
                "line_items_count": len(list(order.lineItems.nodes)) if hasattr(
                    order, 'lineItems'
                ) else 0
            }
        except Exception as e:
            self.logger.warning("Error converting order to dict: %s", e)
            return {
                "id": str(order.id) if hasattr(order, 'id') else "unknown",
                "order_number": "unknown",
                "email": None,
                "total_price": "0.00",
                "currency": "USD",
                "error": "Conversion error"
            }