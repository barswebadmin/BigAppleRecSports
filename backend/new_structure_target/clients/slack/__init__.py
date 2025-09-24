"""
Slack client package. Avoid importing heavy modules at package import time to
prevent circular imports (e.g., package __init__ importing slack_service which
imports config, while config imports SlackConfig from this package).

Import concrete implementations directly, e.g.:
    from .slack_service import SlackService
"""

__all__ = []