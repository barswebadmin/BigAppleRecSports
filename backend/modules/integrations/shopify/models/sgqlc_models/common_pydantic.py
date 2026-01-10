"""
Common models shared across Shopify entities.
"""

import inspect
import json
from typing import Optional, TypeVar, Generic, Dict, Any, Type, Union, ClassVar
from pydantic import BaseModel, Field, PrivateAttr

# Generic type variable for connection nodes
T = TypeVar('T', bound=BaseModel)


class PageInfo(BaseModel):
    """Information about a single page of a paginated connection."""
    has_next_page: bool = Field(alias="hasNextPage")
    has_previous_page: bool = Field(alias="hasPreviousPage")
    start_cursor: Optional[str] = Field(None, alias="startCursor")
    end_cursor: Optional[str] = Field(None, alias="endCursor")


class Edge(BaseModel, Generic[T]):
    """An edge type for pagination.
    
    An edge type is used to represent a single item within a paginated connection,
    and contains the node itself as well as the cursor for that node.
    """
    node: T
    cursor: str


class Connection(BaseModel, Generic[T]):
    """A connection type for pagination.
    
    This class is used to represent a connection type for pagination in a GraphQL API.
    Supports both 'edges' and 'nodes' structures (Shopify supports both).
    """
    edges: Optional[list[Edge[T]]] = None
    nodes: Optional[list[T]] = None  # Direct nodes (simplified, skipping edges)
    page_info: PageInfo = Field(alias="pageInfo")


class ShopifylistModel(list):
    """Base for list of Shopify model instances."""
    
    def __init__(self, data: Union[list[Dict], Dict[str, Any]], model_type: Type["ShopifyBaseModel"]):
        """
        Instantiate list from raw data.
        
        Handles:
        - list of dicts: Direct list of node dicts
        - Connection dict: Dict with "nodes" or "edges" key (GraphQL Connection structure)
        
        Args:
            data: list of dicts OR Connection structure (dict with "nodes" or "edges" key)
            model_type: The singular model class (e.g., Customer)
        """
        # Check if data is a Connection structure (dict with "nodes" or "edges" key)
        if isinstance(data, dict) and ("nodes" in data or "edges" in data):
            # Resolve Connection structure to list of nodes
            connection = Connection(**data)
            
            # Prefer nodes if available (simplified), otherwise extract from edges
            if connection.nodes:
                nodes = connection.nodes
            elif connection.edges:
                nodes = [edge.node for edge in connection.edges]  # Extract nodes from edges
            else:
                nodes = []
            
            items = ShopifyBaseModel._resolve_list_items(nodes, model_type)
            
            # Warn about pagination if needed
            if connection.page_info and connection.page_info.has_next_page:
                model_name = model_type.__name__
                cursor = connection.page_info.end_cursor or "N/A"
                print(f"⚠️  Warning: More {model_name} results available. Use cursor '{cursor}' to fetch next page.")
        elif isinstance(data, list):
            # Direct list of dicts
            items = ShopifyBaseModel._resolve_list_items(data, model_type)
        else:
            # Invalid data type
            items = []
        
        super().__init__(items)
        self._model_type = model_type
    
    def __repr__(self):
        return f"{self._model_type.__name__}s({len(self)} items)"


class ShopifyBaseModel(BaseModel):
    """Base model for Shopify entities."""
    
    # Subclasses should set this to declare their list fields (field name -> target type name)
    # Use string forward references: {"refunds": "Refund"}
    list_fields: ClassVar[Dict[str, str]] = {}
    
    # Store raw response data (excluded from serialization)
    _raw_data: Dict[str, Any] = PrivateAttr(default_factory=dict)
    
    def __init__(self, **data):
        """Initialize model and store raw data with error handling."""
        try:
            super().__init__(**data)
            # Store raw data in private attribute
            self._raw_data = data
        except Exception as e:
            # Print raw data for troubleshooting
            try:
                raw_json = json.dumps(data, indent=2, default=str)
                error_msg = f"Failed to instantiate {self.__class__.__name__}: {str(e)}\n\nRaw data:\n{raw_json}"
                print(f"⚠️  {error_msg}")
            except Exception:
                # Fallback if JSON serialization fails
                error_msg = f"Failed to instantiate {self.__class__.__name__}: {str(e)}\n\nRaw data: {data}"
                print(f"⚠️  {error_msg}")
            # Re-raise original exception (Pydantic ValidationError can't be easily recreated)
            raise
    
    @property
    def raw_data(self) -> Dict[str, Any]:
        """Access original raw response data before resolution."""
        return self._raw_data
    
    def model_post_init(self, __context):
        """Auto-resolve lists after Pydantic initialization."""
        self.resolve_list()
    
    @classmethod
    def _get_target_type(cls, type_name: str) -> Optional[Type[BaseModel]]:
        """Resolve type name to actual model class using models namespace."""
        try:
            # Import models module (already has all types resolved via model_rebuild)
            import sys
            if 'models' in sys.modules:
                models_module = sys.modules['models']
                if hasattr(models_module, type_name):
                    target_type = getattr(models_module, type_name)
                    if isinstance(target_type, type) and issubclass(target_type, BaseModel):
                        return target_type
            return None
        except (TypeError, AttributeError, KeyError, ImportError):
            return None
    
    @staticmethod
    def _resolve_list_items(items: list[Any], target_type: Type[BaseModel]) -> list[BaseModel]:
        """
        Core logic to parse list of dicts into list of model instances.
        
        Handles:
        - Empty lists → empty list
        - Already-parsed model instances → pass through
        - Dict items → parse into model instances
        - Invalid items → skip with continue (prints raw data for troubleshooting)
        
        Args:
            items: list of items (dicts, model instances, or mixed)
            target_type: Pydantic model class to parse dicts into
            
        Returns:
            list of parsed model instances
        """
        if not items:
            return []
        
        resolved = []
        for item in items:
            # Already a model instance? Pass through
            if isinstance(item, target_type):
                resolved.append(item)
            # Dict? Parse it
            elif isinstance(item, dict):
                try:
                    resolved.append(target_type(**item))
                except Exception as e:
                    # Print raw data for troubleshooting
                    try:
                        raw_json = json.dumps(item, indent=2)
                        print(f"⚠️  Failed to instantiate {target_type.__name__}: {str(e)}")
                        print(f"   Raw data:\n{raw_json}")
                    except Exception:
                        # Fallback if JSON serialization fails
                        print(f"⚠️  Failed to instantiate {target_type.__name__}: {str(e)}")
                        print(f"   Raw data: {item}")
                    # Skip invalid items
                    continue
            # Something else? Skip
            else:
                continue
        
        return resolved
    
    
    def resolve_list(self) -> "ShopifyBaseModel":
        """
        Resolve all list[Type] fields declared in list_fields class attribute.
        
        Subclasses should set list_fields as a dict mapping field names to target type names.
        The target type is extracted from the field's type annotation (e.g., list["Refund"]).
        
        Example:
            class Order(ShopifyBaseModel):
                refunds: Optional[list[Refund]] = ...
                list_fields = {"refunds": "Refund"}  # Field name -> type name
        """
        list_fields = getattr(self.__class__, 'list_fields', {})
        if not list_fields:
            return self
        
        # Resolve type names to actual model classes using models namespace
        for field_name, type_name in list_fields.items():
            target_type = self.__class__._get_target_type(type_name)
            if not target_type:
                continue
            
            field_value = getattr(self, field_name, None)
            if isinstance(field_value, list):
                resolved = self._resolve_list_items(field_value, target_type)
                # Each resolved item will have its own model_post_init called,
                # which will trigger its own resolve_connections() and resolve_list() automatically
                setattr(self, field_name, resolved)
        
        return self


def create_list_model(singular_class):
    """
    Decorator that auto-creates and exports list class for Shopify models.
    
    Usage:
        @create_list_model
        class Customer(ShopifyBaseModel):
            pass
        
        # Customers is automatically available!
        customers = Customers(response.data)
        # Or from Connection:
        connection = result.get_connection("customers")
        customers = Customers.from_connection(connection)
    """
    list_name = f"{singular_class.__name__}s"
    
    class listClass(ShopifylistModel):
        def __init__(self, data: Union[list[Dict[str, Any]], Dict[str, Any]]):
            super().__init__(data, singular_class)
        
        @classmethod
        def from_connection(cls, connection_dict: Optional[Dict[str, Any]]) -> "listClass":
            """
            Create list from Connection dict.
            
            This is the preferred way to instantiate list models from GraphQL Connections,
            as it provides clear separation between GraphQL structure (Connection) and
            model instantiation.
            
            Args:
                connection_dict: Connection dict with 'edges' and 'pageInfo' keys
                
            Returns:
                listClass instance with resolved model instances
                
            Example:
                connection = result.get_connection("customers")
                customers = Customers.from_connection(connection)
            """
            if not connection_dict or not isinstance(connection_dict, dict):
                return cls([])
            
            connection = Connection(**connection_dict)
            # Prefer nodes if available (simplified), otherwise extract from edges
            if connection.nodes:
                nodes = [n for n in connection.nodes if isinstance(n, dict)]
            elif connection.edges:
                nodes = [edge.node for edge in connection.edges if isinstance(edge.node, dict)]
            else:
                nodes = []
            
            # Warn about pagination if needed
            if connection.page_info and connection.page_info.has_next_page:
                model_name = singular_class.__name__
                cursor = connection.page_info.end_cursor or "N/A"
                print(f"⚠️  Warning: More {model_name} results available. Use cursor '{cursor}' to fetch next page.")
            
            # Resolve nodes to model instances
            resolved = ShopifyBaseModel._resolve_list_items(nodes, singular_class)
            # Create instance with empty list, then extend with resolved items
            instance = cls([])
            instance.extend(resolved)
            return instance
    
    listClass.__name__ = list_name
    singular_class.list = listClass
    
    # Auto-export to calling module
    caller_frame = inspect.stack()[1].frame
    caller_frame.f_globals[list_name] = listClass
    
    return singular_class


class ShopifyResponse(BaseModel, Generic[T]):
    """Generic type-safe response wrapper with pagination support."""
    success: bool
    message: str
    data: Union[Dict[str, Any], list[Dict[str, Any]]] = Field(default_factory=list)
    page_info: Optional[PageInfo] = Field(default=None, alias="pageInfo")
    errors: Optional[list[Dict[str, Any]]] = None
    
    def get_connection(self, field_name: str) -> Optional[Dict[str, Any]]:
        """
        Extract a Connection structure from GraphQL response data.
        
        GraphQL responses wrap Connections in field names:
            {"customers": {nodes: [...], pageInfo: {...}}}
            or
            {"customers": {edges: [...], pageInfo: {...}}}
        
        This method extracts the Connection dict for a given field name.
        
        Args:
            field_name: The GraphQL field name (e.g., "customers", "orders")
            
        Returns:
            Connection dict with 'nodes'/'edges' and 'pageInfo', or None if not found
        """
        if not isinstance(self.data, dict):
            return None
        connection = self.data.get(field_name)
        if isinstance(connection, dict) and ("nodes" in connection or "edges" in connection):
            return connection
        return None
    
    @property
    def first(self) -> Optional[Union[Dict[str, Any], T]]:
        """Get first item if available (convenience property)."""
        if isinstance(self.data, list):
            return self.data[0] if self.data else None
        return self.data if self.data else None
    
    @property
    def has_next_page(self) -> bool:
        """Check if there are more pages available."""
        return self.page_info.has_next_page if self.page_info else False
    
    @property
    def end_cursor(self) -> Optional[str]:
        """Get cursor for next page."""
        return self.page_info.end_cursor if self.page_info else None


# DEPRECATED: create_query_model() is no longer needed.
# We now use sgqlc for query generation (see models/sgqlc_bridge.py),
# which handles Connection types natively without workarounds.

