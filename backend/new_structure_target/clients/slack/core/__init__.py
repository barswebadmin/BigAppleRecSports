"""
Core Slack functionality package. Keep this __init__ lightweight to avoid
importing heavy dependencies (like slack_sdk) during package import.

Import concrete modules directly, e.g.:
    from .slack_security import SlackSecurity
    from .slack_client import SlackClient
"""

__all__ = []
