"""
SGQLC Type definitions for Shopify GraphQL mutations.

Defines types for orderCancel and refundCreate mutations.
"""

from sgqlc.types import Type, Field, String, Boolean, ID, Int, list_of, Input, Enum
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    pass


# ============================================================================
# Enums
# ============================================================================

# Type alias for order cancellation reasons (for type hints)
CancelReasonType = Literal["CUSTOMER", "FRAUD", "INVENTORY", "DECLINED", "OTHER"]

class OrderCancelReason(Enum):
    """Order cancellation reason enum."""
    CUSTOMER = "CUSTOMER"
    FRAUD = "FRAUD"
    INVENTORY = "INVENTORY"
    DECLINED = "DECLINED"
    OTHER = "OTHER"

# Register enum choices with sgqlc schema
OrderCancelReason.__choices__ = ("CUSTOMER", "FRAUD", "INVENTORY", "DECLINED", "OTHER")


class CurrencyCode(Enum):
    """Currency code enum for Shopify."""
    USD = "USD"
    CAD = "CAD"
    EUR = "EUR"
    GBP = "GBP"
    # Add other currencies as needed

# Register enum choices with sgqlc schema
CurrencyCode.__choices__ = ("USD", "CAD", "EUR", "GBP")


class OrderTransactionKind(Enum):
    """Order transaction kind enum for Shopify."""
    SALE = "SALE"
    CAPTURE = "CAPTURE"
    AUTHORIZATION = "AUTHORIZATION"
    EMV_AUTHORIZATION = "EMV_AUTHORIZATION"
    REFUND = "REFUND"
    VOID = "VOID"
    CHANGE = "CHANGE"
    ECHECK_SALE = "ECHECK_SALE"
    ECHECK_CREDIT = "ECHECK_CREDIT"
    ECHECK_DEBIT = "ECHECK_DEBIT"
    # Add other transaction kinds as needed

# Register enum choices with sgqlc schema
OrderTransactionKind.__choices__ = ("SALE", "CAPTURE", "AUTHORIZATION", "EMV_AUTHORIZATION", "REFUND", "VOID", "CHANGE", "ECHECK_SALE", "ECHECK_CREDIT", "ECHECK_DEBIT")


# ============================================================================
# Input Types (using Input base class for mutation inputs)
# ============================================================================

class MoneyInput(Input):
    """Money input for refunds."""
    amount = String
    currencyCode = CurrencyCode


class StoreCreditRefund(Input):
    """Store credit refund input."""
    amount = MoneyInput


class RefundMethod(Input):
    """Refund method input."""
    storeCreditRefund = StoreCreditRefund


class TransactionInput(Input):
    """Transaction input for refunds."""
    orderId = ID
    gateway = String
    kind = OrderTransactionKind  # Transaction kind enum
    amount = String
    parentId = ID


class RefundInput(Input):
    """Input for refundCreate mutation."""
    notify = Boolean
    orderId = ID
    note = String
    refundMethods = list_of(RefundMethod)
    transactions = list_of(TransactionInput)


# ============================================================================
# Mutation Response Types
# ============================================================================

class Job(Type):
    """Job status for async operations."""
    id = Field(ID)
    done = Field(Boolean)


class UserError(Type):
    """User error from mutations."""
    field = Field(list_of(String))
    message = Field(String)


class OrderCancelUserError(Type):
    """Order cancel specific user error."""
    field = Field(list_of(String))
    message = Field(String)


class OrderCancelPayload(Type):
    """Response payload for orderCancel mutation."""
    job = Field(Job)
    orderCancelUserErrors = Field(list_of(OrderCancelUserError))
    userErrors = Field(list_of(UserError))


class RefundCreatePayload(Type):
    """Response payload for refundCreate mutation."""
    refund = Field('Refund')  # Forward reference to existing Refund type
    userErrors = Field(list_of(UserError))


# ============================================================================
# Order Editing Mutations
# ============================================================================

class CalculatedOrder(Type):
    """Calculated order from orderEditBegin."""
    id = Field(ID)


class OrderEditBeginPayload(Type):
    """Response payload for orderEditBegin mutation."""
    calculatedOrder = Field(CalculatedOrder)
    userErrors = Field(list_of(UserError))


class CalculatedLineItem(Type):
    """Calculated line item from CalculatedOrder."""
    id = Field(ID)
    title = Field(String)
    originalUnitPriceSet = Field('MoneySetWrapper')


class CalculatedLineItemConnection(Type):
    """Connection of calculated line items."""
    edges = Field(list_of('CalculatedLineItemEdge'))


class CalculatedLineItemEdge(Type):
    """Edge in calculated line item connection."""
    node = Field(CalculatedLineItem)


class CalculatedOrderNode(Type):
    """Node type for CalculatedOrder in node query."""
    id = Field(ID)
    lineItems = Field(CalculatedLineItemConnection, args={'first': 'Int'})


class OrderEditAddLineItemDiscountPayload(Type):
    """Response payload for orderEditAddLineItemDiscount mutation."""
    userErrors = Field(list_of(UserError))


class OrderEditCommitPayload(Type):
    """Response payload for orderEditCommit mutation."""
    userErrors = Field(list_of(UserError))


class OrderEditAppliedDiscountInput(Type):
    """Input for orderEditAddLineItemDiscount discount field."""
    description = Field(String)
    fixedValue = Field(MoneyInput)  # Reuse existing MoneyInput


# ============================================================================
# Inventory Mutations
# ============================================================================

class InventoryChange(Input):
    """Inventory change input."""
    delta = Int
    inventoryItemId = ID
    locationId = ID


class InventoryAdjustQuantitiesInput(Input):
    """Input for inventoryAdjustQuantities mutation."""
    reason = String
    name = String
    referenceDocumentUri = String
    changes = list_of(InventoryChange)


class InventoryAdjustmentGroup(Type):
    """Inventory adjustment group response."""
    createdAt = Field(String)
    reason = Field(String)
    referenceDocumentUri = Field(String)


class InventoryAdjustQuantitiesPayload(Type):
    """Response payload for inventoryAdjustQuantities mutation."""
    userErrors = Field(list_of(UserError))
    inventoryAdjustmentGroup = Field(InventoryAdjustmentGroup)


# ============================================================================
# Customer Update Mutations
# ============================================================================

class CustomerInput(Input):
    """Input for customerUpdate mutation."""
    email = String
    phone = String


class CustomerUpdateInput(Input):
    """Input wrapper for customerUpdate mutation."""
    id = ID
    customer = CustomerInput


class CustomerUpdatePayload(Type):
    """Response payload for customerUpdate mutation."""
    customer = Field('Customer')  # Forward reference to existing Customer type
    userErrors = Field(list_of(UserError))


# ============================================================================
# Mutation Root
# ============================================================================

class Mutation(Type):
    """Root mutation type for Shopify GraphQL API."""
    orderCancel = Field(
        OrderCancelPayload,
        args={
            'notifyCustomer': Boolean,
            'orderId': ID,
            'reason': OrderCancelReason,
            'refund': Boolean,
            'restock': Boolean,
            'staffNote': String
        }
    )
    refundCreate = Field(
        RefundCreatePayload,
        args={'input': RefundInput}
    )
    orderEditBegin = Field(
        OrderEditBeginPayload,
        args={'id': ID}
    )
    orderEditAddLineItemDiscount = Field(
        OrderEditAddLineItemDiscountPayload,
        args={
            'id': ID,
            'lineItemId': ID,
            'discount': OrderEditAppliedDiscountInput
        }
    )
    orderEditCommit = Field(
        OrderEditCommitPayload,
        args={
            'id': ID,
            'notifyCustomer': Boolean,
            'staffNote': String
        }
    )
    customerUpdate = Field(
        CustomerUpdatePayload,
        args={'input': 'CustomerUpdateInput'}
    )
    inventoryAdjustQuantities = Field(
        InventoryAdjustQuantitiesPayload,
        args={'input': InventoryAdjustQuantitiesInput}
    )

