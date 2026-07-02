# REFERENCE ONLY — this file's contents were commented out on 2026-07-01.
# To reactivate: strip leading '# ' from every line below this header.
# Original path: backend/modules/integrations/shopify/services/shopify_normalizers.py
#
# from typing import Any, Dict, Optional
# from validator_collection import is_between, is_integer, is_string, is_url
# 
# from config import config
# import logging
# 
# logger = logging.getLogger(__name__)
# 
# 
# def _get_shopify_admin_url() -> str:
#     """Get Shopify admin URL with safe access."""
#     shopify = config.shopify
#     if shopify and shopify.url:
#         return shopify.url.admin
#     import os
#     return os.getenv("SHOPIFY.URL.ADMIN", "")
# 
# 
# SHOPIFY_ADMIN_BASE_URL = _get_shopify_admin_url()
# SHOPIFY_GID_BASE = "gid://shopify/"
# 
# RESOURCE_IDENTIFIER_CONFIG = {
#     "order_id": {
#         "url_slugs": ["orders"],
#         "gid_prefix": "Order",
#         "id_field": "order_id",
#         "id_field_2": "order_number",
#         "min_length": 10,
#         "max_length": 15,
#     },
#     "order_number": {
#         "url_slugs": ["orders"],
#         "gid_prefix": "Order",
#         "id_field": "name",
#         "min_length": 4,
#         "max_length": None,
#     },
#     "product": {
#         "url_slugs": ["products"],
#         "gid_prefix": "Product",
#         "id_field": "product_id",
#         "min_length": 8,
#         "max_length": 20,
#     },
#     "customer": {
#         "url_slugs": ["customers"],
#         "gid_prefix": "Customer",
#         "id_field": "customer_id",
#         "min_length": 8,
#         "max_length": 20,
#     },
#     "variant": {
#         "url_slugs": ["products", "variants"],
#         "gid_prefix": "ProductVariant",
#         "id_field": "variant_id",
#         "min_length": 8,
#         "max_length": 20,
#     },
#     "transaction": {
#         "url_slugs": ["transactions"],
#         "gid_prefix": "Transaction",
#         "id_field": "transaction_id",
#         "min_length": 8,
#         "max_length": 20,
#     },
# }
# 
# 
# def build_shopify_resource_url(input_dict: Dict[str, str], resource_config: Dict[str, Any]) -> Optional[str]:
#     """Build Shopify admin URL for a given resource type and ID."""
#     resource_id = input_dict.get("input")
#     if not resource_id:
#         return None
# 
#     product_input = input_dict.get("product_input")
#     base_url = _get_shopify_admin_url()
#     url_parts = [base_url]
#     url_slugs = resource_config["url_slugs"]
# 
#     if input_dict.get("type") == "variant" and product_input:
#         url_parts.extend([url_slugs[0], product_input, url_slugs[1]])
#     else:
#         url_parts.extend(url_slugs)
# 
#     url_parts.append(resource_id)
#     return "/".join(url_parts)
# 
# 
# def _extract_order_number_digits(order_number: Optional[str]) -> Optional[str]:
#     """Extract digits from order number, returning None if invalid."""
#     if order_number is None:
#         return None
#     if is_url(order_number):
#         return None
#     if order_number.startswith("gid://"):
#         return None
# 
#     digits_only = order_number.lstrip("#")
#     string_length = len(digits_only)
# 
#     if not is_integer(digits_only) or not is_between(string_length, 4, 8):
#         return None
# 
#     return digits_only
# 
# 
# def normalize_order_number(order_number_input: Optional[str]) -> Optional[Dict[str, str]]:
#     """Normalize order number to a dict with with_hash and digits_only."""
#     digits_only = _extract_order_number_digits(order_number_input)
#     if digits_only is None:
#         return None
#     return {"digits_only": digits_only, "with_hash": f"#{digits_only}"}
# 
# 
# def _extract_resource_digits(input_dict: Dict[str, str]) -> Optional[str]:
#     """Extract digits from a Shopify resource identifier, returning None if invalid."""
#     resource_type = input_dict.get("type")
#     id_input = input_dict.get("input")
# 
#     if not resource_type or not id_input:
#         return None
# 
#     resource_config = RESOURCE_IDENTIFIER_CONFIG.get(resource_type)
#     if not resource_config:
#         return None
# 
#     min_length = resource_config["min_length"]
#     max_length = resource_config["max_length"]
#     gid_prefix = resource_config["gid_prefix"]
# 
#     if is_url(id_input):
#         if not id_input.startswith(SHOPIFY_ADMIN_BASE_URL):
#             return None
#         digits_only = id_input.split("/")[-1]
#     elif id_input.startswith(SHOPIFY_GID_BASE):
#         expected_gid_prefix = f"{SHOPIFY_GID_BASE}{gid_prefix}/"
#         if not id_input.startswith(expected_gid_prefix):
#             return None
#         digits_only = id_input.split("/")[-1]
#     else:
#         digits_only = id_input
# 
#     if not is_integer(digits_only):
#         return None
# 
#     string_length = len(digits_only)
#     if not is_between(string_length, min_length, max_length):
#         return None
# 
#     return digits_only
# 
# 
# def normalize_shopify_resource_identifier(input_dict: Dict[str, str], resource_config: Dict[str, Any]) -> Optional[Dict[str, Optional[str]]]:
#     """Normalize a Shopify resource identifier to a dict with digits_only and gid."""
#     digits_only = _extract_resource_digits(input_dict)
#     if digits_only is None or not is_string(digits_only):
#         return None
# 
#     gid_prefix = resource_config["gid_prefix"]
#     return {
#         "digits_only": digits_only,
#         "gid": f"{SHOPIFY_GID_BASE}{gid_prefix}/{digits_only}",
#     }
# 
# 
# def normalize_order_identifier(order_id_input: str) -> Optional[Dict[str, Optional[str]]]:
#     """Normalize an order id."""
#     resource_config = RESOURCE_IDENTIFIER_CONFIG.get("order_id")
#     if not resource_config:
#         return None
# 
#     result = normalize_shopify_resource_identifier({"type": "order_id", "input": order_id_input}, resource_config)
#     if not result:
#         return None
# 
#     input_dict = {"type": "order_id", "input": result["digits_only"]}
#     url = build_shopify_resource_url(input_dict, resource_config)
#     return {**result, "url": url}
# 
# 
# def normalize_product_identifier(product_id_input: str) -> Optional[Dict[str, Optional[str]]]:
#     """Normalize a product id."""
#     resource_config = RESOURCE_IDENTIFIER_CONFIG.get("product")
#     if not resource_config:
#         return None
# 
#     result = normalize_shopify_resource_identifier({"type": "product", "input": product_id_input}, resource_config)
#     if not result:
#         return None
# 
#     input_dict = {"type": "product", "input": result["digits_only"]}
#     url = build_shopify_resource_url(input_dict, resource_config)
#     return {**result, "url": url}
# 
# 
# def normalize_customer_identifier(customer_id_input: str) -> Optional[Dict[str, Optional[str]]]:
#     """Normalize a customer id."""
#     resource_config = RESOURCE_IDENTIFIER_CONFIG.get("customer")
#     if not resource_config:
#         return None
# 
#     result = normalize_shopify_resource_identifier({"type": "customer", "input": customer_id_input}, resource_config)
#     if not result:
#         return None
# 
#     input_dict = {"type": "customer", "input": result["digits_only"]}
#     url = build_shopify_resource_url(input_dict, resource_config)
#     return {**result, "url": url}
# 
# 
# def normalize_transaction_identifier(transaction_id_input: str) -> Optional[Dict[str, Optional[str]]]:
#     """Normalize a transaction id."""
#     resource_config = RESOURCE_IDENTIFIER_CONFIG.get("transaction")
#     if not resource_config:
#         return None
# 
#     result = normalize_shopify_resource_identifier({"type": "transaction", "input": transaction_id_input}, resource_config)
#     if not result:
#         return None
# 
#     input_dict = {"type": "transaction", "input": result["digits_only"]}
#     url = build_shopify_resource_url(input_dict, resource_config)
#     return {**result, "url": url}
# 
# 
# def normalize_variant_identifier(variant_id_input: str, product_id_input: Optional[str] = None) -> Optional[Dict[str, Optional[str]]]:
#     """Normalize a variant id."""
#     resource_config = RESOURCE_IDENTIFIER_CONFIG.get("variant")
#     if not resource_config:
#         return None
# 
#     result = normalize_shopify_resource_identifier({"type": "variant", "input": variant_id_input}, resource_config)
#     if not result:
#         return None
# 
#     if product_id_input:
#         input_dict = {"type": "variant", "input": result["digits_only"], "product_input": product_id_input}
#         url = build_shopify_resource_url(input_dict, resource_config)
#         return {**result, "url": url}
# 
#     return result
