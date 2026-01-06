"""
SGQLC Query classes for Shopify GraphQL API.

Provides BaseQuery with generic field selection helpers and Query with
customer and order-specific fields and helpers.
"""

from typing import Optional
from sgqlc.types import Type, Field, String
from sgqlc.types.relay import connection_args
from sgqlc.operation import Operation

from models.sgqlc_models import CustomerConnection, OrderConnection


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
        from models import sgqlc_models
        import re
        
        field = getattr(model_class, field_name, None)
        if not field:
            return (None, None)
        
        # Get the type representation
        type_repr = None
        if isinstance(field, Field):
            if hasattr(field, 'type'):
                type_repr = field.type
        
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
        
        # Check for nested object type (must be a Type subclass, not a scalar)
        if isinstance(type_repr, type):
            from sgqlc.types import Type
            # Only treat as object if it's a Type subclass (actual object type)
            # Scalar types like String, Int, Boolean are not Type subclasses
            if issubclass(type_repr, Type) and not issubclass(type_repr, Connection):
                return ('object', type_repr)
            else:
                # It's a scalar type (String, Int, Boolean, etc.)
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
    """Query class with customer and order-specific fields and selection helpers.
    
    Extends BaseQuery to provide customer and order-specific functionality.
    This is the root query type used by sgqlc's Operation.
    """
    # Customer-specific field
    customers = Field(CustomerConnection, args=connection_args(query=String))
    
    # Order-specific field
    orders = Field(OrderConnection, args=connection_args(query=String))
    
    # Extract Customer model from CustomerConnection automatically (no import needed)
    @classmethod
    def _get_customer_model(cls):
        """Extract Customer model from CustomerConnection without importing."""
        from models import sgqlc_models
        # Extract node type from Connection class name (CustomerConnection -> Customer)
        node_name = CustomerConnection.__name__.replace('Connection', '')
        if hasattr(sgqlc_models, node_name):
            return getattr(sgqlc_models, node_name)
        return None
    
    # Extract Order model from OrderConnection automatically (no import needed)
    @classmethod
    def _get_order_model(cls):
        """Extract Order model from OrderConnection without importing."""
        from models import sgqlc_models
        # Extract node type from Connection class name (OrderConnection -> Order)
        node_name = OrderConnection.__name__.replace('Connection', '')
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

