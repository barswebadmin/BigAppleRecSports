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
from pathlib import Path
from typing import Dict, Any, List, Optional

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
            error_msg = f"GraphQL errors: {json.dumps(response.get('errors'), indent=2)}"
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
            error_msg = f"GraphQL errors: {json.dumps(response.get('errors'), indent=2)}"
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
    
    # TODO: Implement additional order operations
    # def cancel_order(...)
    # def create_refund(...)
    
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
            error_msg = f"GraphQL errors: {json.dumps(response.get('errors'), indent=2)}"
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
    
    # TODO: Implement inventory operations
    # def adjust_inventory(...)
    # def get_inventory_item(...)
    
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

