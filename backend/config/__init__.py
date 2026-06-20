"""
Re-export global config singleton from config.py.

This allows imports like: from config import config
"""
from .config import config, Config

__all__ = ["config", "Config"]
