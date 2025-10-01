import re
from typing import Optional, TypedDict


class ValidationResult(TypedDict, total=True):
    success: bool
    message: Optional[str]

def validate_email_format(email: Optional[str], criteria: Optional[object] = None) -> ValidationResult:
    """
    Pragmatic email validation:
    - local part allows common RFC 5322 safe chars
    - domain has at least one dot and valid labels
    """
    if email is None:
        return {"success": False, "message": "Email was not provided"}
    pattern = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}$")
    if pattern.match(email) is None:
        return {"success": False, "message": "Invalid email format"}
    return {"success": True, "message": "Email is valid"}

def validate_shopify_order_number_format(order_number: Optional[str]) -> ValidationResult:
    """
    Validate a Shopify order number: optional leading '#', followed by at least 4 digits.
    """
    if order_number is None:
        return {"success": False, "message": "Order number was not provided"}
    if re.match(r'^#?\d{4,}$', order_number) is None:
        return {"success": False, "message": "Invalid order number format"}
    return {"success": True, "message": "Order number is valid"}

def validate_shopify_order_id_format(order_id: Optional[str]) -> ValidationResult:
    """
    Validate a Shopify order ID: optional leading "gid://shopify/Order/" followed by 10-15 digits.
    """
    if order_id is None:
        return {"success": False, "message": "Order ID was not provided"}
    # Accept either numeric id or full gid form
    if re.match(r'^\d{10,15}$', order_id) is None and re.match(r'^gid://shopify/Order/\d{10,15}$', order_id) is None:
        return {"success": False, "message": "Invalid order ID format"}
    return {"success": True, "message": "Order ID is valid"}


def validate_shopify_product_id_format(product_id: Optional[str]) -> ValidationResult:
    """
    Validate a Shopify product ID: allow numeric or full GID (gid://shopify/Product/{digits}).
    """
    if product_id is None:
        return {"success": False, "message": "Product ID was not provided"}
    if re.match(r'^\d{8,20}$', product_id) is None and re.match(r'^gid://shopify/Product/\d{8,20}$', product_id) is None:
        return {"success": False, "message": "Invalid product ID format"}
    return {"success": True, "message": "Product ID is valid"}


def validate_shopify_customer_id_format(customer_id: Optional[str]) -> ValidationResult:
    """
    Validate a Shopify customer ID: allow numeric or full GID (gid://shopify/Customer/{digits}).
    """
    if customer_id is None:
        return {"success": False, "message": "Customer ID was not provided"}
    if re.match(r'^\d{8,20}$', customer_id) is None and re.match(r'^gid://shopify/Customer/\d{8,20}$', customer_id) is None:
        return {"success": False, "message": "Invalid customer ID format"}
    return {"success": True, "message": "Customer ID is valid"}


def validate_shopify_transaction_id_format(transaction_id: Optional[str]) -> ValidationResult:
    """
    Validate a Shopify transaction ID: allow numeric or full GID (gid://shopify/Transaction/{digits}).
    """
    if transaction_id is None:
        return {"success": False, "message": "Transaction ID was not provided"}
    if re.match(r'^\d{8,20}$', transaction_id) is None and re.match(r'^gid://shopify/Transaction/\d{8,20}$', transaction_id) is None:
        return {"success": False, "message": "Invalid transaction ID format"}
    return {"success": True, "message": "Transaction ID is valid"}


def validate_shopify_variant_id_format(variant_id: Optional[str]) -> ValidationResult:
    """
    Validate a Shopify variant ID: allow numeric or full GID (gid://shopify/Variant/{digits}).
    """
    if variant_id is None:
        return {"success": False, "message": "Variant ID was not provided"}
    if re.match(r'^\d{8,20}$', variant_id) is None and re.match(r'^gid://shopify/Variant/\d{8,20}$', variant_id) is None:
        return {"success": False, "message": "Invalid variant ID format"}
    return {"success": True, "message": "Variant ID is valid"}