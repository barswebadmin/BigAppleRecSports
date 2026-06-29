"""
Direct sgqlc Type definitions for Customer models.

These are separate from Pydantic models and defined directly using sgqlc's Type system.
"""

from sgqlc.types import Type, Field, String, Int, Boolean, list_of, Enum
from sgqlc.types.relay import Connection


class OrderSortKeys(Enum):
    """Order sort keys enum for Shopify."""
    CREATED_AT = "CREATED_AT"
    UPDATED_AT = "UPDATED_AT"
    NUMBER = "NUMBER"
    TOTAL_PRICE = "TOTAL_PRICE"
    PROCESSED_AT = "PROCESSED_AT"
    # Add other sort keys as needed

# Register enum choices with sgqlc schema
OrderSortKeys.__choices__ = ("CREATED_AT", "UPDATED_AT", "NUMBER", "TOTAL_PRICE", "PROCESSED_AT")



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
    orders = Field('OrderConnection', args={'first': Int, 'sortKey': OrderSortKeys, 'reverse': Boolean})


class CustomerConnection(Connection):
    """Customer Connection type."""
    nodes = list_of(Customer)

