from typing import Dict, Optional

from backend.utils.validators import validate_shopify_order_number_format

def normalize_order_id(order_id_input: str) -> Dict[str,str]:
    """Normalize a order id"""
    
    if order_id_input.startswith("gid://"):
        digits_only = order_id_input.split("/")[-1]
    else:
        digits_only = order_id_input
    return {
        "digits_only": digits_only,
        "gid": f"gid://shopify/Order/{digits_only}"
    }

def normalize_order_number(order_number_input: str) -> Optional[Dict[str,str]]:
    """Normalize a order number"""
    if not validate_shopify_order_number_format(order_number_input).get("success"):
        return None
    if order_number_input.startswith("#"):
        normalized = order_number_input
    else:
        normalized = f"#{order_number_input}"
    return {
        "with_hash": normalized,
        "digits_only": normalized.replace("#", "")
    }

def normalize_product_id(product_id_input: str) -> Dict[str,str]:
    """Normalize a product id"""
    if product_id_input.startswith("gid://"):
        digits_only = product_id_input.split("/")[-1]
    else:
        digits_only = product_id_input
    return {
        "digits_only": digits_only,
        "gid": f"gid://shopify/Product/{digits_only}"
    }   
def normalize_customer_id(customer_id_input: str) -> Dict[str,str]:
    """Normalize a customer id"""
    if customer_id_input.startswith("gid://"):
        digits_only = customer_id_input.split("/")[-1]
    else:
        digits_only = customer_id_input
    return {
        "digits_only": digits_only,
        "gid": f"gid://shopify/Customer/{digits_only}"
    }

def normalize_transaction_id(transaction_id_input: str) -> Dict[str,str]:
    """Normalize a transaction id"""
    if transaction_id_input.startswith("gid://"):
        digits_only = transaction_id_input.split("/")[-1]
    else:
        digits_only = transaction_id_input
    return {
        "digits_only": digits_only,
        "gid": f"gid://shopify/Transaction/{digits_only}"
    }

def normalize_variant_id(variant_id_input: str) -> Dict[str,str]:
    """Normalize a variant id"""
    if variant_id_input.startswith("gid://"):
        digits_only = variant_id_input.split("/")[-1]
    else:
        digits_only = variant_id_input
    return {
        "digits_only": digits_only,
        "gid": f"gid://shopify/Variant/{digits_only}"
    }