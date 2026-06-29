"""
Main Shopify service - Table of Contents for all Shopify operations.

Provides a clean interface to all Shopify operations organized by resource:
- Customers (get, search, update)
- Orders (get, search, update, cancel, refund)
- Products (get, create, update)
- Inventory (adjustments, movements)


This service is pure Shopify - no BARS domain logic.
"""
import datetime
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any as AnyType
    from backend.modules.integrations.shopify.models.sgqlc_models.sgqlc_mutations import CancelReasonType
else:
    CancelReasonType = str  # Runtime fallback
    AnyType = Any

from lib.utils.discount_calculator import calculate_discount_amount
from modules.integrations.shopify.client.shopify_sgqlc_client import ShopifySGQLCClient
from modules.integrations.shopify.models.sgqlc_models.sgqlc_query import Query
from sgqlc.operation import Operation
from config import config
from modules.integrations.shopify.services.shopify_normalizers import (
    normalize_order_identifier,
    normalize_order_number,
    normalize_product_identifier,
    normalize_customer_identifier,
    normalize_transaction_identifier,
    normalize_variant_identifier,
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
        import sys
        print(f"[DEBUG] ShopifyService.__init__: Entry with environment={environment}", file=sys.stderr)
        logger.debug(f"ShopifyService.__init__: Entry with environment={environment}")
        
        print("[DEBUG] ShopifyService.__init__: Creating ShopifySGQLCClient", file=sys.stderr)
        logger.debug("ShopifyService.__init__: Creating ShopifySGQLCClient")
        self.client = ShopifySGQLCClient(environment=environment)
        self.environment = environment
        print(f"[DEBUG] ShopifyService.__init__: Client created: {type(self.client)}", file=sys.stderr)
        logger.debug(f"ShopifyService.__init__: Client created: {type(self.client)}")
    
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
        import sys
        print(f"[DEBUG] ShopifyService.get_customer_by_identifier: Entry with query_params={query_params}, orders_first={orders_first}", file=sys.stderr)
        logger.debug(f"ShopifyService.get_customer_by_identifier: Entry with query_params={query_params}, orders_first={orders_first}")
        
        query_str = query_params["query"]
        first = query_params.get("first", 1)
        
        print(f"[DEBUG] ShopifyService.get_customer_by_identifier: query_str={query_str}, first={first}", file=sys.stderr)
        logger.debug(f"ShopifyService.get_customer_by_identifier: query_str={query_str}, first={first}")
        
        # Build query operation (domain-specific logic in models)
        print("[DEBUG] ShopifyService.get_customer_by_identifier: Building customer query operation", file=sys.stderr)
        logger.debug("ShopifyService.get_customer_by_identifier: Building customer query operation")
        op = Query.build_customer_query(query_str, first=first, orders_first=orders_first)
        print(f"[DEBUG] ShopifyService.get_customer_by_identifier: Query operation built: {type(op)}", file=sys.stderr)
        logger.debug(f"ShopifyService.get_customer_by_identifier: Query operation built: {type(op)}")
        
        # Execute with generic client
        print(f"[DEBUG] ShopifyService.get_customer_by_identifier: Executing query with client={type(self.client)}", file=sys.stderr)
        logger.debug(f"ShopifyService.get_customer_by_identifier: Executing query with client={type(self.client)}")
        try:
            response = self.client.execute(op)
            print(f"[DEBUG] ShopifyService.get_customer_by_identifier: Query executed successfully, response keys: {list(response.keys()) if isinstance(response, dict) else 'not a dict'}", file=sys.stderr)
            logger.debug(f"ShopifyService.get_customer_by_identifier: Query executed successfully, response keys: {list(response.keys()) if isinstance(response, dict) else 'not a dict'}")
        except Exception as e:
            print(f"[DEBUG] ShopifyService.get_customer_by_identifier: Exception during execute: {type(e).__name__}: {e}", file=sys.stderr)
            logger.debug(f"ShopifyService.get_customer_by_identifier: Exception during execute: {type(e).__name__}: {e}", exc_info=True)
            raise
        
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
        
        # Build mutation operation using builder
        from backend.modules.integrations.shopify.models.sgqlc_models.sgqlc_mutations import Mutation
        
        op = Mutation.build_customer_update_mutation(customer_id, email=email, phone=phone)
        
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
    
    def update_customer_tags(
        self,
        email: str,
        new_tags: set[str],
        should_replace: bool = False
    ) -> Dict[str, Any]:
        """
        Update customer tags by email address.
        
        Gets the customer by email, then either replaces all tags or appends new tags
        to existing tags, and sends a customer update request.
        
        Args:
            email: Customer email address
            new_tags: Set of tag strings to add or replace
            should_replace: If True, replaces all tags with new_tags. If False, appends
                new_tags to existing tags (default: False)
        
        Returns:
            Dict with structure:
            {
                "success": bool,
                "data": {...},  # Customer data if successful
                "errors": [...],  # User errors if failed
                "message": str  # Error message if failed
            }
        
        Raises:
            ValueError: If customer not found
        """
        # Get customer by email
        try:
            query_params = {
                "query": f"email:{email}",
                "not_found_message": f"Customer not found with email: {email}",
                "first": 1
            }
            customers = self.get_customer_by_identifier(query_params, orders_first=1)
            if not customers:
                return {"success": False, "message": f"Customer not found with email: {email}"}
            
            customer = customers[0]
            customer_id = customer.id if hasattr(customer, 'id') else None
            if not customer_id:
                return {"success": False, "message": "Customer ID not found in response"}
            
        except ValueError as e:
            return {"success": False, "message": str(e)}
        except Exception as e:
            logger.error(f"Error fetching customer by email {email}: {str(e)}")
            return {"success": False, "message": f"Error fetching customer: {str(e)}"}
        
        # Get existing tags
        existing_tags = []
        if hasattr(customer, 'tags') and customer.tags:
            existing_tags = list(customer.tags) if isinstance(customer.tags, (list, tuple)) else [customer.tags]
        
        # Determine final tags
        if should_replace:
            final_tags = new_tags
        else:
            # Combine existing and new tags, remove duplicates
            final_tags = set(existing_tags) | new_tags
        
        # Convert to comma-separated string (Shopify API format)
        tags_string = ", ".join(sorted(final_tags))
        
        # Build mutation operation using builder
        from backend.modules.integrations.shopify.models.sgqlc_models.sgqlc_mutations import Mutation
        
        op = Mutation.build_customer_update_mutation(customer_id, tags=tags_string)
        
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
        customer_result = payload.customer  # type: ignore[attr-defined]
        customer_data = {
            "id": customer_result.id if customer_result else None,  # type: ignore[attr-defined]
            "email": customer_result.email if customer_result else None,  # type: ignore[attr-defined]
            "tags": list(customer_result.tags) if customer_result and hasattr(customer_result, 'tags') and customer_result.tags else [],  # type: ignore[attr-defined]
        }
        
        return {"success": True, "data": customer_data}
    
    def get_order_line_item_properties(self, order_id: str) -> List[Dict[str, str]]:
        """
        Get line item custom attributes for an order.
        
        Args:
            order_id: Order ID (gid://shopify/Order/... or numeric ID)
            
        Returns:
            List of custom attribute dictionaries with 'key' and 'value' keys
        """
        # Normalize order ID to extract numeric ID for search query
        normalized = normalize_order_identifier(order_id)
        if not normalized:
            logger.error(f"Invalid order ID format: {order_id}")
            return []
        
        # Use numeric ID for search query (Shopify search doesn't accept full GID format)
        numeric_id = normalized["digits_only"]
        orders = self.get_order_by_identifier(
            {"query": f"id:{numeric_id}", "first": 1},
            line_items_first=5
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
        
        def extract_birthday_with_name(properties):
            """Extract birthdays with associated names from properties."""
            birthday = None
            first_name = ""
            last_name = ""
            for prop in properties:
                key = prop.get("key", "").lower()
                value = prop.get("value", "").strip()
                if "date of birth" in key and value:
                    birthday = value
                elif "first name" in key and value and not first_name:
                    first_name = value
                elif "last name" in key and value and not last_name:
                    last_name = value
            return [(birthday, first_name, last_name)] if birthday else []
        
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
        
        def extract_pronouns_with_name(properties):
            """Extract pronouns with associated names from properties."""
            pronouns = None
            first_name = ""
            last_name = ""
            for prop in properties:
                key = prop.get("key", "").lower()
                value = prop.get("value", "").strip()
                if "pronouns" in key and value:
                    pronouns = value.lower()
                elif "first name" in key and value and not first_name:
                    first_name = value
                elif "last name" in key and value and not last_name:
                    last_name = value
            return [(pronouns, first_name, last_name)] if pronouns else []
        
        pronouns_records = []
        
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
        
        # DEBUG: Print raw response
        print(f"\n[DEBUG] Raw GraphQL Response:\n{json.dumps(response, indent=2, default=str)}\n")
        
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
        from backend.modules.integrations.shopify.models.sgqlc_models.sgqlc_mutations import (
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
            from backend.modules.integrations.shopify.models.sgqlc_models.sgqlc_mutations import Mutation
            
            op_begin = Mutation.build_order_edit_begin_mutation(order_id)
            
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
            discount_amount = calculate_discount_amount(
                discount_type, discount_value, unit_price
            )
            
            # Step 4: Add discount
            discount_input = {
                "description": code_desc,
                "fixedValue": {
                    "amount": f"{discount_amount:.2f}",
                    "currencyCode": currency_code
                }
            }
            op_discount = Mutation.build_order_edit_add_line_item_discount_mutation(
                calculated_order_id,
                line_item_id,
                discount_input
            )
            
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
            
            op_commit = Mutation.build_order_edit_commit_mutation(
                calculated_order_id,
                notify_customer=False,
                staff_note=staff_note
            )
            
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
        # Build mutation operation using builder
        from backend.modules.integrations.shopify.models.sgqlc_models.sgqlc_mutations import Mutation
        
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
        
        op = Mutation.build_inventory_adjust_quantities_mutation(input_data)
        
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
    
    def update_product(
        self,
        product_id: str,
        handle: Optional[str] = None,
        tags: Optional[List[str]] = None,
        media: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Update a product's handle, tags, and/or media using Shopify's productUpdate mutation.
        
        Args:
            product_id: Product ID (gid://shopify/Product/...)
            handle: New product handle (optional)
            tags: List of product tags (optional, replaces all tags)
            media: List of media input dicts with keys:
                - originalSource: URL or source of the media (required)
                - alt: Alt text for the media (optional)
                - mediaContentType: Type of media, e.g., "IMAGE" or "VIDEO" (required)
        
        Returns:
            Dict with structure:
            {
                "success": bool,
                "data": {...},  # Product data if successful
                "errors": [...],  # User errors if failed
                "message": str  # Error message if failed
            }
        
        Raises:
            ValueError: If neither handle, tags, nor media is provided
        """
        if handle is None and tags is None and media is None:
            raise ValueError("Must provide at least one of: handle, tags, or media")
        
        # Build mutation operation using builder
        from backend.modules.integrations.shopify.models.sgqlc_models.sgqlc_mutations import Mutation
        
        op = Mutation.build_product_update_mutation(
            product_id,
            handle=handle,
            tags=tags,
            media=media
        )
        
        # Execute mutation
        response = self.client.execute(op)
        
        # Check for GraphQL errors
        if response.get('errors'):
            error_messages = [err.get("message", str(err)) for err in response["errors"]]
            return {"success": False, "errors": error_messages, "message": "; ".join(error_messages)}
        
        # Interpret results
        try:
            mutation_result = op + response
            payload = mutation_result.productUpdate  # type: ignore[attr-defined]
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
        
        # Success - extract product data
        product = payload.product  # type: ignore[attr-defined]
        product_data = {
            "id": product.id if product else None,  # type: ignore[attr-defined]
            "handle": product.handle if product else None,  # type: ignore[attr-defined]
            "tags": list(product.tags) if product and hasattr(product, 'tags') and product.tags else [],  # type: ignore[attr-defined]
        }
        
        # Extract media if it was updated
        if media is not None and product:
            images_conn = getattr(product, 'images', None)  # type: ignore[attr-defined]
            if images_conn:
                images_nodes = getattr(images_conn, 'nodes', None)  # type: ignore[attr-defined]
                if images_nodes:
                    product_data["images"] = [
                        {
                            "url": getattr(img, 'url', None),  # type: ignore[attr-defined]
                            "altText": getattr(img, 'altText', None),  # type: ignore[attr-defined]
                        }
                        for img in images_nodes
                    ]
        
        return {"success": True, "data": product_data}
    
    def update_product_handle(
        self,
        product_id: str,
        handle: str
    ) -> Dict[str, Any]:
        """
        Update a product's handle using Shopify's productUpdate mutation.
        
        Convenience method that calls update_product with handle only.
        
        Args:
            product_id: Product ID (gid://shopify/Product/...)
            handle: New product handle
        
        Returns:
            Dict with structure:
            {
                "success": bool,
                "data": {...},  # Product data if successful
                "errors": [...],  # User errors if failed
                "message": str  # Error message if failed
            }
        """
        return self.update_product(product_id, handle=handle)
    
    def get_product_tags(self, product_id: str) -> List[str]:
        """
        Get current tags for a product by ID.
        
        Args:
            product_id: Product ID (gid://shopify/Product/... or numeric ID)
        
        Returns:
            List of product tags
        
        Raises:
            ValueError: If product not found or query fails
        """
        # Normalize product ID to GID format
        normalized = normalize_product_identifier(product_id)
        if not normalized:
            raise ValueError(f"Failed to normalize product ID: {product_id}")
        
        product_gid = normalized.get('gid')
        if not product_gid:
            raise ValueError(f"No GID found in normalized product ID: {normalized}")
        
        # Use node query to get product by ID
        op = Operation(Query)
        node_sel = op.node(id=product_gid)
        # Cast to Product type
        product_sel = node_sel.__as__('Product')  # type: ignore[attr-defined]
        product_sel.id()  # type: ignore[union-attr]
        product_sel.tags()  # type: ignore[union-attr]
        
        try:
            response = self.client.execute(op)
            
            if response.get('errors'):
                error_msg = f"GraphQL query failed with {len(response.get('errors', []))} errors\n❌ GraphQL errors: {json.dumps(response.get('errors'), indent=2)}"
                logger.error(f"GraphQL query failed for product {product_id}: {error_msg}")
                raise ValueError(error_msg)
            
            query_result = op + response
            node = getattr(query_result, 'node', None)  # type: ignore[attr-defined]
            if node:
                product = getattr(node, '__as__Product', None)  # type: ignore[attr-defined]
                if product:
                    tags = getattr(product, 'tags', None)  # type: ignore[attr-defined]
                    return list(tags) if tags else []
            
            raise ValueError(f"Product {product_id} not found")
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Exception getting tags for product {product_id}: {e}", exc_info=True)
            raise ValueError(f"Failed to get tags for product {product_id}: {e}") from e
    
    def set_product_as_closed(
        self,
        product_id: str,
        closed_image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Set a product as closed by adding "reg:closed" tag and updating media image.
        
        Args:
            product_id: Product ID (gid://shopify/Product/... or numeric ID)
            closed_image_url: URL for the closed image (optional, placeholder if not provided)
        
        Returns:
            Dict with structure:
            {
                "success": bool,
                "data": {...},  # Product data if successful
                "errors": [...],  # User errors if failed
                "message": str  # Error message if failed
            }
        """
        try:
            # Normalize product ID to GID format
            normalized = normalize_product_identifier(product_id)
            if not normalized:
                return {"success": False, "error": "invalid_product_id", "message": f"Failed to normalize product ID: {product_id}"}
            
            product_gid = normalized.get('gid')
            if not product_gid:
                return {"success": False, "error": "invalid_product_id", "message": f"No GID found in normalized product ID: {normalized}"}
            
            # Get current tags
            try:
                current_tags = self.get_product_tags(product_gid)
            except Exception as e:
                logger.error(f"Failed to get current tags for product {product_id}: {e}")
                return {"success": False, "error": "get_tags_failed", "message": str(e)}
            
            # Add "reg:closed" tag if not already present
            new_tags = list(current_tags) if current_tags else []
            if "reg:closed" not in new_tags:
                new_tags.append("reg:closed")
            
            # Prepare media update (placeholder for now)
            media = None
            if closed_image_url:
                media = [{
                    "originalSource": closed_image_url,
                    "alt": "Closed image",
                    "mediaContentType": "IMAGE"
                }]
            
            # Update product with new tags and media
            result = self.update_product(
                product_id=product_gid,
                tags=new_tags,
                media=media
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error setting product {product_id} as closed: {e}", exc_info=True)
            return {"success": False, "error": str(e), "message": f"Failed to set product as closed: {e}"}
    
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
        normalized = normalize_variant_identifier(variant_id)
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
    
    def get_inventory_item_and_quantity(self, variant_gid: str) -> Dict[str, Any]:
        """
        Get inventory item ID and available quantity for a given variant GID.
        
        Args:
            variant_gid: Variant ID (gid://shopify/ProductVariant/...)
        
        Returns:
            Dict with structure:
            {
                "success": bool,
                "inventoryItemId": str,  # Inventory item ID if successful
                "inventoryQuantity": int,  # Current inventory quantity if successful
                "message": str  # Error message if failed
            }
        
        Raises:
            ValueError: If variant not found or GraphQL errors occur
        """
        # Build query operation using builder
        op = Query.build_variant_query(variant_gid)
        
        # Execute with generic client
        response = self.client.execute(op)
        
        # Check for GraphQL errors
        if response.get('errors'):
            error_msg = f"GraphQL query failed with {len(response.get('errors', []))} errors\n❌ GraphQL errors: {json.dumps(response.get('errors'), indent=2)}"
            return {
                "success": False,
                "message": error_msg,
                "inventoryItemId": None,
                "inventoryQuantity": None,
            }
        
        # Interpret results into native objects
        try:
            query_result = op + response
        except Exception as e:
            error_msg = f"Error interpreting results: {type(e).__name__}: {e}\n{json.dumps(response, indent=2, default=str)}"
            return {
                "success": False,
                "message": error_msg,
                "inventoryItemId": None,
                "inventoryQuantity": None,
            }
        
        # Extract variant from result
        variant = getattr(query_result, 'productVariant', None)  # type: ignore[attr-defined]
        if not variant:
            return {
                "success": False,
                "message": f"Variant {variant_gid} not found",
                "inventoryItemId": None,
                "inventoryQuantity": None,
            }
        
        # Extract inventory information
        inventory_item = getattr(variant, 'inventoryItem', None)  # type: ignore[attr-defined]
        inventory_item_id = getattr(inventory_item, 'id', None) if inventory_item else None  # type: ignore[attr-defined]
        inventory_quantity = getattr(variant, 'inventoryQuantity', None)  # type: ignore[attr-defined]
        
        if inventory_item_id is None:
            return {
                "success": False,
                "message": f"Inventory item not found for variant {variant_gid}",
                "inventoryItemId": None,
                "inventoryQuantity": inventory_quantity,
            }
        
        return {
            "success": True,
            "inventoryItemId": inventory_item_id,
            "inventoryQuantity": inventory_quantity,
        }
    
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
        output_format: str = "text",
        theme_id: Optional[str] = None,
        auto_fetch_template: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a Shopify page by handle.
        
        If the page uses a custom template (has template_suffix), automatically fetches
        the template content from theme assets when auto_fetch_template is True.
        
        Args:
            page_handle: The page handle (e.g., "contact", "about")
            output_format: Output format ("text", "json", "html")
            theme_id: Optional theme ID to use for template fetching. If not provided
                and template needs to be fetched, will attempt to use default theme.
            auto_fetch_template: If True, automatically fetch template content when
                page has a template_suffix
        
        Returns:
            Page data dictionary with keys:
            - id: Page ID
            - title: Page title
            - handle: Page handle
            - body_html: Page HTML content (may be empty if using custom template)
            - template_suffix: Template suffix (if any)
            - template_content: Template content (if custom template and auto_fetch_template=True)
            - template_asset_key: Template asset key (if custom template)
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
            
            template_suffix = page.get("template_suffix")
            
            # If page uses custom template and auto_fetch_template is enabled
            if template_suffix and auto_fetch_template:
                # Build template asset key
                # Shopify template naming: templates/page.{template_suffix}.json
                template_asset_key = f"templates/page.{template_suffix}.json"
                
                # Get theme ID if not provided
                if not theme_id:
                    # Try to get current/active theme
                    themes_url = f"{store_url}/admin/api/2024-10/themes.json"
                    themes_response = requests.get(themes_url, headers=headers, timeout=10, verify=verify_ssl)
                    if themes_response.status_code == 200:
                        themes_data = themes_response.json()
                        themes = themes_data.get("themes", [])
                        # Find main/published theme
                        main_theme = next((t for t in themes if t.get("role") == "main"), None)
                        if main_theme:
                            theme_id = str(main_theme.get("id"))
                
                # Fetch template content if we have a theme_id
                if theme_id:
                    try:
                        template_content = self.get_theme_asset(theme_id, template_asset_key, output_format=output_format)
                        if template_content:
                            page["template_content"] = template_content
                            page["template_asset_key"] = template_asset_key
                            page["theme_id"] = theme_id
                    except Exception as e:
                        logger.warning(f"Could not fetch template content: {e}")
                        # Continue without template content
            
            # Format output based on output_format
            if output_format == "json":
                return page
            elif output_format == "html":
                # For HTML output, prefer template content if available
                if page.get("template_content"):
                    return {"body_html": page.get("template_content", "")}
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
        
        # Template assets require an order field - always include it
        payload = {
            "asset": {
                "key": asset_key,
                "value": json.dumps(template_data),
                "order": 0  # Use 0 as default for template assets
            }
        }
        
        logger.info(f"Updating template asset with order=0")
        
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
                    # Re-raise with more specific error message
                    if "missing required key 'order'" in str(error_details):
                        raise RuntimeError(f"Shopify API error: Asset order field is required but missing. Response: {error_details}")
                    else:
                        raise RuntimeError(f"Shopify API error: {error_details}")
                except json.JSONDecodeError:
                    logger.error(f"Response Text: {e.response.text}")
                    raise RuntimeError(f"Shopify API error: {e.response.text}")
            raise RuntimeError(f"HTTP error updating template: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating template: {e}")
            raise RuntimeError(f"Unexpected error updating template: {e}")
    
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
    
    def _get_theme_template_dict(
        self,
        theme_id: str,
        asset_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Internal method: Get a theme template asset as parsed JSON dict.
        
        Use ThemeTemplateService.get_template_model() for typed models instead.
        
        Args:
            theme_id: The theme ID
            asset_key: The asset key (e.g., "templates/page.template-about-us-2.json")
        
        Returns:
            Parsed JSON template data as dict, or None if not found or invalid JSON
        """
        content = self.get_theme_asset(theme_id, asset_key, output_format="text")
        
        if not content:
            return None
        
        try:
            template_data = json.loads(content)
            return template_data
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing template JSON: {e}")
            return None
    
    def find_blocks_by_name(
        self,
        template_data: Dict[str, Any],
        name: str
    ) -> List[Tuple[str, str, Dict[str, Any]]]:
        """
        DEPRECATED: Use ThemeTemplateService.find_blocks_by_name() for typed models.
        
        Find blocks in template by person name.
        
        Searches through all sections and blocks in the template, looking for blocks
        where the 'text' setting matches the provided name (case-insensitive).
        
        Args:
            template_data: Parsed template JSON data (dict)
            name: Person name to search for (matched against block settings.text)
        
        Returns:
            List of (section_id, block_id, block_data) tuples for matching blocks
        """
        matches = []
        name_lower = name.lower().strip()
        
        if 'sections' not in template_data:
            return matches
        
        for section_id, section_data in template_data['sections'].items():
            if 'blocks' not in section_data:
                continue
            
            for block_id, block_data in section_data['blocks'].items():
                settings = block_data.get('settings', {})
                block_text = settings.get('text', '').strip()
                
                if block_text.lower() == name_lower:
                    matches.append((section_id, block_id, block_data))
        
        return matches
    
    def update_theme_asset(
        self,
        theme_id: str,
        asset_key: str,
        template_data: Dict[str, Any],
        dry_run: bool = False
    ) -> bool:
        """
        Update a theme template asset.
        
        Alias for update_page() with same functionality.
        
        Args:
            theme_id: Shopify theme ID
            asset_key: Template asset key
            template_data: Updated template data (dict)
            dry_run: If True, return True without actually updating
        
        Returns:
            True if successful, False otherwise
        """
        return self.update_page(theme_id, asset_key, template_data, dry_run=dry_run)
    
    def upload_theme_image(
        self,
        theme_id: str,
        image_path: str,
        shopify_path: str
    ) -> Optional[str]:
        """
        Upload an image file to Shopify theme assets.
        
        Alias for upload_image() with same functionality.
        
        Args:
            theme_id: Shopify theme ID
            image_path: Local path to image file
            shopify_path: Path in Shopify (e.g., "assets/leadership/john_doe.jpg")
        
        Returns:
            Shopify URL reference (e.g., "shopify://shop_images/john_doe.jpg") or None if failed
        """
        return self.upload_image(theme_id, image_path, shopify_path)
    
    def get_file_admin_url(self, image_reference: Optional[str]) -> Optional[Dict[str, str]]:
        """
        Get Shopify admin URL and original filename for a file from a shopify:// image reference.
        
        Args:
            image_reference: Shopify image reference (e.g., "shopify://shop_images/Eliana_Glatt.jpg")
        
        Returns:
            Dict with keys:
            - "url": Admin URL (e.g., "https://admin.shopify.com/store/09fe59-3/content/files/25520668311646")
            - "filename": Original filename from Shopify
            or None if file not found or reference is invalid
        """
        if not image_reference or not image_reference.startswith("shopify://"):
            return None
        
        import re
        
        # Extract filename from shopify:// reference
        # Format: shopify://shop_images/filename.jpg
        match = re.match(r"shopify://shop_images/(.+)", image_reference)
        if not match:
            return None
        
        filename = match.group(1)
        store_id = self.client.config.get('store_id')
        
        try:
            # Use sgqlc to build and execute the files query
            from backend.modules.integrations.shopify.models.sgqlc_models.sgqlc_query import Query
            
            query_str = f"filename:{filename}"
            op = Query.build_files_query(query_str, first=10)
            
            # Execute using the client
            result = self.client.execute(op)
            
            if result.get('errors'):
                logger.warning(f"GraphQL errors querying files: {result.get('errors')}")
                return None
            
            files_data = result.get('data', {}).get('files', {})
            nodes = files_data.get('nodes', [])
            
            if not nodes:
                logger.warning(f"File not found for reference: {image_reference}")
                return None
            
            # Get the first matching file
            file_node = nodes[0]
            file_gid = file_node.get('id')
            
            if not file_gid:
                logger.warning(f"File ID not found in response for: {image_reference}")
                return None
            
            # Extract numeric ID from GID (format: gid://shopify/File/25520668311646 or gid://shopify/MediaImage/25520668311646)
            gid_match = re.search(r'/(?:File|MediaImage)/(\d+)', file_gid)
            if not gid_match:
                logger.warning(f"Could not extract file ID from GID: {file_gid}")
                return None
            
            file_id = gid_match.group(1)
            
            # Construct admin URL
            admin_url = f"https://admin.shopify.com/store/{store_id}/content/files/{file_id}"
            
            return {
                "url": admin_url,
                "display_text": image_reference  # Use original shopify:// reference as display text
            }
            
        except Exception as e:
            logger.error(f"Error querying Shopify Files API: {e}")
            return None
    
    def get_file_name_by_id(self, file_id: str) -> Optional[str]:
        """
        Get filename for a file by its numeric ID using REST API.
        
        Args:
            file_id: Numeric file ID (e.g., "23046869844062")
        
        Returns:
            Filename (e.g., "Joe_Randazzo.jpg") or None if not found
        """
        import requests
        
        try:
            store_id = self.client.config.get('store_id')
            access_token = self.client.config.get('access_token')
            
            if not store_id or not access_token:
                logger.warning("Missing store_id or access_token for REST API call")
                return None
            
            rest_url = f"https://{store_id}.myshopify.com/admin/api/2024-10/files/{file_id}.json"
            headers = {
                'X-Shopify-Access-Token': access_token,
                'Content-Type': 'application/json'
            }
            
            response = requests.get(rest_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                file_data = response.json().get('file', {})
                # Extract filename from key or url
                file_key = file_data.get('key', '')
                if file_key:
                    # Extract filename from key (e.g., "assets/leadership/Joe_Randazzo.jpg")
                    filename = file_key.split('/')[-1]
                    return filename
                
                # Fallback: try to extract from URL
                file_url = file_data.get('url', '')
                if file_url:
                    filename = file_url.split('/')[-1].split('?')[0]
                    return filename
            
            logger.warning(f"File not found for ID: {file_id} (status: {response.status_code})")
            return None
            
        except Exception as e:
            logger.error(f"Error getting file name by ID: {e}")
            return None
    
    def convert_admin_url_to_shopify_reference(self, admin_url: str) -> Optional[str]:
        """
        Convert Shopify admin URL to shopify:// reference.
        
        Args:
            admin_url: Admin URL like 'https://admin.shopify.com/store/09fe59-3/content/files/23046869844062'
        
        Returns:
            shopify:// reference like 'shopify://shop_images/Joe_Randazzo.jpg' or None if error
        """
        import re
        
        # Extract file ID from URL
        match = re.search(r'/content/files/(\d+)', admin_url)
        if not match:
            logger.warning(f"Could not extract file ID from URL: {admin_url}")
            return None
        
        file_id = match.group(1)
        
        # Get filename by ID
        filename = self.get_file_name_by_id(file_id)
        if not filename:
            return None
        
        # Construct shopify:// reference
        return f"shopify://shop_images/{filename}"
    
    # ============================================================================
    # NORMALIZERS
    # ============================================================================
    # Expose normalizer functions as methods for convenience
    
    @staticmethod
    def normalize_order_identifier(order_id_input: str) -> Optional[Dict[str, Optional[str]]]:
        """Normalize order id to a dict with digits_only and gid."""
        return normalize_order_identifier(order_id_input)
    
    @staticmethod
    def normalize_order_number(order_number_input: str) -> Optional[dict[Any, Any]]:
        """Normalize order number to a dict with with_hash and digits_only."""
        return normalize_order_number(order_number_input)
    
    @staticmethod
    def normalize_product_identifier(product_id_input: str) -> Optional[Dict[str, Optional[str]]]:
        """Normalize a product id."""
        return normalize_product_identifier(product_id_input)
    
    @staticmethod
    def normalize_customer_identifier(customer_id_input: str) -> Optional[dict[Any, Any]]:
        """Normalize a customer id."""
        return normalize_customer_identifier(customer_id_input)
    
    @staticmethod
    def normalize_transaction_identifier(transaction_id_input: str) -> Optional[dict[Any, Any]]:
        """Normalize a transaction id (numeric or GID)."""
        return normalize_transaction_identifier(transaction_id_input)
    
    @staticmethod
    def normalize_variant_identifier(variant_id_input: str, product_id_input: Optional[str] = None) -> Optional[dict[Any, Any]]:
        """Normalize a variant id (numeric or GID)."""
        return normalize_variant_identifier(variant_id_input, product_id_input)

