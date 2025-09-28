import os
import importlib
import pytest


@pytest.fixture(autouse=True)
def config_test_env(monkeypatch):
    # Set test environment and dummy Shopify creds
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("SHOPIFY_STORE_ID", "dummy-store")
    monkeypatch.setenv("SHOPIFY_TOKEN_ADMIN", "dummy-token")

    # Reload backend.config to pick up env vars
    import backend.config as conf
    importlib.reload(conf)

    # Also update modules that imported `config` by value
    import backend.new_structure_target.clients.shopify.core.shopify_client as client_mod
    client_mod.config = conf.config

    yield conf.config

