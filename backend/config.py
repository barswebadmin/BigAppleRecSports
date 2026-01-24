"""
Simple configuration loader that loads .env and exposes all environment variables via dot notation.
Supports nested dot notation (e.g., GOOGLE.SERVICE_ACCOUNT_FILE -> config.GOOGLE.SERVICE_ACCOUNT_FILE).
"""
from dotenv import load_dotenv, find_dotenv
import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any


logger = logging.getLogger("ConfigLogger")
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
            self._load_dotenv()
            self._load_all_env_vars()
        else:
            self._load_from_dict(data)
    
    def _load_from_dict(self, data: Dict[str, Any]):
        """Load configuration from a dictionary."""
        for key, value in data.items():
            setattr(self, key, Config(value) if isinstance(value, dict) else value)

    def _load_dotenv(self) -> None:
        """Load a nearby .env file into os.environ (no override)."""
        candidates: list[Path] = []
        here = Path(__file__).resolve()
        candidates.append(here.parent / ".env")
        candidates.append(here.parent.parent / ".env")
        candidates.append(here.parent.parent.parent / ".env")

        for env_path in candidates:
            if env_path.exists():
                load_dotenv(env_path, override=False)
                return

        # Fallback to dotenv's discovery (best-effort)
        discovered = find_dotenv(".env", usecwd=True)
        if discovered:
            load_dotenv(discovered, override=False)

    @staticmethod
    def _normalize_key_part(part: str) -> str:
        return part.replace("-", "_").upper()

    @classmethod
    def _build_nested_dict(cls, flat: Dict[str, str]) -> Dict[str, Any]:
        root: Dict[str, Any] = {}
        for key, value in flat.items():
            parts = [cls._normalize_key_part(p) for p in key.split(".") if p]
            if len(parts) < 2:
                continue
            cur: Dict[str, Any] = root
            for seg in parts[:-1]:
                nxt = cur.get(seg)
                if not isinstance(nxt, dict):
                    nxt = {}
                    cur[seg] = nxt
                cur = nxt
            cur[parts[-1]] = value
        return root
    
    def _load_google_service_account(self):
        """Load Google service account JSON file into config.GOOGLE.SERVICE_ACCOUNT."""
        try:
            service_account_file = self.get("GOOGLE.SERVICE_ACCOUNT_FILE", "google-service-account.json")
            if not service_account_file:
                return
            
            # Construct path relative to backend directory
            # config.py might be in backend/config/__init__.py or backend/config.py
            # Go up to backend/ directory
            config_file_dir = Path(__file__).parent
            # If we're in backend/config/, go up one level to backend/
            if config_file_dir.name == 'config':
                backend_dir = config_file_dir.parent
            else:
                backend_dir = config_file_dir
            service_account_path = backend_dir / service_account_file
            
            if service_account_path.exists():
                with open(service_account_path, 'r') as f:
                    service_account_data = json.load(f)
                
                # Store in GOOGLE namespace
                if not hasattr(self, 'GOOGLE'):
                    setattr(self, 'GOOGLE', Config({}))
                
                google_config = getattr(self, 'GOOGLE')
                # Ensure google_config is a Config object, not None
                if google_config is None:
                    google_config = Config({})
                    setattr(self, 'GOOGLE', google_config)
                
                setattr(google_config, 'SERVICE_ACCOUNT', service_account_data)
            else:
                # File doesn't exist - log but don't fail (might be optional in some environments)
                logger.warning(
                    f"Google service account file not found: {service_account_path}. "
                    "Google API clients will not be available."
                )
        except Exception as e:
            # Log the error but don't fail config loading
            logger.error(f"Failed to load Google service account: {e}")
    
    def _load_all_env_vars(self):
        """Load all environment variables and organize by dot notation."""
        dotted: Dict[str, str] = {}
        flat_vars: Dict[str, str] = {}

        for key, value in os.environ.items():
            if "." in key:
                dotted[key] = value
            else:
                flat_vars[key.upper()] = value

        nested_data = self._build_nested_dict(dotted)
        for key, value in nested_data.items():
            setattr(self, key, Config(value) if isinstance(value, dict) else value)

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

        setattr(self, name.upper(), value)
        return value
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get environment variable by key with optional default.
        Supports dot notation (e.g., 'GOOGLE.SERVICE_ACCOUNT_FILE').
        """
        if "." not in key:
            return os.getenv(key, default)

        parts = [self._normalize_key_part(p) for p in key.split(".") if p]
        cur: Any = self
        for seg in parts:
            if not hasattr(cur, seg):
                return os.getenv(key, default)
            cur = getattr(cur, seg)
        return cur if isinstance(cur, str) else os.getenv(key, default)
    
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
