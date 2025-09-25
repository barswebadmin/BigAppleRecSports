import re
from typing import Optional, TypedDict


class ValidationResult(TypedDict, total=True):
    success: bool
    message: Optional[str]


def validate_email_format(email: Optional[str]) -> ValidationResult:
    """
    Validate an email address with a simple pattern:
    at least 1 char + @ + at least 1 char + '.' + at least 2 chars
    """
    if email is None:
        return {"success": False, "message": "Email is required"}
    if re.match(r'^.+@.+\..{2,}$', email) is None:
        return {"success": False, "message": "Invalid email format"}
    return {"success": True, "message": "Email is valid"}


def validate_shopify_order_number_format(order_number: Optional[str]) -> ValidationResult:
    """
    Validate a Shopify order number: optional leading '#', followed by at least 4 digits.
    """
    if order_number is None:
        return {"success": False, "message": "Order number is required"}
    if re.match(r'^#?\d{4,}$', order_number) is None:
        return {"success": False, "message": "Invalid order number format"}
    return {"success": True, "message": "Order number is valid"}