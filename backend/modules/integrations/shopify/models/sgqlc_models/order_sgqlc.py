"""
Direct sgqlc Type definitions for Order models.

These are separate from Pydantic models and defined directly using sgqlc's Type system.
"""

from sgqlc.types import Type, Field, String, Int, list_of
from sgqlc.types.relay import Connection, connection_args

# Import Customer for Order.customer field
from backend.modules.integrations.shopify.models.sgqlc_models.customer_sgqlc import Customer


class MoneySet(Type):
    """Money set with shop and presentment money."""
    amount = Field(String)
    currencyCode = Field(String)


class MoneySetWrapper(Type):
    """Wrapper for money sets."""
    shopMoney = Field(MoneySet)
    presentmentMoney = Field(MoneySet)


class InventoryItem(Type):
    """Inventory item model."""
    id = Field(String)


class LineItemVariant(Type):
    """Variant model for line items."""
    id = Field(String)
    title = Field(String)
    displayName = Field(String)
    price = Field(String)
    sku = Field(String)
    inventoryQuantity = Field(Int)
    inventoryItem = Field(InventoryItem)


class CustomAttribute(Type):
    """Custom attribute key-value pair."""
    key = Field(String)
    value = Field(String)


class DiscountApplication(Type):
    """Discount application model (union type - use inline fragments)."""
    # Union type fields - select using inline fragments in queries
    # Common fields that may exist on some variants
    pass


class LineItem(Type):
    """Line item model for Shopify orders."""
    id = Field(String)
    name = Field(String)
    title = Field(String)
    quantity = Field(Int)
    fulfillableQuantity = Field(Int)
    fulfillmentStatus = Field(String)
    originalUnitPriceSet = Field(MoneySetWrapper)
    discountedUnitPriceSet = Field(MoneySetWrapper)
    originalTotalSet = Field(MoneySetWrapper)
    discountedTotalSet = Field(MoneySetWrapper)
    customAttributes = Field(list_of(CustomAttribute))
    product = Field('Product')  # Forward reference to Product type
    variant = Field(LineItemVariant)


class RefundLineItem(Type):
    """Refund line item model."""
    quantity = Field(Int)
    restockType = Field(String)
    lineItem = Field(LineItem)


class RefundTransaction(Type):
    """Transaction within a refund."""
    id = Field(String)
    kind = Field(String)
    status = Field(String)
    amount = Field(String)
    gateway = Field(String)
    createdAt = Field(String)


class BillingAddress(Type):
    """Billing address model for orders."""
    firstName = Field(String)
    lastName = Field(String)
    address1 = Field(String)
    address2 = Field(String)
    city = Field(String)
    province = Field(String)
    zip = Field(String)
    country = Field(String)
    phone = Field(String)


class ShippingAddress(Type):
    """Shipping address model for orders."""
    firstName = Field(String)
    lastName = Field(String)
    address1 = Field(String)
    address2 = Field(String)
    city = Field(String)
    province = Field(String)
    zip = Field(String)
    country = Field(String)
    phone = Field(String)


class Transaction(Type):
    """Transaction model for Shopify orders."""
    id = Field(String)
    kind = Field(String)
    gateway = Field(String)
    status = Field(String)
    amount = Field(String)
    createdAt = Field(String)
    parentTransaction = Field('Transaction')  # Self-reference


class Refund(Type):
    """Refund model for Shopify orders."""
    id = Field(String)
    createdAt = Field(String)
    note = Field(String)
    totalRefundedSet = Field(MoneySetWrapper)
    refundLineItems = Field('RefundLineItemConnection', args=connection_args())  # Forward reference with connection args
    transactions = Field('RefundTransactionConnection', args=connection_args())  # Connection with connection args


class Order(Type):
    """Order sgqlc Type."""
    id = Field(String)
    name = Field(String)
    email = Field(String)
    phone = Field(String)
    createdAt = Field(String)
    updatedAt = Field(String)
    cancelledAt = Field(String)
    cancelReason = Field(String)
    displayFinancialStatus = Field(String)
    displayFulfillmentStatus = Field(String)
    subtotalLineItemsQuantity = Field(Int)
    totalPriceSet = Field(MoneySetWrapper)
    discountApplications = Field('DiscountApplicationConnection', args=connection_args())  # Forward reference with connection args
    refunds = Field(list_of(Refund))
    transactions = Field(list_of(Transaction))
    lineItems = Field('LineItemConnection', args=connection_args())  # Forward reference with connection args
    customer = Field(Customer)  # Direct Customer object, not a Connection
    billingAddress = Field(BillingAddress)
    shippingAddress = Field(ShippingAddress)


class LineItemConnection(Connection):
    """LineItem Connection type."""
    nodes = list_of(LineItem)


class DiscountApplicationConnection(Connection):
    """DiscountApplication Connection type."""
    nodes = list_of(DiscountApplication)


class RefundLineItemConnection(Connection):
    """RefundLineItem Connection type."""
    nodes = list_of(RefundLineItem)


class RefundTransactionConnection(Connection):
    """RefundTransaction Connection type."""
    nodes = list_of(RefundTransaction)


class OrderConnection(Connection):
    """Order Connection type."""
    nodes = list_of(Order)

