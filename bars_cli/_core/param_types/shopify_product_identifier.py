"""Click parameter type for Shopify product identifiers."""

from typing import Dict, Any, Optional, Callable, TYPE_CHECKING

from .base import ValidatedParamType

if TYPE_CHECKING:
    from bars_cli.backend_services.shopify.services import ShopifyService

# Lazy import for ShopifyService to avoid circular dependencies
_normalize_product_id: Optional[Callable[[Optional[str]], Optional[Dict[str, str]]]] = None


def _get_normalizer():
    """Get normalizer function from ShopifyService."""
    global _normalize_product_id
    
    if _normalize_product_id is None:
        # Import via symlink - service handles the backend imports correctly
        from bars_cli.backend_services.shopify.services import ShopifyService  # type: ignore
        _normalize_product_id = ShopifyService.normalize_product_identifier  # type: ignore[attr-defined]
    
    return _normalize_product_id


def _convert_shopify_product_identifier(identifier: str) -> Dict[str, Any]:
    """Convert Shopify product identifier input to dict format.
    
    Shopify products can be identified by:
    - Product ID: gid://shopify/Product/123456789 or just 123456789 (digits only)
    - Handle: product-handle-string (any string without spaces, typically lowercase with hyphens)
    - Admin URL: https://admin.shopify.com/store/{store}/products/{id}
    
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
    import re
    
    identifier = identifier.strip() if identifier else ""
    if not identifier:
        raise ValueError("Shopify product identifier cannot be empty")
    
    # Check for Shopify admin URL format: https://admin.shopify.com/store/{store}/products/{id}
    url_match = re.search(r'/products/(\d+)', identifier)
    if url_match:
        product_id = url_match.group(1)
        return {
            "identifier": product_id,
            "query": f"id:{product_id}",
            "not_found_message": f"No product found with ID: {product_id}",
            "first": 1
        }
    
    # Get normalizer from service (lazy import)
    normalize_product_id = _get_normalizer()
    
    if normalize_product_id is None:
        raise RuntimeError("Failed to load Shopify normalizer from service")
    
    # Try product ID first (more specific - requires numeric ID)
    # This handles gid://shopify/Product/1234567890 or 1234567890
    normalized_id = normalize_product_id(identifier)
    if normalized_id:
        product_id = normalized_id["digits_only"]
        return {
            "identifier": identifier,
            "query": f"id:{product_id}",
            "not_found_message": f"No product found with ID: {identifier}",
            "first": 1
        }
    
    # Try handle (any non-empty string that's not a valid ID)
    # Handles product handles like "2025-fall-kickball-sunday-open-division"
    if identifier and not identifier.startswith("gid://"):
        return {
            "identifier": identifier,
            "query": f"handle:{identifier}",
            "not_found_message": f"No product found with handle: {identifier}",
            "first": 1
        }
    
    # If neither format works, raise error
    raise ValueError(
        f"Invalid product identifier format: {identifier}. "
        "Expected product ID (e.g., gid://shopify/Product/1234567890 or 1234567890), "
        "product handle (e.g., product-handle-string), "
        "or Shopify admin URL (e.g., https://admin.shopify.com/store/{store}/products/{id})"
    )


class ShopifyProductIdentifierParam(ValidatedParamType):
    """Click parameter type for Shopify product identifiers.
    
    Supports multiple formats:
    - Product ID: gid://shopify/Product/123456789 or 123456789
    - Handle: product-handle-string
    - Admin URL: https://admin.shopify.com/store/{store}/products/{id}
    
    Returns a dict with query parameters for GraphQL search.
    """
    
    def __init__(self):
        super().__init__(
            converter_function=_convert_shopify_product_identifier,
            prompt_text="Enter Shopify product identifier (ID or handle)"
        )


SHOPIFY_PRODUCT_IDENTIFIER = ShopifyProductIdentifierParam()

