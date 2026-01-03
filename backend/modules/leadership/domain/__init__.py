"""
Leadership Domain Layer.

Contains pure business logic and domain models with NO external dependencies.
"""

from .models import PersonInfo, Position, LeadershipHierarchy

__all__ = [
    "PersonInfo",
    "Position",
    "LeadershipHierarchy",
]

