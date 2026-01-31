"""Legacy service management for CLI commands.

This module contains all the lazy service initialization logic that will be
removed after migration to the BARS API. All CLI commands will eventually
use the HTTP client from context.py instead of these direct service imports.

TODO: Remove this entire file after migration is complete.
"""

from typing import Any, Dict, Optional, Callable

import click_extra as click

# Legacy service imports - will be removed after migration
from bars_cli.backend_services.shopify.services import ShopifyService
from bars_cli.backend_services.slack.slack_service import SlackService


class LazyServiceDict(dict):
    """Dict that lazily initializes services when accessed via [].

    When a service key is accessed (e.g., ctx.meta['shopify_service']),
    if it doesn't exist, it automatically calls the creation callback
    to create and cache the service.
    """

    # Service creation functions (Legacy - will be removed after migration)
    _SERVICE_CREATORS: Dict[str, Callable[[], Any]] = {
        'shopify_service': lambda: ShopifyService(environment='production'),
        'slack_service': lambda: SlackService(),
    }

    def __missing__(self, key: str) -> Any:
        """Lazily create service when accessed via [] if creator exists."""
        # Check if this is a service key
        if key in self._SERVICE_CREATORS:
            try:
                create_func = self._SERVICE_CREATORS[key]
                service = create_func()
                self[key] = service
                return service
            except Exception as e:
                self[f'{key}_error'] = str(e)
                raise click.ClickException(f"Failed to create {key}: {e}") from e

        # Check if creator is stored in meta (for ctx.meta compatibility)
        callback_key = f'_create_{key}'
        if callback_key in self:
            try:
                create_func = self[callback_key]
                service = create_func()
                self[key] = service
                return service
            except Exception as e:
                self[f'{key}_error'] = str(e)
                raise click.ClickException(f"Failed to create {key}: {e}") from e

        raise KeyError(key)


class LazyServiceProxy:
    """Proxy object that creates a service lazily when accessed.

    When stored in ctx.meta["shopify_service"], accessing attributes or calling
    methods on the proxy will create the actual service on first access and forward
    the operation to it.

    Example:
        service = ctx.meta["shopify_service"]  # Returns LazyServiceProxy
        service.get_product_by_identifier(...)  # Creates service, forwards call
    """
    def __init__(self, create_func: Callable[[], Any], service_key: str):
        self._create_func = create_func
        self._service_key = service_key
        self._service: Optional[Any] = None
        self._error: Optional[str] = None

    def _get_service(self) -> Any:
        """Get the service, creating it if needed."""
        if self._error:
            raise click.ClickException(f"Failed to create {self._service_key}: {self._error}")

        if self._service is None:
            try:
                self._service = self._create_func()
            except Exception as e:
                self._error = str(e)
                raise click.ClickException(f"Failed to create {self._service_key}: {e}") from e

        return self._service

    def __getattr__(self, name: str) -> Any:
        """Forward attribute access to the actual service."""
        return getattr(self._get_service(), name)

    def __repr__(self) -> str:
        """Return representation of the proxy."""
        if self._service is not None:
            return repr(self._service)
        return f"<LazyServiceProxy for {self._service_key}>"


class LazyServiceMeta(dict):
    """Dict wrapper that intercepts service access and creates services lazily.

    When a service key is accessed (e.g., ctx.meta["shopify_service"]),
    it checks if the value is a callable (creation function) and invokes it
    to create the service, then caches and returns it.
    """
    def __init__(self, wrapped_dict: dict):
        super().__init__(wrapped_dict)
        self._wrapped = wrapped_dict

    def __getitem__(self, key: str) -> Any:
        """Get item, creating service lazily if key is a service creator."""
        # Check if key exists in wrapped dict
        if key not in self._wrapped:
            raise KeyError(key)

        value = self._wrapped[key]

        # If value is a callable and it's a service creator, invoke it
        if callable(value) and key in LazyServiceDict._SERVICE_CREATORS:
            try:
                service = value()
                # Cache the created service
                self._wrapped[key] = service
                return service
            except Exception as e:
                self._wrapped[f'{key}_error'] = str(e)
                raise click.ClickException(f"Failed to create {key}: {e}") from e

        return value

    def __setitem__(self, key: str, value: Any) -> None:
        """Set item in wrapped dict."""
        self._wrapped[key] = value
        super().__setitem__(key, value)

    def __contains__(self, key: str) -> bool:
        """Check if key exists in wrapped dict."""
        return key in self._wrapped

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Get item with default, creating service lazily if needed."""
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self):
        """Return keys from wrapped dict."""
        return self._wrapped.keys()

    def values(self):
        """Return values from wrapped dict."""
        return self._wrapped.values()

    def items(self):
        """Return items from wrapped dict."""
        return self._wrapped.items()

    def clear(self) -> None:
        """Clear wrapped dict."""
        self._wrapped.clear()
        super().clear()

    def update(self, other: dict) -> None:
        """Update wrapped dict."""
        self._wrapped.update(other)
        super().update(other)


def get_service(ctx: click.Context, service_key: str) -> Any:
    """Get a service from ctx.meta, creating it lazily if needed.

    If the value in ctx.meta is a callable (creation function), it will be invoked
    to create the service, which is then cached in ctx.meta.

    This enables lazy service initialization: services are created on first access
    rather than at initialization time.

    Args:
        ctx: Click context
        service_key: Service key to retrieve (e.g., 'shopify_service')

    Returns:
        The service instance

    Raises:
        KeyError: If service_key is not found in ctx.meta
        ClickException: If service creation fails
    """
    if service_key not in ctx.meta:
        raise KeyError(service_key)
    service_value = ctx.meta[service_key]

    # If value is a callable (creation function), invoke it to create the service
    if callable(service_value):
        try:
            service = service_value()
            # Cache the created service
            ctx.meta[service_key] = service
            return service
        except Exception as e:
            ctx.meta[f'{service_key}_error'] = str(e)
            raise click.ClickException(f"Failed to create {service_key}: {e}") from e

    # Value is already a service instance, return it
    return service_value