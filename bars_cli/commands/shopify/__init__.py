"""
Shopify management commands for bars-cli.

Command structure:
- bars shopify customer * / bars shopify customers *
- bars shopify order * / bars shopify orders *
- bars shopify product * / bars shopify products *
- bars shopify page * / bars shopify pages *
"""
import click_extra as click

from .customers import customers_group
from .orders import orders_group
from .products import products_group
from .pages import pages_group
from .webhooks import shopify_webhooks


@click.group(
    context_settings={"ignore_unknown_options": True}
)
@click.pass_context
def shopify_grp(ctx: click.Context):
    """Shopify management commands."""
    # Initialize shopify_service once in meta (shared across all contexts)
    # Override LazyServiceProxy from main.py with actual service instance
    from bars_cli._core.context import LazyServiceProxy
    if 'shopify_service' not in ctx.meta or isinstance(ctx.meta.get('shopify_service'), LazyServiceProxy):
        try:
            from bars_cli.backend_services.shopify.services import ShopifyService
            # Get environment from ctx.obj (set by main CLI)
            environment = ctx.obj.get('environment', 'production') if ctx.obj else 'production'
            ctx.meta['shopify_service'] = ShopifyService(environment=environment)
        except (RuntimeError, Exception) as e:
            # Store error in meta so commands can show helpful messages
            ctx.meta['shopify_service_error'] = str(e)
            ctx.meta['shopify_service'] = None


# Register groups with aliases
shopify_grp.add_command(customers_group)
shopify_grp.add_command(orders_group)
shopify_grp.add_command(products_group)
shopify_grp.add_command(pages_group)
shopify_grp.add_command(shopify_webhooks)


__all__ = ["shopify_grp"]

# Export as shopify_group for main.py compatibility
shopify_group = shopify_grp

