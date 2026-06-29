"""
SGQLC models for Shopify File types.
"""

from sgqlc.types import Type, Field, String, ID, list_of
from sgqlc.types.relay import Connection


class File(Type):
    """File interface - represents a file in Shopify."""
    id = Field(ID)
    fileStatus = Field(String)


class FileConnection(Connection):
    """Connection for files query."""
    nodes = list_of(File)
