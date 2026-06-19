"""Google API service namespaces."""

from .drive import Drive
from .sheets import Sheets
from .directory import Directory
from .gmail import Gmail

__all__ = [
    "Drive",
    "Sheets",
    "Directory",
    "Gmail",
]
