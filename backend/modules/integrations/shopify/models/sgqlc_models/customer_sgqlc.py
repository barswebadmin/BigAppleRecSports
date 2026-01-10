"""
Direct sgqlc Type definitions for Customer models.

These are separate from Pydantic models and defined directly using sgqlc's Type system.
"""

from sgqlc.types import Type, Field, String, Int, Boolean, list_of
from sgqlc.types.relay import Connection


class Address(Type):
    """Address sgqlc Type."""
    address1 = Field(String)
    address2 = Field(String)
    city = Field(String)
    province = Field(String)
    zip = Field(String)
    country = Field(String)


class Customer(Type):
    """Customer sgqlc Type."""
    id = Field(String)
    firstName = Field(String)
    lastName = Field(String)
    email = Field(String)
    displayName = Field(String)
    phone = Field(String)
    tags = Field(list_of(String))
    numberOfOrders = Field(Int)
    createdAt = Field(String)
    updatedAt = Field(String)
    state = Field(String)
    verifiedEmail = Field(Boolean)
    defaultAddress = Field(Address)
    # orders will be added as a Connection field in the Query class


class CustomerConnection(Connection):
    """Customer Connection type."""
    nodes = list_of(Customer)

