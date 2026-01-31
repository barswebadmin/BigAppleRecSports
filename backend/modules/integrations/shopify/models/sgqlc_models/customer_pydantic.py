"""
Customer models for Shopify GraphQL API.

Uses forward references to avoid circular imports with Order models.
"""

from typing import TYPE_CHECKING, Dict, Optional, Any
from pydantic import BaseModel, Field

from modules.integrations.shopify.models.sgqlc_models.common_pydantic import Connection
from sgqlc.operation import Operation
from sgqlc.types import Variable

from modules.integrations.shopify.models.sgqlc_models.common_pydantic import ShopifyBaseModel, create_list_model
from modules.integrations.shopify.models.sgqlc_models.sgqlc_bridge import get_sgqlc_type

# Forward reference for Order - only imported at type-checking time
if TYPE_CHECKING:
    from .order import Order


class Address(BaseModel):
    """Address model (used by Customer)."""
    address1: Optional[str] = None
    address2: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    zip: Optional[str] = None
    country: Optional[str] = None


@create_list_model
class Customer(ShopifyBaseModel):
    """Complete customer model with type safety."""
    id: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[str] = None
    displayName: Optional[str] = None
    phone: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    numberOfOrders: Optional[int] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    state: Optional[str] = None
    verifiedEmail: Optional[bool] = None
    defaultAddress: Optional[Address] = None
    orders: Optional[Connection["Order"]] = None
    
    @property
    def recent_orders(self) -> list["Order"]:
        """Get recent orders from Connection."""
        if self.orders and isinstance(self.orders, Connection):
            from .order import Order
            # Prefer nodes if available (simplified), otherwise extract from edges
            if self.orders.nodes:
                return [node for node in self.orders.nodes if isinstance(node, Order)]
            elif self.orders.edges:
                return [edge.node for edge in self.orders.edges if isinstance(edge.node, Order)]
        return []
    
    @classmethod
    def build_query(
        cls,
        query_str: str,
        first: int = 1,
        after: Optional[str] = None
    ) -> tuple[Operation, Dict[str, Any]]:
        """Build a GraphQL query for fetching customers using sgqlc.
        
        Uses bridge-generated sgqlc types from Pydantic models (no duplicate definitions).
        
        Args:
            query_str: GraphQL query string (e.g., "email:test@example.com")
            first: Number of results to fetch
            after: Cursor for pagination
            
        Returns:
            Tuple of (Operation object, variables dict)
        """
        from sgqlc.types import String, Int, Field as SGQLCField, Type as SGQLCType, list_of
        from sgqlc.types.relay import Connection as SGQLCConnection, connection_args
        
        # Generate sgqlc types from Pydantic models using bridge
        CustomerSGQLC = get_sgqlc_type(Customer)
        AddressSGQLC = get_sgqlc_type(Address)
        
        # Build CustomerConnection from CustomerSGQLC
        class CustomerConnection(SGQLCConnection):
            """Customer connection with nodes (simplified, skipping edges)."""
            nodes = list_of(CustomerSGQLC)
        
        # Build Query root type
        class Query(SGQLCType):
            """GraphQL Query root for fetching customers."""
            customers = SGQLCField(
                CustomerConnection,
                args=connection_args(query=String)
            )
        
        # Generate an operation on Query, selecting fields
        op = Operation(Query, variables={'query': String, 'first': Int, 'after': String})
        
        # Select a field with selection arguments
        customers = op.customers(
            first=Variable('first'),
            query=Variable('query'),
            after=Variable('after')
        )
        
        # Select sub-fields directly using nodes (simplified, skipping edges)
        customers.nodes.id()  # type: ignore[union-attr]
        customers.nodes.firstName()  # type: ignore[union-attr]
        customers.nodes.lastName()  # type: ignore[union-attr]
        customers.nodes.email()  # type: ignore[union-attr]
        customers.nodes.displayName()  # type: ignore[union-attr]
        customers.nodes.phone()  # type: ignore[union-attr]
        customers.nodes.tags()  # type: ignore[union-attr]
        customers.nodes.numberOfOrders()  # type: ignore[union-attr]
        customers.nodes.createdAt()  # type: ignore[union-attr]
        customers.nodes.updatedAt()  # type: ignore[union-attr]
        customers.nodes.state()  # type: ignore[union-attr]
        customers.nodes.verifiedEmail()  # type: ignore[union-attr]
        customers.nodes.defaultAddress.__fields__()  # type: ignore[union-attr]
        
        # Select pageInfo fields
        customers.page_info.__fields__('has_next_page', 'has_previous_page', 'start_cursor', 'end_cursor')  # type: ignore[union-attr]
        
        # Prepare variables dict
        variables = {
            'query': query_str,
            'first': first,
            'after': after
        }
        
        return op, variables
    
    @classmethod
    def build_update_mutation(
        cls,
        customer_id: str,
        new_email: Optional[str] = None,
        new_phone: Optional[str] = None
    ) -> tuple[Operation, Dict[str, Any]]:
        """Build a GraphQL mutation for updating a customer using sgqlc.
        
        Args:
            customer_id: Customer ID (gid://shopify/Customer/...)
            new_email: New email address (optional)
            new_phone: New phone number (optional)
            
        Returns:
            Tuple of (Operation object, variables dict)
            
        Raises:
            ValueError: If no update fields provided
        """
        from sgqlc.types import String, Input, Type as SGQLCType, Field as SGQLCField, list_of
        
        if not new_email and not new_phone:
            raise ValueError("Must provide either new_email or new_phone")
        
        # Define mutation input
        class CustomerInput(Input):
            email = String
            phone = String
        
        # Generate sgqlc types from Pydantic models using bridge
        CustomerSGQLC = get_sgqlc_type(Customer)
        
        # Define mutation response
        class CustomerUpdateResponse(SGQLCType):
            customer = CustomerSGQLC
            userErrors = list_of(dict)  # Simplified for now
        
        # Define Mutation root
        class Mutation(SGQLCType):
            customerUpdate = SGQLCField(
                CustomerUpdateResponse,
                args={'input': Input}
            )
        
        # Build operation
        op = Operation(Mutation, variables={'input': Input})
        
        # Build input dict
        customer_input = {}
        if new_email:
            customer_input["email"] = new_email
        if new_phone:
            customer_input["phone"] = new_phone
        
        # Select fields
        result = op.customerUpdate(input={'id': customer_id, 'customer': customer_input})
        result.customer.__fields__()  # type: ignore[union-attr]
        result.userErrors()  # type: ignore[union-attr]
        
        # Prepare variables
        variables = {
            'input': {
                'id': customer_id,
                'customer': customer_input
            }
        }
        
        return op, variables

