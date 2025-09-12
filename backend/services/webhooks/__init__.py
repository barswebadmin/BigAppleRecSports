"""
Webhooks Service Package

Modular webhook processing system for external service integrations.
Currently supports Shopify product webhooks with waitlist form integration.
"""

from .orchestrator import WebhooksOrchestrator

# Main export for backward compatibility
WebhooksService = WebhooksOrchestrator

__all__ = ['WebhooksService', 'WebhooksOrchestrator']
