"""
Bridge between Pydantic models and sgqlc types for query generation.

This module provides utilities to automatically generate sgqlc Type definitions
from Pydantic models, allowing us to use sgqlc for query generation (with native
Connection support) while keeping Pydantic for validation.

The key benefit: No more create_query_model() workaround! sgqlc handles Connections natively.
"""

import re
import sys
from typing import Type, Dict, Any, Optional, get_origin, get_args
from pydantic import BaseModel
from sgqlc.types import Type as SGQLCType, Field, list_of, map_python_to_graphql
from sgqlc.types.relay import Connection as SGQLCConnection, connection_args
from .common import Connection as PydanticConnection

# Cache for generated sgqlc types
_sgqlc_type_cache: Dict[Type[BaseModel], Type[SGQLCType]] = {}
# Cache for generated Connection types
_connection_type_cache: Dict[str, Type[SGQLCConnection]] = {}


def _resolve_type_name(type_name: str) -> Optional[Type[BaseModel]]:
    """Resolve a type name string to an actual BaseModel class using models namespace."""
    try:
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
    
    Handles both resolved and string annotations.
    """
    annotation_str = str(annotation)
    
    # Try to extract Connection[TypeName] from string representation
    match = re.search(r'Connection\[([^\]]+)\]', annotation_str)
    if match:
        inner_type_str = match.group(1).strip()
        # Remove module prefix if present (e.g., "models.order.DiscountApplication" -> "DiscountApplication")
        if '.' in inner_type_str:
            inner_type_str = inner_type_str.split('.')[-1]
        
        # Resolve using models namespace
        resolved_type = _resolve_type_name(inner_type_str)
        if resolved_type:
            return resolved_type
    
    # Fallback: Check if annotation is already a resolved Connection type
    # and try to extract from args
    origin = get_origin(annotation)
    args = get_args(annotation)
    
    # Handle Optional[Connection[T]]
    if origin is not None:
        for arg in args:
            if isinstance(arg, type) and issubclass(arg, PydanticConnection):
                # This is Connection[T], try to get T from string representation
                arg_str = str(arg)
                match = re.search(r'Connection\[([^\]]+)\]', arg_str)
                if match:
                    inner_type_str = match.group(1).strip()
                    if '.' in inner_type_str:
                        inner_type_str = inner_type_str.split('.')[-1]
                    return _resolve_type_name(inner_type_str)
    
    return None


def _pydantic_to_sgqlc_type(annotation: Any, pydantic_model: Optional[Type[BaseModel]] = None, _seen: Optional[set] = None) -> Any:
    """Convert Pydantic type annotation to sgqlc type.
    
    Args:
        annotation: The type annotation to convert
        pydantic_model: The Pydantic model this annotation belongs to (for context)
        _seen: Set of seen annotations to prevent infinite recursion
    """
    if _seen is None:
        _seen = set()
    
    # Prevent infinite recursion
    annotation_id = id(annotation)
    if annotation_id in _seen:
        return str  # Default fallback to break cycle
    _seen.add(annotation_id)
    
    try:
        if annotation is None:
            return str  # Default
        
        origin = get_origin(annotation)
        
        # Handle Optional/Union (str | None)
        if origin is not None:
            args = get_args(annotation)
            
            # Check if it's Optional (Union with None)
            if len(args) == 2 and type(None) in args:
                # Get the non-None type
                non_none_type = next(a for a in args if a is not type(None))
                
                # Check if non_none_type is a Connection type by checking string representation
                # This avoids issues with resolved generic types
                annotation_str = str(annotation)
                if 'Connection[' in annotation_str:
                    # Extract inner type from Connection[T]
                    inner_type = _extract_connection_inner_type(annotation)
                    if inner_type and inner_type not in _seen:
                        # Generate Connection type automatically
                        inner_sgqlc_type = get_sgqlc_type(inner_type)
                        connection_name = f"{inner_type.__name__}Connection"
                        
                        # Check cache
                        if connection_name in _connection_type_cache:
                            connection_class = _connection_type_cache[connection_name]
                        else:
                            # Create Connection type
                            connection_class = type(connection_name, (SGQLCConnection,), {
                                'nodes': list_of(inner_sgqlc_type)
                            })
                            _connection_type_cache[connection_name] = connection_class
                        
                        # Return Field with connection_args
                        return Field(connection_class, args=connection_args())
                
                return _pydantic_to_sgqlc_type(non_none_type, pydantic_model, _seen)
            
            # Regular Union - use first type (simplified)
            if args:
                return _pydantic_to_sgqlc_type(args[0], pydantic_model, _seen)
        
        # Handle Connection types directly (not wrapped in Optional)
        # Check string representation to detect Connection[T]
        annotation_str = str(annotation)
        if 'Connection[' in annotation_str:
            inner_type = _extract_connection_inner_type(annotation)
            if inner_type and inner_type not in _seen:
                inner_sgqlc_type = get_sgqlc_type(inner_type)
                connection_name = f"{inner_type.__name__}Connection"
                
                if connection_name in _connection_type_cache:
                    connection_class = _connection_type_cache[connection_name]
                else:
                    connection_class = type(connection_name, (SGQLCConnection,), {
                        'nodes': list_of(inner_sgqlc_type)
                    })
                    _connection_type_cache[connection_name] = connection_class
                
                return Field(connection_class, args=connection_args())
        
        # Handle list types
        if origin is list:
            args = get_args(annotation)
            if args:
                inner_type = _pydantic_to_sgqlc_type(args[0], pydantic_model, _seen)
                if inner_type is None:
                    return None  # Skip if inner type is Connection
                return list_of(inner_type)
            return list_of(str)  # Default
        
        # Handle basic Python types using sgqlc's map_python_to_graphql
        if annotation in map_python_to_graphql:
            return map_python_to_graphql[annotation]
        
        # If it's a Pydantic model, generate sgqlc type for it
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return get_sgqlc_type(annotation)
        
        # String forward reference
        if isinstance(annotation, str):
            return annotation
        
        # Default to str
        return str
    finally:
        _seen.discard(annotation_id)


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
        sgqlc_type = _pydantic_to_sgqlc_type(annotation, pydantic_model)
        
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

