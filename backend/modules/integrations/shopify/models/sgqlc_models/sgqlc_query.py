"""
SGQLC Query classes for Shopify GraphQL API.

Provides BaseQuery with generic field selection helpers and Query with
customer and order-specific fields and helpers.
"""

from typing import Optional
from sgqlc.types import Type, Field, String, ID
from sgqlc.types.relay import connection_args
from sgqlc.operation import Operation

from backend.modules.integrations.shopify.models.sgqlc_models import CustomerConnection, OrderConnection, ProductConnection
from backend.modules.integrations.shopify.models import sgqlc_models


class BaseQuery(Type):
    """Base Query class with reusable field selection methods.
    
    This class provides generic field selection utilities that can be used
    with any sgqlc Type model. Specific query types (Query, OrderQuery, etc.)
    can extend this class to add domain-specific fields and helper methods.
    """
    
    @staticmethod
    def _get_field_info(model_class, field_name):
        """Unified field inspection: returns (field_category, inner_type_class).
        
        Args:
            model_class: The sgqlc Type model class
            field_name: Name of the field to inspect
        
        Returns:
            tuple: (field_category, inner_type_class)
            - field_category: 'connection' | 'list' | 'object' | 'scalar' | None
            - inner_type_class: The Type class to recurse into, or None
        
        Examples:
            Customer.orders -> ('connection', Order)
            Order.refunds -> ('list', Refund)
            Customer.defaultAddress -> ('object', Address)
            Customer.email -> ('scalar', None)
        """
        from sgqlc.types import Field
        from sgqlc.types.relay import Connection
        import re
        
        field = getattr(model_class, field_name, None)
        if not field:
            return (None, None)
        
        # Get the type representation
        type_repr = None
        if isinstance(field, Field):
            if hasattr(field, 'type'):
                type_repr = field.type
        else:
            # Direct assignment (not wrapped in Field) - could be a string forward reference
            # or a type class directly
            type_repr = field
        
        # Check for string forward reference first (before other checks)
        # This handles cases like customer: Optional["Customer"] where the bridge
        # stores it as a string "Customer" in the sgqlc Type
        if isinstance(type_repr, str) and not type_repr.startswith('['):
            # Try to resolve the string to an actual type from sgqlc_models
            if hasattr(sgqlc_models, type_repr):
                resolved_type = getattr(sgqlc_models, type_repr)
                # Check if it's a Type subclass (object type)
                from sgqlc.types import Type as SGQLCType
                if isinstance(resolved_type, type) and issubclass(resolved_type, SGQLCType):
                    type_name = getattr(resolved_type, '__name__', '')
                    is_edge = 'Edge' in type_name
                    if not issubclass(resolved_type, Connection) and not is_edge:
                        return ('object', resolved_type)
        
        # Check for Connection (has pagination args)
        if isinstance(field, Field) and hasattr(field, 'args') and field.args:
            connection_keys = {'first', 'after', 'before', 'last'}
            has_pagination = any(k in field.args for k in connection_keys)
            
            if has_pagination:
                # It's a Connection - extract node type
                
                # Handle string forward reference (e.g., 'OrderConnection')
                if isinstance(type_repr, str):
                    node_name = type_repr.replace('Connection', '')
                    if hasattr(sgqlc_models, node_name):
                        node_class = getattr(sgqlc_models, node_name)
                        return ('connection', node_class)
                
                # Handle Connection class
                elif isinstance(type_repr, type) and issubclass(type_repr, Connection):
                    # Try to get node type from Connection.nodes
                    if hasattr(type_repr, 'nodes'):
                        # nodes_field.type is [NodeType] (ContainerTypeMeta), not the class
                        # So we use the fallback: extract from class name
                        node_name = type_repr.__name__.replace('Connection', '')
                        
                        if hasattr(sgqlc_models, node_name):
                            node_class = getattr(sgqlc_models, node_name)
                            return ('connection', node_class)
                
                # Couldn't resolve Connection type
                return ('connection', None)
        
        # Check for list (field.type is [TypeName] string or list_of)
        if isinstance(field, Field) and isinstance(type_repr, str) and type_repr.startswith('['):
            if 'Connection' not in type_repr:
                # Extract type name from [TypeName]
                match = re.search(r'\[([^\]]+)\]', type_repr)
                if match:
                    type_name = match.group(1).strip()
                    if hasattr(sgqlc_models, type_name):
                        item_class = getattr(sgqlc_models, type_name)
                        return ('list', item_class)
        
        # Check for direct list_of assignment (not wrapped in Field)
        if not isinstance(field, Field):
            field_type_str = str(type(field))
            if 'list_of' in field_type_str and 'Connection' not in field_type_str:
                # Try to extract from field representation
                field_str = str(field)
                match = re.search(r'\[([^\]]+)\]', field_str)
                if match:
                    type_name = match.group(1).strip()
                    if hasattr(sgqlc_models, type_name):
                        item_class = getattr(sgqlc_models, type_name)
                        return ('list', item_class)
        
        # Check for string forward reference (e.g., "Customer" in Optional["Customer"])
        if isinstance(type_repr, str) and not type_repr.startswith('['):
            # Try to resolve the string to an actual type from sgqlc_models
            if hasattr(sgqlc_models, type_repr):
                resolved_type = getattr(sgqlc_models, type_repr)
                # Check if it's a Type subclass (object type)
                from sgqlc.types import Type as SGQLCType
                if isinstance(resolved_type, type) and issubclass(resolved_type, SGQLCType):
                    type_name = getattr(resolved_type, '__name__', '')
                    is_edge = 'Edge' in type_name
                    if not issubclass(resolved_type, Connection) and not is_edge:
                        return ('object', resolved_type)
        
        # Check if field type is String but should be an object (bridge converted forward ref to String)
        # Try to resolve from field name (e.g., "customer" -> "Customer")
        if isinstance(type_repr, type):
            from sgqlc.types import String, Type as SGQLCType
            if type_repr is String:
                # Field was converted to String by bridge - try to resolve from field name
                # Capitalize first letter and check if that type exists
                potential_type_name = field_name[0].upper() + field_name[1:] if field_name else None
                if potential_type_name and hasattr(sgqlc_models, potential_type_name):
                    resolved_type = getattr(sgqlc_models, potential_type_name)
                    if isinstance(resolved_type, type) and issubclass(resolved_type, SGQLCType):
                        type_name = getattr(resolved_type, '__name__', '')
                        is_edge = 'Edge' in type_name
                        if not issubclass(resolved_type, Connection) and not is_edge:
                            return ('object', resolved_type)
        
        # Check for nested object type (must be a Type subclass, not a scalar)
        if isinstance(type_repr, type):
            from sgqlc.types import Type
            # Only treat as object if it's a Type subclass (actual object type)
            # Exclude Connection and Edge types - these are special structures
            # Edge types are generated by our bridge and have "Edge" in their name
            # Scalar types like String, Int, Boolean are not Type subclasses
            type_name = getattr(type_repr, '__name__', '')
            is_edge = 'Edge' in type_name
            if (issubclass(type_repr, Type) and 
                not issubclass(type_repr, Connection) and
                not is_edge):
                return ('object', type_repr)
            else:
                # It's a scalar type, Connection, Edge, or other special type
                return ('scalar', None)
        
        # Scalar or unknown
        return ('scalar', None)
    
    @staticmethod
    def _recursively_select_fields(
        selector, 
        model_class, 
        first: int = 5,
        depth: int = 0,
        max_depth: int = 5,
        visited: Optional[set] = None,
        parent_model: Optional[Type] = None
    ):
        """Recursively select all fields from a model, automatically handling Connections.
        
        Args:
            selector: The sgqlc selector to select fields on
            model_class: The sgqlc Type model class
            first: Pagination limit for Connection fields
            depth: Current recursion depth
            max_depth: Maximum recursion depth to prevent infinite loops
            visited: Set of (model_class, depth) tuples to prevent cycles
            parent_model: Parent model class to detect context (e.g., Order when selecting Customer.orders)
        
        Returns:
            The selector with all fields selected
        """
        if visited is None:
            visited = set()
        
        # Prevent infinite recursion
        if depth >= max_depth:
            return selector
        
        visit_key = (model_class.__name__, depth)
        if visit_key in visited:
            return selector
        visited.add(visit_key)
        
        # Get all fields from the model
        all_fields = [
            attr for attr in dir(model_class)
            if not attr.startswith('_') 
            and not callable(getattr(model_class, attr, None))
        ]
        
        # Categorize fields and store field info to avoid duplicate calls
        field_info = {}  # field_name -> (category, inner_type)
        connection_fields = []
        list_fields = []
        object_fields = []
        regular_fields = []
        
        for field_name in all_fields:
            field_category, inner_type = BaseQuery._get_field_info(model_class, field_name)
            field_info[field_name] = (field_category, inner_type)
            
            if field_category == 'connection':
                connection_fields.append(field_name)
            elif field_category == 'list':
                list_fields.append(field_name)
            elif field_category == 'object':
                object_fields.append(field_name)
            else:
                regular_fields.append(field_name)
        
        # Select regular fields
        if regular_fields:
            selector.__fields__(*regular_fields)  # type: ignore[union-attr]
        
        # Helper to handle recursive field selection
        def _handle_recursive_field(field_name: str, field_sel, inner_type, field_type_label: str, current_parent: Optional[Type] = None):
            """Helper to recursively select fields or fallback to __fields__()."""
            if inner_type and depth < max_depth:
                BaseQuery._recursively_select_fields(
                    field_sel,
                    inner_type,
                    first=first,
                    depth=depth + 1,
                    max_depth=max_depth,
                    visited=visited,
                    parent_model=current_parent
                )
            else:
                field_sel.__fields__()  # type: ignore[union-attr]
        
        # Handle object fields recursively
        for obj_field in object_fields:
            _, obj_type = field_info[obj_field]
            obj_sel = getattr(selector, obj_field)  # type: ignore[union-attr]
            _handle_recursive_field(obj_field, obj_sel, obj_type, "object field", model_class)
        
        # Handle Connection fields recursively
        for conn_field in connection_fields:
            # Special case: Order.lineItems always uses first=1 (only 1 line item per order)
            if model_class.__name__ == 'Order' and conn_field == 'lineItems':
                conn_sel = getattr(selector, conn_field)(first=1)  # type: ignore[union-attr]
            else:
                conn_sel = getattr(selector, conn_field)(first=first)  # type: ignore[union-attr]
            _, node_type = field_info[conn_field]
            
            # Special case: Limit Customer.orders when nested inside Order to prevent circular nesting
            if (model_class.__name__ == 'Customer' and conn_field == 'orders' and 
                parent_model and parent_model.__name__ == 'Order'):
                # Only select minimal fields (id, name) for orders when customer is nested in order
                conn_sel.nodes.id()  # type: ignore[union-attr]
                conn_sel.nodes.name()  # type: ignore[union-attr]
            else:
                _handle_recursive_field(conn_field, conn_sel.nodes, node_type, "Connection nodes", model_class)  # type: ignore[union-attr]
            
            # Always select pageInfo for Connections
            conn_sel.page_info.__fields__('has_next_page', 'has_previous_page', 'start_cursor', 'end_cursor')  # type: ignore[union-attr]
        
        # Handle list fields recursively
        for list_field in list_fields:
            list_sel = getattr(selector, list_field)  # type: ignore[union-attr]
            _, item_type = field_info[list_field]
            _handle_recursive_field(list_field, list_sel, item_type, "list items", model_class)
        
        return selector


class Query(BaseQuery):
    """Query class with customer, order, and product-specific fields and selection helpers.
    
    Extends BaseQuery to provide customer, order, and product-specific functionality.
    This is the root query type used by sgqlc's Operation.
    """
    # Customer-specific field
    customers = Field(CustomerConnection, args=connection_args(query=String))
    
    # Order-specific field
    orders = Field(OrderConnection, args=connection_args(query=String))
    
    # Product-specific field
    products = Field(ProductConnection, args=connection_args(query=String))
    
    # Node query for fetching any node by ID (used for CalculatedOrder, etc.)
    node = Field('Node', args={'id': ID})
    
    # Extract Customer model from CustomerConnection automatically (no import needed)
    @classmethod
    def _get_customer_model(cls):
        """Extract Customer model from CustomerConnection without importing."""
        # Extract node type from Connection class name (CustomerConnection -> Customer)
        node_name = CustomerConnection.__name__.replace('Connection', '')
        if hasattr(sgqlc_models, node_name):
            return getattr(sgqlc_models, node_name)
        return None
    
    # Extract Order model from OrderConnection automatically (no import needed)
    @classmethod
    def _get_order_model(cls):
        """Extract Order model from OrderConnection without importing."""
        # Extract node type from Connection class name (OrderConnection -> Order)
        node_name = OrderConnection.__name__.replace('Connection', '')
        if hasattr(sgqlc_models, node_name):
            return getattr(sgqlc_models, node_name)
        return None
    
    # Extract Product model from ProductConnection automatically (no import needed)
    @classmethod
    def _get_product_model(cls):
        """Extract Product model from ProductConnection without importing."""
        # Extract node type from Connection class name (ProductConnection -> Product)
        node_name = ProductConnection.__name__.replace('Connection', '')
        if hasattr(sgqlc_models, node_name):
            return getattr(sgqlc_models, node_name)
        return None
    
    @staticmethod
    def get_customer_connection(customers_connection_selector, orders_first: int = 5):
        """Automatically select all fields for customers connection using recursive helper.
        
        This uses the recursive helper to automatically handle:
        - All customer node fields (including nested defaultAddress fields)
        - All Connection fields with automatic pagination (orders, etc.)
        - All nested Connection fields recursively
        - All pageInfo fields for pagination
        
        Args:
            customers_connection_selector: The customers selection from operation
            orders_first: Number of items to fetch for Connection fields (default: 5)
        """
        # Extract Customer from CustomerConnection (no import needed)
        Customer = Query._get_customer_model()
        if not Customer:
            raise ValueError("Could not extract Customer model from CustomerConnection")
        
        node_sel = customers_connection_selector.nodes  # type: ignore[union-attr]
        
        # Use recursive helper to automatically select all fields
        BaseQuery._recursively_select_fields(
            node_sel,
            Customer,
            first=orders_first,
            depth=0,
            max_depth=5,
            visited=None
        )
        
        # Select pageInfo for customers connection
        customers_connection_selector.page_info.__fields__('has_next_page', 'has_previous_page', 'start_cursor', 'end_cursor')  # type: ignore[union-attr]
    
    @staticmethod
    def get_order_connection(orders_connection_selector, line_items_first: int = 5):
        """Automatically select all fields for orders connection using recursive helper.
        
        This uses the recursive helper to automatically handle:
        - All order node fields
        - All Connection fields with automatic pagination (lineItems, etc.)
        - All nested Connection fields recursively
        - All pageInfo fields for pagination
        
        Args:
            orders_connection_selector: The orders selection from operation
            line_items_first: Number of items to fetch for Connection fields (default: 5)
        """
        # Extract Order from OrderConnection (no import needed)
        Order = Query._get_order_model()
        if not Order:
            raise ValueError("Could not extract Order model from OrderConnection")
        
        node_sel = orders_connection_selector.nodes  # type: ignore[union-attr]
        
        # Use recursive helper to automatically select all fields
        BaseQuery._recursively_select_fields(
            node_sel,
            Order,
            first=line_items_first,
            depth=0,
            max_depth=5,
            visited=None
        )
        
        # Select pageInfo for orders connection
        orders_connection_selector.page_info.__fields__('has_next_page', 'has_previous_page', 'start_cursor', 'end_cursor')  # type: ignore[union-attr]
    
    @classmethod
    def build_customer_query(
        cls,
        query_str: str,
        first: int = 1,
        orders_first: int = 5
    ) -> Operation:
        """Build a customer query operation.
        
        This is a domain-specific query builder that creates a fully-configured
        Operation for querying customers. The operation can then be executed
        by a generic client.
        
        Args:
            query_str: GraphQL query string (e.g., "email:test@example.com", "id:123")
            first: Number of customers to fetch (default: 1)
            orders_first: Number of orders to fetch per customer (default: 5)
        
        Returns:
            Configured sgqlc Operation ready for execution
        """
        op = Operation(cls)
        customers_connection_selector = op.customers(query=query_str, first=first)
        cls.get_customer_connection(customers_connection_selector, orders_first=orders_first)
        return op
    
    @classmethod
    def build_order_query(
        cls,
        query_str: str,
        first: int = 1,
        line_items_first: int = 5
    ) -> Operation:
        """Build an order query operation.
        
        This is a domain-specific query builder that creates a fully-configured
        Operation for querying orders. The operation can then be executed
        by a generic client.
        
        Args:
            query_str: GraphQL query string (e.g., "name:#1234", "email:test@example.com")
            first: Number of orders to fetch (default: 1)
            line_items_first: Number of line items to fetch per order (default: 5)
        
        Returns:
            Configured sgqlc Operation ready for execution
        """
        op = Operation(cls)
        orders_connection_selector = op.orders(query=query_str, first=first)
        cls.get_order_connection(orders_connection_selector, line_items_first=line_items_first)
        return op
    
    @staticmethod
    def get_product_connection(products_connection_selector, variants_first: int = 5):
        """Automatically select all fields for products connection using recursive helper.
        
        This uses the recursive helper to automatically handle:
        - All product node fields
        - All Connection fields with automatic pagination (variants, etc.)
        - All nested Connection fields recursively
        - All pageInfo fields for pagination
        
        Args:
            products_connection_selector: The products selection from operation
            variants_first: Number of items to fetch for Connection fields (default: 5)
        """
        # Extract Product from ProductConnection (no import needed)
        Product = Query._get_product_model()
        if not Product:
            raise ValueError("Could not extract Product model from ProductConnection")
        
        node_sel = products_connection_selector.nodes  # type: ignore[union-attr]
        
        # Use recursive helper to automatically select all fields
        BaseQuery._recursively_select_fields(
            node_sel,
            Product,
            first=variants_first,
            depth=0,
            max_depth=5,
            visited=None
        )
        
        # Select pageInfo for products connection
        products_connection_selector.page_info.__fields__('has_next_page', 'has_previous_page', 'start_cursor', 'end_cursor')  # type: ignore[union-attr]
    
    @classmethod
    def build_product_query(
        cls,
        query_str: str,
        first: int = 1,
        variants_first: int = 5
    ) -> Operation:
        """Build a product query operation.
        
        This is a domain-specific query builder that creates a fully-configured
        Operation for querying products. The operation can then be executed
        by a generic client.
        
        Args:
            query_str: GraphQL query string (e.g., "id:123", "handle:product-handle")
            first: Number of products to fetch (default: 1)
            variants_first: Number of variants to fetch per product (default: 5)
        
        Returns:
            Configured sgqlc Operation ready for execution
        """
        op = Operation(cls)
        products_connection_selector = op.products(query=query_str, first=first)
        cls.get_product_connection(products_connection_selector, variants_first=variants_first)
        return op
    
    @classmethod
    def build_variant_query(cls, variant_id: str) -> Operation:
        """Build a query to get a single product variant."""
        from backend.modules.integrations.shopify.models.sgqlc_models.product_sgqlc import ProductVariant
        from sgqlc.types import ID
        
        class VariantQuery(Type):
            productVariant = Field(ProductVariant, args={'id': ID})
        
        op = Operation(VariantQuery)
        variant_sel = op.productVariant(id=variant_id)
        variant_sel.id()  # type: ignore[union-attr]
        variant_sel.product.id()  # type: ignore[union-attr]
        variant_sel.product.title()  # type: ignore[union-attr]
        return op
    
    @classmethod
    def build_location_query(cls, first: int = 1) -> Operation:
        """Build a query to get locations."""
        from backend.modules.integrations.shopify.models.sgqlc_models.location_sgqlc import LocationConnection
        from sgqlc.types.relay import connection_args
        
        class LocationQuery(Type):
            locations = Field(LocationConnection, args=connection_args())
        
        op = Operation(LocationQuery)
        locations_sel = op.locations(first=first)
        locations_sel.nodes.id()  # type: ignore[union-attr]
        locations_sel.nodes.name()  # type: ignore[union-attr]
        return op

