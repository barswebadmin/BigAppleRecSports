"""
Re-export global config singleton from backend/config.py.

This allows imports like: from config import config
"""
# Import from the symlinked config.py file in this directory
# This avoids circular import issues with backend.config module
from .config import config, Config

__all__ = ["config", "Config"]
