"""Products domain service. Flat module-level async functions, no class."""

from core.clients import shopify
from lib.clients.shopify.generated.products_get import ProductsGetProductsNodes


async def get_product(product_id: int) -> ProductsGetProductsNodes:
    """Fetch a single product by numeric ID. Raises if not found."""
    result = await shopify.products_get(query=f"id:{product_id}", first=1)
    if not result.products.nodes:
        raise ValueError(f"Product not found: {product_id}")
    if len(result.products.nodes) > 1:
        raise ValueError(f"Multiple products found: {product_id}")
    return result.products.nodes[0]


async def find_products(handle: str | None) -> list[ProductsGetProductsNodes]:
    result = await shopify.products_get(query=f"handle:{handle}", first=10)
    return result.products.nodes
