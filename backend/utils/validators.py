import re
from typing import Optional, TypedDict


def validate_email_format(email: Optional[str]) -> Optional[str]:
    """
    Validate an email address with a simple pattern:
    at least 1 char + @ + at least 1 char + '.' + at least 2 chars
    """
    if email is None:
        return "Email is required"
    if re.match(r'^.+@.+\..{2,}$', email) is None:
        return "Invalid email format"
    return None


def validate_shopify_order_number_format(order_number: Optional[str]) -> Optional[str]:
    """
    Validate a Shopify order number: optional leading '#', followed by at least 4 digits.
    """
    if order_number is None:
        return "Order number is required"
    if re.match(r'^#?\d{4,}$', order_number) is None:
        return "Invalid order number format"
    return None