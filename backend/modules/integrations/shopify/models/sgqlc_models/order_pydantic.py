"""
Order models for Shopify GraphQL API.

Uses forward references to avoid circular imports with Customer models.
"""

from typing import Optional, List, TYPE_CHECKING, Dict, Any, Type
from pydantic import BaseModel, Field

from backend.modules.integrations.shopify.models.sgqlc_models.common_pydantic import Connection

from backend.modules.integrations.shopify.models.sgqlc_models.common_pydantic import ShopifyBaseModel, create_list_model

# Forward reference for Customer - only imported at type-checking time
if TYPE_CHECKING:
    from backend.modules.integrations.shopify.models.sgqlc_models.customer_pydantic import Customer


class MoneySet(BaseModel):
    """Money set with shop and presentment money."""
    amount: Optional[str] = None
    currencyCode: Optional[str] = None


class MoneySetWrapper(BaseModel):
    """Wrapper for money sets (shopMoney and presentmentMoney)."""
    shopMoney: Optional[MoneySet] = None
    presentmentMoney: Optional[MoneySet] = None


class RefundLineItem(BaseModel):
    """Refund line item model."""
    quantity: Optional[int] = None
    restockType: Optional[str] = None
    lineItem: Optional[Dict[str, Any]] = None  # Simplified - just id, name, title


class RefundTransaction(BaseModel):
    """Transaction within a refund."""
    id: Optional[str] = None
    kind: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[str] = None
    gateway: Optional[str] = None
    createdAt: Optional[str] = None


class Refund(BaseModel):
    """Refund model for Shopify orders."""
    id: str
    createdAt: Optional[str] = None
    note: Optional[str] = None
    totalRefundedSet: Optional[MoneySetWrapper] = None
    refundLineItems: Optional[Dict[str, Any]] = None  # Connection structure
    transactions: Optional[List[RefundTransaction]] = None


class Transaction(BaseModel):
    """Transaction model for Shopify orders."""
    id: str
    kind: Optional[str] = None
    gateway: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[str] = None
    createdAt: Optional[str] = None
    parentTransaction: Optional[Dict[str, str]] = None  # Just {id: str}


class CustomAttribute(BaseModel):
    """Custom attribute key-value pair."""
    key: str
    value: str


class InventoryItem(BaseModel):
    """Inventory item model for Shopify products."""
    id: str


class LineItemVariant(BaseModel):
    """Variant model for line items."""
    id: Optional[str] = None
    title: Optional[str] = None
    displayName: Optional[str] = None
    price: Optional[str] = None
    sku: Optional[str] = None
    inventoryQuantity: Optional[int] = None
    inventoryItem: Optional[InventoryItem] = None


class DiscountApplication(BaseModel):
    """Discount application model (union of DiscountCodeApplication, ScriptDiscountApplication, AutomaticDiscountApplication)."""
    code: Optional[str] = None  # For DiscountCodeApplication
    title: Optional[str] = None  # For ScriptDiscountApplication and AutomaticDiscountApplication


class LineItem(BaseModel):
    """Line item model for Shopify orders."""
    id: str
    name: Optional[str] = None
    title: Optional[str] = None
    quantity: Optional[int] = None
    fulfillableQuantity: Optional[int] = None
    fulfillmentStatus: Optional[str] = None
    originalUnitPriceSet: Optional[MoneySetWrapper] = None
    discountedUnitPriceSet: Optional[MoneySetWrapper] = None
    originalTotalSet: Optional[MoneySetWrapper] = None
    discountedTotalSet: Optional[MoneySetWrapper] = None
    customAttributes: List[CustomAttribute] = Field(default_factory=list)
    product: Optional[Dict[str, Any]] = None  # Full product fields
    variant: Optional[LineItemVariant] = None


@create_list_model
class Order(ShopifyBaseModel):
    """Complete order model with type safety."""
    id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    createdAt: Optional[str] = None
    cancelledAt: Optional[str] = None
    cancelReason: Optional[str] = None
    totalPriceSet: Optional[MoneySetWrapper] = None
    discountApplications: Optional[Connection["DiscountApplication"]] = None
    refunds: Optional[List[Refund]] = None
    transactions: Optional[List[Transaction]] = None
    lineItems: Optional[Connection["LineItem"]] = None
    customer: Optional["Customer"] = None
    
    # Declare list fields for automatic resolution (field name -> target type name)
    list_fields = {
        "refunds": "Refund",
        "transactions": "Transaction",
    }
    
    @property
    def customer_name(self) -> str:
        """Get customer name if available."""
        if not self.customer:
            return "N/A"
        
        # customer is a Connection[Customer]
        if isinstance(self.customer, Connection):
            if self.customer.edges:
                customer_node = self.customer.edges[0].node
                # customer_node is a Customer model instance
                from .customer import Customer
                if isinstance(customer_node, Customer):
                    if customer_node.displayName:
                        return customer_node.displayName
                    parts = [customer_node.firstName, customer_node.lastName]
                    return " ".join(p for p in parts if p) or "N/A"
        return "N/A"

