"""Click parameter type for Shopify customer identifiers."""

from typing import Dict, Any, Optional, Callable

from .base import ValidatedParamType
from ..prompts import prompt_select_from_options, EXIT_SENTINEL

# Lazy import for ShopifyService to avoid circular dependencies
_normalize_customer_id: Optional[Callable] = None


def _get_normalizer():
    """Get normalizer function from ShopifyService."""
    global _normalize_customer_id
    
    if _normalize_customer_id is None:
        # Import via symlink - service handles the backend imports correctly
        from bars_cli.backend_services.shopify.services import ShopifyService
        _normalize_customer_id = ShopifyService.normalize_customer_id  # type: ignore[attr-defined]
    
    return _normalize_customer_id


def _convert_shopify_customer_identifier(identifier: str) -> Dict[str, Any]:
    """Convert Shopify customer identifier input to dict format.
    
    Shopify customers can be identified by:
    - Customer ID: gid://shopify/Customer/123456789 or just 123456789
    - Email: customer@example.com
    - Name: "First Last", "-f First", "-l Last", or just "Name" (will prompt for first/last)
    
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
    
    # Step 1: Try to normalize as customer ID first
    normalize_customer_id = _get_normalizer()
    if normalize_customer_id is None:
        raise RuntimeError("Failed to load Shopify normalizer from service")
    normalized_id = normalize_customer_id(identifier)
    if normalized_id:
        customer_id = normalized_id["digits_only"]
        return {
            "identifier": identifier,
            "query": f"id:{customer_id}",
            "not_found_message": f"No customer found with ID: {identifier}",
            "first": 1
        }
    
    # Step 2: Try email lookup
    if "@" in identifier:
        return {
            "identifier": identifier,
            "query": f"email:{identifier}",
            "not_found_message": f"No customer found with email: {identifier}",
            "first": 1
        }
    
    # Step 3: Parse name with flags and spaces
    # Handle flags: -f for first name, -l for last name
    parts = identifier.split()
    
    # Check for flags
    first_name = None
    last_name = None
    remaining_parts = []
    
    i = 0
    while i < len(parts):
        part = parts[i]
        if part == "-f" and i + 1 < len(parts):
            first_name = parts[i + 1]
            i += 2
        elif part == "-l" and i + 1 < len(parts):
            last_name = parts[i + 1]
            i += 2
        else:
            remaining_parts.append(part)
            i += 1
    
    # If flags were used, use them
    if first_name or last_name:
        search_parts = []
        search_desc = []
        if first_name:
            search_parts.append(f"first_name:{first_name}")
            search_desc.append(f"first name '{first_name}'")
        if last_name:
            search_parts.append(f"last_name:{last_name}")
            search_desc.append(f"last name '{last_name}'")
        
        if search_parts:
            return {
                "identifier": identifier,
                "query": " ".join(search_parts),
                "not_found_message": f"No customers found with {' and '.join(search_desc)}",
                "first": 10
            }
    
    # No flags used - parse remaining parts
    if len(remaining_parts) == 0:
        raise ValueError("No name provided")
    
    if len(remaining_parts) == 1:
        # Single name - prompt user to choose first or last
        name = remaining_parts[0]
        choice = prompt_select_from_options(
            display_text=f"Is '{name}' a first name or last name?",
            options=["First name", "Last name"],
            autocomplete=False
        )
        
        if choice == EXIT_SENTINEL:
            raise ValueError("Name type selection cancelled")
        
        if choice == "First name":
            return {
                "identifier": identifier,
                "query": f"first_name:{name}",
                "not_found_message": f"No customers found with first name '{name}'",
                "first": 10
            }
        else:  # Last name
            return {
                "identifier": identifier,
                "query": f"last_name:{name}",
                "not_found_message": f"No customers found with last name '{name}'",
                "first": 10
            }
    
    # Multiple parts: first is first name, rest joined as last name
    first_name = remaining_parts[0]
    last_name = " ".join(remaining_parts[1:])
    
    return {
        "identifier": identifier,
        "query": f"first_name:{first_name} last_name:{last_name}",
        "not_found_message": f"No customers found with first name '{first_name}' and last name '{last_name}'",
        "first": 10
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

