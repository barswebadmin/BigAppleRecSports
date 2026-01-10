"""
SGQLC Type definitions for Shopify GraphQL mutations.

Defines types for orderCancel and refundCreate mutations.
"""

from sgqlc.types import Type, Field, String, Boolean, ID, list_of, Input, Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# ============================================================================
# Enums
# ============================================================================

class OrderCancelReason(Enum):
    """Order cancellation reason enum."""
    CUSTOMER = "CUSTOMER"
    FRAUD = "FRAUD"
    INVENTORY = "INVENTORY"
    DECLINED = "DECLINED"
    OTHER = "OTHER"


# ============================================================================
# Input Types (using Input base class for mutation inputs)
# ============================================================================

class MoneyInput(Type):
    """Money input for refunds."""
    amount = Field(String)
    currencyCode = Field(String)


class StoreCreditRefund(Type):
    """Store credit refund input."""
    amount = Field(MoneyInput)


class RefundMethod(Type):
    """Refund method input."""
    storeCreditRefund = Field(StoreCreditRefund)


class TransactionInput(Type):
    """Transaction input for refunds."""
    orderId = Field(ID)
    gateway = Field(String)
    kind = Field(String)  # "REFUND"
    amount = Field(String)
    parentId = Field(ID)


class RefundInput(Type):
    """Input for refundCreate mutation."""
    notify = Field(Boolean)
    orderId = Field(ID)
    note = Field(String)
    refundMethods = Field(list_of(RefundMethod))
    transactions = Field(list_of(TransactionInput))


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

