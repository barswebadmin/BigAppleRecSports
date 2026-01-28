"""
Shopify management commands for bars-cli.

Command structure:
- bars shopify customer * / bars shopify customers *
- bars shopify order * / bars shopify orders *
- bars shopify product * / bars shopify products *
- bars shopify page * / bars shopify pages *
"""
import click
from click_aliases import ClickAliasedGroup

from .customers.get import get_customer_cmd
from .customers.update import update_customer_cmd
from .orders.get import get_order_cmd
from .orders.cancel import cancel_order_cmd
from .orders.refund import refund_order_cmd
from .orders.apply_discount import apply_discount_cmd
from .orders.restock import restock_cmd
from .products.get import get_product_cmd
from .products.orders import product_orders_cmd
from .products.update_inventory import update_inventory_cmd
from .pages import page_group
from .webhooks import shopify_webhooks


@click.group(
    cls=ClickAliasedGroup,
    context_settings={"ignore_unknown_options": True}
)
@click.pass_context
def shopify(ctx: click.Context):
    """Shopify management commands."""
    # Service is lazily initialized on first access via ctx.meta['shopify_service']
    pass


# Register subcommands
# Create order group and add get command to it
@click.group('orders')
@click.pass_context
def order_group(ctx: click.Context):
    """Order management commands."""
    pass

order_group.add_command(get_order_cmd, 'get')
order_group.add_command(cancel_order_cmd, 'cancel')
order_group.add_command(refund_order_cmd, 'refund')
order_group.add_command(apply_discount_cmd, 'apply-discount')
order_group.add_command(restock_cmd, 'restock')

# Create customer group and add get command to it
@click.group('customers')
@click.pass_context
def customer_group(ctx: click.Context):
    """Customer management commands."""
    pass

customer_group.add_command(get_customer_cmd, 'get')
customer_group.add_command(update_customer_cmd, 'update')

@click.group('products')
@click.pass_context
def product_group(ctx: click.Context):
    """Product management commands."""
    pass

product_group.add_command(get_product_cmd, 'get')
product_group.add_command(product_orders_cmd, 'orders')
product_group.add_command(update_inventory_cmd, 'update-inventory')

# Register groups with aliases using click-aliases
shopify.add_command(customer_group, 'customers', aliases=['customer'])
shopify.add_command(order_group, 'orders', aliases=['order'])
shopify.add_command(product_group, 'products', aliases=['product'])
shopify.add_command(page_group, 'pages', aliases=['page'])
shopify.add_command(shopify_webhooks, 'webhooks', aliases=['webhook'])

