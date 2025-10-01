from typing import Optional

def build_shopify_gid(type: Optional[str], id: Optional[str]) -> str:
    if not type or not id:
        raise ValueError("type and id must be provided")
    if type not in ["product", "variant", "order", "customer", "invoice", "line_item", "tax_line", "shipping_line", "payment", "fulfillment", "transaction"]:
        raise ValueError(f"Invalid type: {type}")
    if not id.isdigit():
        raise ValueError(f"Invalid id: {id}")
    return f"gid://shopify/{type}/{id}"