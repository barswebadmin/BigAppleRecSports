"""Get Shopify product details command."""
from typing import Dict, Any, Optional, List, TYPE_CHECKING, TypedDict, Callable

import click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SHOPIFY_PRODUCT_IDENTIFIER
from bars_cli.backend_services.shopify.models.sgqlc_models import Product

if TYPE_CHECKING:
    from sgqlc.types import Type as SGQLCType
    ProductSGQLCType = SGQLCType
else:
    ProductSGQLCType = Any


# ============================================================================
# Display Functions (Now Type-Safe)
# ============================================================================

class ProductDisplayField(TypedDict):
    """Type definition for product display field configuration."""
    field_name: str
    display_label: str
    default: Optional[str]
    formatter: Optional[Callable[[Any], str]]


product_display_fields: List[ProductDisplayField] = [
    {"field_name": "id", "display_label": "ID", "default": None, "formatter": None},
    {"field_name": "title", "display_label": "Title", "default": "N/A", "formatter": None},
    {"field_name": "handle", "display_label": "Handle", "default": "N/A", "formatter": None},
    {"field_name": "productType", "display_label": "Type", "default": "N/A", "formatter": None},
    {"field_name": "vendor", "display_label": "Vendor", "default": "N/A", "formatter": None},
    {"field_name": "status", "display_label": "Status", "default": "N/A", "formatter": None},
    {"field_name": "createdAt", "display_label": "Created", "default": "N/A", "formatter": None},
    {"field_name": "updatedAt", "display_label": "Updated", "default": "N/A", "formatter": None},
]


def format_product(product: Any) -> str:
    """Format product data for display."""
    output = []
    output.append("\n✅ Product Found!")
    output.append("=" * 60)
    
    for field_config in product_display_fields:
        field_name = field_config["field_name"]
        display_label = field_config["display_label"]
        default = field_config["default"]
        formatter = field_config["formatter"]
        
        if formatter:
            value = formatter(product)
        else:
            value = getattr(product, field_name, None)  # type: ignore[attr-defined]
            if value is None:
                value = default
            else:
                value = str(value)
        
        output.append(f"{display_label:<15} {value}")
    
    # Display tags
    if hasattr(product, 'tags') and product.tags:  # type: ignore[attr-defined]
        tags_list = list(product.tags)  # type: ignore[attr-defined]
        if tags_list:
            output.append(f"\nTags ({len(tags_list)}):")
            for tag in tags_list:
                output.append(f"  • {tag}")
    
    # Display variants
    if hasattr(product, 'variants') and product.variants:  # type: ignore[attr-defined]
        variants_conn = product.variants  # type: ignore[attr-defined]
        variants = variants_conn.nodes if hasattr(variants_conn, 'nodes') else []  # type: ignore[attr-defined]
        if variants:
            output.append(f"\nVariants ({len(variants)}):")
            for variant in variants:
                title = getattr(variant, 'title', 'N/A')  # type: ignore[attr-defined]
                price = getattr(variant, 'price', 'N/A')  # type: ignore[attr-defined]
                inventory = getattr(variant, 'inventoryQuantity', 'N/A')  # type: ignore[attr-defined]
                output.append(f"  • {title} - ${price} (qty: {inventory})")
    
    output.append("=" * 60)
    return '\n'.join(output)


def _format_product_option(product: Any) -> str:
    """Format product for display in selection options."""
    title = getattr(product, 'title', 'N/A')  # type: ignore[attr-defined]
    handle = getattr(product, 'handle', 'N/A')  # type: ignore[attr-defined]
    return f"{title} ({handle})"


def handle_multiple_results(products: List[Any], json_output: bool, should_display: bool, must_return_one: bool = False) -> Optional[Any]:
    """Handle selection when multiple products are found.
    
    Args:
        products: List of product objects
        json_output: Whether to output JSON format
        should_display: Whether to display output
        must_return_one: If True, requires selecting exactly one product (no "All" option)
        
    Returns:
        Selected product object, list of all products if "All" selected, or None if cancelled
    """
    from bars_cli.commands.shopify._shared.command_helpers import handle_multiple_shopify_results
    return handle_multiple_shopify_results(
        items=products,
        json_output=json_output,
        should_display=should_display,
        format_option_func=_format_product_option,
        entity_name="product",
        must_return_one=must_return_one
    )


@click.command('get')
@handle_display_options(display=True, exit_on_error=True)
@click.option('--one', 'must_return_one', is_flag=True, default=False, help='Require selecting exactly one product (no "All" option)')
@click.argument('identifier', type=SHOPIFY_PRODUCT_IDENTIFIER, required=False)
@click.pass_context
def get_product_cmd(ctx: click.Context, identifier: Optional[Dict[str, Any]], must_return_one: bool = False) -> Optional[List[Any]]:
    """
    Get Shopify product details by product ID or handle.
    
    IDENTIFIER: Product ID (gid://shopify/Product/123 or 123) or product handle.
    
    Examples:
      bars shopify product get 123456789
      bars shopify product get gid://shopify/Product/123456789
      bars shopify product get 2025-fall-kickball-sunday-open-division
      bars --json shopify product get 123456789
    """
    from bars_cli.commands.shopify._shared.command_helpers import handle_shopify_get_command
    
    # Service is guaranteed to be available (initialized in shopify group)
    shopify_service = ctx.meta.get('shopify_service')
    
    return handle_shopify_get_command(
        ctx=ctx,
        identifier=identifier,
        service_method=shopify_service.get_product_by_identifier,  # type: ignore[attr-defined]
        entity_name="product",
        format_func=format_product,
        handle_multiple_func=(handle_multiple_results, {"must_return_one": must_return_one}),
        service_method_kwargs={"variants_first": 5},
        identifier_required_msg="Product identifier is required"
    )

