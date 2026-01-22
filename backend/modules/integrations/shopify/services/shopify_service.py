"""
Main Shopify service - Table of Contents for all Shopify operations.

Provides a clean interface to all Shopify operations organized by resource:
- Customers (get, search, update)
- Orders (get, search, update, cancel, refund)
- Products (get, create, update)
- Inventory (adjustments, movements)

This service is pure Shopify - no BARS domain logic.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any as AnyType
    from backend.modules.integrations.shopify.models.sgqlc_models.mutations_sgqlc import CancelReasonType
else:
    CancelReasonType = str  # Runtime fallback
    AnyType = Any

from backend.modules.integrations.shopify.client.shopify_sgqlc_client import ShopifySGQLCClient
from backend.modules.integrations.shopify.models.sgqlc_models.sgqlc_query import Query

# Import shopify normalizers
# Add backend/shared to path if not already there
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))
from shared.shopify_normalizers import (
    normalize_order_id,
    normalize_order_number,
    normalize_product_id,
    normalize_customer_id,
    normalize_transaction_id,
    normalize_variant_id,
)

logger = logging.getLogger(__name__)


class ShopifyService:
    """
    Main Shopify service - Table of Contents for all Shopify operations.
    
    This service provides a clean interface to all Shopify operations organized by concern:
    - Pure Shopify API operations (no BARS domain logic)
    - Type-safe using sgqlc models
    - Consistent error handling
    - Reusable across CLI, backend APIs, and other services
    """
    
    def __init__(self, environment: str = "production"):
        """Initialize the Shopify service.
        
        Args:
            environment: Environment name ("production", "staging", or "development").
                Defaults to "production".
        """
        self.client = ShopifySGQLCClient(environment=environment)
        self.environment = environment
    
    # ============================================================================
    # CUSTOMERS
    # ============================================================================
    
    def get_customer_by_identifier(
        self,
        query_params: Dict[str, Any],
        orders_first: int = 5
    ) -> List[Any]:
        """
        Get customer by identifier using Shopify SGQLC client.
        
        Handles the complete flow:
        1. Builds and executes the GraphQL query
        2. Checks for GraphQL errors (raises if found)
        3. Interprets results into native objects
        4. Extracts customers from result
        5. Returns list of customer objects or raises if none found
        
        Args:
            query_params: Dict with keys:
                - query: GraphQL search query string (e.g., "email:test@example.com", "id:123")
                - first: Number of results to fetch (default: 1)
                - not_found_message: Error message if not found (optional)
                - identifier: Original identifier string (optional, for reference)
            orders_first: Number of orders to fetch per customer (default: 5)
        
        Returns:
            List of customer objects (sgqlc Type instances)
        
        Raises:
            RuntimeError: If the HTTP request fails (non-200 status or network errors)
            ValueError: If GraphQL errors are present, results can't be interpreted, or no customers found
        """
        query_str = query_params["query"]
        first = query_params.get("first", 1)
        
        # Build query operation (domain-specific logic in models)
        op = Query.build_customer_query(query_str, first=first, orders_first=orders_first)
        
        # Execute with generic client
        response = self.client.execute(op)
        
        # Check for GraphQL errors
        if response.get('errors'):
            error_msg = f"GraphQL query failed with {len(response.get('errors', []))} errors\n❌ GraphQL errors: {json.dumps(response.get('errors'), indent=2)}"
            raise ValueError(error_msg)
        
        # Interpret results into native objects (op + data pattern)
        try:
            query_result = op + response
        except Exception as e:
            error_msg = f"Error interpreting results: {type(e).__name__}: {e}\n{json.dumps(response, indent=2, default=str)}"
            raise ValueError(error_msg) from e
        
        # Extract customers from result
        customers_connection = query_result.customers
        customers_nodes = customers_connection.nodes if customers_connection else []
        
        # Check for empty customers
        if not customers_nodes:
            not_found_msg = query_params.get('not_found_message', 'No customers found')
            raise ValueError(f"{not_found_msg}\n{json.dumps(response, indent=2, default=str)}")
        
        return customers_nodes
    
    def update_identifier(
        self,
        customer_id: str,
        email: Optional[str] = None,
        phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update a customer's identifier (email or phone) using Shopify's customerUpdate mutation.
        
        First validates the customer exists, then updates it.
        
        Args:
            customer_id: Customer ID (gid://shopify/Customer/...)
            email: New email address (optional)
            phone: New phone number (optional)
        
        Returns:
            Dict with structure:
            {
                "success": bool,
                "data": {...},  # Customer data if successful
                "errors": [...],  # User errors if failed
                "message": str  # Error message if failed
            }
        
        Raises:
            ValueError: If customer not found or no update fields provided
        """
        if not email and not phone:
            raise ValueError("Must provide either email or phone")
        
        # First, validate customer exists
        try:
            query_params = {
                "identifier": customer_id,
                "query": f"id:{customer_id.split('/')[-1]}" if customer_id.startswith("gid://shopify/Customer/") else f"id:{customer_id}",
                "not_found_message": f"Customer not found: {customer_id}",
                "first": 1
            }
            _ = self.get_customer_by_identifier(query_params, orders_first=1)
        except ValueError as e:
            return {"success": False, "message": str(e)}
        
        # Build mutation operation
        from sgqlc.operation import Operation
        from backend.modules.integrations.shopify.models.sgqlc_models.mutations_sgqlc import (
            Mutation,
            CustomerUpdateInput
        )
        
        op = Operation(Mutation, variables={'input': CustomerUpdateInput})
        
        # Build customer input dict
        customer_input = {}
        if email:
            customer_input["email"] = email
        if phone:
            customer_input["phone"] = phone
        
        # Build update input dict
        update_input = {
            "id": customer_id,
            "customer": customer_input
        }
        
        # Select mutation with input
        result = op.customerUpdate(input=update_input)  # type: ignore[call-arg]
        
        # Select response fields
        result.customer.id()  # type: ignore[attr-defined]
        result.customer.email()  # type: ignore[attr-defined]
        result.customer.phone()  # type: ignore[attr-defined]
        result.customer.firstName()  # type: ignore[attr-defined]
        result.customer.lastName()  # type: ignore[attr-defined]
        result.userErrors.field()  # type: ignore[attr-defined]
        result.userErrors.message()  # type: ignore[attr-defined]
        
        # Execute mutation
        response = self.client.execute(op)
        
        # Check for GraphQL errors
        if response.get('errors'):
            error_messages = [err.get("message", str(err)) for err in response["errors"]]
            return {"success": False, "errors": error_messages, "message": "; ".join(error_messages)}
        
        # Interpret results
        try:
            mutation_result = op + response
            payload = mutation_result.customerUpdate  # type: ignore[attr-defined]
        except Exception as e:
            return {"success": False, "message": f"Error interpreting mutation result: {str(e)}"}
        
        # Check for user errors
        user_errors = []
        if payload.userErrors:  # type: ignore[attr-defined]
            for err in payload.userErrors:  # type: ignore[attr-defined]
                field = ", ".join(err.field) if err.field else "N/A"  # type: ignore[attr-defined]
                message = err.message  # type: ignore[attr-defined]
                user_errors.append(f"{field}: {message}")
        
        if user_errors:
            return {"success": False, "errors": user_errors, "message": "; ".join(user_errors)}
        
        # Success - extract customer data
        customer = payload.customer  # type: ignore[attr-defined]
        customer_data = {
            "id": customer.id if customer else None,  # type: ignore[attr-defined]
            "email": customer.email if customer else None,  # type: ignore[attr-defined]
            "phone": customer.phone if customer else None,  # type: ignore[attr-defined]
            "firstName": customer.firstName if customer else None,  # type: ignore[attr-defined]
            "lastName": customer.lastName if customer else None,  # type: ignore[attr-defined]
        }
        
        return {"success": True, "data": customer_data}
    
    def get_order_line_item_properties(self, order_id: str) -> List[Dict[str, str]]:
        """
        Get line item custom attributes for an order.
        
        Args:
            order_id: Order ID (gid://shopify/Order/...)
            
        Returns:
            List of custom attribute dictionaries with 'key' and 'value' keys
        """
        orders = self.get_order_by_identifier(
            {"query": f"id:{order_id}", "first": 1},
            line_items_first=50
        )
        
        if not orders:
            return []
        
        order = orders[0]
        properties = []
        
        # Get line items
        line_items_conn = getattr(order, 'lineItems', None)
        if not line_items_conn:
            return []
        
        nodes = getattr(line_items_conn, 'nodes', None)
        if not nodes:
            return []
        
        # Extract custom attributes from each line item
        for line_item in nodes:
            custom_attrs = getattr(line_item, 'customAttributes', None)
            if custom_attrs:
                for attr in custom_attrs:
                    key = getattr(attr, 'key', '')
                    value = getattr(attr, 'value', '')
                    if key and value:
                        properties.append({"key": key, "value": value})
        
        return properties
    
    def get_customer_birthdays_from_orders(self, order_ids: List[str]) -> List[Tuple[str, str, str]]:
        """
        Fetch birthdays with associated names from multiple orders concurrently.
        
        Args:
            order_ids: List of order IDs (gid://shopify/Order/...)
            
        Returns:
            List of (birthday, first_name, last_name) tuples
        """
        import concurrent.futures
        from backend.shared.customer_property_extractors import extract_birthday_with_name
        
        birthday_records = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_order = {
                executor.submit(self.get_order_line_item_properties, order_id): order_id
                for order_id in order_ids
            }
            
            for future in concurrent.futures.as_completed(future_to_order):
                try:
                    properties = future.result()
                    records = extract_birthday_with_name(properties)
                    birthday_records.extend(records)
                except Exception as e:
                    logger.error(f"Error fetching order: {e}")
        
        return birthday_records
    
    def get_customer_pronouns_from_orders(self, orders_with_dates: List[Tuple[str, str]]) -> List[Tuple[str, str, str, str]]:
        """
        Fetch pronouns with associated names and dates from multiple orders concurrently.
        
        Args:
            orders_with_dates: List of (order_id, created_at) tuples
            
        Returns:
            List of (pronouns, first_name, last_name, created_at) tuples
        """
        import concurrent.futures
        from backend.shared.customer_property_extractors import extract_pronouns_with_name
        
        pronouns_records = []
        
        # Process orders concurrently while preserving date info
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_order = {
                executor.submit(self.get_order_line_item_properties, order_id): (order_id, created_at)
                for order_id, created_at in orders_with_dates
            }
            
            for future in concurrent.futures.as_completed(future_to_order):
                order_id, created_at = future_to_order[future]
                try:
                    properties = future.result()
                    records = extract_pronouns_with_name(properties)
                    # Add created_at to each record
                    for pronouns, first_name, last_name in records:
                        pronouns_records.append((pronouns, first_name, last_name, created_at))
                except Exception as e:
                    logger.error(f"Error fetching order {order_id}: {e}")
        
        return pronouns_records
    
    def get_customer_birthdays(self, customer_id: str) -> List[Tuple[str, str, str]]:
        """
        Get customer birthdays from their orders.
        
        High-level convenience method that:
        1. Gets customer with orders
        2. Extracts order IDs
        3. Fetches birthdays from orders concurrently
        4. Returns sorted results
        
        Args:
            customer_id: Customer ID (gid://shopify/Customer/...)
            
        Returns:
            List of (birthday, first_name, last_name) tuples, sorted by birthday then name
        """
        # Get customer with orders
        customer_id_short = customer_id.split('/')[-1] if '/' in customer_id else customer_id
        customer = self.get_customer_by_identifier(
            {"query": f"id:{customer_id_short}", "first": 1},
            orders_first=5
        )[0]
        
        # Extract order IDs
        order_ids = self._extract_order_ids_from_customer(customer)
        
        if not order_ids:
            return []
        
        # Fetch birthdays
        birthday_records = self.get_customer_birthdays_from_orders(order_ids)
        
        # Sort by birthday, then by name
        return sorted(birthday_records, key=lambda x: (x[0], x[1], x[2]))
    
    def get_customer_pronouns(self, customer_id: str) -> List[Tuple[str, str, str, str]]:
        """
        Get customer pronouns from their orders.
        
        High-level convenience method that:
        1. Gets customer with orders
        2. Extracts order IDs with dates
        3. Fetches pronouns from orders concurrently
        4. Returns sorted results (most recent first)
        
        Args:
            customer_id: Customer ID (gid://shopify/Customer/...)
            
        Returns:
            List of (pronouns, first_name, last_name, created_at) tuples, sorted by most recent first
        """
        # Get customer with orders
        customer_id_short = customer_id.split('/')[-1] if '/' in customer_id else customer_id
        customer = self.get_customer_by_identifier(
            {"query": f"id:{customer_id_short}", "first": 1},
            orders_first=5
        )[0]
        
        # Extract order IDs with dates
        orders_with_dates = self._extract_order_ids_with_dates_from_customer(customer)
        
        if not orders_with_dates:
            return []
        
        # Fetch pronouns
        pronouns_records = self.get_customer_pronouns_from_orders(orders_with_dates)
        
        # Sort by created_at (most recent first), then by name
        # created_at is ISO 8601 format so string sort works correctly
        return sorted(pronouns_records, key=lambda x: (x[3], x[1], x[2]), reverse=True)
    
    def _extract_order_ids_from_customer(self, customer: AnyType) -> List[str]:
        """
        Extract order IDs from customer data.
        
        Private helper method.
        
        Args:
            customer: Customer object (sgqlc Type instance)
            
        Returns:
            List of order IDs (gid://shopify/Order/...)
        """
        orders_conn = getattr(customer, 'orders', None)
        if not orders_conn:
            return []
        
        nodes = getattr(orders_conn, 'nodes', None)
        if not nodes:
            return []
        
        return [getattr(order, 'id', '') for order in nodes if getattr(order, 'id', None)]
    
    def _extract_order_ids_with_dates_from_customer(self, customer: AnyType) -> List[Tuple[str, str]]:
        """
        Extract order IDs with created_at dates from customer data.
        
        Private helper method.
        
        Args:
            customer: Customer object (sgqlc Type instance)
            
        Returns:
            List of (order_id, created_at) tuples
        """
        orders_conn = getattr(customer, 'orders', None)
        if not orders_conn:
            return []
        
        nodes = getattr(orders_conn, 'nodes', None)
        if not nodes:
            return []
        
        return [
            (getattr(order, 'id', ''), getattr(order, 'createdAt', ''))
            for order in nodes
            if getattr(order, 'id', None)
        ]
    
    # ============================================================================
    # ORDERS
    # ============================================================================
    
    def get_order_by_identifier(
        self,
        query_params: Dict[str, Any],
        line_items_first: int = 5
    ) -> List[Any]:
        """
        Get order by identifier using Shopify SGQLC client.
        
        Handles the complete flow:
        1. Builds and executes the GraphQL query
        2. Checks for GraphQL errors (raises if found)
        3. Interprets results into native objects
        4. Extracts orders from result
        5. Returns list of order objects or raises if none found
        
        Args:
            query_params: Dict with keys:
                - query: GraphQL search query string (e.g., "name:#1234", "id:123")
                - first: Number of results to fetch (default: 1)
                - not_found_message: Error message if not found (optional)
                - identifier: Original identifier string (optional, for reference)
            line_items_first: Number of line items to fetch per order (default: 5)
        
        Returns:
            List of order objects (sgqlc Type instances)
        
        Raises:
            RuntimeError: If the HTTP request fails (non-200 status or network errors)
            ValueError: If GraphQL errors are present, results can't be interpreted, or no orders found
        """
        query_str = query_params["query"]
        first = query_params.get("first", 1)
        
        # Build query operation (domain-specific logic in models)
        op = Query.build_order_query(query_str, first=first, line_items_first=line_items_first)
        
        # Execute with generic client
        response = self.client.execute(op)
        
        # Check for GraphQL errors
        if response.get('errors'):
            error_msg = f"GraphQL query failed with {len(response.get('errors', []))} errors\n❌ GraphQL errors: {json.dumps(response.get('errors'), indent=2)}"
            raise ValueError(error_msg)
        
        # Interpret results into native objects (op + data pattern)
        try:
            query_result = op + response
        except Exception as e:
            error_msg = f"Error interpreting results: {type(e).__name__}: {e}\n{json.dumps(response, indent=2, default=str)}"
            raise ValueError(error_msg) from e
        
        # Extract orders from result
        orders_connection = query_result.orders
        orders_nodes = orders_connection.nodes if orders_connection else []
        
        # Check for empty orders
        if not orders_nodes:
            not_found_msg = query_params.get('not_found_message', 'No orders found')
            raise ValueError(f"{not_found_msg}\n{json.dumps(response, indent=2, default=str)}")
        
        return orders_nodes
    
    def cancel_order(
        self,
        order_id: str,
        reason: CancelReasonType = "CUSTOMER",
        notify_customer: bool = False,
        refund: bool = False,
        restock: bool = False,
        staff_note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel an order using Shopify's orderCancel mutation.
        
        Args:
            order_id: Order ID (gid://shopify/Order/...)
            reason: Cancellation reason - one of: "CUSTOMER", "FRAUD", "INVENTORY", "DECLINED", "OTHER" (default: "CUSTOMER")
            notify_customer: Whether to notify customer (default: False)
            refund: Whether to refund (default: False)
            restock: Whether to restock inventory (default: False)
            staff_note: Optional staff note
        
        Returns:
            Dict with structure:
            {
                "success": bool,
                "data": {...},  # Job info if successful
                "errors": [...],  # User errors if failed
                "message": str  # Error message if failed
            }
        """
        from sgqlc.operation import Operation
        from backend.modules.integrations.shopify.models.sgqlc_models.mutations_sgqlc import (
            Mutation,
            OrderCancelReason
        )
        
        # Build mutation operation
        op = Operation(Mutation)
        
        # Pass reason string directly (sgqlc accepts strings for enum arguments)
        # The CancelReasonType Literal ensures type safety
        reason_value = reason.upper() if isinstance(reason, str) else reason
        
        # Select mutation with arguments
        result = op.orderCancel(
            notifyCustomer=notify_customer,
            orderId=order_id,
            reason=reason_value,
            refund=refund,
            restock=restock,
            staffNote=staff_note or "Cancelled via CLI"
        )
        
        # Select response fields
        result.job.__fields__('id', 'done')  # type: ignore[union-attr]
        result.orderCancelUserErrors.__fields__('field', 'message')  # type: ignore[union-attr]
        result.userErrors.__fields__('field', 'message')  # type: ignore[union-attr]
        
        # Execute mutation
        response = self.client.execute(op)
        
        # Check for GraphQL errors
        if response.get('errors'):
            error_messages = [err.get("message", str(err)) for err in response["errors"]]
            return {"success": False, "errors": error_messages, "message": "; ".join(error_messages)}
        
        # Interpret results
        try:
            mutation_result = op + response
            payload = mutation_result.orderCancel  # type: ignore[attr-defined]
        except Exception as e:
            return {"success": False, "message": f"Error interpreting mutation result: {str(e)}"}
        
        # Check for user errors
        user_errors = []
        if payload.orderCancelUserErrors:  # type: ignore[attr-defined]
            for err in payload.orderCancelUserErrors:  # type: ignore[attr-defined]
                field = ", ".join(err.field) if err.field else "N/A"  # type: ignore[attr-defined]
                message = err.message  # type: ignore[attr-defined]
                user_errors.append(f"{field}: {message}")
        
        if payload.userErrors:  # type: ignore[attr-defined]
            for err in payload.userErrors:  # type: ignore[attr-defined]
                field = ", ".join(err.field) if err.field else "N/A"  # type: ignore[attr-defined]
                message = err.message  # type: ignore[attr-defined]
                user_errors.append(f"{field}: {message}")
        
        if user_errors:
            return {"success": False, "errors": user_errors, "message": "; ".join(user_errors)}
        
        # Success - extract job info
        job = payload.job  # type: ignore[attr-defined]
        job_data = {
            "id": job.id if job else None,  # type: ignore[attr-defined]
            "done": job.done if job else False  # type: ignore[attr-defined]
        }
        
        return {"success": True, "data": job_data}
    
    def create_refund(
        self,
        order_id: str,
        refund_amount: float,
        refund_type: str,
        transactions: List[Any],
        currency: str = "USD",
        notify: bool = True,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Create a refund using Shopify's refundCreate mutation.
        
        Args:
            order_id: Order ID (gid://shopify/Order/...)
            refund_amount: Refund amount (float)
            refund_type: "refund" (original payment) or "credit" (store credit)
            transactions: List of transaction objects from order
            currency: Currency code (default: "USD")
            notify: Whether to notify customer (default: True)
            max_retries: Maximum retry attempts (default: 3)
        
        Returns:
            Dict with structure:
            {
                "success": bool,
                "data": {...},  # Refund data if successful
                "errors": [...],  # User errors if failed
                "message": str  # Error message if failed
            }
        """
        import time
        from sgqlc.operation import Operation
        from backend.modules.integrations.shopify.models.sgqlc_models.mutations_sgqlc import (
            Mutation,
            RefundInput,
            CurrencyCode,
            OrderTransactionKind
        )
        
        # Build refund input
        refund_input = {
            "notify": notify,
            "orderId": order_id,
        }
        
        # Map currency string to CurrencyCode enum
        currency_enum = getattr(CurrencyCode, currency.upper(), CurrencyCode.USD)
        
        if refund_type.lower() == "credit":
            # Store credit refund
            refund_input["note"] = f"Store Credit issued for ${refund_amount:.2f}"
            refund_input["refundMethods"] = [
                {
                    "storeCreditRefund": {
                        "amount": {
                            "amount": str(refund_amount),
                            "currencyCode": currency_enum  # Use enum value from order currency
                        }
                    }
                }
            ]
        else:
            # Original payment refund - find capture transaction
            capture_transaction = None
            for txn in transactions:
                txn_data = txn.__json_data__ if hasattr(txn, '__json_data__') else txn
                kind = txn_data.get("kind") if isinstance(txn_data, dict) else getattr(txn, 'kind', None)
                status = txn_data.get("status") if isinstance(txn_data, dict) else getattr(txn, 'status', None)
                
                if kind in ["CAPTURE", "SALE"] and status == "SUCCESS":
                    capture_transaction = txn_data if isinstance(txn_data, dict) else txn
                    break
            
            if not capture_transaction:
                return {"success": False, "message": "No successful capture transaction found for refund"}
            
            # Get gateway and parent transaction ID
            gateway = capture_transaction.get("gateway") if isinstance(capture_transaction, dict) else getattr(capture_transaction, 'gateway', 'shopify_payments')
            parent_trans = capture_transaction.get("parentTransaction") if isinstance(capture_transaction, dict) else getattr(capture_transaction, 'parentTransaction', None)
            
            if parent_trans:
                parent_id = parent_trans.get("id") if isinstance(parent_trans, dict) else getattr(parent_trans, 'id', None)
            else:
                parent_id = capture_transaction.get("id") if isinstance(capture_transaction, dict) else getattr(capture_transaction, 'id', None)
            
            if not parent_id:
                return {"success": False, "message": "Could not determine parent transaction ID"}
            
            refund_input["note"] = f"Refund issued for ${refund_amount:.2f}"
            refund_input["transactions"] = [
                {
                    "orderId": order_id,
                    "gateway": gateway,
                    "kind": OrderTransactionKind.REFUND,  # Use enum value
                    "amount": str(refund_amount),
                    "parentId": parent_id
                }
            ]
        
        # Build mutation operation
        op = Operation(Mutation)
        
        # Select mutation with input (pass dict directly, sgqlc will handle conversion)
        result = op.refundCreate(input=refund_input)  # type: ignore[call-arg]
        
        # Select response fields
        result.refund.__fields__('id', 'createdAt', 'note', 'totalRefundedSet')  # type: ignore[union-attr]
        result.refund.totalRefundedSet.shopMoney.__fields__('amount', 'currencyCode')  # type: ignore[union-attr]
        result.refund.totalRefundedSet.presentmentMoney.__fields__('amount', 'currencyCode')  # type: ignore[union-attr]
        result.userErrors.__fields__('field', 'message')  # type: ignore[union-attr]
        
        # Retry logic with exponential backoff
        base_delay = 1.0
        backoff_factor = 2.0
        last_error: Dict[str, Any] = {"success": False, "error": "Unknown error"}
        
        for attempt in range(max_retries + 1):
            try:
                # Execute mutation
                response = self.client.execute(op)
                
                # Check for GraphQL errors
                if response.get('errors'):
                    error_messages = [err.get("message", str(err)) for err in response["errors"]]
                    last_error = {"success": False, "message": error_messages}
                    if attempt < max_retries:
                        delay = base_delay * (backoff_factor ** attempt)
                        time.sleep(delay)
                        continue
                    return last_error
                
                # Interpret results
                try:
                    mutation_result = op + response
                    payload = mutation_result.refundCreate  # type: ignore[attr-defined]
                except Exception as e:
                    last_error = {"success": False, "message": f"Error interpreting mutation result: {str(e)}"}
                    if attempt < max_retries:
                        delay = base_delay * (backoff_factor ** attempt)
                        time.sleep(delay)
                        continue
                    return last_error
                
                # Check for user errors
                user_errors = []
                if payload.userErrors:  # type: ignore[attr-defined]
                    for err in payload.userErrors:  # type: ignore[attr-defined]
                        field = ", ".join(err.field) if err.field else "N/A"  # type: ignore[attr-defined]
                        message = err.message  # type: ignore[attr-defined]
                        user_errors.append(f"{field}: {message}")
                
                if user_errors:
                    last_error = {"success": False, "message": user_errors}
                    if attempt < max_retries:
                        delay = base_delay * (backoff_factor ** attempt)
                        time.sleep(delay)
                        continue
                    return last_error
                
                # Success - extract refund data
                refund = payload.refund  # type: ignore[attr-defined]
                if not refund:
                    last_error = {"success": False, "message": "Refund creation returned no refund data"}
                    if attempt < max_retries:
                        delay = base_delay * (backoff_factor ** attempt)
                        time.sleep(delay)
                        continue
                    return last_error
                
                refund_data = refund.__json_data__ if hasattr(refund, '__json_data__') else {}
                return {
                    "success": True,
                    "data": refund_data,
                    "raw_response": response  # Include raw GraphQL response
                }
                
            except RuntimeError as e:
                # HTTP/network errors - retry
                last_error = {"success": False, "error": str(e)}
                if attempt < max_retries:
                    delay = base_delay * (backoff_factor ** attempt)
                    time.sleep(delay)
                    continue
                return last_error
        
        return last_error
    
    def apply_discount(
        self,
        order_id: str,
        discount_type: str,
        discount_value: float,
        code_desc: Optional[str] = None,
        currency_code: str = "USD",
        sleep_between_calls: float = 0.05
    ) -> Dict[str, Any]:
        """
        Apply a discount to an order using Shopify's Order Editing API.
        
        Process:
        1. orderEditBegin - Start order editing session
        2. Fetch first calculated line item and its unit price
        3. orderEditAddLineItemDiscount - Apply discount
        4. orderEditCommit - Commit the changes
        
        Args:
            order_id: Order ID (gid://shopify/Order/...)
            discount_type: "fixed" or "percentage"
            discount_value: Discount amount (for fixed) or percentage (for percentage, e.g., 5.0 for 5%)
            code_desc: Optional description for the discount (defaults to auto-generated)
            currency_code: Currency code (default: "USD")
            sleep_between_calls: Seconds to sleep between API calls (default: 0.05)
        
        Returns:
            Dict with structure:
            {
                "success": bool,
                "data": {
                    "calculated_order_id": str,
                    "line_item_id": str,
                    "unit_price": float,
                    "discount_amount": float,
                    "step": str  # "done" if successful
                },
                "errors": [...],  # User errors if failed
                "message": str  # Error message if failed
            }
        """
        import time
        from sgqlc.operation import Operation
        from backend.modules.integrations.shopify.models.sgqlc_models.mutations_sgqlc import (
            Mutation,
            OrderEditAppliedDiscountInput,
            MoneyInput
        )
        
        # Generate code description if not provided
        if not code_desc:
            if discount_type == "fixed":
                code_desc = f"code: fixed-discount-${discount_value:.2f}"
            else:
                code_desc = f"code: percentage-discount-{discount_value}%"
        
        try:
            # Step 1: Begin order editing
            op_begin = Operation(Mutation)
            begin_result = op_begin.orderEditBegin(id=order_id)
            begin_result.calculatedOrder.id()  # type: ignore[attr-defined]
            begin_result.userErrors.field()  # type: ignore[attr-defined]
            begin_result.userErrors.message()  # type: ignore[attr-defined]
            
            response = self.client.execute(op_begin)
            if response.get('errors'):
                error_messages = [err.get("message", str(err)) for err in response["errors"]]
                return {"success": False, "errors": error_messages, "message": "; ".join(error_messages)}
            
            interpreted = op_begin + response
            begin_payload = interpreted.orderEditBegin  # type: ignore[attr-defined]
            
            user_errors = []
            if begin_payload.userErrors:  # type: ignore[attr-defined]
                for err in begin_payload.userErrors:  # type: ignore[attr-defined]
                    field = ", ".join(err.field) if err.field else "N/A"  # type: ignore[attr-defined]
                    message = err.message  # type: ignore[attr-defined]
                    user_errors.append(f"{field}: {message}")
            
            if user_errors:
                return {"success": False, "errors": user_errors, "message": "; ".join(user_errors)}
            
            calculated_order_id = begin_payload.calculatedOrder.id  # type: ignore[attr-defined]
            time.sleep(sleep_between_calls)
            
            # Step 2: Fetch first calculated line item using node query
            # We need to query the CalculatedOrder node to get line items
            op_query = Operation(Query)
            node_result = op_query.node(id=calculated_order_id)
            node_result.__typename()  # type: ignore[attr-defined]
            # Use inline fragment for CalculatedOrder
            calc_order = node_result.on('CalculatedOrder')  # type: ignore[attr-defined]
            calc_order.id()  # type: ignore[attr-defined]
            line_items = calc_order.lineItems(first=50)  # type: ignore[attr-defined]
            edges = line_items.edges()  # type: ignore[attr-defined]
            node = edges.node()  # type: ignore[attr-defined]
            node.id()  # type: ignore[attr-defined]
            node.title()  # type: ignore[attr-defined]
            original_price = node.originalUnitPriceSet()  # type: ignore[attr-defined]
            shop_money = original_price.shopMoney()  # type: ignore[attr-defined]
            shop_money.amount()  # type: ignore[attr-defined]
            shop_money.currencyCode()  # type: ignore[attr-defined]
            
            response = self.client.execute(op_query)
            if response.get('errors'):
                error_messages = [err.get("message", str(err)) for err in response["errors"]]
                return {"success": False, "errors": error_messages, "message": "; ".join(error_messages)}
            
            interpreted = op_query + response
            node_data = interpreted.node  # type: ignore[attr-defined]
            
            # Get CalculatedOrder from node
            if not hasattr(node_data, 'lineItems') or not node_data.lineItems:  # type: ignore[attr-defined]
                return {"success": False, "message": "No calculated line items found on CalculatedOrder"}
            
            edges = node_data.lineItems.edges  # type: ignore[attr-defined]
            if not edges or len(edges) == 0:
                return {"success": False, "message": "No calculated line items found on CalculatedOrder"}
            
            first_item = edges[0].node  # type: ignore[attr-defined]
            line_item_id = first_item.id  # type: ignore[attr-defined]
            unit_price = float(first_item.originalUnitPriceSet.shopMoney.amount)  # type: ignore[attr-defined]
            time.sleep(sleep_between_calls)
            
            # Step 3: Calculate discount amount
            if discount_type == "fixed":
                discount_amount = discount_value
            else:
                # Percentage: calculate from unit price
                discount_amount = (discount_value / 100.0) * unit_price
            
            # Step 4: Add discount
            op_discount = Operation(Mutation)
            discount_input = OrderEditAppliedDiscountInput(
                description=code_desc,
                fixedValue=MoneyInput(amount=f"{discount_amount:.2f}", currencyCode=currency_code)
            )
            discount_result = op_discount.orderEditAddLineItemDiscount(
                id=calculated_order_id,
                lineItemId=line_item_id,
                discount=discount_input
            )
            discount_result.userErrors.field()  # type: ignore[attr-defined]
            discount_result.userErrors.message()  # type: ignore[attr-defined]
            
            response = self.client.execute(op_discount)
            if response.get('errors'):
                error_messages = [err.get("message", str(err)) for err in response["errors"]]
                return {"success": False, "errors": error_messages, "message": "; ".join(error_messages)}
            
            interpreted = op_discount + response
            discount_payload = interpreted.orderEditAddLineItemDiscount  # type: ignore[attr-defined]
            
            user_errors = []
            if discount_payload.userErrors:  # type: ignore[attr-defined]
                for err in discount_payload.userErrors:  # type: ignore[attr-defined]
                    field = ", ".join(err.field) if err.field else "N/A"  # type: ignore[attr-defined]
                    message = err.message  # type: ignore[attr-defined]
                    user_errors.append(f"{field}: {message}")
            
            if user_errors:
                return {"success": False, "errors": user_errors, "message": "; ".join(user_errors)}
            
            time.sleep(sleep_between_calls)
            
            # Step 5: Commit order edit
            staff_note = f"Applied ${discount_amount:.2f} discount via {code_desc}" if discount_type == "fixed" else f"Applied {discount_value}% discount via {code_desc}"
            
            op_commit = Operation(Mutation)
            commit_result = op_commit.orderEditCommit(
                id=calculated_order_id,
                notifyCustomer=False,
                staffNote=staff_note
            )
            commit_result.userErrors.field()  # type: ignore[attr-defined]
            commit_result.userErrors.message()  # type: ignore[attr-defined]
            
            response = self.client.execute(op_commit)
            if response.get('errors'):
                error_messages = [err.get("message", str(err)) for err in response["errors"]]
                return {"success": False, "errors": error_messages, "message": "; ".join(error_messages)}
            
            interpreted = op_commit + response
            commit_payload = interpreted.orderEditCommit  # type: ignore[attr-defined]
            
            user_errors = []
            if commit_payload.userErrors:  # type: ignore[attr-defined]
                for err in commit_payload.userErrors:  # type: ignore[attr-defined]
                    field = ", ".join(err.field) if err.field else "N/A"  # type: ignore[attr-defined]
                    message = err.message  # type: ignore[attr-defined]
                    user_errors.append(f"{field}: {message}")
            
            if user_errors:
                return {"success": False, "errors": user_errors, "message": "; ".join(user_errors)}
            
            # Success
            return {
                "success": True,
                "data": {
                    "calculated_order_id": calculated_order_id,
                    "line_item_id": line_item_id,
                    "unit_price": unit_price,
                    "discount_amount": discount_amount,
                    "step": "done"
                }
            }
        
        except Exception as e:
            return {"success": False, "message": f"Error applying discount: {str(e)}"}
    
    def adjust_inventory(
        self,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Adjust inventory using Shopify's inventoryAdjustQuantities mutation.
        
        Args:
            request: Dict with keys:
                - inventory_item_id: Inventory item ID (gid://shopify/InventoryItem/...)
                - location_id: Location ID (gid://shopify/Location/...)
                - delta: Quantity change (positive for increase, negative for decrease)
                - reason: Reason for adjustment (default: "correction")
                - name: Inventory name (default: "available")
                - reference_uri: Optional reference URI
        
        Returns:
            Dict with structure:
            {
                "success": bool,
                "data": {...},  # Adjustment data if successful
                "errors": [...],  # User errors if failed
                "message": str  # Error message if failed
            }
        """
        from sgqlc.operation import Operation
        from backend.modules.integrations.shopify.models.sgqlc_models.mutations_sgqlc import (
            Mutation,
            InventoryAdjustQuantitiesInput
        )
        
        # Build mutation operation (no variables, pass input directly)
        op = Operation(Mutation)
        
        # Build input dict
        changes = [{
            "delta": request["delta"],
            "inventoryItemId": request["inventory_item_id"],
            "locationId": request["location_id"]
        }]
        
        input_data = {
            "reason": request.get("reason", "correction"),
            "name": request.get("name", "available"),
            "changes": changes
        }
        
        if request.get("reference_uri"):
            input_data["referenceDocumentUri"] = request["reference_uri"]
        
        # Select mutation with input (pass dict directly, sgqlc will handle conversion)
        result = op.inventoryAdjustQuantities(input=input_data)  # type: ignore[call-arg]
        result.userErrors.__fields__('field', 'message')  # type: ignore[union-attr]
        result.inventoryAdjustmentGroup.__fields__('createdAt', 'reason', 'referenceDocumentUri')  # type: ignore[union-attr]
        
        # Execute mutation
        response = self.client.execute(op)
        
        # Check for GraphQL errors
        if response.get('errors'):
            error_messages = [err.get("message", str(err)) for err in response["errors"]]
            return {"success": False, "errors": error_messages, "message": "; ".join(error_messages)}
        
        # Interpret results
        try:
            mutation_result = op + response
            payload = mutation_result.inventoryAdjustQuantities  # type: ignore[attr-defined]
        except Exception as e:
            return {"success": False, "message": f"Error interpreting mutation result: {str(e)}"}
        
        # Check for user errors
        user_errors = []
        if payload.userErrors:  # type: ignore[attr-defined]
            for err in payload.userErrors:  # type: ignore[attr-defined]
                field = ", ".join(err.field) if err.field else "N/A"  # type: ignore[attr-defined]
                message = err.message  # type: ignore[attr-defined]
                user_errors.append(f"{field}: {message}")
        
        if user_errors:
            return {"success": False, "errors": user_errors, "message": "; ".join(user_errors)}
        
        # Success - extract adjustment data
        adjustment_group = payload.inventoryAdjustmentGroup  # type: ignore[attr-defined]
        adjustment_data = {
            "createdAt": adjustment_group.createdAt if adjustment_group else None,  # type: ignore[attr-defined]
            "reason": adjustment_group.reason if adjustment_group else None,  # type: ignore[attr-defined]
            "referenceDocumentUri": adjustment_group.referenceDocumentUri if adjustment_group else None  # type: ignore[attr-defined]
        }
        
        return {
            "success": True,
            "data": adjustment_data,
            "raw_response": response  # Include raw GraphQL response
        }
    
    def calculate_payment_summary(self, order: Any) -> Dict[str, Any]:
        """
        Calculate payment summary from order including refunds.
        
        Args:
            order: Order object (sgqlc Type instance)
        
        Returns:
            Dict with keys:
            - total_amount: Total amount paid (from CAPTURE/SALE transactions)
            - currency: Currency code
            - total_refunded: Total amount refunded
            - pending_refunds: Amount of pending refunds
            - completed_refunds: Amount of completed refunds
            - remaining_refundable: Remaining refundable amount
        """
        total_amount = 0.0
        currency = 'USD'
        
        # Calculate total paid from CAPTURE and SALE transactions
        # CAPTURE is the actual payment, SALE is included as fallback
        transactions = getattr(order, 'transactions', None)  # type: ignore[attr-defined]
        if transactions:
            transaction_list = list(transactions) if hasattr(transactions, '__iter__') and not isinstance(transactions, str) else []
            for trans in transaction_list:
                # Try accessing via sgqlc attributes first
                trans_kind = getattr(trans, 'kind', None)  # type: ignore[attr-defined]
                trans_status = getattr(trans, 'status', None)  # type: ignore[attr-defined]
                trans_amount_str = getattr(trans, 'amount', None)  # type: ignore[attr-defined]
                
                # Fallback to __json_data__ if attributes are None (field not selected)
                if trans_kind is None and hasattr(trans, '__json_data__'):
                    trans_data = trans.__json_data__
                    trans_kind = trans_data.get('kind')
                    trans_status = trans_data.get('status')
                    trans_amount_str = trans_data.get('amount')
                
                # Look for CAPTURE (actual payment) or SALE transactions with SUCCESS status
                if trans_kind in ['CAPTURE', 'SALE'] and trans_status == 'SUCCESS':
                    try:
                        trans_amount = float(trans_amount_str) if trans_amount_str else 0.0
                        if trans_amount > 0:
                            total_amount += trans_amount
                            # Get currency from totalPriceSet if available, otherwise default to USD
                            if currency == 'USD':
                                total_price_set = getattr(order, 'totalPriceSet', None)  # type: ignore[attr-defined]
                                if total_price_set:
                                    shop_money = getattr(total_price_set, 'shopMoney', None)  # type: ignore[attr-defined]
                                    if shop_money:
                                        currency = getattr(shop_money, 'currencyCode', 'USD')  # type: ignore[attr-defined]
                    except (ValueError, TypeError):
                        pass
        
        # Fallback: Use totalPriceSet if no CAPTURE/SALE transactions found
        if total_amount == 0.0:
            total_price_set = getattr(order, 'totalPriceSet', None)  # type: ignore[attr-defined]
            if total_price_set:
                shop_money = getattr(total_price_set, 'shopMoney', None)  # type: ignore[attr-defined]
                if shop_money:
                    amount_str = getattr(shop_money, 'amount', '0')  # type: ignore[attr-defined]
                    currency = getattr(shop_money, 'currencyCode', 'USD')  # type: ignore[attr-defined]
                    try:
                        total_amount = float(amount_str)
                    except (ValueError, TypeError):
                        total_amount = 0.0
        
        # Last resort: Calculate from line items if still zero
        if total_amount == 0.0:
            line_items_conn = getattr(order, 'lineItems', None)  # type: ignore[attr-defined]
            if line_items_conn:
                nodes = getattr(line_items_conn, 'nodes', None)  # type: ignore[attr-defined]
                if nodes:
                    for line_item in nodes:
                        # Try discountedTotalSet first, then originalTotalSet
                        discounted_total_set = getattr(line_item, 'discountedTotalSet', None)  # type: ignore[attr-defined]
                        if discounted_total_set:
                            shop_money = getattr(discounted_total_set, 'shopMoney', None)  # type: ignore[attr-defined]
                            if shop_money:
                                amount_str = getattr(shop_money, 'amount', '0')  # type: ignore[attr-defined]
                                try:
                                    total_amount += float(amount_str)
                                    currency = getattr(shop_money, 'currencyCode', currency)  # type: ignore[attr-defined]
                                except (ValueError, TypeError):
                                    pass
                        else:
                            original_total_set = getattr(line_item, 'originalTotalSet', None)  # type: ignore[attr-defined]
                            if original_total_set:
                                shop_money = getattr(original_total_set, 'shopMoney', None)  # type: ignore[attr-defined]
                                if shop_money:
                                    amount_str = getattr(shop_money, 'amount', '0')  # type: ignore[attr-defined]
                                    try:
                                        total_amount += float(amount_str)
                                        currency = getattr(shop_money, 'currencyCode', currency)  # type: ignore[attr-defined]
                                    except (ValueError, TypeError):
                                        pass
        
        # Calculate refunds
        refunds = getattr(order, 'refunds', None)  # type: ignore[attr-defined]
        total_refunded = 0.0
        pending_refunds = 0.0
        completed_refunds = 0.0
        
        if refunds:
            refund_list = list(refunds) if hasattr(refunds, '__iter__') and not isinstance(refunds, str) else []
            for refund in refund_list:
                # Access Refund fields directly via sgqlc attributes
                total_refunded_set = getattr(refund, 'totalRefundedSet', None)  # type: ignore[attr-defined]
                refund_total = 0.0
                
                if total_refunded_set:
                    shop_money = getattr(total_refunded_set, 'shopMoney', None)  # type: ignore[attr-defined]
                    if shop_money:
                        amount_str = getattr(shop_money, 'amount', '0')  # type: ignore[attr-defined]
                        try:
                            refund_total = float(amount_str)
                        except (ValueError, TypeError):
                            refund_total = 0.0
                
                if refund_total == 0:
                    # Check transactions for pending refunds
                    refund_transactions_conn = getattr(refund, 'transactions', None)  # type: ignore[attr-defined]
                    if refund_transactions_conn:
                        nodes = getattr(refund_transactions_conn, 'nodes', None)  # type: ignore[attr-defined]
                        if nodes:
                            for trans in nodes:
                                trans_kind = getattr(trans, 'kind', None)  # type: ignore[attr-defined]
                                trans_status = getattr(trans, 'status', None)  # type: ignore[attr-defined]
                                trans_amount_str = getattr(trans, 'amount', None)  # type: ignore[attr-defined]
                                
                                # Fallback to __json_data__ if needed
                                if trans_kind is None and hasattr(trans, '__json_data__'):
                                    trans_data = trans.__json_data__
                                    trans_kind = trans_data.get('kind')
                                    trans_status = trans_data.get('status')
                                    trans_amount_str = trans_data.get('amount')
                                
                                if trans_kind == 'REFUND':
                                    try:
                                        trans_amount = float(trans_amount_str) if trans_amount_str else 0.0
                                        if trans_status == 'PENDING':
                                            pending_refunds += trans_amount
                                        refund_total += trans_amount
                                        break
                                    except (ValueError, TypeError):
                                        pass
                else:
                    completed_refunds += refund_total
                
                total_refunded += refund_total
        
        remaining_refundable = total_amount - total_refunded
        
        return {
            'total_amount': total_amount,
            'currency': currency,
            'total_refunded': total_refunded,
            'pending_refunds': pending_refunds,
            'completed_refunds': completed_refunds,
            'remaining_refundable': remaining_refundable
        }
    
    def calculate_estimated_refund(
        self,
        order: Any,
        total_amount: float,
        refund_type: str,
        submitted_at: Optional[datetime] = None
    ) -> Tuple[Optional[float], Optional[str]]:
        """
        Calculate estimated refund amount based on season dates.
        
        Args:
            order: Order object (sgqlc Type instance)
            total_amount: Total order amount
            refund_type: "refund" or "credit"
            submitted_at: Optional datetime for refund calculation (defaults to current time)
        
        Returns:
            Tuple of (estimated_amount, message) or (None, None) if calculation not possible
        """
        from backend.shared.date_utils import extract_season_dates, calculate_refund_amount
        from datetime import datetime, timezone
        
        if submitted_at is None:
            submitted_at = datetime.now(timezone.utc)
        
        line_items_conn = getattr(order, 'lineItems', None)  # type: ignore[attr-defined]
        if not line_items_conn:
            return None, None
        
        nodes = getattr(line_items_conn, 'nodes', None)  # type: ignore[attr-defined]
        if not nodes or len(nodes) == 0:
            return None, None
        
        first_item = nodes[0]
        product = getattr(first_item, 'product', None)  # type: ignore[attr-defined]
        if not product:
            return None, None
        
        # Try to access descriptionHtml as attribute first (if selected in GraphQL)
        product_description = getattr(product, 'descriptionHtml', None)
        
        # Fall back to __json_data__ if not available as attribute
        if not product_description and hasattr(product, '__json_data__'):
            product_data = product.__json_data__
            product_description = product_data.get('descriptionHtml', '')
        
        if not product_description:
            return None, None
        
        season_start_date_str, off_dates_str = extract_season_dates(product_description)
        
        if not season_start_date_str:
            return None, None
        
        estimated_refund_amount, estimated_refund_message = calculate_refund_amount(
            season_start_date_str=season_start_date_str,
            off_dates_str=off_dates_str,
            total_amount_paid=total_amount,
            refund_type=refund_type,
            request_submitted_at=submitted_at
        )
        
        return estimated_refund_amount, estimated_refund_message
    
    # ============================================================================
    # PRODUCTS
    # ============================================================================
    
    def get_product_by_identifier(
        self,
        query_params: Dict[str, Any],
        variants_first: int = 5
    ) -> List[Any]:
        """
        Get product by identifier using Shopify SGQLC client.
        
        Handles the complete flow:
        1. Builds and executes the GraphQL query
        2. Checks for GraphQL errors (raises if found)
        3. Interprets results into native objects
        4. Extracts products from result
        5. Returns list of product objects or raises if none found
        
        Args:
            query_params: Dict with keys:
                - query: GraphQL search query string (e.g., "id:123", "handle:product-handle")
                - first: Number of results to fetch (default: 1)
                - not_found_message: Error message if not found (optional)
                - identifier: Original identifier string (optional, for reference)
            variants_first: Number of variants to fetch per product (default: 5)
        
        Returns:
            List of product objects (sgqlc Type instances)
        
        Raises:
            RuntimeError: If the HTTP request fails (non-200 status or network errors)
            ValueError: If GraphQL errors are present, results can't be interpreted, or no products found
        """
        query_str = query_params["query"]
        first = query_params.get("first", 1)
        
        # Build query operation (domain-specific logic in models)
        op = Query.build_product_query(query_str, first=first, variants_first=variants_first)
        
        # Execute with generic client
        response = self.client.execute(op)
        
        # Check for GraphQL errors
        if response.get('errors'):
            error_msg = f"GraphQL query failed with {len(response.get('errors', []))} errors\n❌ GraphQL errors: {json.dumps(response.get('errors'), indent=2)}"
            raise ValueError(error_msg)
        
        # Interpret results into native objects (op + data pattern)
        try:
            query_result = op + response
        except Exception as e:
            error_msg = f"Error interpreting results: {type(e).__name__}: {e}\n{json.dumps(response, indent=2, default=str)}"
            raise ValueError(error_msg) from e
        
        # Extract products from result
        products_connection = query_result.products
        products_nodes = products_connection.nodes if products_connection else []
        
        # Check for empty products
        if not products_nodes:
            not_found_msg = query_params.get('not_found_message', 'No products found')
            raise ValueError(f"{not_found_msg}\n{json.dumps(response, indent=2, default=str)}")
        
        return products_nodes
    
    # TODO: Implement additional product operations
    # def create_product(...)
    # def update_product(...)
    
    # ============================================================================
    # INVENTORY
    # ============================================================================
    
    def get_product_id_from_variant(self, variant_id: str) -> Optional[str]:
        """
        Get product ID from variant ID.
        
        Args:
            variant_id: Variant ID (gid://shopify/ProductVariant/... or numeric ID)
        
        Returns:
            Product ID (gid://shopify/Product/...) or None if not found
            
        Raises:
            ValueError: If GraphQL query fails with errors
        """
        # Normalize variant ID to GID format
        normalized = normalize_variant_id(variant_id)
        if not normalized:
            raise ValueError(f"Failed to normalize variant ID: {variant_id}")
        
        # Use GID format for GraphQL query
        variant_gid = normalized.get('gid')
        if not variant_gid:
            raise ValueError(f"No GID found in normalized variant ID: {normalized}")
        
        op = Query.build_variant_query(variant_gid)
        
        try:
            response = self.client.execute(op)
            
            if response.get('errors'):
                error_msg = f"GraphQL query failed with {len(response.get('errors', []))} errors\n❌ GraphQL errors: {json.dumps(response.get('errors'), indent=2)}"
                logger.error(f"GraphQL query failed for variant {variant_id}: {error_msg}")
                raise ValueError(error_msg)
            
            query_result = op + response
            variant = getattr(query_result, 'productVariant', None)  # type: ignore[attr-defined]
            if variant:
                product = getattr(variant, 'product', None)  # type: ignore[attr-defined]
                if product:
                    return getattr(product, 'id', None)  # type: ignore[attr-defined]
        except ValueError:
            # Re-raise ValueError (GraphQL errors)
            raise
        except Exception as e:
            logger.error(f"Exception getting product ID from variant {variant_id}: {e}", exc_info=True)
            raise ValueError(f"Failed to get product ID from variant {variant_id}: {e}") from e
        
        raise ValueError(f"Variant {variant_id} not found or has no associated product")
    
    def get_product_variants_for_restock(self, variant_id: str) -> List[Dict[str, Any]]:
        """
        Get all variants for a product, starting from a variant ID.
        
        Fetches the product ID from the variant, then fetches all variants for that product.
        
        Args:
            variant_id: Variant ID (gid://shopify/ProductVariant/... or numeric ID)
        
        Returns:
            List of variant dicts with keys:
            - id: Variant ID
            - title: Variant title
            - inventory_quantity: Current inventory quantity
            - inventory_item_id: Inventory item ID
            
        Raises:
            ValueError: If variant lookup or product query fails
        """
        # Get product ID from variant (raises ValueError on failure)
        product_id = self.get_product_id_from_variant(variant_id)
        if not product_id:
            raise ValueError(f"Failed to get product ID from variant {variant_id}")
        
        # Use minimal query builder for restock (only selects needed fields)
        # This avoids high query cost from selecting all product fields recursively
        op = Query.build_product_variants_query(product_id, variants_first=10)
        
        try:
            response = self.client.execute(op)
            
            if response.get('errors'):
                error_msg = f"GraphQL query failed with {len(response.get('errors', []))} errors\n❌ GraphQL errors: {json.dumps(response.get('errors'), indent=2)}"
                logger.error(f"GraphQL query failed for product {product_id}: {error_msg}")
                raise ValueError(error_msg)
            
            query_result = op + response
            products_conn = getattr(query_result, 'products', None)  # type: ignore[attr-defined]
            if not products_conn or not products_conn.nodes:
                return []
            
            product = products_conn.nodes[0]
            variants_conn = getattr(product, 'variants', None)  # type: ignore[attr-defined]
            if not variants_conn:
                return []
            
            variants = []
            nodes = getattr(variants_conn, 'nodes', None)  # type: ignore[attr-defined]
            if nodes:
                for variant in nodes:
                    inventory_item = getattr(variant, 'inventoryItem', None)  # type: ignore[attr-defined]
                    inventory_item_id = None
                    if inventory_item:
                        inventory_item_id = getattr(inventory_item, 'id', None)  # type: ignore[attr-defined]
                    
                    variants.append({
                        'id': getattr(variant, 'id', None),  # type: ignore[attr-defined]
                        'title': getattr(variant, 'title', 'Unknown'),  # type: ignore[attr-defined]
                        'inventory_quantity': getattr(variant, 'inventoryQuantity', None),  # type: ignore[attr-defined]
                        'inventory_item_id': inventory_item_id
                    })
            
            return variants
        except Exception:
            return []
    
    def get_first_location_id(self) -> Optional[str]:
        """
        Get the first available location ID.
        
        Returns:
            Location ID (gid://shopify/Location/...) or None if not found
        """
        op = Query.build_location_query(first=1)
        
        try:
            response = self.client.execute(op)
            
            if response.get('errors'):
                return None
            
            query_result = op + response
            locations_conn = getattr(query_result, 'locations', None)  # type: ignore[attr-defined]
            if locations_conn:
                nodes = getattr(locations_conn, 'nodes', None)  # type: ignore[attr-defined]
                if nodes and len(nodes) > 0:
                    location = nodes[0]
                    return getattr(location, 'id', None)  # type: ignore[attr-defined]
        except Exception:
            pass
        
        return None
    
    def update_inventory(
        self,
        inventory_item_id: str,
        location_id: str,
        delta: int,
        reference_uri: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update inventory for a single variant (can increase or decrease).
        
        Args:
            inventory_item_id: Inventory item ID (gid://shopify/InventoryItem/...)
            location_id: Location ID (gid://shopify/Location/...)
            delta: Quantity change (positive to increase, negative to decrease)
            reference_uri: Optional reference URI for the adjustment
        
        Returns:
            Dict with structure:
            {
                "success": bool,
                "data": {...},  # Adjustment data if successful
                "errors": [...],  # User errors if failed
                "message": str  # Error message if failed
            }
        """
        from datetime import datetime
        
        if not reference_uri:
            reference_uri = f"logistics://cli-inventory-update/{datetime.utcnow().isoformat()}"
        
        request = {
            "inventory_item_id": inventory_item_id,
            "location_id": location_id,
            "delta": delta,
            "reason": "correction",
            "name": "available",
            "reference_uri": reference_uri
        }
        
        return self.adjust_inventory(request)
    
    # ============================================================================
    # UI / PAGES
    # ============================================================================
    
    def get_page(
        self,
        page_handle: str,
        output_format: str = "text"
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a Shopify page by handle.
        
        Args:
            page_handle: The page handle (e.g., "contact", "about")
            output_format: Output format ("text", "json", "html")
        
        Returns:
            Page data dictionary with keys:
            - id: Page ID
            - title: Page title
            - handle: Page handle
            - body_html: Page HTML content
            - template_suffix: Template suffix (if any)
            Or None if not found
        """
        import os
        import requests
        
        # Get SSL verification setting
        ssl_cert_file = os.getenv('SSL_CERT_FILE', '/opt/homebrew/etc/openssl@3/cert.pem')
        verify_ssl = ssl_cert_file if os.path.exists(ssl_cert_file) else True
        
        # Build API URL
        store_id = self.client.config.get('store_id')
        store_url = f"https://{store_id}.myshopify.com"
        api_url = f"{store_url}/admin/api/2024-10/pages.json"
        
        headers = {
            "X-Shopify-Access-Token": self.client.config.get('token'),
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(api_url, headers=headers, timeout=10, verify=verify_ssl)
            response.raise_for_status()
            
            pages_data = response.json()
            pages = pages_data.get("pages", [])
            
            # Find page by handle
            page = next((p for p in pages if p.get("handle") == page_handle), None)
            
            if not page:
                return None
            
            # Format output based on output_format
            if output_format == "json":
                return page
            elif output_format == "html":
                return {"body_html": page.get("body_html", "")}
            else:
                # text format - return full page data
                return page
            
        except requests.RequestException as e:
            logger.error(f"Error fetching page: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"API Response: {json.dumps(error_data, indent=2)}")
                except (ValueError, AttributeError):
                    logger.error(f"Response Text: {e.response.text}")
            return None
    
    def get_theme_asset(
        self,
        theme_id: str,
        asset_key: str,
        output_format: str = "text"
    ) -> Optional[str]:
        """
        Fetch a theme asset (template, section, snippet).
        
        Args:
            theme_id: The theme ID
            asset_key: The asset key (e.g., "templates/page.about-us-2.json")
            output_format: Output format ("text", "json")
        
        Returns:
            Asset content as string, or None if not found
        """
        import os
        import requests
        
        # Get SSL verification setting
        ssl_cert_file = os.getenv('SSL_CERT_FILE', '/opt/homebrew/etc/openssl@3/cert.pem')
        verify_ssl = ssl_cert_file if os.path.exists(ssl_cert_file) else True
        
        # Build API URL
        store_id = self.client.config.get('store_id')
        store_url = f"https://{store_id}.myshopify.com"
        api_url = f"{store_url}/admin/api/2024-10/themes/{theme_id}/assets.json"
        
        headers = {
            "X-Shopify-Access-Token": self.client.config.get('token'),
            "Content-Type": "application/json"
        }
        
        params = {"asset[key]": asset_key}
        
        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=10, verify=verify_ssl)
            response.raise_for_status()
            
            asset_data = response.json()
            asset = asset_data.get("asset")
            
            if not asset:
                return None
            
            content = asset.get("value") or asset.get("attachment")
            
            if output_format == "json" and asset_key.endswith(".json"):
                try:
                    parsed = json.loads(content)
                    return json.dumps(parsed, indent=2)
                except json.JSONDecodeError:
                    return content
            elif output_format == "json":
                return json.dumps(asset, indent=2)
            else:
                return content
            
        except requests.RequestException as e:
            logger.error(f"Error fetching theme asset: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"API Response: {json.dumps(error_data, indent=2)}")
                except (ValueError, AttributeError):
                    logger.error(f"Response Text: {e.response.text}")
            return None
    
    def list_theme_assets(
        self,
        theme_id: str,
        filter_pattern: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all assets in a theme.
        
        Args:
            theme_id: The theme ID
            filter_pattern: Optional pattern to filter assets (e.g., "template", "about")
        
        Returns:
            List of asset dictionaries with keys: key, size, etc.
        """
        import os
        import requests
        
        # Get SSL verification setting
        ssl_cert_file = os.getenv('SSL_CERT_FILE', '/opt/homebrew/etc/openssl@3/cert.pem')
        verify_ssl = ssl_cert_file if os.path.exists(ssl_cert_file) else True
        
        # Build API URL
        store_id = self.client.config.get('store_id')
        store_url = f"https://{store_id}.myshopify.com"
        api_url = f"{store_url}/admin/api/2024-10/themes/{theme_id}/assets.json"
        
        headers = {
            "X-Shopify-Access-Token": self.client.config.get('token'),
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(api_url, headers=headers, timeout=10, verify=verify_ssl)
            response.raise_for_status()
            
            assets_data = response.json()
            assets = assets_data.get("assets", [])
            
            if filter_pattern:
                assets = [a for a in assets if filter_pattern.lower() in a.get("key", "").lower()]
            
            return assets
            
        except requests.RequestException as e:
            logger.error(f"Error listing theme assets: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"API Response: {json.dumps(error_data, indent=2)}")
                except (ValueError, AttributeError):
                    logger.error(f"Response Text: {e.response.text}")
            return []
    
    def extract_leadership_positions(
        self,
        theme_id: str,
        asset_key: str = "templates/page.template-about-us-2.json",
        raw: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Extract leadership position titles from the About Us page template.
        
        Args:
            theme_id: The Shopify theme ID
            asset_key: The template asset key (defaults to About Us template)
            raw: If True, return raw API response instead of extracted positions
        
        Returns:
            If raw=True: Dict with template data
            If raw=False: Dict with keys:
                - positions: List of (name, position) tuples
                - unique_positions: Sorted list of unique position titles
                - total_count: Total number of entries
                - unique_count: Number of unique positions
        """
        content = self.get_theme_asset(theme_id, asset_key, output_format="text")
        
        if not content:
            return None
        
        try:
            template_data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing template JSON: {e}")
            return None
        
        # If raw mode, return template data
        if raw:
            return template_data
        
        # Extract positions
        positions = []
        
        if 'sections' in template_data:
            for section_id, section_data in template_data['sections'].items():
                if 'blocks' in section_data:
                    for block_id, block_data in section_data['blocks'].items():
                        if block_data.get('type') == 'Text':
                            settings = block_data.get('settings', {})
                            name = settings.get('text', '').strip()
                            position = settings.get('description', '').strip()
                            
                            if position and name:
                                positions.append((name, position))
        
        unique_positions = sorted(set([p[1] for p in positions]), key=lambda x: x.lower())
        
        return {
            "positions": positions,
            "unique_positions": unique_positions,
            "total_count": len(positions),
            "unique_count": len(unique_positions)
        }
    
    def update_page(
        self,
        theme_id: str,
        asset_key: str,
        template_data: Dict[str, Any],
        dry_run: bool = False
    ) -> bool:
        """
        Update a theme template asset.
        
        Args:
            theme_id: Shopify theme ID
            asset_key: Template asset key
            template_data: Updated template data (dict)
            dry_run: If True, return True without actually updating
        
        Returns:
            True if successful, False otherwise
        """
        import os
        import requests
        
        if dry_run:
            return True
        
        # Get SSL verification setting
        ssl_cert_file = os.getenv('SSL_CERT_FILE', '/opt/homebrew/etc/openssl@3/cert.pem')
        verify_ssl = ssl_cert_file if os.path.exists(ssl_cert_file) else True
        
        # Build API URL
        store_id = self.client.config.get('store_id')
        store_url = f"https://{store_id}.myshopify.com"
        api_url = f"{store_url}/admin/api/2024-10/themes/{theme_id}/assets.json"
        
        headers = {
            "X-Shopify-Access-Token": self.client.config.get('token'),
            "Content-Type": "application/json"
        }
        
        payload = {
            "asset": {
                "key": asset_key,
                "value": json.dumps(template_data)
            }
        }
        
        try:
            response = requests.put(api_url, headers=headers, json=payload, verify=verify_ssl, timeout=30)
            response.raise_for_status()
            return True
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error updating template: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    logger.error(f"API Response: {json.dumps(error_details, indent=2)}")
                except json.JSONDecodeError:
                    logger.error(f"Response Text: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating template: {e}")
            return False
    
    def upload_image(
        self,
        theme_id: str,
        image_path: str,
        shopify_path: str
    ) -> Optional[str]:
        """
        Upload an image file to Shopify theme assets.
        
        Args:
            theme_id: Shopify theme ID
            image_path: Local path to image file
            shopify_path: Path in Shopify (e.g., "assets/leadership/john_doe.jpg")
        
        Returns:
            Shopify URL reference (e.g., "shopify://shop_images/john_doe.jpg") or None if failed
        """
        import os
        import base64
        import requests
        from pathlib import Path
        
        # Read image file as base64
        try:
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
        except FileNotFoundError:
            logger.error(f"Image file not found: {image_path}")
            return None
        except Exception as e:
            logger.error(f"Error reading image: {e}")
            return None
        
        # Get SSL verification setting
        ssl_cert_file = os.getenv('SSL_CERT_FILE', '/opt/homebrew/etc/openssl@3/cert.pem')
        verify_ssl = ssl_cert_file if os.path.exists(ssl_cert_file) else True
        
        # Build API URL
        store_id = self.client.config.get('store_id')
        store_url = f"https://{store_id}.myshopify.com"
        api_url = f"{store_url}/admin/api/2024-10/themes/{theme_id}/assets.json"
        
        headers = {
            "X-Shopify-Access-Token": self.client.config.get('token'),
            "Content-Type": "application/json"
        }
        
        payload = {
            "asset": {
                "key": shopify_path,
                "attachment": image_data
            }
        }
        
        try:
            response = requests.put(api_url, headers=headers, json=payload, verify=verify_ssl, timeout=30)
            response.raise_for_status()
            
            # Extract filename for shopify:// reference
            filename = Path(shopify_path).name
            shopify_reference = f"shopify://shop_images/{filename}"
            
            return shopify_reference
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error uploading image: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    logger.error(f"API Response: {json.dumps(error_details, indent=2)}")
                except json.JSONDecodeError:
                    logger.error(f"Response Text: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error uploading image: {e}")
            return None
    
    # ============================================================================
    # NORMALIZERS
    # ============================================================================
    # Expose normalizer functions as methods for convenience
    
    @staticmethod
    def normalize_order_id(order_id_input: Optional[str]) -> Optional[Dict[str, str]]:
        """Normalize order id to a dict with digits_only and gid."""
        return normalize_order_id(order_id_input)
    
    @staticmethod
    def normalize_order_number(order_number_input: Optional[str]) -> Optional[Dict[str, str]]:
        """Normalize order number to a dict with with_hash and digits_only."""
        return normalize_order_number(order_number_input)
    
    @staticmethod
    def normalize_product_id(product_id_input: Optional[str]) -> Optional[Dict[str, str]]:
        """Normalize a product id."""
        return normalize_product_id(product_id_input)
    
    @staticmethod
    def normalize_customer_id(customer_id_input: Optional[str]) -> Optional[Dict[str, str]]:
        """Normalize a customer id."""
        return normalize_customer_id(customer_id_input)
    
    @staticmethod
    def normalize_transaction_id(transaction_id_input: Optional[str]) -> Optional[Dict[str, str]]:
        """Normalize a transaction id (numeric or GID)."""
        return normalize_transaction_id(transaction_id_input)
    
    @staticmethod
    def normalize_variant_id(variant_id_input: Optional[str]) -> Optional[Dict[str, str]]:
        """Normalize a variant id (numeric or GID)."""
        return normalize_variant_id(variant_id_input)

