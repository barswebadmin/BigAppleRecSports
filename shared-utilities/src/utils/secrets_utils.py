"""
Secret Management Helper Functions
Converted from GAS secretsUtils.gs for Python usage
"""

import os
import re
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class SecretsManager:
    """
    Manages secrets for the application
    Provides compatibility with both environment variables and configuration files
    """

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize secrets manager

        Args:
            config_file: Optional path to configuration file
        """
        self.config_file = config_file
        self._config_cache: Optional[Dict[str, str]] = None

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a secret value

        Args:
            key: The secret key
            default: Default value if secret not found

        Returns:
            The secret value or default

        Raises:
            ValueError: If secret not found and no default provided
        """
        # First try environment variables
        value = os.getenv(key)
        if value is not None:
            return value

        # Try configuration file if provided
        if self.config_file and self._load_config():
            value = self._config_cache.get(key)
            if value is not None:
                return value

        # Return default or raise error
        if default is not None:
            return default

        raise ValueError(
            f"Secret '{key}' not found. Make sure it's set in environment variables or config file."
        )

    def set_secret(self, key: str, value: str) -> bool:
        """
        Set a secret value (environment variable)

        Args:
            key: Secret key
            value: Secret value

        Returns:
            Success status
        """
        try:
            os.environ[key] = value
            return True
        except Exception as e:
            logger.error(f"Error setting secret '{key}': {e}")
            return False

    def list_secret_keys(self, pattern: Optional[str] = None) -> List[str]:
        """
        List all available secret keys

        Args:
            pattern: Optional regex pattern to filter keys

        Returns:
            List of secret keys
        """
        keys = []

        # Get from environment variables
        env_keys = [k for k in os.environ.keys() if self._is_likely_secret(k)]
        keys.extend(env_keys)

        # Get from config file
        if self.config_file and self._load_config():
            config_keys = list(self._config_cache.keys())
            keys.extend(config_keys)

        # Remove duplicates
        keys = list(set(keys))

        # Filter by pattern if provided
        if pattern:
            regex = re.compile(pattern, re.IGNORECASE)
            keys = [k for k in keys if regex.search(k)]

        return sorted(keys)

    def test_secrets(
        self, test_keys: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Test if secrets are accessible and valid

        Args:
            test_keys: List of keys to test (defaults to common secrets)

        Returns:
            Test results for each key
        """
        if test_keys is None:
            test_keys = [
                "SHOPIFY_TOKEN",
                "SLACK_BOT_TOKEN",
                "API_ENDPOINT",
                "BACKEND_API_URL",
                "DATABASE_URL",
            ]

        results = {}

        for key in test_keys:
            try:
                value = self.get_secret(key)
                results[key] = {
                    "status": "success",
                    "length": len(value) if value else 0,
                    "preview": value[:10] + "..."
                    if value and len(value) > 10
                    else value,
                }
            except ValueError as e:
                results[key] = {"status": "error", "message": str(e)}

        return results

    def _load_config(self) -> bool:
        """Load configuration from file (if needed)"""
        if self._config_cache is not None:
            return True

        if not self.config_file or not os.path.exists(self.config_file):
            return False

        try:
            import json

            with open(self.config_file, "r") as f:
                self._config_cache = json.load(f)
            return True
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            return False

    def _is_likely_secret(self, key: str) -> bool:
        """Check if a key is likely to be a secret"""
        secret_indicators = [
            "token",
            "key",
            "secret",
            "password",
            "api",
            "webhook",
            "url",
            "endpoint",
            "database",
            "db",
            "auth",
        ]
        key_lower = key.lower()
        return any(indicator in key_lower for indicator in secret_indicators)


# Global instance for convenience
_default_manager = SecretsManager()


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Retrieve a secret using the default manager

    Args:
        key: Secret key
        default: Default value if not found

    Returns:
        Secret value or default
    """
    return _default_manager.get_secret(key, default)


def set_secret(key: str, value: str) -> bool:
    """
    Set a secret using the default manager

    Args:
        key: Secret key
        value: Secret value

    Returns:
        Success status
    """
    return _default_manager.set_secret(key, value)


def list_secret_keys(pattern: Optional[str] = None) -> List[str]:
    """
    List secret keys using the default manager

    Args:
        pattern: Optional regex pattern to filter keys

    Returns:
        List of secret keys
    """
    return _default_manager.list_secret_keys(pattern)


def test_secrets(test_keys: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    """
    Test secrets using the default manager

    Args:
        test_keys: List of keys to test

    Returns:
        Test results
    """
    return _default_manager.test_secrets(test_keys)


def identify_potential_secrets(code_content: str) -> List[Dict[str, str]]:
    """
    Scan code for potential hardcoded secrets

    Args:
        code_content: Code content to scan

    Returns:
        List of potential secret findings
    """
    secret_patterns = [
        (r'token["\']?\s*[:=]\s*["\'][^"\']+["\']', "Token"),
        (r'api[_-]?key["\']?\s*[:=]\s*["\'][^"\']+["\']', "API Key"),
        (r'secret["\']?\s*[:=]\s*["\'][^"\']+["\']', "Secret"),
        (r'password["\']?\s*[:=]\s*["\'][^"\']+["\']', "Password"),
        (r'bearer["\']?\s*[:=]\s*["\'][^"\']+["\']', "Bearer Token"),
        (r'webhook["\']?\s*[:=]\s*["\']https?://[^"\']+["\']', "Webhook URL"),
        (r'["\'][a-zA-Z0-9]{32,}["\']', "Long String (Potential Token)"),
    ]

    findings = []

    for pattern, description in secret_patterns:
        matches = re.finditer(pattern, code_content, re.IGNORECASE)
        for match in matches:
            findings.append(
                {
                    "type": description,
                    "match": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "line": code_content[: match.start()].count("\n") + 1,
                }
            )

    return findings


def setup_development_secrets() -> Dict[str, str]:
    """
    Set up common development secrets with placeholder values

    Returns:
        Dictionary of secret keys that were set up
    """
    dev_secrets = {
        "SHOPIFY_TOKEN": "your_shopify_token_here",
        "SHOPIFY_STORE": "your_store_name",
        "SHOPIFY_GRAPHQL_URL": "https://your-store.myshopify.com/admin/api/2024-01/graphql.json",
        "SLACK_BOT_TOKEN": "xoxb-your-slack-bot-token",
        "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        "API_ENDPOINT": "https://your-api.example.com",
        "BACKEND_API_URL": "https://your-backend.example.com",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/dbname",
        "DEBUG_EMAIL": "debug@example.com",
    }

    setup_results = {}

    for key, default_value in dev_secrets.items():
        # Only set if not already present
        if not os.getenv(key):
            setup_results[key] = default_value
            logger.warning(f"Setting development placeholder for {key}")
        else:
            setup_results[key] = "already_set"

    return setup_results


def validate_secret_format(key: str, value: str) -> Dict[str, Any]:
    """
    Validate that a secret value has the expected format

    Args:
        key: Secret key
        value: Secret value to validate

    Returns:
        Validation result
    """
    validations = {
        "SHOPIFY_TOKEN": {
            "pattern": r"^shpat_[a-f0-9]{32}$",
            "description": "Shopify private app token (shpat_...)",
        },
        "SLACK_BOT_TOKEN": {
            "pattern": r"^xoxb-\d+-\d+-[a-zA-Z0-9]+$",
            "description": "Slack bot token (xoxb-...)",
        },
        "DATABASE_URL": {
            "pattern": r"^postgresql://.*",
            "description": "PostgreSQL connection URL",
        },
        "API_ENDPOINT": {"pattern": r"^https?://.*", "description": "HTTP(S) URL"},
    }

    if key in validations:
        validation = validations[key]
        pattern = validation["pattern"]

        if re.match(pattern, value):
            return {"valid": True, "message": f'Valid {validation["description"]}'}
        else:
            return {
                "valid": False,
                "message": f'Invalid format. Expected: {validation["description"]}',
                "pattern": pattern,
            }

    # Generic validation for unknown keys
    if len(value) < 8:
        return {
            "valid": False,
            "message": "Secret value is too short (minimum 8 characters)",
        }

    return {"valid": True, "message": "Format validation passed"}
