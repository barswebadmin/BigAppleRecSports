import importlib
import os
import sys


def reload_config_module():
    # Ensure fresh import so Config() re-runs with current env
    if "backend.config" in sys.modules:
        del sys.modules["backend.config"]
    import backend.config as config_module
    return importlib.reload(config_module)


def test_staging_env_uses_prod_shopify_creds(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("SHOPIFY_STORE_ID", "prod-store-id")
    monkeypatch.setenv("SHOPIFY_TOKEN_ADMIN", "prod-admin-token")
    monkeypatch.setenv("SHOPIFY_LOCATION_ID", "prod-location-id")

    config_module = reload_config_module()
    cfg = config_module.config

    assert cfg.environment == "staging"
    # ShopifyConfig uses production creds for staging/production
    assert cfg.Shopify.store_id == "prod-store-id"
    assert cfg.Shopify.token == "prod-admin-token"
    assert cfg.Shopify.location_id == "prod-location-id"
    # is_production only true for explicit production
    assert cfg.is_production is False
    # SlackConfig honors passed ENVIRONMENT from Config
    assert cfg.Slack.environment == "staging"


def test_production_env_uses_prod_shopify_creds(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SHOPIFY_STORE_ID", "prod-store-id")
    monkeypatch.setenv("SHOPIFY_TOKEN_ADMIN", "prod-admin-token")
    monkeypatch.setenv("SHOPIFY_LOCATION_ID", "prod-location-id")

    config_module = reload_config_module()
    cfg = config_module.config

    assert cfg.environment == "production"
    assert cfg.Shopify.store_id == "prod-store-id"
    assert cfg.Shopify.token == "prod-admin-token"
    assert cfg.Shopify.location_id == "prod-location-id"
    assert cfg.is_production is True
    assert cfg.Slack.environment == "production"


def test_dev_env_uses_dev_shopify_creds(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("SHOPIFY_DEV_STORE", "dev-store")
    monkeypatch.setenv("SHOPIFY_DEV_TOKEN", "dev-token")
    monkeypatch.setenv("SHOPIFY_DEV_LOCATION_ID", "dev-location")

    config_module = reload_config_module()
    cfg = config_module.config

    assert cfg.environment == "dev"
    assert cfg.Shopify.store_id == "dev-store"
    assert cfg.Shopify.token == "dev-token"
    assert cfg.Shopify.location_id == "dev-location"


