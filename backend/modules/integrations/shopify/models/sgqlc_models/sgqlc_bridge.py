"""
Bridge between Pydantic models and sgqlc types for query generation.

This module provides utilities to automatically generate sgqlc Type definitions
from Pydantic models, allowing us to use sgqlc for query generation (with native
Connection support) while keeping Pydantic for validation.

The key benefit: No more create_query_model() workaround! sgqlc handles Connections natively.
"""

import re
import sys
from typing import Type, Dict, Any, Optional, List, get_origin, get_args
from pydantic import BaseModel
from sgqlc.types import Type as SGQLCType, Field, list_of, map_python_to_graphql
from sgqlc.types.relay import Connection as SGQLCConnection, connection_args
from backend.modules.integrations.shopify.models.sgqlc_models.common_pydantic import Connection as PydanticConnection

# Cache for generated sgqlc types
_sgqlc_type_cache: Dict[Type[BaseModel], Type[SGQLCType]] = {}
# Cache for generated Connection types
_connection_type_cache: Dict[str, Type[SGQLCConnection]] = {}


# ============================================================================
# Type Detection Helpers
# ============================================================================

def _is_optional(annotation: Any) -> bool:
    """Check if annotation is Optional[T] or Union[T, None]."""
    origin = get_origin(annotation)
    if origin is None:
        return False
    args = get_args(annotation)
    return len(args) == 2 and type(None) in args


def _is_connection(annotation: Any) -> bool:
    """Check if annotation is Connection[T].
    
    Tries type introspection first (more reliable), falls back to string check
    for forward references.
    """
    # Try to detect via origin first (more reliable)
    origin = get_origin(annotation)
    if origin is not None:
        args = get_args(annotation)
        return any(
            isinstance(arg, type) and issubclass(arg, PydanticConnection)
            for arg in args
        )
    # Fallback to string check for forward references
    return 'Connection[' in str(annotation)


def _is_list(annotation: Any) -> bool:
    """Check if annotation is list[T]."""
    return get_origin(annotation) is list


def _is_pydantic_model(annotation: Any) -> bool:
    """Check if annotation is a Pydantic BaseModel."""
    return isinstance(annotation, type) and issubclass(annotation, BaseModel)


# ============================================================================
# Type Resolution Helpers
# ============================================================================

def _resolve_type_name(type_name: str) -> Optional[Type[BaseModel]]:
    """Resolve a type name string to an actual BaseModel class using models namespace."""
    try:
        # Try sgqlc_models module first (where our Pydantic models are)
        from backend.modules.integrations.shopify.models import sgqlc_models
        # Check product_pydantic, customer_pydantic, etc. for the model
        for module_name in ['product_pydantic', 'customer_pydantic', 'order_pydantic', 'common_pydantic']:
            try:
                module = getattr(sgqlc_models, module_name, None)
                if module and hasattr(module, type_name):
                    target_type = getattr(module, type_name)
                    if isinstance(target_type, type) and issubclass(target_type, BaseModel):
                        return target_type
            except (AttributeError, TypeError):
                continue
        
        # Fallback to generic models module
        if 'models' in sys.modules:
            models_module = sys.modules['models']
            if hasattr(models_module, type_name):
                target_type = getattr(models_module, type_name)
                if isinstance(target_type, type) and issubclass(target_type, BaseModel):
                    return target_type
        return None
    except (TypeError, AttributeError, KeyError, ImportError):
        return None


def _extract_connection_inner_type(annotation: Any) -> Optional[Type[BaseModel]]:
    """Extract the inner type from Connection[T] annotation.
    
    Handles both resolved and string annotations. Tries type introspection first
    (more reliable), falls back to string parsing for forward references.
    """
    # Try type introspection first (more reliable)
    origin = get_origin(annotation)
    if origin is not None:
        args = get_args(annotation)
        # Check if origin itself is Connection (e.g., Connection[Collection])
        if origin is PydanticConnection:
            if args and len(args) > 0:
                inner = args[0]
                if isinstance(inner, type) and issubclass(inner, BaseModel):
                    return inner
        
        # Look for Connection in args (e.g., Optional[Connection[Collection]])
        for arg in args:
            # Check if arg is a generic Connection type
            arg_origin = get_origin(arg) if arg is not None else None
            if arg_origin is PydanticConnection:
                arg_args = get_args(arg)
                if arg_args and len(arg_args) > 0:
                    inner = arg_args[0]
                    if isinstance(inner, type) and issubclass(inner, BaseModel):
                        return inner
            
            # Check if arg is a concrete Connection class (Pydantic creates concrete classes)
            # For Pydantic models, check string representation to extract inner type
            if arg is not None:
                arg_str = str(arg)
                if 'Connection[' in arg_str:
                    match = re.search(r'Connection\[([^\]]+)\]', arg_str)
                    if match:
                        inner_type_str = match.group(1).strip().split('.')[-1]
                        # Try to resolve from product_pydantic module directly
                        try:
                            from backend.modules.integrations.shopify.models.sgqlc_models import product_pydantic
                            if hasattr(product_pydantic, inner_type_str):
                                resolved = getattr(product_pydantic, inner_type_str)
                                if isinstance(resolved, type) and issubclass(resolved, BaseModel):
                                    return resolved
                        except (ImportError, AttributeError, TypeError):
                            pass
                        # Fallback to _resolve_type_name
                        resolved = _resolve_type_name(inner_type_str)
                        if resolved:
                            return resolved
            
            # Fallback: check if arg is a Connection class instance
            if isinstance(arg, type) and issubclass(arg, PydanticConnection):
                # Try to extract from Connection's __args__
                # Type ignore: __args__ is a typing attribute that exists at runtime
                if hasattr(arg, '__args__'):
                    inner_args = getattr(arg, '__args__', None)  # type: ignore[attr-defined]
                    if inner_args and len(inner_args) > 0:
                        inner = inner_args[0]
                        if isinstance(inner, type) and issubclass(inner, BaseModel):
                            return inner
    
    # Fallback to string parsing for forward references
    annotation_str = str(annotation)
    match = re.search(r'Connection\[([^\]]+)\]', annotation_str)
    if match:
        inner_type_str = match.group(1).strip().split('.')[-1]
        return _resolve_type_name(inner_type_str)
    
    return None


# ============================================================================
# Connection Type Creation
# ============================================================================

def _create_connection_type(inner_pydantic_type: Type[BaseModel]) -> Type[SGQLCConnection]:
    """Create or retrieve cached Connection type for a Pydantic model.
    
    Args:
        inner_pydantic_type: The Pydantic model class that will be the node type
        
    Returns:
        An sgqlc Connection type class (e.g., CustomerConnection)
    """
    connection_name = f"{inner_pydantic_type.__name__}Connection"
    
    if connection_name in _connection_type_cache:
        return _connection_type_cache[connection_name]
    
    inner_sgqlc_type = get_sgqlc_type(inner_pydantic_type)
    connection_class = type(connection_name, (SGQLCConnection,), {
        'nodes': list_of(inner_sgqlc_type)
    })
    _connection_type_cache[connection_name] = connection_class
    return connection_class


def get_connection_type(pydantic_model: Type[BaseModel]) -> Type[SGQLCConnection]:
    """Get or generate sgqlc Connection type for a Pydantic model.
    
    Args:
        pydantic_model: The Pydantic model class
        
    Returns:
        An sgqlc Connection type class (e.g., CustomerConnection)
    """
    return _create_connection_type(pydantic_model)


# ============================================================================
# Type Conversion Handlers
# ============================================================================

def _convert_optional(annotation: Any, seen: set) -> Any:
    """Convert Optional[T] to sgqlc type.
    
    Handles Optional[Connection[T]] specially by creating Connection types.
    """
    args = get_args(annotation)
    non_none_type = next(a for a in args if a is not type(None))
    
    # Check if Optional wraps a Connection
    annotation_str = str(annotation)
    if 'Connection[' in annotation_str:
        inner_type = _extract_connection_inner_type(annotation)
        if inner_type and inner_type not in seen:
            connection_class = _create_connection_type(inner_type)
            return Field(connection_class, args=connection_args())
    
    # Regular Optional - unwrap and convert
    return _pydantic_to_sgqlc_type(non_none_type, seen=seen)


def _convert_connection(annotation: Any, seen: set) -> Optional[Any]:
    """Convert Connection[T] to sgqlc Field with connection_args.
    
    Returns None if inner type cannot be extracted or is already in seen set.
    """
    inner_type = _extract_connection_inner_type(annotation)
    if not inner_type or inner_type in seen:
        return None
    
    connection_class = _create_connection_type(inner_type)
    return Field(connection_class, args=connection_args())


def _convert_list(annotation: Any, seen: set) -> Any:
    """Convert list[T] to sgqlc list_of.
    
    Returns list_of(str) as default if no inner type specified.
    """
    args = get_args(annotation)
    if not args:
        return list_of(str)
    
    inner_type = _pydantic_to_sgqlc_type(args[0], seen=seen)
    return list_of(inner_type) if inner_type else None


def _convert_union(annotation: Any, seen: set) -> Any:
    """Convert Union[T1, T2, ...] to sgqlc type.
    
    Simplified: uses first non-None type.
    """
    args = get_args(annotation)
    if not args:
        return str
    
    # Skip None types
    non_none_args = [a for a in args if a is not type(None)]
    if non_none_args:
        return _pydantic_to_sgqlc_type(non_none_args[0], seen=seen)
    
    return str


# ============================================================================
# Main Type Conversion Function
# ============================================================================

def _pydantic_to_sgqlc_type(annotation: Any, seen: Optional[set] = None, **kwargs) -> Any:
    """Convert Pydantic type annotation to sgqlc type.
    
    This is the main dispatcher that routes to appropriate handlers based on
    the annotation type.
    
    Args:
        annotation: The type annotation to convert
        seen: Set of seen annotations to prevent infinite recursion
        **kwargs: Unused, kept for backward compatibility
        
    Returns:
        An sgqlc type (Field, list_of, or scalar type)
    """
    if seen is None:
        seen = set()
    
    # Prevent infinite recursion
    annotation_id = id(annotation)
    if annotation_id in seen:
        return str  # Default fallback to break cycle
    seen.add(annotation_id)
    
    try:
        # Early returns for simple cases
        if annotation is None:
            return str
        
        # Handle Optional (Union with None)
        if _is_optional(annotation):
            return _convert_optional(annotation, seen)
        
        # Handle Connection (direct, not wrapped in Optional)
        if _is_connection(annotation):
            result = _convert_connection(annotation, seen)
            if result:
                return result
        
        # Handle List
        if _is_list(annotation):
            return _convert_list(annotation, seen)
        
        # Handle Union (non-Optional)
        origin = get_origin(annotation)
        if origin is not None and origin is not list:
            return _convert_union(annotation, seen)
        
        # Handle basic Python types using sgqlc's map_python_to_graphql
        if annotation in map_python_to_graphql:
            return map_python_to_graphql[annotation]
        
        # Handle Pydantic models
        if _is_pydantic_model(annotation):
            return get_sgqlc_type(annotation)
        
        # Handle string forward references
        if isinstance(annotation, str):
            return annotation
        
        # Default to str
        return str
    finally:
        seen.discard(annotation_id)


# ============================================================================
# Public API
# ============================================================================

def get_sgqlc_type(pydantic_model: Type[BaseModel]) -> Type[SGQLCType]:
    """Get or generate sgqlc Type for a Pydantic model.
    
    This creates an sgqlc Type class that mirrors the Pydantic model,
    automatically handling Connection fields by generating Connection types.
    
    Args:
        pydantic_model: The Pydantic model class
        
    Returns:
        An sgqlc Type class that can be used for query generation
    """
    # Check cache first
    if pydantic_model in _sgqlc_type_cache:
        return _sgqlc_type_cache[pydantic_model]
    
    # Create class name
    sgqlc_name = f"{pydantic_model.__name__}SGQLC"
    
    # Build fields dict
    fields = {}
    for field_name, field_info in pydantic_model.model_fields.items():
        annotation = field_info.annotation
        
        # Convert annotation to sgqlc type
        sgqlc_type = _pydantic_to_sgqlc_type(annotation)
        
        # Skip if None (shouldn't happen now, but keep for safety)
        if sgqlc_type is None:
            continue
        
        # Add field
        fields[field_name] = sgqlc_type
    
    # Create the sgqlc Type class
    sgqlc_class = type(sgqlc_name, (SGQLCType,), fields)
    
    # Cache it
    _sgqlc_type_cache[pydantic_model] = sgqlc_class
    
    return sgqlc_class


def to_pydantic(sgqlc_instance: SGQLCType, pydantic_model: Type[BaseModel]) -> BaseModel:
    """Convert sgqlc Type instance to Pydantic model.
    
    This function extracts the raw JSON data from an sgqlc Type instance
    and validates it into a Pydantic model.
    
    Args:
        sgqlc_instance: An sgqlc Type instance (from op + data pattern)
        pydantic_model: The Pydantic model class to convert to
        
    Returns:
        A validated Pydantic model instance
        
    Example:
        >>> customer_sgqlc = query_result.customers.nodes[0]
        >>> customer = to_pydantic(customer_sgqlc, Customer)
    """
    if not hasattr(sgqlc_instance, '__json_data__'):
        raise ValueError(
            f"sgqlc instance {type(sgqlc_instance)} does not have __json_data__ attribute. "
            "Make sure you're using the (op + data) pattern to get typed instances."
        )
    
    # __json_data__ is a runtime attribute added by sgqlc, not a class attribute
    json_data = getattr(sgqlc_instance, '__json_data__')  # type: ignore[attr-defined]
    return pydantic_model.model_validate(json_data)


def to_pydantic_list(
    sgqlc_instances: List[SGQLCType],
    pydantic_model: Type[BaseModel]
) -> List[BaseModel]:
    """Convert a list of sgqlc Type instances to Pydantic models.
    
    Args:
        sgqlc_instances: List of sgqlc Type instances
        pydantic_model: The Pydantic model class to convert to
        
    Returns:
        List of validated Pydantic model instances
    """
    return [to_pydantic(instance, pydantic_model) for instance in sgqlc_instances]
