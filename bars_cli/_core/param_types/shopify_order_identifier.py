"""Click parameter type for Shopify order identifiers."""

from typing import Dict, Any, Optional, Callable, TYPE_CHECKING

from .base import ValidatedParamType

if TYPE_CHECKING:
    from bars_cli.backend_services.shopify.services import ShopifyService

# Lazy import for ShopifyService to avoid circular dependencies
_normalize_order_id: Optional[Callable[[Optional[str]], Optional[Dict[str, str]]]] = None
_normalize_order_number: Optional[Callable[[Optional[str]], Optional[Dict[str, str]]]] = None


def _get_normalizers():
    """Get normalizer functions from ShopifyService."""
    global _normalize_order_id, _normalize_order_number
    
    if _normalize_order_id is None or _normalize_order_number is None:
        # Import via symlink - service handles the backend imports correctly
        from bars_cli.backend_services.shopify.services import ShopifyService  # type: ignore
        _normalize_order_id = ShopifyService.normalize_order_identifier  # type: ignore
        _normalize_order_number = ShopifyService.normalize_order_number  # type: ignore
    
    return _normalize_order_id, _normalize_order_number


def _convert_shopify_order_identifier(identifier: str) -> Dict[str, Any]:
    """Convert Shopify order identifier input to dict format.
    
    Shopify orders can be identified by:
    - Order number: 1234 or #1234
    - Order ID: gid://shopify/Order/123456789 or just 123456789 (digits only)
    
    Uses normalizers directly to validate and normalize input.
    
    Args:
        identifier: Raw identifier string from user input
        
    Returns:
        Dict with keys:
        - identifier: Original identifier string
        - query: GraphQL search query string
        - not_found_message: Error message if not found
        - first: Number of results to fetch (1 for single lookups)
    
    Raises:
        ValueError: If identifier format is invalid
    """
    identifier = identifier.strip() if identifier else ""
    if not identifier:
        raise ValueError("Shopify order identifier cannot be empty")
    
    # Get normalizers from service (lazy import)
    normalize_order_id, normalize_order_number = _get_normalizers()
    
    if normalize_order_id is None or normalize_order_number is None:
        raise RuntimeError("Failed to load Shopify normalizers from service")
    
    # Try order ID first (more specific - requires 10-15 digits)
    # This handles gid://shopify/Order/1234567890 or 1234567890
    normalized_id = normalize_order_id(identifier)
    if normalized_id:
        order_id = normalized_id["digits_only"]
        return {
            "identifier": identifier,
            "query": f"id:{order_id}",
            "not_found_message": f"No order found with ID: {identifier}",
            "first": 1
        }
    
    # Try order number (handles #1234 and 1234, requires 4+ digits)
    normalized_number = normalize_order_number(identifier)
    if normalized_number:
        order_num = normalized_number["digits_only"]
        return {
            "identifier": identifier,
            "query": f"name:#{order_num}",
            "not_found_message": f"No order found with number: {order_num}",
            "first": 1
        }
    
    # If neither normalizer accepts it, raise error
    raise ValueError(f"Invalid order identifier format: {identifier}. Expected order number (e.g., 1234 or #1234) or order ID (e.g., gid://shopify/Order/1234567890 or 1234567890)")


class ShopifyOrderIdentifierParam(ValidatedParamType):
    """Click parameter type for Shopify order identifiers.
    
    Supports multiple formats:
    - Order number: 1234 or #1234
    - Order ID: gid://shopify/Order/123456789 or 123456789
    
    Returns a dict with query parameters for GraphQL search.
    """
    
    def __init__(self):
        super().__init__(
            converter_function=_convert_shopify_order_identifier,
            prompt_text="Enter Shopify order identifier (number or ID)"
        )


SHOPIFY_ORDER_IDENTIFIER = ShopifyOrderIdentifierParam()

