"""
SGQLC Customer models for Shopify GraphQL API.
"""

from typing import TYPE_CHECKING
from sgqlc.types import Type, Field, String, Int, Boolean, list_of
from sgqlc.types.relay import Connection, connection_args

if TYPE_CHECKING:
    from .order import OrderConnection


class Address(Type):
    """Address model (used by Customer)."""
    address1 = String
    address2 = String
    city = String
    province = String
    zip = String
    country = String


class Customer(Type):
    """Complete customer model with type safety."""
    id = String
    firstName = String
    lastName = String
    email = String
    displayName = String
    phone = String
    tags = list_of(String)
    numberOfOrders = Int
    createdAt = String
    updatedAt = String
    state = String
    verifiedEmail = Boolean
    defaultAddress = Address
    orders = Field('OrderConnection', args=connection_args())


class CustomerConnection(Connection):
    """Customer connection with nodes."""
    nodes = list_of(Customer)

