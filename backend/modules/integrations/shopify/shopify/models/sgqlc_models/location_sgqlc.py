"""Location sgqlc Type definitions."""

from sgqlc.types import Type, Field, String, ID, list_of
from sgqlc.types.relay import Connection



class Location(Type):
    """Location model."""
    id = Field(ID)
    name = Field(String)


class LocationConnection(Connection):
    """Location Connection type."""
    nodes = list_of(Location)

