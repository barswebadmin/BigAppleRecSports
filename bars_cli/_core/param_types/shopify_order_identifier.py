"""Click parameter type for Shopify order identifiers."""

from typing import Dict, Any

from .base import ValidatedParamType


def _convert_shopify_order_identifier(identifier: str) -> Dict[str, Any]:
    """Convert Shopify order identifier input to dict format.
    
    Shopify orders can be identified by:
    - Order number: 1234 or #1234 (5 digits after stripping #)
    - Order ID: gid://shopify/Order/123456789 or 123456789 (11-16 digits)
    
    Args:
        identifier: Raw identifier string from user input
        
    Returns:
        Dict with keys:
        - identifier: Normalized identifier string (# stripped for order numbers, just digits)
        - type: "order_number" or "order_id"
    
    Raises:
        ValueError: If identifier format is invalid
    """
    identifier = identifier.strip() if identifier else ""
    if not identifier:
        raise ValueError("Shopify order identifier cannot be empty")
    
    # Try order number first (5 digits after stripping leading #)
    test_number = identifier.lstrip('#')
    if test_number.isdigit() and len(test_number) == 5:
        # It's an order number - return WITHOUT # prefix (to avoid URL fragment issues)
        return {
            "identifier": test_number,  # Send just digits, backend will add # for query
            "type": "order_number"
        }
    
    # Try order ID (11-16 digits, possibly in gid:// format)
    # Split on '/' and take last element
    parts = identifier.split('/')
    test_id = parts[-1]
    
    if test_id.isdigit() and 11 <= len(test_id) <= 16:
        # It's an order ID - return just the digits
        return {
            "identifier": test_id,
            "type": "order_id"
        }
    
    # If neither format matches, raise error
    raise ValueError(
        f"Invalid order identifier format: {identifier}. "
        f"Expected order number (5 digits, e.g., 1234 or #12345) "
        f"or order ID (11-16 digits, e.g., gid://shopify/Order/1234567890 or 1234567890)"
    )


class ShopifyOrderIdentifierParam(ValidatedParamType):
    """Click parameter type for Shopify order identifiers.
    
    Supports multiple formats:
    - Order number: 12345 or #12345 (5 digits)
    - Order ID: gid://shopify/Order/123456789 or 123456789 (11-16 digits)
    
    Returns a dict with the identifier to send to the API.
    """
    
    def __init__(self):
        super().__init__(
            converter_function=_convert_shopify_order_identifier,
            prompt_text="Enter Shopify order identifier (number or ID)"
        )


SHOPIFY_ORDER_IDENTIFIER = ShopifyOrderIdentifierParam()


