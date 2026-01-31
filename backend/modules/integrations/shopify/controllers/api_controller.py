"""
Shopify API Controller

Handles HTTP request/response conversion for Shopify API endpoints.
Delegates to existing backend services and maintains consistency with CLI command functionality.

CRITICAL: This controller ONLY handles HTTP-specific logic and delegates all business logic
to existing backend services. It does NOT rewrite or duplicate existing functionality.
"""

from typing import Dict, Any, Optional

from controllers.api.base import BaseAPIController
from modules.integrations.shopify.services.shopify_service import ShopifyService
from shared.api_models import (
    APIError,
    NotFoundAPIError,
    ValidationAPIError
)
from modules.integrations.shopify.models import (
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
        Returns full order object as JSON without filtering.
        """
        try:
            self.log_api_request("GET", f"/orders?identifier={identifier}")

            # Parse identifier to determine type and build query
            identifier_type, query_str = self._parse_order_identifier(identifier)

            # Build query_params dict for service (same format as CLI uses)
            query_params = {
                "query": query_str,
                "first": 1,
                "not_found_message": f"Order not found: {identifier}",
                "identifier": identifier
            }

            # DELEGATE to existing service method - same as CLI command uses
            self.log_service_call("get_order_by_identifier", query_params)
            orders = self.shopify_service.get_order_by_identifier(
                query_params,
                line_items_first=50  # Fetch more line items for complete data
            )

            if not orders:
                raise NotFoundAPIError("Order", identifier)

            # Use first order (same logic as CLI)
            order = orders[0]

            # Convert sgqlc object to JSON dict (preserves all fields)
            import json
            if hasattr(order, '__json_data__'):
                order_dict = order.__json_data__
            else:
                # Fallback: use json serialization
                order_dict = json.loads(json.dumps(order, default=str))

            result = OrderResponse(**self.format_success_response(
                data=order_dict,
                message="Order retrieved successfully"
            ))
            return result

        except ValidationAPIError:
            # Re-raise validation errors as-is
            raise
        except APIError:
            raise
        except Exception as e:
            self.logger.error("Error getting order %s: %s", identifier, e)
            raise self.map_exception_to_http_error(e)

    async def validate_order_cancellation(self, identifier: str, submitted_at: Optional[str] = None) -> OrderResponse:
        """
        Validate if an order is eligible for cancellation with enriched data.

        DELEGATES to ShopifyService.enrich_order_with_cancellation_and_refund_info.
        Returns order data with cancellation status, payment summary, and refund calculations.
        
        Args:
            identifier: Order identifier (number or ID)
            submitted_at: Optional ISO 8601 datetime string for refund calculation
        """
        try:
            self.log_api_request("GET", f"/orders?identifier={identifier}&reason=cancel")

            # Parse identifier to determine type and build query
            identifier_type, query_str = self._parse_order_identifier(identifier)

            # Build query_params dict for service
            query_params = {
                "query": query_str,
                "first": 1,
                "not_found_message": f"Order not found: {identifier}",
                "identifier": identifier
            }

            # DELEGATE to enriched service method
            self.log_service_call("enrich_order_with_cancellation_and_refund_info", query_params)
            result = self.shopify_service.enrich_order_with_cancellation_and_refund_info(
                query_params, 
                reason="cancel",
                submitted_at=submitted_at
            )

            # Extract status code and data from result
            status_code = result.get("status_code", 500)
            success = result.get("success", False)
            message = result.get("message", "Unknown error")
            
            # Build response data with all enriched information
            response_data = {
                "order": result.get("order"),
                "cancellation_status": result.get("cancellation_status"),
                "payment_summary": result.get("payment_summary")
            }

            # Map status codes to HTTP exceptions or return success
            if status_code == 404:
                raise NotFoundAPIError("Order", identifier)
            elif status_code == 202:
                # Order already canceled - return with 202 status (warning, not error)
                from fastapi import Response
                return Response(
                    content=json.dumps({
                        "success": False,
                        "message": message,
                        "data": response_data
                    }),
                    status_code=202,
                    media_type="application/json"
                )
            elif status_code == 500:
                raise APIError(message)
            elif status_code == 200:
                # Order is eligible - return success with enriched data
                return OrderResponse(**self.format_success_response(
                    data=response_data,
                    message=message
                ))
            else:
                # Unexpected status code
                raise APIError(f"Unexpected status code: {status_code}")

        except ValidationAPIError:
            raise
        except APIError:
            raise
        except Exception as e:
            self.logger.error("Error validating order cancellation %s: %s", identifier, e)
            raise self.map_exception_to_http_error(e)
    
    async def validate_order_refund(self, identifier: str, submitted_at: Optional[str] = None) -> OrderResponse:
        """
        Validate if an order has refundable amount with enriched data including refund calculations.

        DELEGATES to ShopifyService.enrich_order_with_cancellation_and_refund_info.
        Returns order data with cancellation status, payment summary, and refund calculations for both types.
        
        Args:
            identifier: Order identifier (number or ID)
            submitted_at: Optional ISO 8601 datetime string for refund calculation (defaults to current time)
        """
        try:
            self.log_api_request("GET", f"/orders?identifier={identifier}&reason=refund")

            # Parse identifier to determine type and build query
            identifier_type, query_str = self._parse_order_identifier(identifier)

            # Build query_params dict for service
            query_params = {
                "query": query_str,
                "first": 1,
                "not_found_message": f"Order not found: {identifier}",
                "identifier": identifier
            }

            # DELEGATE to enriched service method
            self.log_service_call("enrich_order_with_cancellation_and_refund_info", query_params)
            result = self.shopify_service.enrich_order_with_cancellation_and_refund_info(
                query_params,
                reason="refund",
                submitted_at=submitted_at
            )

            # Extract status code and data from result
            status_code = result.get("status_code", 500)
            success = result.get("success", False)
            message = result.get("message", "Unknown error")
            
            # Build response data with all enriched information
            response_data = {
                "order": result.get("order"),
                "cancellation_status": result.get("cancellation_status"),
                "payment_summary": result.get("payment_summary"),
                "refund_calculations": result.get("refund_calculations")
            }

            # Map status codes to HTTP exceptions or return success
            if status_code == 404:
                raise NotFoundAPIError("Order", identifier)
            elif status_code == 202:
                # No refundable amount - return with 202 status (warning, not error)
                from fastapi import Response
                return Response(
                    content=json.dumps({
                        "success": False,
                        "message": message,
                        "data": response_data
                    }),
                    status_code=202,
                    media_type="application/json"
                )
            elif status_code == 500:
                raise APIError(message)
            elif status_code == 200:
                # Order has refundable amount - return success with enriched data
                return OrderResponse(**self.format_success_response(
                    data=response_data,
                    message=message
                ))
            else:
                # Unexpected status code
                raise APIError(f"Unexpected status code: {status_code}")

        except ValidationAPIError:
            raise
        except APIError:
            raise
        except Exception as e:
            self.logger.error("Error validating order refund %s: %s", identifier, e)
            raise self.map_exception_to_http_error(e)

    async def cancel_order(
        self,
        order_id: str,
        reason: str = "CUSTOMER",
        notify_customer: bool = False,
        refund: bool = False,
        restock: bool = False,
        staff_note: Optional[str] = None
    ) -> OrderResponse:
        """
        Cancel an order using Shopify's orderCancel mutation.

        DELEGATES to ShopifyService.cancel_order.
        Returns success/error based on mutation result.
        """
        try:
            self.log_api_request("DELETE", f"/orders/{order_id}")

            # DELEGATE to service method
            cancel_params = {
                "order_id": order_id,
                "reason": reason,
                "notify_customer": notify_customer,
                "refund": refund,
                "restock": restock,
                "staff_note": staff_note or "Cancelled via API"
            }
            self.log_service_call("cancel_order", cancel_params)
            
            result = self.shopify_service.cancel_order(
                order_id=order_id,
                reason=reason,
                notify_customer=notify_customer,
                refund=refund,
                restock=restock,
                staff_note=staff_note
            )

            # Check if cancellation was successful
            if result.get("success"):
                # Return success response with job data
                return OrderResponse(**self.format_success_response(
                    data=result.get("data", {}),
                    message="Order cancelled successfully"
                ))
            else:
                # Shopify returned errors - map to 422 (Unprocessable Entity)
                error_msg = result.get("message", "Unknown error")
                errors = result.get("errors", [])
                
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=422,
                    detail={
                        "success": False,
                        "message": error_msg,
                        "errors": errors
                    }
                )

        except ValidationAPIError:
            raise
        except APIError:
            raise
        except Exception as e:
            self.logger.error("Error cancelling order %s: %s", order_id, e)
            raise self.map_exception_to_http_error(e)

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    def _parse_order_identifier(self, identifier: str) -> tuple[str, str]:
        """
        Parse order identifier and build GraphQL query string.
        
        Args:
            identifier: Order number (12345, normalized without #) or Order ID (123456789, just digits)
        
        Returns:
            Tuple of (identifier_type, query_string)
            - identifier_type: "order_number" or "order_id"
            - query_string: GraphQL query string (e.g., "name:#12345" or "id:123456789")
        
        Raises:
            ValidationAPIError: If identifier format is invalid
        """
        identifier = identifier.strip() if identifier else ""
        if not identifier:
            raise ValidationAPIError("Order identifier cannot be empty")
        
        # Check if it's a 5-digit order number (already normalized without #)
        if identifier.isdigit() and len(identifier) == 5:
            # It's an order number - add # prefix for GraphQL query
            return ("order_number", f"name:#{identifier}")
        
        # Check if it's an 11-16 digit order ID
        if identifier.isdigit() and 11 <= len(identifier) <= 16:
            # It's an order ID - use as-is
            return ("order_id", f"id:{identifier}")
        
        # If neither format matches, raise error
        raise ValidationAPIError(
            f"Invalid order identifier format: {identifier}. "
            f"Expected order number (5 digits, e.g., 12345) "
            f"or order ID (11-16 digits, e.g., 1234567890)"
        )

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

            # Extract order number from order.name field (e.g., "#45308")
            order_number = "unknown"
            if hasattr(order, 'name') and order.name:
                order_number = str(order.name)

            return {
                "id": str(order.id),
                "order_number": order_number,  # Use order.name as order_number
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