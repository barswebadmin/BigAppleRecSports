"""
Simplified configuration loader.

Loads environment variables with dot notation into nested dictionaries.
Supports dictionary-style access: config['GOOGLE']['SERVICE_ACCOUNT']

Environment variables with dots are organized into nested structures:
- GOOGLE.SERVICE_ACCOUNT -> config['GOOGLE']['SERVICE_ACCOUNT'] (parsed as JSON if valid)
- SLACK.BOT_TOKEN_DEV -> config['SLACK']['BOT_TOKEN_DEV']
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv


class Config(dict):
    """
    Configuration dictionary that loads from environment variables.
    
    Supports nested access via dictionary keys:
        config['GOOGLE']['SERVICE_ACCOUNT']['private_key']
        config['SLACK']['BOT_TOKEN_DEV']
    
    Also supports attribute access for convenience:
        config.GOOGLE.SERVICE_ACCOUNT.private_key
    """
    
    def __init__(self):
        super().__init__()
        
        # Load .env file (local development)
        # In production (Render), env vars are injected directly
        load_dotenv(override=True)
        
        # Build nested structure from environment variables
        self._build_from_env()
    
    def _build_from_env(self) -> None:
        """Build nested dict structure from environment variables with dot notation."""
        # Sort environment variables to ensure consistent processing order
        sorted_env_items = sorted(os.environ.items())
        
        for key, value in sorted_env_items:
            if "." in key:
                # Build nested structure
                parts = key.split(".")
                if len(parts) >= 2:
                    current = self
                    
                    # Navigate/create nested structure
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = Config._create_nested()
                        elif not isinstance(current[part], dict):
                            # Can't navigate further if not a dict
                            break
                        current = current[part]
                    else:
                        # Set the final value
                        final_key = parts[-1]
                        
                        # Try to parse as JSON if it looks like JSON
                        parsed_value = self._try_parse_json(value)
                        current[final_key] = parsed_value
            else:
                # Store flat variables
                parsed_value = self._try_parse_json(value)
                self[key] = parsed_value
    
    @staticmethod
    def _create_nested() -> 'Config':
        """Create a new nested Config instance."""
        nested = Config.__new__(Config)
        dict.__init__(nested)
        return nested
    
    @staticmethod
    def _try_parse_json(value: str) -> Any:
        """Try to parse value as JSON, return original string if not valid JSON."""
        if not value:
            return value
        
        # Quick check if it looks like JSON
        if value.startswith(('{', '[')):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                pass
        
        return value
    
    def __getattr__(self, name: str) -> Any:
        """Allow attribute-style access: config.GOOGLE instead of config['GOOGLE']"""
        if name.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        
        try:
            return self[name]
        except KeyError:
            # Try loading from environment
            value = os.getenv(name)
            if value is not None:
                parsed_value = self._try_parse_json(value)
                self[name] = parsed_value
                return parsed_value
            
            # Return None instead of raising AttributeError for missing config keys
            return None
    
    def __setattr__(self, name: str, value: Any) -> None:
        """Allow attribute-style setting: config.GOOGLE = {...}"""
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self[name] = value
    
    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """
        Get config value by dot-notation key or dictionary key.
        
        Examples:
            config.get('GOOGLE.SERVICE_ACCOUNT')
            config.get('SLACK')
        """
        if "." not in key:
            return dict.get(self, key, default) or os.getenv(key, default)
        
        parts = key.split(".")
        current: Any = self
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return os.getenv(key, default)
        
        return current if current is not None else default
    
    @property
    def repo_root(self) -> Path:
        """Get repository root as a Path object."""
        repo_root_str = os.getenv('REPO_ROOT')
        if repo_root_str:
            return Path(repo_root_str).resolve()
        
        # Fallback: detect environment and calculate accordingly
        current_file = Path(__file__).resolve()
        
        # Check if we're in a monorepo structure (local dev)
        potential_repo_root = current_file.parent.parent.parent
        if (potential_repo_root / 'pyproject.toml').exists():
            # Monorepo structure: backend/config/config.py -> ../../../
            return potential_repo_root
        
        # Deployment structure: backend is the root
        # Navigate up from backend/config/config.py to backend/
        return current_file.parent.parent


# Create global singleton instance
config = Config()

__all__ = ["Config", "config"]
