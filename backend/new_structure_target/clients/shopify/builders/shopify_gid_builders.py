def build_product_gid(product_id: str) -> str:
    """Build a product GID"""
    return f"gid://shopify/Product/{product_id}"

def build_order_gid(order_id: str) -> str:
    """Build a order GID"""
    return f"gid://shopify/Order/{order_id}"

def build_customer_gid(customer_id: str) -> str:
    """Build a customer GID"""
    return f"gid://shopify/Customer/{customer_id}"

def build_transaction_gid(transaction_id: str) -> str:
    """Build a transaction GID"""
    return f"gid://shopify/Transaction/{transaction_id}"

def build_variant_gid(variant_id: str) -> str:
    """Build a variant GID"""
    return f"gid://shopify/Variant/{variant_id}"