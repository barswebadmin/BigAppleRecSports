"""
Re-export global config singleton from config.py.

This allows imports like: from backend.config import config
"""
from .config import config, Config

__all__ = ["config", "Config"]
