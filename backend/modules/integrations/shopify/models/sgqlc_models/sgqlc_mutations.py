"""
SGQLC Type definitions for Shopify GraphQL mutations.

Defines types for orderCancel and refundCreate mutations.
"""

from sgqlc.types import Type, Field, String, Boolean, ID, Int, list_of, Input, Enum
from sgqlc.operation import Operation
from typing import TYPE_CHECKING, Literal, Optional, Dict, Any, Tuple

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
    
    # ============================================================================
    # Mutation Builders
    # ============================================================================
    
    @classmethod
    def build_customer_update_mutation(
        cls,
        customer_id: str,
        email: Optional[str] = None,
        phone: Optional[str] = None
    ) -> Operation:
        """Build customerUpdate mutation operation.
        
        Args:
            customer_id: Customer ID (gid://shopify/Customer/...)
            email: New email address (optional)
            phone: New phone number (optional)
        
        Returns:
            Configured sgqlc Operation ready for execution
        """
        op = Operation(cls, variables={'input': CustomerUpdateInput})
        
        customer_input = {}
        if email:
            customer_input["email"] = email
        if phone:
            customer_input["phone"] = phone
        
        update_input = {
            "id": customer_id,
            "customer": customer_input
        }
        
        result = op.customerUpdate(input=update_input)  # type: ignore[call-arg]
        result.customer.id()  # type: ignore[attr-defined]
        result.customer.email()  # type: ignore[attr-defined]
        result.customer.phone()  # type: ignore[attr-defined]
        result.customer.firstName()  # type: ignore[attr-defined]
        result.customer.lastName()  # type: ignore[attr-defined]
        result.userErrors.field()  # type: ignore[attr-defined]
        result.userErrors.message()  # type: ignore[attr-defined]
        
        return op
    
    @classmethod
    def build_order_cancel_mutation(
        cls,
        order_id: str,
        reason: str,
        notify_customer: bool = False,
        refund: bool = False,
        restock: bool = False,
        staff_note: Optional[str] = None
    ) -> Operation:
        """Build orderCancel mutation operation.
        
        Args:
            order_id: Order ID (gid://shopify/Order/...)
            reason: Cancellation reason (CUSTOMER, FRAUD, INVENTORY, DECLINED, OTHER)
            notify_customer: Whether to notify customer (default: False)
            refund: Whether to refund the order (default: False)
            restock: Whether to restock items (default: False)
            staff_note: Optional staff note (default: "Cancelled via CLI")
        
        Returns:
            Configured sgqlc Operation ready for execution
        """
        op = Operation(cls)
        
        reason_value = reason.upper() if isinstance(reason, str) else reason
        
        result = op.orderCancel(
            notifyCustomer=notify_customer,
            orderId=order_id,
            reason=reason_value,
            refund=refund,
            restock=restock,
            staffNote=staff_note or "Cancelled via CLI"
        )
        
        result.job.__fields__('id', 'done')  # type: ignore[union-attr]
        result.orderCancelUserErrors.__fields__('field', 'message')  # type: ignore[union-attr]
        result.userErrors.__fields__('field', 'message')  # type: ignore[union-attr]
        
        return op
    
    @classmethod
    def build_refund_create_mutation(
        cls,
        refund_input: Dict[str, Any]
    ) -> Operation:
        """Build refundCreate mutation operation.
        
        Args:
            refund_input: Refund input dict with keys:
                - orderId: Order ID
                - notify: Whether to notify customer
                - note: Refund note
                - refundMethods: List of refund methods
                - transactions: List of transaction inputs
        
        Returns:
            Configured sgqlc Operation ready for execution
        """
        op = Operation(cls)
        
        result = op.refundCreate(input=refund_input)  # type: ignore[call-arg]
        result.refund.__fields__('id', 'createdAt', 'note', 'totalRefundedSet')  # type: ignore[union-attr]
        result.refund.totalRefundedSet.shopMoney.__fields__('amount', 'currencyCode')  # type: ignore[union-attr]
        result.refund.totalRefundedSet.presentmentMoney.__fields__('amount', 'currencyCode')  # type: ignore[union-attr]
        result.userErrors.__fields__('field', 'message')  # type: ignore[union-attr]
        
        return op
    
    @classmethod
    def build_order_edit_begin_mutation(
        cls,
        order_id: str
    ) -> Operation:
        """Build orderEditBegin mutation operation.
        
        Args:
            order_id: Order ID (gid://shopify/Order/...)
        
        Returns:
            Configured sgqlc Operation ready for execution
        """
        op = Operation(cls)
        
        result = op.orderEditBegin(id=order_id)
        result.calculatedOrder.id()  # type: ignore[attr-defined]
        result.userErrors.field()  # type: ignore[attr-defined]
        result.userErrors.message()  # type: ignore[attr-defined]
        
        return op
    
    @classmethod
    def build_order_edit_add_line_item_discount_mutation(
        cls,
        calculated_order_id: str,
        line_item_id: str,
        discount_input: Dict[str, Any]
    ) -> Operation:
        """Build orderEditAddLineItemDiscount mutation operation.
        
        Args:
            calculated_order_id: Calculated order ID from orderEditBegin
            line_item_id: Line item ID to apply discount to
            discount_input: Discount input dict with keys:
                - description: Discount description
                - fixedValue: MoneyInput dict with amount and currencyCode
        
        Returns:
            Configured sgqlc Operation ready for execution
        """
        op = Operation(cls)
        
        result = op.orderEditAddLineItemDiscount(
            id=calculated_order_id,
            lineItemId=line_item_id,
            discount=discount_input  # type: ignore[call-arg]
        )
        result.userErrors.field()  # type: ignore[attr-defined]
        result.userErrors.message()  # type: ignore[attr-defined]
        
        return op
    
    @classmethod
    def build_order_edit_commit_mutation(
        cls,
        calculated_order_id: str,
        notify_customer: bool = False,
        staff_note: Optional[str] = None
    ) -> Operation:
        """Build orderEditCommit mutation operation.
        
        Args:
            calculated_order_id: Calculated order ID from orderEditBegin
            notify_customer: Whether to notify customer (default: False)
            staff_note: Optional staff note
        
        Returns:
            Configured sgqlc Operation ready for execution
        """
        op = Operation(cls)
        
        result = op.orderEditCommit(
            id=calculated_order_id,
            notifyCustomer=notify_customer,
            staffNote=staff_note
        )
        result.userErrors.field()  # type: ignore[attr-defined]
        result.userErrors.message()  # type: ignore[attr-defined]
        
        return op
    
    @classmethod
    def build_inventory_adjust_quantities_mutation(
        cls,
        input_data: Dict[str, Any]
    ) -> Operation:
        """Build inventoryAdjustQuantities mutation operation.
        
        Args:
            input_data: Inventory adjustment input dict with keys:
                - reason: Adjustment reason (default: "correction")
                - name: Adjustment name (default: "available")
                - referenceDocumentUri: Optional reference URI
                - changes: List of InventoryChange dicts with:
                    - delta: Quantity change
                    - inventoryItemId: Inventory item ID
                    - locationId: Location ID
        
        Returns:
            Configured sgqlc Operation ready for execution
        """
        op = Operation(cls)
        
        result = op.inventoryAdjustQuantities(input=input_data)  # type: ignore[call-arg]
        result.userErrors.__fields__('field', 'message')  # type: ignore[union-attr]
        result.inventoryAdjustmentGroup.__fields__('createdAt', 'reason', 'referenceDocumentUri')  # type: ignore[union-attr]
        
        return op

