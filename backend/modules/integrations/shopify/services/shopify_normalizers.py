from typing import Any, Dict, Optional
from validator_collection import is_between, is_integer, is_string, is_url
from backend.shared.validators import ValidationResult

from backend.config import config
import logging

logger = logging.getLogger(__name__)

def _get_shopify_admin_url() -> str:
    """Get Shopify admin URL with safe access."""
    shopify = config.shopify
    if shopify and shopify.url:
        return shopify.url.admin
    # Fallback to environment variable if config not loaded
    import os
    return os.getenv("SHOPIFY.URL.ADMIN", "")

SHOPIFY_ADMIN_BASE_URL = _get_shopify_admin_url()
SHOPIFY_GID_BASE = "gid://shopify/"

RESOURCE_IDENTIFIER_CONFIG = {
    "order_id": {
        "url_slugs": ["orders"],
        "gid_prefix": "Order",
        "id_field": "order_id",
        "id_field_2": "order_number",
        "min_length": 10,
        "max_length": 15,
    },
    "order_number": {
        "url_slugs": ["orders"],
        "gid_prefix": "Order",
        "id_field": "name",
        "min_length": 4,
        "max_length": None,
    },
    "product": {
        "url_slugs": ["products"],
        "gid_prefix": "Product",
        "id_field": "product_id",
        "min_length": 8,
        "max_length": 20,
    },
    "customer": {
        "url_slugs": ["customers"],
        "gid_prefix": "Customer",
        "id_field": "customer_id",
        "min_length": 8,
        "max_length": 20,
    },
    "variant": {
        "url_slugs": ["products", "variants"],
        "gid_prefix": "ProductVariant",
        "id_field": "variant_id",
        "min_length": 8,
        "max_length": 20,
    },
    "transaction": {
        "url_slugs": ["transactions"],
        "gid_prefix": "Transaction",
        "id_field": "transaction_id",
        "min_length": 8,
        "max_length": 20,
    },
}

def build_shopify_resource_url(input_dict: Dict[str, str], resource_config: Dict[str, Any]) -> Optional[str]:
    """Build Shopify admin URL for a given resource type and ID.
    
    Args:
        input_dict: Dict with "type" (str), "input" (str), and optionally "product_input" (str) for variants
        resource_config: Resource configuration dict from RESOURCE_IDENTIFIER_CONFIG
    
    Returns:
        Shopify admin URL or None if invalid
    """
    resource_id = input_dict.get("input")
    if not resource_id:
        return None
    
    product_input = input_dict.get("product_input")
    base_url = _get_shopify_admin_url()
    url_parts = [base_url]
    url_slugs = resource_config["url_slugs"]
    
    if input_dict.get("type") == "variant" and product_input:
        url_parts.extend([url_slugs[0], product_input, url_slugs[1]])
    else:
        url_parts.extend(url_slugs)
    
    url_parts.append(resource_id)
    return "/".join(url_parts)
    



def normalize_order_number(order_number_input: Optional[str]) -> Optional[Dict[str, str]]:
    """Normalize order number to a dict with with_hash and digits_only"""
    if not order_number_input or not validate_shopify_order_number_format(order_number_input).get("success"):
        return None
    digits_only = order_number_input.replace("#", "")
    return {"digits_only": digits_only, "with_hash": f"#{digits_only}"}





def normalize_shopify_resource_identifier(input_dict: Dict[str, str], resource_config: Dict[str, Any]) -> Optional[Dict[str, Optional[str]]]:
    """
    Normalize a Shopify resource identifier to a dict with digits_only and gid.
    
    Args:
        input_dict: Dict with "type" (str), "input" (str), and optionally "product_input" (str) for variants
        resource_config: Resource configuration dict from RESOURCE_IDENTIFIER_CONFIG
    
    Returns:
        Dict with "digits_only" and "gid" keys, or None if validation fails
    """
    validation_result = validate_shopify_resource_identifier(input_dict)
    if not validation_result.is_valid or not is_string(validation_result.input_after_validation):
        return None

    digits_only = str(validation_result.input_after_validation)
    gid_prefix = resource_config["gid_prefix"]
    return {
        "digits_only": digits_only,
        "gid": f"{SHOPIFY_GID_BASE}{gid_prefix}/{digits_only}",
    }

def normalize_order_identifier(order_id_input: str) -> Optional[Dict[str, Optional[str]]]:
    """Normalize an order id. Wrapper for normalize_shopify_resource_identifier."""
    resource_config = RESOURCE_IDENTIFIER_CONFIG.get("order_id")
    if not resource_config:
        return None
    
    result = normalize_shopify_resource_identifier({"type": "order_id", "input": order_id_input}, resource_config)
    if not result:
        return None
    
    input_dict = {"type": "order_id", "input": result["digits_only"]}
    url = build_shopify_resource_url(input_dict, resource_config)
    return {**result, "url": url}


def normalize_product_identifier(product_id_input: str) -> Optional[Dict[str, Optional[str]]]:
    """Normalize a product id. Wrapper for normalize_shopify_resource_identifier."""
    resource_config = RESOURCE_IDENTIFIER_CONFIG.get("product")
    if not resource_config:
        return None
    
    result = normalize_shopify_resource_identifier({"type": "product", "input": product_id_input}, resource_config)
    if not result:
        return None
    
    input_dict = {"type": "product", "input": result["digits_only"]}
    url = build_shopify_resource_url(input_dict, resource_config)
    return {**result, "url": url}


def normalize_customer_identifier(customer_id_input: str) -> Optional[Dict[str, Optional[str]]]:
    """Normalize a customer id. Wrapper for normalize_shopify_resource_identifier."""
    resource_config = RESOURCE_IDENTIFIER_CONFIG.get("customer")
    if not resource_config:
        return None
    
    result = normalize_shopify_resource_identifier({"type": "customer", "input": customer_id_input}, resource_config)
    if not result:
        return None
    
    input_dict = {"type": "customer", "input": result["digits_only"]}
    url = build_shopify_resource_url(input_dict, resource_config)
    return {**result, "url": url}


def normalize_transaction_identifier(transaction_id_input: str) -> Optional[Dict[str, Optional[str]]]:
    """Normalize a transaction id. Wrapper for normalize_shopify_resource_identifier."""
    resource_config = RESOURCE_IDENTIFIER_CONFIG.get("transaction")
    if not resource_config:
        return None
    
    result = normalize_shopify_resource_identifier({"type": "transaction", "input": transaction_id_input}, resource_config)
    if not result:
        return None
    
    input_dict = {"type": "transaction", "input": result["digits_only"]}
    url = build_shopify_resource_url(input_dict, resource_config)
    return {**result, "url": url}


def normalize_variant_identifier(variant_id_input: str, product_id_input: Optional[str] = None) -> Optional[Dict[str, Optional[str]]]:
    """Normalize a variant id. Wrapper for normalize_shopify_resource_identifier.
    
    Args:
        variant_id_input: Variant identifier to normalize
        product_id_input: Optional product identifier for variant URL construction
    """
    resource_config = RESOURCE_IDENTIFIER_CONFIG.get("variant")
    if not resource_config:
        return None
    
    result = normalize_shopify_resource_identifier({"type": "variant", "input": variant_id_input}, resource_config)
    if not result:
        return None
    
    if product_id_input:
        input_dict = {"type": "variant", "input": result["digits_only"], "product_input": product_id_input}
        url = build_shopify_resource_url(input_dict, resource_config)
        return {**result, "url": url}
    
    return result





def validate_shopify_order_number_format(order_number: Optional[str]) -> ValidationResult:
    """
    Validate a Shopify order number: optional leading '#', followed by at least 4 digits.
    Supports numeric format only (order numbers are not GIDs or URLs).
    """
    if order_number is None:
        return ValidationResult.failure("Order number is required")
    
    if is_url(order_number):
        return ValidationResult.failure("Order number cannot be a URL")
    
    if order_number.startswith("gid://"):
        return ValidationResult.failure("Order number cannot be a GID")
    
    digits_only = order_number.lstrip("#")
    string_length = len(digits_only)

    if not is_integer(digits_only) or not is_between(string_length, 4, 8):
        return ValidationResult.failure(f"Invalid order number format detected for {order_number}")
    
    return ValidationResult.success(order_number)


def validate_shopify_resource_identifier(input_dict: Dict[str, str]) -> ValidationResult:
    """
    Validate a Shopify resource identifier: numeric, GID (gid://shopify/{Resource}/{digits}), or URL.
    
    Args:
        input_dict: Dict with "type" (str), "input" (str), and optionally "product_input" (str) for variants
    
    Returns:
        ValidationResult.success() with digits_only as input_after_validation if valid,
        ValidationResult.failure() with error message if invalid
    """
    resource_type = input_dict.get("type")
    id_input = input_dict.get("input")
    
    if not resource_type:
        return ValidationResult.failure("Resource type was not provided")
    if not id_input:
        return ValidationResult.failure(f"{resource_type} was not provided")
    
    resource_config = RESOURCE_IDENTIFIER_CONFIG.get(resource_type)
    if not resource_config:
        return ValidationResult.failure(f"Invalid resource type: {resource_type}")
    
    min_length = resource_config["min_length"]
    max_length = resource_config["max_length"]
    resource_name = resource_type.replace("_", " ").title()
    gid_prefix = resource_config["gid_prefix"]
    
    if is_url(id_input):
        if not id_input.startswith(SHOPIFY_ADMIN_BASE_URL):
            return ValidationResult.failure(f"Invalid {resource_name} URL format")
        digits_only = id_input.split("/")[-1]
    elif id_input.startswith(SHOPIFY_GID_BASE):
        expected_gid_prefix = f"{SHOPIFY_GID_BASE}{gid_prefix}/"
        if not id_input.startswith(expected_gid_prefix):
            return ValidationResult.failure(f"Invalid {resource_name} GID format")
        digits_only = id_input.split("/")[-1]
    else:
        digits_only = id_input
    
    if not is_integer(digits_only):
        return ValidationResult.failure(f"{resource_name} must be numeric")
    
    string_length = len(digits_only)
    if not is_between(string_length, min_length, max_length):
        return ValidationResult.failure(f"{resource_name} must be {min_length}-{max_length} digits")

    return ValidationResult.success(digits_only)

