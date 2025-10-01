from typing import Dict, Optional
# No validator imports needed - doing validation inline


def normalize_shopify_id(id_input: Optional[str]) -> Optional[str]:
    """
    Normalize any Shopify ID (order, product, customer, etc.) to digits-only format.
    
    Handles both GID format (gid://shopify/ResourceType/123456) and plain numeric IDs.
    Returns the numeric ID string if valid, None otherwise.
    """
    if not id_input:
        return None
    
    id_str = str(id_input).strip()
    
    # Check for GID format (case insensitive)
    if id_str.lower().startswith("gid://"):
        parts = id_str.split("/")
        # Must have format: gid://shopify/ResourceType/ID
        # Parts will be: ['gid:', '', 'shopify', 'ResourceType', 'ID']
        if len(parts) != 5 or parts[2].lower() != "shopify":
            return None
        digits = parts[4]  # Last part should be the ID
    else:
        # Plain numeric ID
        digits = id_str
    
    # Validate digits: must be numeric and between 8-20 characters
    if not digits.isdigit() or not (8 <= len(digits) <= 20):
        return None
    
    return digits


def normalize_order_number(order_number_input: Optional[str]) -> Optional[str]:
    """
    Normalize order number to digits-only format.
    
    Removes any leading hash (#) and validates the remaining digits.
    Returns the numeric string if valid (4-8 digits), None otherwise.
    """
    if not order_number_input:
        return None
    
    order_str = str(order_number_input).strip()
    
    # Remove leading hash if present
    if order_str.startswith("#"):
        digits = order_str[1:]
    else:
        digits = order_str
    
    # Validate digits: must be numeric and between 4-8 characters
    if not digits.isdigit() or not (4 <= len(digits) <= 8):
        return None
    
    return digits


def normalize_email(email_input: Optional[str]) -> Optional[str]:
    """
    Normalize email address with basic validation.
    
    Strips whitespace, converts to lowercase, and validates basic email format.
    Returns the normalized email if valid, None otherwise.
    """
    if not email_input:
        return None
    
    email_str = str(email_input).strip().lower()
    
    # Basic email validation: must contain @ and . with reasonable lengths
    if "@" not in email_str or "." not in email_str:
        return None
    
    # Split on @ to check parts
    parts = email_str.split("@")
    if len(parts) != 2:
        return None
    
    local_part, domain_part = parts
    
    # Basic length checks
    if not (1 <= len(local_part) <= 64) or not (1 <= len(domain_part) <= 253):
        return None
    
    # Domain must contain at least one dot and not start/end with dot
    if "." not in domain_part or domain_part.startswith(".") or domain_part.endswith("."):
        return None
    
    # Overall length check
    if len(email_str) > 320:  # RFC 5321 limit
        return None
    
    return email_str


