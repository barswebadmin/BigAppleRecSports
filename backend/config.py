"""
Simple configuration loader that loads .env and exposes all environment variables via dot notation.
Supports nested dot notation (e.g., GOOGLE.SERVICE_ACCOUNT_FILE -> config.GOOGLE.SERVICE_ACCOUNT_FILE).
"""
from dotenv import load_dotenv, find_dotenv
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple


class Config:
    """
    Programmatic configuration that loads .env and exposes all environment variables
    via dot notation (e.g., config.SHOPIFY_TOKEN, config.GOOGLE.SERVICE_ACCOUNT_FILE).
    
    Environment variables with dots are organized into nested structures:
    - GOOGLE.SERVICE_ACCOUNT_FILE -> config.GOOGLE.SERVICE_ACCOUNT_FILE
    - SLACK.BOT_TOKEN_DEV -> config.SLACK.BOT_TOKEN_DEV
    """
    
    def __init__(self, data: Optional[Dict[str, Any]] = None):
        if data is None:
            env_path = find_dotenv('../.env')
            if env_path:
                load_dotenv(env_path, override=False)
            self._load_all_env_vars()
        else:
            self._load_from_dict(data)
    
    def _load_from_dict(self, data: Dict[str, Any]):
        """Load configuration from a dictionary."""
        for key, value in data.items():
            setattr(self, key, Config(value) if isinstance(value, dict) else value)
    
    def _parse_key(self, key: str) -> Tuple[Optional[str], Optional[str], bool]:
        """
        Parse a key into namespace and subkey if it contains a dot.
        Returns: (namespace, subkey, has_dot)
        """
        if '.' not in key:
            return None, None, False
        namespace, subkey = key.split('.', 1)
        return namespace.upper(), subkey.upper(), True
    
    def _get_or_create_namespace(self, namespace: str) -> 'Config':
        """Get existing namespace Config or create a new one."""
        if not hasattr(self, namespace):
            setattr(self, namespace, Config({}))
        return getattr(self, namespace)
    
    def _load_google_service_account(self):
        """Load Google service account JSON file into config.GOOGLE.SERVICE_ACCOUNT."""
        try:
            service_account_file = self.get("GOOGLE.SERVICE_ACCOUNT_FILE", "google-service-account.json")
            if not service_account_file:
                return
            
            # Construct path relative to backend directory
            backend_dir = Path(__file__).parent
            service_account_path = backend_dir / service_account_file
            
            if service_account_path.exists():
                with open(service_account_path, 'r') as f:
                    service_account_data = json.load(f)
                
                # Store in GOOGLE namespace
                if not hasattr(self, 'GOOGLE'):
                    setattr(self, 'GOOGLE', Config({}))
                
                google_config = getattr(self, 'GOOGLE')
                setattr(google_config, 'SERVICE_ACCOUNT', service_account_data)
        except Exception:
            # Silently fail if file doesn't exist or can't be loaded
            pass
    
    def _load_all_env_vars(self):
        """Load all environment variables and organize by dot notation."""
        nested_data: Dict[str, Dict[str, str]] = {}
        flat_vars: Dict[str, str] = {}
        
        for key, value in os.environ.items():
            namespace, subkey, has_dot = self._parse_key(key)
            if has_dot and namespace and subkey:
                nested_data.setdefault(namespace, {})[subkey] = value
            else:
                flat_vars[key.upper()] = value
        
        for namespace, values in nested_data.items():
            setattr(self, namespace, Config(values))
        
        for key, value in flat_vars.items():
            setattr(self, key, value)
        
        # Load Google service account JSON if it exists
        self._load_google_service_account()
    
    def __getattr__(self, name: str) -> Any:
        """
        Fallback getter for environment variables not yet loaded.
        This allows lazy access to env vars that might be set after initialization.
        """
        if name.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        
        value = os.getenv(name)
        if value is None:
            return None
        
        namespace, subkey, has_dot = self._parse_key(name)
        if has_dot and namespace and subkey:
            namespace_obj = self._get_or_create_namespace(namespace)
            setattr(namespace_obj, subkey, value)
        else:
            setattr(self, name.upper(), value)
        return value
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get environment variable by key with optional default.
        Supports dot notation (e.g., 'GOOGLE.SERVICE_ACCOUNT_FILE').
        """
        namespace, subkey, has_dot = self._parse_key(key)
        if has_dot and namespace and subkey:
            if hasattr(self, namespace):
                namespace_obj = getattr(self, namespace)
                if hasattr(namespace_obj, subkey):
                    return getattr(namespace_obj, subkey)
            return os.getenv(key, default)
        return os.getenv(key, default)
    
    @property
    def environment(self) -> str:
        """Get current environment (defaults to 'dev')."""
        return os.getenv("ENVIRONMENT", "dev").lower()
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return "prod" in self.environment.lower()


# Create global singleton instance
# This is the single source of truth for configuration
# Accessible via: from config import config
config = Config()

# Make it available as a module-level export
__all__ = ["Config", "config"]
