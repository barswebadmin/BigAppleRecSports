"""Click parameter type for Shopify customer identifiers."""

from typing import Dict, Any

from .base import ValidatedParamType


def _convert_shopify_customer_identifier(identifier: str) -> Dict[str, Any]:
    """Convert Shopify customer identifier input to dict format.
    
    Shopify customers can be identified by:
    - Email: customer@example.com
    - ID: gid://shopify/Customer/123456789 or just 123456789 (digits only)
    - Name: "First Last", "f:First", "l:Last" (with or without hash/prefix)
    
    Args:
        identifier: Raw identifier string from user input
        
    Returns:
        Dict with keys:
        - identifier: Original identifier string
        - query: GraphQL search query string
        - not_found_message: Error message if not found
        - first: Number of results to fetch (1 for email/ID, 10 for name)
    
    Raises:
        ValueError: If identifier format is invalid
    """
    identifier = identifier.strip() if identifier else ""
    if not identifier:
        raise ValueError("Shopify customer identifier cannot be empty")
    
    # Email lookup
    if "@" in identifier:
        return {
            "identifier": identifier,
            "query": f"email:{identifier}",
            "not_found_message": f"No customer found with email: {identifier}",
            "first": 1
        }
    
    # First name prefix (f:First or #f:First)
    if identifier.startswith("#f:"):
        first_name = identifier[3:].strip()
    elif identifier.startswith("f:"):
        first_name = identifier[2:].strip()
    else:
        first_name = None
    
    if first_name is not None:
        if not first_name:
            raise ValueError("First name cannot be empty after 'f:' prefix")
        return {
            "identifier": identifier,
            "query": f"first_name:{first_name}",
            "not_found_message": f"No customers found with first name '{first_name}'",
            "first": 10
        }
    
    # Last name prefix (l:Last or #l:Last)
    if identifier.startswith("#l:"):
        last_name = identifier[3:].strip()
    elif identifier.startswith("l:"):
        last_name = identifier[2:].strip()
    else:
        last_name = None
    
    if last_name is not None:
        if not last_name:
            raise ValueError("Last name cannot be empty after 'l:' prefix")
        return {
            "identifier": identifier,
            "query": f"last_name:{last_name}",
            "not_found_message": f"No customers found with last name '{last_name}'",
            "first": 10
        }
    
    # Full name (First Last) - check for space
    if " " in identifier:
        parts = identifier.split(maxsplit=1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else None
        search_parts = [f"first_name:{first_name}"]
        if last_name:
            search_parts.append(f"last_name:{last_name}")
        search_desc = [f"first name '{first_name}'"]
        if last_name:
            search_desc.append(f"last name '{last_name}'")
        return {
            "identifier": identifier,
            "query": " ".join(search_parts),
            "not_found_message": f"No customers found with {' and '.join(search_desc)}",
            "first": 10
        }
    
    # ID lookup - handle gid://shopify/Customer/123 or just 123
    if identifier.startswith("gid://shopify/Customer/"):
        numeric_id = identifier.split("/")[-1]
        search_query = f"id:{numeric_id}"
    elif identifier.isdigit():
        # Just digits - treat as ID
        search_query = f"id:{identifier}"
    else:
        # Try as ID anyway (might be non-numeric ID format)
        search_query = f"id:{identifier}"
    
    return {
        "identifier": identifier,
        "query": search_query,
        "not_found_message": f"No customer found with ID: {identifier}",
        "first": 1
    }


class ShopifyCustomerIdentifierParam(ValidatedParamType):
    """Click parameter type for Shopify customer identifiers.
    
    Supports multiple formats:
    - Email: customer@example.com
    - ID: gid://shopify/Customer/123456789 or 123456789
    - Name: "First Last", "f:First", "l:Last" (with or without # prefix)
    
    Returns a dict with query parameters for GraphQL search.
    """
    
    def __init__(self):
        super().__init__(
            converter_function=_convert_shopify_customer_identifier,
            prompt_text="Enter Shopify customer identifier (email, ID, or name)"
        )


SHOPIFY_CUSTOMER_IDENTIFIER = ShopifyCustomerIdentifierParam()

