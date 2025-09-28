from typing import Dict, Optional

from typing import Optional, Dict
from backend.utils.validators import (
    validate_shopify_order_number_format,
    validate_shopify_order_id_format,
    validate_shopify_product_id_format,
    validate_shopify_customer_id_format,
    validate_shopify_transaction_id_format,
    validate_shopify_variant_id_format,
)

def normalize_order_id(order_id_input: Optional[str]) -> Optional[Dict[str, str]]:
    """Normalize order id to a dict with digits_only and gid"""
    if not order_id_input or not validate_shopify_order_id_format(order_id_input).get("success"):
        return None
    digits_only = order_id_input.split("/")[-1] if order_id_input.startswith("gid://") else order_id_input
    return {"digits_only": digits_only, "gid": f"gid://shopify/Order/{digits_only}"}

def normalize_order_number(order_number_input: Optional[str]) -> Optional[Dict[str, str]]:
    """Normalize order number to a dict with with_hash and digits_only"""
    if not order_number_input or not validate_shopify_order_number_format(order_number_input).get("success"):
        return None
    hash = order_number_input if order_number_input.startswith("#") else f"#{order_number_input}"
    return {"digits_only": hash.replace("#", ""), "hash": hash}

def normalize_product_id(product_id_input: Optional[str]) -> Optional[Dict[str,str]]:
    """Normalize a product id"""
    if not product_id_input or not validate_shopify_product_id_format(product_id_input).get("success"):
        return None
    if product_id_input.startswith("gid://"):
        digits_only = product_id_input.split("/")[-1]
    else:
        digits_only = product_id_input
    return {
        "digits_only": digits_only,
        "gid": f"gid://shopify/Product/{digits_only}"
    }   

def normalize_customer_id(customer_id_input: Optional[str]) -> Optional[Dict[str,str]]:
    """Normalize a customer id"""
    if not customer_id_input or not validate_shopify_customer_id_format(customer_id_input).get("success"):
        return None
    if customer_id_input.startswith("gid://"):
        digits_only = customer_id_input.split("/")[-1]
    else:
        digits_only = customer_id_input
    return {
        "digits_only": digits_only,
        "gid": f"gid://shopify/Customer/{digits_only}"
    }

def normalize_transaction_id(transaction_id_input: Optional[str]) -> Optional[Dict[str,str]]:
    """Normalize a transaction id (numeric or GID)"""
    if not transaction_id_input or not validate_shopify_transaction_id_format(transaction_id_input).get("success"):
        return None
    digits_only = transaction_id_input.split("/")[-1] if transaction_id_input.startswith("gid://") else transaction_id_input
    return {"digits_only": digits_only, "gid": f"gid://shopify/Transaction/{digits_only}"}

def normalize_variant_id(variant_id_input: Optional[str]) -> Optional[Dict[str,str]]:
    """Normalize a variant id (numeric or GID)"""
    if not variant_id_input or not validate_shopify_variant_id_format(variant_id_input).get("success"):
        return None
    digits_only = variant_id_input.split("/")[-1] if variant_id_input.startswith("gid://") else variant_id_input
    return {"digits_only": digits_only, "gid": f"gid://shopify/Variant/{digits_only}"}