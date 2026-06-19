"""Google Discovery API utilities for schema introspection.

Pure functions for working with Google Discovery documents - no client imports.
Used by export and analysis scripts.
"""

from typing import Any


def list_schemas(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract all resource schemas from a discovery document.
    
    Args:
        doc: Google API discovery document
        
    Returns:
        Dict mapping schema names to schema definitions
    """
    return doc.get("schemas", {})


def list_methods(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract all methods from a discovery document with flat paths.
    
    Args:
        doc: Google API discovery document
        
    Returns:
        Dict mapping method paths (e.g. "users.messages.send") to method definitions
    """
    resources = doc.get("resources", {})
    return _extract_methods_recursive(resources)


def _extract_methods_recursive(
    resources: dict[str, Any],
    prefix: str = ""
) -> dict[str, dict[str, Any]]:
    """Recursively extract methods from nested resource structures."""
    all_methods = {}
    
    for resource_name, resource_data in resources.items():
        full_prefix = f"{prefix}{resource_name}." if prefix or resource_name else ""
        
        # Extract methods at this level
        if "methods" in resource_data:
            for method_name, method_def in resource_data["methods"].items():
                method_path = f"{full_prefix}{method_name}"
                all_methods[method_path] = method_def
        
        # Recurse into nested resources
        if "resources" in resource_data:
            nested = _extract_methods_recursive(resource_data["resources"], full_prefix)
            all_methods.update(nested)
    
    return all_methods


def extract_method_scopes(doc: dict[str, Any]) -> dict[str, list[str]]:
    """Extract OAuth scopes required by each method.
    
    Args:
        doc: Google API discovery document
        
    Returns:
        Dict mapping method paths to lists of required OAuth scopes
    """
    methods = list_methods(doc)
    return {
        method_path: method_def.get("scopes", [])
        for method_path, method_def in methods.items()
    }


def get_api_scopes(doc: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Extract all OAuth scopes defined for an API.
    
    Args:
        doc: Google API discovery document
        
    Returns:
        Dict mapping scope URLs to scope metadata (description)
    """
    auth = doc.get("auth", {}).get("oauth2", {})
    return auth.get("scopes", {})


def get_api_metadata(doc: dict[str, Any]) -> dict[str, Any]:
    """Extract high-level API metadata from discovery document.
    
    Args:
        doc: Google API discovery document
        
    Returns:
        Dict with name, version, title, description, baseUrl, documentationLink
    """
    return {
        "name": doc.get("name", ""),
        "version": doc.get("version", ""),
        "title": doc.get("title", ""),
        "description": doc.get("description", ""),
        "baseUrl": doc.get("baseUrl", ""),
        "documentationLink": doc.get("documentationLink", ""),
    }


def format_method_summary(method_path: str, method_def: dict[str, Any]) -> str:
    """Format a human-readable summary of a method.
    
    Args:
        method_path: Dot-notation path (e.g. "users.messages.send")
        method_def: Method definition from discovery doc
        
    Returns:
        Formatted string summary
    """
    lines = [
        f"📍 {method_path}",
        f"   {method_def.get('httpMethod', 'GET')} {method_def.get('path', '')}",
    ]
    
    description = method_def.get("description", "").strip()
    if description:
        # Truncate long descriptions
        desc_line = description[:100] + "..." if len(description) > 100 else description
        lines.append(f"   {desc_line}")
    
    scopes = method_def.get("scopes", [])
    if scopes:
        lines.append(f"   Scopes: {' OR '.join(scopes)}")
    
    return "\n".join(lines)


def format_scope_summary(scope_url: str, scope_info: dict[str, str]) -> str:
    """Format a human-readable summary of an OAuth scope.
    
    Args:
        scope_url: Full OAuth scope URL
        scope_info: Scope metadata with description
        
    Returns:
        Formatted string summary
    """
    lines = [
        f"• {scope_url}",
        f"  {scope_info.get('description', 'No description')}",
    ]
    return "\n".join(lines)
