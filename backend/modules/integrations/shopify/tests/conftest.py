import os
import importlib
import pytest

from backend.clients.shopify import ShopifyClient as client_mod

@pytest.fixture(autouse=True)
def reset_client_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    yield

