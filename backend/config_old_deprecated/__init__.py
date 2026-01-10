"""
Deprecated config package - do not use for new code.

This package is kept temporarily for backward compatibility.
All new code should use the global config singleton from backend.config.
"""
# This package should not import from backend.config to avoid circular imports
# Individual modules (slack.py, main.py, etc.) are self-contained
__all__ = []
