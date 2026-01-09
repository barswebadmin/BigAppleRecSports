"""
Shopify management commands for bars-cli.

Command structure:
- bars shopify customer *
- bars shopify order *
- bars shopify product *
"""
import click

from .customers.get_customer_cmd import get_customer_cmd
from .orders.get_order_cmd import get_order_cmd
from .products.get_product_cmd import get_product_cmd


@click.group(
    context_settings={"ignore_unknown_options": True}
)
@click.pass_context
def shopify(ctx: click.Context):
    """Shopify management commands."""
    # Initialize ShopifyService once in meta (shared across all contexts)
    if 'shopify_service' not in ctx.meta:
        create_service = ctx.meta.get('_create_shopify_service')
        if not create_service:
            raise click.ClickException(
                "Shopify service creation callback not found. This is a bug - callbacks should be initialized in context."
            )
        # Callback raises exception on failure - fail early
        ctx.meta['shopify_service'] = create_service()


# Register subcommands
# Create order group and add get command to it
@click.group('orders')
@click.pass_context
def order_group(ctx: click.Context):
    """Order management commands."""
    pass

order_group.add_command(get_order_cmd, 'get')

# Create customer group and add get command to it
@click.group('customers')
@click.pass_context
def customer_group(ctx: click.Context):
    """Customer management commands."""
    pass

customer_group.add_command(get_customer_cmd, 'get')

@click.group('products')
@click.pass_context
def product_group(ctx: click.Context):
    """Product management commands."""
    pass

product_group.add_command(get_product_cmd, 'get')

# Register groups
shopify.add_command(customer_group)
shopify.add_command(order_group)
shopify.add_command(product_group)

