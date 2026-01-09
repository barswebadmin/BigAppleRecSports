"""
SGQLC Order models for Shopify GraphQL API.
"""

from typing import TYPE_CHECKING
from sgqlc.types import Type, Field, String, Int, list_of
from sgqlc.types.relay import Connection, connection_args

if TYPE_CHECKING:
    from .customer import CustomerConnection


class MoneySet(Type):
    """Money set with shop and presentment money."""
    amount = String
    currencyCode = String


class MoneySetWrapper(Type):
    """Wrapper for money sets (shopMoney and presentmentMoney)."""
    shopMoney = MoneySet
    presentmentMoney = MoneySet


class RefundTransaction(Type):
    """Transaction within a refund."""
    id = String
    kind = String
    status = String
    amount = String
    gateway = String
    createdAt = String


class RefundTransactionConnection(Connection):
    """Refund transaction connection."""
    nodes = list_of(RefundTransaction)


class Refund(Type):
    """Refund model for Shopify orders."""
    id = String
    createdAt = String
    note = String
    totalRefundedSet = MoneySetWrapper
    refundLineItems = Field('RefundLineItemConnection', args=connection_args())
    transactions = Field(RefundTransactionConnection, args=connection_args())


class LineItemReference(Type):
    """Line item reference (simplified - just id, name, title)."""
    id = String
    name = String
    title = String


class RefundLineItem(Type):
    """Refund line item model."""
    quantity = Int
    restockType = String
    lineItem = LineItemReference


class RefundLineItemConnection(Connection):
    """Refund line item connection."""
    nodes = list_of(RefundLineItem)


class Transaction(Type):
    """Transaction model for Shopify orders."""
    id = String
    kind = String
    gateway = String
    status = String
    amount = String
    createdAt = String
    parentTransaction = Field('Transaction')  # Recursive reference - parentTransaction is also a Transaction


class TransactionConnection(Connection):
    """Transaction connection."""
    nodes = list_of(Transaction)


class CustomAttribute(Type):
    """Custom attribute key-value pair."""
    key = String
    value = String


class InventoryItem(Type):
    """Inventory item reference (just contains id)."""
    id = String


class LineItemVariant(Type):
    """Variant model for line items."""
    id = String
    title = String
    displayName = String
    price = String
    sku = String
    inventoryQuantity = Int
    inventoryItem = InventoryItem


class DiscountApplication(Type):
    """Discount application model (union of DiscountCodeApplication, ScriptDiscountApplication, AutomaticDiscountApplication)."""
    code = String  # For DiscountCodeApplication
    title = String  # For ScriptDiscountApplication and AutomaticDiscountApplication


class DiscountApplicationConnection(Connection):
    """Discount application connection."""
    nodes = list_of(DiscountApplication)


class LineItem(Type):
    """Line item model for Shopify orders."""
    id = String
    name = String
    title = String
    quantity = Int
    fulfillableQuantity = Int
    fulfillmentStatus = String
    originalUnitPriceSet = MoneySetWrapper
    discountedUnitPriceSet = MoneySetWrapper
    originalTotalSet = MoneySetWrapper
    discountedTotalSet = MoneySetWrapper
    customAttributes = list_of(CustomAttribute)
    # product = Field('Product')  # Product object - needs explicit field selection (commented out until Product type is defined)
    variant = LineItemVariant


class LineItemConnection(Connection):
    """Line item connection."""
    nodes = list_of(LineItem)


class Order(Type):
    """Complete order model with type safety."""
    id = String
    name = String
    email = String
    phone = String
    createdAt = String
    cancelledAt = String
    cancelReason = String
    totalPriceSet = MoneySetWrapper
    # discountApplications = Field(DiscountApplicationConnection, args=connection_args()) # Union type, need to figure out how to handle it
    refunds = list_of(Refund)
    transactions = list_of(Transaction)
    lineItems = Field(LineItemConnection, args=connection_args())
    customer = Field('Customer')


class OrderConnection(Connection):
    """Order connection with nodes."""
    nodes = list_of(Order)

